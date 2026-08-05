import uuid
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

@app.post("/api/session/answer")
def process_answer(req: AnswerRequest, db: Session = Depends(get_db)):
    session = db.query(CandidateSession).filter(CandidateSession.id == req.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

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

    # Dynamic follow-up generation
    follow_up = "Thank you. Let's move to the next part of our discussion."
    if "background" in req.question.lower():
        follow_up = f"That is a great background overview. Why specifically do you want to join {session.company}, and what excites you about our engineering culture?"
    elif "why" in req.question.lower() or "motivation" in req.question.lower():
        follow_up = "Appreciate your passion! Walk me through your most impactful project. What architecture did you choose, what was your role, and what challenges arose?"
    elif any(k in req.answer.lower() for k in ["react", "python", "node", "docker", "postgres"]):
        follow_up = "Solid technical detail. In that system, how did you handle state management, caching, or performance bottlenecks under high QPS?"

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

# Mount static frontend files if folder exists
frontend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=os.path.join(frontend_path, "static")), name="static")
