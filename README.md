# InterviewPro AI — Enterprise Full-Stack AI Mock Interview Platform

Production-grade 1-on-1 AI mock interview platform featuring a **Python FastAPI backend**, **SQLite/SQLAlchemy database**, **C native code evaluator engine**, **modular JavaScript/CSS frontend**, and **Chart.js graphical reporting**.

---

## Project Architecture & Stack

- **Backend**: Python 3.10+ with FastAPI, Uvicorn, SQLAlchemy, Pydantic, Subprocess Code Runner.
- **Database**: SQLite (`interviewpro.db`) with Session Persistence, Transcript Logs, Code Submissions, and Assessment Reports.
- **Native Engine**: C Language Code Evaluator (`engine/evaluator.c`) for microsecond timing and performance benchmarking.
- **Frontend**: HTML5, CSS3, JavaScript (Modular ES6), Chart.js Graphical Analytics, Web Speech API (STT & TTS).

---

## Directory Structure

```
Ai voice agent/
├── backend/
│   ├── app.py                # FastAPI REST Server & Session Controller
│   ├── database.py           # SQLAlchemy SQLite Models & Persistence
│   └── code_runner.py        # Multi-Language Code Compilation Engine
├── engine/
│   ├── evaluator.c           # Native C Performance Benchmarking Engine
│   └── Makefile              # C Build Instructions
├── frontend/
│   ├── index.html            # Production Frontend Dashboard
│   └── static/
│       ├── css/
│       │   └── style.css     # Production Design System & Dark Theme
│       └── js/
│           ├── app.js        # REST API Client & View Router
│           ├── speech.js     # Web Speech Recognition & Siri Orb Canvas
│           ├── ide.js        # Multi-Language IDE Execution Client
│           └── charts.js     # Chart.js Graphical Reporting Module
├── requirements.txt          # Python Backend Dependencies
├── README.md                 # Full-Stack Documentation
└── interviewpro_ai_app.html  # Standalone Single-File Launcher
```

---

## How to Run the Full-Stack Application

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch FastAPI Backend Server
```bash
uvicorn backend.app:app --port 8000 --reload
```
- Open Swagger API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Open Frontend Web Application: [http://localhost:8000/static/index.html](http://localhost:8000/static/index.html) or [http://localhost:3000/interviewpro_ai_app.html](http://localhost:3000/interviewpro_ai_app.html)

### 3. Compile Native C Engine (Optional)
```bash
cd engine
make
./evaluator
```
