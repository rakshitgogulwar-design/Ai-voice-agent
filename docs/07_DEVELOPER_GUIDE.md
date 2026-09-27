# 07 — Developer Guide

This is the complete guide for setting up, running, extending, and deploying ResumeFlow Interview Studio. Follow this document to understand the full project from end to end.

---

## Project Structure Reference

```
Ai-voice-agent/
│
├── backend/                    ← Python FastAPI server
│   ├── app.py                  # Main app, all REST endpoints (848 lines)
│   ├── database.py             # SQLAlchemy models + SQLite connection
│   ├── models.py               # Pydantic request/response schemas
│   ├── resume_parser.py        # PDF/DOCX/TXT extraction + NLP fact extraction
│   ├── interview_generator.py  # STAR question generation, follow-up logic
│   ├── evaluator.py            # 10-dimension scoring, Groq/Gemini/fallback
│   └── pdf_generator.py        # ReportLab PDF generator
│
├── frontend/                   ← Vanilla JS Single Page Application
│   ├── index.html              # SPA shell (all 5 views pre-rendered)
│   └── static/
│       ├── css/style.css       # Complete dark-mode design system
│       └── js/
│           ├── app.js          # State machine, API client, results UI
│           └── speech.js       # TTS/STT/AudioContext waveform engine
│
├── docs/                       ← This documentation suite
│   ├── README.md               # Documentation index
│   ├── 01_SYSTEM_OVERVIEW.md
│   ├── 02_TECH_STACK.md
│   ├── 03_BACKEND_ARCHITECTURE.md
│   ├── 04_FRONTEND_ARCHITECTURE.md
│   ├── 05_VOICE_AND_AI_PIPELINE.md
│   ├── 06_EVALUATION_AND_SCORING.md
│   └── 07_DEVELOPER_GUIDE.md   # ← You are here
│
├── engine/                     ← C evaluator micro-library (optional native speed)
│   ├── evaluator.c
│   └── Makefile
│
├── .env                        ← Your local secrets (not committed to git)
├── .env.example                ← Template for environment variables
├── requirements.txt            ← Python dependencies
├── run.sh                      ← Convenience startup script
├── Dockerfile                  ← Container image definition
├── interviewpro.db             ← SQLite database file (auto-created on first run)
└── README.md                   ← Project README
```

---

## Prerequisites

Before running the project, ensure you have:

| Requirement | Version | Check |
| :--- | :--- | :--- |
| Python | ≥ 3.9 | `python3 --version` |
| pip | Latest | `pip3 --version` |
| A modern browser | Chrome / Edge recommended | — |
| GROQ API Key | Free at console.groq.com | Optional but recommended |
| Gemini API Key | Free at aistudio.google.com | Optional but recommended |

> **Note**: Docker is fully optional. The app runs fine with just Python.

---

## Setup: Step by Step

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd Ai-voice-agent
```

### 2. Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate    # macOS / Linux
# .venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Current `requirements.txt`:

```
fastapi>=0.100.0
uvicorn>=0.22.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
python-dotenv>=1.0.0
python-multipart>=0.0.6
aiofiles>=23.1.0
requests>=2.31.0
pdfplumber>=0.10.0
python-docx>=1.0.0
reportlab>=4.0.0
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
```

Then edit `.env`:

```ini
# ── AI Providers (at least one recommended) ───────────────────────
GROQ_API_KEY=gsk_your_groq_key_here
GROQ_MODEL=openai/gpt-oss-120b      # Optional — default

GEMINI_API_KEY=AIzaSy_your_gemini_key_here
GEMINI_MODEL=gemini-3.8-flash       # Optional — default

# ── Server Configuration ──────────────────────────────────────────
HOST=127.0.0.1
PORT=8005
DEBUG=true
```

### 5. Start the Server

**Option A — Quick start (uses .venv automatically):**
```bash
chmod +x run.sh
./run.sh
```

**Option B — Manual uvicorn:**
```bash
uvicorn backend.app:app --host 127.0.0.1 --port 8005 --reload
```

### 6. Open the App

Navigate to: **http://127.0.0.1:8005**

---

## Available API Endpoints

You can explore all endpoints interactively at: **http://127.0.0.1:8005/docs**

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Health check |
| `POST` | `/api/resume/upload` | Upload PDF/DOCX/TXT resume |
| `POST` | `/api/resume/upload-text` | Upload raw text resume |
| `GET` | `/api/resume/{id}` | Get parsed resume profile |
| `PUT` | `/api/resume/{id}` | Update candidate profile |
| `POST` | `/api/interview/start` | Start interview, generate questions |
| `GET` | `/api/interview/{id}` | Get session status + transcripts |
| `POST` | `/api/interview/answer` | Submit answer, get scoring |
| `POST` | `/api/interview/end` | End session, generate full evaluation |
| `GET` | `/api/interview/{id}/results` | Get complete scorecard JSON |
| `GET` | `/api/interview/{id}/pdf` | Download PDF assessment report |
| `GET` | `/api/interview/{id}/transcript` | Download transcript (txt/json) |

---

## Database Management

The SQLite database is created automatically at `interviewpro.db` when the server starts for the first time.

### View database contents (optional):
```bash
# Install sqlitebrowser for a GUI
# Or use the sqlite3 CLI:
sqlite3 interviewpro.db ".tables"
sqlite3 interviewpro.db "SELECT id, candidate_name, created_at FROM resumes;"
sqlite3 interviewpro.db "SELECT id, status, overall_score FROM interview_evaluations;"
```

### Reset the database:
```bash
rm interviewpro.db
# Next server start will recreate it fresh
```

---

## Testing the AI Pipeline

To quickly verify your API keys are working:

```bash
cd /Users/yuvii/Ai-voice-agent
source .venv/bin/activate

