from chromadb import Client as ChromaClient
from chromadb.config import Settings as ChromaSettings
from config import settings

chroma_client = ChromaClient(
    settings=ChromaSettings(persist_directory=settings.CHROMA_PATH, is_persistent=True)
)
chroma_collection = chroma_client.create_collection(name="procureai_documents", get_or_create=True)
