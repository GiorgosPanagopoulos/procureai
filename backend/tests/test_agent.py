"""Agent-core tests: the ReAct loop in agent/executor.py driven by a scripted, offline LLM.

The LLM is replaced at the import site the executor actually uses
(agent.executor.claude_llm) with a BaseChatModel that replays canned ReAct
turns, so the real AgentExecutor, output parser, tools and trace builder all
run without touching Anthropic, MongoDB or ChromaDB.
"""

import sys
from typing import Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

# Stub the LLM/embedding stack BEFORE importing agent.* so no real clients or
# ChromaDB connections are opened during test collection (same as test_tools.py).
sys.modules.setdefault("rag.embeddings", MagicMock())
sys.modules.setdefault("rag.vectorstore", MagicMock())
sys.modules.setdefault("llm.clients", MagicMock())

import agent.tools as tools_module  # noqa: E402
from agent.executor import run_agent  # noqa: E402
from exceptions import AgentExecutionError  # noqa: E402
from llm.pricing import _current_usage  # noqa: E402


class ScriptedChatModel(BaseChatModel):
    """Replays `responses` in order (wrapping around) and records every prompt it was sent.

    An Exception instance in `responses` is raised instead of returned, to
    simulate an API failure mid-loop.
    """

    responses: List[Any]
    prompts: List[str] = []
    calls: int = 0

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        self.prompts.append(str(messages[-1].content))
        reply = self.responses[self.calls % len(self.responses)]
        self.calls += 1
        if isinstance(reply, Exception):
            raise reply
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=reply))])


def _action(tool: str, tool_input: str, thought: str = "I should use a tool.") -> str:
    return f"Thought: {thought}\nAction: {tool}\nAction Input: {tool_input}"


FINAL = "Thought: I now know the final answer\nFinal Answer: Here is what I found."


def _fake_executor_db() -> MagicMock:
    """Stand-in for the `db` used by run_agent to persist usage and the trace."""
    return MagicMock(
        usage=MagicMock(insert_one=AsyncMock()),
        conversations=MagicMock(update_one=AsyncMock()),
    )


def _fake_tools_db(suppliers: Optional[list] = None, bids: Optional[list] = None) -> MagicMock:
    """Stand-in for the `db` used by the tools: find(...)[.limit(n)].to_list(...)."""

    def _collection(docs, error: Optional[Exception] = None):
        cursor = MagicMock()
        cursor.limit.return_value = cursor
        cursor.to_list = AsyncMock(return_value=docs)
        find = MagicMock(side_effect=error) if error else MagicMock(return_value=cursor)
        return MagicMock(find=find, count_documents=AsyncMock(return_value=len(docs)))

    return MagicMock(
        suppliers=_collection(suppliers or []),
        bids=_collection(bids or []),
    )


SUPPLIER = {"name": "Acme IT", "category": "IT Hardware", "rating": 4.5, "contact": "n/a"}


@pytest.fixture
def executor_db():
    fake = _fake_executor_db()
    with patch("agent.executor.db", fake):
        yield fake


async def _run(llm: ScriptedChatModel, user_input: str, tools_db: Optional[MagicMock] = None):
    with (
        patch("agent.executor.claude_llm", llm),
        patch("agent.tools.db", tools_db or _fake_tools_db()),
    ):
        return await run_agent(user_input, "conv-test")


# ── run_agent ────────────────────────────────────────────────────────────────


async def test_run_agent_returns_final_answer_and_trace(executor_db):
    llm = ScriptedChatModel(responses=[_action("supplier_lookup", "IT Hardware"), FINAL])

    result = await _run(llm, "Find IT hardware suppliers", _fake_tools_db(suppliers=[SUPPLIER]))

    assert result["response"] == "Here is what I found."
    assert result["tool_used"] == "supplier_lookup"
    assert result["conversation_id"] == "conv-test"
    assert [t["type"] for t in result["trace"]] == ["thought", "tool_call", "observation"]
    assert result["trace"][0]["content"] == "I should use a tool."
    assert result["trace"][1] == {
        "type": "tool_call",
        "tool": "supplier_lookup",
        "input": "IT Hardware",
    }
    assert "Acme IT" in result["trace"][2]["content"]
    assert set(result["usage"]) >= {"input_tokens", "output_tokens", "cost_usd"}

    executor_db.usage.insert_one.assert_awaited_once()
    executor_db.conversations.update_one.assert_awaited_once()
    persisted = executor_db.conversations.update_one.call_args.args[1]["$set"]
    assert persisted["trace"] == result["trace"]
    assert executor_db.conversations.update_one.call_args.kwargs["upsert"] is True


