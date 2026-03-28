from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from models import Supplier, Bid
import os
from typing import List, Dict
from pathlib import Path
from io import BytesIO
from pypdf import PdfReader
from pydantic import BaseModel
import json

# Chromadb for vector store
from chromadb import Client as ChromaClient
from chromadb.config import Settings

# OpenAI for embeddings and LLM
from openai import OpenAI

app = FastAPI(title="ProcureAI API", version="2.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB client
mongodb_url = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
client = AsyncIOMotorClient(mongodb_url)
db = client.procureai

class ChatRequest(BaseModel):
    message: str

# OpenAI and Chroma setup
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY is not set. Embeddings/LLM calls will fail until set.")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

CHROMA_DIR = Path(__file__).resolve().parent / "chroma_db"
CHROMA_DIR.mkdir(exist_ok=True)

# Initialize Chroma client
chroma_client = ChromaClient(settings=Settings(persist_directory=str(CHROMA_DIR), is_persistent=True))
chroma_collection = chroma_client.create_collection(name="procureai_documents", get_or_create=True)


def split_text_chunks(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Simple recursive character text splitter: split by sentences/paragraphs."""
    if not text.strip():
        return []
    
    # Split by double newlines first (paragraphs)
    paragraphs = text.split('\n\n')
    
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        # Split by single newlines if paragraph is too large
        lines = para.split('\n')
        for line in lines:
            if len(current_chunk) + len(line) + 1 <= chunk_size:
                current_chunk += line + "\n"
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = line + "\n"
        
        if current_chunk.strip() and len(current_chunk) > chunk_size // 2:
            chunks.append(current_chunk.strip())
            current_chunk = ""
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return [c for c in chunks if len(c.strip()) > 0]


def embed_text(text: str) -> List[float]:
    """Generate embedding using OpenAI API."""
    if not text.strip():
        return [0.0] * 1536
    
    try:
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text[:8191]  # truncate to API limit
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error embedding text: {e}")
        return [0.0] * 1536


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF."""
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text)
        return "\n".join(pages).strip()
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        return ""


def ingest_text(source: str, text: str) -> int:
    """Split text into chunks, embed, and store in Chroma."""
    if not text.strip():
        return 0

    chunks = split_text_chunks(text, chunk_size=500, overlap=50)
    if not chunks:
        return 0

    # Embed and add to chromadb
    ids = []
    documents = []
    embeddings_list = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        chunk_id = f"{source}_chunk_{i}"
        ids.append(chunk_id)
        documents.append(chunk)
        embedding = embed_text(chunk)
        embeddings_list.append(embedding)
        metadatas.append({"source": source, "chunk": i})

    if ids:
        try:
            chroma_collection.add(
                ids=ids,
                metadatas=metadatas,
                documents=documents,
                embeddings=embeddings_list,
            )
        except Exception as e:
            print(f"Error adding documents to Chroma: {e}")

    return len(chunks)


def ingest_pdf(source: str, pdf_bytes: bytes) -> int:
    """Extract PDF text and ingest."""
    text = extract_text_from_pdf(pdf_bytes)
    return ingest_text(source, text)


def ingest_pdf_file(path: Path) -> Dict[str, str]:
    """Ingest a PDF file."""
    try:
        with path.open("rb") as f:
            pdf_bytes = f.read()
        chunks = ingest_pdf(path.name, pdf_bytes)
        return {"file": path.name, "chunks": chunks}
    except Exception as e:
        print(f"Error ingesting PDF file {path.name}: {e}")
        return {"file": path.name, "chunks": 0}


def is_vectorstore_empty() -> bool:
    try:
        count = chroma_collection.count()
        return count == 0
    except Exception:
        return True


def document_qa(question: str, k: int = 4) -> Dict:
    """Answer question using document Q&A."""
    if not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Embed the question
    try:
        query_embedding = embed_text(question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error embedding query: {e}")

    # Search in Chroma
    try:
        results = chroma_collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "distances", "metadatas"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching vector store: {e}")

    # Construct context
    context_docs = []
    source_refs = []
    
    if results and "documents" in results and results["documents"]:
        for doc_list in results["documents"]:
            context_docs.extend(doc_list)

        if "metadatas" in results and results["metadatas"]:
            for meta_list in results["metadatas"]:
                for meta in meta_list:
                    source = meta.get("source", "unknown")
                    if source not in source_refs:
                        source_refs.append(source)

    # Build prompt and get LLM response
    context = "\n".join(context_docs) if context_docs else "No relevant documents found."
    prompt = f"""You are a helpful assistant answering questions about procurement documents.
Use the following context to answer the question.

Context:
{context}

Question: {question}

Answer:"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        answer = response.choices[0].message.content
    except Exception as e:
        answer = f"Error generating answer: {e}"

    return {
        "question": question,
        "answer": answer,
        "sources": source_refs,
    }


document_qa_tool = {
    "name": "document_qa",
    "func": document_qa,
    "description": "Answer questions over ingested PDF documents (ChromaDB vector store). Returns answer and source references.",
}


# ============= AGENT TOOLS =============

async def bid_comparison_tool(category: str = "", max_results: int = 5) -> str:
    """Compare bids by price, delivery, and terms. Returns ranked results."""
    try:
        bids_cursor = db.bids.find({}).limit(max_results)
        bids_list = await bids_cursor.to_list(length=max_results)
        
        if not bids_list:
            return "No bids found in the system."
        
        # Sort by total_price (ascending) with delivery_days as tiebreaker
        sorted_bids = sorted(bids_list, key=lambda x: (x.get("total_price", 0), x.get("delivery_days", 0)))
        
        result_text = "Bid Comparison Results:\n"
        for i, bid in enumerate(sorted_bids, 1):
            result_text += f"\n{i}. Supplier ID: {bid.get('supplier_id', 'N/A')}\n"
            result_text += f"   Total Price: ${bid.get('total_price', 0):.2f}\n"
            result_text += f"   Delivery Days: {bid.get('delivery_days', 'N/A')}\n"
            result_text += f"   Terms: {bid.get('terms', 'N/A')}\n"
            result_text += f"   Status: {bid.get('status', 'pending')}\n"
        
        return result_text
    except Exception as e:
        return f"Error comparing bids: {e}"


async def report_generation_tool(report_type: str = "procurement") -> str:
    """Generate structured procurement summary from MongoDB data."""
    try:
        suppliers_cursor = db.suppliers.find({})
        suppliers_list = await suppliers_cursor.to_list(length=None)
        
        bids_cursor = db.bids.find({})
        bids_list = await bids_cursor.to_list(length=None)
        
        report = f"""
PROCUREMENT REPORT - {report_type.upper()}
====================================

SUPPLIERS SUMMARY:
- Total Suppliers: {len(suppliers_list)}
"""
        
        if suppliers_list:
            avg_rating = sum(s.get("rating", 0) for s in suppliers_list) / len(suppliers_list)
            report += f"- Average Supplier Rating: {avg_rating:.2f}/5.0\n"
            
            categories = set(s.get("category", "unknown") for s in suppliers_list)
            report += f"- Categories: {', '.join(categories)}\n"
        
        report += f"""
BIDS SUMMARY:
- Total Bids: {len(bids_list)}
"""
        
        if bids_list:
            total_value = sum(b.get("total_price", 0) for b in bids_list)
            avg_delivery = sum(b.get("delivery_days", 0) for b in bids_list) / len(bids_list)
            report += f"- Total Bid Value: ${total_value:,.2f}\n"
            report += f"- Average Delivery Time: {avg_delivery:.1f} days\n"
            
            statuses = {}
            for bid in bids_list:
                status = bid.get("status", "pending")
                statuses[status] = statuses.get(status, 0) + 1
            report += f"- Bid Status Distribution: {dict(statuses)}\n"
        
        return report
    except Exception as e:
        return f"Error generating report: {e}"


async def supplier_lookup_tool(category: str = "", min_rating: float = 0.0) -> str:
    """Query suppliers with filtering and recommendations."""
    try:
        query = {}
        if category:
            query["category"] = {"$regex": category, "$options": "i"}
        if min_rating > 0:
            query["rating"] = {"$gte": min_rating}
        
        suppliers_cursor = db.suppliers.find(query).limit(10)
        suppliers_list = await suppliers_cursor.to_list(length=10)
        
        if not suppliers_list:
            return f"No suppliers found matching criteria: category={category}, rating>={min_rating}"
        
        result_text = f"Supplier Lookup Results ({len(suppliers_list)} found):\n"
        
        # Sort by rating descending
        sorted_suppliers = sorted(suppliers_list, key=lambda x: x.get("rating", 0), reverse=True)
        
        for i, supplier in enumerate(sorted_suppliers, 1):
            result_text += f"\n{i}. {supplier.get('name', 'N/A')}\n"
            result_text += f"   Category: {supplier.get('category', 'N/A')}\n"
            result_text += f"   Rating: {supplier.get('rating', 'N/A')}/5.0\n"
            result_text += f"   Contact: {supplier.get('contact', 'N/A')}\n"
        
        return result_text
    except Exception as e:
        return f"Error looking up suppliers: {e}"


async def router_agent(user_input: str) -> Dict:
    """
    ReAct agent with intent routing: analyzes user input and selects appropriate tool(s).
    Returns tool results via OpenAI LLM orchestration.
    """
    if not user_input.strip():
        return {"response": "Please provide a query.", "tool_used": "none"}
    
    # Intent classification via LLM
    intent_prompt = f"""Analyze the user's procurement query and identify the primary intent.
Classify into one of these categories:
1. "document_qa" - Questions about procurement documents/contracts/terms
2. "bid_comparison" - Comparing bids, prices, delivery times
3. "supplier_lookup" - Finding suppliers, checking ratings
4. "report" - Generating summaries or reports
5. "multi_tool" - Requires multiple tools

User Query: {user_input}

Respond with ONLY the classification (e.g., "bid_comparison") and any tool parameters in JSON format.
Format: {{"intent": "...", "params": {{...}}}}"""
    
    try:
        intent_response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": intent_prompt}],
            temperature=0,
        )
        intent_text = intent_response.choices[0].message.content.strip()
        
        # Parse intent
        try:
            intent_data = json.loads(intent_text)
        except json.JSONDecodeError:
            # Fallback parsing
            intent_data = {"intent": "multi_tool", "params": {}}
        
        intent = intent_data.get("intent", "multi_tool")
        params = intent_data.get("params", {})
        
        # Execute tool(s) based on intent
        tool_result = ""
        
        if intent == "document_qa":
            tool_result = document_qa(user_input, k=4)
            tool_used = "document_qa"
        elif intent == "bid_comparison":
            tool_result = await bid_comparison_tool(
                category=params.get("category", ""),
                max_results=params.get("max_results", 5)
            )
            tool_used = "bid_comparison"
        elif intent == "supplier_lookup":
            tool_result = await supplier_lookup_tool(
                category=params.get("category", ""),
                min_rating=params.get("min_rating", 0.0)
            )
            tool_used = "supplier_lookup"
        elif intent == "report":
            tool_result = await report_generation_tool(report_type=params.get("type", "procurement"))
            tool_used = "report_generation"
        else:  # multi_tool
            # Run multiple relevant tools
            doc_qa_result = document_qa(user_input, k=3)
            bid_result = await bid_comparison_tool(max_results=3)
            supplier_result = await supplier_lookup_tool(max_results=3)
            
            tool_result = f"""
Document Search: {doc_qa_result.get('answer', 'N/A')}

Top Bids:
{bid_result}

Top Suppliers:
{supplier_result}
"""
            tool_used = "multi_tool"
        
        # Generate final response via LLM
        final_prompt = f"""You are a helpful procurement assistant. Based on the following query and tool results, provide a clear, structured answer.

User Query: {user_input}

Tool Results:
{tool_result}

Provide a concise, actionable response that directly addresses the user's query."""
        
        final_response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": final_prompt}],
            temperature=0,
        )
        
        answer = final_response.choices[0].message.content
        
        return {
            "response": answer,
            "tool_used": tool_used,
            "raw_results": tool_result,
        }
    
    except Exception as e:
        return {"response": f"Error processing query: {e}", "tool_used": "error"}


# ============= END AGENT TOOLS =============

@app.on_event("startup")
async def startup_event():
    """Ingest mock PDFs on startup if vector store is empty."""
    if is_vectorstore_empty():
        pdf_dir = Path(__file__).resolve().parent / "data" / "pdfs"
        if pdf_dir.exists():
            for pdf_path in pdf_dir.glob("*.pdf"):
                try:
                    ingested = ingest_pdf_file(pdf_path)
                    print(f"Ingested {ingested['chunks']} chunks from {ingested['file']}")
                except Exception as exc:
                    print(f"Failed to ingest {pdf_path.name}: {exc}")

@app.get("/")
async def root():
    return {"message": "ProcureAI API (RAG pipeline ready)"}

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
async def chat(payload: ChatRequest):
    """Chat endpoint powered by ReAct agent."""
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        result = await router_agent(payload.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {e}")

    if not result or not result.get("response"):
        raise HTTPException(status_code=500, detail="Agent returned empty response")

    return {"response": result["response"], "tool_used": result.get("tool_used", "unknown")}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")

    content = await file.read()
    chunks = ingest_pdf(file.filename or "uploaded.pdf", content)

    if chunks == 0:
        raise HTTPException(status_code=400, detail="PDF had no extractable text")

    return {"message": "PDF ingested successfully", "chunks": chunks, "file": file.filename}

@app.post("/doc_qa")
async def qna(question: str, k: int = 4):
    answer = document_qa(question, k=k)
    return answer

@app.get("/reports")
async def get_reports():
    return {"reports": []}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
