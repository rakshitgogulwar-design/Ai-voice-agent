const STATE = {
  sessionId: null,
  company: 'Amazon',
  role: 'Senior Software Engineer',
  exp: 'Mid-Level',
  personaId: 'dm',
  currentRoundIdx: 0,
  currentQuestionIdx: 0,
  transcripts: [],
  orbState: 'IDLE'
};

const API_BASE = window.location.port ? `http://localhost:${window.location.port}/api` : 'http://localhost:8005/api';

window.addEventListener('DOMContentLoaded', () => {
  if (typeof renderPersonas === 'function') renderPersonas();
  if (typeof initSiriOrb === 'function') initSiriOrb();
});

function switchView(viewId) {
  document.querySelectorAll('.view-section').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-tab-btn').forEach(b => b.classList.remove('active'));
  
  const target = document.getElementById(viewId);
  if (target) target.classList.add('active');

  const btn = Array.from(document.querySelectorAll('.nav-tab-btn')).find(b => b.getAttribute('onclick')?.includes(viewId));
  if (btn) btn.classList.add('active');

  if (viewId === 'reportView') {
    renderGraphicalCharts();
  }
}

function startInterviewSession() {
  STATE.company = document.getElementById('setupCompany').value;
  STATE.role = document.getElementById('setupRole').value;
  STATE.exp = document.getElementById('setupExp').value;

  fetch(`${API_BASE}/session/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      company: STATE.company,
      role: STATE.role,
      experience: STATE.exp,
      persona_id: STATE.personaId
    })
  })
  .then(res => res.json())
  .then(data => {
    STATE.sessionId = data.session_id;
    document.getElementById('studioQuestionText').textContent = data.initial_question;
    switchView('studioView');
    speakAIText(data.initial_question, () => startSpeechListening());
  })
  .catch(() => {
    switchView('studioView');
    document.getElementById('studioQuestionText').textContent = `Welcome to your ${STATE.company} interview! Please introduce yourself and your background.`;
  });
}
