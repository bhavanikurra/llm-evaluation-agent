# Project Presentation Guide: LLM RAG Evaluation Harness

This document serves as your slide structure, talk track, and demonstration script for presenting the **Milestone 1** prototype to your mentor or team.

---

## 📋 Presentation Slide Structure

### Slide 1: Title & Overview
*   **Slide Title**: Multi-Agent LLM Evaluation Harness & Knowledge Base
*   **Subtitle**: Milestone 1: Core Architecture, Seeding, and Input Module
*   **Key Talking Points**:
    *   Designed a RAG-grounded evaluation engine based on state-of-the-art academic frameworks (RAGAS & TruLens).
    *   Engineered a multi-agent judging pipeline analyzing responses across 4 critical dimensions: Relevance, Accuracy, Groundedness (Hallucination), and Completeness.
    *   Seeded a local reference database using Hugging Face datasets (SQuAD and TruthfulQA).

### Slide 2: Problem Statement & Motivation
*   **Slide Title**: Why Multi-Agent RAG Evaluation?
*   **Key Talking Points**:
    *   Traditional metrics (ROUGE, BLEU) fail to grasp semantic meaning and context.
    *   **Hallucination risk**: LLMs frequently generate plausible-sounding but completely incorrect statements.
    *   **The RAG Triad**: Standardizing evaluation based on context relevance, groundedness, and answer relevance.
    *   Need for automated, structured, and interpretable evaluations before deploying production LLMs.

### Slide 3: Technical Architecture
*   **Slide Title**: Decoupled Engine Flow
*   **Visual Flow** (Draw or speak through this path):
    1.  **Frontend (SPA)**: Glassmorphic user interface collects the Query, AI Response, and options.
    2.  **FastAPI Backend**: Orchestrates the retrieval and evaluation logic.
    3.  **Reference Knowledge Base**: SQLite + NumPy semantic search (using `all-MiniLM-L6-v2` embeddings) finds ground-truth matching facts.
    4.  **Multi-Agent Pipeline**: Spawns 4 distinct evaluators in parallel (Relevance, Accuracy, Hallucination, Completeness).
    5.  **Verdict Agent**: Consolidates the scores (1-5 scale) and summaries into a structured JSON scorecard.

### Slide 4: Agent Responsibilities
*   **Slide Title**: The Judging Panel
*   **Details**:
    *   **Relevance Judge**: Does the response answer the user's intent? (ignores correctness).
    *   **Accuracy Judge**: Compares facts with reference texts.
    *   **Hallucination Detector**: Scans for assertions not backed by source documents (groundedness).
    *   **Completeness Judge**: Confirms all subparts of the query are addressed.
    *   **Verdict Agent**: Acts as meta-reviewer, averages scores, and writes the executive summary.

### Slide 5: Engineering Decisions & Highlights
*   **Slide Title**: Smart Engineering & Robustness
*   **Details**:
    *   **SQLite + NumPy Vector Engine**: Avoided heavy compilation issues (like FAISS or ChromaDB on Windows) by using numpy-optimized cosine calculations on top of SQLite blob storage. Fast and 100% reliable.
    *   **Dual Mode Evaluation**: Configured with Gemini API integration (`google-genai`), falling back to a deterministic semantic heuristic algorithm if the API key is not in the environment.
    *   **Modern SPA Design**: Modern typography (Outfit/Inter), glowing animations, dark-theme layout, and preset buttons for SQuAD and TruthfulQA.

---

## 🎙️ Presentation Talk Track & Demo Script

Follow this script to demonstrate the live functionality:

### Step 1: Initialize the Stage
1.  Open the dashboard in Chrome/Edge by loading `frontend/index.html`.
2.  Point out the **"API Active"** indicator in the top-right, showing the FastAPI server is online.
3.  Point out the **"KB: 87 SQuAD | 50 TQA"** database badge, demonstrating that SQuAD and TruthfulQA data are indexed in the vector database.

### Step 2: Run a SQuAD Grounded Test
1.  Click the **SQuAD Sample** preset button. This populates a factual question about the European Space Agency.
2.  Click **Evaluate Response**.
3.  *Explain*: "Our interface shows animated status indicators as the orchestrator triggers the Relevance, Accuracy, Groundedness, and Completeness agents in sequence."
4.  Once the results load, show:
    *   The **Overall Score** (4.5/5) and **Verdict** (Excellent).
    *   The individual **Dimensional Scores** with progress bars and reasonings.
    *   The **Retrieved Grounding Context** section at the bottom, which displays similar contexts retrieved from the SQLite vector DB.

### Step 3: Run a TruthfulQA Hallucination Test
1.  Click **Clear**, then click **TruthfulQA Sample**.
2.  *Explain*: "This sample asks if touching a toad's warts causes warts. The AI response claims it is highly contagious. We leave the 'Source Document' field blank to force the RAG engine to query our pre-seeded reference knowledge base."
3.  Click **Evaluate Response**.
4.  Once it returns:
    *   Show how the **Hallucination Judge** catches the discrepancy.
    *   Show how the **RAG Grounding Context** section shows the retrieved statements from TruthfulQA (explaining that human warts are caused by HPV, not toads).
