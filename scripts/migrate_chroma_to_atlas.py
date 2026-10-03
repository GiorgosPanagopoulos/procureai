#!/usr/bin/env python3
"""Copy every chunk from the local ChromaDB store into the Atlas document_chunks collection.

One-off migration for the move from ChromaDB to MongoDB Atlas Vector Search. Each
chunk keeps its text, its stored embedding (nothing is re-embedded, so no OpenAI
calls) and all of its metadata (user_id, source, chunk, category if present).

Documents are upserted with the Chroma id as _id. That id is
"{user_id}_{source}_chunk_{i}", the same one rag/ingest.py generates, so the
migration is safe to re-run and a later re-ingest of the same file replaces
these documents instead of duplicating them.

chromadb is no longer a backend dependency; install it just for this run:
    pip install chromadb

Usage (from the repo root, with the backend venv active):
    python scripts/migrate_chroma_to_atlas.py --dry-run          # read Chroma only
    python scripts/migrate_chroma_to_atlas.py                    # uses MONGODB_URI from backend/.env
    python scripts/migrate_chroma_to_atlas.py --uri 'mongodb+srv://...'

Create the vector index from backend/rag/atlas_vector_index.json in Atlas
before querying; the migration itself does not need it.
"""

import argparse
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"

from dotenv import load_dotenv  # noqa: E402
from pymongo import MongoClient, ReplaceOne  # noqa: E402

load_dotenv(_BACKEND / ".env")

CHROMA_COLLECTION = "procureai_documents"
EMBEDDING_DIMENSIONS = 1536
BATCH_SIZE = 100
# Fields the vector store owns; a metadata key with one of these names would clobber them.
_RESERVED = {"_id", "text", "embedding"}


def _parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--chroma-path", default=str(_BACKEND / "chroma_db"))
    parser.add_argument(
        "--uri",
        default=os.environ.get("MONGODB_URI"),
        help="MongoDB connection string (default: MONGODB_URI from backend/.env)",
    )
    parser.add_argument("--db", default="procureai")
    parser.add_argument(
        "--collection", default=os.environ.get("VECTOR_COLLECTION", "document_chunks")
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="read and validate Chroma, write nothing"
    )
    return parser.parse_args(argv)


def _read_chroma(path: str) -> list[dict]:
    try:
        import chromadb
    except ImportError:
        sys.exit("chromadb is not installed; run `pip install chromadb` for the migration")

    if not Path(path).is_dir():
        sys.exit(f"No Chroma store at {path}")
    collection = chromadb.PersistentClient(path=path).get_collection(CHROMA_COLLECTION)
    result = collection.get(include=["documents", "embeddings", "metadatas"])

    docs = []
    for chunk_id, text, embedding, metadata in zip(
        result["ids"], result["documents"], result["embeddings"], result["metadatas"]
    ):
        # Chroma returns metadata keys in no fixed order; MongoDB treats a reordered
        # document as modified, so sort them to keep re-runs a true no-op.
        metadata = dict(sorted((metadata or {}).items()))
        clashes = _RESERVED & metadata.keys()
        if clashes:
            sys.exit(f"Chunk {chunk_id} has metadata keys reserved by the vector store: {clashes}")
        docs.append(
            {
                "_id": chunk_id,
                "text": text,
                "embedding": [float(x) for x in embedding],
                **metadata,
            }
        )

    if len(docs) != collection.count():
        sys.exit(f"Chroma get() returned {len(docs)} chunks but count() is {collection.count()}")
    return docs


def _validate(docs: list[dict]) -> list[str]:
    problems = []
    for doc in docs:
        if len(doc["embedding"]) != EMBEDDING_DIMENSIONS:
            problems.append(
                f"{doc['_id']}: embedding has {len(doc['embedding'])} dims, "
                f"index expects {EMBEDDING_DIMENSIONS}"
            )
        if not doc.get("text"):
            problems.append(f"{doc['_id']}: empty text")
        if not doc.get("user_id"):
            problems.append(f"{doc['_id']}: missing user_id (tenant filter would never match)")
    return problems


def main(argv=None) -> int:
    args = _parse_args(argv)

    docs = _read_chroma(args.chroma_path)
    print(f"Chroma   {args.chroma_path}: {len(docs)} chunks")
    problems = _validate(docs)
    if problems:
        print("Refusing to migrate:", *problems, sep="\n  ", file=sys.stderr)
        return 1

    tenants: dict[str, int] = {}
    for doc in docs:
        tenants[doc["user_id"]] = tenants.get(doc["user_id"], 0) + 1
    for user_id, n in sorted(tenants.items()):
        print(f"         user_id={user_id}: {n} chunks")

    if args.dry_run:
        print("Dry run: nothing written.")
        return 0
    if not args.uri:
        print("No MongoDB URI: pass --uri or set MONGODB_URI in backend/.env", file=sys.stderr)
        return 1

    client: MongoClient = MongoClient(args.uri)
    try:
        target = client[args.db][args.collection]
        before = target.count_documents({})
        print(f"Atlas    {args.db}.{args.collection}: {before} documents before")

        upserted = modified = 0
        for start in range(0, len(docs), BATCH_SIZE):
            batch = docs[start : start + BATCH_SIZE]
            result = target.bulk_write(
                [ReplaceOne({"_id": d["_id"]}, d, upsert=True) for d in batch], ordered=False
            )
            upserted += result.upserted_count
            modified += result.modified_count

        after = target.count_documents({})
        print(
            f"Atlas    {args.db}.{args.collection}: {after} documents after "
            f"({upserted} inserted, {modified} updated, "
            f"{len(docs) - upserted - modified} already up to date)"
        )

        ids = [d["_id"] for d in docs]
        found = set(target.distinct("_id", {"_id": {"$in": ids}}))
        missing = [i for i in ids if i not in found]
        if missing:
            print(f"FAILED: {len(missing)} chunks missing in Atlas:", file=sys.stderr)
            for chunk_id in missing:
                print(f"  {chunk_id}", file=sys.stderr)
            return 1
        print(f"Verified: all {len(docs)} Chroma chunks are present in Atlas.")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
