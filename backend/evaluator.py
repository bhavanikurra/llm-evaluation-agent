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

def split_sentences(text: str) -> list[str]:
    """Helper to split text into sentences cleanly."""
    if not text:
        return []
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in sentences if len(s.strip()) > 3]

def get_filtered_words(text: str, question: str = "") -> set[str]:
    """Extracts words from text, excluding common stopwords and question terms."""
    if not text:
        return set()
    stopwords = {"the", "a", "an", "is", "are", "was", "were", "of", "in", "to", "and", "or", "for", "with", "by", "on", "it", "its", "has", "have", "had", "been", "be", "that", "this", "these", "those", "about"}
    q_words = set(question.lower().split()) if question else set()
    
    words = re.findall(r'\b[a-z]{3,}\b', text.lower())
    return {w for w in words if w not in stopwords and w not in q_words}

def run_heuristic_accuracy(ai_response: str, reference: str, source_doc: str, question: str = "") -> dict:
    ref_text = (reference or "") + " " + (source_doc or "")
    ref_text = ref_text.strip()
    
    sentences = split_sentences(ai_response)
    matched = []
    mismatched = []
    
    if not ref_text:
        return {
            "score": 3,
            "reasoning": "No reference answer or source document provided. Score is neutral.",
            "matched_facts": [],
            "mismatched_facts": sentences
        }
        
    ref_filtered = get_filtered_words(ref_text, question)
    
    for sentence in sentences:
        s_filtered = get_filtered_words(sentence, question)
        if not s_filtered:
            # If the sentence has no content terms beyond the question context,
            # we classify it as matched to prevent false negatives on short structural replies
            matched.append(sentence)
            continue
            
        matches = s_filtered.intersection(ref_filtered)
        ratio = len(matches) / len(s_filtered)
        
        # If over 25% of new content words match the filtered reference, we treat it as accurate
        if ratio >= 0.25:
            matched.append(sentence)
        else:
            mismatched.append(sentence)
            
    ratio_correct = len(matched) / max(len(sentences), 1)
    if ratio_correct >= 0.8:
        score = 5
        reasoning = "Excellent accuracy. Almost all claims made in the response match the facts in the reference material."
    elif ratio_correct >= 0.5:
        score = 4
        reasoning = "High accuracy. The response contains major facts that align with reference, but includes minor unsupported details."
    elif ratio_correct >= 0.2:
        score = 3
        reasoning = "Moderate accuracy. Several key statements contain factual mismatches or are not present in reference."
    else:
        score = 1
        reasoning = "Low accuracy. The response heavily contradicts or fails to align with reference facts."
        
    return {
        "score": score,
        "reasoning": reasoning,
        "matched_facts": matched,
        "mismatched_facts": mismatched
    }

def run_heuristic_hallucination(ai_response: str, reference: str, source_doc: str, question: str = "") -> dict:
    ref_text = (reference or "") + " " + (source_doc or "")
    ref_text = ref_text.strip()
    
    sentences = split_sentences(ai_response)
    claims_analysis = []
    flagged = []
    
    if not ref_text:
        for s in sentences:
            claims_analysis.append({
                "claim": s,
                "status": "Hallucinated",
                "explanation": "No reference or source document provided to ground assertions."
            })
            flagged.append(s)
        return {
            "score": 3,
            "reasoning": "No context provided. Potential hallucination risk is moderate due to lack of grounding context.",
            "claims_analysis": claims_analysis,
            "flagged_statements": flagged
        }
        
    ref_filtered = get_filtered_words(ref_text, question)
    
    for s in sentences:
        s_filtered = get_filtered_words(s, question)
        if not s_filtered:
            claims_analysis.append({
                "claim": s,
                "status": "Grounded",
                "explanation": "Contains standard query/helper words only."
            })
            continue
            
        matches = s_filtered.intersection(ref_filtered)
        ratio = len(matches) / len(s_filtered)
        
        # Groundedness checks if claims are supported.
        # If overlap ratio of new content terms is above 25%, it is Grounded.
        if ratio >= 0.25:
            claims_analysis.append({
                "claim": s,
                "status": "Grounded",
                "explanation": f"Grounded: {int(ratio*100)}% of content keywords match retrieved source chunks."
            })
        else:
            claims_analysis.append({
                "claim": s,
                "status": "Hallucinated",
                "explanation": "Hallucinated: No matching supporting evidence found in the retrieved context."
            })
            flagged.append(s)
            
    hallucinated_count = len(flagged)
    ratio_grounded = 1.0 - (hallucinated_count / max(len(sentences), 1))
    
    if ratio_grounded == 1.0:
        score = 5
        reasoning = "Perfect groundedness. No ungrounded claims or hallucinated statements detected."
    elif ratio_grounded >= 0.7:
        score = 4
        reasoning = "High groundedness. The main claims are fully supported, with only minor auxiliary details ungrounded."
    elif ratio_grounded >= 0.4:
        score = 3
        reasoning = "Moderate hallucination. Multiple distinct statements are unsupported by retrieved contexts."
    else:
        score = 1
        reasoning = f"Severe hallucination detected. The following statements are ungrounded: {', '.join(flagged[:2])}"
        
    return {
        "score": score,
        "reasoning": reasoning,
        "claims_analysis": claims_analysis,
        "flagged_statements": flagged
    }

def run_heuristic_completeness(question: str, ai_response: str) -> dict:
    q_len = len(question.split())
    r_len = len(ai_response.split())
    
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
            Evaluate whether the AI Response directly and relevantly answers the Question, ignoring correctness/factuality.
            Rate from 1 (completely irrelevant) to 5 (perfectly relevant).
            
            Rubric:
            1: Off-topic. No semantic alignment.
            2: Contextual mismatch. Mentions keywords but answers a different query.
            3: Partial fit. Addresses part of the question but misses key constraints.
            4: High relevance. Fully answers query with minor irrelevant details.
            5: Perfect alignment. Direct, clear, and perfectly targeted response.

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
            
            Extract the list of facts that matched the reference, and list any facts that mismatched or contradicted the reference.
            
            Respond strictly in JSON format matching this schema:
            {{
              "score": int, 
              "reasoning": "str",
              "matched_facts": ["str"],
              "mismatched_facts": ["str"]
            }}
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
            
            Break down the AI Response into individual sentences/claims. For each claim, determine if it is "Grounded" or "Hallucinated".
            List any flagged ungrounded statements.
            
            Respond strictly in JSON format matching this schema:
            {{
              "score": int, 
              "reasoning": "str",
              "claims_analysis": [
                {{"claim": "str", "status": "Grounded" | "Hallucinated", "explanation": "str"}}
              ],
              "flagged_statements": ["str"]
            }}
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
    acc_res = run_heuristic_accuracy(ai_response, reference, source_doc, question)
    hal_res = run_heuristic_hallucination(ai_response, reference, source_doc, question)
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
