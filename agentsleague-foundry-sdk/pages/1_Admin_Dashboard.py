"""
pages/1_Admin_Dashboard.py – Admin-only agent interaction inspector.

Shows how each agent in the pipeline contributed to the final
LearnerProfile output. Protected by a session-scoped mock login gate.

Credentials  →  username: admin  |  password: agents2026
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import json
import html as _html

from cert_prep.database import get_all_students, get_student, delete_student
from cert_prep.models import LearnerProfile

# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Admin Dashboard – Cert Prep Agents",
    page_icon="🔐",
    layout="wide",
)

# ─── Theme constants (Microsoft Learn light theme) ────────────────────────────
BG        = "#F5F5F5"
CARD_BG   = "#FFFFFF"
BLUE      = "#0078D4"
PURPLE    = "#5C2D91"
GREEN     = "#107C10"
ORANGE    = "#CA5010"
RED       = "#D13438"
YELLOW    = "#8A6D00"
GREY      = "#616161"

AGENT_COLORS = {
    "safety":     RED,
    "intake":     BLUE,
    "profiling":  PURPLE,
    "scorer":     GREEN,
    "gate":       ORANGE,
    "analogy":    "#00B7C3",
    "engagement": "#0078D4",
}

# ─── Minimal page CSS (MS Learn light) ────────────────────────────────────────
st.markdown("""
<style>
  /* ── Main content area ── */
  [data-testid="stAppViewContainer"] { background: #F5F5F5; }
  [data-testid="stHeader"]           { background: #fff !important; border-bottom: 1px solid #E1DFDD; }
  [data-testid="stSidebarNav"]       { display: none; }
  [data-testid="stSidebarCollapseButton"],
  [data-testid="collapsedControl"]   { display: none !important; }
  h1, h2, h3, h4                     { color: #1B1B1B !important; font-family: 'Segoe UI', sans-serif; }
  .stMarkdown p, .stMarkdown li      { color: #323130; }
  .stExpander details                 { background: #FFFFFF; border-radius: 4px; border: 1px solid #E1DFDD !important; }
  .stExpander summary                 { color: #1B1B1B !important; }
  div[data-testid="stTable"]          { background: #FFFFFF; border-radius: 4px; border: 1px solid #E1DFDD; }
  .stButton > button {
    background: #0078D4 !important; border: none !important; color: #fff !important;
    border-radius: 4px !important; font-weight: 600 !important;
  }
  .stButton > button:hover { background: #106EBE !important; }
  .stCaption { color: #616161 !important; }

  /* ── Sidebar: dark blue gradient matching main app ── */
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0078D4 0%, #005A9E 100%) !important;
    border-right: none !important;
  }
  [data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    background: transparent !important;
    padding-top: 0.2rem;
  }
  [data-testid="stSidebar"] h1,
  [data-testid="stSidebar"] h2,
  [data-testid="stSidebar"] h3 { color: #fff !important; }
  [data-testid="stSidebar"] .stMarkdown p,
  [data-testid="stSidebar"] .stMarkdown li,
  [data-testid="stSidebar"] .stMarkdown span,
  [data-testid="stSidebar"] .stMarkdown b,
  [data-testid="stSidebar"] .stMarkdown strong { color: rgba(255,255,255,0.9) !important; }
  [data-testid="stSidebar"] .stCaption { color: rgba(255,255,255,0.6) !important; }
  [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.2) !important; }
  [data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.1) !important;
    border: none !important;
    color: rgba(255,255,255,0.9) !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
  }
  [data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.2) !important;
    color: #fff !important;
  }
  [data-testid="stSidebar"] a, [data-testid="stSidebar"] a:visited {
    color: rgba(255,255,255,0.85) !important;
  }
</style>
""", unsafe_allow_html=True)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _card(label: str, value: str, color: str = BLUE, wide: bool = False) -> str:
    w = "100%" if wide else "auto"
    return f"""
    <div style="background:{CARD_BG};border-left:4px solid {color};border-radius:4px;
                padding:10px 16px;display:inline-block;min-width:160px;width:{w};
                margin-bottom:8px;box-sizing:border-box;border:1px solid #E1DFDD;
                box-shadow:0 1px 2px rgba(0,0,0,0.04);">
      <div style="color:{GREY};font-size:0.7rem;font-weight:600;text-transform:uppercase;
                  letter-spacing:.06em;margin-bottom:3px;">{label}</div>
      <div style="color:#1B1B1B;font-size:1rem;font-weight:700;">{value}</div>
    </div>"""


def _section_header(title: str, icon: str = "") -> None:
    st.markdown(
        f"""<h3 style="color:#1B1B1B;border-bottom:1px solid #E1DFDD;
                        padding-bottom:6px;margin-top:28px;">{icon} {title}</h3>""",
        unsafe_allow_html=True,
    )


def _badge(text: str, color: str) -> str:
    return (
        f'<span style="background:{color}15;color:{color};border:1px solid {color}40;'
        f'border-radius:12px;padding:1px 10px;font-size:0.78rem;font-weight:600;">{text}</span>'
    )


def _hex_rgba(hex_color: str, alpha: float = 1.0) -> str:
    """Convert a #RRGGBB hex color to rgba() string Plotly can use."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ─── Login gate ───────────────────────────────────────────────────────────────

MOCK_USER = "admin"
MOCK_PASS = "agents2026"

# Auto-login if already authenticated as admin from the main sign-in page
if st.session_state.get("user_type") == "admin":
    st.session_state["admin_logged_in"] = True

if "admin_logged_in" not in st.session_state:
    st.session_state["admin_logged_in"] = False


def _show_login() -> None:
    st.markdown("""
    <div style="max-width:400px;margin:80px auto 0;">
      <div style="text-align:center;margin-bottom:32px;">
        <span style="font-size:3rem;">🔐</span>
        <h2 style="color:#1B1B1B;margin-top:8px;">Admin Access</h2>
        <p style="color:#616161;font-size:0.9rem;">
          This dashboard is restricted to administrators.<br/>
          Enter your credentials to continue.
        </p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        with st.form("admin_login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="admin")
            password = st.text_input("Password", type="password", placeholder="••••••••••")
            submitted = st.form_submit_button("🔓  Sign in", use_container_width=True)

        if submitted:
            if username == MOCK_USER and password == MOCK_PASS:
                st.session_state["admin_logged_in"] = True
                st.rerun()
            else:
                st.error("Invalid credentials. Please try again.")

        st.markdown(
            "<p style='text-align:center;color:#a0a0a0;font-size:0.78rem;"
            "margin-top:16px;'>Hint: username&nbsp;=&nbsp;<code>admin</code> &nbsp;|&nbsp; "
            "password&nbsp;=&nbsp;<code>agents2026</code></p>",
            unsafe_allow_html=True,
        )


if not st.session_state["admin_logged_in"]:
    _show_login()
    st.stop()


# ─── Authenticated: sidebar logout ────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔐 Admin Panel")
    st.markdown(f"Signed in as **{MOCK_USER}**")
    if st.button("Sign Out", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.switch_page("streamlit_app.py")
    st.markdown("---")
    st.markdown(
        "<a href='/' target='_self' style='color:#0078D4;font-weight:600;"
        "text-decoration:none;'>🏠 ← Back to Main App</a>",
        unsafe_allow_html=True,
    )
    st.caption("Only admins can see this page.\nStudents see the main Profiler UI.")


# ─── Page header ──────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
  <span style="font-size:2rem;">🤖</span>
  <div>
    <h1 style="color:#1B1B1B;margin:0;font-size:1.9rem;">Agent Interaction Dashboard</h1>
    <p style="color:#616161;margin:0;font-size:0.9rem;">
      Real-time audit of how each AI agent contributed to the learner profile output.
    </p>
  </div>
</div>
""", unsafe_allow_html=True)
st.markdown("---")


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 0 – All Students Overview (from SQLite)
# ═════════════════════════════════════════════════════════════════════════════
_section_header("All Students", "👥")
st.caption("All registered students and their current progress — data persisted in SQLite.")

import pandas as pd

_all_students = get_all_students()

# ── Delete empty-profile students (admin housekeeping) ───────────────────────
_empty_names = [s["name"] for s in _all_students if not s.get("profile_json")]
if _empty_names:
    st.warning(
        f"⚠️ {len(_empty_names)} student(s) with no profile data: **{', '.join(_empty_names)}**",
        icon=None,
    )
    if st.button(f"🗑️ Remove {len(_empty_names)} empty record(s)", key="del_empty"):
        for _en in _empty_names:
            delete_student(_en)
        st.success(f"Deleted: {', '.join(_empty_names)}")
        st.rerun()
    _all_students = [s for s in _all_students if s.get("profile_json")]

if _all_students:
    _student_rows = []
    for _s in _all_students:
        _has_profile   = bool(_s.get("profile_json"))
        _has_plan      = bool(_s.get("plan_json"))
        _has_progress  = bool(_s.get("progress_assessment_json"))
        _has_quiz      = bool(_s.get("assessment_result_json"))

        # Parse profile for avg confidence
        _avg_conf = "—"
        _risk_cnt = "—"
        _level    = "—"
        if _has_profile:
            try:
                _prof = LearnerProfile.model_validate_json(_s["profile_json"])
                _avg_conf = f"{sum(dp.confidence_score for dp in _prof.domain_profiles) / len(_prof.domain_profiles):.0%}"
                _risk_cnt = len(_prof.risk_domains)
                _level = _prof.experience_level.value.replace("_", " ").title()
            except Exception:
                pass

        # Parse progress for readiness
        _readiness = "—"
        _go_nogo   = "—"
        if _has_progress:
            try:
                _pr = json.loads(_s["progress_assessment_json"])
                _readiness = f"{_pr.get('readiness_pct', 0):.0f}%"
                _go_nogo   = _pr.get("exam_go_nogo", "—")
            except Exception:
                pass

        # Parse quiz score
        _quiz_score = "—"
        if _has_quiz:
            try:
                _qr = json.loads(_s["assessment_result_json"])
                _quiz_score = f"{_qr.get('score_pct', 0):.0f}%"
            except Exception:
                pass

        _student_rows.append({
            "Name":       _s["name"],
            "Exam":       _s.get("exam_target", "—") or "—",
            "Level":      _level,
            "Avg Conf":   _avg_conf,
            "Risk":       _risk_cnt,
            "Plan":       "✅" if _has_plan else "—",
            "Progress":   _readiness,
            "Quiz":       _quiz_score,
            "GO/NO-GO":   _go_nogo,
            "Updated":    (_s.get("updated_at", "—") or "—")[:16],
        })

    _students_df = pd.DataFrame(_student_rows)

    # Summary KPIs
    _kc1, _kc2, _kc3, _kc4 = st.columns(4)
    with _kc1:
        st.markdown(_card("Total Students", str(len(_student_rows)), BLUE, wide=True), unsafe_allow_html=True)
    with _kc2:
        _with_profile = sum(1 for r in _student_rows if r["Level"] != "—")
        st.markdown(_card("Profiles Generated", str(_with_profile), PURPLE, wide=True), unsafe_allow_html=True)
    with _kc3:
        _with_progress = sum(1 for r in _student_rows if r["Progress"] != "—")
        st.markdown(_card("Progress Check-ins", str(_with_progress), GREEN, wide=True), unsafe_allow_html=True)
    with _kc4:
        _with_quiz = sum(1 for r in _student_rows if r["Quiz"] != "—")
        st.markdown(_card("Quizzes Completed", str(_with_quiz), ORANGE, wide=True), unsafe_allow_html=True)

    st.dataframe(
        _students_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Name":     st.column_config.TextColumn("Student",   width="medium"),
            "Exam":     st.column_config.TextColumn("Exam",      width="small"),
            "Level":    st.column_config.TextColumn("Level",     width="small"),
            "Avg Conf": st.column_config.TextColumn("Avg Conf",  width="small"),
            "Risk":     st.column_config.TextColumn("Risk",      width="small"),
            "Plan":     st.column_config.TextColumn("Plan",      width="small"),
            "Progress": st.column_config.TextColumn("Readiness", width="small"),
            "Quiz":     st.column_config.TextColumn("Quiz",      width="small"),
            "GO/NO-GO": st.column_config.TextColumn("GO/NO-GO",  width="small"),
            "Updated":  st.column_config.TextColumn("Updated",   width="medium"),
        },
    )

    # ── Auto-generated Insights ──────────────────────────────────────────────
    _section_header("Key Insights", "💡")
    st.caption("Auto-generated observations from student data — so you don’t have to dig through charts.")

    _insights: list[tuple[str, str, str]] = []  # (icon, text, color)

    # Insight: students needing attention (no plan or no progress)
    _no_plan = [r["Name"] for r in _student_rows if r["Plan"] == "—"  and r["Level"] != "—"]
    if _no_plan:
        _insights.append(("⚠️", f"**{len(_no_plan)} student(s)** profiled but no study plan yet: {', '.join(_no_plan[:3])}{'...' if len(_no_plan) > 3 else ''}", ORANGE))

    _no_progress = [r["Name"] for r in _student_rows if r["Progress"] == "—" and r["Plan"] == "✅"]
    if _no_progress:
        _insights.append(("📌", f"**{len(_no_progress)} student(s)** have a plan but haven’t checked in: {', '.join(_no_progress[:3])}", BLUE))

    # Insight: risk domains
    _high_risk = [r for r in _student_rows if r["Risk"] != "—" and isinstance(r["Risk"], int) and r["Risk"] >= 3]
    if _high_risk:
        _names = ', '.join(r["Name"] for r in _high_risk[:3])
        _insights.append(("🚨", f"**{len(_high_risk)} student(s)** have 3+ risk domains and likely need intervention: {_names}", RED))

    # Insight: average confidence
    _conf_vals = []
    for r in _student_rows:
        if r["Avg Conf"] != "—":
            try:
                _conf_vals.append(float(r["Avg Conf"].replace("%", "")) / 100)
            except Exception:
                pass
    if _conf_vals:
        _mean_conf = sum(_conf_vals) / len(_conf_vals)
        _conf_clr = GREEN if _mean_conf >= 0.65 else (ORANGE if _mean_conf >= 0.4 else RED)
        _conf_word = "strong" if _mean_conf >= 0.65 else ("moderate" if _mean_conf >= 0.4 else "low")
        _insights.append(("🎯", f"Cohort average confidence is **{_mean_conf:.0%}** ({_conf_word}). "
                          + ("Most students are on track." if _mean_conf >= 0.55 else "Consider group review sessions for weak domains."), _conf_clr))

    # Insight: exam popularity
    _exam_counts: dict[str, int] = {}
    for r in _student_rows:
        if r["Exam"] != "—":
            _exam_counts[r["Exam"]] = _exam_counts.get(r["Exam"], 0) + 1
    if _exam_counts:
        _top_exam = max(_exam_counts, key=_exam_counts.get)
        _insights.append(("📚", f"Most popular exam: **{_top_exam}** ({_exam_counts[_top_exam]} student{'s' if _exam_counts[_top_exam]>1 else ''})", PURPLE))

    # Insight: GO / NO-GO summary
    _go_count  = sum(1 for r in _student_rows if "GO" in str(r["GO/NO-GO"]).upper() and "NO" not in str(r["GO/NO-GO"]).upper())
    _nogo_count = sum(1 for r in _student_rows if "NO-GO" in str(r["GO/NO-GO"]).upper() or "NO_GO" in str(r["GO/NO-GO"]).upper())
    if _go_count or _nogo_count:
        _insights.append(("✅" if _go_count > _nogo_count else "❌",
                          f"Exam readiness: **{_go_count} GO** vs **{_nogo_count} NO-GO** across assessed students.",
                          GREEN if _go_count > _nogo_count else RED))

    # Insight: quiz performance
    _quiz_vals = []
    for r in _student_rows:
        if r["Quiz"] != "—":
            try:
                _quiz_vals.append(float(r["Quiz"].replace("%", "")))
            except Exception:
                pass
    if _quiz_vals:
        _avg_quiz = sum(_quiz_vals) / len(_quiz_vals)
        _insights.append(("🧪", f"Average quiz score: **{_avg_quiz:.0f}%** across {len(_quiz_vals)} student{'s' if len(_quiz_vals)>1 else ''}. "
                          + ("Above 70% pass threshold — good cohort performance." if _avg_quiz >= 70 else "Below 70% pass threshold — more practice needed."),
                          GREEN if _avg_quiz >= 70 else ORANGE))

    if not _insights:
        _insights.append(("ℹ️", "Not enough data to generate insights yet. Students need to complete profiling, study plans, and quizzes.", GREY))

    # Render insight cards
    for _ic, _txt, _clr in _insights:
        st.markdown(
            f'<div style="background:#fff;border-left:4px solid {_clr};border:1px solid #E1DFDD;'
            f'border-radius:4px;padding:10px 16px;margin-bottom:8px;font-size:0.88rem;'
            f'color:#323130;line-height:1.5;box-shadow:0 1px 2px rgba(0,0,0,0.03);">' 
            f'{_ic} {_txt}</div>',
            unsafe_allow_html=True,
        )

    # Expandable per-student detail
    st.markdown("#### 🔍 Student Detail")
    _selected_student = st.selectbox(
        "Select a student to inspect",
        options=[s["name"] for s in _all_students if s.get("profile_json")],
        key="admin_student_select",
    )
    if _selected_student:
        _sel = get_student(_selected_student)
        if _sel and _sel.get("profile_json"):
            _sel_prof = LearnerProfile.model_validate_json(_sel["profile_json"])
            _d_c1, _d_c2 = st.columns(2)
            with _d_c1:
                st.markdown(f"**Student:** {_sel_prof.student_name}")
                st.markdown(f"**Exam:** {_sel_prof.exam_target}")
                st.markdown(f"**Experience:** {_sel_prof.experience_level.value.replace('_',' ').title()}")
                st.markdown(f"**Study Budget:** {_sel_prof.total_budget_hours:.0f} h "
                            f"({_sel_prof.hours_per_week}h/wk × {_sel_prof.weeks_available} wks)")
            with _d_c2:
                st.markdown("**Domain Confidence:**")
                for dp in _sel_prof.domain_profiles:
                    _pct = int(dp.confidence_score * 100)
                    _clr = GREEN if _pct >= 65 else (ORANGE if _pct >= 40 else RED)
                    _short = dp.domain_name.replace("Implement ","").replace(" Solutions","")
                    st.markdown(
                        f'<div style="margin-bottom:4px;font-size:0.85rem;">'
                        f'<b>{_short}</b> '
                        f'<span style="color:{_clr};font-weight:700;">{_pct}%</span></div>',
                        unsafe_allow_html=True,
                    )

else:
    st.info("No students registered yet. Students will appear here after they sign in and generate a profile.")

st.markdown("---")


# ─── Check for trace data ─────────────────────────────────────────────────────
from cert_prep.agent_trace import RunTrace, AgentStep, build_mock_trace

trace: RunTrace | None = st.session_state.get("trace", None)
profile                = st.session_state.get("profile", None)
raw                    = st.session_state.get("raw", None)

if trace is None:
    # Build a small demo raw + profile for preview
    from cert_prep.models import RawStudentInput
    _demo_raw = RawStudentInput(
        student_name    = "Demo Student",
        exam_target     = "AI-102 – Azure AI Engineer Associate",
        background_text = "Data scientist with 3 years of Python and scikit-learn",
        existing_certs  = ["DP-100"],
        hours_per_week  = 10,
        weeks_available = 8,
        concern_topics  = ["generative AI", "responsible AI"],
        preferred_style = "hands-on labs",
        goal_text       = "Pass AI-102 exam",
    )
    from cert_prep.b1_mock_profiler import run_mock_profiling
    _demo_profile = run_mock_profiling(_demo_raw)
    trace = build_mock_trace(_demo_raw, _demo_profile)
    profile = _demo_profile
    raw = _demo_raw
    _demo_mode = True
else:
    _demo_mode = False


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1 – Run Summary Cards
# ═════════════════════════════════════════════════════════════════════════════
_section_header("Run Summary", "📋")

run_cols = st.columns(6)
summary_items = [
    ("Run ID",      trace.run_id,                                  BLUE),
    ("Student",     trace.student_name,                            PURPLE),
    ("Exam Target", trace.exam_target.split("–")[0].strip(),       GREEN),
    ("Timestamp",   trace.timestamp,                               GREY),
    ("Mode",        trace.mode,                                    ORANGE),
    ("Total Time",  f"{trace.total_ms:.0f} ms",                    YELLOW),
]
for col, (lbl, val, clr) in zip(run_cols, summary_items):
    with col:
        st.markdown(_card(lbl, val, clr, wide=True), unsafe_allow_html=True)



# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2 – Learner Journey Flow
# ═════════════════════════════════════════════════════════════════════════════
_section_header("Learner Journey Flow", "🗺️")

st.caption(
    "End-to-end view of the learner's path through the multi-agent system. "
    "Each stage shows the responsible agent, its contribution, and timing."
)

# ── 2a: Journey funnel ───────────────────────────────────────────────────────
_j_col1, _j_col2 = st.columns([3, 2])

with _j_col1:
    _stages = [
        "Student Input",
        "Intake & Profiling",
        "Learning Path Planning",
        "Study Plan Generation",
        "Domain Confidence Scoring",
        "Readiness Assessment",
    ]
    _stage_values  = [100, 92, 85, 78, 70, 65]
    _stage_colors  = [BLUE, PURPLE, "#a78bfa", "#06b6d4", GREEN, ORANGE]

    funnel_fig = go.Figure(go.Funnel(
        y=_stages,
        x=_stage_values,
        textinfo="value+percent initial",
        marker=dict(color=_stage_colors),
        connector=dict(line=dict(color="#E1DFDD", width=1)),
    ))
    funnel_fig.update_layout(
        paper_bgcolor=CARD_BG,
        plot_bgcolor=CARD_BG,
        font=dict(color="#1B1B1B", size=11),
        height=340,
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(funnel_fig, use_container_width=True)

with _j_col2:
    # Agent contribution — horizontal bar (cleaner than pie)
    _agent_labels = [s.agent_name.split("(")[0].strip() for s in trace.steps]
    _agent_times  = [s.duration_ms for s in trace.steps]
    _agent_clrs   = [AGENT_COLORS.get(s.agent_id, BLUE) for s in trace.steps]
    _agent_pcts   = [t / max(1, trace.total_ms) * 100 for t in _agent_times]

    bar_fig = go.Figure(go.Bar(
        y=_agent_labels,
        x=_agent_times,
        orientation="h",
        marker_color=_agent_clrs,
        text=[f"{t:.0f} ms ({p:.0f}%)" for t, p in zip(_agent_times, _agent_pcts)],
        textposition="auto",
        textfont=dict(size=10),
        hovertemplate="<b>%{y}</b><br>%{x:.0f} ms<extra></extra>",
    ))
    bar_fig.update_layout(
        paper_bgcolor=CARD_BG,
        plot_bgcolor=CARD_BG,
        font=dict(color="#1B1B1B", size=11),
        height=340,
        margin=dict(l=10, r=10, t=10, b=30),
        xaxis=dict(title="Time (ms)", color=GREY, gridcolor="#E1DFDD"),
        yaxis=dict(color="#1B1B1B", autorange="reversed"),
        showlegend=False,
    )
    st.plotly_chart(bar_fig, use_container_width=True)

    # Quick insight: bottleneck
    _slowest = max(trace.steps, key=lambda s: s.duration_ms)
    _slowest_pct = _slowest.duration_ms / max(1, trace.total_ms) * 100
    st.markdown(
        f'<div style="background:#FFF8F0;border-left:3px solid {ORANGE};border-radius:4px;'
        f'padding:8px 12px;font-size:0.82rem;color:#323130;">'
        f'⚡ <b>Bottleneck:</b> {_slowest.agent_name.split("(")[0].strip()} '
        f'consumed {_slowest_pct:.0f}% of total run time ({_slowest.duration_ms:.0f} ms / {trace.total_ms:.0f} ms).</div>',
        unsafe_allow_html=True,
    )

# ── 2b: Journey stage cards ──────────────────────────────────────────────────
_journey_stages = [
    {
        "icon": "📥", "title": "Intake",
        "agent": "safety + intake", "color": BLUE,
        "desc": "Collect learner background, goals, constraints. Apply safety guardrails.",
    },
    {
        "icon": "🧠", "title": "Profiling",
        "agent": "profiling + scorer", "color": PURPLE,
        "desc": "Infer experience level, learning style, per-domain knowledge & confidence.",
    },
    {
        "icon": "🗺️", "title": "Learning Path",
        "agent": "analogy mapper", "color": "#06b6d4",
        "desc": "Map existing skills to exam domains. Curate MS Learn modules & resources.",
    },
    {
        "icon": "📅", "title": "Study Plan",
        "agent": "engagement gen", "color": GREEN,
        "desc": "Generate week-by-week Gantt plan. Allocate hours by domain weight & risk.",
    },
    {
        "icon": "✅", "title": "Readiness Gate",
        "agent": "gate checker", "color": ORANGE,
        "desc": "Evaluate if learner is ready for assessment or needs remediation loop.",
    },
    {
        "icon": "📊", "title": "Assessment",
        "agent": "assessment + verifier", "color": RED,
        "desc": "Build exam-style quiz, verify quality, score results, decide GO/NO-GO.",
    },
]

_jcols = st.columns(len(_journey_stages))
for _jc, _js in zip(_jcols, _journey_stages):
    with _jc:
        st.markdown(
            f"""<div style="background:{CARD_BG};border-top:3px solid {_js['color']};
                 border-radius:4px;padding:14px 12px;text-align:center;min-height:180px;
                 border:1px solid #E1DFDD;box-shadow:0 1px 2px rgba(0,0,0,0.04);">
              <div style="font-size:1.8rem;">{_js['icon']}</div>
              <div style="color:#1B1B1B;font-weight:700;font-size:0.95rem;margin:6px 0 4px;">
                {_js['title']}</div>
              <div style="color:{GREY};font-size:0.72rem;text-transform:uppercase;
                   letter-spacing:.04em;margin-bottom:6px;">{_js['agent']}</div>
              <div style="color:#616161;font-size:0.78rem;line-height:1.4;">{_js['desc']}</div>
            </div>""",
            unsafe_allow_html=True,
        )


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3 – Agent Execution Timeline (Gantt)
# ═════════════════════════════════════════════════════════════════════════════
_section_header("Agent Execution Timeline", "⏱️")
st.caption("Horizontal bars show each agent\'s processing window (relative ms from run start).")

import pandas as pd

gantt_rows = []
for step in trace.steps:
    gantt_rows.append({
        "Agent":    f"{step.icon} {step.agent_name.split('(')[0].strip()}",
        "Start":    step.start_ms,
        "Finish":   step.start_ms + step.duration_ms,
        "Duration": step.duration_ms,
        "Status":   step.status,
        "Color":    AGENT_COLORS.get(step.agent_id, BLUE),
    })

gantt_df = pd.DataFrame(gantt_rows)

gantt_fig = go.Figure()
for _, row in gantt_df.iterrows():
    gantt_fig.add_trace(go.Bar(
        name        = row["Agent"],
        x           = [row["Duration"]],
        y           = [row["Agent"]],
        base        = row["Start"],
        orientation = "h",
        marker_color= row["Color"],
        text        = f'{row["Duration"]:.0f} ms',
        textposition= "auto",
        showlegend  = False,
        hovertemplate = (
            f"<b>{row['Agent']}</b><br>"
            f"Start: {row['Start']:.0f} ms<br>"
            f"Duration: {row['Duration']:.0f} ms<br>"
            f"Status: {row['Status']}<extra></extra>"
        ),
    ))

gantt_fig.update_layout(
    barmode      = "stack",
    paper_bgcolor= CARD_BG,
    plot_bgcolor = CARD_BG,
    font         = dict(color="#1B1B1B", size=11),
    height       = max(220, len(trace.steps) * 52),
    margin       = dict(l=10, r=20, t=10, b=40),
    xaxis = dict(
        title      = "Time (ms from run start)",
        color      = GREY,
        gridcolor  = "#E1DFDD",
        zeroline   = False,
    ),
    yaxis = dict(
        color      = "#1B1B1B",
        gridcolor  = "#E1DFDD",
        autorange  = "reversed",
    ),
)
st.plotly_chart(gantt_fig, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4 – Per-Agent I/O Cards
# ═════════════════════════════════════════════════════════════════════════════
_section_header("Per-Agent Interaction Log", "🗂️")
st.caption("Every agent's role, inputs, outputs, decisions and timing — always visible at a glance.")

for step in trace.steps:
    clr          = AGENT_COLORS.get(step.agent_id, BLUE)
    _status_map  = {"success": "✓ Completed", "warning": "⚠ Review", "error": "✗ Failed"}
    status_color = GREEN if step.status == "success" else (RED if step.status == "error" else ORANGE)
    _status_lbl  = _html.escape(_status_map.get(step.status, step.status.title()))

    # Escape I/O text so angle-brackets / ampersands never break the HTML card
    _in_html  = _html.escape(str(step.input_summary)).replace("\n", "<br>")
    _out_html = _html.escape(str(step.output_summary)).replace("\n", "<br>")

    # Build decisions HTML (rendered inside the card)
    _dec_html = ""
    if step.decisions:
        _dec_items = "".join(
            f'<li style="margin-bottom:3px;color:#323130;font-size:0.83rem;line-height:1.5;">{_html.escape(str(d))}</li>'
            for d in step.decisions
        )
        _dec_html = f"""
        <div style="padding:10px 16px 8px;border-top:1px solid #E1DFDD;">
          <div style="color:{GREY};font-size:0.7rem;font-weight:700;text-transform:uppercase;
                      letter-spacing:.06em;margin-bottom:6px;">⚙️ Rules / Decisions Applied</div>
          <ul style="margin:0;padding-left:18px;">{_dec_items}</ul>
        </div>"""

    # Build card HTML via concatenation — never inject _dec_html inside an
    # f-string, which causes Streamlit to render it as escaped plain text.
    _agent_label = _html.escape(step.agent_name.split("(")[0].strip())
    _dur_lbl     = f"{step.duration_ms:.0f}&nbsp;ms"
    _icon_lbl    = _html.escape(str(step.icon))

    _card_html = (
        f'<div style="background:{CARD_BG};border:1px solid #E1DFDD;border-radius:8px;'
        f'margin-bottom:16px;overflow:hidden;box-shadow:0 2px 6px rgba(0,0,0,0.06);">'

        # ── Header band ──
        f'<div style="background:{clr};padding:10px 16px;'
        f'display:flex;align-items:center;justify-content:space-between;">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<span style="font-size:1.3rem;">{_icon_lbl}</span>'
        f'<div>'
        f'<span style="color:#fff;font-size:0.95rem;font-weight:700;display:block;">{_agent_label}</span>'
        f'</div></div>'
        f'<div style="display:flex;gap:6px;align-items:center;">'
        f'<span style="background:rgba(255,255,255,0.25);color:#fff;'
        f'border:1px solid rgba(255,255,255,0.5);border-radius:12px;'
        f'padding:2px 10px;font-size:0.75rem;font-weight:700;">{_status_lbl}</span>'
        f'<span style="background:rgba(255,255,255,0.25);color:#fff;'
        f'border-radius:12px;padding:2px 10px;font-size:0.75rem;font-weight:600;">{_dur_lbl}</span>'
        f'</div></div>'

        # ── I/O grid ──
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:0;">'
        f'<div style="padding:12px 16px;border-right:1px solid #E1DFDD;">'
        f'<div style="color:{GREY};font-size:0.7rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:.06em;margin-bottom:6px;">📨 Input</div>'
        f'<div style="color:#323130;font-size:0.85rem;line-height:1.5;">{_in_html}</div>'
        f'</div>'
        f'<div style="padding:12px 16px;">'
        f'<div style="color:{GREY};font-size:0.7rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:.06em;margin-bottom:6px;">📤 Output</div>'
        f'<div style="color:#323130;font-size:0.85rem;line-height:1.5;">{_out_html}</div>'
        f'</div></div>'
    )
    # Append decisions block as plain string (no f-string wrapping)
    _card_html += _dec_html
    _card_html += '</div>'

    st.markdown(_card_html, unsafe_allow_html=True)

    if step.warnings:
        for w in step.warnings:
            st.warning(w, icon="⚠️")
    if step.detail:
        import json as _json
        with st.expander(f"🔍 {step.agent_name.split('(')[0].strip()} — raw JSON payload", expanded=False):
            st.code(_json.dumps(step.detail, indent=2, default=str), language="json")


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 5 – Domain Decision Audit Trail
# ═════════════════════════════════════════════════════════════════════════════
_section_header("Domain Decision Audit Trail", "📋")
st.caption(
    "Final per-domain outcome: confidence score, knowledge level, "
    "skip recommendation, and risk flag."
)

if profile is not None:
    audit_rows = []
    for dp in profile.domain_profiles:
        audit_rows.append({
            "Domain":        dp.domain_name,
            "Knowledge Level": dp.knowledge_level.value.replace("_", " ").title(),
            "Confidence":    f"{dp.confidence_score:.0%}",
            "Conf (raw)":    dp.confidence_score,
            "Skip?":         "✅ Yes" if dp.skip_recommended else "—",
            "Risk?":         "⚠️ Yes" if dp.domain_id in profile.risk_domains else "—",
            "Notes":         dp.notes[:90] + "…" if len(dp.notes) > 90 else dp.notes,
        })

    audit_df = pd.DataFrame(audit_rows)

    # Colour-code confidence bars via plotly table
    col_table, col_bar = st.columns([3, 2])

    with col_table:
        header_vals = ["Domain", "Level", "Confidence", "Skip?", "Risk?"]
        cell_vals   = [
            audit_df["Domain"].tolist(),
            audit_df["Knowledge Level"].tolist(),
            audit_df["Confidence"].tolist(),
            audit_df["Skip?"].tolist(),
            audit_df["Risk?"].tolist(),
        ]
        conf_colors = [
            GREEN if r >= 0.65 else (ORANGE if r >= 0.40 else RED)
            for r in audit_df["Conf (raw)"].tolist()
        ]
        table_fig = go.Figure(go.Table(
            columnwidth = [180, 130, 100, 60, 60],
            header = dict(
                values     = [f"<b>{h}</b>" for h in header_vals],
                fill_color = "#EFF6FF",
                align      = "left",
                font       = dict(color="#1B1B1B", size=12),
                height     = 32,
            ),
            cells = dict(
                values     = cell_vals,
                fill_color = [
                    [CARD_BG] * len(audit_df),
                    [CARD_BG] * len(audit_df),
                    conf_colors,
                    [CARD_BG] * len(audit_df),
                    [CARD_BG] * len(audit_df),
                ],
                align      = ["left", "left", "center", "center", "center"],
                font       = dict(color="#1B1B1B", size=11),
                height     = 30,
            ),
        ))
        table_fig.update_layout(
            paper_bgcolor = CARD_BG,
            margin        = dict(l=0, r=0, t=0, b=0),
            height        = 280,
        )
        st.plotly_chart(table_fig, use_container_width=True)

    with col_bar:
        _adm_labels = [dp.domain_name.replace("Implement ", "").replace(" Solutions", "")
                       for dp in profile.domain_profiles]
        bar_fig = go.Figure(go.Bar(
            y    = _adm_labels,
            x    = [dp.confidence_score for dp in profile.domain_profiles],
            orientation = "h",
            marker_color = conf_colors,
            text  = [f"{dp.confidence_score:.0%}" for dp in profile.domain_profiles],
            textposition = "outside",
        ))
        bar_fig.update_layout(
            paper_bgcolor = CARD_BG,
            plot_bgcolor  = CARD_BG,
            font          = dict(color="#1B1B1B", size=11),
            height        = len(_adm_labels) * 52 + 50,  # fixed 52 px per bar
            bargap        = 0.30,
            margin        = dict(l=0, r=50, t=10, b=20),
            xaxis = dict(
                range      = [0, 1.05],
                gridcolor  = "#E1DFDD",
                color      = GREY,
                tickformat = ".0%",
            ),
            yaxis = dict(color="#1B1B1B", gridcolor="#E1DFDD"),
            uniformtext_minsize=7,
            uniformtext_mode="hide",
        )
        bar_fig.add_vline(x=0.50, line_dash="dash", line_color="rgba(0,0,0,0.15)",
                          annotation_text="50% threshold",
                          annotation_font_color=GREY,
                          annotation_position="top right")
        st.plotly_chart(bar_fig, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 6 – Session Student Table (all profiles this session)
# ═════════════════════════════════════════════════════════════════════════════
_section_header("Session History", "📂")
st.caption("All learner profiles generated in this browser session.")

# Append current profile to a running history list
if profile is not None and not _demo_mode:
    history: list = st.session_state.get("admin_history", [])
    # Avoid duplicates by run_id
    existing_ids = {h.get("run_id") for h in history}
    if trace.run_id not in existing_ids:
        history.append({
            "run_id":      trace.run_id,
            "student":     trace.student_name,
            "exam":        trace.exam_target.split("–")[0].strip(),
            "mode":        trace.mode,
            "time":        trace.timestamp,
            "total_ms":    f"{trace.total_ms:.0f} ms",
            "level":       profile.experience_level.value.replace("_", " ").title(),
            "avg_conf":    f"{sum(dp.confidence_score for dp in profile.domain_profiles)/len(profile.domain_profiles):.0%}",
            "risk_count":  len(profile.risk_domains),
        })
        st.session_state["admin_history"] = history
    history_df = pd.DataFrame(history)
else:
    # Demo mode fallback
    history_df = pd.DataFrame([{
        "run_id": trace.run_id, "student": trace.student_name,
        "exam": trace.exam_target.split("–")[0].strip(), "mode": trace.mode, "time": trace.timestamp,
        "total_ms": f"{trace.total_ms:.0f} ms",
        "level": profile.experience_level.value.replace("_", " ").title() if profile else "—",
        "avg_conf": "—", "risk_count": None,
    }])

if len(history_df) > 0:
    st.dataframe(
        history_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "run_id":     st.column_config.TextColumn("Run ID",     width="small"),
            "student":    st.column_config.TextColumn("Student",    width="medium"),
            "exam":       st.column_config.TextColumn("Exam",       width="medium"),
            "mode":       st.column_config.TextColumn("Mode",       width="small"),
            "time":       st.column_config.TextColumn("Timestamp",  width="medium"),
            "total_ms":   st.column_config.TextColumn("Total Time", width="small"),
            "level":      st.column_config.TextColumn("Level",      width="medium"),
            "avg_conf":   st.column_config.TextColumn("Avg Conf",   width="small"),
            "risk_count": st.column_config.NumberColumn("Risk Domains", width="small"),
        },
    )
else:
    st.info("No sessions recorded yet — generate a profile from the main page first.")


# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#a0a0a0;font-size:0.78rem;'>"
    "🔐 Admin Dashboard · Microsoft Agents League · For authorised users only"
    "</p>",
    unsafe_allow_html=True,
)
