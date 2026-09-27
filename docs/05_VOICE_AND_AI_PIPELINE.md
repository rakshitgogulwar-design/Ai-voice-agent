# 05 — Voice & AI Pipeline

This document details how the voice processing stack and multi-tier AI pipeline work together to deliver real-time, adaptive interview conversations.

---

## Overview: The Three-Tier AI Architecture

I engineered the system with **graceful degradation** — it never crashes even if all external AI APIs are unavailable:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AI PROVIDER HIERARCHY                         │
│                                                                      │
│  Tier 1 (Primary)   ──►  GROQ Cloud (openai/gpt-oss-120b via LPU)   │
│       │ if unavailable / rate-limited                                │
│       ▼                                                              │
│  Tier 2 (Secondary) ──►  Google Gemini (gemini-3.8-flash)            │
│       │ if unavailable / quota exceeded                              │
│       ▼                                                              │
│  Tier 3 (Fallback)  ──►  Rule-Based Python Engine (always works)     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Tier 1: Groq Cloud (`openai/gpt-oss-120b`)

### What It Does
Groq is used as the **primary AI engine** for:
- Real-time STAR question generation (during `/api/interview/start`)
- Adaptive follow-up question generation (during `/api/interview/answer`)
- Per-answer dimensional scoring (10-dimension evaluation rubric)

### Why Groq
Groq runs inference on custom **LPU (Language Processing Unit)** hardware that delivers approximately `0.6 seconds` per generation response. This is critical for the voice interview experience — if question generation takes 3–5 seconds, the candidate experiences an awkward silence.

### Configuration

```python
# backend/evaluator.py
def _groq_config() -> Optional[Dict[str, str]]:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or api_key.startswith("your_"):
        return None
    return {
        "api_url": "https://api.groq.com/openai/v1/chat/completions",
        "api_key":  api_key,
        "model":    os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
    }
```

The model ID is configurable via `GROQ_MODEL` environment variable, so you can swap to `llama3-70b-8192` or other Groq-hosted models without any code changes.

### API Call Pattern

```python
response = requests.post(
    cfg["api_url"],
    headers={"Authorization": f"Bearer {cfg['api_key']}"},
    json={
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 2048,
    },
    timeout=30,
)
```

---

## Tier 2: Google Gemini (`gemini-3.8-flash`)

### What It Does
Gemini serves as the **secondary AI engine** when Groq is unavailable. It also acts as a **deep evaluator** for overall interview scoring because of its longer context window.

### Configuration

```python
# backend/evaluator.py
def _gemini_config() -> Optional[Dict[str, str]]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key.startswith("your_"):
        return None
    return {
        "api_key": api_key,
        "model":   os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
    }
```

### Gemini API Call Pattern (REST)

```python
url = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{cfg['model']}:generateContent?key={cfg['api_key']}"
)
response = requests.post(url, json={
    "contents": [{"parts": [{"text": prompt}]}],
    "generationConfig": {
        "temperature": 0.7,
        "maxOutputTokens": 2048,
    }
}, timeout=30)
```

---

## Tier 3: Rule-Based Fallback Engine

When both Groq and Gemini are unreachable, the Python fallback engine computes deterministic scores using observable metrics from the candidate's answer text:

| Metric | How Calculated |
| :--- | :--- |
| **Speaking Pace** | Word count ÷ duration in seconds |
| **Filler Word Count** | Regex matches for "um", "uh", "like", "you know", "basically", etc. |
| **Answer Length Score** | Whether answer word count falls within the expected range for the question type |
| **STAR Structure Detection** | Keyword presence checks for "situation", "task", "I did", "the result was" |
| **Resume Keyword Presence** | Whether answer references terms extracted from candidate's parsed profile |

This guarantees the evaluation pipeline **never returns an error** regardless of external API status.

---

## Voice Processing Stack

The voice pipeline runs entirely in the **browser** — no audio data is ever transmitted to the backend.

### Text-to-Speech (TTS) — Interviewer Voice

