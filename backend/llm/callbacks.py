from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from llm.pricing import _current_usage


class _UsageCallback(BaseCallbackHandler):
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        accum = _current_usage.get()
        if accum is None:
            return
        for gens in response.generations:
            for gen in gens:
                msg = getattr(gen, "message", None)
                if msg is None:
                    continue
                meta = getattr(msg, "usage_metadata", None) or {}
                accum.input_tokens += meta.get("input_tokens", 0)
                accum.output_tokens += meta.get("output_tokens", 0)

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        accum = _current_usage.get()
        if accum:
            accum.tool_calls += 1
