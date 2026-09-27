# 01 — System Overview & Architecture

## Project Vision & Motivation

I designed and engineered **ResumeFlow Interview Studio** as a full-stack, AI-powered conversational platform that bridges the gap between passive resume screening and live voice interviews.

Traditional interview preparation tools either provide generic text questions or require human coaches. I built ResumeFlow to provide a **personalized, real-time voice interview experience** where:
1. The AI reads and extracts the candidate's actual projects, skills, and metrics from their resume.
2. The AI generates tailored, conversational questions using the **STAR methodology** (Situation, Task, Action, Result).
3. The candidate conducts the interview completely hands-free using natural speech.
4. The AI listens, identifies vague answers or missing details in real-time, and generates **adaptive follow-up probes**.
5. At the conclusion, the candidate receives an evidence-based evaluation across 10 dimensions, complete with a professional downloadable PDF assessment.

---

## High-Level Execution Architecture

The system operates across **5 discrete stages**:

```
+---------------------------------------------------------------------------------+
|                                 1. CLIENT TIER                                  |
|   - Vanilla JS SPA (No heavy bundle, zero build step, instant load)             |
|   - Browser Web Speech Recognition (STT) + Speech Synthesis (TTS)               |
|   - Canvas Audio Waveform Visualizer + Fallback Text Mode                       |
+----------------------------------------+----------------------------------------+
                                         | HTTP REST (JSON / Multipart)
                                         v
+---------------------------------------------------------------------------------+
|                             2. API GATEWAY & SERVER                             |
|   - FastAPI (Asynchronous Python REST Framework)                                |
|   - CORS Middleware + Static File Mounts (/static)                              |
|   - Endpoints: /api/resume/*, /api/interview/*, /api/health                     |
+----------------------------------------+----------------------------------------+
                                         |
         +-------------------------------+-------------------------------+
         |                                                               |
         v                                                               v
+----------------------------------+            +----------------------------------+
|      3. INGESTION & DATA         |            |        4. AI ENGINE TIER         |
| - pdfplumber & python-docx       |            | - Groq Cloud (gpt-oss-120b)      |
| - Regex fact extraction          |            | - Google Gemini (3.8 Flash)      |
| - SQLite + SQLAlchemy ORM        |            | - Rule-Based Engine (Fallback)   |
+----------------------------------+            +----------------------------------+
                                         |
                                         v
+---------------------------------------------------------------------------------+
|                                5. OUTPUT TIER                                   |
|   - Interactive Results Dashboard (Scorecards, Strengths, Improvements)         |
|   - Server-Side PDF Generator (ReportLab Canvas Engine)                         |
|   - Exportable Raw Transcripts (JSON & Text)                                    |
+---------------------------------------------------------------------------------+
```

---

## Why I Made These Key Architecture Decisions

### 1. Browser-Native Web Speech API vs. Cloud Speech APIs (Whisper/ElevenLabs)
- **Zero Audio Transfer Overhead**: Instead of recording large `.wav` files on the client and uploading megabytes of audio to the server, transcription happens natively on the user's device via `webkitSpeechRecognition`.
- **Zero Latency Audio Playback**: The interviewer speaks using `window.speechSynthesis`. This eliminates network buffering delays and API audio streaming fees.
- **Privacy First**: Raw microphone audio is never uploaded to or stored on our servers; only clean textual transcripts are transmitted.

### 2. Multi-Tier AI Provider Orchestration
- Relying on a single AI provider causes brittle failures when rate limits or service outages occur.
- I structured the AI engine with a primary-secondary fallback hierarchy:
  - **Tier 1 (Groq)**: Uses `openai/gpt-oss-120b` running on Groq LPUs. Delivers sub-second (~0.6s) generation for live question turns.
  - **Tier 2 (Google Gemini)**: Uses `gemini-3.8-flash` via Google's Generative Language API. Offers high-context reasoning and acts as the deep evaluator.
  - **Tier 3 (Rule Engine)**: If both external APIs are unreachable, deterministic Python heuristics calculate speaking rates, filler words, and fallback rubrics to ensure the interview never crashes.

### 3. Lightweight Vanilla JavaScript Frontend
- Rather than bloating the client with a heavy React/Next.js bundle that requires build pipelines and hydration, I crafted a clean Vanilla ES6 Single-Page Application (`app.js` and `speech.js`).
- State transitions (Landing $\rightarrow$ Upload $\rightarrow$ Review $\rightarrow$ Interview $\rightarrow$ Results) are managed instantaneously via a lightweight state machine.
