from typing import Optional, List, Dict
from pydantic import BaseModel, Field

class EvaluationRequest(BaseModel):
    question: str = Field(..., description="The original user query or question.")
    ai_response: str = Field(..., description="The AI-generated answer to be evaluated.")
    reference_answer: Optional[str] = Field(None, description="Optional ground truth reference answer.")
    source_document: Optional[str] = Field(None, description="Optional source reference document or passage.")
    use_rag: bool = Field(True, description="Whether to fetch additional context from the RAG knowledge base.")

class RetrievedContext(BaseModel):
    id: int
    text: str
    source_dataset: str
    score: float

class DimensionResult(BaseModel):
    score: int
    reasoning: str

class EvaluationResponse(BaseModel):
    status: str
    overall_score: float
    verdict: str
    summary: str
    dimensions: Dict[str, DimensionResult]
    evaluator_type: str
    retrieved_contexts: Optional[List[RetrievedContext]] = None
