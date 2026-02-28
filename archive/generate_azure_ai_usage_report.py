"""
Azure AI Services Usage Report — CertPrep Multi-Agent System
Generates docs/azure_ai_services_usage.pdf
"""
import datetime
import pathlib

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle, HRFlowable,
)
from reportlab.platypus.flowables import KeepTogether

# ── colours ───────────────────────────────────────────────────────────────────
AZURE_BLUE   = colors.HexColor("#0078D4")
DARK_NAVY    = colors.HexColor("#1e3a5f")
LIGHT_BLUE   = colors.HexColor("#EFF6FF")
GREEN        = colors.HexColor("#16A34A")
RED          = colors.HexColor("#DC2626")
AMBER        = colors.HexColor("#D97706")
GREY_BG      = colors.HexColor("#F8FAFC")
BORDER_GREY  = colors.HexColor("#CBD5E1")
WHITE        = colors.white
TEXT_DARK    = colors.HexColor("#111827")
TEXT_MED     = colors.HexColor("#374151")
TEXT_MUTED   = colors.HexColor("#6B7280")
MINT         = colors.HexColor("#DCFCE7")
MINT_D       = colors.HexColor("#166534")
RED_LIGHT    = colors.HexColor("#FEE2E2")
AMBER_LIGHT  = colors.HexColor("#FEF3C7")

W, H = A4

# ── styles ────────────────────────────────────────────────────────────────────
base = getSampleStyleSheet()

def _style(name, **kw):
    return ParagraphStyle(name, **kw)

S = {
    "cover_title": _style("ct", fontSize=28, textColor=WHITE, fontName="Helvetica-Bold",
                           leading=34, alignment=TA_LEFT),
    "cover_sub":   _style("cs", fontSize=13, textColor=colors.HexColor("#BFDBFE"),
                           fontName="Helvetica", leading=18, alignment=TA_LEFT),
    "cover_meta":  _style("cm", fontSize=9,  textColor=colors.HexColor("#BFDBFE"),
                           fontName="Helvetica", leading=13, alignment=TA_LEFT),
    "h1":          _style("h1", fontSize=16, textColor=DARK_NAVY, fontName="Helvetica-Bold",
                           leading=20, spaceAfter=6, spaceBefore=14),
    "h2":          _style("h2", fontSize=12, textColor=AZURE_BLUE, fontName="Helvetica-Bold",
                           leading=16, spaceAfter=4, spaceBefore=10),
    "h3":          _style("h3", fontSize=10, textColor=DARK_NAVY, fontName="Helvetica-Bold",
                           leading=14, spaceAfter=3, spaceBefore=7),
    "body":        _style("bd", fontSize=9,  textColor=TEXT_MED,  fontName="Helvetica",
                           leading=14, spaceAfter=3, alignment=TA_JUSTIFY),
    "body_l":      _style("bl", fontSize=9,  textColor=TEXT_MED,  fontName="Helvetica",
                           leading=14, spaceAfter=2, alignment=TA_LEFT),
    "bullet":      _style("bu", fontSize=9,  textColor=TEXT_MED,  fontName="Helvetica",
                           leading=13, leftIndent=12, bulletIndent=0, spaceAfter=2),
    "code":        _style("co", fontSize=8,  textColor=colors.HexColor("#1E40AF"),
                           fontName="Courier", leading=12,
                           backColor=colors.HexColor("#EFF6FF"),
                           borderPadding=(3, 5, 3, 5)),
    "tag_use":     _style("tu", fontSize=8,  textColor=MINT_D,  fontName="Helvetica-Bold",
                           leading=11, alignment=TA_CENTER),
    "tag_warn":    _style("tw", fontSize=8,  textColor=RED,     fontName="Helvetica-Bold",
                           leading=11, alignment=TA_CENTER),
    "tag_amber":   _style("ta", fontSize=8,  textColor=colors.HexColor("#92400E"),
                           fontName="Helvetica-Bold", leading=11, alignment=TA_CENTER),
    "caption":     _style("ca", fontSize=8,  textColor=TEXT_MUTED, fontName="Helvetica-Oblique",
                           leading=11, alignment=TA_CENTER),
}

# ── helpers ───────────────────────────────────────────────────────────────────
def p(text, style="body"):     return Paragraph(text, S[style])
def h1(text):                  return p(text, "h1")
def h2(text):                  return p(text, "h2")
def h3(text):                  return p(text, "h3")
def sp(h=0.2):                 return Spacer(1, h * cm)
def hr():                      return HRFlowable(width="100%", thickness=0.5,
                                                  color=BORDER_GREY, spaceAfter=4)
def bullet(text):              return p(f"• &nbsp;{text}", "bullet")

def badge_cell(text, colour=MINT, text_colour=MINT_D):
    return Paragraph(
        f'<para alignment="center"><font color="#{text_colour.hexval()[2:]}" size="7">'
        f'<b>{text}</b></font></para>',
        S["body_l"],
    )

def tbl(data, col_widths, style_cmds):
    t = Table(data, colWidths=col_widths)
    base_style = [
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, GREY_BG]),
        ("GRID",          (0, 0), (-1, -1), 0.4, BORDER_GREY),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("BACKGROUND",    (0, 0), (-1, 0), DARK_NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
    ]
    t.setStyle(TableStyle(base_style + style_cmds))
    return t