async def test_trace_lists_tool_calls_in_order(executor_db):
    llm = ScriptedChatModel(
        responses=[
            _action("supplier_lookup", "IT Hardware", thought="First the suppliers."),
            _action("report_generation", "summary", thought="Now the report."),
            FINAL,
        ]
    )

    result = await _run(llm, "Suppliers, then a report", _fake_tools_db(suppliers=[SUPPLIER]))

    tool_calls = [t["tool"] for t in result["trace"] if t["type"] == "tool_call"]
    assert tool_calls == ["supplier_lookup", "report_generation"]
    thoughts = [t["content"] for t in result["trace"] if t["type"] == "thought"]
    assert thoughts == ["First the suppliers.", "Now the report."]
    assert result["tool_used"] == "supplier_lookup"
    # Each LLM turn sees the scratchpad built from the previous observations.
    assert "Acme IT" not in llm.prompts[0]
    assert "Acme IT" in llm.prompts[1]
    assert "PROCUREMENT REPORT" not in llm.prompts[1]
    assert "PROCUREMENT REPORT" in llm.prompts[2]


async def test_max_iterations_is_respected(executor_db):
    # An LLM that never produces a Final Answer must be cut off by max_iterations=5.
    llm = ScriptedChatModel(responses=[_action("supplier_lookup", "anything")])

    result = await _run(llm, "Loop forever")

    tool_calls = [t for t in result["trace"] if t["type"] == "tool_call"]
    assert len(tool_calls) == 5
    assert llm.calls == 5
    assert "stopped" in result["response"].lower()


async def test_tool_error_surfaces_as_observation_not_crash(executor_db):
    llm = ScriptedChatModel(responses=[_action("bid_comparison", ""), FINAL])
    tools_db = _fake_tools_db()
    tools_db.bids.find.side_effect = RuntimeError("mongo unavailable")

    result = await _run(llm, "Compare bids", tools_db)

    observations = [t["content"] for t in result["trace"] if t["type"] == "observation"]
    assert observations == ["Error comparing bids: mongo unavailable"]
    # The loop kept going: the error was fed back to the LLM, which then finished.
    assert "Error comparing bids: mongo unavailable" in llm.prompts[1]
    assert result["response"] == "Here is what I found."


async def test_pii_is_redacted_before_reaching_the_agent(executor_db):
    llm = ScriptedChatModel(responses=[FINAL])
    raw = "Supplier AFM 123456789, contact maria@example.gr, please check"

    await _run(llm, raw)

    assert len(llm.prompts) == 1
    prompt = llm.prompts[0]
    assert "123456789" not in prompt
    assert "maria@example.gr" not in prompt
    assert "[AFM_REDACTED]" in prompt
    assert "[EMAIL_REDACTED]" in prompt
    # The persisted query is the redacted one as well.
    persisted = executor_db.conversations.update_one.call_args.args[1]["$set"]
    assert (
        persisted["query"] == "Supplier AFM [AFM_REDACTED], contact [EMAIL_REDACTED], please check"
    )


async def test_malformed_llm_output_is_recovered(executor_db):
    # handle_parsing_errors=True: a turn with neither Action nor Final Answer
    # becomes an "_Exception" step whose observation asks the LLM to retry.
    llm = ScriptedChatModel(responses=["Thought: hmm, not sure what to do here.", FINAL])

    result = await _run(llm, "Something vague")

    assert result["response"] == "Here is what I found."
    tool_calls = [t["tool"] for t in result["trace"] if t["type"] == "tool_call"]
    assert tool_calls == ["_Exception"]
    assert "Missing 'Action:'" in result["trace"][-1]["content"]


