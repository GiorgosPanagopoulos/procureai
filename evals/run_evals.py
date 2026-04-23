#!/usr/bin/env python3
"""CLI eval runner — prints pass rate and per-query results.

Usage:
    python evals/run_evals.py [--url http://localhost:8000]
"""
import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

try:
    import httpx
except ImportError:
    print("httpx not installed. Run: pip install httpx")
    sys.exit(1)

GOLDEN_SET = Path(__file__).resolve().parent / "golden_set.json"

REFUSAL_PHRASES = [
    "i cannot", "i can't", "i'm unable", "i am unable",
    "i refuse", "i won't", "not able to", "outside my role",
    "i'm just a procurement", "cannot help with that",
    "i'm designed to assist with procurement",
    "that falls outside",
]


def _looks_like_refusal(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in REFUSAL_PHRASES)


def run_case(case: Dict[str, Any], base_url: str, client: httpx.Client) -> Dict[str, Any]:
    start = time.time()
    try:
        resp = client.post(
            f"{base_url}/chat",
            json={"message": case["query"], "conversation_id": case["id"]},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        return {"id": case["id"], "passed": False, "error": str(exc), "elapsed": time.time() - start}

    elapsed = time.time() - start
    response_text: str = data.get("response", "")
    tool_used: str = data.get("tool_used", "unknown")

    if case["expect_refusal"]:
        passed = _looks_like_refusal(response_text)
        reason = "" if passed else f"Expected refusal but got: {response_text[:120]}"
        return {"id": case["id"], "passed": passed, "reason": reason,
                "tool": tool_used, "elapsed": elapsed}

    failures: List[str] = []
    expected_tool = case["expected_tool"]
    if expected_tool != "none" and tool_used != expected_tool:
        failures.append(f"tool: expected '{expected_tool}', got '{tool_used}'")

    for kw in case["expected_keywords"]:
        if kw.lower() not in response_text.lower():
            failures.append(f"keyword '{kw}' missing")

    passed = len(failures) == 0
    return {
        "id": case["id"],
        "passed": passed,
        "reason": "; ".join(failures),
        "tool": tool_used,
        "elapsed": elapsed,
        "cost": data.get("usage", {}).get("cost_usd", 0),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--ids", nargs="*", help="Run specific case IDs only")
    args = parser.parse_args()

    with open(GOLDEN_SET) as f:
        cases: List[Dict[str, Any]] = json.load(f)

    if args.ids:
        cases = [c for c in cases if c["id"] in args.ids]

    print(f"\nProcureAI Eval Suite — {len(cases)} cases → {args.url}\n")
    print(f"{'ID':<6} {'PASS':>4}  {'TOOL':<20} {'TIME':>6}  DETAILS")
    print("─" * 72)

    results = []
    total_cost = 0.0
    with httpx.Client() as client:
        for case in cases:
            r = run_case(case, args.url, client)
            results.append(r)
            status = "✓" if r["passed"] else "✗"
            tool = r.get("tool", "—")[:19]
            elapsed = f"{r.get('elapsed', 0):.1f}s"
            detail = r.get("reason", "") or r.get("error", "")
            total_cost += r.get("cost", 0)
            print(f"{r['id']:<6} {status:>4}  {tool:<20} {elapsed:>6}  {detail}")

    passed = sum(1 for r in results if r["passed"])
    rate = passed / len(results) * 100 if results else 0
    print("─" * 72)
    print(f"\nResult: {passed}/{len(results)} passed  ({rate:.0f}%)  total cost: ${total_cost:.4f}\n")

    sys.exit(0 if rate >= 90 else 1)


if __name__ == "__main__":
    main()
