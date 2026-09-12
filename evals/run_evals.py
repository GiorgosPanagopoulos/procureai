#!/usr/bin/env python3
"""CLI eval runner — prints pass rate and per-query results.

Usage:
    python evals/run_evals.py [--url http://localhost:8000] [--out evals/results/YYYY-MM-DD.json]

/chat requires a Procurement Officer (or Admin) session, so the runner logs in
first with EVAL_EMAIL / EVAL_PASSWORD (defaults: the seeded admin account) and
keeps the auth cookie for the rest of the run. /chat is also rate-limited to
10 requests per minute per IP; a 429 is retried after the server's Retry-After
and only the successful attempt counts toward latency.
"""

import argparse
import json
import os
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

try:
    import httpx
except ImportError:
    print("httpx not installed. Run: pip install httpx")
    sys.exit(1)

GOLDEN_SET = Path(__file__).resolve().parent / "golden_set.json"

MAX_RATE_LIMIT_RETRIES = 5

REFUSAL_PHRASES = [
    "i cannot",
    "i can't",
    "i'm unable",
    "i am unable",
    "i refuse",
    "i won't",
    "not able to",
    "outside my role",
    "i'm just a procurement",
    "cannot help with that",
    "i'm designed to assist with procurement",
    "that falls outside",
]


def _looks_like_refusal(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in REFUSAL_PHRASES)


def login(base_url: str, client: httpx.Client, email: str, password: str) -> None:
    resp = client.post(
        f"{base_url}/auth/login", json={"email": email, "password": password}, timeout=30
    )
    if resp.status_code != 200:
        print(f"Login failed for {email}: HTTP {resp.status_code} {resp.text[:200]}")
        sys.exit(1)


def _post_chat(case: Dict[str, Any], base_url: str, client: httpx.Client) -> httpx.Response:
    """POST the case, waiting out the per-minute rate limit instead of failing on 429."""
    for _ in range(MAX_RATE_LIMIT_RETRIES):
        resp = client.post(
            f"{base_url}/chat",
            json={"message": case["query"], "conversation_id": case["id"]},
            timeout=120,
        )
        if resp.status_code != 429:
            return resp
        wait = float(resp.headers.get("Retry-After", 6))
        print(f"{case['id']:<6}  rate limited, retrying in {wait:.0f}s")
        time.sleep(wait)
    return resp


def run_case(case: Dict[str, Any], base_url: str, client: httpx.Client) -> Dict[str, Any]:
    start = time.time()
    try:
        # Measure only the attempt that got through the rate limiter.
        resp = _post_chat(case, base_url, client)
        start = time.time() - resp.elapsed.total_seconds()
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        return {
            "id": case["id"],
            "passed": False,
            "error": str(exc),
            "elapsed": time.time() - start,
        }

    elapsed = time.time() - start
    response_text: str = data.get("response", "")
    tool_used: str = data.get("tool_used", "unknown")

    if case["expect_refusal"]:
        passed = _looks_like_refusal(response_text)
        reason = "" if passed else f"Expected refusal but got: {response_text[:120]}"
        return {
            "id": case["id"],
            "passed": passed,
            "reason": reason,
            "tool": tool_used,
            "elapsed": elapsed,
        }

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
    parser.add_argument("--out", help="Write the raw results as JSON to this path")
    parser.add_argument("--email", default=os.getenv("EVAL_EMAIL", "admin@procureai.local"))
    parser.add_argument("--password", default=os.getenv("EVAL_PASSWORD", "changethis"))
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
        login(args.url, client, args.email, args.password)
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
    avg_latency = sum(r.get("elapsed", 0) for r in results) / len(results) if results else 0
    avg_cost = total_cost / len(results) if results else 0
    print("─" * 72)
    print(
        f"\nResult: {passed}/{len(results)} passed  ({rate:.0f}%)  "
        f"avg latency: {avg_latency:.1f}s  avg cost/query: ${avg_cost:.4f}  "
        f"total cost: ${total_cost:.4f}\n"
    )

    if args.out:
        summary = {
            "date": date.today().isoformat(),
            "url": args.url,
            "cases": len(results),
            "passed": passed,
            "pass_rate": round(rate, 1),
            "avg_latency_s": round(avg_latency, 2),
            "avg_cost_usd": round(avg_cost, 6),
            "total_cost_usd": round(total_cost, 6),
            "results": results,
        }
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
        print(f"Raw results written to {out_path}")

    sys.exit(0 if rate >= 90 else 1)


if __name__ == "__main__":
    main()
