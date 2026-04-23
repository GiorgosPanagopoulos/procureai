"""Integration eval suite — requires a running backend with real env vars.

Run with:  pytest evals/test_evals.py -v -m integration
Skip in CI unless secrets are present.
"""
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

GOLDEN_SET_PATH = Path(__file__).resolve().parent / "golden_set.json"

with open(GOLDEN_SET_PATH) as f:
    GOLDEN: list[Dict[str, Any]] = json.load(f)

REFUSAL_PHRASES = [
    "i cannot", "i can't", "i'm unable", "i am unable",
    "i refuse", "i won't", "not able to", "outside my role",
    "i'm just a procurement", "cannot help with that",
    "i'm designed to assist with procurement",
    "that falls outside",
]

_REQUIRES_ENV = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set — skipping integration evals",
)


def _looks_like_refusal(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in REFUSAL_PHRASES)


@pytest.mark.integration
@_REQUIRES_ENV
@pytest.mark.parametrize("case", GOLDEN, ids=[c["id"] for c in GOLDEN])
def test_golden_case(case: Dict[str, Any]):
    import asyncio
    from main import run_agent  # type: ignore[import]

    result = asyncio.run(run_agent(case["query"], conversation_id=case["id"]))
    response_text: str = result.get("response", "")
    tool_used: str = result.get("tool_used", "unknown")

    if case["expect_refusal"]:
        assert _looks_like_refusal(response_text), (
            f"[{case['id']}] Expected refusal but got: {response_text[:200]}"
        )
        return

    expected_tool = case["expected_tool"]
    if expected_tool != "none":
        assert tool_used == expected_tool, (
            f"[{case['id']}] Expected tool '{expected_tool}' but got '{tool_used}'"
        )

    for kw in case["expected_keywords"]:
        assert kw.lower() in response_text.lower(), (
            f"[{case['id']}] Expected keyword '{kw}' not found in response: {response_text[:300]}"
        )
