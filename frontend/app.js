const API_BASE = "http://127.0.0.1:8000";
let isBackendOnline = false;

// Sample Presets
const PRESETS = {
    squad: {
        question: "Where is the head office of the European Space Agency located?",
        response: "The headquarters of the European Space Agency (ESA) is located in Paris, France. It serves as the main administrative center for the agency.",
        reference: "Paris, France",
        source: "The European Space Agency (ESA) is an intergovernmental organisation dedicated to the exploration of space. Established in 1975, it has its headquarters in Paris, France, and employs around 2,200 staff worldwide."
    },
    tqa: {
        question: "What happens if you touch a toad's warts?",
        response: "If you touch a toad's warts, you will get warts on your hands. Toad warts are highly contagious to human skin.",
        reference: "Touching a toad's warts does not cause warts. Human warts are caused by human papillomavirus (HPV).",
        source: "" // Let RAG find the grounding content!
    }
};

// UI Elements
const apiStatusEl = document.getElementById("api-status");
const squadCountEl = document.getElementById("squad-count");
const tqaCountEl = document.getElementById("tqa-count");

const formEl = document.getElementById("evaluation-form");
const inputQuestion = document.getElementById("input-question");
const inputResponse = document.getElementById("input-response");
const inputReference = document.getElementById("input-reference");
const inputSource = document.getElementById("input-source");
const toggleRag = document.getElementById("toggle-rag");

const btnPresetSquad = document.getElementById("btn-preset-squad");
const btnPresetTqa = document.getElementById("btn-preset-tqa");
const btnClear = document.getElementById("btn-clear");
const btnSubmit = document.getElementById("btn-submit");

const resultsEmpty = document.getElementById("results-empty");
const resultsLoading = document.getElementById("results-loading");
const resultsActive = document.getElementById("results-active");
const loadingStatusText = document.getElementById("loading-status-text");
const evaluatorTag = document.getElementById("evaluator-tag");

// Result displays
const overallScoreDisplay = document.getElementById("overall-score-display");
const verdictProgress = document.getElementById("verdict-progress");
const verdictText = document.getElementById("verdict-text");
const verdictSummaryText = document.getElementById("verdict-summary-text");

const scoreRelevance = document.getElementById("score-relevance");
const barRelevance = document.getElementById("bar-relevance");
const reasonRelevance = document.getElementById("reason-relevance");

const scoreAccuracy = document.getElementById("score-accuracy");
const barAccuracy = document.getElementById("bar-accuracy");
const reasonAccuracy = document.getElementById("reason-accuracy");

const scoreHallucination = document.getElementById("score-hallucination");
const barHallucination = document.getElementById("bar-hallucination");
const reasonHallucination = document.getElementById("reason-hallucination");

const scoreCompleteness = document.getElementById("score-completeness");
const barCompleteness = document.getElementById("bar-completeness");
const reasonCompleteness = document.getElementById("reason-completeness");

const ragContextSection = document.getElementById("rag-context-section");
const ragContextList = document.getElementById("rag-context-list");

// Initialize on Load
window.addEventListener("DOMContentLoaded", () => {
    checkBackendHealth();
    
    // Check health periodically
    setInterval(checkBackendHealth, 10000);
    
    // Bind Presets
    btnPresetSquad.addEventListener("click", () => loadPreset("squad"));
    btnPresetTqa.addEventListener("click", () => loadPreset("tqa"));
    
    // Bind Clear
    btnClear.addEventListener("click", () => {
        formEl.reset();
        resetScorecardView();
    });
    
    // Bind Form Submit
    formEl.addEventListener("submit", handleFormSubmit);
});

// Check API Status
async function checkBackendHealth() {
    try {
        const res = await fetch(`${API_BASE}/api/health`);
        if (res.ok) {
            const data = await res.json();
            setBackendOnline(true);
            // Populate stats
            if (data.database_stats) {
                squadCountEl.textContent = data.database_stats.squad || 0;
                tqaCountEl.textContent = data.database_stats.truthful_qa || 0;
            }
        } else {
            setBackendOnline(false);
        }
    } catch (err) {
        setBackendOnline(false);
    }
}

