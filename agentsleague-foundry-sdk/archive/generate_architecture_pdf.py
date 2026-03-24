#!/usr/bin/env python3
"""
generate_architecture_pdf.py  –  Faithful V4-style architecture diagram
========================================================================
Produces a high-quality, spacious single-page PDF that mirrors the
AI102_planning_v4_final.drawio layout with updated agent names.

Run:   python Notes/generate_architecture_pdf.py
Out:   docs/architecture_diagram.pdf
"""
from __future__ import annotations
import math
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.colors import HexColor, black, white
from reportlab.pdfbase.pdfmetrics import stringWidth

# ═══════════════════════════════════════════════════════════════════════════════
# PALETTE  (matches the drawio colour scheme)
# ═══════════════════════════════════════════════════════════════════════════════
PURPLE   = HexColor("#5C2D91")
PURP_L   = HexColor("#F5F0FF")
PURP_LL  = HexColor("#F3F0FF")
BLUE     = HexColor("#0F6CBD")
BLUE_L   = HexColor("#EEF6FF")
GREEN    = HexColor("#107C10")
GREEN_L  = HexColor("#E9F7EE")
GOLD     = HexColor("#8A6D00")
GOLD_L   = HexColor("#FFF4CE")
GOLD_LL  = HexColor("#FFFDE7")
GOLD_TR  = HexColor("#FFF9C4")
PINK     = HexColor("#B4009E")
PINK_L   = HexColor("#FDE7F3")
GREY_BG  = HexColor("#ECECEC")
GREY_TXT = HexColor("#666666")
BLK      = HexColor("#111827")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE & COORDINATE SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════
# drawio canvas = 1920 × ~900 content.  Map to A3 landscape with margins.
PAGE_W, PAGE_H = landscape(A3)          # 1190.55  ×  841.89
S  = (PAGE_W - 40) / 1920              # ≈ 0.599
MX = 20                                # left offset
MY = 24                                # top offset

def tx(dx):       return MX + dx * S
def ty(dy):       return PAGE_H - MY - dy * S
def tw(dw):       return dw * S
def th(dh):       return dh * S
def fs(f):        return max(6.0, round(f * S, 1))


# ═══════════════════════════════════════════════════════════════════════════════
# DRAWING PRIMITIVES
# ═══════════════════════════════════════════════════════════════════════════════

def drect(c, dx, dy, dw, dh, fill, stroke, r=6, lw=1.2):
    px, py, pw, ph = tx(dx), ty(dy + dh), tw(dw), th(dh)
    c.setStrokeColor(stroke); c.setLineWidth(lw)
    if fill:
        c.setFillColor(fill)
        c.roundRect(px, py, pw, ph, r, stroke=1, fill=1)
    else:
        c.roundRect(px, py, pw, ph, r, stroke=1, fill=0)


def dtxt(c, text, dx, dy, dw, dh,
         font="Helvetica-Bold", size=13, color=BLK, valign="middle"):
    sz  = fs(size)
    cx  = tx(dx + dw / 2)
    top = ty(dy); bot = ty(dy + dh); h = top - bot
    c.setFont(font, sz); c.setFillColor(color)
    lines = text.split("\n")
    lh    = sz * 1.35
    total = len(lines) * lh
    base_y = bot + h / 2 + total / 2 - lh + sz * 0.35 if valign == "middle" else top - sz - 2
    for i, ln in enumerate(lines):
        c.drawCentredString(cx, base_y - i * lh, ln)


def dtxt_left(c, text, dx, dy, font="Helvetica-Bold", size=13, color=BLK):
    c.setFont(font, fs(size)); c.setFillColor(color)
    c.drawString(tx(dx), ty(dy), text)


def dtxt_right(c, text, dx, dy, font="Helvetica", size=11, color=GREY_TXT):
    c.setFont(font, fs(size)); c.setFillColor(color)
    c.drawRightString(tx(dx), ty(dy), text)


