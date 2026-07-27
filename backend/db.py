from config import settings
from motor.motor_asyncio import AsyncIOMotorClient
from utils.lazy import _lazy_proxy


def _create_mongo_client():
    return AsyncIOMotorClient(settings.MONGODB_URI)


def _get_db():
    return mongo_client.procureai


mongo_client = _lazy_proxy(_create_mongo_client)
db = _lazy_proxy(_get_db)
