import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer

# Ensure parent directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import database
import evaluator
from models import EvaluationRequest, EvaluationResponse, RetrievedContext

app = FastAPI(
    title="RAG Evaluation Multi-Agent Judging Pipeline",
    description="Milestone 1 API server for evaluating AI responses and grounding them in QA Datasets.",
    version="1.0.0"
)

# Enable CORS for frontend interface testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global embedding model loaded on startup
embed_model = None

@app.on_event("startup")
def startup_event():
    global embed_model
    print("Starting up Evaluation backend...")
    database.init_db()
    
    # Pre-load embedding model for fast RAG lookups
    try:
        print("Pre-loading sentence-transformer model ('all-MiniLM-L6-v2')...")
        embed_model = SentenceTransformer("all-MiniLM-L6-v2")
        print("Model loaded successfully.")
    except Exception as e:
        print(f"Warning: Could not pre-load model: {e}. Model will load lazily on first request.")

def get_embedding_model():
    global embed_model
    if embed_model is None:
        print("Lazy-loading sentence-transformer model...")
        embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    return embed_model

@app.post("/api/evaluate", response_model=EvaluationResponse)
def evaluate(req: EvaluationRequest):
    try:
        retrieved_docs = []
        source_doc_for_eval = req.source_document or ""
        
        # 1. Perform RAG query if requested and no explicit context is provided (or in addition)
        if req.use_rag:
            try:
                # Embed query
                model = get_embedding_model()
                q_emb = model.encode(req.question).tolist()
                
                # Fetch top 3 matches from knowledge base
                matches = database.retrieve_top_k(q_emb, k=3)
                
                for m in matches:
                    retrieved_docs.append(RetrievedContext(
                        id=m["id"],
                        text=m["text"],
                        source_dataset=m["source_dataset"],
                        score=round(m["score"], 4)
                    ))
                    
                # Append retrieved texts to source_doc if not empty, to ground the check
                if retrieved_docs:
                    retrieved_context_str = "\n\n".join([
                        f"[Source: {d.source_dataset}] {d.text}" for d in retrieved_docs
                    ])
                    if source_doc_for_eval:
                        source_doc_for_eval = f"{source_doc_for_eval}\n\nRetrieved Knowledge:\n{retrieved_context_str}"
                    else:
                        source_doc_for_eval = retrieved_context_str
            except Exception as ex:
                print(f"RAG Retrieval failed: {ex}. Proceeding with original inputs...")
                
        # 2. Run Multi-Agent evaluation
        eval_result = evaluator.evaluate_submission(
            question=req.question,
            ai_response=req.ai_response,
            reference=req.reference_answer,
            source_doc=source_doc_for_eval if source_doc_for_eval else None
        )
        
        return EvaluationResponse(
            status=eval_result["status"],
            overall_score=eval_result["overall_score"],
            verdict=eval_result["verdict"],
            summary=eval_result["summary"],
            dimensions=eval_result["dimensions"],
            evaluator_type=eval_result["evaluator_type"],
            retrieved_contexts=retrieved_docs if retrieved_docs else None
        )
        
    except Exception as e:
        print(f"Evaluation Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
def get_db_stats():
    try:
        return database.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query database stats: {str(e)}")

@app.get("/api/health")
def healthcheck():
    stats = {}
    try:
        stats = database.get_stats()
        db_status = "healthy"
    except Exception:
        db_status = "unreachable"
        
    return {
        "status": "online",
        "database": db_status,
        "database_stats": stats,
        "api_version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
