# ProcureAI

An AI-Native Procurement Assistant powered by LLM and LangChain.

## Overview

ProcureAI automates procurement workflows through natural language commands using a React chat interface.

## Tech Stack

- **Backend**: Python 3.14.3, FastAPI, LangChain, ChromaDB, MongoDB
- **Frontend**: React + TypeScript
- **AI**: OpenAI API, ReAct pattern

## Project Structure

```
procureai/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── models/              # Pydantic models
│   ├── routes/              # API routes
│   ├── data/                # Seed data and PDFs
│   ├── utils/               # Utilities
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    └── package.json         # React TypeScript setup
```

## Setup

### Backend

1. Install dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your MongoDB URL and OpenAI API key
   ```

3. Seed the database:
   ```bash
   python data/seed.py
   ```

4. Run the server:
   ```bash
   python main.py
   ```

### Frontend

1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Run the development server:
   ```bash
   npm run dev
   ```

## API Endpoints

- `GET /` - Root
- `GET /suppliers` - List suppliers
- `GET /bids` - List bids
- `POST /chat` - Chat with AI agent
- `POST /upload` - Upload documents
- `GET /reports` - Get reports

## Milestones

- **Milestone 1**: Data layer + FastAPI skeleton ✅
- Milestone 2: RAG system + document upload
- Milestone 3: LangChain agent with tools
- Milestone 4: React frontend integration
- Milestone 5: Full deployment