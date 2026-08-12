import os
import re
import requests
import uuid
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import init_db, get_db, CandidateSession, TranscriptRecord, CodeSubmissionRecord, AssessmentReport
from backend.code_runner import execute_code

app = FastAPI(
    title="InterviewPro AI Enterprise API Server",
    version="5.0.0",
    description="Production REST API backend for AI mock interviews, transcript evaluation, code execution, and database persistence."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB tables on startup
@app.on_event("startup")
def startup_event():
    init_db()

# Pydantic Schemas
class StartSessionRequest(BaseModel):
    company: str = "Amazon"
    role: str = "Senior Software Engineer"
    experience: str = "Mid-Level"
    persona_id: str = "dm"
    resume_text: Optional[str] = ""

class AnswerRequest(BaseModel):
    session_id: str
    round_index: int = 0
    question: str
    answer: str

class CodeCompileRequest(BaseModel):
    session_id: str
    language: str
    code: str

# REST ENDPOINTS

@app.get("/api/health")
def health_check():
    return {"status": "online", "version": "5.0.0", "backend": "FastAPI + SQLite"}

@app.post("/api/session/start")
def start_session(req: StartSessionRequest, db: Session = Depends(get_db)):
    session_id = str(uuid.uuid4())[:8]
    new_session = CandidateSession(
        id=session_id,
        company=req.company,
        role=req.role,
        experience=req.experience,
        persona_id=req.persona_id
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    initial_question = (
        f"Welcome to your {req.company} interview! I'm your executive interviewer. "
        "To start off, please introduce yourself — tell me about your background, what you studied or work on, and your journey in technology."
    )

    return {
        "session_id": session_id,
        "company": req.company,
        "role": req.role,
        "initial_question": initial_question
    }

def generate_adaptive_followup(company: str, role: str, history: list, current_question: str, answer: str) -> str:
    ans_text = answer.strip()
    ans_lower = ans_text.lower()
    words = ans_text.split()
    word_count = len(words)
    
    # Check for LLM API Keys (OpenAI / Gemini) for 100% realistic AI interviewer
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if openai_key:
        try:
            prompt = (
                f"You are a Senior Technical Interviewer conducting a 1-on-1 placement interview at {company} for a {role}.\n"
                f"Previous Interview Question: \"{current_question}\"\n"
                f"Candidate's Full Answer: \"{ans_text}\"\n\n"
                f"Instructions:\n"
                f"1. Read the candidate's answer carefully.\n"
                f"2. Ask a precise, 1-to-1 follow-up question based directly on a specific technical claim, architecture choice, or detail they mentioned.\n"
                f"3. Do NOT ask a generic or pre-scripted question.\n"
                f"4. Keep your question concise, professional, and natural (1-3 sentences max).\n"
            )
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "system", "content": "You are a professional tech interviewer."}, {"role": "user", "content": prompt}],
                    "max_tokens": 150,
                    "temperature": 0.7
                },
                timeout=5
            )
            if resp.status_code == 200:
                ai_q = resp.json()["choices"][0]["message"]["content"].strip()
                if ai_q: return ai_q
        except Exception:
            pass

    # High-precision Rule & Keyword Extraction Engine
    tech_keywords = {
        "react": "React frontend",
        "next.js": "Next.js SSR framework",
        "node": "Node.js runtime",
        "python": "Python backend",
        "django": "Django ORM framework",
        "fastapi": "FastAPI async services",
        "c++": "C++ native engine",
        "cpp": "C++ native engine",
        "java": "Java enterprise backend",
        "golang": "Go concurrency model",
        "go": "Go microservices",
        "sql": "relational SQL schema",
        "postgres": "PostgreSQL database",
        "mongo": "MongoDB NoSQL store",
        "redis": "Redis cache",
        "docker": "Docker containers",
        "kubernetes": "Kubernetes orchestration",
        "kafka": "Kafka event streams",
        "rabbitmq": "RabbitMQ queue",
        "aws": "AWS cloud infra",
        "microservices": "microservice architecture",
        "websocket": "WebSocket bi-directional streams",
        "graphql": "GraphQL schema design",
        "rest": "REST API design",
        "sharding": "database sharding",
        "indexing": "database indexing",
        "concurrency": "concurrent thread handling",
        "latency": "low-latency optimization",
        "ci/cd": "CI/CD automated deployment pipeline"
    }

    found_tech = []
    for k, v in tech_keywords.items():
        if re.search(r'\b' + re.escape(k) + r'\b', ans_lower):
            found_tech.append((k, v))

    # Extract dynamic key phrases from candidate answer for quote-mirroring
    phrase_match = re.search(r'(built|developed|designed|implemented|worked on|managed|used|created)\s+([a-zA-Z0-9\s,-]+?)(?=\.|\,|and|$)', ans_text, re.IGNORECASE)
    extracted_phrase = phrase_match.group(2).strip() if phrase_match and len(phrase_match.group(2).strip().split()) <= 6 else None

    # Handle short or incomplete answers (< 8 words)
    if word_count < 8:
        if found_tech:
            return f"You mentioned {found_tech[0][1]}, but your answer was quite brief. Could you walk me through your exact implementation and your specific role in that project?"
        return f"That was quite a short answer. Could you elaborate with a concrete technical example from your past engineering experience?"

    # Contextual Round-based & Technical Follow-ups
    q_lower = current_question.lower()
    round_count = len(history)

    # Round 1: Intro -> Company & Role Alignment
    if ("introduce" in q_lower or "background" in q_lower) and round_count <= 1:
        if found_tech:
            tech_str = " and ".join([t[1] for t in found_tech[:2]])
            return f"Thank you for sharing your background in {tech_str}. Why specifically are you excited to join {company} as a {role}, and how do your skills align with our scale?"
        return f"Thanks for introducing yourself! What specifically motivates you to join {company} as a {role}, and what engineered system are you most proud of?"

    # Round 2: Project Deep Dive & Technical Choices
    if extracted_phrase and len(extracted_phrase) > 5:
        return f"You mentioned that you {phrase_match.group(1).lower()} {extracted_phrase}. What technical trade-offs did you evaluate when making those design choices, and what was the main bottleneck under peak load?"

    # Specific Technology Deep Dives
    if found_tech:
        primary_tech = found_tech[0][0]
        if primary_tech in ["redis", "cache"]:
            return f"Regarding your use of {found_tech[0][1]}, how did you handle cache invalidation, TTL expiration, and cache stampedes under high concurrency?"
        elif primary_tech in ["kafka", "rabbitmq", "microservices"]:
            return f"Deep diving into your {found_tech[0][1]}, how did you ensure transactional message consistency and handle service failures gracefully?"
        elif primary_tech in ["postgres", "sql", "mongo", "sharding", "indexing"]:
            return f"Focusing on your {found_tech[0][1]}, when database query traffic spikes 10x, how do you optimize index structures and prevent connection pool starvation?"
        elif primary_tech in ["docker", "kubernetes", "aws", "ci/cd"]:
            return f"Given your experience with {found_tech[0][1]}, how did you handle zero-downtime rolling deployments, health checks, and automated rollback triggers?"
        elif primary_tech in ["websocket", "rest", "graphql"]:
            return f"Regarding your {found_tech[0][1]}, how did you enforce authentication, rate limiting, and connection management under high concurrent active connections?"
        else:
            return f"You highlighted {found_tech[0][1]}. What were the primary performance metrics or latency SLAs you maintained, and how did you profile bottlenecks?"

    # Handling challenges & bug fixes
    if any(w in ans_lower for w in ["challenge", "bug", "issue", "failure", "bottleneck", "down", "error"]):
        return f"That sounds like a critical production issue. What specific telemetry, logging, or profiling tools did you use to diagnose the root cause, and how did you ensure long-term stability?"

    # High-scale system design follow-up
    return f"Thank you for that detailed explanation. Building on what you just shared, if we scaled this workload to 100,000 requests per second at {company}, what part of your design would fail first and how would you re-architect it?"