```javascript
// speech.js
Speech.speak(text, onEndCallback) {
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.voice  = Speech._selectedVoice;  // Best available OS voice
  utterance.rate   = 0.92;  // Slightly slower than default for natural pacing
  utterance.pitch  = 1.0;
  utterance.volume = 1.0;
  utterance.onend  = onEndCallback;  // Triggers microphone open after speaking
  window.speechSynthesis.speak(utterance);
}
```

**Voice selection priority** (most natural → least natural):
1. macOS `Samantha` (warm, natural US female)
2. macOS `Daniel` (professional UK male)
3. macOS `Karen`, `Moira`, `Tessa`, `Veena`, `Alex`
4. `Google UK English Female` / `Google UK English Male`
5. Any `en-US` or `en-GB` voice
6. Any available English voice

### Speech-to-Text (STT) — Candidate Listening

```javascript
Speech.startListening() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  this.recognition = new SpeechRecognition();
  this.recognition.continuous     = true;   // Keep listening until silence
  this.recognition.interimResults = true;   // Show live partial transcript
  this.recognition.lang           = 'en-US';
  this.recognition.onresult = (e) => {
    // Build final transcript from all result segments
    this.transcript = Array.from(e.results)
      .map(r => r[0].transcript)
      .join(' ');
  };
  this.recognition.onspeechend = () => {
    this.stopListening(); // Silence detected → submit answer
  };
  this.recognition.start();
}
```

### Audio State Management

To prevent **audio feedback loops** (the interviewer voice being picked up by the microphone as input):

```
TTS Speak starts
      │
      │ speech.synthesis.onstart fires
      ▼
Microphone is DISABLED (recognition.stop() + mediaStream tracks suspended)
      │
      │ speech.synthesis.onend fires
      ▼
Microphone is ENABLED (recognition.start() resumes)
```

---

## Adaptive Follow-Up Logic

After each answer, the backend evaluates whether a follow-up question is warranted:

```python
# backend/interview_generator.py
def should_ask_followup(answer_text: str, question_category: str, score: float) -> bool:
    """Determine if the answer warrants a follow-up probe."""
    # Trigger follow-up if:
    # 1. Answer is very short (< 30 words) for a technical question
    # 2. Score is below threshold (< 3.0 out of 5.0)
    # 3. Answer lacks specificity markers (no numbers, names, or project references)
    word_count = len(answer_text.split())
    needs_expansion = word_count < 30 and question_category in ["technical_skills", "project_deep_dive"]
    low_quality = score < 3.0
    return needs_expansion or low_quality
```

When triggered, `generate_followup()` calls Groq/Gemini with the original question, the candidate's answer, and the resume context to generate a targeted clarification probe (e.g., *"You mentioned React — can you describe a specific component you built and what problem it solved?"*).

---

## End-to-End Request Flow (Single Question Turn)

```
Browser                    FastAPI Backend              Groq / Gemini
   │                             │                           │
   │── POST /api/interview/answer ──►                        │
   │   {session_id, question_id,  │                          │
   │    answer_text, duration}    │                          │
   │                             │── score_answer_with_groq()──►
   │                             │                           │ (0.6s)
   │                             │◄── JSON scores, strengths ─┤
   │                             │    improvements, suggested │
   │                             │    structure               │
   │                             │                           │
   │                             │── should_ask_followup() ──►(local)
   │                             │   [if True]               │
   │                             │── generate_followup() ────►
   │                             │                           │ (0.8s)
   │                             │◄── follow_up question text┤
   │                             │                           │
   │◄── {answer_id, follow_up} ──│                           │
   │                             │                           │
   │  [if follow_up != null]     │                           │
   │── Speech.speak(follow_up) ──►(local TTS)                │
   │── Speech.startListening() ──►(local STT)                │
```

---

## Environment Variables Reference

All AI provider keys are loaded from `.env`:

```ini
# Groq (Primary AI Engine)
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-120b   # Optional — this is the default

# Google Gemini (Secondary AI Engine)
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-3.8-flash    # Optional — this is the default
```

To get free API keys:
- **Groq**: https://console.groq.com/keys (Free tier: 14,400 req/day)
- **Gemini**: https://aistudio.google.com/app/apikey (Free tier: 1,500 req/day)
