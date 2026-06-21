from contextvars import ContextVar
from typing import Any, Dict, Optional

MODEL_NAME = "claude-sonnet-4-6"
COST_PER_INPUT_TOKEN = 3.00 / 1_000_000
COST_PER_OUTPUT_TOKEN = 15.00 / 1_000_000
COST_PER_CACHE_WRITE = 3.75 / 1_000_000
COST_PER_CACHE_READ = 0.30 / 1_000_000


def _compute_cost(
    input_tokens: int, output_tokens: int, cache_creation: int = 0, cache_read: int = 0
) -> float:
    return (
        input_tokens * COST_PER_INPUT_TOKEN
        + output_tokens * COST_PER_OUTPUT_TOKEN
        + cache_creation * COST_PER_CACHE_WRITE
        + cache_read * COST_PER_CACHE_READ
    )


class _UsageAccum:
    __slots__ = (
        "input_tokens",
        "output_tokens",
        "cache_creation",
        "cache_read",
        "tool_calls",
    )

    def __init__(self) -> None:
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_creation = 0
        self.cache_read = 0
        self.tool_calls = 0

    def add_anthropic(self, usage: Any) -> None:
        self.input_tokens += getattr(usage, "input_tokens", 0)
        self.output_tokens += getattr(usage, "output_tokens", 0)
        self.cache_creation += getattr(usage, "cache_creation_input_tokens", 0)
        self.cache_read += getattr(usage, "cache_read_input_tokens", 0)

    def to_dict(self) -> Dict:
        cost = _compute_cost(
            self.input_tokens, self.output_tokens, self.cache_creation, self.cache_read
        )
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_creation_tokens": self.cache_creation,
            "cache_read_tokens": self.cache_read,
            "cost_usd": round(cost, 6),
            "tool_calls_count": self.tool_calls,
        }


_current_usage: ContextVar[Optional[_UsageAccum]] = ContextVar("current_usage", default=None)