def ddiamond(c, dx, dy, dw, dh, fill=GREEN_L, stroke=GREEN, lw=1.4):
    cx = tx(dx + dw / 2); cy = ty(dy + dh / 2)
    hw = tw(dw) / 2;      hh = th(dh) / 2
    c.setStrokeColor(stroke); c.setFillColor(fill); c.setLineWidth(lw)
    p = c.beginPath()
    p.moveTo(cx, cy + hh); p.lineTo(cx + hw, cy)
    p.lineTo(cx, cy - hh); p.lineTo(cx - hw, cy); p.close()
    c.drawPath(p, stroke=1, fill=1)


def _ah(c, x2, y2, angle, color, sz=5):
    c.setFillColor(color)
    p = c.beginPath()
    p.moveTo(x2, y2)
    p.lineTo(x2 - sz * math.cos(angle - 0.4), y2 - sz * math.sin(angle - 0.4))
    p.lineTo(x2 - sz * math.cos(angle + 0.4), y2 - sz * math.sin(angle + 0.4))
    p.close(); c.drawPath(p, stroke=0, fill=1)


def darrow(c, pts_d, color=BLK, dashed=False, lw=1.2):
    pts = [(tx(x), ty(y)) for x, y in pts_d]
    c.setStrokeColor(color); c.setLineWidth(lw)
    c.setDash([4, 3] if dashed else [])
    p = c.beginPath(); p.moveTo(*pts[0])
    for pt in pts[1:]: p.lineTo(*pt)
    c.drawPath(p, stroke=1, fill=0); c.setDash([])
    dx = pts[-1][0] - pts[-2][0]; dy = pts[-1][1] - pts[-2][1]
    _ah(c, pts[-1][0], pts[-1][1], math.atan2(dy, dx), color)


def dlabel(c, text, dx, dy, color=BLK, size=11, font="Helvetica-Bold"):
    c.setFont(font, fs(size)); c.setFillColor(color)
    c.drawCentredString(tx(dx), ty(dy), text)


def wrap_text(text, font_name, font_size, max_w):
    words = text.split(); lines = []; cur = ""
    for w in words:
        t = (cur + " " + w).strip()
        if stringWidth(t, font_name, font_size) <= max_w:
            cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines or [""]


# ═══════════════════════════════════════════════════════════════════════════════
# BUILD THE DIAGRAM
# ═══════════════════════════════════════════════════════════════════════════════

