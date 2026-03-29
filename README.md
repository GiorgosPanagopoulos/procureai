# ProcureAI

An AI-native procurement assistant that turns procurement workflows into natural language actions. ProcureAI supports bid comparison, supplier lookup, report generation, and document Q&A via a React chat interface backed by FastAPI + MongoDB + ChromaDB + OpenAI.

[![Python](https://img.shields.io/badge/Python-3.14.3-blue.svg)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.2.0-61DAFB.svg)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0.2-3178C6.svg)](https://www.typescriptlang.org)
[![LangChain](https://img.shields.io/badge/LangChain-0.1.0-000000.svg)](https://python.langchain.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-4.6-47A248.svg)](https://www.mongodb.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-1.5.5-FF6B35.svg)](https://www.trychroma.com)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-3.3.0-38B2AC.svg)](https://tailwindcss.com)

## Project Description

ProcureAI combines a robust backend with an intelligent LLM agent and a modern frontend chat interface.

- **Backend**: FastAPI, MongoDB, ChromaDB, OpenAI, and local vector store for RAG.
- **Agent**: ReAct-style prompt routing to tools for bid comparison, supplier lookup, report generation, and document query.
- **Frontend**: React + TypeScript + Tailwind CSS dashboard for chat and results.

> Architecture: frontend React app → FastAPI backend → MongoDB + ChromaDB + OpenAI.


## Architecture

- `frontend`: React app with `/chat`, `/upload`, and helper panels
- `backend`: FastAPI routes with Mongo and ChromaDB access
- `models`: Pydantic schemas for Supplier/Bid
- `data`: seed data + sample PDFs
- `agent`: routing and tool invocation in `main.py`

## Tech Stack

- 🐍 Python 3.14.3 (FastAPI, Motor, Pydantic)
- ⚛️ React 18.2.0 (TypeScript)
- 🟦 TypeScript 5.0.2
- 🧠 LangChain-style ReAct agent (customized from template)
- 🍃 MongoDB (async Motor driver)
- 🔶 ChromaDB vector store
- 🎨 Tailwind CSS frontend styling

## Setup Instructions

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# set OPENAI_API_KEY, MONGODB_URI
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

Frontend runs at `http://localhost:3000`.

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

- GitHub: https://github.com/GiorgosPanagopoulos
- LinkedIn: https://linkedin.com/in/georgios-panagopoulos-9253842ba