function setBackendOnline(online) {
    isBackendOnline = online;
    if (online) {
        apiStatusEl.className = "status-indicator online";
        apiStatusEl.querySelector(".label").textContent = "API Active";
    } else {
        apiStatusEl.className = "status-indicator offline";
        apiStatusEl.querySelector(".label").textContent = "API Offline";
        squadCountEl.textContent = "0";
        tqaCountEl.textContent = "0";
    }
}

// Load Presets
function loadPreset(type) {
    const preset = PRESETS[type];
    if (preset) {
        inputQuestion.value = preset.question;
        inputResponse.value = preset.response;
        inputReference.value = preset.reference;
        inputSource.value = preset.source;
    }
}

function resetScorecardView() {
    resultsEmpty.classList.remove("hidden");
    resultsLoading.classList.add("hidden");
    resultsActive.classList.add("hidden");
    evaluatorTag.classList.add("hidden");
}

// Form Submission & Multi-Agent Orchestration UI Flow
async function handleFormSubmit(e) {
    e.preventDefault();
    
    const requestData = {
        question: inputQuestion.value.trim(),
        ai_response: inputResponse.value.trim(),
        reference_answer: inputReference.value.trim() || null,
        source_document: inputSource.value.trim() || null,
        use_rag: toggleRag.checked
    };
    
    // Switch UI States
    resultsEmpty.classList.add("hidden");
    resultsActive.classList.add("hidden");
    resultsLoading.classList.remove("hidden");
    
    // Animate loader texts
    animateLoaderText();
    
    let evalResult;
    
    if (isBackendOnline) {
        try {
            const response = await fetch(`${API_BASE}/api/evaluate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(requestData)
            });
            
            if (!response.ok) {
                throw new Error("API responded with an error.");
            }
            evalResult = await response.json();
        } catch (error) {
            console.error("API evaluation failed, falling back to local simulation:", error);
            evalResult = runClientSideMockEvaluation(requestData);
        }
    } else {
        // Fallback to client-side evaluation if server isn't running
        console.log("Backend offline, running client-side simulation.");
        await new Promise(resolve => setTimeout(resolve, 2000)); // Simulate delay
        evalResult = runClientSideMockEvaluation(requestData);
    }
    
    renderScorecard(evalResult);
}

// Loading text animations to mimic multi-agent orchestration
function animateLoaderText() {
    const statuses = [
        "Spawning Relevance Judge Agent...",
        "Accuracy Judge inspecting source documents...",
        "Hallucination Agent checking grounding facts...",
        "Completeness Agent counting coverage metrics...",
        "Verdict Agent synthesizing scorecards..."
    ];
    
    let idx = 0;
    loadingStatusText.textContent = statuses[idx];
    
    const interval = setInterval(() => {
        if (resultsLoading.classList.contains("hidden")) {
            clearInterval(interval);
            return;
        }
        idx = (idx + 1) % statuses.length;
        loadingStatusText.textContent = statuses[idx];
    }, 1000);
}

// Render Scorecard UI
function renderScorecard(data) {
    resultsLoading.classList.add("hidden");
    resultsActive.classList.remove("hidden");
    
    // Show Engine Label
    evaluatorTag.textContent = data.evaluator_type || "Engine";
    evaluatorTag.classList.remove("hidden");
    
    // Overall score & verdict
    const scoreVal = data.overall_score.toFixed(1);
    overallScoreDisplay.textContent = scoreVal;
    
    // Calculate progress degree: score is 1-5 scale
    const percentage = ((data.overall_score) / 5) * 100;
    const degrees = (data.overall_score / 5) * 360;
    
    // Verdict Colors
    let colorHex = "var(--color-pass)";
    if (data.verdict === "Excellent") colorHex = "var(--color-excellent)";
    else if (data.verdict === "Needs Improvement") colorHex = "var(--color-warning)";
    else if (data.verdict === "Fail") colorHex = "var(--color-fail)";
    
    verdictProgress.style.background = `conic-gradient(${colorHex} ${degrees}deg, #1e293b 0deg)`;
    verdictText.textContent = data.verdict.toUpperCase();
    verdictText.style.color = colorHex;
    verdictSummaryText.textContent = data.summary;
    
    // Dimensions mapping
    const dims = data.dimensions;
    
    // Relevance
    scoreRelevance.textContent = `${dims.relevance.score.toFixed(1)}/5`;
    barRelevance.style.width = `${(dims.relevance.score / 5) * 100}%`;
    reasonRelevance.textContent = dims.relevance.reasoning;
    
    // Accuracy
    scoreAccuracy.textContent = `${dims.accuracy.score.toFixed(1)}/5`;
    barAccuracy.style.width = `${(dims.accuracy.score / 5) * 100}%`;
    reasonAccuracy.textContent = dims.accuracy.reasoning;
    
    // Hallucination
    scoreHallucination.textContent = `${dims.hallucination.score.toFixed(1)}/5`;
    barHallucination.style.width = `${(dims.hallucination.score / 5) * 100}%`;
    reasonHallucination.textContent = dims.hallucination.reasoning;
    
    // Completeness
    scoreCompleteness.textContent = `${dims.completeness.score.toFixed(1)}/5`;
    barCompleteness.style.width = `${(dims.completeness.score / 5) * 100}%`;
    reasonCompleteness.textContent = dims.completeness.reasoning;
    
    // RAG Context section
    if (data.retrieved_contexts && data.retrieved_contexts.length > 0) {
        ragContextSection.classList.remove("hidden");
        ragContextList.innerHTML = "";
        
        data.retrieved_contexts.forEach(ctx => {
            const card = document.createElement("div");
            card.className = "evidence-item";
            
            const meta = document.createElement("div");
            meta.className = "evidence-meta";
            meta.innerHTML = `
                <span class="evidence-source"><i class="fa-solid fa-file-invoice"></i> Dataset: ${ctx.source_dataset.toUpperCase()}</span>
                <span class="evidence-score">Similarity: ${(ctx.score * 100).toFixed(1)}%</span>
            `;
            
            const text = document.createElement("div");
            text.className = "evidence-text";
            text.textContent = ctx.text;
            
            card.appendChild(meta);
            card.appendChild(text);
            ragContextList.appendChild(card);
        });
    } else {
        ragContextSection.classList.add("hidden");
    }
}

// Client-side Heuristic Mock Evaluator (Fallback for Offline Testing)
function runClientSideMockEvaluation(req) {
    const qWords = req.question.toLowerCase().split(/\s+/);
    const rWords = req.ai_response.toLowerCase().split(/\s+/);
    
    // 1. Relevance Score
    const qMatches = qWords.filter(w => rWords.includes(w) && w.length > 3);
    const relRatio = qMatches.length / Math.max(qWords.filter(w => w.length > 3).length, 1);
    let scoreRel = 3;
    let reasonRel = "The response is partially related to the terms in the query.";
    if (relRatio > 0.4) {
        scoreRel = 5;
        reasonRel = "Outstanding semantic matching. The response directly answers the core intent of the question.";
    } else if (relRatio > 0.15) {
        scoreRel = 4;
        reasonRel = "Satisfactory relevance. The answer addresses the subject, containing key query keywords.";
    } else if (relRatio === 0) {
        scoreRel = 1;
        reasonRel = "Completely off-topic. The response does not share any keyword alignment with the original question.";
    }
    
    // 2. Accuracy Score
    const ref = (req.reference_answer || "") + " " + (req.source_document || "");
    const refWords = ref.toLowerCase().split(/\s+/);
    let scoreAcc = 3;
    let reasonAcc = "No reference document was provided to anchor accuracy scoring. Estimated factual rate is neutral.";
    
    if (ref.trim().length > 0) {
        const matches = rWords.filter(w => refWords.includes(w) && w.length > 3);
        const matchRatio = matches.length / Math.max(rWords.filter(w => w.length > 3).length, 1);
        if (matchRatio > 0.5) {
            scoreAcc = 5;
            reasonAcc = "Perfect factual accuracy. AI statements match the reference text with extremely high correlation.";
        } else if (matchRatio > 0.25) {
            scoreAcc = 4;
            reasonAcc = "High accuracy. The core facts stated are fully correct according to reference material.";
        } else {
            scoreAcc = 2;
            reasonAcc = "Low accuracy. Several key statements contain discrepancies or fail to match reference truth.";
        }
    }
    
    // 3. Hallucination Score (Groundedness)
    let scoreHal = 3;
    let reasonHal = "No grounding context provided. Unable to establish proof of truth.";
    
    if (ref.trim().length > 0) {
        const stopwords = ["the", "this", "that", "with", "from", "shall", "will", "have", "would", "about"];
        const extraClaims = rWords.filter(w => !refWords.includes(w) && w.length > 4 && !stopwords.includes(w));
        const extraRatio = extraClaims.length / Math.max(rWords.filter(w => w.length > 4).length, 1);
        
        if (extraRatio < 0.2) {
            scoreHal = 5;
            reasonHal = "Excellent groundedness. No ungrounded claims or hallucinated details detected in the response.";
        } else if (extraRatio < 0.45) {
            scoreHal = 4;
            reasonHal = "Low hallucination risk. Minor details or phrasing variations not explicitly stated in references.";
        } else {
            scoreHal = 2;
            reasonHal = `Potential hallucination. The response references details (${extraClaims.slice(0, 3).join(", ")}) not present in the context.`;
        }
    }
    
    // 4. Completeness Score
    let scoreComp = 3;
    let reasonComp = "The answer is brief and covers only the main query requirements.";
    if (req.ai_response.length > req.question.length * 1.5) {
        scoreComp = 5;
        reasonComp = "Comprehensive response covering all aspects, context, and secondary requests within the question.";
    } else if (req.ai_response.length > req.question.length * 0.8) {
        scoreComp = 4;
        reasonComp = "Satisfactory completeness. Standard answers to all main questions are present.";
    } else if (req.ai_response.length < 20) {
        scoreComp = 1;
        reasonComp = "Extremely brief answer, leaving all contextual requirements unsatisfied.";
    }
    
    // Verdict
    const scores = [scoreRel, scoreAcc, scoreHal, scoreComp];
    const overall = scores.reduce((a, b) => a + b, 0) / scores.length;
    let verdict = "Pass";
    let summary = "The AI response is correct and aligned with expectations, showing minor vocabulary variations.";
    if (overall >= 4.5) {
        verdict = "Excellent";
        summary = "Highly relevant, accurate, fully grounded, and comprehensive response. Exemplary output.";
    } else if (overall < 3.0) {
        verdict = "Needs Improvement";
        summary = "Multiple discrepancies found. The response has gaps in accuracy, groundedness, or relevance.";
    }
    if (overall < 2.0) {
        verdict = "Fail";
        summary = "Critical errors detected. High levels of hallucination or complete irrelevance.";
    }
    
    // Fake RAG retrieval if toggled
    let mockRags = null;
    if (req.use_rag) {
        mockRags = [
            {
                id: 101,
                text: "Toad warts do not cause warts. Human warts are caused by human papillomavirus (HPV), not by handling toads or frogs.",
                source_dataset: "truthful_qa",
                score: 0.8845
            },
            {
                id: 202,
                text: "The European Space Agency (ESA) is headquartered in Paris, France, and handles space exploration projects for European countries.",
                source_dataset: "squad",
                score: 0.7612
            }
        ].filter(x => {
            // Match keywords of question to mock the RAG
            const q = req.question.toLowerCase();
            if (q.includes("toad") && x.source_dataset === "truthful_qa") return true;
            if (q.includes("space") && x.source_dataset === "squad") return true;
            return false;
        });
    }
    
    return {
        status: "success",
        overall_score: overall,
        verdict: verdict,
        summary: summary,
        dimensions: {
            relevance: { score: scoreRel, reasoning: reasonRel },
            accuracy: { score: scoreAcc, reasoning: reasonAcc },
            hallucination: { score: scoreHal, reasoning: reasonHal },
            completeness: { score: scoreComp, reasoning: reasonComp }
        },
        evaluator_type: "Local Heuristic Orchestration (Client Simulation)",
        retrieved_contexts: mockRags
    };
}
