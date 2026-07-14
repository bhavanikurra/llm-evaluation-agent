import os
import json
import re
import numpy as np

HAS_GENAI = False
try:
    import google.generativeai as genai
    # Check if key is available
    if os.environ.get("GEMINI_API_KEY"):
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        HAS_GENAI = True
except ImportError:
    pass

def parse_json_response(text: str) -> dict:
    """Extracts and parses JSON content from LLM response."""
    try:
        # Search for first occurrences of { and last }
        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        return json.loads(text)
    except Exception:
        # Fallback parsing or default schema
        return {"score": 3, "reasoning": f"Failed to parse LLM JSON. Original output: {text[:100]}..."}

def query_gemini(prompt: str, model_name: str = "gemini-1.5-flash") -> str:
    """Queries Gemini API for evaluation."""
    if not HAS_GENAI:
        raise ValueError("Gemini API not configured or google-generativeai not installed.")
        
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    return response.text

# ----------------- MOCK / HEURISTIC EVALUATION ENGINE -----------------

def run_heuristic_relevance(question: str, ai_response: str) -> dict:
    q_words = set(question.lower().split())
    r_words = set(ai_response.lower().split())
    overlap = len(q_words.intersection(r_words))
    
    # Simple score based on overlap relative to question length
    ratio = overlap / max(len(q_words), 1)
    if ratio > 0.4:
        score = 5
        reasoning = f"The response is highly relevant, sharing significant vocabulary ({overlap} matching terms) with the question."
    elif ratio > 0.2:
        score = 4
        reasoning = "The response is relevant, directly addressing topics matching terms in the question."
    elif ratio > 0.05:
        score = 3
        reasoning = "The response is moderately relevant, but references only a few key terms from the prompt."
    else:
        score = 2
        reasoning = "The response has low relevance, failing to share significant contextual overlap with the query."
    return {"score": score, "reasoning": reasoning}

def run_heuristic_accuracy(ai_response: str, reference: str, source_doc: str) -> dict:
    ref_text = (reference or "") + " " + (source_doc or "")
    ref_text = ref_text.strip()
    
    if not ref_text:
        return {"score": 3, "reasoning": "No reference answer or source document provided. Score is neutral."}
        
    r_words = set(ai_response.lower().split())
    ref_words = set(ref_text.lower().split())
    overlap = len(r_words.intersection(ref_words))
    
    ratio = overlap / max(len(r_words), 1)
    if ratio > 0.5:
        score = 5
        reasoning = f"The response is highly accurate, matching {int(ratio*100)}% of content terms found in the reference document."
    elif ratio > 0.3:
        score = 4
        reasoning = "The response is mostly accurate, containing substantial matching information from references."
    elif ratio > 0.1:
        score = 3
        reasoning = "The response is partially accurate, but misses key supporting facts from the reference source."
    else:
        score = 1
        reasoning = "The response has very low accuracy, sharing almost no factual alignment with the reference material."
        
    return {"score": score, "reasoning": reasoning}

def run_heuristic_hallucination(ai_response: str, reference: str, source_doc: str) -> dict:
    ref_text = (reference or "") + " " + (source_doc or "")
    ref_text = ref_text.strip()
    
    if not ref_text:
        # In a real pipeline, lack of context makes groundedness hard to score, so we flag it
        return {"score": 3, "reasoning": "No reference or source document provided to ground assertions. Potential hallucination risk is moderate."}
        
    # Find words in response that are NOT in reference
    r_words = ai_response.lower().split()
    ref_words = set(ref_text.lower().split())
    
    # We ignore standard stopwords to avoid false flags
    stopwords = {"the", "a", "an", "is", "are", "was", "were", "of", "in", "to", "and", "or", "for", "with", "by", "on"}
    unsupported = [w for w in r_words if w not in ref_words and w not in stopwords and len(w) > 3]
    
    ratio = len(unsupported) / max(len(r_words), 1)
    if ratio < 0.15:
        score = 5
        reasoning = "Excellent groundedness. Almost all semantic assertions are backed by the provided reference text."
    elif ratio < 0.3:
        score = 4
        reasoning = "Mostly grounded. Contains minor auxiliary claims or word variations not explicitly stated in the source."
    elif ratio < 0.5:
        score = 3
        reasoning = "Moderate hallucination. Multiple key statements lack support in the reference material."
    else:
        score = 1
        reasoning = f"Severe hallucination. A large portion of the assertions (unsupported terms: {', '.join(list(set(unsupported))[:5])}) are ungrounded."
        
    return {"score": score, "reasoning": reasoning}