# ── page template ─────────────────────────────────────────────────────────────
def _header_footer(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(TEXT_MUTED)
        canvas.drawString(2 * cm, H - 1.1 * cm,
                          "Azure AI Services Usage Report — CertPrep Multi-Agent System")
        canvas.drawRightString(W - 2 * cm, H - 1.1 * cm,
                               f"Page {doc.page}")
        canvas.setStrokeColor(BORDER_GREY)
        canvas.setLineWidth(0.4)
        canvas.line(2 * cm, H - 1.35 * cm, W - 2 * cm, H - 1.35 * cm)
        # footer
        canvas.drawString(2 * cm, 1.0 * cm,
                          f"Generated {datetime.date.today().strftime('%d %b %Y')} · Confidential — for internal review")
        canvas.line(2 * cm, 1.35 * cm, W - 2 * cm, 1.35 * cm)
    canvas.restoreState()


# ── cover page ────────────────────────────────────────────────────────────────
def cover_page():
    from reportlab.platypus import FrameBreak
    story = []

    # Blue header block
    from reportlab.platypus import Flowable
    class CoverBlock(Flowable):
        def draw(self):
            c = self.canv
            # Navy background
            c.setFillColor(DARK_NAVY)
            c.rect(0, 0, W, H, fill=1, stroke=0)
            # Azure accent stripe
            c.setFillColor(AZURE_BLUE)
            c.rect(0, H * 0.55, W, H * 0.45, fill=1, stroke=0)
            # Bottom white area
            c.setFillColor(WHITE)
            c.rect(0, 0, W, H * 0.38, fill=1, stroke=0)
        def wrap(self, aw, ah): return (0, 0)

    story.append(CoverBlock())

    # Title block
    story.append(Spacer(1, 7.5 * cm))
    title_tbl = Table(
        [[p("Azure AI Services\nUsage Report", "cover_title")],
         [p("CertPrep Multi-Agent System — Agents League Battle #2", "cover_sub")],
         [sp(0.4)],
         [p(f"Prepared: {datetime.date.today().strftime('%d %B %Y')}  ·  Author: Athiq Ahmed  ·  Version 1.0", "cover_meta")],
        ],
        colWidths=[W - 4 * cm],
    )
    title_tbl.setStyle(TableStyle([
        ("LEFTPADDING",  (0, 0), (-1, -1), 2 * cm),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
    ]))
    story.append(title_tbl)
    story.append(Spacer(1, 5.5 * cm))

    # Summary box (white area)
    box_data = [[
        p("<b>What this document covers</b><br/>"
          "A complete audit of every Azure AI / Microsoft service called, "
          "mocked, or planned in the CertPrep multi-agent Streamlit application. "
          "For each service the report maps: which agent/block uses it, "
          "why it is used, how it is called, and a personal recommendation "
          "on whether the current usage is appropriate — or should be replaced, "
          "deferred, or cached for a production deployment.", "body_l"),
    ]]
    box_tbl = Table(box_data, colWidths=[W - 5 * cm])
    box_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), LIGHT_BLUE),
        ("LEFTPADDING",   (0, 0), (-1, -1), 2 * cm),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 1 * cm),
        ("TOPPADDING",    (0, 0), (-1, -1), 0.5 * cm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5 * cm),
        ("ROUNDEDCORNERS",(0, 0), (-1, -1), [4, 4, 4, 4]),
    ]))
    story.append(box_tbl)
    story.append(PageBreak())
    return story


# ── section 1: executive summary ─────────────────────────────────────────────
def section_exec_summary():
    story = [h1("1. Executive Summary"), hr(), sp(0.15)]
    story.append(p(
        "The CertPrep system is a multi-agent AI application built for the Microsoft Agents League hackathon. "
        "It orchestrates eight specialised agents to create personalised Microsoft certification study plans. "
        "Despite being marketed as an 'AI-powered' system, the vast majority of its logic is intentionally "
        "<b>rule-based and deterministic</b> — calling Azure OpenAI only at one well-defined point in the pipeline. "
        "This is by design: determinism, testability, and zero-cost mock operation are primary goals for a demo system."
    ))
    sp(0.2)
    story.append(sp(0.2))

    # Service count table
    rows = [
        [p("<b>Service / Technology</b>", "body_l"),
         p("<b>Is it used?</b>", "body_l"),
         p("<b>Number of call points</b>", "body_l"),
         p("<b>Can run without it?</b>", "body_l")],
        [p("Azure OpenAI GPT-4o", "body_l"), p("Optional (live mode only)", "body_l"),
         p("1 — LearnerProfilingAgent", "body_l"), p("✅ Yes — full mock mode", "body_l")],
        [p("Microsoft Learn API", "body_l"), p("❌ Not called at runtime", "body_l"),
         p("0 — data is hardcoded", "body_l"), p("✅ Always — offline catalogue", "body_l")],
        [p("Azure AI Content Safety", "body_l"), p("❌ Not integrated yet", "body_l"),
         p("0 — heuristic only (G-16)", "body_l"), p("✅ Yes — keyword heuristic", "body_l")],
        [p("Azure Communication Services", "body_l"), p("❌ Not integrated", "body_l"),
         p("0 — SMTP only", "body_l"), p("✅ Yes — SMTP optional", "body_l")],
        [p("Azure AI Search / Cognitive Search", "body_l"), p("❌ Not integrated", "body_l"),
         p("0 — question bank hardcoded", "body_l"), p("✅ Yes — in-memory bank", "body_l")],
        [p("SQLite (local persistence)", "body_l"), p("✅ Always on", "body_l"),
         p("1 — database.py (all CRUD)", "body_l"), p("✅ Yes — optional skip mode", "body_l")],
        [p("SMTP (Python stdlib)", "body_l"), p("Optional (env vars gated)", "body_l"),
         p("1 — progress summary email", "body_l"), p("✅ Yes — silently skipped", "body_l")],
        [p("Plotly + Streamlit (UI)", "body_l"), p("✅ Always on", "body_l"),
         p("Many — charts / tabs / forms", "body_l"), p("N/A — core UI layer", "body_l")],
    ]
    story.append(tbl(rows,
        [5.5 * cm, 3.8 * cm, 4.5 * cm, 3.5 * cm],
        [("BACKGROUND", (3, 1), (3, -1), MINT),
         ("BACKGROUND", (1, 2), (1, 5), RED_LIGHT),
         ("BACKGROUND", (1, 1), (1, 1), AMBER_LIGHT),
         ("BACKGROUND", (1, 6), (1, 6), MINT),
         ("BACKGROUND", (1, 7), (1, 7), AMBER_LIGHT),
         ("BACKGROUND", (1, 8), (1, 8), MINT),
        ]))
    return story


