"""
Pydantic data models for ResumeFlow Interview Platform.
These models define the typed interfaces for all data flowing through the system.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ── Resume & Candidate Models ──────────────────────────────────────────

class ResumeSection(BaseModel):
    title: str = ""
    content: str = ""


class CandidateProfile(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    summary: str = ""
    job_titles: List[str] = Field(default_factory=list)
    companies: List[str] = Field(default_factory=list)  # Only as context from resume
    skills: List[str] = Field(default_factory=list)
    tools_and_tech: List[str] = Field(default_factory=list)
    projects: List[Dict[str, str]] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    education: List[Dict[str, str]] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    career_timeline: List[Dict[str, str]] = Field(default_factory=list)
    measurable_results: List[str] = Field(default_factory=list)
    missing_or_unclear: List[str] = Field(default_factory=list)
    sections: List[ResumeSection] = Field(default_factory=list)
    raw_text: str = ""


class ResumeUploadResponse(BaseModel):
    resume_id: str
    candidate_name: str
    filename: str
    profile: CandidateProfile
    message: str = "Resume uploaded and parsed successfully"


class ResumeUpdateRequest(BaseModel):
    profile: CandidateProfile


# ── Interview Models ───────────────────────────────────────────────────

class EvaluationRubric(BaseModel):
    relevance: str = "Does the answer address the question asked?"
    accuracy: str = "Is the answer consistent with the resume?"
    specificity: str = "Does the answer include specific details?"
    examples: str = "Does the answer use concrete examples?"
    structure: str = "Does the answer follow a clear structure (e.g., STAR)?"
    depth: str = "Does the answer demonstrate technical/professional depth?"
    clarity: str = "Is the answer clear and well-articulated?"
    completeness: str = "Is the answer complete?"


class InterviewQuestionModel(BaseModel):
    question_id: int = 0
    question_index: int = 0
    question_text: str = ""
    category: str = "general"
    rubric: EvaluationRubric = Field(default_factory=EvaluationRubric)
    is_followup: bool = False
    parent_question_id: Optional[int] = None


class StartInterviewRequest(BaseModel):
    resume_id: str


class StartInterviewResponse(BaseModel):
    session_id: str
    welcome_message: str
    first_question: InterviewQuestionModel
    total_questions: int


class SubmitAnswerRequest(BaseModel):
    session_id: str
    question_id: int
    answer_text: str
    duration_seconds: float = 0.0


class SubmitAnswerResponse(BaseModel):
    answer_id: int
    follow_up: Optional[InterviewQuestionModel] = None
    transcript_count: int
    message: str = ""


class EndInterviewRequest(BaseModel):
    session_id: str


# ── Evaluation Models ──────────────────────────────────────────────────

class EvaluationScore(BaseModel):
    dimension: str
    score: float = 0.0  # 1-5
    max_score: float = 5.0
    evidence: str = ""


class StrengthItem(BaseModel):
    area: str
    description: str
    evidence: str = ""


class ImprovementItem(BaseModel):
    area: str
    description: str
    suggestion: str = ""


class CommunicationMetrics(BaseModel):
    avg_answer_duration: float = 0.0
    speaking_pace: str = ""
    filler_word_count: int = 0
    long_pauses: int = 0
    repeated_phrases: int = 0
    questions_requiring_repetition: int = 0
    conciseness_rating: str = ""


class PracticeRecommendation(BaseModel):
    priority: int = 1
    recommendation: str = ""
    rationale: str = ""


class QuestionEvaluation(BaseModel):
    question_id: int = 0
    question_text: str = ""
    answer_text: str = ""
    answer_duration: float = 0.0
    timestamp: str = ""
    category: str = ""
    scores: List[EvaluationScore] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    suggested_answer_structure: str = ""


class ResumeConsistencyNote(BaseModel):
    statement: str
    resume_context: str
    status: str = "consistent"  # consistent, inconsistent, unverifiable


class InterviewEvaluationResult(BaseModel):
    session_id: str
    candidate_name: str = ""
    resume_filename: str = ""
    interview_date: str = ""
    duration_seconds: float = 0.0
    total_questions: int = 0
    total_followups: int = 0
    completion_percentage: int = 0

    overall_score: float = 0.0
    readiness_level: str = "Needs more practice"
    scores: List[EvaluationScore] = Field(default_factory=list)
    strengths: List[StrengthItem] = Field(default_factory=list)
    improvements: List[ImprovementItem] = Field(default_factory=list)
    question_evaluations: List[QuestionEvaluation] = Field(default_factory=list)
    communication: CommunicationMetrics = Field(default_factory=CommunicationMetrics)
    practice_plan: List[PracticeRecommendation] = Field(default_factory=list)
    resume_consistency: List[ResumeConsistencyNote] = Field(default_factory=list)


# ── Transcript Models ──────────────────────────────────────────────────

class TranscriptSegment(BaseModel):
    segment_type: str  # system, question, answer, followup
    text: str
    timestamp: str = ""
    duration_seconds: float = 0.0


# ── API Response Wrappers ──────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "online"
    version: str = "1.0.0"
    platform: str = "ResumeFlow Interview Studio"


class ErrorResponse(BaseModel):
    error: str
    detail: str = ""
