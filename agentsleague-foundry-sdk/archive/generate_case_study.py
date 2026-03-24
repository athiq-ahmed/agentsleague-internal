"""
AI-102 Certification Prep – Multi-Agent System Case Study Generator
Produces a polished PDF with 3 end-to-end student scenarios.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import Flowable
import datetime

# ─── Palette (mirrors the architecture diagram) ────────────────────────────
C_PURPLE_DARK  = colors.HexColor("#5C2D91")
C_PURPLE_LIGHT = colors.HexColor("#F5F0FF")
C_PINK_DARK    = colors.HexColor("#B4009E")
C_PINK_LIGHT   = colors.HexColor("#FDE7F3")
C_GREEN_DARK   = colors.HexColor("#107C10")
C_GREEN_LIGHT  = colors.HexColor("#E9F7EE")
C_GOLD_DARK    = colors.HexColor("#8A6D00")
C_GOLD_LIGHT   = colors.HexColor("#FFF4CE")
C_BLUE_DARK    = colors.HexColor("#0F6CBD")
C_BLUE_LIGHT   = colors.HexColor("#EEF6FF")
C_GREY_LIGHT   = colors.HexColor("#F5F5F5")
C_BLACK        = colors.HexColor("#1A1A1A")
C_WHITE        = colors.white

W, H = A4

# ─── Styles ─────────────────────────────────────────────────────────────────
base = getSampleStyleSheet()

def S(name, parent="Normal", **kw):
    return ParagraphStyle(name, parent=base[parent], **kw)

sTitle      = S("sTitle",      "Title",   fontSize=22, textColor=C_PURPLE_DARK, spaceAfter=4, leading=28)
sSubtitle   = S("sSubtitle",   "Normal",  fontSize=12, textColor=C_GOLD_DARK,  spaceAfter=2, leading=16)
sH1         = S("sH1",         "Heading1", fontSize=16, textColor=C_PURPLE_DARK, spaceBefore=14, spaceAfter=4)
sH2         = S("sH2",         "Heading2", fontSize=13, textColor=C_BLUE_DARK,   spaceBefore=8,  spaceAfter=3)
sH3         = S("sH3",         "Heading3", fontSize=11, textColor=C_PINK_DARK,   spaceBefore=6,  spaceAfter=2)
sBody       = S("sBody",       "Normal",   fontSize=10, textColor=C_BLACK,       leading=15, spaceAfter=4)
sBodyBold   = S("sBodyBold",   "Normal",   fontSize=10, textColor=C_BLACK,       leading=15, spaceAfter=4, fontName="Helvetica-Bold")
sSmall      = S("sSmall",      "Normal",   fontSize=9,  textColor=colors.HexColor("#444444"), leading=13)
sCaption    = S("sCaption",    "Normal",   fontSize=8,  textColor=colors.HexColor("#666666"), leading=12, alignment=TA_CENTER)
sLabel      = S("sLabel",      "Normal",   fontSize=9,  textColor=C_WHITE,       fontName="Helvetica-Bold", leading=12, alignment=TA_CENTER)
sFooter     = S("sFooter",     "Normal",   fontSize=8,  textColor=colors.HexColor("#888888"), alignment=TA_CENTER)

# ─── Helper Flowables ────────────────────────────────────────────────────────
def hr(color=C_PURPLE_DARK, width=0.5):
    return HRFlowable(width="100%", thickness=width, color=color, spaceAfter=4, spaceBefore=4)

def sp(h=4):
    return Spacer(1, h)

def section_title(text, scenario_num=None, color=C_PURPLE_DARK, bg=C_PURPLE_LIGHT):
    label = f"SCENARIO {scenario_num}" if scenario_num else "OVERVIEW"
    data = [[Paragraph(f'<font color="white"><b>{label}</b></font>', sLabel),
             Paragraph(f'<b>{text}</b>', S("st", fontSize=14, textColor=color))]]
    t = Table(data, colWidths=[28*mm, None])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,0), color),
        ("BACKGROUND", (1,0), (1,0), bg),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING",(0,0), (0,0), 6),
        ("LEFTPADDING",(1,0), (1,0), 10),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
        ("BOX",        (0,0), (-1,-1), 1, color),
        ("ROUNDEDCORNERS", [4]),
    ]))
    return t

def agent_step_table(steps):
    """steps = list of (agent, action, output) tuples"""
    hdr = [
        Paragraph("<b>Agent</b>", sLabel),
        Paragraph("<b>Action</b>", sLabel),
        Paragraph("<b>Output / Decision</b>", sLabel),
    ]
    rows = [hdr]
    for i, (agent, action, output) in enumerate(steps):
        bg = C_GREY_LIGHT if i % 2 == 0 else C_WHITE
        rows.append([
            Paragraph(f"<b>{agent}</b>", S("ac", fontSize=9, textColor=C_PURPLE_DARK, fontName="Helvetica-Bold")),
            Paragraph(action, sSmall),
            Paragraph(output, sSmall),
        ])
    col_w = [45*mm, 65*mm, 72*mm]
    t = Table(rows, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), C_PURPLE_DARK),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_GREY_LIGHT, C_WHITE]),
        ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#CCCCCC")),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
    ]))
    return t

def score_table(domain_scores, overall, threshold_overall=75, threshold_domain=70):
    hdr = [Paragraph("<b>Domain</b>", sLabel),
           Paragraph("<b>Score %</b>", sLabel),
           Paragraph("<b>Threshold</b>", sLabel),
           Paragraph("<b>Status</b>", sLabel)]
    rows = [hdr]
    for domain, score in domain_scores:
        passed = score >= threshold_domain
        status = "✓ Pass" if passed else "✗ Gap"
        status_color = C_GREEN_DARK if passed else C_PINK_DARK
        rows.append([
            Paragraph(domain, sSmall),
            Paragraph(f"<b>{score}%</b>", S("sc", fontSize=9, textColor=C_BLACK, fontName="Helvetica-Bold")),
            Paragraph(f"{threshold_domain}%", sSmall),
            Paragraph(f"<b>{status}</b>", S("ss", fontSize=9, textColor=status_color, fontName="Helvetica-Bold")),
        ])
    # Overall row
    passed_overall = overall >= threshold_overall
    ov_color = C_GREEN_DARK if passed_overall else C_PINK_DARK
    rows.append([
        Paragraph("<b>OVERALL</b>", S("ov", fontSize=10, fontName="Helvetica-Bold")),
        Paragraph(f"<b>{overall}%</b>", S("ovs", fontSize=10, fontName="Helvetica-Bold", textColor=ov_color)),
        Paragraph(f"{threshold_overall}%", sSmall),
        Paragraph(f"<b>{'✓ READY' if passed_overall else '✗ NOT READY'}</b>",
                  S("ovst", fontSize=10, fontName="Helvetica-Bold", textColor=ov_color)),
    ])
    t = Table(rows, colWidths=[85*mm, 28*mm, 28*mm, 28*mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), C_GREEN_DARK),
        ("BACKGROUND",    (0,-1),(-1,-1), C_GREEN_LIGHT),
        ("ROWBACKGROUNDS",(0,1), (-1,-2), [C_GREY_LIGHT, C_WHITE]),
        ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#CCCCCC")),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("BOX",           (0,-1),(-1,-1), 1, C_GREEN_DARK),
    ]))
    return t

def profile_table(rows_data, col_label_w=45*mm):
    rows = []
    for label, value in rows_data:
        rows.append([
            Paragraph(f"<b>{label}</b>", S("pl", fontSize=9, textColor=C_GOLD_DARK, fontName="Helvetica-Bold")),
            Paragraph(value, sSmall),
        ])
    t = Table(rows, colWidths=[col_label_w, None])
    t.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [C_GOLD_LIGHT, C_WHITE]),
        ("GRID",           (0,0), (-1,-1), 0.4, colors.HexColor("#DDDDDD")),
        ("VALIGN",         (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",     (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",  (0,0), (-1,-1), 5),
        ("LEFTPADDING",    (0,0), (-1,-1), 7),
    ]))
    return t

def decision_box(decision, rationale, color=C_GREEN_DARK, bg=C_GREEN_LIGHT):
    data = [[
        Paragraph(f'<font color="white"><b>DECISION</b></font>', sLabel),
        Paragraph(f'<b><font color="{color.hexval() if hasattr(color,"hexval") else "#107C10"}">{decision}</font></b><br/>{rationale}',
                  S("db", fontSize=10, leading=15, textColor=C_BLACK))
    ]]
    t = Table(data, colWidths=[24*mm, None])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(0,0), color),
        ("BACKGROUND",   (1,0),(1,0), bg),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",   (0,0),(-1,-1), 10),
        ("BOTTOMPADDING",(0,0),(-1,-1), 10),
        ("LEFTPADDING",  (0,0),(0,0), 8),
        ("LEFTPADDING",  (1,0),(1,0), 12),
        ("BOX",          (0,0),(-1,-1), 1.5, color),
    ]))
    return t

def study_plan_table(weeks):
    """weeks = list of (week, focus, resources, milestone)"""
    hdr = [Paragraph("<b>Week</b>", sLabel),
           Paragraph("<b>Focus Domain</b>", sLabel),
           Paragraph("<b>Microsoft Learn Modules</b>", sLabel),
           Paragraph("<b>Milestone</b>", sLabel)]
    rows = [hdr] + [
        [Paragraph(f"<b>Wk {w}</b>", S("wk", fontSize=9, fontName="Helvetica-Bold")),
         Paragraph(f, sSmall),
         Paragraph(r, sSmall),
         Paragraph(m, sSmall)]
        for w, f, r, m in weeks
    ]
    t = Table(rows, colWidths=[14*mm, 50*mm, 75*mm, 43*mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), C_BLUE_DARK),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_BLUE_LIGHT, C_WHITE]),
        ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#CCCCCC")),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
    ]))
    return t

# ─── Page template (header/footer) ──────────────────────────────────────────
def build_header_footer(canvas, doc):
    canvas.saveState()
    # Top rule
    canvas.setStrokeColor(C_PURPLE_DARK)
    canvas.setLineWidth(2)
    canvas.line(20*mm, H - 14*mm, W - 20*mm, H - 14*mm)
    # Header text
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawString(20*mm, H - 11*mm, "Microsoft Agents League – AI-102 Certification Prep  |  Multi-Agent System Case Study")
    canvas.drawRightString(W - 20*mm, H - 11*mm, "Confidential – Internal Draft")
    # Bottom rule
    canvas.line(20*mm, 15*mm, W - 20*mm, 15*mm)
    canvas.drawCentredString(W / 2, 10*mm, f"Page {doc.page}")
    canvas.drawString(20*mm, 10*mm, "© 2026 Agents League Team")
    canvas.drawRightString(W - 20*mm, 10*mm, "AI-102 Exam Prep • Case Study")
    canvas.restoreState()

# ─── Document build ──────────────────────────────────────────────────────────
output_path = r"d:/OneDrive/Athiq/MSFT/Agents League/Notes/AI102_CaseStudy.pdf"
doc = SimpleDocTemplate(
    output_path, pagesize=A4,
    leftMargin=20*mm, rightMargin=20*mm,
    topMargin=22*mm, bottomMargin=22*mm,
)

story = []

# ════════════════════ COVER / TITLE ═════════════════════════════════════════
story.append(sp(15))
story.append(Paragraph("AI-102: Designing and Implementing", sTitle))
story.append(Paragraph("a Microsoft Azure AI Solution", sTitle))
story.append(sp(4))
story.append(Paragraph("Multi-Agent System — Student Case Study", sSubtitle))
story.append(hr(C_PURPLE_DARK, 2))
story.append(sp(4))
story.append(Paragraph(
    "This document presents <b>three realistic student scenarios</b> that walk through the complete "
    "end-to-end flow of the Certification Prep Multi-Agent System. Each scenario covers: "
    "student profiling, personalised study plan generation, adaptive assessment, "
    "AI-powered verification, scoring, gap analysis, and the final readiness decision.",
    sBody))
story.append(sp(4))

# System overview mini-table
overview_data = [
    [Paragraph("<b>Component</b>", sLabel), Paragraph("<b>Role</b>", sLabel)],
    [Paragraph("Learner Intake & Profiling", sSmall), Paragraph("Converts student input → structured learner profile with skill gaps and time budget", sSmall)],
    [Paragraph("1.1 Learning Path Planner", sSmall), Paragraph("Maps AI-102 syllabus domains to Microsoft Learn modules and resources", sSmall)],
    [Paragraph("1.2 Study Plan & Engagement Generator", sSmall), Paragraph("Produces week-by-week schedule with milestones; sends reminders", sSmall)],
    [Paragraph("2.1 Assessment Builder", sSmall), Paragraph("Generates scenario-based questions tagged by domain and Bloom's level", sSmall)],
    [Paragraph("2.2 Tiered Verifier + Repair Loop", sSmall), Paragraph("Validates question quality, coverage, and safety; auto-repairs failures", sSmall)],
    [Paragraph("2.3 Scoring Engine", sSmall), Paragraph("Computes domain-level and overall scores deterministically", sSmall)],
    [Paragraph("3.1 Gap Analyzer & Decision Policy", sSmall), Paragraph("Ready if overall ≥ 75 % AND every domain ≥ 70 %; else → targeted remediation", sSmall)],
    [Paragraph("3.2 Certification + Exam Planner", sSmall), Paragraph("Guides student to book and sit the AI-102 exam with concrete next steps", sSmall)],
]
ov_t = Table(overview_data, colWidths=[58*mm, None], repeatRows=1)
ov_t.setStyle(TableStyle([
    ("BACKGROUND",    (0,0), (-1,0), C_PURPLE_DARK),
    ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_GREY_LIGHT, C_WHITE]),
    ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#CCCCCC")),
    ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ("TOPPADDING",    (0,0), (-1,-1), 5),
    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ("LEFTPADDING",   (0,0), (-1,-1), 7),
]))
story.append(ov_t)
story.append(sp(6))
story.append(Paragraph(
    "<b>Readiness thresholds:</b>  Overall score ≥ 75 %  &amp;  All individual domains ≥ 70 %",
    S("thresh", fontSize=9, textColor=C_GREEN_DARK, fontName="Helvetica-Bold",
      borderPad=6, borderColor=C_GREEN_DARK, borderWidth=1,
      backColor=C_GREEN_LIGHT, leading=14)))
story.append(PageBreak())

# ════════════════════════════════════════════════════════════════════════════
# SCENARIO 1 – PRIYA  (Complete beginner, 10 weeks)
# ════════════════════════════════════════════════════════════════════════════
story.append(section_title("Priya Sharma — Fresh Graduate, Career Starter", scenario_num=1,
                           color=C_PURPLE_DARK, bg=C_PURPLE_LIGHT))
story.append(sp(6))

story.append(Paragraph("1A. Student Profile", sH2))
story.append(profile_table([
    ("Name",          "Priya Sharma"),
    ("Background",    "BSc Computer Science graduate (2025); strong Python basics; no prior Azure or AI services experience"),
    ("Goal",          "Pass AI-102 to strengthen job applications for AI Engineer roles"),
    ("Available time","10 hours/week over 10 weeks (100 hours total)"),
    ("Declared gaps", "No hands-on Azure experience; unfamiliar with Cognitive Services APIs; limited ML theory"),
    ("Preferences",   "Prefers structured, linear learning; needs motivational reminders; hands-on labs important"),
]))
story.append(sp(8))

story.append(Paragraph("1B. End-to-End Agent Flow", sH2))
story.append(agent_step_table([
    ("Learner Intake\n& Profiling",
     "Parses Priya's free-text input; identifies zero Azure exposure, moderate Python, 10 hrs/wk budget",
     "Profile: {level: beginner, azure_xp: 0, time_budget: 10h/wk, style: linear+labs, domains_at_risk: ALL}"),
    ("1.1 Learning Path\nPlanner",
     "Maps all 6 AI-102 domains; assigns weights proportional to exam blueprint; anchors every module to Microsoft Learn paths",
     "Ordered path: Fundamentals of AI →  Azure AI Fundamentals → Cognitive Services → Vision → NLP → Generative AI. 18 Learn modules identified."),
    ("1.2 Study Plan\n& Engagement",
     "Distributes 18 modules across 8 study weeks (2 exam-sim weeks reserved); sets weekly milestones; schedules 3× weekly reminders",
     "10-week plan generated (see table below). Reminder cadence: Mon recap, Wed lab nudge, Fri milestone check."),
    ("2.1 Assessment\nBuilder",
     "After Wk 8 study plan completion signal → builds 60-question mock exam; tags each Q by domain + Bloom level (Apply/Analyse)",
     "60 questions generated: 10 per domain. Mix: 40% scenario-based, 35% code-completion, 25% concept MCQ."),
    ("2.2 Tiered Verifier\n+ Repair Loop",
     "Tier-1: factual accuracy check (answer key vs. docs). Tier-2: coverage audit (each domain ≥ 8 Q). Tier-3: safety (no leaked exam content). 4 questions flagged → repaired → re-verified.",
     "60/60 questions approved after 1 repair pass. Verifier confidence score: 0.94."),
    ("2.3 Scoring\nEngine",
     "Priya completes the 60-question mock; engine scores each domain independently; computes weighted overall",
     "See score breakdown table below."),
    ("3.1 Gap Analyzer\n& Decision Policy",
     "Compares each domain score vs. 70 % threshold; flags NLP (62%) and Generative AI (58%) as gaps; applies overall ≥ 75 % gate",
     "Decision: NOT READY. Remediation plan: 2 focused weeks on NLP + Gen AI modules + targeted re-assessment."),
    ("Remediation Loop\n(automatic)",
     "System re-routes to Preparation block with narrowed scope: only NLP and Generative AI modules refreshed",
     "New 2-week targeted plan generated. 30-question focused re-assessment built and verified."),
    ("2nd Assessment\nCycle",
     "Priya completes the 30-question targeted re-assessment",
     "NLP: 74% → 78%  |  Gen AI: 58% → 76%  |  Overall: 68% → 79%"),
    ("3.1 Gap Analyzer\n(2nd pass)",
     "All domains now ≥ 70%; overall 79% ≥ 75%",
     "Decision: READY. Routes to 3.2 Certification + Exam Planner."),
    ("3.2 Certification\n+ Exam Planner",
     "Generates exam booking checklist; recommends Pearson VUE online proctored exam; suggests final day-before review",
     "Booking link, ID requirements, calm-down tips, and 2-hour quick-review cheat sheet delivered."),
]))
story.append(sp(8))

story.append(Paragraph("1C. Generated Study Plan (excerpt)", sH2))
story.append(study_plan_table([
    (1, "Azure AI Fundamentals\n+ Platform Overview",
     "Intro to Azure AI • Azure AI Services overview • Responsible AI",
     "Create Azure AI resource; call REST endpoint"),
    (2, "Plan & Manage\nAzure AI Solutions",
     "Authenticate & secure AI services • Monitor with Azure Monitor • Deploy containers",
     "Deploy Cognitive Services container locally"),
    (3, "Computer Vision",
     "Azure AI Vision • Image Analysis • Face API • Custom Vision training",
     "Build image classifier on custom dataset"),
    (4, "Document Intelligence\n& Knowledge Mining",
     "Azure AI Document Intelligence • Azure Cognitive Search • Custom skills",
     "Extract structured data from PDF invoices"),
    (5, "Natural Language\nProcessing",
     "Azure AI Language • Sentiment analysis • NER • Question answering",
     "Build FAQ bot with CLU + QnA"),
    (6, "Conversational AI\n+ Bot Service",
     "Azure Bot Service • Power Virtual Agents • Dialogues",
     "Deploy FAQ bot to Teams channel"),
    (7, "Generative AI\n+ Azure OpenAI",
     "Azure OpenAI Service • Prompt engineering • RAG patterns • Content filters",
     "Build RAG app with Azure OpenAI + Cognitive Search"),
    (8, "Revision + Mock Exam",
     "Full syllabus revision using flash cards • 60-question mock exam",
     "Complete system mock exam → trigger assessment agent"),
    ("9–10", "Targeted Remediation\n(NLP + Gen AI)",
     "Deepen NLP modules • Azure OpenAI advanced patterns",
     "30-question focused re-assessment → READY"),
]))
story.append(sp(8))

story.append(Paragraph("1D. Assessment Scores", sH2))
story.append(score_table([
    ("Plan & Manage Azure AI Solutions",         82),
    ("Implement Computer Vision Solutions",      78),
    ("Implement NLP Solutions",                  62),
    ("Implement Document Intelligence",          71),
    ("Implement Conversational AI Solutions",    75),
    ("Implement Generative AI Solutions",        58),
], overall=68))
story.append(sp(4))
story.append(Paragraph("↑ After first assessment. Two domains below 70% threshold triggered remediation loop.", sCaption))
story.append(sp(6))

story.append(Paragraph("1E. Final Decision", sH2))
story.append(decision_box(
    "✓ READY TO SIT AI-102 (after remediation cycle)",
    "2nd cycle scores: NLP 78% | Gen AI 76% | Overall 79%. All domains > 70%, overall > 75%. "
    "Estimated time from start to ready: 10 weeks. Booking recommendation: Pearson VUE online proctored.",
    color=C_GREEN_DARK, bg=C_GREEN_LIGHT
))
story.append(PageBreak())

# ════════════════════════════════════════════════════════════════════════════
# SCENARIO 2 – MARCUS  (Azure pro, 3-week sprint)
# ════════════════════════════════════════════════════════════════════════════
story.append(section_title("Marcus Chen — Cloud Solutions Architect, Fast-Track", scenario_num=2,
                           color=C_BLUE_DARK, bg=C_BLUE_LIGHT))
story.append(sp(6))

story.append(Paragraph("2A. Student Profile", sH2))
story.append(profile_table([
    ("Name",          "Marcus Chen"),
    ("Background",    "5 years as Cloud Solutions Architect; deep Azure infrastructure expertise (AZ-104, AZ-305 certified); no AI/ML certifications"),
    ("Goal",          "Add AI-102 to badge wall before Q1 performance review; wants fast-track focused prep"),
    ("Available time","15 hours/week over 3 weeks (45 hours total)"),
    ("Declared gaps", "AI-specific services (Vision, NLP, Gen AI); responsible AI governance; Azure OpenAI Service details"),
    ("Preferences",   "Skips basics he already knows; wants reference cards; assessment-heavy approach to identitfy gaps fast"),
]))
story.append(sp(8))

story.append(Paragraph("2B. End-to-End Agent Flow", sH2))
story.append(agent_step_table([
    ("Learner Intake\n& Profiling",
     "Detects existing AZ-104/AZ-305 certs; maps Azure platform knowledge as 'known'; flags AI services domains as priority gaps",
     "Profile: {level: advanced_azure, ai_xp: low, time_budget: 15h/wk x3, style: gap-focused+reference, skip_modules: [platform_basics, auth_security]}"),
    ("1.1 Learning Path\nPlanner",
     "Skips 4 already-mastered modules (auth, monitoring, containers, deployment); focuses path on AI-specific domains only",
     "Compressed path: 8 modules (was 18). Azure AI Vision, NLP, Document Intelligence, OpenAI Service, Responsible AI governance."),
    ("1.2 Study Plan\n& Engagement",
     "Builds aggressive 3-week plan; front-loads hardest domains; schedules diagnostics at end of week 1",
     "3-week plan with daily 2-hour blocks. Mid-point diagnostic at end of Week 1 to validate pace."),
    ("Week 1\nDiagnostic Assessment",
     "After 5 days of study, system triggers an early 30-question diagnostic to check pace and identify any surprises",
     "Diagnostic: Vision 85%, NLP 71%, Gen AI 55%, Responsible AI 68%. Gen AI flagged as bigger gap than expected."),
    ("Plan Adaptation",
     "Gap Analyzer compares diagnostic vs. thresholds; triggers partial replan for Week 2 to allocate extra 3 hours to Gen AI",
     "Revised Week 2: +3h Azure OpenAI deep-dive; -3h Vision (already strong). Dynamic replan delivered."),
    ("2.1 Assessment\nBuilder",
     "After Week 3 study → builds 50-question final mock; skips pure infrastructure Qs; heavier weighting on AI service config + security",
     "50 questions: 35% Gen AI, 25% NLP, 20% Vision, 10% Document Intelligence, 10% Responsible AI."),
    ("2.2 Tiered Verifier\n+ Repair Loop",
     "All 50 questions pass Tier-1 and Tier-2. 2 Gen AI questions flagged for potential answer ambiguity → repaired.",
     "50/50 approved after 1 repair pass. Verifier confidence: 0.97."),
    ("2.3 Scoring\nEngine",
     "Marcus completes mock exam",
     "See score table below. All domains pass on first attempt."),
    ("3.1 Gap Analyzer\n& Decision Policy",
     "All domains ≥ 70%, overall ≥ 75%",
     "Decision: READY. No remediation needed. Routes directly to Certification Planner."),
    ("3.2 Certification\n+ Exam Planner",
     "Generates fast-track booking checklist; recommends earliest available slot (within 5 days); provides 2-page reference card",
     "Same-week exam booking recommended. Reference cards: Azure AI service endpoints, exam time-management tips."),
]))
story.append(sp(8))

story.append(Paragraph("2C. Generated Study Plan", sH2))
story.append(study_plan_table([
    (1, "Azure AI Vision +\nDocument Intelligence",
     "Azure AI Vision (Image Analysis, Face, OCR) • Document Intelligence models • Custom Vision",
     "Build invoice extraction pipeline; mid-week diagnostic quiz"),
    (2, "NLP + Conversational AI\n+ Responsible AI",
     "Azure AI Language • CLU • Bot Service • Responsible AI principles • Content Safety",
     "Build + deploy CLU model; Responsible AI assessment quiz"),
    (3, "Generative AI +\nAzure OpenAI Service",
     "Azure OpenAI: models, deployments, prompt engineering • RAG architecture • Content filters • BYOD",
     "RAG prototype with Cognitive Search; 50-question final mock exam"),
]))
story.append(sp(8))

story.append(Paragraph("2D. Assessment Scores", sH2))
story.append(score_table([
    ("Plan & Manage Azure AI Solutions",         91),
    ("Implement Computer Vision Solutions",      83),
    ("Implement NLP Solutions",                  76),
    ("Implement Document Intelligence",          79),
    ("Implement Conversational AI Solutions",    74),
    ("Implement Generative AI Solutions",        72),
], overall=79))
story.append(sp(4))
story.append(Paragraph("All domains ≥ 70%, overall 79% ≥ 75%. First-attempt pass. Total prep time: 3 weeks.", sCaption))
story.append(sp(6))

story.append(Paragraph("2E. Final Decision", sH2))
story.append(decision_box(
    "✓ READY TO SIT AI-102 — First Attempt",
    "All 6 domains cleared ≥ 70%. Overall 79%. No remediation required. "
    "Fast-track route completed in 3 weeks / 45 hours. Exam booking recommended within 5 days.",
    color=C_GREEN_DARK, bg=C_GREEN_LIGHT
))
story.append(PageBreak())

# ════════════════════════════════════════════════════════════════════════════
# SCENARIO 3 – SARAH  (Data Scientist, bridging ML → Azure AI)
# ════════════════════════════════════════════════════════════════════════════
story.append(section_title("Sarah Al-Rashid — Data Scientist, ML-to-Azure Bridge", scenario_num=3,
                           color=C_PINK_DARK, bg=C_PINK_LIGHT))
story.append(sp(6))

story.append(Paragraph("3A. Student Profile", sH2))
story.append(profile_table([
    ("Name",          "Sarah Al-Rashid"),
    ("Background",    "Senior Data Scientist at a retail enterprise; 7 years scikit-learn / PyTorch / Jupyter; Azure ML workspace experience but no Cognitive Services usage"),
    ("Goal",          "Formalise and certify Azure AI knowledge to lead company's AI-102 compliance programme"),
    ("Available time","8 hours/week over 5 weeks (40 hours total)"),
    ("Declared gaps", "Azure Cognitive Services (non-ML), Bot Service, Document Intelligence, Responsible AI policies in enterprise context"),
    ("Preferences",   "Learns by doing; likes API-first exploration; wants to map new concepts to familiar ML equivalents"),
]))
story.append(sp(8))

story.append(Paragraph("3B. End-to-End Agent Flow", sH2))
story.append(agent_step_table([
    ("Learner Intake\n& Profiling",
     "Recognises ML/data science background; maps Azure ML experience as partial credit for 'Plan & Manage' domain; flags Cognitive Services and Bot Service as cold-start gaps",
     "Profile: {level: expert_ml, azure_ml: yes, cognitive_services: no, bot_service: no, time_budget: 8h/wk x5, style: api-first+analogies}"),
    ("1.1 Learning Path\nPlanner",
     "Generates ML→Azure AI analogy map (e.g., scikit-learn pipeline ↔ Azure ML Pipeline; custom model ↔ Custom Vision); skips basic ML theory; emphasises service configuration and REST/SDK usage",
     "Tailored path: 11 modules with ML-to-Azure bridging commentary. Analogy reference card auto-generated."),
    ("1.2 Study Plan\n& Engagement",
     "5-week plan with API-first labs each week; learning style annotation (show SDK code before portal steps); end-of-week reflection prompts",
     "5-week plan with 3 lab sessions/week. Reflection prompts: 'How does this differ from your PyTorch pipeline?'"),
    ("Week 2\nEarly Diagnostic",
     "System detects Sarah completed Week 1+2 modules ahead of schedule; triggers early 20-question diagnostic",
     "Vision: 90%, Document Intelligence: 62%, NLP: 84%, Bot: 55%. Bot Service identified as major gap."),
    ("Plan Adaptation",
     "Decision Policy identifies Bot Service below threshold; re-allocates Week 3 to focus on Bot Service + CLU integration; compresses Vision (already strong)",
     "Dynamic replan: Week 3 becomes Bot Service deep-dive. Vision revision moved to Week 5 quick-review."),
    ("2.1 Assessment\nBuilder",
     "After Week 5 → builds 55-question enterprise-flavoured mock; includes policy/governance scenarios relevant to a senior practitioner",
     "55 questions: 20% enterprise governance, 20% NLP, 20% Bot, 20% Vision+Doc Intel, 20% Gen AI. All tagged with enterprise context."),
    ("2.2 Tiered Verifier\n+ Repair Loop",
     "Tier-1 flags 3 governance questions as potentially ambiguous due to policy version mismatch → repaired using latest Responsible AI docs. All 55 pass after repair.",
     "55/55 approved. 3 questions updated to reference 2025 Responsible AI Standard v2. Verifier confidence: 0.96."),
    ("2.3 Scoring\nEngine",
     "Sarah completes 55-question mock",
     "See score table below."),
    ("3.1 Gap Analyzer\n& Decision Policy",
     "Bot Service (68%) marginally below 70% threshold; all others pass",
     "Decision: NOT READY. Targeted 1-week remediation: Bot Service + CLU only. 20-question focused re-assessment."),
    ("Remediation Loop\n(Bot Service only)",
     "1-week focused plan: Bot Framework Composer, CLU channel integration, Adaptive Dialogs lab",
     "Bot Service score: 68% → 77%. Overall: 78% → 80%."),
    ("3.1 Gap Analyzer\n(2nd pass)",
     "All domains ≥ 70%, overall 80% ≥ 75%",
     "Decision: READY. Routes to Certification Planner."),
    ("3.2 Certification\n+ Exam Planner",
     "Generates enterprise-context exam booking; suggests case-study review of real-world Responsible AI governance; provides 90-day re-cert reminder",
     "Exam booked. Enterprise governance quick-reference delivered. 90-day renewal reminder set."),
]))
story.append(sp(8))

story.append(Paragraph("3C. Generated Study Plan", sH2))
story.append(study_plan_table([
    (1, "Azure AI Foundations +\nVision (API-first)",
     "Azure AI Services SDK deep-dive • Image Analysis REST • Custom Vision Python SDK",
     "Build image classifier with Custom Vision Python SDK"),
    (2, "NLP + Document Intelligence\n(SDK mapping to sklearn)",
     "Azure AI Language SDK (vs. NLTK/spaCy) • Document Intelligence Python SDK",
     "Extract + classify financial docs; map to existing sklearn pipeline"),
    (3, "Bot Service + CLU Deep-Dive\n(dynamic replan)",
     "Bot Framework Composer • CLU channel deployment • Adaptive Dialogs",
     "Deploy enterprise FAQ bot with CLU; connect to Teams"),
    (4, "Generative AI +\nAzure OpenAI (enterprise)",
     "Azure OpenAI API • RAG + Cognitive Search • Content Safety • BYOD governance",
     "Build RAG-powered enterprise search; apply content filters"),
    (5, "Responsible AI +\nRevision + Mock Exam",
     "Responsible AI Standard v2 • Fairness / Reliability / Privacy • Enterprise governance case studies",
     "Complete 55-question enterprise mock → Scoring Engine"),
]))
story.append(sp(8))

story.append(Paragraph("3D. Assessment Scores", sH2))
story.append(score_table([
    ("Plan & Manage Azure AI Solutions",         86),
    ("Implement Computer Vision Solutions",      88),
    ("Implement NLP Solutions",                  82),
    ("Implement Document Intelligence",          75),
    ("Implement Conversational AI Solutions",    68),
    ("Implement Generative AI Solutions",        77),
], overall=78))
story.append(sp(4))
story.append(Paragraph("↑ After first assessment. Bot Service (68%) marginally below 70% → 1-week targeted remediation triggered.", sCaption))
story.append(sp(6))

story.append(Paragraph("3E. Final Decision", sH2))
story.append(decision_box(
    "✓ READY TO SIT AI-102 (after 1-week remediation)",
    "After Bot Service remediation: Conversational AI 77% | Overall 80%. All domains ≥ 70%. "
    "Total time: 6 weeks / 48 hours. Enterprise governance reference card delivered.",
    color=C_GREEN_DARK, bg=C_GREEN_LIGHT
))
story.append(PageBreak())

# ════════════════════════════════════════════════════════════════════════════
# COMPARATIVE SUMMARY
# ════════════════════════════════════════════════════════════════════════════
story.append(Paragraph("Cross-Scenario Comparison", sH1))
story.append(hr(C_PURPLE_DARK))
story.append(sp(4))

summary_data = [
    [Paragraph("<b>Attribute</b>", sLabel),
     Paragraph("<b>Priya (Beginner)</b>", sLabel),
     Paragraph("<b>Marcus (Azure Pro)</b>", sLabel),
     Paragraph("<b>Sarah (Data Scientist)</b>", sLabel)],
    [Paragraph("Target weeks", sSmall), Paragraph("10 weeks", sSmall), Paragraph("3 weeks", sSmall), Paragraph("5 weeks", sSmall)],
    [Paragraph("Hours/week", sSmall), Paragraph("10 h/wk", sSmall), Paragraph("15 h/wk", sSmall), Paragraph("8 h/wk", sSmall)],
    [Paragraph("Modules skipped", sSmall), Paragraph("None (all 18)", sSmall), Paragraph("4 of 18 (known)", sSmall), Paragraph("7 of 18 (ML basics)", sSmall)],
    [Paragraph("Assessment questions", sSmall), Paragraph("60 Q + 30 Q remediation", sSmall), Paragraph("30 Q diagnostic + 50 Q final", sSmall), Paragraph("20 Q early diag + 55 Q final + 20 Q remediation", sSmall)],
    [Paragraph("Verifier repair passes", sSmall), Paragraph("1 pass (4 Q fixed)", sSmall), Paragraph("1 pass (2 Q fixed)", sSmall), Paragraph("1 pass (3 Q fixed)", sSmall)],
    [Paragraph("Remediation cycles", sSmall), Paragraph("1 cycle (NLP + Gen AI)", sSmall), Paragraph("None — first attempt pass", sSmall), Paragraph("1 cycle (Bot Service only)", sSmall)],
    [Paragraph("Final overall score", sSmall), Paragraph("79% (after remediation)", sSmall), Paragraph("79% (first attempt)", sSmall), Paragraph("80% (after remediation)", sSmall)],
    [Paragraph("Dynamic replan triggered?", sSmall), Paragraph("No", sSmall), Paragraph("Yes (Week 2, Gen AI extra)", sSmall), Paragraph("Yes (Week 3, Bot deep-dive)", sSmall)],
    [Paragraph("Exam readiness", sSmall),
     Paragraph("<b>✓ Ready — Wk 10</b>", S("rd1", fontSize=9, textColor=C_GREEN_DARK, fontName="Helvetica-Bold")),
     Paragraph("<b>✓ Ready — Wk 3</b>", S("rd2", fontSize=9, textColor=C_GREEN_DARK, fontName="Helvetica-Bold")),
     Paragraph("<b>✓ Ready — Wk 6</b>", S("rd3", fontSize=9, textColor=C_GREEN_DARK, fontName="Helvetica-Bold"))],
]
sum_t = Table(summary_data, colWidths=[50*mm, 46*mm, 46*mm, 46*mm], repeatRows=1)
sum_t.setStyle(TableStyle([
    ("BACKGROUND",    (0,0), (-1,0), C_PURPLE_DARK),
    ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_GREY_LIGHT, C_WHITE]),
    ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#CCCCCC")),
    ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ("TOPPADDING",    (0,0), (-1,-1), 5),
    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ("LEFTPADDING",   (0,0), (-1,-1), 7),
    ("BACKGROUND",    (0,-1),(-1,-1), C_GREEN_LIGHT),
]))
story.append(sum_t)
story.append(sp(10))

story.append(Paragraph("Key Design Observations", sH2))
story.append(Paragraph(
    "<b>1. Personalisation at intake:</b>  The Learner Profiling agent's ability to skip known content was the single biggest factor in Marcus completing prep in 3 weeks vs. Priya's 10 weeks. Skill-graph inference from declared certifications saved ~28 hours of redundant study.",
    sBody))
story.append(Paragraph(
    "<b>2. Dynamic replan (adaptive loop):</b>  Both Marcus and Sarah benefited from mid-course diagnostic assessments that triggered plan revisions before the final mock. This prevented exam-day surprises and corrected trajectory 2–3 weeks early.",
    sBody))
story.append(Paragraph(
    "<b>3. Tiered Verifier value:</b>  In all three scenarios the Verifier caught between 2–4 content errors before they reached the student. Sarah's scenario highlighted a real-world risk: policy-version drift in Responsible AI questions — the Verifier's doc-anchoring check caught this automatically.",
    sBody))
story.append(Paragraph(
    "<b>4. Surgical remediation:</b>  The Gap Analyzer recommended domain-specific remediation (not a full retake) in both Priya's and Sarah's cases. This reduced extra prep time to 1–2 weeks instead of a full second cycle, preserving motivation.",
    sBody))
story.append(Paragraph(
    "<b>5. Threshold gate enforcement:</b>  The 70%/75% policy was the system's most opinionated component. It correctly held Priya back despite an improving trend, ensuring she sat the exam only when domain-level confidence was verified.",
    sBody))

story.append(sp(8))
story.append(hr(C_GOLD_DARK))
story.append(sp(4))
story.append(Paragraph(
    f"Document generated by the Certification Prep Multi-Agent System  •  AI-102 Case Study  •  {datetime.date.today().strftime('%B %d, %Y')}",
    sFooter))

# ─── Build ───────────────────────────────────────────────────────────────────
doc.build(story, onFirstPage=build_header_footer, onLaterPages=build_header_footer)
print(f"PDF written → {output_path}")