# ── section 2: service deep-dives ─────────────────────────────────────────────
def section_azure_openai():
    story = [sp(0.3), h1("2. Azure OpenAI GPT-4o"), hr(), sp(0.1)]

    story.append(h2("2.1  What is it?"))
    story.append(p(
        "Azure OpenAI is a managed deployment of OpenAI's GPT-4o large language model hosted on Microsoft Azure. "
        "It provides chat completions with JSON-mode structured output, meaning the model can be "
        "instructed to return a strict JSON schema — used here to generate a typed <b>LearnerProfile</b> Pydantic object."
    ))
    story.append(sp(0.15))

    story.append(h2("2.2  Where is it used?"))
    rows = [
        [p("<b>Block</b>", "body_l"), p("<b>Agent/Module</b>", "body_l"), p("<b>Streamlit Tab</b>", "body_l"),
         p("<b>Call</b>", "body_l"), p("<b>Mode</b>", "body_l")],
        [p("B0 — Learner Profiling", "body_l"),
         p("LearnerProfilingAgent\n(b0_intake_agent.py)", "body_l"),
         p("Tab 1 — Intake & Setup", "body_l"),
         p("chat.completions.create()\nGPT-4o · json_object mode\ntemp=0.2 · max_tokens=2000", "code"),
         p("Optional\n(use_live flag)", "body_l")],
    ]
    story.append(tbl(rows,
        [4 * cm, 4 * cm, 3.5 * cm, 4.5 * cm, 2.3 * cm],
        [("BACKGROUND", (0, 1), (-1, 1), LIGHT_BLUE)]))
    story.append(sp(0.2))

    story.append(h2("2.3  How it is called"))
    story.append(p(
        "The <b>LearnerProfilingAgent</b> sends a structured system prompt (containing the full "
        "JSON schema for <i>LearnerProfile</i>) and a user message containing all intake form fields. "
        "GPT-4o returns a JSON object that is parsed and validated by Pydantic. "
        "If validation fails, a <i>ValidationError</i> is raised before any downstream agent runs. "
        "The call uses <b>temperature=0.2</b> to maximise determinism (low creative variation)."
    ))
    story.append(sp(0.1))
    story.append(p(
        "<b>System prompt pattern:</b> 'You are an AI certification advisor. Given the student "
        "background, return ONLY valid JSON matching this schema…' — no prose, no explanation, "
        "just structured data. This is the most appropriate use of an LLM: transforming "
        "unstructured free-text input into a validated, typed data contract."
    ))
    story.append(sp(0.2))

    story.append(h2("2.4  Mock mode — no Azure OpenAI needed"))
    story.append(p(
        "When <code>use_live = False</code> (the default), <b>b1_mock_profiler.py</b> is used instead. "
        "The mock profiler is a rule-based Python module (no API calls) that applies regex keyword "
        "matching, experience level inference, cert domain boost matrices, and concern topic mapping "
        "to produce an identical <i>LearnerProfile</i> output contract. "
        "For the five demo personas, mock output is indistinguishable from live GPT-4o output."
    ))
    story.append(sp(0.2))

    story.append(h2("2.5  Recommendation"))
    rec_data = [[
        p("✅  <b>KEEP — but gate it strictly</b>", "h3"),
    ], [
        p(
            "Using Azure OpenAI at this one point (intake profiling) is the correct architectural decision. "
            "The LLM is being used to solve a real NLP problem — interpreting unstructured background text, "
            "mapping it to structured domain confidence scores, and inferring learning style and experience level. "
            "A rule-based mock can approximate this for five known personas, but for arbitrary real-world "
            "students the LLM provides meaningfully better profiling.", "body_l"
        ),
    ], [
        p(
            "<b>What to avoid:</b> Do NOT call Azure OpenAI from StudyPlanAgent, AssessmentAgent, "
            "ProgressAgent, or CertRecommendationAgent. These agents do deterministic computation "
            "(Largest Remainder allocation, weighted formula, rule-based routing) where an LLM adds "
            "latency and cost with no accuracy benefit. An LLM 'recommending' which week to study "
            "a domain is worse than a deterministic algorithm that uses actual exam weightings.", "body_l"
        ),
    ], [
        p(
            "<b>Production improvement:</b> Add a response cache keyed by a hash of the intake inputs. "
            "If two students have near-identical backgrounds/certs/concerns, return the cached profile "
            "rather than paying for a second GPT-4o call. Use <code>functools.lru_cache</code> or Redis.", "body_l"
        ),
    ]]
    rec_tbl = Table(rec_data, colWidths=[W - 4 * cm])
    rec_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#DCFCE7")),
        ("BACKGROUND",    (0, 1), (-1, -1), colors.HexColor("#F0FDF4")),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW",     (0, 0), (-1, 0), 1, GREEN),
        ("GRID",          (0, 0), (-1, -1), 0.3, BORDER_GREY),
    ]))
    story.append(rec_tbl)
    return story


