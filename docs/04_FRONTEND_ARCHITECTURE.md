# 04 — Frontend Architecture & Design System

This document explains how I designed and built the entire client-side application — from the HTML structure and CSS design system to the JavaScript state machine and audio visualizer.

---

## Directory Layout

```
frontend/
├── index.html              # Single-Page Application shell (all views embedded)
└── static/
    ├── css/
    │   └── style.css       # Complete design system (~1700 lines, zero dependencies)
    └── js/
        ├── app.js          # Main application controller, state machine, API client
        └── speech.js       # Voice engine (TTS + STT + Audio Waveform Visualizer)
```

---

## Why Vanilla JS (No Framework)

I deliberately chose **not** to use React, Vue, or Angular. Here is why:

| Criterion | Vanilla JS SPA | React/Next.js |
| :--- | :--- | :--- |
| **Build step required** | ❌ None | ✅ `npm run build` every time |
| **Audio API compatibility** | ✅ Direct native access | ⚠️ Synthetic event wrappers can interfere |
| **Initial load time** | ✅ `< 100 ms` (pure HTML+JS) | ❌ Bundle parse + hydration overhead |
| **SpeechRecognition timing** | ✅ Synchronous native control | ⚠️ React lifecycle delays recognition events |
| **Deployment complexity** | ✅ Zero — just static files | ❌ Node server or CDN pipeline needed |

The Web Speech API fires rapid-fire events (`onresult`, `onaudioend`, `onspeechend`) that must be handled synchronously. A React re-render cycle would introduce enough delay to cause dropped recognition frames during live voice interaction.

---

## Application State Machine (`app.js`)

The entire app is built as a **finite state machine** with 5 views:

```
      ┌──────────┐
      │ LANDING  │  (Hero page, "Start My Interview" CTA)
      └────┬─────┘
           │ navigate('upload')
           ▼
      ┌──────────┐
      │  UPLOAD  │  (File drop zone + text input fallback)
      └────┬─────┘
           │ POST /api/resume/upload → success
           ▼
      ┌──────────┐
      │  REVIEW  │  (Candidate verifies extracted profile before interview)
      └────┬─────┘
           │ POST /api/interview/start → success
           ▼
      ┌───────────┐
      │ INTERVIEW │  (Voice loop: TTS question → STT listen → POST answer)
      └─────┬─────┘
            │ POST /api/interview/end → success
            ▼
      ┌─────────┐
      │ RESULTS │  (Scorecard dashboard + PDF download)
      └─────────┘
```

### Global State Object

```javascript
const State = {
  resumeId: null,         // UUID of the uploaded resume record
  sessionId: null,        // UUID of the active interview session
  profile: null,          // CandidateProfile JSON from resume parsing
  questions: [],          // Array of InterviewQuestionModel objects
  currentQuestionIdx: 0,  // Which question is currently active
  isRecording: false,     // Is the microphone currently open?
  isPaused: false,        // Is the interview paused?
  interviewStartTime: null,
  timerInterval: null,
  questionStartTime: null,
  elapsedSeconds: 0,
  transcripts: [],        // Live transcript log
  consentGiven: false,    // Microphone consent flag
  voiceAvailable: false,  // Detected: is Web Speech API supported?
};
```

---

## CSS Design System (`style.css`)

The entire visual layer is built using a hand-crafted CSS custom property design system.

### Color Palette (Dark Mode)

```css
:root {
  --bg-base:          #0a0a0f;    /* Near-black base background */
  --bg-surface:       #111118;    /* Card surfaces */
  --bg-elevated:      #18181f;    /* Modals and overlays */
  --border:           #2a2a35;    /* Subtle dividers */
  --text-primary:     #f0eff4;    /* Primary readable text */
  --text-secondary:   #8b8a99;    /* Muted labels and captions */
  --accent:           #c2492b;    /* Primary brand accent (warm crimson) */
  --accent-gold:      #b97e12;    /* Secondary accent (gold) */
  --accent-hover:     #d4543a;    /* Hover state for accent */
}
```

### Glassmorphism Cards

```css
.card {
  background:  rgba(17, 17, 24, 0.85);
  border:      1px solid rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(18px);
  border-radius: 16px;
}
```

### Typography

Three typeface families loaded from Google Fonts:

| Family | Usage |
| :--- | :--- |
| `Inter` (400/500/600/700) | Body text, labels, buttons |
| `Fraunces` (italic, display) | Hero headlines — editorial serif |
| `IBM Plex Mono` (400/500) | Code blocks, score metrics, data rendering |

---

## Interview Voice Loop

```
1. App.askQuestion(question)
        │
        ▼
2. Speech.speak(question.text)           ← TTS: browser reads question aloud
        │ onend event fires
        ▼
3. Speech.startListening()               ← STT: mic opens, recognition starts
        │ onresult fires (partial transcripts)
        │ onspeechend fires (silence detected)
        ▼
4. App.submitAnswer(transcript, duration) ← Sends text + duration to backend
        │
        ▼
5. POST /api/interview/answer            ← Backend scores the answer
        │ response includes optional follow_up
        ▼
6. if (follow_up) → App.askQuestion(follow_up)
   else           → App.askNextQuestion()
        │
        ▼
7. Repeat until all questions answered → POST /api/interview/end
```

---

## Audio Waveform Visualizer

When the mic is active, a canvas-based waveform visualizer renders in real time using the WebAudio API:

```javascript
const analyser = audioContext.createAnalyser();
analyser.fftSize = 128;
microphone.connect(analyser);
// 40 animated bars at 60fps via requestAnimationFrame
// Each bar height = amplitude at that frequency bucket
```

### Fallback Text Mode

If `webkitSpeechRecognition` is not available (e.g. Firefox), the app automatically:
1. Hides the microphone button
2. Reveals a `<textarea>` text input
3. Displays a clear compatibility notice

---

## Key Frontend Files Reference

| File | Lines | Purpose |
| :--- | :--- | :--- |
| `frontend/index.html` | 490 | Full SPA shell with all 5 views pre-rendered |
| `frontend/static/js/app.js` | 775 | State machine, API calls, results dashboard |
| `frontend/static/js/speech.js` | 501 | TTS engine, STT recognition, waveform visualizer |
| `frontend/static/css/style.css` | ~1700 | Complete design system |
