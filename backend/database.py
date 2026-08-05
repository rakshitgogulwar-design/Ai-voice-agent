import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "interviewpro.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class CandidateSession(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, index=True)
    company = Column(String, default="Amazon")
    role = Column(String, default="Senior Software Engineer")
    experience = Column(String, default="Mid-Level")
    persona_id = Column(String, default="dm")
    created_at = Column(DateTime, default=datetime.utcnow)

    transcripts = relationship("TranscriptRecord", back_populates="session", cascade="all, delete-orphan")
    code_submissions = relationship("CodeSubmissionRecord", back_populates="session", cascade="all, delete-orphan")
    report = relationship("AssessmentReport", back_populates="session", uselist=False, cascade="all, delete-orphan")

class TranscriptRecord(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    round_index = Column(Integer, default=0)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    score = Column(Integer, default=75)
    tech_keywords = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("CandidateSession", back_populates="transcripts")

class CodeSubmissionRecord(Base):
    __tablename__ = "code_submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    language = Column(String, default="python")
    code = Column(Text, nullable=False)
    execution_time_ms = Column(Float, default=0.0)
    passed_tests = Column(Integer, default=1)
    complexity_rating = Column(String, default="O(N)")
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("CandidateSession", back_populates="code_submissions")

class AssessmentReport(Base):
    __tablename__ = "assessment_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"), unique=True)
    overall_score = Column(Integer, default=85)
    verdict = Column(String, default="STRONG HIRE")
    tech_score = Column(Integer, default=88)
    prob_score = Column(Integer, default=85)
    code_score = Column(Integer, default=90)
    comm_score = Column(Integer, default=88)
    star_score = Column(Integer, default=82)
    conf_score = Column(Integer, default=92)
    lead_score = Column(Integer, default=84)
    arch_score = Column(Integer, default=86)
    strengths = Column(Text, default="")
    growth_areas = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("CandidateSession", back_populates="report")

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
