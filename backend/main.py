from contextlib import asynccontextmanager
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
from dotenv import load_dotenv

# Chromadb for vector store
from chromadb import Client as ChromaClient
from chromadb.config import Settings

# OpenAI for embeddings only
from openai import OpenAI

# LangChain agent framework
from langchain_core.tools import tool
from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import PromptTemplate

# Load environment variables from backend directory
load_dotenv(Path(__file__).resolve().parent / ".env")


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    yield


app = FastAPI(title="ProcureAI API", version="3.0.0", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB client
mongodb_url = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
mongo_client = AsyncIOMotorClient(mongodb_url)
db = mongo_client.procureai


class ChatRequest(BaseModel):
    message: str


# OpenAI client — embeddings only
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY is not set. Embeddings will fail until set.")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Anthropic Claude — LLM for the agent
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_API_KEY:
    print("Warning: ANTHROPIC_API_KEY is not set. LLM calls will fail until set.")

claude_llm = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    api_key=ANTHROPIC_API_KEY,
    temperature=0,
    max_tokens=1024,
)

# ChromaDB persistent vector store
CHROMA_DIR = Path(__file__).resolve().parent / "chroma_db"
CHROMA_DIR.mkdir(exist_ok=True)

chroma_client = ChromaClient(settings=Settings(persist_directory=str(CHROMA_DIR), is_persistent=True))
chroma_collection = chroma_client.create_collection(name="procureai_documents", get_or_create=True)


# ============= RAG HELPERS =============