@app.post("/api/session/answer")
def process_answer(req: AnswerRequest, db: Session = Depends(get_db)):
    session = db.query(CandidateSession).filter(CandidateSession.id == req.session_id).first()
    company_name = session.company if session else "Amazon"
    role_name = session.role if session else "Senior Software Engineer"

    words = req.answer.strip().split()
    tech_keywords = ["react", "node", "python", "cpp", "java", "sql", "postgres", "mongo", "redis", "docker", "kubernetes", "kafka", "aws", "microservices", "api", "graphql", "algorithm"]
    detected = [k for k in tech_keywords if k in req.answer.lower()]

    score = 70
    if len(words) > 15: score += 10
    if len(words) > 35: score += 10
    score += min(len(detected) * 4, 20)
    score = max(50, min(100, score))

    record = TranscriptRecord(
        session_id=req.session_id,
        round_index=req.round_index,
        question=req.question,
        answer=req.answer,
        score=score,
        tech_keywords=", ".join(detected)
    )
    db.add(record)
    db.commit()

    # Retrieve prior session history for context
    history = db.query(TranscriptRecord).filter(TranscriptRecord.session_id == req.session_id).all()

    # Generate dynamic context-aware follow-up question
    follow_up = generate_adaptive_followup(company_name, role_name, history, req.question, req.answer)

    return {
        "score": score,
        "detected_keywords": detected,
        "follow_up_question": follow_up
    }

@app.post("/api/code/compile")
def compile_code(req: CodeCompileRequest, db: Session = Depends(get_db)):
    res = execute_code(req.language, req.code)
    
    submission = CodeSubmissionRecord(
        session_id=req.session_id,
        language=req.language,
        code=req.code,
        execution_time_ms=res.get("execution_time_ms", 0.0),
        passed_tests=1 if res.get("success") else 0,
        complexity_rating=res.get("complexity", "O(N)")
    )
    db.add(submission)
    db.commit()

    return res

@app.get("/api/report/{session_id}")
def get_report(session_id: str, db: Session = Depends(get_db)):
    transcripts = db.query(TranscriptRecord).filter(TranscriptRecord.session_id == session_id).all()
    
    if not transcripts:
        avg_score = 82
    else:
        avg_score = round(sum(t.score for t in transcripts) / len(transcripts))

    verdict = "STRONG HIRE" if avg_score >= 85 else ("HIRE" if avg_score >= 75 else "LEAN HIRE")

    return {
        "session_id": session_id,
        "overall_score": avg_score,
        "verdict": verdict,
        "tech_score": min(98, avg_score + 3),
        "prob_score": avg_score,
        "code_score": 88,
        "comm_score": min(95, avg_score + 2),
        "star_score": min(92, avg_score - 2),
        "conf_score": min(96, avg_score + 4),
        "lead_score": min(90, avg_score),
        "arch_score": min(94, avg_score + 1),
        "transcript_count": len(transcripts)
    }

# Serve frontend root and HTML launchers
@app.get("/")
@app.get("/index.html")
@app.get("/static/index.html")
@app.get("/interviewpro_ai_app.html")
def read_index():
    standalone_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "interviewpro_ai_app.html")
    if os.path.exists(standalone_path):
        return FileResponse(standalone_path)
    index_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "InterviewPro AI API Server Online"}

# Mount static frontend assets
frontend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=os.path.join(frontend_path, "static")), name="static")