async def test_llm_failure_raises_agent_execution_error(executor_db):
    llm = ScriptedChatModel(responses=[ConnectionError("anthropic down")])

    with pytest.raises(AgentExecutionError) as excinfo:
        await _run(llm, "Anything")

    assert "anthropic down" in str(excinfo.value.detail)
    # The usage ContextVar must be reset even on failure.
    assert _current_usage.get() is None
    executor_db.usage.insert_one.assert_not_awaited()


async def test_empty_input_short_circuits_without_llm(executor_db):
    llm = ScriptedChatModel(responses=[FINAL])

    result = await _run(llm, "   ")

    assert result["response"] == "Please provide a query."
    assert result["trace"] == []
    assert llm.calls == 0
    executor_db.usage.insert_one.assert_not_awaited()


# ── document_qa ──────────────────────────────────────────────────────────────


def _fake_anthropic(answer: str) -> MagicMock:
    from anthropic.types import TextBlock

    response = MagicMock()
    response.content = [TextBlock(text=answer, type="text")]
    response.usage = MagicMock(
        input_tokens=10, output_tokens=5, cache_creation_input_tokens=0, cache_read_input_tokens=0
    )
    client = MagicMock()
    client.messages.create = AsyncMock(return_value=response)
    return client


def _context_sent_to_claude(client: MagicMock) -> str:
    return client.messages.create.call_args.kwargs["messages"][0]["content"][0]["text"]


async def test_document_qa_with_no_documents():
    from agent.tools import document_qa

    chroma = MagicMock()
    chroma.count.return_value = 50
    chroma.query.return_value = {"documents": [[]], "metadatas": [[]]}
    client = _fake_anthropic("The information is not available in the provided documents.")

    with (
        patch("agent.tools.get_active_user_id", return_value="user-1"),
        patch("agent.tools.embed_text", return_value=[0.0] * 4),
        patch("agent.tools.chroma_collection", chroma),
        patch("agent.tools._raw_anthropic_async", client),
    ):
        answer = await document_qa.ainvoke("What are the warranty terms?")

    assert _context_sent_to_claude(client) == "Context:\nNo relevant documents found."
    assert answer == "The information is not available in the provided documents."
    assert "Sources:" not in answer


async def test_document_qa_reranker_reorders_and_truncates():
    from agent.tools import document_qa

    docs = [f"chunk-{i}" for i in range(6)]
    chroma = MagicMock()
    chroma.count.return_value = 50
    chroma.query.return_value = {
        "documents": [docs],
        "metadatas": [[{"source": f"doc{i}.pdf"} for i in range(6)]],
    }
    # Higher score = more relevant: reverse Chroma's order.
    reranker = MagicMock()
    reranker.predict.return_value = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    client = _fake_anthropic("Reranked answer")

    with (
        patch("agent.tools.get_active_user_id", return_value="user-1"),
        patch.object(tools_module.settings, "USE_RERANKER", True),
        patch("agent.tools._get_reranker", return_value=reranker),
        patch("agent.tools.embed_text", return_value=[0.0] * 4),
        patch("agent.tools.chroma_collection", chroma),
        patch("agent.tools._raw_anthropic_async", client),
    ):
        answer = await document_qa.ainvoke("Payment terms?")

    # Reranking mode retrieves a wider candidate set (20) before narrowing to 5,
    # as long as the store holds at least that many chunks.
    assert chroma.query.call_args.kwargs["n_results"] == 20
    reranker.predict.assert_called_once_with([("Payment terms?", d) for d in docs])
    assert _context_sent_to_claude(client) == "Context:\n" + "\n".join(
        ["chunk-5", "chunk-4", "chunk-3", "chunk-2", "chunk-1"]
    )
    assert answer.startswith("Reranked answer")
    sources = answer.split("Sources: ")[1].split(", ")
    assert set(sources) == {"doc5.pdf", "doc4.pdf", "doc3.pdf", "doc2.pdf", "doc1.pdf"}


# ── chat prompt ──────────────────────────────────────────────────────────────


