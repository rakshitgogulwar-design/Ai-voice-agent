# 08 — Codebase Walkthrough: How I Built ResumeFlow

This document is a personal, plain-English walkthrough of the entire codebase. It explains **what every file does**, **why I made each decision**, and **how all the pieces connect together**. If you are reading this codebase for the first time — this is where to start.

---

## The Big Picture

I built **ResumeFlow Interview Studio** to solve a real problem: standard interview prep tools give you generic questions. They don't know *your* story.

My system:
1. Reads *your actual resume*
2. Generates interview questions specifically about *your* experience, projects, and skills
3. Interviews you via voice — it speaks, you speak back
4. Grades every answer across 10 dimensions using Groq AI
5. Gives you a downloadable PDF report with evidence-backed feedback

Here is how I assembled all of that:

---

## Step 1: The Backend Foundation

### `backend/database.py` — Where all data is stored

This is the first file I wrote. I needed a place to store:
- The candidate's uploaded resume
- The interview session and its progress
- Every question asked and every answer given
- The final evaluation results

I used **SQLite** (a file-based database built into Python) with **SQLAlchemy** (a library that lets me write Python classes instead of raw SQL). The database auto-creates itself when the server starts for the first time — no setup required.

```
resumes → interview_sessions → interview_questions → interview_answers
                             └──────────────────── → interview_evaluations
                             └──────────────────── → interview_transcripts
```

Everything is connected: a resume can have many sessions, a session has many questions, each question has one answer.

---

### `backend/models.py` — The shape of all data

I defined every data shape in this file using **Pydantic** models (Python type-safe data classes). Think of this as the contract between the frontend and backend.

Key models:
- `CandidateProfile` — All extracted facts from the resume (name, skills, projects, companies, achievements)
- `InterviewQuestionModel` — One question (text, category, rubric guidelines, is it a follow-up?)
- `SubmitAnswerRequest` — What the frontend sends when the candidate finishes speaking
- `InterviewEvaluationResult` — The complete final evaluation with all 10 dimension scores

---

### `backend/resume_parser.py` — Reading the candidate's resume

This is where the resume file gets processed. I needed to support three formats: **PDF**, **Word (.docx)**, and **plain text**.

**How PDF parsing works:**
```python
import pdfplumber
with pdfplumber.open(file_path) as pdf:
    for page in pdf.pages:
        text += page.extract_text()
```

`pdfplumber` is smarter than basic PDF readers — it understands multi-column layouts and preserves table formatting.

**After extracting raw text**, I run a series of regex patterns to pull out structured facts:
- Name (usually the first large text on the resume)
- Email and phone (regex patterns for common formats)
- Skills section (lines after "Skills:", "Technical Skills:", etc.)
- Projects (sections after "Projects:", "Portfolio:", etc.)
- Companies and job titles (lines with date ranges like "Jan 2022 – Present")
- Achievements (lines starting with bullet points containing numbers and % signs)

All of this gets saved as a `CandidateProfile` JSON in the database.

---

### `backend/interview_generator.py` — Creating personalised questions

Once I have the candidate's profile, I generate 10 interview questions tailored specifically to their experience.

I send a prompt to **Groq AI** that includes:
- Their job titles and company names
- Their listed skills and tools
- Their projects and what they built
- Their measurable achievements

Groq generates 10 questions in the **STAR methodology** format (Situation, Task, Action, Result). These questions are things like:
- *"You listed React and Node.js on your resume — tell me about a specific project where you used both together. What was the challenge and what did you deliver?"*
- *"Your resume mentions you reduced API latency by 40% — walk me through how you diagnosed and solved that performance issue."*

If Groq is unavailable, I have a library of 100+ fallback question templates organized by category (`technical_skills`, `project_deep_dive`, `achievements`, etc.) that get filled in with resume facts.

---

### `backend/evaluator.py` — Scoring the answers with AI

This is the most complex module. After each answer, I call Groq to evaluate it across **10 dimensions**.

The function `score_answer_with_groq()` sends Groq a prompt like:

```
You are an expert technical interviewer. Score this answer:

Question: "Describe your experience with Python backend development."
Answer:   "I've been using Python for 3 years, mainly with FastAPI. At my last
           job I built a resume processing API that handled 500 files per day
           and reduced processing time by 60% using async workers."
Resume:   "Python, FastAPI, 3 years backend experience, async processing"

Score across these 10 dimensions: Relevance, Completeness, Specificity...
Return ONLY a JSON object with scores, evidence quotes, strengths, improvements.
```

The JSON response gets validated (all 10 dimensions must be present, scores must be 1–5) and then stored in the database.

If Groq fails, the same prompt is tried with **Google Gemini**. If that also fails, the system falls back to a rule-based engine that measures things like word count, filler words, and whether the answer contains specific numbers or project references.

---

### `backend/app.py` — The REST API server (main entry point)

This is where all the HTTP endpoints live. When the frontend makes an API call, it lands here.

Key endpoints I built:

```python
POST /api/resume/upload       → parse_resume() → save to database → return profile
POST /api/interview/start     → generate_interview_questions() → return first question  
POST /api/interview/answer    → score_answer() → maybe generate_followup() → return next question
POST /api/interview/end       → evaluate_full_interview() → save evaluation → return results
GET  /api/interview/{id}/pdf  → generate_pdf_report() → stream PDF binary
```

I used **FastAPI** because it automatically generates API documentation (visible at `/docs`) and handles all the JSON parsing/validation through Pydantic automatically.

---

### `backend/pdf_generator.py` — Creating the PDF assessment report

At the end of the interview, the candidate can download a professional PDF report. I generate it entirely in Python using **ReportLab** — no Chromium, no HTML-to-PDF conversion.

The report includes:
- A cover page with overall score and readiness level
- A scorecard table showing all 10 dimension scores
- Question-by-question breakdown with the candidate's actual answer and AI feedback
- Communication metrics (speaking pace, filler word count, timing)
- Resume consistency findings
- A prioritized practice plan

---

## Step 2: The Frontend

### `frontend/index.html` — The entire web app in one file

I built the frontend as a **Single Page Application (SPA)** where all 5 "pages" are actually hidden `<div>` elements in a single HTML file. JavaScript toggles which one is visible.

The 5 views:
1. `view-landing` — Hero page with "Start My Interview" button
2. `view-upload` — File drop zone for uploading the resume
3. `view-review` — Shows the extracted profile so the candidate can verify it
4. `view-interview` — The actual voice interview with waveform and question display
5. `view-results` — The scorecard dashboard with all scores and PDF download

---

### `frontend/static/js/app.js` — The brain of the frontend

This file manages everything the user sees and does. It:

1. Handles navigation between the 5 views
2. Makes all API calls to the FastAPI backend using `fetch()`
3. Manages the global `State` object (which resume was uploaded, which session is active, current question index, etc.)
4. Renders the results dashboard dynamically with the scores and feedback
5. Coordinates with `speech.js` for the voice interview loop

The voice interview loop works like this:
```
1. Backend returns a question object
2. app.js calls Speech.speak(question.text)   → computer reads question aloud
3. When speaking finishes → Speech.startListening()   → microphone opens
4. Candidate speaks → real-time transcript appears
5. Silence detected → Speech.stopListening()   → transcript finalized
6. app.js calls POST /api/interview/answer with the transcript
7. Backend returns: scoring results + optional follow-up question
8. If follow-up exists → go back to step 2
9. If no follow-up and more questions remain → load next question → go to step 2
10. If all done → POST /api/interview/end → navigate to results view
```

---

### `frontend/static/js/speech.js` — The voice engine

This handles everything voice-related:

**Text-to-Speech (the interviewer speaking):**
- Uses `window.speechSynthesis` — built into every browser
- Automatically picks the most natural-sounding available voice (macOS voices like "Samantha" or "Daniel" are used first)
- Speaks at a slightly slower pace (`rate: 0.92`) for better clarity

**Speech-to-Text (listening to the candidate):**
- Uses `webkitSpeechRecognition` — Chrome/Edge/Safari only
- Runs in `continuous` mode so it keeps listening until silence
- Shows a live transcript as the candidate speaks
- Falls back to a text input field if the browser doesn't support voice

