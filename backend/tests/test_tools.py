import asyncio
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

# Stub the LLM/embedding stack BEFORE importing agent.tools so no real
# clients or ChromaDB connections are opened during test collection.
sys.modules.setdefault("rag.embeddings", MagicMock())
sys.modules.setdefault("rag.vectorstore", MagicMock())
sys.modules.setdefault("llm.clients", MagicMock())

import agent.tools as tools_module  # noqa: E402
from agent.tools import document_qa  # noqa: E402


def test_document_qa_is_async_tool():
    """Regression: document_qa must be registered as an async LangChain tool."""
    assert asyncio.iscoroutinefunction(document_qa.coroutine)
    assert document_qa.func is None


async def test_document_qa_offloads_blocking_calls_to_thread():
    """Regression: embed_text and chroma_collection.query must go through asyncio.to_thread."""
    from anthropic.types import TextBlock

    fake_usage = SimpleNamespace(
        input_tokens=10,
        output_tokens=5,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )
    fake_response = MagicMock()
    fake_response.content = [TextBlock(text="answer", type="text")]
    fake_response.usage = fake_usage

    # Each call to asyncio.to_thread returns the next value from this list.
    fake_to_thread = AsyncMock(
        side_effect=[
            [0.0] * 4,  # embedding returned for embed_text call
            {  # chroma results returned for chroma_collection.query call
                "documents": [["procurement contract clause"]],
                "metadatas": [[{"source": "contract.pdf"}]],
            },
        ]
    )

    with (
        patch("asyncio.to_thread", new=fake_to_thread),
        patch("agent.tools.get_active_user_id", return_value="test_user_id"),
        patch.object(
            tools_module._raw_anthropic_async.messages,
            "create",
            new=AsyncMock(return_value=fake_response),
        ),
    ):
        await document_qa.ainvoke("test question")

    assert fake_to_thread.call_count >= 2, (
        f"Expected at least 2 asyncio.to_thread calls (embed + query), "
        f"got {fake_to_thread.call_count}"
    )
