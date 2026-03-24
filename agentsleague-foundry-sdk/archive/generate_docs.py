#!/usr/bin/env python3
"""
generate_docs.py – Generates Technical Documentation and Judge Playbook PDFs
=============================================================================
Run from the workspace root:
    python Notes/generate_docs.py

Outputs (to docs/ folder):
    docs/technical_documentation.pdf
    docs/judge_playbook.pdf
"""

from __future__ import annotations

import os
from pathlib import Path

# ─── Reportlab imports ────────────────────────────────────────────────────────
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.platypus.flowables import Flowable

# ─── Palette ──────────────────────────────────────────────────────────────────
PURPLE   = HexColor("#5C2D91")
PURPLE_L = HexColor("#EDE9FE")
BLUE     = HexColor("#0F6CBD")
BLUE_L   = HexColor("#DBEAFE")
GREEN    = HexColor("#107C10")
GREEN_L  = HexColor("#DCFCE7")
GOLD     = HexColor("#8A6D00")
GOLD_L   = HexColor("#FEF3C7")
RED      = HexColor("#DC2626")
RED_L    = HexColor("#FEE2E2")
GREY     = HexColor("#6B7280")
GREY_L   = HexColor("#F9FAFB")
DARK     = HexColor("#111827")


# ─── Styles ───────────────────────────────────────────────────────────────────
def make_styles():
    base = getSampleStyleSheet()

    h1 = ParagraphStyle("H1", parent=base["Heading1"],
                         fontSize=22, textColor=PURPLE, spaceAfter=8,
                         spaceBefore=18, leading=28, fontName="Helvetica-Bold")
    h2 = ParagraphStyle("H2", parent=base["Heading2"],
                         fontSize=16, textColor=BLUE, spaceAfter=6,
                         spaceBefore=14, leading=22, fontName="Helvetica-Bold")
    h3 = ParagraphStyle("H3", parent=base["Heading3"],
                         fontSize=12, textColor=PURPLE, spaceAfter=4,
                         spaceBefore=10, leading=16, fontName="Helvetica-Bold")
    body = ParagraphStyle("Body", parent=base["Normal"],
                          fontSize=10, textColor=DARK, spaceAfter=6,
                          leading=15, fontName="Helvetica")
    callout = ParagraphStyle("Callout", parent=base["Normal"],
                              fontSize=9.5, textColor=DARK, spaceAfter=4,
                              leading=14, fontName="Helvetica", leftIndent=12,
                              rightIndent=12)
    code = ParagraphStyle("Code", parent=base["Code"],
                           fontSize=8.5, textColor=HexColor("#1e3a5f"),
                           spaceAfter=4, leading=13,
                           backColor=HexColor("#f1f5f9"), fontName="Courier",
                           leftIndent=12, rightIndent=12)
    bullet = ParagraphStyle("Bullet", parent=base["Normal"],
                             fontSize=9.5, textColor=DARK, spaceAfter=3,
                             leading=14, fontName="Helvetica", leftIndent=18,
                             bulletIndent=6)
    badge_style = ParagraphStyle("Badge", parent=base["Normal"],
                                  fontSize=9, textColor=white, spaceAfter=0,
                                  leading=14, fontName="Helvetica-Bold")
    caption = ParagraphStyle("Caption", parent=base["Normal"],
                              fontSize=8, textColor=GREY, spaceAfter=4,
                              leading=12, fontName="Helvetica-Oblique",
                              alignment=TA_CENTER)
    q_style = ParagraphStyle("Q", parent=base["Normal"],
                              fontSize=10.5, textColor=PURPLE, spaceAfter=4,
                              leading=16, fontName="Helvetica-Bold")
    a_style = ParagraphStyle("A", parent=base["Normal"],
                              fontSize=10, textColor=DARK, spaceAfter=8,
                              leading=15, fontName="Helvetica", leftIndent=16)

    return dict(h1=h1, h2=h2, h3=h3, body=body, callout=callout, code=code,
                bullet=bullet, caption=caption, badge_style=badge_style,
                q=q_style, a=a_style)


# ─── Helper builders ──────────────────────────────────────────────────────────

def hr(color=PURPLE, width=1):
    return HRFlowable(width="100%", thickness=width, color=color,
                      spaceAfter=6, spaceBefore=4)

def sp(h=6):
    return Spacer(1, h * mm)

def coloured_table(data, col_widths, bg_header=PURPLE, bg_row=GREY_L):
    """Create a styled table with coloured header row."""
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0),  bg_header),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  white),
        ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0),  9),
        ("BACKGROUND",  (0, 1), (-1, -1), bg_row),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, bg_row]),
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 1), (-1, -1), 9),
        ("GRID",        (0, 0), (-1, -1), 0.5, HexColor("#D1D5DB")),
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0,0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ])
    t.setStyle(style)
    return t


def section_header(title: str, styles: dict, color=PURPLE, bg=PURPLE_L):
    """A visually distinct section header block."""
    data = [[Paragraph(f"<b>{title}</b>",
                        ParagraphStyle("SH", fontSize=13, textColor=white,
                                       leading=18, fontName="Helvetica-Bold"))]]
    t = Table(data, colWidths=["100%"])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
    ]))
    return t


# ══════════════════════════════════════════════════════════════════════════════
# DOCUMENT 1 – TECHNICAL DOCUMENTATION
# ══════════════════════════════════════════════════════════════════════════════