def section_ms_learn():
    story = [sp(0.3), h1("3. Microsoft Learn Module Catalogue"), hr(), sp(0.1)]

    story.append(h2("3.1  What is it?"))
    story.append(p(
        "Microsoft Learn (<i>learn.microsoft.com</i>) provides a public REST API that lists all "
        "available training modules by exam or topic. In principle the app could call "
        "<code>GET https://learn.microsoft.com/api/catalog/?locale=en-us&type=modules</code> "
        "at runtime to dynamically fetch the latest module list for each domain."
    ))
    story.append(sp(0.15))

    story.append(h2("3.2  Current usage — offline / hardcoded"))
    story.append(p(
        "The current implementation in <b>b1_1_learning_path_curator.py</b> does NOT call the MS Learn API. "
        "Instead, it uses a Python dictionary (<code>_LEARN_CATALOGUE</code>) with manually curated "
        "module metadata for five exam families (AI-102, AI-900, DP-100, AZ-204, AZ-305). "
        "This includes title, direct URL, duration in minutes, difficulty, type (module/path), "
        "and display priority (core / supplemental / optional)."
    ))
    story.append(sp(0.1))

    rows = [
        [p("<b>Exam</b>", "body_l"), p("<b>Domains covered</b>", "body_l"),
         p("<b>Module count</b>", "body_l"), p("<b>Data source</b>", "body_l")],
        [p("AI-102", "body_l"), p("6 domains", "body_l"),
         p("~36 modules", "body_l"), p("Hardcoded dict", "body_l")],
        [p("AI-900", "body_l"), p("5 domains", "body_l"),
         p("~20 modules", "body_l"), p("Hardcoded dict", "body_l")],
        [p("DP-100", "body_l"), p("6 domains", "body_l"),
         p("~24 modules", "body_l"), p("Hardcoded dict", "body_l")],
        [p("AZ-204", "body_l"), p("5 domains", "body_l"),
         p("~18 modules", "body_l"), p("Hardcoded dict", "body_l")],
        [p("AZ-305", "body_l"), p("4 domains", "body_l"),
         p("~16 modules", "body_l"), p("Hardcoded dict", "body_l")],
    ]
    story.append(tbl(rows,
        [3 * cm, 4 * cm, 3.5 * cm, 5 * cm],
        []))
    story.append(sp(0.2))

    story.append(h2("3.3  Recommendation"))
    rec_data = [[
        p("✅  <b>KEEP AS HARDCODED — correct for demo scale; plan API integration for production</b>", "h3"),
    ], [
        p(
            "For a hackathon demo covering five known exam families, live MS Learn API calls add latency, "
            "internet dependency, rate-limit risk, and API contract drift risk — for zero learner benefit. "
            "The curated catalogue is faster, fully offline, always consistent, and lets you control "
            "exactly which modules are shown (human editorial quality gate). Keep it.", "body_l"
        ),
    ], [
        p(
            "<b>For production deployment:</b> Schedule a nightly <i>Azure Function</i> (or GitHub Action) "
            "that calls the MS Learn Catalog API, diffs against the stored catalogue, and updates only "
            "changed/new modules. The Streamlit app always reads from the locally cached version — "
            "never hitting the API at request time. This gives you live data freshness without "
            "per-request API latency.", "body_l"
        ),
    ], [
        p(
            "<b>Do NOT call the MS Learn API on every page load or tab switch.</b> The catalogue "
            "changes at most weekly. Calling it per-request would add 500ms–2s per user, risk "
            "rate-limiting, and produce no better output than the curated offline data.", "body_l"
        ),
    ]]
    rec_tbl = Table(rec_data, colWidths=[W - 4 * cm])
    rec_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), AMBER_LIGHT),
        ("BACKGROUND",    (0, 1), (-1, -1), colors.HexColor("#FFFBEB")),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW",     (0, 0), (-1, 0), 1, AMBER),
        ("GRID",          (0, 0), (-1, -1), 0.3, BORDER_GREY),
    ]))
    story.append(rec_tbl)
    return story


def section_content_safety():
    story = [sp(0.3), h1("4. Azure AI Content Safety"), hr(), sp(0.1)]

    story.append(h2("4.1  What is it?"))
    story.append(p(
        "Azure AI Content Safety is a managed API that classifies text and images against "
        "four harm categories (Hate, Self-Harm, Sexual, Violence) with severity scoring, "
        "and provides a Prompt Shield feature specifically designed to detect prompt injection "
        "attacks against LLM-based systems."
    ))
    story.append(sp(0.15))

    story.append(h2("4.2  Current usage — heuristic only (G-16)"))
    story.append(p(
        "The current <b>GuardrailsPipeline</b> rule <b>G-16</b> implements a basic keyword scan "
        "over free-text intake fields (background, concern_topics, goal_text) looking for "
        "heuristic patterns (expletives, violence keywords). This is a pure Python check with "
        "no external API call. It is intentionally conservative — it rarely fires in practice "
        "since the user population is certification students."
    ))
    story.append(sp(0.15))

    story.append(h2("4.3  Recommendation"))
    rec_data = [[
        p("🟡  <b>UPGRADE — replace G-16 with Azure AI Content Safety API in production</b>", "h3"),
    ], [
        p(
            "The heuristic keyword scan (G-16) is sufficient for the hackathon demo. "
            "A real deployment accepting arbitrary student text from the public should use "
            "Azure AI Content Safety for G-16 to get supported, maintained, multi-language "
            "harm detection with severity levels.", "body_l"
        ),
    ], [
        p(
            "<b>Recommended call pattern:</b> One Content Safety API call per intake form submission "
            "(not per keypress, not per tab change). Call it asynchronously alongside the profiler "
            "call — not before it — so the 200–400ms latency is hidden in the parallel execution. "
            "Only BLOCK-level harms halt the pipeline; LOW severity returns a WARN.", "body_l"
        ),
    ], [
        p(
            "<b>Do NOT</b> call Content Safety on every agent transition or on the study plan output. "
            "The system generates only structured data (not freehand LLM prose) after the intake, "
            "so there is no untrusted text to scan downstream. Over-calling adds latency and cost "
            "with no safety benefit.", "body_l"
        ),
    ]]
    rec_tbl = Table(rec_data, colWidths=[W - 4 * cm])
    rec_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), AMBER_LIGHT),
        ("BACKGROUND",    (0, 1), (-1, -1), colors.HexColor("#FFFBEB")),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW",     (0, 0), (-1, 0), 1, AMBER),
        ("GRID",          (0, 0), (-1, -1), 0.3, BORDER_GREY),
    ]))
    story.append(rec_tbl)
    return story


