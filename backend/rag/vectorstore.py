from chromadb import Client as ChromaClient
from chromadb.config import Settings as ChromaSettings
from config import settings
from utils.lazy import _lazy_proxy


def _create_chroma_client():
    return ChromaClient(
        settings=ChromaSettings(persist_directory=settings.CHROMA_PATH, is_persistent=True)
    )


def _create_chroma_collection():
    return chroma_client.create_collection(name="procureai_documents", get_or_create=True)


chroma_client = _lazy_proxy(_create_chroma_client)
chroma_collection = _lazy_proxy(_create_chroma_collection)
