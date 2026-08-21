import os
import json
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "interviewpro.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Resume(Base):
    """Stores uploaded resume data and extracted information."""
    __tablename__ = "resumes"

    id = Column(String, primary_key=True, index=True)
    candidate_name = Column(String, default="")
    filename = Column(String, default="")
    file_type = Column(String, default="")  # pdf, docx, txt
    raw_text = Column(Text, default="")
    parsed_json = Column(Text, default="{}")  # JSON of all extracted fields
    created_at = Column(DateTime, default=datetime.utcnow)

    sessions = relationship("InterviewSession", back_populates="resume", cascade="all, delete-orphan")


class InterviewSession(Base):
    """Stores interview session metadata."""
    __tablename__ = "interview_sessions"

    id = Column(String, primary_key=True, index=True)
    resume_id = Column(String, ForeignKey("resumes.id"))
    status = Column(String, default="pending")  # pending, in_progress, completed, cancelled
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, default=0.0)
    total_questions = Column(Integer, default=0)
    total_followups = Column(Integer, default=0)
    completion_percentage = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    resume = relationship("Resume", back_populates="sessions")
    questions = relationship("InterviewQuestion", back_populates="session", cascade="all, delete-orphan")
    answers = relationship("InterviewAnswer", back_populates="session", cascade="all, delete-orphan")
    transcripts = relationship("InterviewTranscript", back_populates="session", cascade="all, delete-orphan")
    evaluation = relationship("InterviewEvaluation", back_populates="session", uselist=False, cascade="all, delete-orphan")


class InterviewQuestion(Base):
    """Stores each question asked during the interview."""
    __tablename__ = "interview_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("interview_sessions.id"))
    question_index = Column(Integer, default=0)
    question_text = Column(Text, nullable=False)
    category = Column(String, default="general")
    rubric_json = Column(Text, default="{}")  # Evaluation rubric
    is_followup = Column(Boolean, default=False)
    parent_question_id = Column(Integer, nullable=True)
    asked_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("InterviewSession", back_populates="questions")
    answer = relationship("InterviewAnswer", back_populates="question", uselist=False)


class InterviewAnswer(Base):
    """Stores candidate answers with timing and evaluation."""
    __tablename__ = "interview_answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey("interview_questions.id"))
    session_id = Column(String, ForeignKey("interview_sessions.id"))
    answer_text = Column(Text, default="")
    duration_seconds = Column(Float, default=0.0)
    score_json = Column(Text, default="{}")  # Detailed per-dimension scores
    evaluation_json = Column(Text, default="{}")  # What was done well, improvements, etc.
    answered_at = Column(DateTime, default=datetime.utcnow)

    question = relationship("InterviewQuestion", back_populates="answer")
    session = relationship("InterviewSession", back_populates="answers")


class InterviewTranscript(Base):
    """Stores full transcript segments for the interview."""
    __tablename__ = "interview_transcripts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("interview_sessions.id"))
    segment_type = Column(String, default="system")  # system, question, answer, followup
    text = Column(Text, default="")
    timestamp = Column(DateTime, default=datetime.utcnow)
    duration_seconds = Column(Float, default=0.0)

    session = relationship("InterviewSession", back_populates="transcripts")


class InterviewEvaluation(Base):
    """Stores the final evaluation after interview completion."""
    __tablename__ = "interview_evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("interview_sessions.id"), unique=True)
    overall_score = Column(Float, default=0.0)
    readiness_level = Column(String, default="Needs more practice")
    scores_json = Column(Text, default="{}")  # All dimension scores
    strengths_json = Column(Text, default="[]")
    improvements_json = Column(Text, default="[]")
    communication_json = Column(Text, default="{}")
    practice_plan_json = Column(Text, default="[]")
    resume_consistency_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("InterviewSession", back_populates="evaluation")


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
