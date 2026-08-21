/* ═══════════════════════════════════════════════════════════════════
   ResumeFlow — Speech Module v2
   Natural human-sounding interviewer voice with pauses, pacing,
   and conversational rhythm. No robotic TTS.
   ═══════════════════════════════════════════════════════════════════ */

const Speech = {
  recognition: null,
  synthesis: window.speechSynthesis || null,
  audioContext: null,
  analyser: null,
  microphone: null,
  mediaStream: null,
  animationId: null,
  transcript: '',
  isListening: false,
  canvasCtx: null,
  waveformBars: [],
  _selectedVoice: null,
  _voiceReady: false,
  _pendingUtterances: [],
  _isSpeaking: false,

  /* ── Initialization ──────────────────────────────────────────── */
  init() {
    this.setupWaveform();
    this.checkVoiceSupport();
    this._selectBestVoice();
  },

  checkVoiceSupport() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    State.voiceAvailable = !!SpeechRecognition;
    if (!State.voiceAvailable) {
      document.getElementById('textInputArea').style.display = 'flex';
    }
  },

  /* ── Voice Selection — Find the most human-sounding voice ─────── */
  _selectBestVoice() {
    if (!this.synthesis) return;

    const pick = () => {
      const voices = this.synthesis.getVoices();
      if (!voices.length) return;

      // Priority order for natural-sounding English voices
      // macOS/iOS voices are generally more natural
      const preferred = [
        // macOS premium natural voices
        'Samantha',       // US female — warm, natural
        'Daniel',         // UK male — professional
        'Karen',          // Australian female — clear
        'Moira',          // Irish female — expressive
        'Tessa',          // South African female — warm
        'Veena',          // Indian female — clear
        'Alex',           // US male — natural pace
        // Google voices (decent quality)
        'Google UK English Female',
        'Google UK English Male',
        'Google US English',
        'Google English (US)',
        // Microsoft voices
        'Microsoft Zira',    // US female
        'Microsoft David',   // US male
        'Microsoft Mark',    // US male (Australian)
      ];

      for (const name of preferred) {
        const found = voices.find(v => v.name === name || v.name.includes(name));
        if (found) {
          this._selectedVoice = found;
          this._voiceReady = true;
          return;
        }
      }

      // Fallback: find any natural-sounding English voice
      // Prefer voices that are NOT local (remote voices sound better)
      const english = voices.filter(v => v.lang.startsWith('en'));
      const remote = english.filter(v => !v.localService);
      const local = english.filter(v => v.localService);

      if (remote.length > 0) {
        this._selectedVoice = remote[0];
      } else if (local.length > 0) {
        this._selectedVoice = local[0];
      } else if (english.length > 0) {
        this._selectedVoice = english[0];
      }

      this._voiceReady = true;
    };

    // Voices may load asynchronously
    pick();
    if (this.synthesis.onvoiceschanged !== undefined) {
      this.synthesis.onvoiceschanged = pick;
    }
  },

  /* ── Text-to-Speech — Natural Human Voice ─────────────────────── */
  speak(text, onEnd) {
    if (!this.synthesis) { if (onEnd) onEnd(); return; }

    // Cancel any ongoing speech
    this.synthesis.cancel();
    this._isSpeaking = false;

    // Split text into natural segments for pacing
    const segments = this._splitIntoSegments(text);
    this._speakSegments(segments, 0, onEnd);
  },

  /**
   * Split text into segments that will be spoken with natural pauses
   * between them, like a real person pausing for emphasis.
   */
  _splitIntoSegments(text) {
    // Split on sentence boundaries, keeping punctuation context
    const segments = [];
    // Split by sentence-ending punctuation
    const parts = text.split(/(?<=[.!?])\s+/);

    let buffer = '';
    for (const part of parts) {
      buffer += (buffer ? ' ' : '') + part;
      // Combine short consecutive sentences for flow
      if (buffer.length > 60 || part.match(/[.!?]$/)) {
        segments.push(buffer.trim());
        buffer = '';
      }
    }
    if (buffer.trim()) segments.push(buffer.trim());

    return segments.length > 0 ? segments : [text];
  },

  /**
   * Speak an array of text segments with natural pauses between them.
   * This creates the rhythm of a real person speaking — pausing
   * between thoughts, not robotically reading one continuous stream.
   */
  _speakSegments(segments, index, onEnd) {
    if (index >= segments.length) {
      this._isSpeaking = false;
      this._onSpeechEnd();
      if (onEnd) onEnd();
      return;
    }

    this._isSpeaking = true;
    const segment = segments[index];
    const utterance = new SpeechSynthesisUtterance(segment);

    // ── Voice Configuration — Natural Human Pacing ──
    // Vary rate slightly per segment for natural rhythm
    // Real people don't speak at a perfectly constant speed
    const baseRate = 0.88;  // Slightly slower than default — measured, professional
    const rateVariation = (Math.random() * 0.06) - 0.03; // ±0.03 variation
    utterance.rate = baseRate + rateVariation;

    // Slightly lower pitch for authority and warmth
    utterance.pitch = 0.95 + (Math.random() * 0.05); // 0.95-1.0 range
    utterance.volume = 1.0;

    // Apply selected voice
    if (this._selectedVoice) {
      utterance.voice = this._selectedVoice;
    }

    // UI updates
    utterance.onstart = () => {
      this._onSpeechStart();
    };

    utterance.onend = () => {
      // Natural pause between segments — like a real person
      // pausing between sentences for emphasis
      const pauseMs = this._calculatePause(index, segments.length);
      setTimeout(() => {
        this._speakSegments(segments, index + 1, onEnd);
      }, pauseMs);
    };

    utterance.onerror = (e) => {
      // Don't break on cancelled errors
      if (e.error !== 'canceled' && e.error !== 'interrupted') {
        console.warn('Speech synthesis error:', e.error);
      }
      // Try to continue with next segment
      this._speakSegments(segments, index + 1, onEnd);
    };

    this.synthesis.speak(utterance);
  },

  /**
   * Calculate natural pause duration between segments.
   * Longer pauses after questions, shorter between related statements.
   */
  _calculatePause(segmentIndex, totalSegments) {
    const isLast = segmentIndex === totalSegments - 1;

    // No pause after the last segment
    if (isLast) return 50;

    // Longer pause at end of a "thought" (after a period)
    // Shorter pause between comma-separated clauses
    return 250 + Math.floor(Math.random() * 200); // 250-450ms
  },

  _onSpeechStart() {
    const orb = document.getElementById('micOrb');
    const state = document.getElementById('micStateText');
    if (orb && !State.isRecording) {
      orb.className = 'recording-indicator active';
    }
    if (state) state.textContent = 'Speaking';
  },

  _onSpeechEnd() {
    const orb = document.getElementById('micOrb');
    const state = document.getElementById('micStateText');
    if (orb && !State.isRecording) {
      orb.className = 'recording-indicator';
    }
    if (state) state.textContent = 'Ready';
  },

  /**
   * Speak with a conversational lead-in.
   * e.g., "So, tell me about..." instead of just the raw question.
   */
  speakConversational(text, onEnd) {
    if (!this.synthesis) { if (onEnd) onEnd(); return; }
    this.synthesis.cancel();
    this._isSpeaking = false;

    // Don't add lead-ins to questions that already have them
    const conversationalText = this._makeConversational(text);
    const segments = this._splitIntoSegments(conversationalText);
    this._speakSegments(segments, 0, onEnd);
  },

  _makeConversational(text) {
    const trimmed = text.trim();

    // If already conversational (starts with So, Well, Now, etc.), return as-is
    if (/^(so|well|now|alright|okay|great|good|excellent|thank|I see|right|now then)/i.test(trimmed)) {
      return trimmed;
    }

    // For follow-up questions, add a brief acknowledgment
    if (State.currentQuestionIdx > 0) {
      const acks = [
        'Okay. ',
        'I see. ',
        'Alright. ',
        'Good. ',
        'Thank you for that. ',
        'Got it. ',
      ];
      const ack = acks[Math.floor(Math.random() * acks.length)];
      return ack + trimmed;
    }

    return trimmed;
  },

  stop() {
    if (this.synthesis) {
      this.synthesis.cancel();
      this._isSpeaking = false;
    }
    this._onSpeechEnd();
    this.stopListening();
  },

  /* ── Speech-to-Text ─────────────────────────────────────────── */
  async requestMic() {
    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.setupAudioContext(this.mediaStream);
      return true;
    } catch (err) {
      console.warn('Microphone access denied:', err);
      return false;
    }
  },

  startListening() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      document.getElementById('textInputArea').style.display = 'flex';
      return;
    }

    // Cancel any ongoing TTS
    if (this.synthesis) this.synthesis.cancel();
    this._isSpeaking = false;

    this.transcript = '';
    this.recognition = new SpeechRecognition();
    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.lang = 'en-US';

    this.recognition.onresult = (event) => {
      let interim = '';
      let final = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const t = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          final += t;
        } else {
          interim += t;
        }
      }
      if (final) this.transcript += final;

      // Show interim results in transcript area
      const body = document.getElementById('transcriptBody');
      const interimEl = document.getElementById('interimTranscript');
      if (interimEl) {
        interimEl.textContent = interim || this.transcript || 'Listening...';
      } else if (interim || this.transcript) {
        const div = document.createElement('div');
        div.id = 'interimTranscript';
        div.className = 'transcript-entry';
        div.innerHTML = `
          <div class="transcript-entry__role transcript-entry__role--candidate">You (speaking)</div>
          <div class="transcript-entry__text" style="color:var(--text-muted);font-style:italic">${interim || this.transcript || 'Listening...'}</div>
        `;
        body.appendChild(div);
        body.scrollTop = body.scrollHeight;
      }
    };

    this.recognition.onerror = (event) => {
      console.warn('Speech recognition error:', event.error);
      if (event.error === 'not-allowed') {
        App.toast('Microphone permission denied. Please allow microphone access.', 'error');
        App.updateRecordingUI(false);
        document.getElementById('textInputArea').style.display = 'flex';
      }
    };

    this.recognition.onend = () => {
      // Restart if still supposed to be recording
      if (State.isRecording && this.recognition) {
        try { this.recognition.start(); } catch (e) {}
      }
    };

    try {
      this.recognition.start();
      this.isListening = true;

      // Also start audio context for waveform if not started
      if (!this.mediaStream) {
        this.requestMic().then(ok => {
          if (!ok) {
            App.toast('Microphone access needed for voice input.', 'info');
          }
        });
      }
    } catch (err) {
      console.warn('Failed to start recognition:', err);
      document.getElementById('textInputArea').style.display = 'flex';
    }
  },

  stopListening() {
    if (this.recognition) {
      try { this.recognition.stop(); } catch (e) {}
      this.recognition = null;
    }
    this.isListening = false;
    this.stopWaveform();

    // Remove interim transcript element
    const interimEl = document.getElementById('interimTranscript');
    if (interimEl) interimEl.remove();
  },

  getTranscript() {
    return this.transcript.trim();
  },

  /* ── Audio Context & Waveform ───────────────────────────────── */
  setupAudioContext(stream) {
    try {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;
      this.microphone = this.audioContext.createMediaStreamSource(stream);
      this.microphone.connect(this.analyser);
    } catch (err) {
      console.warn('Failed to set up audio context:', err);
    }
  },

  setupWaveform() {
    const canvas = document.getElementById('waveformCanvas');
    if (!canvas) return;
    this.canvasCtx = canvas.getContext('2d');
    this.drawIdleWaveform();
  },

  drawIdleWaveform() {
    const canvas = document.getElementById('waveformCanvas');
    if (!canvas || !this.canvasCtx) return;
    const ctx = this.canvasCtx;
    const w = canvas.width;
    const h = canvas.height;

    ctx.clearRect(0, 0, w, h);

    // Draw subtle static waveform bars
    const barCount = 64;
    const barWidth = w / barCount - 1;
    const centerY = h / 2;

    for (let i = 0; i < barCount; i++) {
      const x = i * (barWidth + 1);
      const barH = 2 + Math.sin(i * 0.3) * 2;

      ctx.fillStyle = 'rgba(232, 115, 90, 0.12)';
      ctx.fillRect(x, centerY - barH / 2, barWidth, barH);
    }
  },

  startWaveform() {
    if (this.animationId) cancelAnimationFrame(this.animationId);
    const canvas = document.getElementById('waveformCanvas');
    if (!canvas || !this.canvasCtx) return;

    const ctx = this.canvasCtx;
    const w = canvas.width;
    const h = canvas.height;

    const draw = () => {
      this.animationId = requestAnimationFrame(draw);

      if (!this.analyser) {
        this.drawIdleWaveform();
        return;
      }

      const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
      this.analyser.getByteFrequencyData(dataArray);

      ctx.clearRect(0, 0, w, h);

      const barCount = 64;
      const barWidth = w / barCount - 1;
      const centerY = h / 2;

      for (let i = 0; i < barCount; i++) {
        const dataIndex = Math.floor(i * (dataArray.length / barCount));
        const value = dataArray[dataIndex] || 0;
        const barH = Math.max(2, (value / 255) * h * 0.8);

        // Warm color gradient based on intensity
        const intensity = value / 255;
        const r = Math.round(232 + (52 - 232) * intensity * 0.3);
        const g = Math.round(115 + (199 - 115) * intensity * 0.5);
        const b = Math.round(90 + (123 - 90) * intensity * 0.3);
        ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${0.2 + intensity * 0.8})`;

        ctx.fillRect(x, centerY - barH / 2, barWidth, barH);
      }
    };

    draw();
  },

  stopWaveform() {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }
    this.drawIdleWaveform();
  },
};

/* ── Patch App.toggleRecording to use waveform ─────────────────── */
const _origToggleRecording = App.toggleRecording.bind(App);
App.toggleRecording = function() {
  if (State.isRecording) {
    Speech.stopWaveform();
    _origToggleRecording();
  } else {
    _origToggleRecording();
    if (State.isRecording) {
      Speech.startWaveform();
    }
  }
};
