"""
ResumeFlow Interview Studio — FastAPI Backend
Resume-based voice interview platform.
"""

import os
import uuid
import json
import tempfile
import shutil
from datetime import datetime
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import (
    init_db, get_db,
    Resume, InterviewSession, InterviewQuestion,
    InterviewAnswer, InterviewTranscript, InterviewEvaluation,
)
from backend.models import (
    CandidateProfile, StartInterviewRequest, SubmitAnswerRequest,
    EndInterviewRequest, ResumeUpdateRequest,
)
from backend.resume_parser import parse_resume, parse_resume_text
from backend.interview_generator import (
    generate_interview_questions, generate_followup, should_ask_followup,
)
from backend.evaluator import score_answer, evaluate_full_interview
from backend.pdf_generator import (
    HAS_REPORTLAB, generate_pdf_report,
    generate_transcript_txt, generate_transcript_json,
)

app = FastAPI(
    title="ResumeFlow Interview Studio API",
    version="1.0.0",
    description="Resume-based voice interview platform for career assessment and coaching.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    init_db()


# ── Health Check ───────────────────────────────────────────────────────

@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "version": "1.0.0",
        "platform": "ResumeFlow Interview Studio",
    }


# ── Resume Upload & Parsing ────────────────────────────────────────────

@app.post("/api/resume/upload")
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload and parse a resume file (PDF, DOCX, TXT)."""
    # Validate file type
    allowed_types = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "text/plain": "txt",
    }

    # Also check file extension
    ext_map = {"pdf": "pdf", "docx": "docx", "txt": "txt"}
    filename = file.filename or "resume"
    file_ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if file.content_type in allowed_types:
        file_type = allowed_types[file.content_type]
    elif file_ext in ext_map:
        file_type = ext_map[file_ext]
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload PDF, DOCX, or TXT files."
        )

    # Validate file size (max 10MB)
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit.")

    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Save to temp file for parsing
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        parsed = parse_resume(tmp_path, file_type, filename)
    finally:
        os.unlink(tmp_path)

    raw_text = parsed.get("raw_text", "")
    profile = parsed.get("profile", {})

    if not raw_text:
        raise HTTPException(
            status_code=400,
            detail="Could not extract text from the uploaded file. Please try a different format."
        )

    # Create resume record
    resume_id = str(uuid.uuid4())[:12]
    resume = Resume(
        id=resume_id,
        candidate_name=profile.get("name", ""),
        filename=filename,
        file_type=file_type,
        raw_text=raw_text,
        parsed_json=json.dumps(profile, default=str),
    )
    db.add(resume)
    db.commit()

    return {
        "resume_id": resume_id,
        "candidate_name": profile.get("name", ""),
        "filename": filename,
        "profile": profile,
        "message": "Resume uploaded and parsed successfully.",
    }


class TextUploadRequest(BaseModel):
    resume_text: str
    filename: str = "resume.txt"


@app.post("/api/resume/upload-text")
def upload_resume_text(req: TextUploadRequest, db: Session = Depends(get_db)):
    """Upload resume as raw text (for testing and text paste)."""
    raw_text = req.resume_text.strip()
    if not raw_text:
        raise HTTPException(status_code=400, detail="Resume text is empty.")
    if len(raw_text) > 500_000:
        raise HTTPException(status_code=400, detail="Resume text exceeds 500K characters.")

    parsed = parse_resume_text(raw_text)
    profile = parsed.get("profile", {})

    resume_id = str(uuid.uuid4())[:12]
    resume = Resume(
        id=resume_id,
        candidate_name=profile.get("name", ""),
        filename=req.filename,
        file_type="txt",
        raw_text=raw_text,
        parsed_json=json.dumps(profile, default=str),
    )
    db.add(resume)
    db.commit()

    return {
        "resume_id": resume_id,
        "candidate_name": profile.get("name", ""),
        "filename": req.filename,
        "profile": profile,
        "message": "Resume text parsed successfully.",
    }


@app.get("/api/resume/{resume_id}")
def get_resume(resume_id: str, db: Session = Depends(get_db)):
    """Get parsed resume data."""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    profile = json.loads(resume.parsed_json) if resume.parsed_json else {}
    return {
        "resume_id": resume.id,
        "candidate_name": resume.candidate_name,
        "filename": resume.filename,
        "file_type": resume.file_type,
        "raw_text": resume.raw_text[:5000],  # Limit for API response
        "profile": profile,
    }


@app.put("/api/resume/{resume_id}")
def update_resume(resume_id: str, req: ResumeUpdateRequest, db: Session = Depends(get_db)):
    """Update parsed resume information after user review."""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    profile_dict = req.profile.model_dump()
    resume.parsed_json = json.dumps(profile_dict, default=str)
    if profile_dict.get("name"):
        resume.candidate_name = profile_dict["name"]

    db.commit()
    return {
        "resume_id": resume.id,
        "profile": profile_dict,
        "message": "Resume information updated successfully.",
    }


# ── Interview Session Management ───────────────────────────────────────

@app.post("/api/interview/start")
def start_interview(req: StartInterviewRequest, db: Session = Depends(get_db)):
    """Start a new interview session based on the resume."""
    resume = db.query(Resume).filter(Resume.id == req.resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    profile = json.loads(resume.parsed_json) if resume.parsed_json else {}
    profile = json.loads(json.dumps(profile, default=str))

    # Generate interview questions
    questions = generate_interview_questions(profile, resume.raw_text)
    if not questions:
        raise HTTPException(status_code=500, detail="Failed to generate interview questions.")

    # Create session
    session_id = str(uuid.uuid4())[:12]
    session = InterviewSession(
        id=session_id,
        resume_id=req.resume_id,
        status="in_progress",
        started_at=datetime.utcnow(),
        total_questions=len(questions),
    )
    db.add(session)
    db.flush()

    # Create question records
    created_questions = []
    for i, q in enumerate(questions):
        question = InterviewQuestion(
            session_id=session_id,
            question_index=i,
            question_text=q["question_text"],
            category=q.get("category", "general"),
            rubric_json=json.dumps(q.get("rubric", {}), default=str),
            is_followup=False,
        )
        db.add(question)
        db.flush()
        created_questions.append({
            "question_id": question.id,
            "question_index": question.question_index,
            "question_text": question.question_text,
            "category": question.category,
            "is_followup": False,
        })

    db.commit()

    # Welcome message — conversational, like a real interviewer
    name = profile.get("name", "")
    welcome = (
        f"{'Hi ' + name + '. ' if name else 'Hi there. '}"
        "Welcome. I've looked over your resume and I have a few questions "
        "I'd like to go through with you. This is a practice session, "
        "so take your time and don't worry about getting things perfect. "
        "If you'd like me to repeat anything, just say so. "
        "Let's get started."
    )

    # Add system transcript
    transcript = InterviewTranscript(
        session_id=session_id,
        segment_type="system",
        text=welcome,
    )
    db.add(transcript)

    # Add first question transcript
    if created_questions:
        first_q = created_questions[0]
        q_transcript = InterviewTranscript(
            session_id=session_id,
            segment_type="question",
            text=first_q["question_text"],
        )
        db.add(q_transcript)

    db.commit()

    return {
        "session_id": session_id,
        "welcome_message": welcome,
        "first_question": created_questions[0] if created_questions else None,
        "total_questions": len(created_questions),
        "questions": created_questions,
    }


@app.get("/api/interview/{session_id}")
def get_interview_status(session_id: str, db: Session = Depends(get_db)):
    """Get current interview session status."""
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found.")

    questions = db.query(InterviewQuestion).filter(
        InterviewQuestion.session_id == session_id
    ).order_by(InterviewQuestion.question_index).all()

    answers = db.query(InterviewAnswer).filter(
        InterviewAnswer.session_id == session_id
    ).all()

    transcripts = db.query(InterviewTranscript).filter(
        InterviewTranscript.session_id == session_id
    ).order_by(InterviewTranscript.id).all()

    # Calculate completion
    main_questions = [q for q in questions if not q.is_followup]
    answered_count = len(set(a.question_id for a in answers))
    total_main = len(main_questions) if main_questions else 1
    completion = min(100, round((answered_count / total_main) * 100)) if main_questions else 0

    return {
        "session_id": session.id,
        "status": session.status,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "total_questions": session.total_questions,
        "answered_count": answered_count,
        "completion_percentage": completion,
        "questions": [
            {
                "question_id": q.id,
                "question_index": q.question_index,
                "question_text": q.question_text,
                "category": q.category,
                "is_followup": q.is_followup,
                "has_answer": any(a.question_id == q.id for a in answers),
            }
            for q in questions
        ],
        "transcripts": [
            {
                "segment_type": t.segment_type,
                "text": t.text,
                "timestamp": t.timestamp.isoformat() if t.timestamp else "",
            }
            for t in transcripts
        ],
    }


@app.post("/api/interview/answer")
def submit_answer(req: SubmitAnswerRequest, db: Session = Depends(get_db)):
    """Submit an answer to a question during the interview."""
    session = db.query(InterviewSession).filter(InterviewSession.id == req.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    if session.status != "in_progress":
        raise HTTPException(status_code=400, detail="Interview is not in progress.")

    question = db.query(InterviewQuestion).filter(InterviewQuestion.id == req.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found.")

    # Get resume profile for context
    resume = db.query(Resume).filter(Resume.id == session.resume_id).first()
    profile = json.loads(resume.parsed_json) if resume and resume.parsed_json else {}

    # Score the answer
    evaluation = score_answer(
        question=question.question_text,
        answer=req.answer_text,
        category=question.category,
        profile=profile,
        duration_seconds=req.duration_seconds,
        question_number=question.question_index + 1,
        total_questions=session.total_questions,
    )

    # Save answer
    answer = InterviewAnswer(
        question_id=req.question_id,
        session_id=req.session_id,
        answer_text=req.answer_text,
        duration_seconds=req.duration_seconds,
        score_json=json.dumps(evaluation.get("scores", []), default=str),
        evaluation_json=json.dumps(evaluation, default=str),
    )
    db.add(answer)

    # Add answer transcript
    answer_transcript = InterviewTranscript(
        session_id=req.session_id,
        segment_type="answer",
        text=req.answer_text,
        duration_seconds=req.duration_seconds,
    )
    db.add(answer_transcript)

    db.flush()

    # Determine if we should ask a follow-up
    follow_up = None
    if should_ask_followup(req.answer_text, question.category):
        followup_text = generate_followup(
            question=question.question_text,
            answer=req.answer_text,
            profile=profile,
            category=question.category,
        )

        # Create follow-up question
        fq = InterviewQuestion(
            session_id=req.session_id,
            question_index=question.question_index,
            question_text=followup_text,
            category=question.category,
            is_followup=True,
            parent_question_id=question.id,
        )
        db.add(fq)
        db.flush()

        session.total_followups = (session.total_followups or 0) + 1

        # Add follow-up transcript
        fu_transcript = InterviewTranscript(
            session_id=req.session_id,
            segment_type="followup",
            text=followup_text,
        )
        db.add(fu_transcript)

        follow_up = {
            "question_id": fq.id,
            "question_index": fq.question_index,
            "question_text": fq.question_text,
            "category": fq.category,
            "is_followup": True,
            "parent_question_id": question.id,
        }

    db.commit()

    # Count total transcripts
    transcript_count = db.query(InterviewTranscript).filter(
        InterviewTranscript.session_id == req.session_id
    ).count()

    return {
        "answer_id": answer.id,
        "follow_up": follow_up,
        "transcript_count": transcript_count,
        "message": "Answer recorded successfully.",
    }


@app.post("/api/interview/end")
def end_interview(req: EndInterviewRequest, db: Session = Depends(get_db)):
    """End the interview and generate the full evaluation."""
    session = db.query(InterviewSession).filter(InterviewSession.id == req.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Update session
    session.ended_at = datetime.utcnow()
    session.status = "completed"
    if session.started_at:
        session.duration_seconds = (session.ended_at - session.started_at).total_seconds()

    # Calculate completion
    all_questions = db.query(InterviewQuestion).filter(
        InterviewQuestion.session_id == req.session_id,
        InterviewQuestion.is_followup == False,
    ).all()
    all_answers = db.query(InterviewAnswer).filter(
        InterviewAnswer.session_id == req.session_id
    ).all()
    answered_ids = set(a.question_id for a in all_answers)
    # Include answers to follow-ups
    followup_questions = db.query(InterviewQuestion).filter(
        InterviewQuestion.session_id == req.session_id,
        InterviewQuestion.is_followup == True,
    ).all()
    for fq in followup_questions:
        if fq.id in answered_ids or any(a.question_id == fq.id for a in all_answers):
            answered_ids.add(fq.id)

    total_main = len(all_questions) if all_questions else 1
    main_answered = sum(1 for q in all_questions if q.id in answered_ids)
    session.completion_percentage = min(100, round((main_answered / total_main) * 100)) if all_questions else 0

    # Build evaluation data
    resume = db.query(Resume).filter(Resume.id == session.resume_id).first()
    profile = json.loads(resume.parsed_json) if resume and resume.parsed_json else {}

    questions_data = []
    for q in all_questions:
        q_answer = next((a for a in all_answers if a.question_id == q.id), None)
        questions_data.append({
            "question_id": q.id,
            "question_text": q.question_text,
            "category": q.category,
            "answer_text": q_answer.answer_text if q_answer else "",
            "duration_seconds": q_answer.duration_seconds if q_answer else 0,
            "evaluation": json.loads(q_answer.evaluation_json) if q_answer and q_answer.evaluation_json else {},
        })

    # Also include follow-up answers
    for fq in followup_questions:
        fq_answer = next((a for a in all_answers if a.question_id == fq.id), None)
        if fq_answer:
            questions_data.append({
                "question_id": fq.id,
                "question_text": fq.question_text,
                "category": fq.category,
                "answer_text": fq_answer.answer_text if fq_answer else "",
                "duration_seconds": fq_answer.duration_seconds if fq_answer else 0,
                "evaluation": json.loads(fq_answer.evaluation_json) if fq_answer and fq_answer.evaluation_json else {},
            })

    session_data = {
        "questions": questions_data,
        "answers": questions_data,
    }

    evaluation = evaluate_full_interview(session_data, profile)

    # Save evaluation
    eval_record = InterviewEvaluation(
        session_id=req.session_id,
        overall_score=evaluation.get("overall_score", 0),
        readiness_level=evaluation.get("readiness_level", "Needs more practice"),
        scores_json=json.dumps(evaluation.get("scores", []), default=str),
        strengths_json=json.dumps(evaluation.get("strengths", []), default=str),
        improvements_json=json.dumps(evaluation.get("improvements", []), default=str),
        communication_json=json.dumps(evaluation.get("communication", {}), default=str),
        practice_plan_json=json.dumps(evaluation.get("practice_plan", []), default=str),
        resume_consistency_json=json.dumps(evaluation.get("resume_consistency", []), default=str),
    )
    db.add(eval_record)
    db.commit()

    # Build full evaluation result for frontend
    question_evaluations = []
    for q in all_questions:
        q_answer = next((a for a in all_answers if a.question_id == q.id), None)
        q_eval_data = json.loads(q_answer.evaluation_json) if q_answer and q_answer.evaluation_json else {}
        question_evaluations.append({
            "question_id": q.id,
            "question_text": q.question_text,
            "answer_text": q_answer.answer_text if q_answer else "No answer recorded",
            "answer_duration": q_answer.duration_seconds if q_answer else 0,
            "timestamp": q_answer.answered_at.isoformat() if q_answer and q_answer.answered_at else "",
            "category": q.category,
            "scores": q_eval_data.get("scores", []),
            "strengths": q_eval_data.get("strengths", []),
            "improvements": q_eval_data.get("improvements", []),
            "suggested_answer_structure": q_eval_data.get("suggested_answer_structure", ""),
        })

    return {
        "session_id": session.id,
        "status": "completed",
        "overall_score": evaluation.get("overall_score", 0),
        "readiness_level": evaluation.get("readiness_level", "Needs more practice"),
        "scores": evaluation.get("scores", []),
        "strengths": evaluation.get("strengths", []),
        "improvements": evaluation.get("improvements", []),
        "communication": evaluation.get("communication", {}),
        "practice_plan": evaluation.get("practice_plan", []),
        "resume_consistency": evaluation.get("resume_consistency", []),
        "question_evaluations": question_evaluations,
        "candidate_name": profile.get("name", ""),
        "resume_filename": resume.filename if resume else "",
        "interview_date": datetime.utcnow().strftime("%B %d, %Y"),
        "duration_seconds": session.duration_seconds,
        "total_questions": session.total_questions,
        "total_followups": session.total_followups or 0,
        "completion_percentage": session.completion_percentage,
    }


@app.get("/api/interview/{session_id}/results")
def get_results(session_id: str, db: Session = Depends(get_db)):
    """Get the full evaluation results for an interview."""
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    evaluation = db.query(InterviewEvaluation).filter(
        InterviewEvaluation.session_id == session_id
    ).first()

    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found. Complete the interview first.")

    resume = db.query(Resume).filter(Resume.id == session.resume_id).first()
    profile = json.loads(resume.parsed_json) if resume and resume.parsed_json else {}

    all_questions = db.query(InterviewQuestion).filter(
        InterviewQuestion.session_id == session_id
    ).order_by(InterviewQuestion.question_index, InterviewQuestion.is_followup).all()

    all_answers = db.query(InterviewAnswer).filter(
        InterviewAnswer.session_id == session_id
    ).all()

    question_evaluations = []
    for q in all_questions:
        q_answer = next((a for a in all_answers if a.question_id == q.id), None)
        q_eval_data = json.loads(q_answer.evaluation_json) if q_answer and q_answer.evaluation_json else {}
        question_evaluations.append({
            "question_id": q.id,
            "question_text": q.question_text,
            "answer_text": q_answer.answer_text if q_answer else "No answer recorded",
            "answer_duration": q_answer.duration_seconds if q_answer else 0,
            "timestamp": q_answer.answered_at.isoformat() if q_answer and q_answer.answered_at else "",
            "category": q.category,
            "is_followup": q.is_followup,
            "scores": q_eval_data.get("scores", []),
            "strengths": q_eval_data.get("strengths", []),
            "improvements": q_eval_data.get("improvements", []),
            "suggested_answer_structure": q_eval_data.get("suggested_answer_structure", ""),
        })

    transcripts = db.query(InterviewTranscript).filter(
        InterviewTranscript.session_id == session_id
    ).order_by(InterviewTranscript.id).all()

    return {
        "session_id": session.id,
        "status": session.status,
        "overall_score": evaluation.overall_score,
        "readiness_level": evaluation.readiness_level,
        "scores": json.loads(evaluation.scores_json) if evaluation.scores_json else [],
        "strengths": json.loads(evaluation.strengths_json) if evaluation.strengths_json else [],
        "improvements": json.loads(evaluation.improvements_json) if evaluation.improvements_json else [],
        "communication": json.loads(evaluation.communication_json) if evaluation.communication_json else {},
        "practice_plan": json.loads(evaluation.practice_plan_json) if evaluation.practice_plan_json else [],
        "resume_consistency": json.loads(evaluation.resume_consistency_json) if evaluation.resume_consistency_json else [],
        "question_evaluations": question_evaluations,
        "candidate_name": profile.get("name", ""),
        "resume_filename": resume.filename if resume else "",
        "interview_date": evaluation.created_at.strftime("%B %d, %Y") if evaluation.created_at else "",
        "duration_seconds": session.duration_seconds,
        "total_questions": session.total_questions,
        "total_followups": session.total_followups or 0,
        "completion_percentage": session.completion_percentage,
        "transcripts": [
            {
                "segment_type": t.segment_type,
                "text": t.text,
                "timestamp": t.timestamp.isoformat() if t.timestamp else "",
                "duration_seconds": t.duration_seconds or 0,
            }
            for t in transcripts
        ],
    }


# ── PDF Report ─────────────────────────────────────────────────────────

@app.get("/api/interview/{session_id}/pdf")
def download_pdf(session_id: str, db: Session = Depends(get_db)):
    """Generate and download the PDF interview report."""
    if not HAS_REPORTLAB:
        raise HTTPException(
            status_code=500,
            detail="PDF generation requires reportlab. Install with: pip install reportlab"
        )

    # Get evaluation data (reuse the results endpoint logic)
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    evaluation = db.query(InterviewEvaluation).filter(
        InterviewEvaluation.session_id == session_id
    ).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found.")

    resume = db.query(Resume).filter(Resume.id == session.resume_id).first()
    profile = json.loads(resume.parsed_json) if resume and resume.parsed_json else {}

    all_questions = db.query(InterviewQuestion).filter(
        InterviewQuestion.session_id == session_id
    ).order_by(InterviewQuestion.question_index, InterviewQuestion.is_followup).all()

    all_answers = db.query(InterviewAnswer).filter(
        InterviewAnswer.session_id == session_id
    ).all()

    question_evaluations = []
    for q in all_questions:
        q_answer = next((a for a in all_answers if a.question_id == q.id), None)
        q_eval_data = json.loads(q_answer.evaluation_json) if q_answer and q_answer.evaluation_json else {}
        question_evaluations.append({
            "question_id": q.id,
            "question_text": q.question_text,
            "answer_text": q_answer.answer_text if q_answer else "No answer recorded",
            "answer_duration": q_answer.duration_seconds if q_answer else 0,
            "category": q.category,
            "scores": q_eval_data.get("scores", []),
            "strengths": q_eval_data.get("strengths", []),
            "improvements": q_eval_data.get("improvements", []),
            "suggested_answer_structure": q_eval_data.get("suggested_answer_structure", ""),
        })

    evaluation_data = {
        "candidate_name": profile.get("name", "Candidate"),
        "resume_filename": resume.filename if resume else "resume",
        "interview_date": evaluation.created_at.strftime("%B %d, %Y") if evaluation.created_at else datetime.utcnow().strftime("%B %d, %Y"),
        "duration_seconds": session.duration_seconds,
        "total_questions": session.total_questions,
        "total_followups": session.total_followups or 0,
        "completion_percentage": session.completion_percentage,
        "overall_score": evaluation.overall_score,
        "readiness_level": evaluation.readiness_level,
        "scores": json.loads(evaluation.scores_json) if evaluation.scores_json else [],
        "strengths": json.loads(evaluation.strengths_json) if evaluation.strengths_json else [],
        "improvements": json.loads(evaluation.improvements_json) if evaluation.improvements_json else [],
        "communication": json.loads(evaluation.communication_json) if evaluation.communication_json else {},
        "practice_plan": json.loads(evaluation.practice_plan_json) if evaluation.practice_plan_json else [],
        "question_evaluations": question_evaluations,
    }

    try:
        pdf_bytes = generate_pdf_report(evaluation_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    name_slug = (profile.get("name", "candidate")).replace(" ", "-").lower()
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"interview-report-{name_slug}-{date_str}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/interview/{session_id}/transcript")
def download_transcript(session_id: str, format: str = "txt", db: Session = Depends(get_db)):
    """Download the interview transcript as TXT or JSON."""
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    resume = db.query(Resume).filter(Resume.id == session.resume_id).first()
    profile = json.loads(resume.parsed_json) if resume and resume.parsed_json else {}
    candidate_name = profile.get("name", "Candidate")

    transcripts = db.query(InterviewTranscript).filter(
        InterviewTranscript.session_id == session_id
    ).order_by(InterviewTranscript.id).all()

    transcript_data = [
        {
            "segment_type": t.segment_type,
            "text": t.text,
            "timestamp": t.timestamp.isoformat() if t.timestamp else "",
            "duration_seconds": t.duration_seconds or 0,
        }
        for t in transcripts
    ]

    if format == "json":
        content = generate_transcript_json(transcript_data, candidate_name)
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="transcript-{session_id}.json"'},
        )
    else:
        content = generate_transcript_txt(transcript_data, candidate_name)
        return Response(
            content=content,
            media_type="text/plain",
            headers={"Content-Disposition": f'attachment; filename="transcript-{session_id}.txt"'},
        )


# ── Session Deletion ───────────────────────────────────────────────────

@app.delete("/api/interview/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    """Delete an interview session and all associated data."""
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Delete related records
    db.query(InterviewTranscript).filter(InterviewTranscript.session_id == session_id).delete()
    db.query(InterviewAnswer).filter(InterviewAnswer.session_id == session_id).delete()
    db.query(InterviewQuestion).filter(InterviewQuestion.session_id == session_id).delete()
    db.query(InterviewEvaluation).filter(InterviewEvaluation.session_id == session_id).delete()
    db.delete(session)
    db.commit()

    return {"message": "Session deleted successfully."}


# ── Serve Frontend ─────────────────────────────────────────────────────

@app.get("/")
@app.get("/index.html")
@app.get("/static/index.html")
def serve_frontend():
    index_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "ResumeFlow Interview Studio API Server Online"}


# Mount static assets
frontend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=os.path.join(frontend_path, "static")), name="static")
