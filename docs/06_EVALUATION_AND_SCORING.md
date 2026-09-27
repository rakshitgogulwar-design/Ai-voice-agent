# 06 — Evaluation & Scoring System

This document explains how I designed the multi-dimensional interview evaluation engine, the 10-dimension rubric, how the PDF assessment report is generated, and what each score means for the candidate.

---

## Design Philosophy: Evidence-Grounded Scoring

Most AI interview tools produce vague "good/bad" verdicts. I specifically designed this scoring system to be **evidence-grounded**:

1. Every score is accompanied by a **direct quote or specific observation** from the candidate's actual transcript.
2. Every score is cross-referenced against facts in the candidate's uploaded resume to detect **consistency or contradictions**.
3. Scores are never fabricated — if the AI cannot find evidence for a dimension, it assigns a **lower score with an explanation**, rather than guessing.

---

## The 10 Scoring Dimensions

Each answer is evaluated across 10 dimensions on a **1–5 scale**:

| # | Dimension | What It Measures |
| :--- | :--- | :--- |
| 1 | **Relevance** | Does the answer directly address what was asked? |
| 2 | **Completeness** | Does the answer cover all aspects of the question? |
| 3 | **Specificity** | Are there concrete details, numbers, names, and dates? |
| 4 | **Structure** | Does the answer follow a clear STAR pattern? |
| 5 | **Evidence & Examples** | Does the answer use real projects, tasks, or situations? |
| 6 | **Resume Consistency** | Does the answer align with the candidate's resume claims? |
| 7 | **Technical Depth** | Does the answer demonstrate genuine technical expertise? |
| 8 | **Communication Clarity** | Is the answer articulate and easy to follow? |
| 9 | **Conciseness** | Is the answer appropriately concise (avoids rambling)? |
| 10 | **Overall Readiness** | Holistic assessment of interview-readiness for this role |

### Score Scale Reference

| Score | Label | Meaning |
| :--- | :--- | :--- |
| 5 | Excellent | Exceeds expectations; concrete, specific, complete |
| 4 | Good | Meets expectations; minor gaps in detail or structure |
| 3 | Adequate | Partially meets expectations; needs more specifics |
| 2 | Developing | Notable gaps; vague or incomplete |
| 1 | Insufficient | Does not address the question or has major issues |

---

## How `score_answer_with_groq()` Works

```python
# backend/evaluator.py
def score_answer_with_groq(question, answer, resume_context="") -> Optional[Dict]:
```

The function sends the following structured prompt to Groq:

```
SYSTEM: You are an expert technical interviewer. Score the following answer
        across 10 dimensions. Return ONLY a JSON object — no prose.

USER:   Question: {question}
        Candidate's Answer: {answer}
        Resume Context: {resume_context}

        Return JSON:
        {
          "scores": [
            {
              "dimension": "Relevance",
              "score": 4,
              "evidence": "Candidate directly addressed Python usage..."
            },
            ...all 10 dimensions...
          ],
          "strengths": ["Strong STAR structure", "Mentioned specific metrics"],
          "improvements": ["Could add more context about team size"],
          "suggested_answer_structure": "Start with the situation..."
        }
```

### JSON Validation

The raw LLM response is parsed and validated before being stored:

```python
def _parse_scored_result(result: Dict) -> Optional[Dict]:
    """Validate all 10 dimensions are present with scores 1-5."""
    raw_scores = {item["dimension"]: item for item in result.get("scores", [])}
    if any(dim not in raw_scores for dim in DISPLAY_DIMENSIONS):
        return None  # Missing dimensions → reject and fall back
    scores = []
    for dim in DISPLAY_DIMENSIONS:
        s = raw_scores[dim]
        scores.append({
            "dimension": dim,
            "score": max(1.0, min(5.0, float(s.get("score", 3.0)))),
            "evidence": s.get("evidence", ""),
        })
    return {"scores": scores, ...}
```

---

## Overall Interview Score Calculation

At the end of the interview (`POST /api/interview/end`), `evaluate_full_interview()` aggregates all per-question scores:

```
overall_score = average of all per-answer "overall_readiness" dimension scores
              × completion_percentage_bonus
```

### Readiness Level Mapping

