from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from models import Supplier, Bid
import os
from typing import List

app = FastAPI(title="ProcureAI API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB client
mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(mongodb_url)
db = client.procureai

@app.get("/")
async def root():
    return {"message": "ProcureAI API"}

@app.get("/suppliers", response_model=List[Supplier])
async def get_suppliers():
    suppliers = []
    async for supplier in db.suppliers.find():
        suppliers.append(Supplier(**supplier))
    return suppliers

@app.get("/bids", response_model=List[Bid])
async def get_bids():
    bids = []
    async for bid in db.bids.find():
        bids.append(Bid(**bid))
    return bids

@app.post("/chat")
async def chat(message: str):
    # Placeholder for chat endpoint
    return {"response": f"Echo: {message}"}

@app.post("/upload")
async def upload_file():
    # Placeholder for file upload
    return {"message": "File uploaded successfully"}

@app.get("/reports")
async def get_reports():
    # Placeholder for reports
    return {"reports": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)