def section_assessment_sqlite():
    story = [sp(0.3), h1("5. Assessment Question Bank & SQLite Persistence"), hr(), sp(0.1)]

    story.append(h2("5.1  Assessment Agent — Hardcoded Question Bank"))
    story.append(p(
        "The <b>AssessmentAgent</b> (b2_assessment_agent.py) maintains a 30-question bank per "
        "exam family, manually authored and stored in Python data structures. "
        "The quiz sampling algorithm (Largest Remainder Method) draws a weighted subset of "
        "questions proportional to real exam domain weights. "
        "<b>No external API is called at any point in the quiz lifecycle.</b>"
    ))
    story.append(sp(0.1))

    rows = [
        [p("<b>Exam</b>", "body_l"), p("<b>Questions in bank</b>", "body_l"),
         p("<b>Source</b>", "body_l"), p("<b>Serving method</b>", "body_l")],
        [p("AI-102", "body_l"), p("30 (5 per domain)", "body_l"),
         p("Manually authored", "body_l"), p("In-memory random.sample()", "body_l")],
        [p("DP-100", "body_l"), p("30 (5 per domain)", "body_l"),
         p("Manually authored", "body_l"), p("In-memory random.sample()", "body_l")],
        [p("AI-900 + others", "body_l"), p("Shared bank", "body_l"),
         p("Manually authored", "body_l"), p("In-memory random.sample()", "body_l")],
    ]
    story.append(tbl(rows, [3 * cm, 4 * cm, 4 * cm, 5.3 * cm], []))
    story.append(sp(0.15))

    story.append(h2("5.2  SQLite — Session Persistence"))
    story.append(p(
        "All student, profile, plan, learning path, trace, and progress data is persisted to "
        "<code>cert_prep_data.db</code> via Python's standard-library <b>sqlite3</b> module "
        "(wrapped in <b>database.py</b>). This enables session recovery on page refresh: "
        "a returning student re-enters name + PIN to restore their full profile and plan."
    ))
    story.append(sp(0.15))

    story.append(h2("5.3  Recommendations"))
    rows2 = [
        [p("<b>Component</b>", "body_l"), p("<b>Current</b>", "body_l"),
         p("<b>Demo verdict</b>", "body_l"), p("<b>Production upgrade</b>", "body_l")],
        [p("Question bank", "body_l"), p("30 hardcoded Qs per exam", "body_l"),
         p("✅ Keep — no API needed\nfor 5 known exams", "body_l"),
         p("Azure AI Search index — allow dynamic Q bank growth, semantic search for relevant questions", "body_l")],
        [p("SQLite", "body_l"), p("Local file, zero deps", "body_l"),
         p("✅ Keep — correct for demo", "body_l"),
         p("Azure Cosmos DB (NoSQL, serverless) for multi-user, multi-region, auto-scale", "body_l")],
    ]
    story.append(tbl(rows2,
        [3 * cm, 4 * cm, 4 * cm, 5 * cm],
        [("BACKGROUND", (2, 1), (2, -1), MINT)]))
    return story


def section_email_smtp():
    story = [sp(0.3), h1("6. Email / SMTP Notification"), hr(), sp(0.1)]

    story.append(h2("6.1  What is it?"))
    story.append(p(
        "The <b>ProgressAgent</b> (b1_2_progress_agent.py) includes an optional email dispatch path. "
        "After generating a weekly study summary, the function <code>attempt_send_email()</code> "
        "reads SMTP configuration from environment variables (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS) "
        "and sends an HTML email using Python's <code>smtplib</code> stdlib. "
        "If the SMTP env vars are absent, the function silently returns <code>False</code> — "
        "the pipeline continues without error."
    ))
    story.append(sp(0.15))

    story.append(h2("6.2  Current usage in Streamlit"))
    story.append(p(
        "In the Streamlit UI, the 'Send Weekly Summary' button in the Progress tab calls "
        "<code>generate_weekly_summary()</code> to produce an HTML report, then calls "
        "<code>attempt_send_email()</code> with the student's email address from session state. "
        "The email is sent only if SMTP credentials are set — default demo mode shows the report "
        "in the UI without sending."
    ))
    story.append(sp(0.15))

    story.append(h2("6.3  Recommendation"))
    rec_data = [[
        p("🟡  <b>ACCEPTABLE for demo — replace with Azure Communication Services for production</b>", "h3"),
    ], [
        p(
            "SMTP via Python stdlib works and has zero external dependency on Azure. "
            "For a demo that may never send a real email, this is fine. "
            "The silent-fail pattern (returns False, pipeline continues) is good defensive design.", "body_l"
        ),
    ], [
        p(
            "<b>Production upgrade:</b> Replace <code>smtplib</code> with Azure Communication Services "
            "Email SDK. Benefits: guaranteed delivery tracking, bounce/unsubscribe handling, "
            "template rendering, no SMTP port blocking on Azure-hosted VMs, and full audit log "
            "in Azure Monitor. The code change is isolated to <code>attempt_send_email()</code> only.", "body_l"
        ),
    ], [
        p(
            "<b>Do NOT</b> send an email on every tab navigation or progress form save. "
            "Email dispatch should be explicit user action (button click) only, "
            "as currently implemented.", "body_l"
        ),
    ]]
    rec_tbl = Table(rec_data, colWidths=[W - 4 * cm])
    rec_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), AMBER_LIGHT),
        ("BACKGROUND",    (0, 1), (-1, -1), colors.HexColor("#FFFBEB")),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW",     (0, 0), (-1, 0), 1, AMBER),
        ("GRID",          (0, 0), (-1, -1), 0.3, BORDER_GREY),
    ]))
    story.append(rec_tbl)
    return story