python3 -c "
from backend.evaluator import score_answer_with_groq
from dotenv import load_dotenv
load_dotenv()

result = score_answer_with_groq(
    question='Tell me about yourself.',
    answer='I am a software engineer with 3 years of Python experience. I built a REST API at my last company that reduced latency by 40%.',
    resume_context='Python, FastAPI, 3 years backend experience'
)
print('Groq result:', result)
"
```

---

## Customising Question Generation

To modify how interview questions are generated, edit:

```
backend/interview_generator.py
```

Key functions:

| Function | Description |
| :--- | :--- |
| `generate_interview_questions(profile)` | Generates all 10 STAR questions from resume |
| `generate_followup(question, answer, resume_context)` | Generates adaptive follow-up |
| `should_ask_followup(answer, category, score)` | Decides if follow-up is needed |
| `get_rubric_for_category(category)` | Returns evaluation rubric for a question type |

To add a new question category, add it to `QUESTION_CATEGORIES` and add a matching entry in `get_rubric_for_category()`.

---

## Customising the Evaluation Rubric

To add new scoring dimensions or change the 10-dimension rubric, edit `backend/evaluator.py`:

```python
SCORE_DIMENSIONS = [
    "relevance",
    "completeness",
    # Add new dimension key here
]

DISPLAY_DIMENSIONS = [
    "Relevance",
    "Completeness",
    # Add matching display name here
]
```

> **Important**: The Groq prompt and the `_parse_scored_result()` validation must also be updated to reflect any new dimensions.

---

## Troubleshooting

### "GROQ_API_KEY not found" / No AI evaluation
- Check that `.env` exists and contains `GROQ_API_KEY=gsk_...`
- Ensure you are not using the placeholder value `your_groq_api_key_here`
- The app will fall back to the rule-based engine automatically

### "ModuleNotFoundError: No module named 'backend'"
- Ensure you are running uvicorn from the project root (`/Users/yuvii/Ai-voice-agent`)
- Ensure the virtual environment is active: `source .venv/bin/activate`

### Voice not working / microphone not activating
- Voice recognition requires HTTPS or localhost — the dev server at `http://127.0.0.1:8005` is localhost, so this should work
- Chrome and Edge have the best Web Speech API support — try a different browser if Firefox is used
- Check that microphone permission is granted in the browser

### PDF download fails / empty PDF
- Ensure `reportlab` is installed: `pip install reportlab`
- Check server logs for `HAS_REPORTLAB = False` warnings

---

## Docker Deployment (Optional)

> Docker Desktop must be installed from https://docs.docker.com/desktop/install/mac-install/

```bash
docker build -t resumeflow .
docker run -p 7860:7860 \
  -e GROQ_API_KEY=gsk_your_key \
  -e GEMINI_API_KEY=AIza_your_key \
  resumeflow
```

Then open: **http://localhost:7860**

---

## Deploying to Hugging Face Spaces

The project includes a `Dockerfile` pre-configured for Hugging Face Spaces deployment on port `7860`.

1. Create a new Space at https://huggingface.co/spaces
2. Set Space SDK to **Docker**
3. Push this repository to the Space
4. Add your `GROQ_API_KEY` and `GEMINI_API_KEY` as Space **Secrets** in the Settings

---

## Adding New Features: Suggested Extension Points

| Feature Idea | Where to Add |
| :--- | :--- |
| Support for more resume formats (e.g. LinkedIn JSON) | `backend/resume_parser.py` |
| Add OpenAI GPT-4 as an additional tier | `backend/evaluator.py` — add `_openai_config()` |
| Add a candidate login / session history | `backend/database.py` — add `User` model |
| Support multiple interview types (technical, behavioural) | `backend/interview_generator.py` — add type parameter |
| Email the PDF report to the candidate | `backend/app.py` — add `/api/interview/{id}/email` endpoint |
| Add a timer countdown on the frontend | `frontend/static/js/app.js` — extend `State.timerInterval` |
