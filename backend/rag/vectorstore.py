from typing import Any, Dict, List

from config import settings
from langchain_core.embeddings import Embeddings
from langchain_mongodb import MongoDBAtlasVectorSearch
from pymongo import MongoClient, ReplaceOne
from utils.lazy import _lazy_proxy

from rag.embeddings import embed_text

# Chunk documents in the collection look like
#   {_id, text, embedding, user_id, source, chunk}
# with metadata as top-level fields, which is the layout MongoDBAtlasVectorSearch
# reads and what the filter fields in rag/atlas_vector_index.json point at.
TEXT_KEY = "text"
EMBEDDING_KEY = "embedding"


class _OpenAIEmbeddings(Embeddings):
    """Embeds with the same model as ingestion (rag.embeddings.embed_text)."""

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [embed_text(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return embed_text(text)


def _create_vector_client():
    # Sync PyMongo client: LangChain's vector store does not take Motor, and every
    # call into it already runs off the event loop via asyncio.to_thread.
    return MongoClient(settings.MONGODB_URI)


def _create_vector_store():
    return MongoDBAtlasVectorSearch(
        collection=vector_client.procureai[settings.VECTOR_COLLECTION],
        embedding=_OpenAIEmbeddings(),
        index_name=settings.VECTOR_INDEX_NAME,
        text_key=TEXT_KEY,
        embedding_key=EMBEDDING_KEY,
        relevance_score_fn="cosine",
        # The index is created once from rag/atlas_vector_index.json (README step 7),
        # not on every cold start.
        auto_create_index=False,
    )


vector_client = _lazy_proxy(_create_vector_client)
vector_store = _lazy_proxy(_create_vector_store)


def upsert_chunks(
    ids: List[str],
    texts: List[str],
    embeddings: List[List[float]],
    metadatas: List[Dict[str, Any]],
) -> None:
    """Store pre-computed chunks, replacing any existing chunk with the same id."""
    ops = [
        ReplaceOne(
            {"_id": chunk_id},
            {"_id": chunk_id, TEXT_KEY: text, EMBEDDING_KEY: embedding, **metadata},
            upsert=True,
        )
        for chunk_id, text, embedding, metadata in zip(ids, texts, embeddings, metadatas)
    ]
    if ops:
        vector_store.collection.bulk_write(ops, ordered=False)


def delete_chunks(query: Dict[str, Any]) -> int:
    return vector_store.collection.delete_many(query).deleted_count


def count_chunks() -> int:
    return vector_store.collection.count_documents({})
