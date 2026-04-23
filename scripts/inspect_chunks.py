#!/usr/bin/env python3
"""Sample 20 random chunks from ChromaDB and show the top-3 most similar
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
sys.path.insert(0, str(_ROOT / "backend"))

from chromadb import Client as ChromaClient          # type: ignore
from chromadb.config import Settings as ChromaSettings  # type: ignore

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
    return client.embeddings.create(
        model="text-embedding-3-small", input=text[:8191]
    ).data[0].embedding


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=20, help="Number of chunks to sample")
    parser.add_argument("--chroma-path", default=str(_ROOT / "backend" / "chroma_db"))
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not set — set it in .env or environment")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    with open(GOLDEN_SET_PATH) as f:
        golden: list[dict] = json.load(f)
    queries = [q["query"] for q in golden]

    chroma = ChromaClient(
        settings=ChromaSettings(persist_directory=args.chroma_path, is_persistent=True)
    )
    try:
        col = chroma.get_collection("procureai_documents")
    except Exception:
        print("Collection 'procureai_documents' not found. Ingest PDFs first.")
        sys.exit(1)

    all_data = col.get(include=["documents", "metadatas"])
    all_ids = all_data["ids"]
    all_docs = all_data["documents"]
    all_metas = all_data["metadatas"]

    if not all_ids:
        print("Vector store is empty — ingest PDFs first.")
        sys.exit(1)

    n = min(args.n, len(all_ids))
    indices = random.sample(range(len(all_ids)), n)

    print(f"\nEmbedding {len(queries)} golden queries …")
    query_embeddings = [embed(q, client) for q in queries]

    print(f"Sampling {n} / {len(all_ids)} chunks …\n")
    print(f"| {'Chunk ID':<28} | {'Source':<22} | {'Preview (80 chars)':<82} | Top-3 similar queries |")
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