def test_chat_prompt_answers_in_the_language_of_the_message():
    # v1.3 rule: the 2026-09-12 eval run answered English queries in Greek because the
    # prompt only said what to do for Greek input. The executor's prompt must carry the
    # bidirectional rule so the language check never silently regresses.
    from agent.prompt import get_react_prompt

    template = get_react_prompt().template

    assert (
        "Always respond in the same language as the user's message. If the message is in "
        "English, answer in English; if in Greek, answer in Greek. Retrieved documents may be "
        "in Greek regardless of the answer language."
    ) in template
    assert "Respond in Greek when the user writes in Greek." not in template


def test_chat_prompt_keeps_document_currency_and_formats_database_prices_as_eur():
    # v1.5 rule: the v1.2 "all prices are EUR" rule made the agent relabel document
    # figures. In eval q01 (2026-09-12c) document_qa quoted "$875,500.00 USD" from
    # contract_techsupply.pdf and the final answer printed "€875,500.00" — same number,
    # swapped symbol. The prompt must state both halves: database prices are EUR,
    # document figures keep the currency the document states.
    from agent.prompt import get_react_prompt

    template = get_react_prompt().template
    currency_rules = template.split("CURRENCY RULES")[1].split("TOOL SELECTION RULES")[0]

    database_rule = next(line for line in currency_rules.splitlines() if "database" in line)
    for tool_name in ("bid_comparison", "supplier_lookup", "report_generation"):
        assert tool_name in database_rule
    assert "in EUR" in database_rule
    assert "€ with two decimals" in database_rule

    document_rule = next(line for line in currency_rules.splitlines() if "document_qa" in line)
    assert "keep the currency stated in the document" in document_rule
    assert "Never relabel them and never convert them" in document_rule
    assert "if a document says USD, say USD and name the source document" in document_rule

    # The old blanket rule must be gone: it is what produced the relabelling.
    assert "All prices are in EUR" not in template


def test_chat_prompt_separates_aggregates_from_bid_comparisons():
    # v1.4 sent q18 ("total value of all bids") to report_generation, but its "all bids"
    # wording also pulled q12 ("average delivery time across all bids") and q13 ("show
    # accepted bids") there (2026-09-12c: 17/18 → 15/18). v1.5 narrows it: only totals,
    # counts and status breakdowns are aggregates; ranking, comparing, listing or
    # filtering bids is bid_comparison even when the request spans every bid, because
    # it returns a ranked list rather than one figure.
    from agent.prompt import get_react_prompt
    from core.prompt_loader import prompt_loader

    template = get_react_prompt().template
    rules = template.split("TOOL SELECTION RULES")[1].split("{tools}")[0]

    aggregate_rule = next(line for line in rules.splitlines() if "total value of all bids" in line)
    assert "ALWAYS use report_generation" in aggregate_rule
    assert "totals, sums, counts and status breakdowns across ALL bids" in aggregate_rule
    assert "συνοπτική αναφορά όλων των προσφορών" in aggregate_rule
    # The v1.4 catch-alls that misrouted q12/q13 must not come back.
    for cue in ("overviews", "statistics across the whole dataset", '"summary of all bids"'):
        assert cue not in aggregate_rule

    comparison_rule = next(line for line in rules.splitlines() if "use bid_comparison" in line)
    assert "ranking, comparing, listing or filtering bids" in comparison_rule
    assert "even when the request spans every bid" in comparison_rule
    assert "returns the individual bids as a ranked list" in comparison_rule
    assert "empty string for the full ranked set" in comparison_rule
    assert '"show accepted bids"' in comparison_rule
    assert '"delivery times across all bids"' in comparison_rule
    assert "Never use it" not in comparison_rule
    assert "specific subset" not in comparison_rule

    assert prompt_loader.get_with_metadata("chat").metadata.version == "v1.5"


def test_bid_comparison_description_matches_routing_rules():
    # The agent sees the tool docstring through {tools}; it must not contradict the
    # prompt. The previous wording said overviews "of all bids" belong to
    # report_generation, which is what pulled q12/q13 the wrong way.
    from agent.tools import bid_comparison

    description = " ".join(bid_comparison.description.split())
    assert "including when the comparison spans every bid" in description
    assert "empty string for the full ranked set" in description
    assert "totals, counts or status breakdowns: those belong to report_generation" in description
    assert "overviews" not in description