| Score Range | Readiness Level |
| :--- | :--- |
| 85–100 | 🟢 **Interview Ready** |
| 70–84 | 🔵 **Strong Candidate** |
| 55–69 | 🟡 **Good Foundation** |
| 40–54 | 🟠 **Developing** |
| 0–39 | 🔴 **Needs More Practice** |

---

## Communication Metrics

In addition to the 10 qualitative dimensions, the system computes **communication analytics** from the transcript:

| Metric | Measurement |
| :--- | :--- |
| **Average Answer Duration** | Mean seconds per response across all answers |
| **Speaking Pace** | Words per minute (WPM) based on duration + word count |
| **Filler Word Count** | Regex count of "um", "uh", "like", "you know", "basically", "sort of" |
| **Questions Requiring Repetition** | Count of follow-up questions triggered by insufficient answers |
| **Conciseness Rating** | `Excellent` / `Good` / `Fair` / `Needs Work` based on avg word count vs question type |

---

## Resume Consistency Checker

For each answer, the AI checks whether the candidate's claims are consistent with their resume:

```python
class ResumeConsistencyNote:
    statement:      str   # What the candidate claimed in their answer
    resume_context: str   # What the resume actually says
    status:         str   # "consistent" | "inconsistent" | "unverifiable"
```

Examples of consistency notes:
- ✅ *Consistent*: "Candidate said 'I led the backend migration' — resume confirms Senior Backend Engineer role at that company during that period."
- ⚠️ *Unverifiable*: "Candidate mentioned working with Kubernetes — resume lists Docker but does not mention Kubernetes."
- ❌ *Inconsistent*: "Candidate claimed '5 years of React experience' — resume shows first React project 2 years ago."

---

## Practice Roadmap Generation

The final evaluation includes a **prioritized practice plan** with specific action items:

```python
class PracticeRecommendation:
    priority:       int   # 1 (most urgent) to N
    recommendation: str   # What to practice
    rationale:      str   # Why this dimension scored lower
```

Example output:
```json
[
  {
    "priority": 1,
    "recommendation": "Quantify your achievements with numbers and metrics",
    "rationale": "3 of 5 answers scored below 3.0 on Specificity — answers lacked measurable impact"
  },
  {
    "priority": 2,
    "recommendation": "Practice the STAR answer structure for behavioral questions",
    "rationale": "Structure scores averaged 2.4/5 — answers often jumped to action without establishing context"
  }
]
```

---

## PDF Report Generator (`pdf_generator.py`)

The PDF assessment report is generated server-side using **ReportLab Canvas**:

```python
# backend/pdf_generator.py
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
```

### Report Sections

1. **Cover Page** — Candidate name, interview date, overall score badge, readiness level
2. **Executive Summary** — 3 strongest dimensions + top 3 improvement areas
3. **Dimension Scorecard** — Visual table of all 10 scores (1–5) with evidence quotes
4. **Question-by-Question Breakdown** — Each question, the full answer transcript, per-dimension scores, strengths, and suggested answer structure
5. **Communication Analytics** — Speaking pace, filler words, timing metrics
6. **Resume Consistency Report** — All consistency notes flagged by the AI
7. **Personalized Practice Roadmap** — Prioritized improvement action items

### Download Endpoint

```
GET /api/interview/{session_id}/pdf
```

Returns a `Content-Type: application/pdf` binary stream. The frontend triggers a browser download via:

```javascript
const blob = new Blob([await response.arrayBuffer()], {type: 'application/pdf'});
const url  = URL.createObjectURL(blob);
const a    = document.createElement('a');
a.href     = url;
a.download = `ResumeFlow_Assessment_${candidateName}.pdf`;
a.click();
```

---

## Key Source Files

| File | Key Functions |
| :--- | :--- |
| `backend/evaluator.py` | `score_answer()`, `score_answer_with_groq()`, `evaluate_full_interview()`, `generate_overall_evaluation()` |
| `backend/pdf_generator.py` | `generate_pdf_report()`, `generate_transcript_txt()`, `generate_transcript_json()` |
| `backend/models.py` | `EvaluationScore`, `InterviewEvaluationResult`, `CommunicationMetrics`, `PracticeRecommendation`, `ResumeConsistencyNote` |
