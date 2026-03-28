# ProcureAI

An AI-Native Procurement Assistant powered by LLM and LangChain.

[![Python](https://img.shields.io/badge/Python-3.14.3-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.2.0-61DAFB.svg)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0.2-3178C6.svg)](https://typescriptlang.org)
[![LangChain](https://img.shields.io/badge/LangChain-0.1.0-000000.svg)](https://langchain.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-4.6-47A248.svg)](https://mongodb.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-1.5.5-FF6B35.svg)](https://chroma-db.com)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.3.0-38B2AC.svg)](https://tailwindcss.com)

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

## Author

Developed by **[Georgios Panagopoulos](https://github.com/GiorgosPanagopoulos)**.

- GitHub: https://github.com/GiorgosPanagopoulos
- LinkedIn: https://linkedin.com/in/georgios-panagopoulos-9253842ba