from datetime import datetime, timezone
from typing import Dict, List

import sentry_sdk
import structlog
from db import db
from exceptions import AgentExecutionError
from langchain_classic.agents import AgentExecutor, create_react_agent
from llm.clients import claude_llm
from llm.pricing import MODEL_NAME, _current_usage, _UsageAccum
from security.pii import redact_pii

from agent.prompt import react_prompt
from agent.tools import bid_comparison, document_qa, report_generation, supplier_lookup

log = structlog.get_logger()

lc_tools = [document_qa, bid_comparison, supplier_lookup, report_generation]
agent = create_react_agent(llm=claude_llm, tools=lc_tools, prompt=react_prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=lc_tools,
    return_intermediate_steps=True,
    handle_parsing_errors=True,
    max_iterations=5,
    verbose=True,
)


def _build_trace(steps: List) -> List[Dict]:
    trace = []
    for action, observation in steps:
        log_text: str = action.log or ""
        thought = ""
        if "Thought:" in log_text:
            start = log_text.find("Thought:") + len("Thought:")
            end = log_text.find("\nAction:")
            thought = (log_text[start:end] if end > start else log_text[start:]).strip()
        if thought:
            trace.append({"type": "thought", "content": thought})
        trace.append({"type": "tool_call", "tool": action.tool, "input": str(action.tool_input)})
        trace.append({"type": "observation", "content": str(observation)[:500]})
    return trace


async def run_agent(user_input: str, conversation_id: str) -> Dict:
    if not user_input.strip():
        return {
            "response": "Please provide a query.",
            "tool_used": "none",
            "conversation_id": conversation_id,
            "trace": [],
            "usage": {},
        }

    clean_input, redaction_count = redact_pii(user_input)
    if redaction_count:
        log.info("pii_redacted", count=redaction_count, conversation_id=conversation_id)

    accum = _UsageAccum()
    token = _current_usage.set(accum)
    sentry_sdk.add_breadcrumb(category="agent", message="Agent invocation start", level="info")
    try:
        with sentry_sdk.start_span(op="llm.invoke", description="Claude API call") as _span:
            _span.set_data("model", MODEL_NAME)
            _span.set_data("tool", "agent_executor")
            result = await agent_executor.ainvoke(
                {"input": clean_input},
                config={
                    "metadata": {
                        "conversation_id": conversation_id,
                        "user_input_length": len(clean_input),
                    },
                    "run_name": "procureai_agent",
                },
            )
            _span.set_data("tool_calls", len(result.get("intermediate_steps", [])))
    except Exception as exc:
        sentry_sdk.set_context(
            "agent_input",
            {
                "query": clean_input[:500],
                "conversation_id": conversation_id,
            },
        )
        sentry_sdk.capture_exception(exc)
        log.error("agent_error", error=str(exc), conversation_id=conversation_id)
        raise AgentExecutionError(detail=f"Agent failed: {exc}")
    finally:
        _current_usage.reset(token)

    steps = result.get("intermediate_steps", [])
    tool_used = steps[0][0].tool if steps else "unknown"
    if steps:
        sentry_sdk.add_breadcrumb(
            category="agent", message=f"Agent selected tool: {tool_used}", level="info"
        )
    sentry_sdk.add_breadcrumb(
        category="agent", message="Response generation complete", level="info"
    )
    trace = _build_trace(steps)
    usage = accum.to_dict()

    await db.usage.insert_one(
        {
            "conversation_id": conversation_id,
            "timestamp": datetime.now(timezone.utc),
            "model": MODEL_NAME,
            **usage,
        }
    )
    await db.conversations.update_one(
        {"conversation_id": conversation_id},
        {
            "$set": {
                "conversation_id": conversation_id,
                "trace": trace,
                "query": clean_input,
                "updated_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )
    log.info(
        "agent_done",
        conversation_id=conversation_id,
        tool=tool_used,
        input_tok=usage["input_tokens"],
        output_tok=usage["output_tokens"],
        cost=usage["cost_usd"],
    )
    return {
        "response": result["output"],
        "tool_used": tool_used,
        "conversation_id": conversation_id,
        "trace": trace,
        "usage": usage,
    }
