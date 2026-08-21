"""
PDF Report Generator Module
Generates professional PDF interview reports using reportlab.
"""

import os
import json
from datetime import datetime
from io import BytesIO

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


def _get_score_color(score: float, max_score: float = 5.0) -> colors.Color:
    """Get color based on score value."""
    ratio = score / max_score
    if ratio >= 0.8:
        return colors.HexColor("#10b981")  # Emerald
    elif ratio >= 0.6:
        return colors.HexColor("#3b82f6")  # Blue
    elif ratio >= 0.4:
        return colors.HexColor("#f59e0b")  # Amber
    else:
        return colors.HexColor("#ef4444")  # Red


def _get_styles():
    """Get custom paragraph styles."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='ReportTitle',
        parent=styles['Title'],
        fontSize=24,
        spaceAfter=6,
        textColor=colors.HexColor("#1e293b"),
        fontName='Helvetica-Bold',
    ))

    styles.add(ParagraphStyle(
        name='ReportSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=12,
        textColor=colors.HexColor("#64748b"),
        alignment=TA_CENTER,
    ))

    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=16,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor("#1e293b"),
        fontName='Helvetica-Bold',
        borderWidth=0,
        borderPadding=0,
    ))

    styles.add(ParagraphStyle(
        name='SubHeader',
        parent=styles['Heading3'],
        fontSize=13,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor("#334155"),
        fontName='Helvetica-Bold',
    ))

    styles.add(ParagraphStyle(
        name='BodyText2',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        textColor=colors.HexColor("#475569"),
        leading=14,
    ))

    styles.add(ParagraphStyle(
        name='SmallText',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor("#94a3b8"),
        leading=10,
    ))

    styles.add(ParagraphStyle(
        name='ScoreText',
        parent=styles['Normal'],
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor("#1e293b"),
    ))

    styles.add(ParagraphStyle(
        name='Disclaimer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor("#94a3b8"),
        alignment=TA_CENTER,
        spaceBefore=20,
    ))

    return styles


def _header_footer(canvas, doc):
    """Add header and footer to each page."""
    canvas.saveState()

    # Header
    canvas.setFont('Helvetica-Bold', 9)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(72, letter[1] - 36, "ResumeFlow Interview Studio")
    canvas.setFont('Helvetica', 8)
    canvas.drawRightString(letter[0] - 72, letter[1] - 36, "Interview Assessment Report")

    # Header line
    canvas.setStrokeColor(colors.HexColor("#e2e8f0"))
    canvas.setLineWidth(0.5)
    canvas.line(72, letter[1] - 44, letter[0] - 72, letter[1] - 44)

    # Footer
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor("#94a3b8"))
    canvas.drawString(72, 36, "This report is an assessment and coaching aid. It is not a hiring decision.")
    canvas.drawRightString(letter[0] - 72, 36, f"Page {doc.page}")

    # Footer line
    canvas.line(72, 48, letter[0] - 72, 48)

    canvas.restoreState()


def generate_pdf_report(evaluation_data: dict, output_path: str = None) -> str:
    """
    Generate a professional PDF report from interview evaluation data.

    Args:
        evaluation_data: Complete evaluation data dictionary
        output_path: Path to save the PDF. If None, returns bytes.

    Returns:
        Path to the generated PDF file, or bytes if no path provided.
    """
    if not HAS_REPORTLAB:
        raise RuntimeError(
            "reportlab is required for PDF generation. "
            "Install it with: pip install reportlab"
        )

    styles = _get_styles()

    if output_path:
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=60,
            bottomMargin=60,
        )
    else:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=60,
            bottomMargin=60,
        )

    elements = []

    # ── Title ──────────────────────────────────────────────────────
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("Interview Assessment Report", styles['ReportTitle']))
    elements.append(Paragraph("ResumeFlow Interview Studio", styles['ReportSubtitle']))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", color=colors.HexColor("#e2e8f0"), thickness=1))
    elements.append(Spacer(1, 15))

    # ── Candidate Info ─────────────────────────────────────────────
    candidate_name = evaluation_data.get("candidate_name", "Candidate")
    resume_filename = evaluation_data.get("resume_filename", "resume")
    interview_date = evaluation_data.get("interview_date", datetime.now().strftime("%B %d, %Y"))
    duration = evaluation_data.get("duration_seconds", 0)
    duration_str = f"{int(duration // 60)}m {int(duration % 60)}s" if duration > 0 else "N/A"

    info_data = [
        ["Candidate", candidate_name],
        ["Resume File", resume_filename],
        ["Interview Date", interview_date],
        ["Duration", duration_str],
        ["Questions Asked", str(evaluation_data.get("total_questions", 0))],
        ["Follow-up Questions", str(evaluation_data.get("total_followups", 0))],
        ["Completion", f"{evaluation_data.get('completion_percentage', 0)}%"],
    ]

    info_table = Table(info_data, colWidths=[2.5*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor("#475569")),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor("#1e293b")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 15))

    # ── Overall Scorecard ──────────────────────────────────────────
    elements.append(Paragraph("Overall Scorecard", styles['SectionHeader']))
    elements.append(HRFlowable(width="100%", color=colors.HexColor("#e2e8f0"), thickness=0.5))
    elements.append(Spacer(1, 8))

    overall_score = evaluation_data.get("overall_score", 0)
    readiness = evaluation_data.get("readiness_level", "Needs more practice")

    score_text = f'<font size="28" color="{_get_score_color(overall_score/20, 5).hexval()}">{overall_score}%</font>'
    elements.append(Paragraph(f"Overall Score: {score_text}", styles['ScoreText']))
    elements.append(Paragraph(f"Readiness Level: <b>{readiness}</b>", styles['BodyText2']))
    elements.append(Spacer(1, 8))

    # Score breakdown table
    scores = evaluation_data.get("scores", [])
    if scores:
        score_data = [["Dimension", "Score", "Max", "Evidence"]]
        for s in scores:
            score_data.append([
                s.get("dimension", ""),
                str(s.get("score", 0)),
                str(s.get("max_score", 5)),
                s.get("evidence", "")[:80],
            ])

        score_table = Table(score_data, colWidths=[1.5*inch, 0.7*inch, 0.5*inch, 3.5*inch])
        score_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('ALIGN', (1, 0), (2, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
        ]))
        elements.append(score_table)
    elements.append(Spacer(1, 15))

    # ── Strengths ──────────────────────────────────────────────────
    strengths = evaluation_data.get("strengths", [])
    if strengths:
        elements.append(Paragraph("Strongest Areas", styles['SectionHeader']))
        elements.append(HRFlowable(width="100%", color=colors.HexColor("#e2e8f0"), thickness=0.5))
        elements.append(Spacer(1, 6))
        for i, s in enumerate(strengths, 1):
            desc = s.get("description", s.get("area", ""))
            evidence = s.get("evidence", "")
            text = f"{i}. <b>{desc}</b>"
            if evidence:
                text += f" — {evidence}"
            elements.append(Paragraph(text, styles['BodyText2']))
        elements.append(Spacer(1, 10))

    # ── Improvement Areas ──────────────────────────────────────────
    improvements = evaluation_data.get("improvements", [])
    if improvements:
        elements.append(Paragraph("Areas for Improvement", styles['SectionHeader']))
        elements.append(HRFlowable(width="100%", color=colors.HexColor("#e2e8f0"), thickness=0.5))
        elements.append(Spacer(1, 6))
        for i, imp in enumerate(improvements, 1):
            desc = imp.get("description", imp.get("area", ""))
            suggestion = imp.get("suggestion", "")
            text = f"{i}. <b>{desc}</b>"
            if suggestion:
                text += f" — <i>{suggestion}</i>"
            elements.append(Paragraph(text, styles['BodyText2']))
        elements.append(Spacer(1, 10))

    # ── Question-by-Question Review ────────────────────────────────
    question_evals = evaluation_data.get("question_evaluations", [])
    if question_evals:
        elements.append(PageBreak())
        elements.append(Paragraph("Question-by-Question Review", styles['SectionHeader']))
        elements.append(HRFlowable(width="100%", color=colors.HexColor("#e2e8f0"), thickness=0.5))
        elements.append(Spacer(1, 8))

        for qe in question_evals:
            elements.append(Paragraph(f"Question {qe.get('question_id', '')}: {qe.get('question_text', '')}", styles['SubHeader']))

            answer_text = qe.get("answer_text", "No answer recorded")
            if len(answer_text) > 500:
                answer_text = answer_text[:500] + "..."
            elements.append(Paragraph(f"<b>Answer:</b> {answer_text}", styles['BodyText2']))
            elements.append(Paragraph(f"<b>Duration:</b> {qe.get('answer_duration', 0):.0f}s | <b>Category:</b> {qe.get('category', 'general')}", styles['BodyText2']))

            # Score mini-table
            q_scores = qe.get("scores", [])
            if q_scores:
                q_data = [["Dimension", "Score"]]
                for qs in q_scores:
                    q_data.append([qs.get("dimension", ""), str(qs.get("score", 0))])
                q_table = Table(q_data, colWidths=[3*inch, 1*inch])
                q_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                ]))
                elements.append(q_table)

            strengths_text = qe.get("strengths", [])
            if strengths_text:
                elements.append(Paragraph("<b>What went well:</b> " + "; ".join(strengths_text), styles['BodyText2']))

            improvements_text = qe.get("improvements", [])
            if improvements_text:
                elements.append(Paragraph("<b>What could be improved:</b> " + "; ".join(improvements_text), styles['BodyText2']))

            suggested = qe.get("suggested_answer_structure", "")
            if suggested:
                elements.append(Paragraph(f"<b>Suggested structure:</b> {suggested}", styles['BodyText2']))

            elements.append(Spacer(1, 10))
            elements.append(HRFlowable(width="80%", color=colors.HexColor("#f1f5f9"), thickness=0.5))
            elements.append(Spacer(1, 6))

    # ── Communication Analysis ─────────────────────────────────────
    comm = evaluation_data.get("communication", {})
    if comm:
        elements.append(PageBreak())
        elements.append(Paragraph("Communication Analysis", styles['SectionHeader']))
        elements.append(HRFlowable(width="100%", color=colors.HexColor("#e2e8f0"), thickness=0.5))
        elements.append(Spacer(1, 6))

        comm_data = [
            ["Metric", "Value"],
            ["Average Answer Duration", f"{comm.get('avg_answer_duration', 0):.0f} seconds"],
            ["Speaking Pace", comm.get("speaking_pace", "Unknown")],
            ["Filler Word Count", str(comm.get("filler_word_count", 0))],
            ["Repeated Phrases", str(comm.get("repeated_phrases", 0))],
            ["Conciseness Rating", comm.get("conciseness_rating", "Unknown")],
        ]
        comm_table = Table(comm_data, colWidths=[2.5*inch, 3*inch])
        comm_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(comm_table)
        elements.append(Spacer(1, 8))

        elements.append(Paragraph(
            "<i>Note: Communication metrics are used for coaching purposes only. "
            "They do not interpret personality, intelligence, accent quality, or protected characteristics.</i>",
            styles['SmallText']
        ))
        elements.append(Spacer(1, 15))

    # ── Practice Plan ──────────────────────────────────────────────
    practice_plan = evaluation_data.get("practice_plan", [])
    if practice_plan:
        elements.append(Paragraph("Personalized Practice Plan", styles['SectionHeader']))
        elements.append(HRFlowable(width="100%", color=colors.HexColor("#e2e8f0"), thickness=0.5))
        elements.append(Spacer(1, 6))

        for rec in practice_plan:
            priority = rec.get("priority", 1)
            recommendation = rec.get("recommendation", "")
            rationale = rec.get("rationale", "")
            text = f"<b>Priority {priority}:</b> {recommendation}"
            if rationale:
                text += f" <i>({rationale})</i>"
            elements.append(Paragraph(text, styles['BodyText2']))
        elements.append(Spacer(1, 15))

    # ── Disclaimer ─────────────────────────────────────────────────
    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", color=colors.HexColor("#e2e8f0"), thickness=1))
    elements.append(Paragraph(
        "DISCLAIMER: This report is generated by an automated assessment and coaching tool. "
        "It is not a hiring decision and should not be used as the sole basis for employment decisions. "
        "The system does not make autonomous hiring decisions or infer protected characteristics. "
        "Communication metrics are used for coaching only and do not interpret personality, "
        "intelligence, accent quality, or any protected characteristics.",
        styles['Disclaimer']
    ))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        f"Generated by ResumeFlow Interview Studio on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        styles['Disclaimer']
    ))

    # Build PDF
    doc.build(elements, onFirstPage=_header_footer, onLaterPages=_header_footer)

    if output_path:
        return output_path
    else:
        return buffer.getvalue()


def generate_transcript_txt(transcript_data: list, candidate_name: str = "") -> str:
    """Generate a plain text transcript."""
    lines = []
    lines.append("=" * 60)
    lines.append("ResumeFlow Interview Transcript")
    lines.append(f"Candidate: {candidate_name}")
    lines.append(f"Date: {datetime.now().strftime('%B %d, %Y')}")
    lines.append("=" * 60)
    lines.append("")

    for segment in transcript_data:
        seg_type = segment.get("segment_type", "system")
        text = segment.get("text", "")
        timestamp = segment.get("timestamp", "")

        prefix = {
            "system": "[System]",
            "question": "[Interviewer]",
            "answer": "[Candidate]",
            "followup": "[Interviewer - Follow-up]",
        }.get(seg_type, "[Unknown]")

        lines.append(f"{prefix} {text}")
        lines.append("")

    lines.append("=" * 60)
    lines.append("End of Transcript")
    lines.append("=" * 60)
    return "\n".join(lines)


def generate_transcript_json(transcript_data: list, candidate_name: str = "") -> str:
    """Generate a JSON transcript."""
    data = {
        "candidate_name": candidate_name,
        "generated_at": datetime.now().isoformat(),
        "platform": "ResumeFlow Interview Studio",
        "segments": transcript_data,
    }
    return json.dumps(data, indent=2, default=str)
