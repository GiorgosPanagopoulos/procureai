from config import settings
from motor.motor_asyncio import AsyncIOMotorClient

mongo_client: AsyncIOMotorClient = AsyncIOMotorClient(settings.MONGODB_URI)
db = mongo_client.procureai
