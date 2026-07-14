# RAG Evaluation & Multi-Agent Judging Harness

This project is a multi-agent LLM evaluation framework designed to score, judge, and detect hallucinations in Retrieval-Augmented Generation (RAG) pipelines. It incorporates components of the **RAGAS** metric suite and **TruLens** evaluation triad to assess AI responses across multiple dimensions.

## 🚀 GitHub Repository
- **GitHub Repository Link**: [https://github.com/bhava-intern/rag-eval-agents](https://github.com/bhava-intern/rag-eval-agents)

---

## 🛠️ Tech Stack

### Backend
- **Core Engine**: Python 3.10+
- **API Framework**: FastAPI & Uvicorn
- **Dataset Seeding**: Hugging Face `datasets` (TruthfulQA & SQuAD)
- **Embeddings**: SentenceTransformers (`all-MiniLM-L6-v2`)
- **Vector Index & Storage**: SQLite + NumPy Cosine Similarity
- **LLM Judges**: Gemini API (`google-genai` / `google-generativeai`)

### Frontend
- **Interface**: Vanilla HTML5, CSS3, ES6 Javascript
- **Design System**: Sleek Glassmorphism Dark Mode
- **Typography**: Outfit & Inter (Google Fonts)

---

## 🏗️ System Architecture

1. **Evaluation Input Module**: A clean single-submission web form accepting a question, AI-generated response, and an optional reference answer or source document.
2. **Reference Knowledge Base**: Preseeded database of SQuAD and TruthfulQA contexts, indexed via a vector store for RAG-grounded retrieval.
3. **Multi-Agent Evaluation Pipeline**:
   - **Relevance Judge**: Measures semantic alignment between prompt and response.
   - **Accuracy Judge**: Validates response details against reference documents.
   - **Hallucination Judge**: Verifies if assertions in the response are grounded in references/context.
   - **Completeness Judge**: Confirms that all parts of the user request are answered.
   - **Verdict Agent**: Synthesizes a unified scorecard with scores (1-5) and clear reasoning.

---

## 🏃 Run Guide

### 1. Installation
Clone the repository (or initialize locally) and install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Seeding the Vector Database
Initialize the SQLite database and ingest the reference QA datasets:
```bash
python backend/ingest.py
```

### 3. Running the Server
Start the FastAPI server:
```bash
python backend/app.py
```
Or use Uvicorn directly:
```bash
uvicorn backend.app:app --reload --port 8000
```
Open `frontend/index.html` in your browser (or serve it) to interact with the dashboard.