def split_text_chunks(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Simple recursive character text splitter."""
    if not text.strip():
        return []

    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""

    for para in paragraphs:
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
    """Generate embedding using OpenAI text-embedding-3-small."""
    if not text.strip():
        return [0.0] * 1536

    try:
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text[:8191]
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error embedding text: {e}")
        return [0.0] * 1536


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from a PDF file."""
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        return ""


def ingest_text(source: str, text: str) -> int:
    """Split text into chunks, embed each, and store in ChromaDB."""
    if not text.strip():
        return 0

    chunks = split_text_chunks(text, chunk_size=500, overlap=50)
    if not chunks:
        return 0

    ids, documents, embeddings_list, metadatas = [], [], [], []
    for i, chunk in enumerate(chunks):
        ids.append(f"{source}_chunk_{i}")
        documents.append(chunk)
        embeddings_list.append(embed_text(chunk))
        metadatas.append({"source": source, "chunk": i})

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
    """Extract PDF text and ingest into ChromaDB."""
    return ingest_text(source, extract_text_from_pdf(pdf_bytes))


def ingest_pdf_file(path: Path) -> Dict[str, str]:
    """Ingest a PDF file from disk."""
    try:
        chunks = ingest_pdf(path.name, path.read_bytes())
        return {"file": path.name, "chunks": chunks}
    except Exception as e:
        print(f"Error ingesting PDF file {path.name}: {e}")
        return {"file": path.name, "chunks": 0}


def is_vectorstore_empty() -> bool:
    try:
        return chroma_collection.count() == 0
    except Exception:
        return True


# ============= LANGCHAIN TOOLS =============

@tool
def document_qa(question: str) -> str:
    """Answer questions about procurement documents, contracts, price lists, and terms
    stored in the vector database. Use this for any question about document contents.
    Input: the question to answer."""
    if not question.strip():
        return "Please provide a question."

    query_embedding = embed_text(question)

    try:
        results = chroma_collection.query(
            query_embeddings=[query_embedding],
            n_results=4,
            include=["documents", "metadatas"],
        )
    except Exception as e:
        return f"Error searching documents: {e}"

    context_docs: List[str] = []
    source_refs: List[str] = []

    if results and results.get("documents"):
        for doc_list in results["documents"]:
            context_docs.extend(doc_list)
        for meta_list in results.get("metadatas", []):
            for meta in meta_list:
                src = meta.get("source", "unknown")
                if src not in source_refs:
                    source_refs.append(src)

    context = "\n".join(context_docs) if context_docs else "No relevant documents found."

    prompt = f"""You are a helpful assistant answering questions about procurement documents.
Use the following context to answer the question.

Context:
{context}

Question: {question}

Answer:"""

    try:
        response = claude_llm.invoke(prompt)
        answer = response.content
    except Exception as e:
        answer = f"Error generating answer: {e}"

    sources_note = f"\n\nSources: {', '.join(source_refs)}" if source_refs else ""
    return answer + sources_note


@tool
async def bid_comparison(category: str = "") -> str:
    """Compare procurement bids ranked by price and delivery time.
    Input: optional category filter (e.g. 'office equipment', 'IT hardware')
    or empty string to compare all bids."""
    try:
        bids_cursor = db.bids.find({}).limit(10)
        bids_list = await bids_cursor.to_list(length=10)

        if not bids_list:
            return "No bids found in the system."

        sorted_bids = sorted(
            bids_list,
            key=lambda x: (x.get("total_price", 0), x.get("delivery_days", 0))
        )

        result = "Bid Comparison Results:\n"
        for i, bid in enumerate(sorted_bids, 1):
            result += f"\n{i}. Supplier ID: {bid.get('supplier_id', 'N/A')}\n"
            result += f"   Total Price: ${bid.get('total_price', 0):.2f}\n"
            result += f"   Delivery Days: {bid.get('delivery_days', 'N/A')}\n"
            result += f"   Terms: {bid.get('terms', 'N/A')}\n"
            result += f"   Status: {bid.get('status', 'pending')}\n"

        return result
    except Exception as e:
        return f"Error comparing bids: {e}"


@tool
async def supplier_lookup(query: str = "") -> str:
    """Find and filter suppliers by category or rating.
    Input: category name (e.g. 'IT Hardware', 'Medical'), or 'rating:4.0' to filter
    by minimum rating, or empty string to list all suppliers."""
    try:
        mongo_query: Dict = {}
        min_rating = 0.0

        if query.startswith("rating:"):
            try:
                min_rating = float(query.split(":")[1].strip())
            except ValueError:
                pass
        elif query.strip():
            mongo_query["category"] = {"$regex": query.strip(), "$options": "i"}

        if min_rating > 0:
            mongo_query["rating"] = {"$gte": min_rating}

        suppliers_cursor = db.suppliers.find(mongo_query).limit(10)
        suppliers_list = await suppliers_cursor.to_list(length=10)

        if not suppliers_list:
            return f"No suppliers found matching: {query}"

        sorted_suppliers = sorted(suppliers_list, key=lambda x: x.get("rating", 0), reverse=True)

        result = f"Supplier Lookup Results ({len(sorted_suppliers)} found):\n"
        for i, s in enumerate(sorted_suppliers, 1):
            result += f"\n{i}. {s.get('name', 'N/A')}\n"
            result += f"   Category: {s.get('category', 'N/A')}\n"
            result += f"   Rating: {s.get('rating', 'N/A')}/5.0\n"
            result += f"   Contact: {s.get('contact', 'N/A')}\n"

        return result
    except Exception as e:
        return f"Error looking up suppliers: {e}"


@tool
async def report_generation(report_type: str = "procurement") -> str:
    """Generate a structured procurement summary report from live MongoDB data.
    Input: report type, e.g. 'procurement', 'summary', or 'full'."""
    try:
        suppliers_list = await db.suppliers.find({}).to_list(length=None)
        bids_list = await db.bids.find({}).to_list(length=None)

        report = f"PROCUREMENT REPORT — {report_type.upper()}\n{'=' * 40}\n\n"
        report += f"SUPPLIERS SUMMARY:\n- Total Suppliers: {len(suppliers_list)}\n"

        if suppliers_list:
            avg_rating = sum(s.get("rating", 0) for s in suppliers_list) / len(suppliers_list)
            categories = set(s.get("category", "unknown") for s in suppliers_list)
            report += f"- Average Rating: {avg_rating:.2f}/5.0\n"
            report += f"- Categories: {', '.join(sorted(categories))}\n"

        report += f"\nBIDS SUMMARY:\n- Total Bids: {len(bids_list)}\n"

        if bids_list:
            total_value = sum(b.get("total_price", 0) for b in bids_list)
            avg_delivery = sum(b.get("delivery_days", 0) for b in bids_list) / len(bids_list)
            statuses: Dict[str, int] = {}
            for bid in bids_list:
                s = bid.get("status", "pending")
                statuses[s] = statuses.get(s, 0) + 1
            report += f"- Total Bid Value: ${total_value:,.2f}\n"
            report += f"- Average Delivery Time: {avg_delivery:.1f} days\n"
            report += f"- Status Distribution: {dict(statuses)}\n"

        return report
    except Exception as e:
        return f"Error generating report: {e}"


# ============= LANGCHAIN REACT AGENT =============

REACT_PROMPT_TEMPLATE = """You are a helpful procurement assistant. Use tools to answer the user's question.

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

react_prompt = PromptTemplate.from_template(REACT_PROMPT_TEMPLATE)

lc_tools = [document_qa, bid_comparison, supplier_lookup, report_generation]

agent = create_react_agent(llm=claude_llm, tools=lc_tools, prompt=react_prompt)

agent_executor = AgentExecutor(
    agent=agent,
    tools=lc_tools,
    return_intermediate_steps=True,
    handle_parsing_errors=True,
    max_iterations=5,
    verbose=True,
)


async def run_agent(user_input: str) -> Dict:
    """Invoke the LangChain AgentExecutor and return response + tool used."""
    if not user_input.strip():
        return {"response": "Please provide a query.", "tool_used": "none"}

    try:
        result = await agent_executor.ainvoke({"input": user_input})
        steps = result.get("intermediate_steps", [])
        tool_used = steps[0][0].tool if steps else "unknown"
        return {
            "response": result["output"],
            "tool_used": tool_used,
        }
    except Exception as e:
        return {"response": f"Error processing query: {e}", "tool_used": "error"}


# ============= FASTAPI ENDPOINTS =============

@app.get("/")
async def root():
    return {"message": "ProcureAI API (LangChain ReAct agent ready)"}


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
    """Chat endpoint powered by LangChain ReAct agent with Anthropic Claude."""
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    result = await run_agent(payload.message)

    if not result.get("response"):
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
    """Direct document Q&A endpoint (bypasses agent routing)."""
    return {"answer": document_qa.invoke(question), "question": question}


@app.get("/reports")
async def get_reports():
    return {"reports": []}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