def section_no_service_agents():
    story = [sp(0.3), h1("7. Agents That Intentionally Use No External Service"), hr(), sp(0.1)]
    story.append(p(
        "The following agents are entirely rule-based or algorithmic. "
        "They make no network calls, require no API keys, and run at sub-millisecond speed. "
        "This is intentional — these decisions are deterministic and should remain so."
    ))
    story.append(sp(0.15))

    rows = [
        [p("<b>Agent</b>", "body_l"), p("<b>Module</b>", "body_l"),
         p("<b>Algorithm</b>", "body_l"), p("<b>Why no LLM</b>", "body_l")],
        [p("Study Plan\nGenerator", "body_l"),
         p("b1_1_study_plan_agent.py", "body_l"),
         p("Largest Remainder Method,\nrisk-sorted task scheduling,\nprereq gap detection", "body_l"),
         p("Domain weight allocation is deterministic math. An LLM 'allocating weeks' would be "
           "less accurate than using official exam weights.", "body_l")],
        [p("Progress\nTracker", "body_l"),
         p("b1_2_progress_agent.py", "body_l"),
         p("Weighted formula:\n0.55×conf + 0.25×hours\n+ 0.20×practice", "body_l"),
         p("The readiness formula is transparent & user-auditable. An LLM producing a readiness "
           "score would be a black box.", "body_l")],
        [p("Assessment\nBuilder & Scorer", "body_l"),
         p("b2_assessment_agent.py", "body_l"),
         p("Weighted random sampling\nfrom hardcoded Q bank,\nexact-match scoring", "body_l"),
         p("Quiz scoring is binary correct/incorrect. GPT-4o generating questions risks "
           "hallucinated answers and inconsistent difficulty.", "body_l")],
        [p("Cert\nRecommender", "body_l"),
         p("b3_cert_recommendation_agent.py", "body_l"),
         p("Rule-based next-cert path\nmatching from cert chain table", "body_l"),
         p("Certification paths are fixed Microsoft exam chains. Rules are more reliable than "
           "an LLM that might suggest non-existent certifications.", "body_l")],
        [p("Guardrails\nPipeline", "body_l"),
         p("guardrails.py", "body_l"),
         p("17 deterministic validation\nrules (BLOCK/WARN/INFO)", "body_l"),
         p("Safety rules must be auditable and testable. An LLM-based safety check is non-"
           "deterministic and cannot be reliably unit tested.", "body_l")],
    ]
    story.append(tbl(rows,
        [2.8 * cm, 4 * cm, 4.5 * cm, 5 * cm],
        []))
    story.append(sp(0.2))
    story.append(p(
        "<b>Key principle:</b> Use an LLM only where the task is genuinely language-understanding — "
        "interpreting ambiguous free text, inferring intent, or generating natural language output. "
        "Never use a LLM to replace arithmetic, sorting, lookup tables, or boolean logic.",
        "body_l"
    ))
    return story


