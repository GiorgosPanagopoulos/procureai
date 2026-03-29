# ProcureAI

An AI-native procurement assistant that turns procurement workflows into natural language actions.

ProcureAI supports bid comparison, supplier lookup, report generation, and document Q&A via a React chat interface backed by FastAPI, MongoDB, ChromaDB, Anthropic Claude, and OpenAI embeddings.

[![Python](https://img.shields.io/badge/Python-3.14.3-blue.svg)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135%2B-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.2.0-61DAFB.svg)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0.2-3178C6.svg)](https://www.typescriptlang.org)
[![Claude](https://img.shields.io/badge/Claude-claude--sonnet--4-CC785C.svg)](https://anthropic.com)
[![OpenAI](https://img.shields.io/badge/OpenAI-Embeddings-412991.svg)](https://openai.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248.svg)](https://www.mongodb.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-1.5.5-FF6B35.svg)](https://www.trychroma.com)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-4.x-38B2AC.svg)](https://tailwindcss.com)

## Project Description

ProcureAI combines a robust backend with an intelligent LLM agent and a modern frontend chat interface.

- **Backend**: FastAPI, MongoDB, ChromaDB, and local vector store for RAG.
- **Agent**: ReAct-style prompt routing powered by **Anthropic Claude** (`claude-sonnet-4-20250514`) for intent classification and response synthesis.
- **Embeddings**: OpenAI `text-embedding-3-small` for vector search.
- **Frontend**: React + TypeScript + Tailwind CSS dashboard for chat and results.

> Architecture: frontend React app → FastAPI backend → MongoDB + ChromaDB + Anthropic Claude + OpenAI embeddings.

## Architecture

- `frontend`: React app with `/chat`, `/upload`, and helper panels
- `backend`: FastAPI routes with Mongo and ChromaDB access
- `models`: Pydantic schemas for Supplier/Bid
- `data`: seed data + sample PDFs
- `agent`: routing and tool invocation in `main.py`

## Tech Stack

- 🐍 Python 3.14+ (FastAPI, Motor, Pydantic)
- ⚛️ React 18.2.0 (TypeScript)
- 🟦 TypeScript 5.0.2
- 🧠 Custom ReAct-style agent with Anthropic Claude (`claude-sonnet-4-20250514`)
- 🔗 OpenAI `text-embedding-3-small` for RAG vector search
- 🍃 MongoDB Atlas (async Motor driver)
- 🔶 ChromaDB vector store (RAG pipeline)
- 🎨 Tailwind CSS v4 frontend styling

## Setup Instructions

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# set OPENAI_API_KEY (embeddings), ANTHROPIC_API_KEY (LLM), MONGODB_URI
python data/seed.py
```

Start backend:

```bash
PYTHONPATH=./ uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173` (Vite default).

### 3. One-shot script

Run `./start.sh` from repo root (created below) to start both services.

## Example Queries

- "Compare bids for office equipment"
- "Find suppliers for IT hardware with rating >4"
- "Generate procurement report for this quarter"
- "What are the payment terms in the BuildPro contract?"
- "Show the top 3 cheapest bids with immediate delivery"

## API Endpoints

- `GET /` - health check
- `GET /suppliers` - all supplier records
- `GET /bids` - all bids
- `POST /chat` - `{"message":"..."}`
- `POST /upload` - multipart PDF upload
- `GET /reports` - placeholder report data
- `POST /doc_qa` - doc question (query param `question`)

## Author

Developed by **[Georgios Panagopoulos](https://github.com/GiorgosPanagopoulos)**.

- GitHub: [github.com/GiorgosPanagopoulos](https://github.com/GiorgosPanagopoulos)
- LinkedIn: [linkedin.com/in/georgios-panagopoulos-9253842ba](https://linkedin.com/in/georgios-panagopoulos-9253842ba)
