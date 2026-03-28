from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from models import Supplier, Bid
import os
from typing import List, Dict
from pathlib import Path
from io import BytesIO
from pypdf import PdfReader

# Chromadb for vector store
from chromadb import Client as ChromaClient
from chromadb.config import Settings

# OpenAI for embeddings and LLM
from openai import OpenAI

app = FastAPI(title="ProcureAI API", version="2.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB client
mongodb_url = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
client = AsyncIOMotorClient(mongodb_url)
db = client.procureai

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
    reader = PdfReader(BytesIO(pdf_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    return "\n".join(pages).strip()


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
async def chat(message: str):
    # Placeholder for chat endpoint
    return {"response": f"Echo: {message}"}

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