def build(out_path: Path):
    c = canvas.Canvas(str(out_path), pagesize=landscape(A3))
    c.setTitle("CertPrep AI – Architecture V4 Updated")

    # ── TITLE ────────────────────────────────────────────────────────────────
    dtxt_left(c, "CertPrep AI – Multi-Agent Certification Prep Architecture (V4 Updated)",
              40, 18, size=18, color=BLK)
    dtxt_right(c, "Microsoft Agents League 2026  ·  Battle #2 – Reasoning Agents",
               1880, 18, size=11, color=GREY_TXT)

    # ── SAFETY BAR ───────────────────────────────────────────────────────────
    drect(c, 40, 42, 1840, 44, PINK_L, PINK, lw=1.4)
    dtxt(c, "Policy & Safety Guardrails (cross-cutting):   G-01→G-05 Input bounds  ·  G-06→G-08 Profile integrity  ·"
         "  G-09→G-10 Plan bounds  ·  G-11→G-13 Progress validity  ·  G-14→G-15 Quiz integrity  ·  G-16→G-17 Content + URL trust",
         40, 42, 1840, 44, "Helvetica-Bold", 12, PINK)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1:  INTAKE & PREPARATION
    # ══════════════════════════════════════════════════════════════════════════
    drect(c, 40, 96, 1840, 310, GOLD_LL, GOLD, lw=1.6)
    dtxt_left(c, "1.  Intake & Preparation", 58, 114, size=13, color=GOLD)

    # Student Input box
    drect(c, 60, 148, 240, 96, BLUE_L, BLUE)
    dtxt(c, "Student Input\n(Streamlit Form)\nName · Exam · Background\nHours · Weeks · Certs\nConcerns",
         60, 148, 240, 96, "Helvetica-Bold", 12, BLUE)

    # Learner Intake & Profiling
    drect(c, 336, 148, 240, 96, PURP_L, PURPLE)
    dtxt(c, "Learner Intake &\nProfiling Agent\nMock (rule-based) /\nAzure OpenAI gpt-4o\n→ LearnerProfile",
         336, 148, 240, 96, "Helvetica-Bold", 12, PURPLE)

    # Orchestrator outer block (gold)
    drect(c, 614, 106, 740, 280, GOLD_L, GOLD, lw=1.4)
    # header strip
    drect(c, 664, 112, 640, 30, GREY_BG, GREY_BG, r=4, lw=0.3)
    dtxt(c, "Preparation Orchestrator (Central Brain)",
         664, 112, 640, 30, "Helvetica-Bold", 14, BLK)

    # 1.1 Learning Path Curator
    drect(c, 638, 166, 310, 96, PURP_L, PURPLE)
    dtxt(c, "1.1 Learning Path\nCurator Agent\n30+ MS Learn modules\nPriority-boost risk domains\nBudget cap (2× max)",
         638, 166, 310, 96, "Helvetica-Bold", 12, PURPLE)

    # 1.2 Study Plan + Progress + Engagement
    drect(c, 990, 166, 340, 96, PURP_L, PURPLE)
    dtxt(c, "1.2 StudyPlan + Progress\n+ Engagement Agents\nGantt (Largest Remainder)\nReadiness: 0.55d+0.25h+0.20p\nEmail nudges + SMTP report",
         990, 166, 340, 96, "Helvetica-Bold", 12, PURPLE)

    # Reasoning Trace Log strip
    drect(c, 680, 296, 540, 44, GOLD_TR, GOLD, r=4, lw=0.8)
    dtxt(c, "Reasoning Trace Log  +  GuardrailsPipeline  (17 rules across 5 categories – explainability)",
         680, 296, 540, 44, "Helvetica-Oblique", 11, GOLD)

    # Preparation Output Artifact
    drect(c, 1400, 170, 340, 96, BLUE_L, BLUE)
    dtxt(c, "Preparation Output\nArtifact\nLearningPath + StudyPlan\n+ Milestones + Readiness",
         1400, 170, 340, 96, "Helvetica-Bold", 12, BLUE)

    # Diamond: Ready for Assessment?
    ddiamond(c, 1430, 290, 170, 100, GREEN_L, GREEN, 1.5)
    dtxt(c, "Ready for\nAssessment?", 1430, 290, 170, 100, "Helvetica-Bold", 13, GREEN)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2:  ASSESSMENT + VERIFICATION
    # ══════════════════════════════════════════════════════════════════════════
    dtxt_left(c, "2.  Assessment + Verification", 830, 442, size=15, color=PURPLE)
    drect(c, 490, 462, 1230, 180, PURP_LL, PURPLE, lw=1.6)

    # 2.1 Assessment Builder
    drect(c, 510, 486, 280, 100, PURP_L, PURPLE)
    dtxt(c, "2.1 Assessment\nBuilder Agent\n30-Q bank · 5/domain\n3 difficulty levels\nDomain-weighted sampling",
         510, 486, 280, 100, "Helvetica-Bold", 12, PURPLE)

    # 2.2 Guardrail Verifier + Repair
    drect(c, 840, 486, 320, 100, PINK_L, PINK)
    dtxt(c, "2.2 Guardrail Verifier\n+ Repair Loop\nG-14 (≥5 Qs) · G-15 (no dups)\nG-16 content filter\nG-17 URL trust check",
         840, 486, 320, 100, "Helvetica-Bold", 12, PINK)

    # 2.3 Scoring Engine
    drect(c, 1210, 486, 290, 100, GREEN_L, GREEN)
    dtxt(c, "2.3 Scoring Engine\n(deterministic)\nPer-domain breakdown\nPass ≥ 60%\nGO threshold ≥ 70%",
         1210, 486, 290, 100, "Helvetica-Bold", 12, GREEN)

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3:  DECISION + ADAPTATION
    # ══════════════════════════════════════════════════════════════════════════
    dtxt_left(c, "3.  Decision + Adaptation", 70, 444, size=13, color=GREEN)
    drect(c, 40, 462, 430, 180, GREEN_L, GREEN, lw=1.6)

    # 3.1 Gap Analyzer & Decision
    drect(c, 240, 490, 210, 100, GREEN_L, GREEN)
    dtxt(c, "3.1 CertRecommendation\nAgent + Gap Analyzer\nGO ≥ 70% quiz score\nRemediate if < 70%\nNext-cert suggestions",
         240, 490, 210, 100, "Helvetica-Bold", 10, GREEN)

    # 3.2 Cert & Exam Planner
    drect(c, 58, 490, 162, 100, BLUE_L, BLUE)
    dtxt(c, "3.2 Cert & Exam\nPlanner\nAI-102: 180min, $165\nPearson VUE link\n7-item checklist",
         58, 490, 162, 100, "Helvetica-Bold", 10, BLUE)

    # ══════════════════════════════════════════════════════════════════════════
    # OBSERVABILITY BAR
    # ══════════════════════════════════════════════════════════════════════════
    drect(c, 40, 668, 1840, 44, BLUE_L, BLUE, lw=1.0)
    dtxt(c, "Evaluation Harness & Observability (passive – no control arrows)  ·  KPIs  ·  token usage  ·"
         "  guardrail catch-rate  ·  gap delta  ·  readiness accuracy  ·  quiz pass-rate  ·  latency",
         40, 668, 1840, 44, "Helvetica-Oblique", 11, BLUE)

    # ══════════════════════════════════════════════════════════════════════════
    # ARROWS  (exact drawio routing, updated y coords for taller boxes)
    # ══════════════════════════════════════════════════════════════════════════

    # A1:  Student Input right → Learner Intake left
    darrow(c, [(300, 196), (336, 196)])

    # A2:  Learner Intake right → Orch block left edge  (orthogonal jog)
    darrow(c, [(576, 196), (595, 196), (595, 246), (614, 246)])

    # A3:  1.1 right → 1.2 left (inside orchestrator)
    darrow(c, [(948, 214), (990, 214)], color=PURPLE)

    # A4:  Orchestrator right edge → Prep Output left edge  (orthogonal jog)
    darrow(c, [(1354, 246), (1377, 246), (1377, 218), (1400, 218)])

    # A5:  Prep Output bottom-center → jog to diamond top-center  (aligned)
    darrow(c, [(1570, 266), (1570, 278), (1515, 278), (1515, 290)])

    # A6:  Diamond bottom → YES → Assessment 2.1 top
    darrow(c, [(1515, 390), (1515, 440), (650, 440), (650, 486)], color=GREEN)
    dlabel(c, "Yes", 1080, 432, GREEN, 12)

    # A7:  Diamond right → NO – Replan → loop right → up → sec1 right
    darrow(c, [(1600, 340), (1870, 340), (1870, 250), (1880, 250)],
           color=GOLD, dashed=True)
    dlabel(c, "No – Replan", 1870, 285, GOLD, 10)

    # A8:  2.1 right → 2.2 left
    darrow(c, [(790, 536), (840, 536)])

    # A9:  2.2 bottom → repair loop → 2.1 bottom
    darrow(c, [(1000, 586), (1000, 624), (650, 624), (650, 586)],
           color=PINK, dashed=True)
    dlabel(c, "repair", 825, 618, PINK, 10)

    # A10: 2.2 right → 2.3 left  "validated only"
    darrow(c, [(1160, 536), (1210, 536)], color=GREEN)
    dlabel(c, "validated only", 1185, 526, GREEN, 9)

    # A11: 2.3 bottom-center → route BELOW both section boxes → 3.1 bottom-center
    darrow(c, [(1355, 586), (1355, 655), (345, 655), (345, 590)], color=GREEN)
    dlabel(c, "scores", 850, 649, GREEN, 10)

    # A12: 3.1 left → 3.2 right  "Ready"
    darrow(c, [(240, 540), (220, 540)], color=GREEN)
    dlabel(c, "Ready", 230, 526, GREEN, 13, "Helvetica-Bold")

    # A13: 3.1 top → Not Ready → up → sec1 bottom
    darrow(c, [(345, 490), (345, 430), (940, 430), (940, 406)],
           color=GOLD, dashed=True)
    dlabel(c, "Not Ready – Remediate", 642, 422, GOLD, 10)

    # ══════════════════════════════════════════════════════════════════════════
    # LEGEND  (4 rows below observability bar, matches drawio V4 style)
    # ══════════════════════════════════════════════════════════════════════════
    legends = [
        (PURPLE,
         "Learner Intake & Profiling Agent",
         "converts raw student form data into a structured LearnerProfile "
         "(6 domain confidence scores + experience level + risk domains + analogy_map).  "
         "Mock mode: keyword-based rule inference.  Live: Azure OpenAI gpt-4o with JSON-schema prompt."),
        (PURPLE,
         "1.1 Learning Path Curator + 1.2 StudyPlan + Progress + Engagement Agents",
         "– Curator maps AI-102 domains to 30+ MS Learn modules; priority-boosts risk domains; "
         "caps at 2× hours budget.  StudyPlan uses Largest Remainder Method for a week-level Gantt schedule.  "
         "Progress computes readiness = 0.55×domain + 0.25×hours + 0.20×practice.  "
         "Engagement agent generates a self-contained HTML email report sent via SMTP."),
        (PINK,
         "2.1 Assessment Builder + 2.2 Guardrail Verifier + 2.3 Scoring Engine",
         "– 30-question bank (5 per domain × 6 AI-102 domains, 3 difficulty levels).  "
         "Domain-weighted random sampling via Largest Remainder allocation.  "
         "Verifier: G-14 (≥5 Qs), G-15 (no duplicate IDs), G-16 (content filter), G-17 (URL trust).  "
         "Scoring: per-domain breakdown, pass ≥ 60%.  Assessment result feeds Block 3."),
        (GREEN,
         "3.1 CertRecommendation Agent & Gap Analyzer + 3.2 Cert & Exam Planner",
         "– GO threshold ≥ 70% quiz score.  If ready: exam logistics (AI-102 = 180 min, $165 USD, "
         "Pearson VUE URL), 7-item booking checklist, next-cert suggestions (DP-100 / AZ-305 / AI-900).  "
         "Not ready: targeted remediation plan listing weak domains → loops back to Block 1.1."),
    ]

    leg_y_start = 730
    for idx, (color, bold_part, rest_part) in enumerate(legends):
        y = leg_y_start + idx * 38
        bsz = fs(11)
        rsz = fs(10.5)

        lbl = f"■  {bold_part}"
        c.setFont("Helvetica-Bold", bsz)
        c.setFillColor(color)
        lbl_w = stringWidth(lbl, "Helvetica-Bold", bsz)
        c.drawString(tx(44), ty(y + 8), lbl)

        # Wrap the rest text onto 1-2 lines
        c.setFont("Helvetica", rsz)
        c.setFillColor(BLK)
        avail_first = tw(1840) - lbl_w - 12
        avail_rest  = tw(1840) - tw(14)
        rlines = wrap_text(rest_part, "Helvetica", rsz, avail_first)

        if rlines:
            c.drawString(tx(44) + lbl_w + 4, ty(y + 8), rlines[0])
        for ri in range(1, len(rlines)):
            ry = ty(y + 8) - ri * (rsz + 2)
            # re-wrap for full width if second+ line overflows first-line width
            c.drawString(tx(58), ry, rlines[ri])

    c.save()
    print(f"Architecture PDF saved → {out_path}")


# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    docs = Path(__file__).parent.parent / "docs"
    docs.mkdir(exist_ok=True)
    build(docs / "architecture_diagram.pdf")
