# 03 — Backend Architecture & Database Design

This document details how I structured the backend codebase in `backend/`, including the database models, REST API controllers, and data lifecycle.

---

## Directory Organization

```
backend/
├── app.py                  # Main FastAPI application & REST endpoint handlers
├── database.py             # SQLAlchemy models, SQLite connection & session management
├── models.py               # Pydantic request/response schemas
├── resume_parser.py        # PDF/DOCX parsing & semantic fact extraction
├── interview_generator.py  # STAR question generation & adaptive follow-up logic
├── evaluator.py            # Multi-dimensional answer scoring & LLM assessment
└── pdf_generator.py        # ReportLab PDF generator
```

---

## Database Schema (SQLAlchemy Models)

I designed the relational model in [`backend/database.py`](file:///Users/yuvii/Ai-voice-agent/backend/database.py) using SQLite with 5 interconnected tables:

```
+------------------+         1 : N         +----------------------+
|     Resume       | --------------------> |   InterviewSession   |
|------------------|                       |----------------------|
| id (PK)          |                       | id (PK)              |
| candidate_name   |                       | resume_id (FK)       |
| filename         |                       | status               |
| file_type        |                       | started_at, ended_at |
| raw_text         |                       | total_questions      |
| parsed_json      |                       | completion_pct       |
+------------------+                       +----------------------+
                                                       |
                             +-------------------------+-------------------------+
                             | 1 : N                                             | 1 : 1
                             v                                                   v
                  +----------------------+                             +----------------------+
                  |  InterviewQuestion   |                             | InterviewEvaluation  |
                  |----------------------|                             |----------------------|
                  | id (PK)              |                             | id (PK)              |
                  | session_id (FK)      |                             | session_id (FK)      |
                  | question_index       |                             | overall_score        |
                  | question_text        |                             | readiness_level      |
                  | category             |                             | scores_json          |
                  | rubric_json          |                             | strengths_json       |
                  | is_followup          |                             | improvements_json    |
                  +----------------------+                             | communication_json   |
                             |                                         | practice_plan_json   |
                             | 1 : N                                   | consistency_json     |
                             v                                         +----------------------+
                  +----------------------+
                  |   InterviewAnswer    |
                  |----------------------|
                  | id (PK)              |
                  | question_id (FK)     |
                  | session_id (FK)      |
                  | answer_text          |
                  | duration_seconds     |
                  | score_json           |
                  | evaluation_json      |
                  +----------------------+
```

### Key Models Defined:
1. **`Resume`**: Stores the raw extracted text and serialized candidate profile (skills, job titles, companies, tools, projects, and achievements).
2. **`InterviewSession`**: Manages the state of an interview (`in_progress`, `completed`, `cancelled`), tracking progress percentage.
3. **`InterviewQuestion`**: Stores each generated question, category, rubric guidelines, and flag indicating if it was a dynamically generated follow-up.
4. **`InterviewAnswer`**: Captures candidate answer text, spoken duration in seconds, and individual turn evaluations.
5. **`InterviewTranscript`**: An immutable chronological audit log of all system messages, questions, and candidate answers.
6. **`InterviewEvaluation`**: The aggregated final assessment generated at the end of the session.

---

## REST API Specification

### 1. Resume Ingestion
- **`POST /api/resume/upload`**:
  - Accepts `multipart/form-data` with PDF, DOCX, or TXT files.
  - Temporarily buffers file, calls `parse_resume()`, saves record in SQLite, and returns extracted `profile` and `resume_id`.
- **`POST /api/resume/upload-text`**:
  - Direct raw text upload fallback.
- **`GET /api/resume/{resume_id}`**:
  - Retrieves parsed candidate profile and resume facts.
- **`PUT /api/resume/{resume_id}`**:
  - Allows candidate to edit or verify their extracted skills/experience before starting.

### 2. Interview Session Flow
- **`POST /api/interview/start`**:
  - Initializes a new `InterviewSession`.
  - Invokes `generate_interview_questions()` to synthesize 10 STAR questions.
  - Generates conversational welcome greeting and returns the first question.
- **`GET /api/interview/{session_id}`**:
  - Polls session status, current progress percentage, and transcripts.
- **`POST /api/interview/answer`**:
  - Records candidate's answer and duration.
  - Executes real-time scoring via `score_answer()`.
  - Runs `should_ask_followup()` heuristic. If triggered, generates a dynamic follow-up via Groq/Gemini and returns it immediately.
- **`POST /api/interview/end`**:
  - Concludes session, calculates overall readiness score (0-100%), produces full practice roadmap, and saves `InterviewEvaluation`.

### 3. Reporting & Exports
- **`GET /api/interview/{session_id}/results`**:
  - Delivers complete scorecard payload for the frontend dashboard.
- **`GET /api/interview/{session_id}/pdf`**:
  - Streams dynamically generated ReportLab PDF binary.
- **`GET /api/interview/{session_id}/transcript`**:
  - Exports full transcript as plain text or JSON.