def build_technical_doc(out_path: Path):
    styles = make_styles()
    s = styles

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=22*mm, bottomMargin=22*mm,
        title="CertPrep AI — Technical Documentation",
        author="Agents League 2026",
    )

    story = []

    # ── Cover page ────────────────────────────────────────────────────────────
    story.append(sp(20))
    cover_data = [[
        Paragraph(
            "<b>CertPrep AI</b>",
            ParagraphStyle("CoverTitle", fontSize=36, textColor=white,
                           fontName="Helvetica-Bold", alignment=TA_CENTER, leading=44)
        )
    ], [
        Paragraph(
            "Multi-Agent Certification Preparation System",
            ParagraphStyle("CoverSub", fontSize=18, textColor=PURPLE_L,
                           fontName="Helvetica", alignment=TA_CENTER, leading=24)
        )
    ], [
        Paragraph(
            "Technical Documentation  ·  Microsoft Agents League 2026  ·  Battle #2",
            ParagraphStyle("CoverMeta", fontSize=10, textColor=HexColor("#C4B5FD"),
                           fontName="Helvetica", alignment=TA_CENTER, leading=16)
        )
    ]]
    cover_t = Table(cover_data, colWidths=["100%"])
    cover_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), PURPLE),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING",   (0, 0), (-1, -1), 20),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 20),
    ]))
    story.append(cover_t)
    story.append(sp(6))

    meta_row = [
        ["📅 Date", "February 2026"],
        ["🏆 Track", "Battle #2 – Reasoning Agents with Microsoft Foundry"],
        ["📐 Architecture", "Multi-agent pipeline (7 agents + 17 guardrails)"],
        ["🛠️ Stack", "Python 3.11 · Streamlit · Plotly · Pydantic · ReportLab"],
    ]
    meta_t = Table([[Paragraph(k, s["body"]), Paragraph(v, s["body"])]
                    for k, v in meta_row],
                   colWidths=[50*mm, 120*mm])
    meta_t.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), GREY_L),
        ("GRID",        (0, 0), (-1, -1), 0.5, HexColor("#D1D5DB")),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0,0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("FONTNAME",    (0, 0), (0, -1),  "Helvetica-Bold"),
    ]))
    story.append(meta_t)
    story.append(PageBreak())

    # ── 1. Executive Summary ──────────────────────────────────────────────────
    story += [
        section_header("1. Executive Summary", s),
        sp(2),
        Paragraph(
            "CertPrep AI is a <b>multi-agent, pipeline-based</b> certification preparation system "
            "designed to help learners pass the <b>Microsoft AI-102 (Azure AI Engineer Associate)</b> "
            "exam on their first attempt. The system guides a student from initial intake through "
            "structured domain profiling, personalised study planning, daily learning content curation, "
            "mid-journey readiness assessment, automated knowledge quizzes, and a final exam booking decision.",
            s["body"]
        ),
        Paragraph(
            "The application is implemented as a <b>Streamlit web app</b> with 7 interactive tabs, "
            "backed by 7 specialised Python agent classes and a 17-rule guardrails pipeline. "
            "All agent transitions are validated, all outputs are visible to the user, and the system "
            "supports both a <b>mock (offline) mode</b> and a <b>live Azure OpenAI mode</b>.",
            s["body"]
        ),
        hr(),
    ]

    # ── 2. System Architecture ────────────────────────────────────────────────
    story += [
        section_header("2. System Architecture — Agent Pipeline", s),
        sp(2),
        Paragraph(
            "The pipeline is organised into four sequential blocks, each encapsulating one or more agents. "
            "A dedicated guardrails layer sits between every block, providing input validation, output bounds "
            "checking, and content safety inspection.",
            s["body"]
        ),
        sp(2),
    ]

    arch_data = [
        ["Block", "Agent(s)", "Role", "Output"],
        ["Block 0\nInput",
         "Streamlit UI form",
         "Collect student intake form data",
         "RawStudentInput dataclass"],
        ["Block 1\nIntake &\nProfiling",
         "LearnerIntakeAgent\nLearnerProfilingAgent",
         "Interview student → infer experience level, domain knowledge scores, risk domains",
         "LearnerProfile (Pydantic model)"],
        ["Block 1.1\nLearning Path",
         "LearningPathCuratorAgent\nStudyPlanAgent",
         "Map domains to MS Learn modules → Build week-by-week Gantt study schedule",
         "LearningPath + StudyPlan"],
        ["Block 1.2\nProgress\nTracking",
         "ProgressAgent\nEngagement Agent\n(email)",
         "Self-check-in → readiness scoring → smart nudges → weekly email report",
         "ReadinessAssessment + HTML email"],
        ["Block 2\nAssessment",
         "AssessmentAgent",
         "Generate domain-weighted quiz (up to 30 Qs) → score → provide feedback",
         "Assessment + AssessmentResult"],
        ["Block 3\nCertification",
         "CertificationRecommendationAgent",
         "GO / NO-GO exam decision → exam logistics → next certification path",
         "CertRecommendation"],
    ]
    arch_cols = [22*mm, 50*mm, 65*mm, 40*mm]
    story.append(coloured_table(
        [[Paragraph(str(c), ParagraphStyle("TH", fontSize=8.5, textColor=white, fontName="Helvetica-Bold"))
          for c in arch_data[0]]] +
        [[Paragraph(str(c), ParagraphStyle("TC", fontSize=8.5, textColor=DARK, fontName="Helvetica", leading=13))
          for c in row]
         for row in arch_data[1:]],
        arch_cols
    ))
    story.append(hr())

    # ── 3. Agent-by-Agent Breakdown ───────────────────────────────────────────
    agents = [
        {
            "id": "Agent 1",
            "name": "LearnerIntakeAgent",
            "file": "src/cert_prep/intake_agent.py",
            "block": "Block 1",
            "trigger": "User submits intake form",
            "input": "Student form values (name, background, hours, weeks, certs, concerns)",
            "output": "RawStudentInput dataclass",
            "reasoning": (
                "Collects structured answers to 7 standardised questions. "
                "In CLI mode it uses Rich prompts; in Streamlit mode the form replaces the CLI. "
                "No AI inference at this stage — pure data collection."
            ),
            "guardrails": "G-01 (empty name/target), G-02 (hours range), G-03 (weeks range), G-04 (cert code check), G-05 (PII notice)",
        },
        {
            "id": "Agent 2",
            "name": "LearnerProfilingAgent",
            "file": "src/cert_prep/intake_agent.py  /  mock_profiler.py",
            "block": "Block 1",
            "trigger": "After LearnerIntakeAgent returns RawStudentInput",
            "input": "RawStudentInput",
            "output": "LearnerProfile (6 DomainProfile objects + metadata)",
            "reasoning": (
                "In Mock mode: rule-based inference maps keywords in background_text to domain knowledge levels "
                "(UNKNOWN / WEAK / MODERATE / STRONG) and sets confidence scores. "
                "In Live mode: sends a JSON-schema-anchored system prompt to Azure OpenAI gpt-4o, "
                "parses the response directly into the Pydantic LearnerProfile model."
            ),
            "guardrails": "G-06 (6 domains present), G-07 (confidence ∈ [0,1]), G-08 (valid domain IDs)",
        },
        {
            "id": "Agent 3",
            "name": "LearningPathCuratorAgent",
            "file": "src/cert_prep/learning_path_curator.py",
            "block": "Block 1.1",
            "trigger": "After profile generation (autorun on submit)",
            "input": "LearnerProfile",
            "output": "LearningPath (~20–30 MS Learn modules, domain-grouped)",
            "reasoning": (
                "Iterates over sorted domain profiles (risk → normal → skip). "
                "For each domain pulls modules from a curated offline catalogue of 30+ MS Learn entries. "
                "Applies priority boosting for risk domains (supplemental → core). "
                "Skips beginner-level modules for learners with moderate/strong knowledge. "
                "Respects a 2× budget cap to prevent overwhelming the learner."
            ),
            "guardrails": "G-17 (URL trusted domain check — all links must be learn.microsoft.com etc.)",
        },
        {
            "id": "Agent 4",
            "name": "StudyPlanAgent",
            "file": "src/cert_prep/study_plan_agent.py",
            "block": "Block 1.1",
            "trigger": "After profile generation (autorun on submit)",
            "input": "LearnerProfile + existing_certs list",
            "output": "StudyPlan (Gantt tasks, prerequisite info, hours breakdown)",
            "reasoning": (
                "Checks _CERT_PREREQ_MAP to identify missing, held, and helpful certifications. "
                "Uses the Largest Remainder Method at day granularity (7 days/week) to allocate "
                "study hours across active domains proportional to exam weight × knowledge deficit. "
                "Front-loads risk domains; schedules skip-eligible domains minimally at the end. "
                "Last week is reserved as a review + practice exam block."
            ),
            "guardrails": "G-09 (start_week ≤ end_week), G-10 (allocated hours ≤ budget + 10%)",
        },
        {
            "id": "Agent 5",
            "name": "ProgressAgent",
            "file": "src/cert_prep/progress_agent.py",
            "block": "Block 1.2",
            "trigger": "User submits My Progress check-in form",
            "input": "LearnerProfile + ProgressSnapshot (hours, weeks, domain self-ratings, practice exam)",
            "output": "ReadinessAssessment (score, verdict, nudges, GO/NO-GO, domain status)",
            "reasoning": (
                "Composite readiness formula: readiness = 0.55 × weighted_domain_score "
                "+ 0.25 × hours_progress_pct + 0.20 × practice_factor. "
                "Verdict thresholds: ≥75% = EXAM_READY, ≥60% = NEARLY_READY, ≥45% = NEEDS_WORK, <45% = NOT_READY. "
                "GO/NO-GO: GO if ≥75% + 0 critical domains; CONDITIONAL GO if ≥65% + ≤1 critical. "
                "Generates up to 6 smart nudges categorised (DANGER/WARNING/INFO/SUCCESS)."
            ),
            "guardrails": "G-11 (hours ≥ 0), G-12 (ratings ∈ [1,5]), G-13 (practice score ∈ [0,100])",
        },
        {
            "id": "Agent 6",
            "name": "AssessmentAgent",
            "file": "src/cert_prep/assessment_agent.py",
            "block": "Block 2",
            "trigger": "User clicks 'Generate New Quiz' (human-in-the-loop gate)",
            "input": "LearnerProfile + requested question count",
            "output": "Assessment (questions) → AssessmentResult (score, domain breakdown, feedback)",
            "reasoning": (
                "Samples questions from a 30-question bank (5 per domain, 3 difficulty levels) "
                "proportional to exam domain weights. Excludes skipped domains. "
                "Fixes rounding to guarantee exactly N questions. "
                "Scoring: correct answers / total × 100. Per-domain scores enable targeted feedback. "
                "PASS threshold: 60%. Result feeds CertificationRecommendationAgent."
            ),
            "guardrails": "G-14 (≥5 questions), G-15 (no duplicate IDs)",
        },
        {
            "id": "Agent 7",
            "name": "CertificationRecommendationAgent",
            "file": "src/cert_prep/cert_recommendation_agent.py",
            "block": "Block 3",
            "trigger": "After AssessmentResult or ReadinessAssessment is available",
            "input": "LearnerProfile + AssessmentResult (or ReadinessAssessment)",
            "output": "CertRecommendation (GO/NO-GO, ExamInfo, next-cert suggestions, booking checklist)",
            "reasoning": (
                "GO threshold: assessment score ≥ 70% (HIGH confidence ≥ 85%). "
                "If GO: returns ExamInfo (passing score, duration, cost, Pearson VUE link, free practice URL) "
                "+ 7-item booking checklist + 2–3 next-cert suggestions. "
                "If NO-GO: generates a targeted remediation plan listing weak domains "
                "and recommends a 2–3 week focused study cycle before retaking. "
                "If looping from a failed assessment, the pipeline returns to Block 1.1 (LearningPathCuratorAgent)."
            ),
            "guardrails": "G-17 (all recommendation URLs verified against trusted domain list)",
        },
    ]

    story.append(section_header("3. Agent-by-Agent Breakdown", s))
    story.append(sp(2))

    for ag in agents:
        agent_header = Table(
            [[Paragraph(f"<b>{ag['id']}: {ag['name']}</b>",
                        ParagraphStyle("AH", fontSize=11, textColor=white, fontName="Helvetica-Bold")),
              Paragraph(f"<b>Block:</b> {ag['block']} · <b>File:</b> {ag['file']}",
                        ParagraphStyle("AF", fontSize=8, textColor=PURPLE_L, fontName="Helvetica"))]],
            colWidths=[90*mm, 87*mm],
        )
        agent_header.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, -1), BLUE),
            ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",  (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING",(0,0), (-1, -1), 7),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING",(0, 0), (-1, -1), 8),
        ]))

        fields = [
            ("Trigger",    ag["trigger"]),
            ("Input",      ag["input"]),
            ("Output",     ag["output"]),
            ("Reasoning",  ag["reasoning"]),
            ("Guardrails", ag["guardrails"]),
        ]
        detail_rows = [
            [Paragraph(f"<b>{k}</b>",
                       ParagraphStyle("FK", fontSize=9, textColor=PURPLE, fontName="Helvetica-Bold")),
             Paragraph(v,
                       ParagraphStyle("FV", fontSize=9, textColor=DARK, fontName="Helvetica", leading=14))]
            for k, v in fields
        ]
        detail_t = Table(detail_rows, colWidths=[28*mm, 149*mm])
        detail_t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), GREY_L),
            ("ROWBACKGROUNDS",(0, 0), (-1, -1), [white, GREY_L]),
            ("GRID",          (0, 0), (-1, -1), 0.5, HexColor("#E5E7EB")),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ]))

        story.append(KeepTogether([agent_header, detail_t, sp(3)]))

    story.append(hr())

    # ── 4. Guardrails Layer ────────────────────────────────────────────────────
    story.append(section_header("4. Guardrails Layer — Responsible AI", s))
    story.append(sp(2))
    story.append(Paragraph(
        "Every agent transition passes through the <b>GuardrailsPipeline</b>, which checks "
        "17 rules across 5 categories. Violations are classified as BLOCK (hard-stop), "
        "WARN (advisory), or INFO (transparent logging). No hallucinated or internally inconsistent "
        "data is passed between agents.",
        s["body"]
    ))
    story.append(sp(2))

    g_data = [
        ["Code", "Level", "Category", "Rule Description"],
        ["G-01", "BLOCK/WARN", "Input",   "Non-empty: student name, exam target, background description"],
        ["G-02", "WARN",       "Input",   "Hours per week in sensible range [1–80]"],
        ["G-03", "BLOCK/WARN", "Input",   "Weeks available ≥ 1, ≤ 52 (warn if >52)"],
        ["G-04", "WARN",       "Input",   "Exam code recognised in certification catalogue"],
        ["G-05", "INFO",       "Input",   "PII notice: student name stored in session only, not sent externally"],
        ["G-06", "WARN",       "Profile", "All 6 AI-102 domains present in profiling output"],
        ["G-07", "BLOCK",      "Profile", "Confidence scores within [0.0, 1.0] range"],
        ["G-08", "WARN",       "Profile", "Risk domain IDs must be valid AI-102 domain identifiers"],
        ["G-09", "BLOCK",      "Plan",    "No study task may have start_week > end_week"],
        ["G-10", "WARN",       "Plan",    "Total allocated hours must not exceed budget by more than 10%"],
        ["G-11", "BLOCK",      "Progress","Hours spent must be ≥ 0"],
        ["G-12", "BLOCK",      "Progress","Domain self-ratings must be in [1, 5] range"],
        ["G-13", "BLOCK",      "Progress","Practice exam score must be in [0, 100] when provided"],
        ["G-14", "WARN",       "Quiz",    "Assessment must contain at least 5 questions for reliability"],
        ["G-15", "BLOCK",      "Quiz",    "No duplicate question IDs in a generated assessment"],
        ["G-16", "BLOCK",      "Content", "Heuristic harmful/profanity content check on all free-text outputs"],
        ["G-17", "WARN",       "Content", "All URLs must originate from trusted domains (learn.microsoft.com etc.)"],
    ]

    level_colors = {"BLOCK": RED_L, "WARN": GOLD_L, "INFO": BLUE_L, "BLOCK/WARN": RED_L}

    def g_row(row):
        lvl = row[1]
        bg  = level_colors.get(lvl, GREY_L)
        return [
            Paragraph(row[0], ParagraphStyle("GC", fontSize=8.5, fontName="Helvetica-Bold", textColor=DARK)),
            Paragraph(row[1], ParagraphStyle("GL", fontSize=8.5, fontName="Helvetica-Bold",
                                              textColor=RED if "BLOCK" in lvl else GOLD if lvl=="WARN" else BLUE)),
            Paragraph(row[2], ParagraphStyle("GCat", fontSize=8.5, fontName="Helvetica", textColor=DARK)),
            Paragraph(row[3], ParagraphStyle("GD", fontSize=8.5, fontName="Helvetica", textColor=DARK, leading=13)),
        ]

    g_table_rows = (
        [[Paragraph(h, ParagraphStyle("TH", fontSize=9, textColor=white, fontName="Helvetica-Bold"))
          for h in g_data[0]]] +
        [g_row(r) for r in g_data[1:]]
    )
    g_t = Table(g_table_rows, colWidths=[14*mm, 22*mm, 20*mm, 121*mm])
    g_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  PURPLE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [white, GREY_L]),
        ("GRID",          (0, 0), (-1, -1), 0.4, HexColor("#D1D5DB")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(g_t)
    story.append(hr())

    # ── 5. Data Models ─────────────────────────────────────────────────────────
    story.append(section_header("5. Key Data Models", s))
    story.append(sp(2))

    models_data = [
        ["Model / Dataclass", "Module", "Purpose", "Key Fields"],
        ["RawStudentInput", "models.py", "Raw form data before profiling",
         "student_name, exam_target, background_text, hours_per_week, weeks_available"],
        ["LearnerProfile (Pydantic)", "models.py", "Structured learner profile",
         "student_name, experience_level, learning_style, domain_profiles, risk_domains, analogy_map"],
        ["DomainProfile (Pydantic)", "models.py", "Per-domain knowledge assessment",
         "domain_id, knowledge_level, confidence_score, skip_recommended, notes"],
        ["LearningPath", "learning_path_curator.py", "MS Learn module mapping",
         "curated_paths (dict), all_modules, total_hours_est, skipped_domains"],
        ["LearningModule", "learning_path_curator.py", "Single MS Learn module",
         "title, url, domain_id, duration_min, difficulty, priority"],
        ["StudyPlan", "study_plan_agent.py", "Gantt study schedule",
         "tasks, prereq_info, review_start_week, total_weeks"],
        ["StudyTask", "study_plan_agent.py", "One domain's study block",
         "domain_id, start_week, end_week, total_hours, priority, confidence_pct"],
        ["ProgressSnapshot", "progress_agent.py", "Mid-journey self-report",
         "total_hours_spent, weeks_elapsed, domain_progress, done_practice_exam, practice_score_pct"],
        ["ReadinessAssessment", "progress_agent.py", "Readiness scoring output",
         "readiness_pct, verdict, nudges, exam_go_nogo, domain_status, recommended_focus"],
        ["Assessment", "assessment_agent.py", "Generated quiz instance",
         "questions (list[QuizQuestion]), total_marks, pass_mark_pct"],
        ["AssessmentResult", "assessment_agent.py", "Scored quiz output",
         "score_pct, passed, domain_scores, feedback, verdict, recommendation"],
        ["CertRecommendation", "cert_recommendation_agent.py", "Exam booking decision",
         "go_for_exam, exam_info, next_cert_suggestions, remediation_plan, booking_checklist"],
        ["GuardrailResult", "guardrails.py", "Guardrail check outcome",
         "passed, violations (list[GuardrailViolation]), blocked, warnings, infos"],
    ]

    story.append(coloured_table(
        [[Paragraph(str(c), ParagraphStyle("TH", fontSize=8, textColor=white, fontName="Helvetica-Bold"))
          for c in models_data[0]]] +
        [[Paragraph(str(c), ParagraphStyle("TC", fontSize=8, textColor=DARK, fontName="Helvetica", leading=12))
          for c in row] for row in models_data[1:]],
        [42*mm, 44*mm, 44*mm, 47*mm]
    ))
    story.append(hr())

    # ── 6. Reasoning Patterns ──────────────────────────────────────────────────
    story.append(section_header("6. Reasoning Patterns Applied", s))
    story.append(sp(2))

    patterns = [
        ("Planner–Executor",
         "StudyPlanAgent (planner) decomposes the total study budget into per-domain "
         "week-blocks using exam weight + knowledge deficit, then 'executes' by emitting "
         "concrete StudyTask records with explicit start/end weeks."),
        ("Critic / Verifier",
         "The GuardrailsPipeline acts as an automated critic after every agent. "
         "It verifies that outputs meet structural constraints (bounds, completeness) "
         "before the next agent receives them, preventing cascading errors."),
        ("Self-Reflection & Iteration",
         "The Progress→Assessment→Recommendation loop implements iterative self-reflection: "
         "if the learner fails the quiz (<60%), the pipeline loops back to "
         "LearningPathCuratorAgent for a new curated study cycle rather than terminating."),
        ("Role-Based Specialisation",
         "Each agent has a single, well-defined responsibility: "
         "Intake (data collection) → Profiling (inference) → Curation (content mapping) "
         "→ Planning (scheduling) → Progress (tracking) → Assessment (evaluation) "
         "→ Recommendation (decision). No agent performs more than one role."),
        ("Human-in-the-Loop",
         "The assessment is not triggered automatically — the student must explicitly "
         "confirm they are ready by clicking 'Generate New Quiz'. "
         "Similarly the progress check-in is voluntary, preserving learner agency."),
    ]

    for title, desc in patterns:
        story.append(Paragraph(f"<b>{title}</b>", s["h3"]))
        story.append(Paragraph(desc, s["body"]))
        story.append(sp(1))

    story.append(hr())

    # ── 7. UI Structure ────────────────────────────────────────────────────────
    story.append(section_header("7. Streamlit UI — 7-Tab Structure", s))
    story.append(sp(2))

    tabs = [
        ("Tab 1: 🗺️ Domain Map",
         "Radar chart + bar chart of domain confidence scores. "
         "Auto-generated Radar Insights and Bar Chart Insights callouts highlight "
         "strongest/weakest domains, below-threshold areas, and skip candidates."),
        ("Tab 2: 📅 Study Setup",
         "Prerequisites section (missing/held/helpful certs), "
         "Prerequisite notes, interactive Plotly Gantt chart, "
         "hours breakdown dataframe, and condensed profile summary cards."),
        ("Tab 3: 📚 Learning Path",
         "Domain-by-domain expandable lists of curated MS Learn modules. "
         "Each module shows title (linked), type, difficulty, duration, and priority. "
         "Summary KPIs: modules curated, estimated hours, budget utilisation."),
        ("Tab 4: 💡 Recommendations",
         "Personalisation recommendation from profiling, readiness outlook progress bar, "
         "CertificationRecommendationAgent output (GO/NO-GO card, exam logistics, "
         "booking checklist, next-cert suggestions), and full agent pipeline status tracker."),
        ("Tab 5: 📈 My Progress",
         "Self-assessment form (hours, weeks, domain sliders, practice exam). "
         "On submit: Plotly gauge + GO/NO-GO card + colour-coded nudge alerts + "
         "domain status table (actual vs expected) + focus recommendation + email section."),
        ("Tab 6: 🧪 Knowledge Check",
         "On-demand quiz (5–30 Qs). Question bank covers all 6 domains with "
         "3 difficulty levels. Results include score, per-domain breakdown, "
         "per-question feedback with explanations, and a 'Retake Quiz' option."),
        ("Tab 7: 📄 Raw JSON",
         "Raw RawStudentInput and LearnerProfile JSON for debugging/inspection. "
         "Download button exports the full profile as a JSON file."),
    ]

    for tab_title, desc in tabs:
        story.append(Paragraph(f"<b>{tab_title}</b>", s["h3"]))
        story.append(Paragraph(desc, s["body"]))

    story.append(hr())

    # ── 8. File Structure ──────────────────────────────────────────────────────
    story.append(section_header("8. Repository File Structure", s))
    story.append(sp(2))

    files = [
        ["File / Directory", "Purpose"],
        ["streamlit_app.py", "Main Streamlit UI (1600+ lines). Entry point for `streamlit run`."],
        ["demo_intake.py", "CLI demonstration of the LearnerIntakeAgent + LearnerProfilingAgent."],
        ["requirements.txt", "Python dependencies (openai, streamlit, plotly, pydantic, reportlab, …)"],
        ["src/cert_prep/models.py", "Core data models: enums, AI102_DOMAINS, RawStudentInput, LearnerProfile, DomainProfile."],
        ["src/cert_prep/intake_agent.py", "LearnerIntakeAgent (CLI) + LearnerProfilingAgent (Azure OpenAI)."],
        ["src/cert_prep/mock_profiler.py", "Rule-based mock profiler — no Azure credentials needed."],
        ["src/cert_prep/study_plan_agent.py", "StudyPlanAgent: prerequisite lookup + Largest Remainder allocation."],
        ["src/cert_prep/learning_path_curator.py", "LearningPathCuratorAgent: 30+ MS Learn module catalogue."],
        ["src/cert_prep/progress_agent.py", "ProgressAgent: composite readiness scoring + SMTP email dispatch."],
        ["src/cert_prep/assessment_agent.py", "AssessmentAgent: 30-question bank + quiz scoring + per-domain feedback."],
        ["src/cert_prep/cert_recommendation_agent.py", "CertificationRecommendationAgent: GO/NO-GO + next-cert path."],
        ["src/cert_prep/guardrails.py", "GuardrailsPipeline: 17 validation rules across 5 categories."],
        ["src/cert_prep/agent_trace.py", "AgentTrace: step-by-step reasoning trace for debugging/transparency."],
        ["src/cert_prep/config.py", "AzureOpenAIConfig: reads from .env file."],
        ["Notes/generate_docs.py", "This script — generates technical_documentation.pdf and judge_playbook.pdf."],
        ["docs/technical_documentation.pdf", "← generated by this script"],
        ["docs/judge_playbook.pdf", "← generated by this script"],
    ]

    story.append(coloured_table(
        [[Paragraph(str(c), ParagraphStyle("TH", fontSize=9, textColor=white, fontName="Helvetica-Bold"))
          for c in files[0]]] +
        [[Paragraph(str(c), ParagraphStyle("TC", fontSize=8.5, textColor=DARK, fontName="Courier" if i == 0 else "Helvetica", leading=13))
          for i, c in enumerate(row)] for row in files[1:]],
        [70*mm, 107*mm]
    ))

    story.append(hr())

    # ── 9. Evaluation Criteria Coverage ───────────────────────────────────────
    story.append(section_header("9. Competition Evaluation Criteria Coverage", s))
    story.append(sp(2))

    criteria = [
        ["Criterion", "Weight", "How CertPrep AI addresses it"],
        ["Accuracy & Relevance", "25%",
         "Directly implements the challenge scenario (AI-102 prep). "
         "Profiling accurately maps student backgrounds to domain knowledge. "
         "Rule-based inference validated against 3 diverse personas. All agent outputs structured and bounded."],
        ["Reasoning & Multi-step Thinking", "25%",
         "7-agent pipeline with explicit block sequencing. "
         "Planner–Executor, Critic/Verifier, and Self-Reflection patterns applied. "
         "Domain allocation uses mathematical reasoning (Largest Remainder Method). "
         "Readiness formula is explainable and multi-factor."],
        ["Creativity & Originality", "15%",
         "Returning-user journey with mid-journey progress tracking is novel vs the reference architecture. "
         "Animated colour-coded KPI cards, Plotly Gantt, radar+bar dual-chart domain assessment. "
         "SMTP weekly summary email with HTML KPI cards. "
         "GO/NO-GO exam decision with booking checklist."],
        ["User Experience & Presentation", "15%",
         "Fully interactive Streamlit web app with 7 tabs. "
         "Colour-coded guardrail notices, smart nudge alerts, visual readiness gauge. "
         "All outputs immediately visible — no hidden intermediate states. "
         "Export to JSON, HTML email, PDF documentation."],
        ["Reliability & Safety", "20%",
         "17-rule GuardrailsPipeline blocks bad data at every transition. "
         "URL trust checking (G-17) prevents hallucinated or poisoned links. "
         "PII notice in G-05. Mock mode requires no live AI credentials. "
         "Graceful fallback: Live Azure OpenAI failure falls back to mock profiler."],
    ]

    story.append(coloured_table(
        [[Paragraph(str(c), ParagraphStyle("TH", fontSize=9, textColor=white, fontName="Helvetica-Bold"))
          for c in criteria[0]]] +
        [[Paragraph(str(c), ParagraphStyle("TC", fontSize=8.5, textColor=DARK, fontName="Helvetica", leading=13))
          for c in row] for row in criteria[1:]],
        [45*mm, 16*mm, 116*mm]
    ))

    doc.build(story)
    print(f"✅ Technical documentation saved → {out_path}")


# ══════════════════════════════════════════════════════════════════════════════
# DOCUMENT 2 – JUDGE PLAYBOOK
# ══════════════════════════════════════════════════════════════════════════════

def build_judge_playbook(out_path: Path):
    styles = make_styles()
    s = styles

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=22*mm, bottomMargin=22*mm,
        title="CertPrep AI — Judge Playbook",
        author="Agents League 2026",
    )

    story = []

    # ── Cover ─────────────────────────────────────────────────────────────────
    cover_data = [[
        Paragraph("<b>CertPrep AI — Judge Playbook</b>",
                  ParagraphStyle("C1", fontSize=28, textColor=white, fontName="Helvetica-Bold",
                                  alignment=TA_CENTER, leading=36))
    ], [
        Paragraph("Anticipated questions and prepared answers for the Agents League judging panel",
                  ParagraphStyle("C2", fontSize=13, textColor=PURPLE_L, fontName="Helvetica",
                                  alignment=TA_CENTER, leading=18))
    ], [
        Paragraph("Battle #2 — Reasoning Agents  ·  Microsoft Agents League 2026",
                  ParagraphStyle("C3", fontSize=9, textColor=HexColor("#C4B5FD"), fontName="Helvetica",
                                  alignment=TA_CENTER, leading=14))
    ]]
    ct = Table(cover_data, colWidths=["100%"])
    ct.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PURPLE),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING", (0, 0), (-1, -1), 20),
        ("RIGHTPADDING",(0, 0), (-1, -1), 20),
    ]))
    story += [ct, sp(4)]

    note_t = Table([[
        Paragraph(
            "<b>How to use this playbook:</b> Each entry gives a likely judge question "
            "(in purple) followed by a model answer. The answers reference specific implementation "
            "details — code files, formula values, or screen sections — so they are verifiable. "
            "Feel free to expand with your own examples during the live demo.",
            ParagraphStyle("Note", fontSize=9.5, textColor=DARK, fontName="Helvetica", leading=15)
        )
    ]], colWidths=["100%"])
    note_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GOLD_L),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING",(0,0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("BOX",        (0, 0), (-1, -1), 1, GOLD),
    ]))
    story += [note_t, sp(4), PageBreak()]

    # ── QA pairs ─────────────────────────────────────────────────────────────
    qa_sections = [
        {
            "section": "Overall System & Architecture",
            "qa": [
                (
                    "Can you walk us through your overall architecture and explain how the agents collaborate?",
                    "We build a linear pipeline of 7 agents grouped into 4 blocks.\n\n"
                    "Block 1 starts with the LearnerIntakeAgent collecting a 9-field form "
                    "(student name, background, target exam, hours, weeks, etc.). Next, "
                    "LearnerProfilingAgent infers 6 per-domain confidence scores and classifies "
                    "the student into one of 4 experience levels. This produces a LearnerProfile "
                    "Pydantic model that all downstream agents consume.\n\n"
                    "Block 1.1 runs two agents in parallel to the same profile: "
                    "the LearningPathCuratorAgent maps each AI-102 domain to curated MS Learn modules "
                    "(30+ in our catalogue, priority-boosted for risk domains), and StudyPlanAgent "
                    "builds a week-by-week Gantt schedule using the Largest Remainder Method to "
                    "fairly allocate study hours.\n\n"
                    "Block 1.2 is the returning-user path: ProgressAgent takes a mid-journey self-report "
                    "and computes a composite readiness score (55% domain + 25% hours + 20% practice). "
                    "It also triggers the Engagement Agent to send a weekly HTML email summary.\n\n"
                    "Block 2 is human-gated: the learner explicitly clicks 'Generate Quiz', "
                    "AssessmentAgent samples from our 30-question bank weighted by exam domain percentages, "
                    "and returns a scored AssessmentResult.\n\n"
                    "Block 3 is CertificationRecommendationAgent: if the quiz score is ≥70% it "
                    "recommends booking the exam and suggests a next-certification path. "
                    "Below 70% it generates a targeted remediation plan and loops the learner back "
                    "to the LearningPathCuratorAgent for another study cycle.\n\n"
                    "A 17-rule GuardrailsPipeline sits between every block to catch bad inputs, "
                    "out-of-bounds values, untrusted URLs, and duplicate IDs before they propagate."
                ),
                (
                    "The reference architecture shows 3 sub-agents — learning path curator, study plan generator, and engagement agent. Did you implement all of them?",
                    "Yes, and we extended them.\n\n"
                    "The learning path curator is our LearningPathCuratorAgent — it maps each AI-102 domain to "
                    "MS Learn modules, respects the learner's knowledge level, and applies priority boosting for "
                    "risk domains. It's backed by a 30+ entry offline catalogue with real learn.microsoft.com URLs.\n\n"
                    "The study plan generator is StudyPlanAgent — it produces an actual Gantt chart (not just a list) "
                    "with week-level scheduling, prerequisite alerts, and a review week at the end.\n\n"
                    "The engagement agent is embedded in ProgressAgent — it generates a self-contained HTML "
                    "email report with KPI cards, nudge alerts, and a domain status table, dispatched "
                    "via SMTP (or previewed in-app when no SMTP credentials are configured).\n\n"
                    "Beyond the reference, we added: LearnerIntakeAgent, LearnerProfilingAgent (live AI), "
                    "ProgressAgent (mid-journey tracking), AssessmentAgent (quiz), "
                    "CertificationRecommendationAgent (exam booking), and the full GuardrailsPipeline."
                ),
            ],
        },
        {
            "section": "Reasoning & Multi-step Thinking",
            "qa": [
                (
                    "How do your agents reason? Where does the actual 'reasoning' happen rather than just data transformation?",
                    "Reasoning happens at four distinct points:\n\n"
                    "1. LearnerProfilingAgent (in live mode) — uses Azure OpenAI gpt-4o with a "
                    "JSON-schema-anchored system prompt that explicitly instructs the model to reason "
                    "about the student's background, infer domain confidence scores, and classify "
                    "knowledge levels. The model must justify each inference with a 1–2 sentence notes field.\n\n"
                    "2. StudyPlanAgent — mathematical reasoning via the Largest Remainder Method: "
                    "it allocates study days proportional to (exam_weight × knowledge_deficit_factor), "
                    "where the deficit factor amplifies time for weak/unknown domains. This is deterministic "
                    "reasoning, not AI, but it is still a non-trivial multi-factor computation.\n\n"
                    "3. ProgressAgent — multi-factor reasoning: readiness = 0.55 × domain_score + "
                    "0.25 × hours_progress + 0.20 × practice_factor. The GO/NO-GO decision also "
                    "inspects the count of 'critical' domains (behind by ≥2 rating points), "
                    "not just the aggregate score. This catches students who are average overall "
                    "but have a dangerous gap in a high-weight domain.\n\n"
                    "4. CertificationRecommendationAgent — conditional branching: it checks quiz score "
                    "vs two thresholds (70% GO, 85% strong GO), then selects from different recommendations "
                    "based on the target certification, generates a targeted remediation plan listing "
                    "specific weak domains, and chooses 2–3 relevant next-cert suggestions from a lookup table."
                ),
                (
                    "What reasoning pattern did you use for the study plan allocation? Could you get stuck in infinite loops?",
                    "We use the Largest Remainder Method (LRM) at day granularity.\n\n"
                    "The algorithm: each active domain gets a base allocation = "
                    "(domain_weight × deficit_factor × total_days). Decimal remainders are ranked descending "
                    "and one extra day is given to the highest-remainder domains until precision is achieved. "
                    "This guarantees the total equals exactly the study budget with no overflows "
                    "(guardrail G-10 also verifies this post-hoc).\n\n"
                    "For the remediation loop question: no, we cannot get into a true infinite loop "
                    "because each loop iteration runs a fresh quiz, and statistically a student's knowledge "
                    "improves with each study cycle. However, in the current mock mode, the profiling scores "
                    "don't change between iterations. In a production live-AI deployment, we would "
                    "re-profile after each study cycle to detect actual knowledge improvement. "
                    "This is called out as a known extension point in our documentation."
                ),
            ],
        },
        {
            "section": "Guardrails & Responsible AI",
            "qa": [
                (
                    "What guardrails have you implemented and why did you choose those specific rules?",
                    "We have 17 guardrail rules in 5 categories, implemented in guardrails.py.\n\n"
                    "Input guardrails (G-01 to G-05) prevent obviously broken data from flowing to expensive "
                    "AI operations — for example, we block empty student names (G-01) before calling Azure OpenAI. "
                    "G-05 adds a PII transparency notice since we store the student's real name in session state.\n\n"
                    "Profile guardrails (G-06 to G-08) ensure the LearnerProfile output is structurally complete. "
                    "G-07 is the most important: it BLOCKS any confidence score outside [0, 1] because downstream "
                    "agents perform arithmetic on these values — an out-of-range score would silently corrupt "
                    "the Gantt allocation and the readiness formula.\n\n"
                    "Plan guardrails (G-09 to G-10): G-09 blocks any study task where start_week > end_week, "
                    "which was a real bug we hit during development when the LRM rounding overflowed in "
                    "3-week plans with 5 active domains. G-10 warns if allocated hours exceed the student's "
                    "declared budget by more than 10%.\n\n"
                    "Progress guardrails (G-11 to G-13) validate that self-rated data is sensible "
                    "before the readiness formula is applied.\n\n"
                    "Content guardrails (G-16 to G-17): G-17 is important for Responsible AI — it "
                    "verifies that every URL from LearningPathCuratorAgent and CertificationRecommendationAgent "
                    "originates from learn.microsoft.com, pearsonvue.com, or other trusted domains. "
                    "This prevents hallucinated or injected URLs from reaching the user."
                ),
                (
                    "How do you handle PII and data privacy in your system?",
                    "In its current form, CertPrep AI does not persist any data outside the user's browser session.\n\n"
                    "All profile data is stored in Streamlit's session_state, which is ephemeral and scoped to "
                    "a single browser session. Nothing is written to a database or sent to an external service "
                    "in mock mode. Guardrail G-05 explicitly shows the user a notice that their name is "
                    "session-only and not transmitted externally.\n\n"
                    "In live Azure OpenAI mode, the student's background_text and existing certs are sent "
                    "to Azure OpenAI for profiling. We document this in the sidebar ('Live Azure OpenAI' mode label) "
                    "and recommend that users avoid including sensitive PII in the background description.\n\n"
                    "For the email feature, we only send the report to the email address the user explicitly "
                    "enters; we do not store it beyond the session.\n\n"
                    "In a production version we would add: data minimisation (strip PII before LLM calls), "
                    "Azure Content Safety API integration for the output content filter, and an explicit "
                    "consent checkbox aligned with GDPR Article 6."
                ),
            ],
        },
        {
            "section": "Technical Implementation",
            "qa": [
                (
                    "How does the study plan allocation algorithm work? Why did you choose it?",
                    "We use the Largest Remainder Method (LRM) at day granularity — "
                    "the same algorithm used in proportional election systems to distribute seats fairly.\n\n"
                    "Step 1: Compute each domain's raw day allocation = "
                    "total_days × (exam_weight × deficit_factor). "
                    "deficit_factor is 2.0 for UNKNOWN domains, 1.5 for WEAK, 1.0 for MODERATE, and 0.3 for STRONG.\n\n"
                    "Step 2: Floor each allocation to get integer days. "
                    "Since floors always under-count, sum them and compute the shortfall.\n\n"
                    "Step 3: Sort domains by their decimal remainders descending and give one extra day "
                    "to the top-N domains until we've distributed exactly total_days.\n\n"
                    "Step 4: Convert days back to week ranges (start_week = 1 + cumulative_days // 7). "
                    "Working at day granularity prevents start > end bugs that occur when you have "
                    "more active domains than study weeks — a real edge case we hit with 5 domains in a 3-week plan.\n\n"
                    "We chose LRM over a simpler round-robin because it correctly handles the case where "
                    "one domain's weight is so small (e.g. 10%) that it rounds to zero days in a short plan."
                ),
                (
                    "How does the readiness scoring formula work and how did you calibrate the weights?",
                    "The formula is: readiness_pct = 0.55 × weighted_domain_score + "
                    "0.25 × hours_progress_pct + 0.20 × practice_factor.\n\n"
                    "weighted_domain_score: each domain's self-rating (1–5) is normalised to [0,1] "
                    "and multiplied by the AI-102 exam blueprint weight. "
                    "This means a poor score in Computer Vision (22.5% weight) hurts more than "
                    "a poor score in Conversational AI (10% weight), matching the exam's stakes.\n\n"
                    "hours_progress_pct: simple ratio of hours_spent to total_budget_hours, "
                    "capped at 100%. This rewards consistent study effort.\n\n"
                    "practice_factor: 'yes' + score ≥ 70% gives 1.0; 'yes' + score < 70% gives "
                    "score/100 (partial credit); 'some' gives 0.5; 'no' gives 0.2 "
                    "(we do not penalise heavily since early in prep practice exams aren't expected).\n\n"
                    "Weight calibration rationale: domain knowledge is the strongest predictor of "
                    "exam success (55%), time invested matters but not as much (25%), "
                    "and practice exams are a leading indicator but students shouldn't be penalised "
                    "for not having done them yet (20%). These weights are inspired by published "
                    "Microsoft certification coaching guidance."
                ),
                (
                    "The reference suggests integrating with the Microsoft Learn MCP server. Did you use it?",
                    "In our current implementation we use a hardcoded offline catalogue of 30+ MS Learn module "
                    "URLs (all real, verified learn.microsoft.com pages) rather than calling the live MCP server. "
                    "This was a deliberate trade-off for reliability and demo stability — the app works "
                    "completely offline without any external API dependency.\n\n"
                    "Architecturally, the LearningPathCuratorAgent is designed to be swapped: "
                    "the _LEARN_CATALOGUE dict in learning_path_curator.py can be replaced by a "
                    "call to the Microsoft Learn Catalog API (https://learn.microsoft.com/api/catalog/) "
                    "or the MCP server without changing any downstream code, because the output shape "
                    "(LearningPath dataclass) remains identical.\n\n"
                    "The MCP integration would give us real-time module availability, updated durations, "
                    "and new content that post-dates our catalogue. We'd add it as enhancement Option A "
                    "in any production roadmap."
                ),
                (
                    "What happens if Azure OpenAI is unavailable or the API key is wrong?",
                    "We have a three-layer fallback strategy.\n\n"
                    "Layer 1 (before the call): Guardrail G-04 checks that the exam code is valid, "
                    "and if Azure credentials aren't loaded, the sidebar shows a warning and "
                    "automatically switches back to Mock mode (we check if az_endpoint and az_key are "
                    "both non-empty before allowing Live mode).\n\n"
                    "Layer 2 (during the call): the LearnerProfilingAgent call is wrapped in a "
                    "try/except block. If it throws (AuthenticationError, RateLimitError, network failure, etc.), "
                    "we display a Streamlit error with the exception message and then fall back to "
                    "run_mock_profiling(), setting mode_badge to '🧪 Mock (fallback)' so the user "
                    "knows they're not getting a live AI result.\n\n"
                    "Layer 3 (post-hoc): Profile guardrails G-06/G-07/G-08 run on whatever profile "
                    "was returned (mock or live) to ensure structural validity before downstream agents receive it.\n\n"
                    "This means the app is always usable, even in a demo environment with no Azure credentials."
                ),
            ],
        },
        {
            "section": "User Experience & Demo",
            "qa": [
                (
                    "Can you demo the end-to-end flow right now? What should we look for?",
                    "Absolutely. Here's the suggested demo script:\n\n"
                    "1. Open http://localhost:8501 in a browser.\n\n"
                    "2. Fill in the intake form as 'Priya Sharma', background 'Python developer with "
                    "3 years experience, familiar with REST APIs and Azure', exam AI-102, 10 hrs/week, "
                    "8 weeks, concerns: 'Azure OpenAI RAG, Bot Service'. Click 'Generate Learner Profile'.\n\n"
                    "3. Notice the 5 coloured KPI cards: Student (purple), Experience (blue), "
                    "Study Budget (green), Risk Domains (orange), Avg Confidence (dynamic).\n\n"
                    "4. Go to Domain Map tab — point out the radar chart and the Radar Insights callout "
                    "showing the strongest axis, below-threshold domains, and the bar chart insights.\n\n"
                    "5. Go to Study Setup tab — show the prerequisite banners (AI-900 recommended), "
                    "then the Gantt chart with colour-coded priority bars and Week N labels. "
                    "Hover over a bar to see the tooltip.\n\n"
                    "6. Go to Learning Path tab — expand a risk domain like Generative AI to show "
                    "the MS Learn module links with difficulty/duration tags.\n\n"
                    "7. Go to My Progress tab — enter 20 hours, 4 weeks elapsed, rate domains with sliders, "
                    "click 'Assess My Readiness'. Show the gauge, GO/NO-GO card, and nudge alerts.\n\n"
                    "8. Go to Knowledge Check tab — click 'Generate New Quiz', answer a few questions, "
                    "submit, show the domain breakdown and per-question feedback.\n\n"
                    "9. Go back to Recommendations tab — the CertificationRecommendationAgent now shows "
                    "its output (GO/NO-GO + exam logistics + next cert suggestions)."
                ),
                (
                    "How does the system handle a returning user — someone who comes back after a week of studying?",
                    "The returning-user journey is designed through the sidebar radio button "
                    "'🔄 Returning — update my progress'.\n\n"
                    "Selecting it changes the hero banner to a personalised welcome-back message "
                    "using the stored session_state profile name and last check-in readiness score.\n\n"
                    "In the My Progress tab, if a previous ProgressSnapshot exists in session_state, "
                    "all form fields are pre-populated with the last values: hours, weeks, domain sliders, "
                    "and practice exam status. The top of the tab shows a 'Last check-in result' card "
                    "with the previous readiness score, verdict, and GO/NO-GO in the appropriate colour.\n\n"
                    "When the learner re-submits, the new assessment overwrites the previous one. "
                    "Smart nudges compare current vs expected progress — for example, if the student "
                    "is behind on hours or still hasn't done a practice exam, a WARNING-level nudge fires.\n\n"
                    "The weekly email sender is also available here: if the user entered their email "
                    "in the sidebar, it's pre-filled in the 'Send report to' field."
                ),
            ],
        },
        {
            "section": "Extensibility & Future Work",
            "qa": [
                (
                    "What would you add if you had another week?",
                    "In priority order:\n\n"
                    "1. Live Microsoft Learn MCP server integration — replace the offline catalogue "
                    "with real-time data from https://github.com/microsoftdocs/mcp so module "
                    "availability and durations stay current.\n\n"
                    "2. Azure AI Foundry orchestration — deploy the 7 agents as Azure AI Foundry "
                    "Agent Service endpoints with the Foundry SDK, enabling proper telemetry, "
                    "token usage tracking, and cloud-hosted evaluation.\n\n"
                    "3. Persistent learner storage — replace session_state with Azure Cosmos DB "
                    "so a learner can close the browser and return to exactly where they left off "
                    "across weeks of preparation.\n\n"
                    "4. Azure Content Safety API — replace the heuristic G-16 keyword filter with "
                    "the real Content Safety service (harm categories: hate, self-harm, sexual, violence).\n\n"
                    "5. Adaptive quiz — instead of random sampling from the static bank, use "
                    "Item Response Theory to select questions slightly above the learner's current "
                    "ability for maximal learning signal (computerised adaptive testing).\n\n"
                    "6. Evaluation pipeline — add test cases for each agent using the Microsoft "
                    "Foundry SDK evaluation tools, scoring accuracy, relevance, and faithfulness "
                    "with automated metrics like BLEU/ROUGE for text outputs."
                ),
                (
                    "Is this system limited to AI-102? How would you extend it to other certifications?",
                    "AI-102 is the primary target but the architecture is certification-agnostic.\n\n"
                    "The domain registry (AI102_DOMAINS in models.py) is the only AI-102-specific "
                    "data structure. To support DP-100, AZ-204, or any other certification we would:\n\n"
                    "1. Add a new domain list (e.g. DP100_DOMAINS) with the corresponding syllabus areas and weights.\n"
                    "2. Extend _LEARN_CATALOGUE in learning_path_curator.py with domain-to-module mappings for the new cert.\n"
                    "3. Add questions for the new domains to _QUESTION_BANK in assessment_agent.py.\n"
                    "4. Add prerequisite entries to _CERT_PREREQ_MAP in study_plan_agent.py.\n"
                    "5. Add next-cert entries to _NEXT_CERT_MAP in cert_recommendation_agent.py.\n\n"
                    "The LearnerProfilingAgent prompt (in live mode) already includes the exam_target "
                    "in its system message, so it naturally adapts to a different certification. "
                    "The guardrails, scoring formula, and UI are all target-cert-independent. "
                    "Realistically, we could support a new certification with 1–2 hours of data entry."
                ),
            ],
        },
    ]

    for section in qa_sections:
        story.append(section_header(section["section"], s, color=BLUE, bg=BLUE_L))
        story.append(sp(2))

        for q_text, a_text in section["qa"]:
            q_block = Table(
                [[Paragraph(f"Q: {q_text}", s["q"])]],
                colWidths=["100%"]
            )
            q_block.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), PURPLE_L),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING",(0,0),(-1,-1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING",(0,0),(-1,-1), 10),
                ("BOX",        (0, 0), (-1, -1), 1, PURPLE),
            ]))

            # Split answer into paragraphs
            a_paras = []
            for para in a_text.split("\n\n"):
                para = para.strip()
                if para:
                    if para.startswith(tuple(
                        [f"{i}." for i in range(1, 10)] + ["Layer", "Step", "Weight", "In priority"]
                    )):
                        a_paras.append(Paragraph(para, s["bullet"]))
                    else:
                        a_paras.append(Paragraph(para, s["a"]))

            story.append(KeepTogether([
                q_block,
                sp(1),
                *a_paras,
                sp(3),
                hr(color=HexColor("#D1D5DB"), width=0.5),
                sp(1),
            ]))

    # ── Final: quick-reference card ───────────────────────────────────────────
    story.append(PageBreak())
    story.append(section_header("Quick Reference — Key Numbers & Files", s))
    story.append(sp(2))

    qr_data = [
        ["Item", "Value / Location"],
        ["Total agents", "7 (Intake, Profiling, Curator, Planner, Progress, Assessment, CertRec)"],
        ["Total guardrails", "17 rules across 5 categories (BLOCK / WARN / INFO)"],
        ["Assessment question bank", "30 questions across 6 domains × 3 difficulty levels"],
        ["Readiness formula", "0.55 × domain + 0.25 × hours + 0.20 × practice"],
        ["GO threshold", "≥ 75% readiness + 0 critical domains"],
        ["Assessment pass mark", "≥ 60% quiz score → feeds CertRec agent"],
        ["Study plan algorithm", "Largest Remainder Method at day granularity (7 days/week)"],
        ["UI tabs", "7 tabs: Domain Map, Study Setup, Learning Path, Recommendations, My Progress, Knowledge Check, Raw JSON"],
        ["Mock mode", "Fully functional offline — no Azure credentials required"],
        ["Live mode fallback", "Azure OpenAI error → auto-fallback to mock profiler"],
        ["Main UI file", "streamlit_app.py  (~1600 lines)"],
        ["Guardrails file", "src/cert_prep/guardrails.py"],
        ["Documentation", "docs/technical_documentation.pdf  (this script's sibling output)"],
    ]

    story.append(coloured_table(
        [[Paragraph(str(c), ParagraphStyle("TH", fontSize=9, textColor=white, fontName="Helvetica-Bold"))
          for c in qr_data[0]]] +
        [[Paragraph(str(c), ParagraphStyle("TC", fontSize=9, textColor=DARK,
                                            fontName="Courier" if i == 0 else "Helvetica", leading=14))
          for i, c in enumerate(row)] for row in qr_data[1:]],
        [60*mm, 117*mm]
    ))

    doc.build(story)
    print(f"✅ Judge playbook saved → {out_path}")


# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    docs_dir = Path(__file__).parent.parent / "docs"
    docs_dir.mkdir(exist_ok=True)

    build_technical_doc(docs_dir / "technical_documentation.pdf")
    build_judge_playbook(docs_dir / "judge_playbook.pdf")
    print(f"\n🎉 Both documents saved to: {docs_dir.resolve()}")
