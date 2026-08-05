let speechRecognition = null;
let silenceTimer = null;

function setOrbState(st) {
  STATE.orbState = st;
  const tag = document.getElementById('orbStateTag');
  if (tag) tag.textContent = st;
}

function speakAIText(text, cb) {
  if (!('speechSynthesis' in window)) { if (cb) cb(); return; }
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.onstart = () => setOrbState('SPEAKING');
  u.onend = () => { setOrbState('LISTENING'); if (cb) cb(); };
  window.speechSynthesis.speak(u);
}

function initSiriOrb() {
  const canvas = document.getElementById('siriOrbCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let angle = 0;

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const cx = canvas.width / 2, cy = canvas.height / 2;
    angle += 0.04;

    let r = 1;
    let c1 = '#06b6d4', c2 = '#6366f1';
    if (STATE.orbState === 'SPEAKING') { r = 1 + Math.sin(angle * 4) * 0.1; c1 = '#ec4899'; c2 = '#8b5cf6'; }
    else if (STATE.orbState === 'LISTENING') { r = 1 + Math.cos(angle * 2.5) * 0.06; c1 = '#10b981'; c2 = '#06b6d4'; }

    const g = ctx.createRadialGradient(cx, cy, 20 * r, cx, cy, 90 * r);
    g.addColorStop(0, c1); g.addColorStop(0.5, c2); g.addColorStop(1, 'transparent');
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.arc(cx, cy, 95 * r, 0, Math.PI * 2); ctx.fill();

    requestAnimationFrame(draw);
  }
  draw();
}

function startSpeechListening() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return;
  speechRecognition = new SR();
  speechRecognition.continuous = true;
  speechRecognition.interimResults = true;

  speechRecognition.onresult = (e) => {
    let t = '';
    for (let i = e.resultIndex; i < e.results.length; i++) t += e.results[i][0].transcript;
    document.getElementById('studioLiveTranscript').textContent = `Candidate: "${t}"`;
    document.getElementById('manualInput').value = t;
  };
  try { speechRecognition.start(); } catch(e){}
}