def run_heuristic_completeness(question: str, ai_response: str) -> dict:
    # Heuristics based on response length and question structure
    q_len = len(question.split())
    r_len = len(ai_response.split())
    
    # If the question contains 'and', 'or', commas, or question marks, it might have multiple parts
    subparts = len(re.split(r'\?|\band\b|,', question))
    
    if r_len > q_len * 1.5:
        score = 5
        reasoning = f"The response is thorough ({r_len} words) and fully addresses the question's subparts."
    elif r_len > q_len * 0.7:
        score = 4
        reasoning = "The response is sufficiently complete, covering the main aspects of the inquiry."
    elif r_len > 10:
        score = 3
        reasoning = "The response is brief. It answers the main question but lacks detail or completeness."
    else:
        score = 2
        reasoning = "The response is overly brief or incomplete, likely leaving some requirements unanswered."
        
    return {"score": score, "reasoning": reasoning}

def run_heuristic_verdict(relevance: dict, accuracy: dict, hallucination: dict, completeness: dict) -> dict:
    scores = [relevance["score"], accuracy["score"], hallucination["score"], completeness["score"]]
    avg_score = sum(scores) / len(scores)
    
    if avg_score >= 4.5:
        verdict = "Excellent"
        summary = "The AI response is outstanding: highly relevant, accurate, fully grounded, and comprehensive."
    elif avg_score >= 3.8:
        verdict = "Pass"
        summary = "The AI response is satisfactory and matches reference expectations with minor omissions or non-critical deviations."
    elif avg_score >= 2.8:
        verdict = "Needs Improvement"
        summary = "The AI response is partially correct but has noticeable gaps in completeness, relevance, or groundedness."
    else:
        verdict = "Fail"
        summary = "The AI response failed critical checkpoints, exhibiting severe hallucinations, low relevance, or high error rates."
        
    return {
        "overall_score": round(avg_score, 2),
        "verdict": verdict,
        "summary": summary
    }

# ----------------- MULTI-AGENT ORCHESTRATION -----------------

