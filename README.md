<div align="center">
<h1>🤖 ProcureAI</h1>
<p><strong>AI-Native Procurement Assistant powered by LangChain ReAct Agent & RAG</strong></p>
<p><em>Turn procurement workflows into natural language actions</em></p>
</div>

---

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18.2.0-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-v4-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-AgentExecutor-1C3C3C?style=for-the-badge&logo=chainlink&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=for-the-badge&logo=mongodb&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-1.5.5-FF6B35?style=for-the-badge&logo=databricks&logoColor=white)
![Anthropic](https://img.shields.io/badge/Anthropic-Claude_Sonnet-CC785C?style=for-the-badge&logo=anthropic&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-Embeddings-412991?style=for-the-badge&logo=openai&logoColor=white)

</div>

---

## 🎬 Demo

<div align="center">

![ProcureAI Demo](docs/screenshots/demo.gif)

</div>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 **Supplier Lookup** | Natural language queries against the supplier database |
| 📊 **Bid Comparison** | Ranked bid analysis with pricing, delivery terms, and compliance scoring |
| 📄 **Document Q&A** | RAG-powered Q&A over uploaded procurement contracts and PDFs |
| 📋 **Report Generation** | Automated procurement summary reports |
| 🌐 **Bilingual UI** | Greek/English toggle with automatic locale switching |
| 🌗 **Dark/Light Mode** | Full theme support via Tailwind CSS v4 |

---

## 🏗️ Architecture

```mermaid
graph TD
    subgraph Frontend["⚛️ Frontend (React + TypeScript)"]
        UI["Chat Interface\n/chat · /upload · /reports"]
    end

    subgraph Backend["⚙️ Backend (FastAPI)"]
        API["REST API\n/chat · /suppliers · /bids\n/upload · /doc_qa · /reports"]
    end

    subgraph AgentLayer["🦜 Agent Layer (LangChain ReAct)"]
        AGENT["AgentExecutor\ncreate_react_agent"]
        T1["🔍 Supplier Lookup"]
        T2["📊 Bid Comparison"]
        T3["📄 Document Q&A"]
        T4["📋 Report Generator"]
    end

    subgraph DataLayer["🗄️ Data Layer"]
        MONGO["MongoDB Atlas\nSuppliers · Bids"]
        CHROMA["ChromaDB\nVector Store"]
        EMBED["OpenAI\ntext-embedding-3-small"]
    end

    subgraph LLM["🧠 LLM Layer"]
        CLAUDE["Anthropic Claude\nclaude-sonnet-4-20250514"]
    end

    UI -->|HTTP / JSON| API
    API --> AGENT
    AGENT --> T1
    AGENT --> T2
    AGENT --> T3
    AGENT --> T4
    T1 --> MONGO
    T2 --> MONGO
    T3 --> EMBED
    EMBED --> CHROMA
    CHROMA -->|Retrieved context| T3
    AGENT <-->|Reasoning & tool calls| CLAUDE
```

---

## 🛠️ Tech Stack

| Technology | Role |
|-----------|------|
| ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white) | Backend runtime, async FastAPI server, agent logic |
| ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white) | REST API framework with async Motor driver |
| ![React](https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black) | Chat interface, upload panel, results dashboard |
| ![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white) | Type-safe frontend development |
| ![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white) | UI styling, dark/light mode, responsive layout |
| ![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=chainlink&logoColor=white) | `AgentExecutor` + `create_react_agent` + `@tool` decorator |
| ![Anthropic](https://img.shields.io/badge/Anthropic-CC785C?style=for-the-badge&logo=anthropic&logoColor=white) | `ChatAnthropic` (`claude-sonnet-4-20250514`) for LLM reasoning |
| ![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white) | `text-embedding-3-small` for ChromaDB vector search |
| ![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=for-the-badge&logo=mongodb&logoColor=white) | Atlas cloud store for supplier and bid records |
| ![ChromaDB](https://img.shields.io/badge/ChromaDB-FF6B35?style=for-the-badge&logo=databricks&logoColor=white) | Local vector store for RAG document retrieval |

---

## 📸 Screenshots

### 🔍 Supplier Lookup

Natural language queries against the supplier database.

![Supplier Lookup](docs/screenshots/supplier-lookup.png)

### 📊 Bid Comparison

Ranked bid analysis with pricing, delivery terms, and status indicators.

![Bid Comparison](docs/screenshots/bid-comparison.png)

### 📄 Document Q&A (RAG)

Ask questions about uploaded procurement contracts and PDFs.

![Document QA](docs/screenshots/document-qa.png)

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/GiorgosPanagopoulos/procureai.git
cd procureai
```

### 2. Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then fill in your API keys
python data/seed.py              # seed MongoDB with sample data
```

Start the backend server:

```bash
PYTHONPATH=./ uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Frontend available at `http://localhost:5173` (Vite default).

### 4. One-shot start

From the repo root, run both services with:

```bash
./start.sh
```

---

## 🔑 Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in the values below:

| Variable | Description | Required |
|----------|-------------|:--------:|
| `ANTHROPIC_API_KEY` | Claude API key for LLM reasoning | ✅ |
| `OPENAI_API_KEY` | OpenAI API key for document embeddings | ✅ |
| `MONGODB_URI` | MongoDB Atlas connection string | ✅ |

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/suppliers` | Return all supplier records |
| `GET` | `/bids` | Return all bid records |
| `POST` | `/chat` | Send a message `{"message": "..."}` to the ReAct agent |
| `POST` | `/upload` | Upload a PDF document (multipart form) |
| `GET` | `/reports` | Retrieve procurement report data |
| `POST` | `/doc_qa` | Ask a question about an uploaded document (`?question=...`) |

---

## 📁 Project Structure

```text
procureai/
├── backend/
│   ├── data/
│   │   ├── pdfs/               # Sample procurement contracts
│   │   └── seed.py             # MongoDB seed script
│   ├── models/
│   │   ├── supplier.py         # Pydantic Supplier schema
│   │   └── bid.py              # Pydantic Bid schema
│   ├── main.py                 # FastAPI app + LangChain agent + all tools
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx             # Main React component
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
├── docs/
│   └── screenshots/
│       ├── demo.gif
│       ├── supplier-lookup.png
│       ├── bid-comparison.png
│       └── document-qa.png
├── start.sh                    # One-shot startup script
└── README.md
```

---

## 💡 Why ProcureAI?

ProcureAI was built as the final project for the **AUEB "AI for Developers" programme** (KEDIVIM / OPA, 2026). The goal was to apply production-grade AI engineering patterns to a real-world domain — institutional procurement.

Key technical decisions:

| Decision | Rationale |
|----------|-----------|
| **ReAct agent over fixed chains** | Dynamic tool selection lets the agent handle diverse, multi-step queries without hardcoded routing logic |
| **Hybrid data layer** | MongoDB for structured supplier/bid records (fast filtering, aggregation); ChromaDB for document embeddings (semantic similarity) |
| **Decoupled embedding & LLM providers** | OpenAI embeddings + Anthropic Claude — avoids vendor lock-in, allows independent cost optimisation of each layer |
| **Bilingual design (Greek/English)** | Built for real-world institutional deployment in Greek public-sector or academic procurement contexts |

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">
**⚡ Built by [Georgios Panagopoulos](https://github.com/GiorgosPanagopoulos)**  
*"I build things I'd trust with something that matters."*

[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/GiorgosPanagopoulos)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/georgios-panagopoulos-9253842ba)
</div>