def section_master_recommendations():
    story = [sp(0.3), h1("8. Master Recommendation Table"), hr(), sp(0.1)]
    story.append(p(
        "This table consolidates all recommendations across every service touchpoint in the system. "
        "Use this as a production readiness checklist."
    ))
    story.append(sp(0.2))

    rows = [
        [p("<b>Service / Pattern</b>", "body_l"),
         p("<b>Current</b>", "body_l"),
         p("<b>Verdict</b>", "body_l"),
         p("<b>Recommendation</b>", "body_l")],

        # GPT-4o for profiling
        [p("Azure OpenAI GPT-4o\n(LearnerProfilingAgent)", "body_l"),
         p("Optional — live mode only", "body_l"),
         p("✅ KEEP", "body_l"),
         p("Best use of LLM in the system. Adds structured profile from free-text. "
           "Add response caching for identical inputs. Use structured output + low temperature.", "body_l")],

        # GPT-4o everywhere else
        [p("Azure OpenAI GPT-4o\n(all other agents)", "body_l"),
         p("NOT used — correctly", "body_l"),
         p("✅ KEEP AS-IS", "body_l"),
         p("Do NOT add OpenAI calls to StudyPlan, Assessment, Progress, or CertRec agents. "
           "These are deterministic computations. LLM adds latency + cost + non-determinism.", "body_l")],

        # MS Learn API
        [p("MS Learn Catalog API\n(LearningPathCurator)", "body_l"),
         p("NOT called — hardcoded offline catalogue", "body_l"),
         p("✅ KEEP for demo\n🟡 Upgrade for prod", "body_l"),
         p("Demo: keep hardcoded. Production: schedule nightly sync (Azure Function / GitHub Action). "
           "Never call per-request.", "body_l")],

        # Content Safety
        [p("Azure AI Content Safety\n(Guardrail G-16)", "body_l"),
         p("Heuristic keyword scan — no API", "body_l"),
         p("🟡 UPGRADE for prod", "body_l"),
         p("Replace G-16 keyword heuristic with Azure AI Content Safety API in production. "
           "Call once per form submit, asynchronously. Never call per tab load.", "body_l")],

        # Assessment bank
        [p("Azure AI Search\n(Assessment Q bank)", "body_l"),
         p("NOT used — in-memory bank", "body_l"),
         p("✅ KEEP for demo\n🟡 Upgrade for prod", "body_l"),
         p("Demo: in-memory bank is fine for 5 exams × 30 questions. Production: "
           "Azure AI Search index for semantic question retrieval + larger bank.", "body_l")],

        # SQLite
        [p("SQLite\n(Session persistence)", "body_l"),
         p("Always on — local file", "body_l"),
         p("✅ KEEP for demo\n🔵 Migrate for prod", "body_l"),
         p("Demo: SQLite is ideal (zero deps, portable). "
           "Production: Azure Cosmos DB for multi-user, multi-instance, serverless scale.", "body_l")],

        # Email
        [p("SMTP\n(Progress email)", "body_l"),
         p("Optional — env-var gated, silent-fail", "body_l"),
         p("✅ KEEP for demo\n🟡 Upgrade for prod", "body_l"),
         p("Demo: SMTP stdlib is fine. Production: Azure Communication Services Email SDK "
           "for delivery tracking, bounces, unsubscribe compliance.", "body_l")],

        # Observability
        [p("Observability\n(AgentStep/RunTrace)", "body_l"),
         p("SQLite + Admin Dashboard", "body_l"),
         p("✅ KEEP for demo\n🔵 Upgrade for prod", "body_l"),
         p("Demo: custom trace structs + Admin Dashboard are excellent for hackathon. "
           "Production: Azure Application Insights + Log Analytics Workspace.", "body_l")],

        # Auth
        [p("Authentication\n(PIN-based login)", "body_l"),
         p("Name + 4-digit PIN, SHA-256 stored", "body_l"),
         p("✅ Fine for demo\n🔴 Must change for prod", "body_l"),
         p("Demo: PIN auth is fine. Production: Azure AD B2C / Entra External ID. "
           "Never ship PIN auth to real users.", "body_l")],

        # Secrets
        [p("Secrets management\n(.env file)", "body_l"),
         p(".env file / env vars", "body_l"),
         p("✅ Fine for demo\n🔴 Must change for prod", "body_l"),
         p("Demo: .env is standard. Production: Azure Key Vault + Managed Identity. "
           "No secrets in code or env vars on shared infrastructure.", "body_l")],
    ]

    story.append(tbl(rows,
        [4 * cm, 3.5 * cm, 2.8 * cm, 6 * cm],
        [("BACKGROUND", (2, 1), (2,  2), MINT),
         ("BACKGROUND", (2, 2), (2,  2), MINT),
         ("BACKGROUND", (2, 3), (2,  4), AMBER_LIGHT),
         ("BACKGROUND", (2, 5), (2,  5), AMBER_LIGHT),
         ("BACKGROUND", (2, 6), (2,  6), MINT),
         ("BACKGROUND", (2, 7), (2,  8), AMBER_LIGHT),
         ("BACKGROUND", (2, 9), (2,  9), AMBER_LIGHT),
         ("BACKGROUND", (2,10), (2, 10), RED_LIGHT),
         ("BACKGROUND", (2,11), (2, 11), RED_LIGHT),
        ]))
    return story


def section_decision_framework():
    story = [sp(0.3), h1("9. Decision Framework — When to Use Azure AI Services"), hr(), sp(0.1)]

    story.append(p(
        "Use the following criteria to evaluate whether any new Azure AI service call is justified:"
    ))
    story.append(sp(0.15))

    rows = [
        [p("<b>Question</b>", "body_l"), p("<b>If YES →</b>", "body_l"), p("<b>If NO →</b>", "body_l")],
        [p("Is the input genuinely unstructured free text that requires language understanding?", "body_l"),
         p("✅ Azure OpenAI may be appropriate", "body_l"),
         p("❌ Use a rule/algorithm instead", "body_l")],
        [p("Would two identical inputs always produce the same correct output?", "body_l"),
         p("❌ Use deterministic code — no LLM needed", "body_l"),
         p("✅ LLM or probabilistic model may help", "body_l")],
        [p("Can the data be safely cached between requests?", "body_l"),
         p("✅ Always cache — avoid redundant API calls", "body_l"),
         p("Consider if real-time freshness is truly required", "body_l")],
        [p("Does the data change more often than daily?", "body_l"),
         p("Evaluate real-time API need vs refresh schedule", "body_l"),
         p("✅ Batch-sync nightly — never per-request", "body_l")],
        [p("Will the user wait for this API call on a demo?", "body_l"),
         p("🔴 Minimise — mock, cache, or async", "body_l"),
         p("✅ Background call acceptable", "body_l")],
        [p("Is the output safety-critical (user-facing verdict, booking advice)?", "body_l"),
         p("✅ Use deterministic formula — explainable by design", "body_l"),
         p("LLM-generated verdict is acceptable for non-critical guidance", "body_l")],
    ]
    story.append(tbl(rows,
        [7 * cm, 4 * cm, 4.5 * cm],
        []))
    story.append(sp(0.2))

    story.append(h2("The Anti-Pattern to Avoid"))
    ap_data = [[
        p("🔴  <b>Do not use Azure OpenAI as a general-purpose function replacement</b>", "h3"),
    ], [
        p(
            "There is a common over-engineering trap where every data transformation, "
            "recommendation, or output in an app is routed through an LLM — 'because it's an AI app'. "
            "This produces: higher latency (2–5s per call), higher cost, non-deterministic outputs, "
            "untestable logic, and worse results than simple rules for structured computations. "
            "In this system, the study plan algorithm, readiness formula, quiz sampling, and "
            "cert routing are all more accurate, faster, and cheaper as deterministic code.", "body_l"
        ),
    ], [
        p(
            "<b>The right mental model:</b> The LLM is a natural-language-to-structured-data converter "
            "at the boundary between the messy human world and the clean typed world of the pipeline. "
            "Once data is typed and structured, keep all computation deterministic.", "body_l"
        ),
    ]]
    ap_tbl = Table(ap_data, colWidths=[W - 4 * cm])
    ap_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), RED_LIGHT),
        ("BACKGROUND",    (0, 1), (-1, -1), colors.HexColor("#FFF5F5")),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW",     (0, 0), (-1, 0), 1, RED),
        ("GRID",          (0, 0), (-1, -1), 0.3, BORDER_GREY),
    ]))
    story.append(ap_tbl)
    return story


