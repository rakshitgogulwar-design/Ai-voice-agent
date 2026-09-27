# 02 — Technology Stack Deep-Dive

In this document, I break down all the technologies, frameworks, and packages chosen for ResumeFlow, explaining exactly what each component does and why I selected it.

---

## Complete Technology Matrix

| Layer | Technology | Version | Purpose in Project |
| :--- | :--- | :--- | :--- |
| **Backend Framework** | **FastAPI** | `>=0.100.0` | Asynchronous REST API routing, request validation, and static file serving |
| **ASGI Web Server** | **Uvicorn** | `>=0.22.0` | High-performance lightning-fast async HTTP server |
| **Database ORM** | **SQLAlchemy** | `>=2.0.0` | Object Relational Mapping for SQLite models and database migrations |
| **Database** | **SQLite** | Built-in | Embedded zero-configuration transactional database |
| **Data Validation** | **Pydantic** | `>=2.0.0` | Strict data schemas, serializing models, and payload typing |
| **File Parsing** | **pdfplumber** | `>=0.10.0` | Precise text, table, and layout extraction from candidate PDFs |
| **File Parsing** | **python-docx** | `>=1.0.0` | Paragraph and section extraction from Microsoft Word documents |
| **PDF Generation** | **ReportLab** | `>=4.0.0` | Programmatic multi-page canvas PDF generation for the assessment report |
| **HTTP Client** | **Requests** | `>=2.31.0` | Synchronous REST requests communicating with Groq and Gemini APIs |
| **Environment** | **python-dotenv** | `>=1.0.0` | Loading `.env` secrets into OS environment |
| **Async Files** | **aiofiles** | `>=23.1.0` | Non-blocking file writes for temporary resume buffering |
| **Multipart** | **python-multipart** | `>=0.0.6` | Form-data parser for file uploads |
| **Frontend Core** | **Vanilla ES6+ JS** | Native | DOM manipulation, state transitions, audio event listeners |
| **Styling** | **Custom CSS3** | Native | Dark mode glassmorphism UI, flexbox/grid layouts, micro-animations |
| **Voice Processing** | **Web Speech API** | Native | Browser STT (`SpeechRecognition`) & TTS (`SpeechSynthesis`) |
| **AI LLM 1** | **Groq API** | `gpt-oss-120b` | Ultra-fast LPU inference for real-time STAR questions & scoring |
| **AI LLM 2** | **Google Gemini API**| `gemini-3.8-flash`| Multi-tier deep reasoning fallback engine for evaluations |

---

## Detailed Tech Breakdown

### 1. Backend: FastAPI & Uvicorn
- **Why FastAPI**: 
  - Automatic OpenAPI documentation (accessible live at `/docs`).
  - Native integration with Pydantic v2 ensures strict typing and input sanitation.
  - Asynchronous event loops allow handling multiple concurrent interview sessions effortlessly.
- **Why Uvicorn**: 
  - Built on `uvloop` (an ultra-fast C-based asyncio event loop implementation).
  - Handles reload on code changes during development and production ASGI workers in Docker.

### 2. Database: SQLite + SQLAlchemy 2.0
- **Why SQLite**: 
  - Zero external database setup (no need to manage PostgreSQL/MySQL clusters for local or container deployment).
  - Entire interview history, transcripts, and scores are preserved in a single, robust file (`interviewpro.db`).
- **Why SQLAlchemy 2.0**:
  - Provides a clean declarative schema pattern (`Base = declarative_base()`).
  - Decouples raw SQL queries from application logic, making it easy to swap SQLite for PostgreSQL if scaling to a distributed cluster.

### 3. Parsing: `pdfplumber` & `python-docx`
- Resume formats vary drastically. Standard regex over raw text often drops formatting:
  - `pdfplumber` inspects character coordinates, preserves tabular formatting, and handles multi-column resumes.
  - `python-docx` extracts structured paragraphs, runs, and headings from `.docx` files.

### 4. PDF Reporting: ReportLab
- Generates pixel-perfect, print-ready PDF assessment reports:
  - Includes candidate scorecards, 10-dimension breakdowns, strengths, improvements, and practice roadmaps.
  - Uses `SimpleDocTemplate`, `Table`, `Paragraph`, and custom `ParagraphStyle` palettes without external rendering engines like Chromium or WeasyPrint.

### 5. Frontend: Vanilla JS & Native CSS
- **Why Not React/Next.js/Vue?**:
  - The application relies heavily on browser hardware features (Microphone streams, Web Speech recognition events, AudioContext frequencies).
  - Writing this in Vanilla JavaScript eliminates the React synthetic event wrapper overhead and avoids dependency on React state cycles that can interfere with real-time audio listeners.
  - Results in a package that loads instantly (<100ms) with zero compilation step.

### 6. Voice & Audio: Web Speech API
- `window.SpeechRecognition` (and `webkitSpeechRecognition`):
  - Listens continuously, delivers real-time partial transcripts, and fires events when speech ends.
- `window.speechSynthesis`:
  - Converts question text into a smooth, natural human voice.
  - Emits `onstart` and `onend` events that coordinate the interviewer state (e.g. disabling the microphone while the interviewer is speaking to prevent audio feedback loop).