def evaluate_submission(question: str, ai_response: str, reference: str = None, source_doc: str = None) -> dict:
    """
    Orchestrates the evaluation flow through Relevance, Accuracy,
    Hallucination, and Completeness agents, concluding with the Verdict Agent.
    """
    ref_context = (reference or "").strip()
    doc_context = (source_doc or "").strip()
    combined_context = f"Reference Answer: {ref_context}\nSource Document: {doc_context}".strip()
    
    # If Gemini is configured, run LLM-based evaluation
    if HAS_GENAI:
        print("Using Gemini API for Multi-Agent Judging...")
        try:
            # 1. Relevance Judge
            prompt_rel = f"""
            You are a Relevance Judge Agent.
            Evaluate whether the AI Response directly answers the Question, ignoring correctness/factuality.
            Rate from 1 (completely irrelevant) to 5 (perfectly relevant).
            
            Question: {question}
            AI Response: {ai_response}
            
            Respond strictly in JSON format matching this schema:
            {{"score": int, "reasoning": "str"}}
            """
            rel_res = parse_json_response(query_gemini(prompt_rel))
            
            # 2. Accuracy Judge
            prompt_acc = f"""
            You are an Accuracy Judge Agent.
            Compare the AI Response with the provided Reference/Source Context. Identify factual inconsistencies or errors.
            Rate from 1 (fully inaccurate/contradictory) to 5 (fully accurate/correct).
            
            Question: {question}
            AI Response: {ai_response}
            Reference/Source Context: {combined_context if combined_context else "None provided."}
            
            Respond strictly in JSON format matching this schema:
            {{"score": int, "reasoning": "str"}}
            """
            acc_res = parse_json_response(query_gemini(prompt_acc))
            
            # 3. Hallucination Judge
            prompt_hal = f"""
            You are a Hallucination Detection Agent.
            Verify if the statements in the AI Response are grounded in (supported by) the Reference/Source Context.
            Ungrounded statements are hallucinations.
            Rate from 1 (completely ungrounded / severe hallucinations) to 5 (perfectly grounded / no hallucinations).
            
            AI Response: {ai_response}
            Reference/Source Context: {combined_context if combined_context else "None provided."}
            
            Respond strictly in JSON format matching this schema:
            {{"score": int, "reasoning": "str"}}
            """
            hal_res = parse_json_response(query_gemini(prompt_hal))
            
            # 4. Completeness Judge
            prompt_comp = f"""
            You are a Completeness Judge Agent.
            Verify if the AI Response answers all subparts or implied requirements of the Question.
            Rate from 1 (highly incomplete) to 5 (perfectly complete).
            
            Question: {question}
            AI Response: {ai_response}
            
            Respond strictly in JSON format matching this schema:
            {{"score": int, "reasoning": "str"}}
            """
            comp_res = parse_json_response(query_gemini(prompt_comp))
            
            # 5. Verdict Agent (Aggregator)
            prompt_verd = f"""
            You are the Verdict Agent.
            Aggregate the scores and reasonings of the other judges to compile an overall scorecard.
            
            Relevance Judge: Score {rel_res.get('score')}, Reasoning: {rel_res.get('reasoning')}
            Accuracy Judge: Score {acc_res.get('score')}, Reasoning: {acc_res.get('reasoning')}
            Hallucination Judge: Score {hal_res.get('score')}, Reasoning: {hal_res.get('reasoning')}
            Completeness Judge: Score {comp_res.get('score')}, Reasoning: {comp_res.get('reasoning')}
            
            Compute the overall score (average of the 4 scores) and formulate an executive summary verdict.
            The verdict must be one of: "Excellent", "Pass", "Needs Improvement", or "Fail".
            
            Respond strictly in JSON format matching this schema:
            {{"overall_score": float, "verdict": "str", "summary": "str"}}
            """
            verd_res = parse_json_response(query_gemini(prompt_verd))
            
            return {
                "status": "success",
                "overall_score": verd_res.get("overall_score", 3.0),
                "verdict": verd_res.get("verdict", "Needs Review"),
                "summary": verd_res.get("summary", "Synthesis completed by Verdict Agent."),
                "dimensions": {
                    "relevance": rel_res,
                    "accuracy": acc_res,
                    "hallucination": hal_res,
                    "completeness": comp_res
                },
                "evaluator_type": "Gemini LLM Multi-Agent Pipeline"
            }
            
        except Exception as e:
            print(f"Gemini evaluation failed: {e}. Falling back to Heuristic Engine...")
            # Fall through to heuristics
            
    # Fallback/Heuristic Evaluation Engine
    print("Running Heuristic Multi-Agent Judging Engine...")
    rel_res = run_heuristic_relevance(question, ai_response)
    acc_res = run_heuristic_accuracy(ai_response, reference, source_doc)
    hal_res = run_heuristic_hallucination(ai_response, reference, source_doc)
    comp_res = run_heuristic_completeness(question, ai_response)
    verd_res = run_heuristic_verdict(rel_res, acc_res, hal_res, comp_res)
    
    return {
        "status": "success",
        "overall_score": verd_res["overall_score"],
        "verdict": verd_res["verdict"],
        "summary": verd_res["summary"],
        "dimensions": {
            "relevance": rel_res,
            "accuracy": acc_res,
            "hallucination": hal_res,
            "completeness": comp_res
        },
        "evaluator_type": "Heuristic Mock Multi-Agent Pipeline (Fallback)"
    }
