#!/usr/bin/env python3
"""Ingest the PDFs in backend/data/pdfs/ into ChromaDB as user_id="system".

The backend only ingests this folder at startup when the vector store is empty,
so PDFs added after the first start (e.g. the N4412_*.pdf law excerpts) are
never picked up and document_qa answers from model knowledge instead of RAG.

Usage (from the repo root, with the backend venv active and backend/.env filled in):
    python scripts/ingest_pdfs.py                 # ingest PDFs not yet in the store
    python scripts/ingest_pdfs.py --force         # re-embed everything, replacing old chunks
    python scripts/ingest_pdfs.py N4412_apeftheias_anathesi.pdf   # only these files

Embedding is an OpenAI call per chunk, so files already present in the store
are skipped unless --force is given.
"""

import argparse
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
_PDF_DIR = _BACKEND / "data" / "pdfs"

# backend/.env may set a relative CHROMA_PATH (./chroma_db); resolve it the way
# `cd backend && uvicorn main:app` does so the script fills the store the app reads.
os.chdir(_BACKEND)
sys.path.insert(0, str(_BACKEND))

from exceptions import DocumentIngestionError  # noqa: E402
from rag.ingest import ingest_pdf_file  # noqa: E402
from rag.vectorstore import chroma_collection  # noqa: E402

SYSTEM_USER = "system"


def _existing_chunk_ids(source: str) -> list[str]:
    result = chroma_collection.get(
        where={"$and": [{"user_id": SYSTEM_USER}, {"source": source}]},
        include=[],
    )
    return list(result.get("ids") or [])


def _parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "files",
        nargs="*",
        help="PDF file names inside backend/data/pdfs/ (default: every *.pdf there)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-ingest files already in the store, replacing their chunks",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    if args.files:
        pdf_paths = [_PDF_DIR / name for name in args.files]
        missing = [p.name for p in pdf_paths if not p.is_file()]
        if missing:
            print(f"Not found in {_PDF_DIR}: {', '.join(missing)}", file=sys.stderr)
            return 1
    else:
        pdf_paths = sorted(_PDF_DIR.glob("*.pdf"))
        if not pdf_paths:
            print(f"No PDFs found in {_PDF_DIR}", file=sys.stderr)
            return 1

    ingested = skipped = failed = 0
    for pdf_path in pdf_paths:
        existing = _existing_chunk_ids(pdf_path.name)
        if existing and not args.force:
            print(f"skip     {pdf_path.name} ({len(existing)} chunks already stored)")
            skipped += 1
            continue
        if existing:
            chroma_collection.delete(ids=existing)
        try:
            result = ingest_pdf_file(pdf_path, user_id=SYSTEM_USER)
        except DocumentIngestionError as exc:
            print(f"FAILED   {pdf_path.name}: {exc.detail}", file=sys.stderr)
            failed += 1
            continue
        verb = "replaced" if existing else "ingested"
        print(f"{verb:<8} {pdf_path.name} ({result['chunks']} chunks)")
        ingested += 1

    print(
        f"\n{ingested} ingested, {skipped} skipped, {failed} failed; "
        f"store now holds {chroma_collection.count()} chunks"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