def section_production_roadmap():
    story = [sp(0.3), h1("10. Production Services Roadmap"), hr(), sp(0.1)]
    story.append(p(
        "Ordered by impact — highest priority first. Each item is an independent upgrade "
        "requiring no changes to the orchestration pipeline or agent contracts."
    ))
    story.append(sp(0.15))

    rows = [
        [p("<b>Priority</b>", "body_l"),
         p("<b>Upgrade</b>", "body_l"),
         p("<b>Replaces</b>", "body_l"),
         p("<b>Effort</b>", "body_l"),
         p("<b>Impact</b>", "body_l")],
        [p("1 — HIGH", "body_l"),
         p("asyncio.gather() for StudyPlan + LearningPath agents", "body_l"),
         p("Sequential execution", "body_l"),
         p("~0.5 days", "body_l"),
         p("Saves ~3s per user (10→7s live mode latency)", "body_l")],
        [p("2 — HIGH", "body_l"),
         p("Azure AI Content Safety API (G-16)", "body_l"),
         p("Keyword heuristic scan", "body_l"),
         p("~1 day", "body_l"),
         p("Supported harm detection; multi-language; prompt shield", "body_l")],
        [p("3 — HIGH", "body_l"),
         p("OpenAI response cache (Redis or lru_cache)", "body_l"),
         p("Uncached GPT-4o calls", "body_l"),
         p("~1 day", "body_l"),
         p("Eliminates redundant API cost for returning students or near-identical profiles", "body_l")],
        [p("4 — MEDIUM", "body_l"),
         p("Nightly MS Learn catalogue sync (GitHub Action)", "body_l"),
         p("Static hardcoded dict", "body_l"),
         p("~2 days", "body_l"),
         p("Learning path stays current without per-request API calls", "body_l")],
        [p("5 — MEDIUM", "body_l"),
         p("Azure Cosmos DB NoSQL (serverless)", "body_l"),
         p("SQLite local file", "body_l"),
         p("~2 days", "body_l"),
         p("Multi-user, multi-region persistence; handles 1000+ concurrent users", "body_l")],
        [p("6 — MEDIUM", "body_l"),
         p("Azure Communication Services Email", "body_l"),
         p("SMTP stdlib", "body_l"),
         p("~1 day", "body_l"),
         p("Delivery tracking, bounce handling, compliance — isolated to attempt_send_email()", "body_l")],
        [p("7 — MEDIUM", "body_l"),
         p("Azure AD B2C authentication", "body_l"),
         p("PIN-based login", "body_l"),
         p("~3 days", "body_l"),
         p("Real identity, SSO, MFA — required before any public launch", "body_l")],
        [p("8 — LOW", "body_l"),
         p("Azure Application Insights", "body_l"),
         p("SQLite trace + Admin Dashboard", "body_l"),
         p("~1 day", "body_l"),
         p("Structured telemetry, per-agent latency dashboards, alerting", "body_l")],
        [p("9 — LOW", "body_l"),
         p("Azure AI Search — dynamic Q bank", "body_l"),
         p("Hardcoded 30-Q bank", "body_l"),
         p("~5 days", "body_l"),
         p("Enables semantic Q retrieval, larger bank, faster updates — only needed at scale", "body_l")],
        [p("10 — FUTURE", "body_l"),
         p("Magentic-One multi-expert profiler deliberation", "body_l"),
         p("Single-agent profiling", "body_l"),
         p("~1 week", "body_l"),
         p("Multiple domain-expert agents debate learner skill level; better for edge-case profiles", "body_l")],
    ]
    story.append(tbl(rows,
        [2.5 * cm, 5 * cm, 3.5 * cm, 2 * cm, 4.3 * cm],
        [("BACKGROUND", (0, 1), (0, 3), RED_LIGHT),
         ("BACKGROUND", (0, 4), (0, 7), AMBER_LIGHT),
         ("BACKGROUND", (0, 8), (0, 9), MINT),
         ("BACKGROUND", (0,10), (0,10), LIGHT_BLUE),
        ]))
    return story


# ── build PDF ─────────────────────────────────────────────────────────────────
def build():
    out = pathlib.Path(__file__).parent / "azure_ai_services_usage.pdf"

    doc = BaseDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="Azure AI Services Usage Report — CertPrep",
        author="Athiq Ahmed",
        subject="Azure AI Services catalogue and recommendations",
    )

    content_frame = Frame(
        2 * cm, 1.8 * cm,
        W - 4 * cm, H - 4 * cm,
        id="content",
    )
    cover_frame = Frame(0, 0, W, H, id="cover")

    doc.addPageTemplates([
        PageTemplate(id="Cover",   frames=[cover_frame]),
        PageTemplate(id="Content", frames=[content_frame],
                     onPage=_header_footer),
    ])

    story = []
    story += cover_page()
    story.append(PageBreak())  # switch to Content template
    story += section_exec_summary()
    story += section_azure_openai()
    story += section_ms_learn()
    story += section_content_safety()
    story += section_assessment_sqlite()
    story += section_email_smtp()
    story += section_no_service_agents()
    story += section_master_recommendations()
    story += section_decision_framework()
    story += section_production_roadmap()

    # final caption
    story.append(sp(0.5))
    story.append(hr())
    story.append(p(
        f"Generated {datetime.datetime.now().strftime('%d %B %Y %H:%M')}  ·  "
        "CertPrep Multi-Agent System — Agents League Battle #2  ·  "
        "Athiq Ahmed · Microsoft AI Foundry",
        "caption"
    ))

    doc.build(story)
    print(f"PDF written → {out}")
    return out


if __name__ == "__main__":
    build()