**Audio Waveform Visualizer:**
- When the microphone is open, draws animated bars on an HTML `<canvas>`
- Uses the **WebAudio API** (`AudioContext → AnalyserNode`) to read real-time frequency amplitudes
- 40 bars at 60fps — shows the candidate their voice is being captured

---

### `frontend/static/css/style.css` — The entire visual design

I designed the entire dark-mode UI from scratch — no Bootstrap, no Tailwind.

The design uses:
- **CSS custom properties** for a consistent color system (all colors defined as variables in `:root`)
- **Glassmorphism cards** with `backdrop-filter: blur(18px)` for a modern, layered look
- **Micro-animations** — hover effects, loading spinners, waveform bars, button lift effects
- **Google Fonts**: Inter (readable body text), Fraunces (elegant hero headlines), IBM Plex Mono (code and scores)

---

## How It All Connects: The Complete Request Journey

Here is what happens from the moment you click "Start My Interview" to seeing your results:

```
1. You drag your resume PDF onto the upload zone
        ↓
2. app.js reads the file → POST /api/resume/upload (multipart form)
        ↓
3. FastAPI receives it → resume_parser.py extracts text → extracts facts
   → saves Resume record in SQLite → returns CandidateProfile JSON
        ↓
4. app.js shows the Review view — you verify your extracted profile
        ↓
5. You click "Start Interview" → POST /api/interview/start
        ↓
6. FastAPI creates InterviewSession → interview_generator.py calls Groq
   → 10 STAR questions generated → first question returned
        ↓
7. app.js receives first question → speech.js speaks it aloud (TTS)
        ↓
8. Microphone opens → you answer → live transcript shown on screen
        ↓
9. Silence detected → POST /api/interview/answer {transcript, duration}
        ↓
10. evaluator.py calls Groq → 10-dimension score JSON returned
    → should_ask_followup() checks if follow-up is needed
    → if yes: generate_followup() generates targeted follow-up question
        ↓
11. Steps 7–10 repeat for each question
        ↓
12. All questions answered → POST /api/interview/end
        ↓
13. evaluate_full_interview() aggregates all scores
    → computes overall_score + readiness_level
    → generates communication metrics + practice plan
    → saves InterviewEvaluation to SQLite
        ↓
14. app.js renders the Results view — scorecard, charts, feedback, strengths
        ↓
15. You click "Download PDF" → GET /api/interview/{id}/pdf
    → pdf_generator.py builds multi-page ReportLab PDF
    → streamed to browser → saved to your Downloads folder
```

---

## Key Technologies Summary

| What | Technology | Why I Chose It |
| :--- | :--- | :--- |
| Web server | FastAPI | Fast, auto-validates JSON, auto-generates API docs |
| Database | SQLite + SQLAlchemy | Zero setup, embedded, stores all session history |
| Resume parsing | pdfplumber + python-docx | Handles complex PDF layouts + Word documents |
| AI (primary) | Groq Cloud | Sub-second inference — critical for live voice flow |
| AI (secondary) | Google Gemini | Higher context window, free tier, deep reasoning |
| PDF generation | ReportLab | Pure Python, no browser/Chromium dependency |
| Frontend | Vanilla JS | Direct access to audio APIs, zero build step |
| Voice input | Web Speech API | Free, built into Chrome/Edge/Safari, no audio upload |
| Voice output | SpeechSynthesis | Free, built into all browsers, natural OS voices |
| Styling | Custom CSS | Full control, dark mode glassmorphism, fast load |

---

## What Makes This Project Unique

1. **The resume is the interview script** — Questions aren't generic; they're generated from your actual projects and experience
2. **Zero audio upload** — Your voice never leaves your device; only text transcripts are sent to the server
3. **Triple-tier AI fallback** — The interview never crashes; if Groq is down, Gemini takes over; if both are down, the rule engine runs
4. **Evidence-based scoring** — Every score is grounded in quotes from your transcript and cross-referenced with your resume
5. **No login required** — The entire experience is session-based; start an interview in 30 seconds
