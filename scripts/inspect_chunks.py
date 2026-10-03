#!/usr/bin/env python3
"""Sample 20 random chunks from the Atlas vector store and show the top-3 most similar
golden-set queries for each, using cosine similarity over OpenAI embeddings.

Usage:
    python scripts/inspect_chunks.py [--n 20]
"""

import argparse
import json
import os
import random
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

from dotenv import load_dotenv  # noqa: E402
from pymongo import MongoClient  # noqa: E402

load_dotenv(_ROOT / "backend" / ".env")

try:
    import numpy as np
    from openai import OpenAI
except ImportError as exc:
    print(f"Missing dependency: {exc}. Run: pip install openai numpy")
    sys.exit(1)

GOLDEN_SET_PATH = _ROOT / "evals" / "golden_set.json"


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.array(a, dtype=float)
    vb = np.array(b, dtype=float)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom > 0 else 0.0


def embed(text: str, client: OpenAI) -> list[float]:
    return (
        client.embeddings.create(model="text-embedding-3-small", input=text[:8191])
        .data[0]
        .embedding
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=20, help="Number of chunks to sample")
    parser.add_argument("--uri", default=os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
    parser.add_argument("--collection", default=os.getenv("VECTOR_COLLECTION", "document_chunks"))
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not set — set it in .env or environment")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    with open(GOLDEN_SET_PATH) as f:
        golden: list[dict] = json.load(f)
    queries = [q["query"] for q in golden]

    mongo = MongoClient(args.uri)
    rows = list(mongo.procureai[args.collection].find({}, {"embedding": 0}))
    mongo.close()
    all_ids = [str(r["_id"]) for r in rows]
    all_docs = [r.get("text", "") for r in rows]
    all_metas = rows

    if not all_ids:
        print("Vector store is empty — ingest PDFs first.")
        sys.exit(1)

    n = min(args.n, len(all_ids))
    indices = random.sample(range(len(all_ids)), n)

    print(f"\nEmbedding {len(queries)} golden queries …")
    query_embeddings = [embed(q, client) for q in queries]

    print(f"Sampling {n} / {len(all_ids)} chunks …\n")
    print(
        f"| {'Chunk ID':<28} | {'Source':<22} | {'Preview (80 chars)':<82} | Top-3 similar queries |"
    )
    print("|" + "-" * 30 + "|" + "-" * 24 + "|" + "-" * 84 + "|" + "-" * 55 + "|")

    for idx in indices:
        chunk_id = all_ids[idx]
        source = all_metas[idx].get("source", "unknown") if all_metas else "unknown"
        text = all_docs[idx] if all_docs else ""
        preview = text[:80].replace("|", "\\|").replace("\n", " ")

        chunk_emb = embed(text, client)
        sims = [(cosine_similarity(chunk_emb, qe), q) for qe, q in zip(query_embeddings, queries)]
        top3 = sorted(sims, reverse=True)[:3]
        top3_str = " / ".join(q[:30] for _, q in top3)

        print(f"| {chunk_id[:28]:<28} | {source[:22]:<22} | {preview:<82} | {top3_str:<53} |")

    print()


if __name__ == "__main__":
    main()
