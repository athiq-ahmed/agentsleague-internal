"""
b1_2_progress_agent.py — Progress Tracker & Readiness Assessor (Block 1.2)
===========================================================================
Handles the "returning learner" flow — the first Human-in-the-Loop (HITL)
gate in the pipeline.  The student fills in a progress check-in form, and
this agent digests those self-reported answers into a structured readiness
verdict plus actionable nudges.

---------------------------------------------------------------------------
HITL Gate 1 (Tab 4 — "Progress & Readiness")
---------------------------------------------------------------------------
  The Streamlit UI collects:
    • Total hours studied so far
    • Per-domain self-confidence rating (slider 1–5)
    • Whether a practice exam was taken and the score (0–100)
    • Optional free-text study notes
  This snapshot feeds ProgressAgent.assess().  Without this gate
  the quiz and certification recommendation tabs remain locked.

---------------------------------------------------------------------------
Agent: ProgressAgent
---------------------------------------------------------------------------
  Input:   ProgressSnapshot + LearnerProfile
  Output:  ReadinessAssessment
  Pattern: Self-Reflection and Iteration

  Readiness formula:
    readiness_pct = 0.55 × weighted_confidence
                  + 0.25 × hours_utilisation      (capped at 100% of budget)
                  + 0.20 × practice_score

  Verdict thresholds:
    ≥ 75%  → EXAM_READY    (go to quiz)
    60–75% → NEARLY_READY  (targeted revision recommended)
    45–60% → NEEDS_WORK    (gap analysis, more study)
    < 45%  → NOT_READY     (remediation loop — rebuild study plan)

---------------------------------------------------------------------------
Utility functions
---------------------------------------------------------------------------
  generate_profile_pdf(profile, plan, lp) → bytes
    ReportLab PDF: domain radar, Gantt study plan, module list.
    Passed to st.download_button() or attached to the welcome email.

  generate_assessment_pdf(profile, snap, asmt) → bytes
    ReportLab PDF: progress snapshot, domain bars, go/no-go verdict.

  generate_weekly_summary(profile, snapshot, assessment) → str (HTML)
    HTML email body for the weekly progress digest.
    Rendered in the UI via st.components.v1.html() to honour inline styles.

  send_simple_email(smtp_host, smtp_port, to_emails, subject, body_text,
                    sender_email, sender_pass, pdf_bytes, pdf_filename) → (bool, str)
    Pure-library SMTP helper.  All credentials passed as arguments —
    no .env dependency.  Compatible with Gmail, Outlook, any SMTP relay.

  attempt_send_email(to_address, subject, html_body, …) → (bool, str)
    Convenience wrapper: uses inline smtp_user/smtp_pass args first,
    then falls back to SMTP_USER/SMTP_PASS environment variables.

---------------------------------------------------------------------------
Environment variables used (all optional)
---------------------------------------------------------------------------
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM
  If unset, email sending is silently skipped and the download button
  remains available as the fallback.

---------------------------------------------------------------------------
Consumers
---------------------------------------------------------------------------
  streamlit_app.py              Tab 4, Tab 5 gating logic, PDF download buttons
  database.py                   save_progress() persists snapshot + assessment
"""

from __future__ import annotations

import io
import os
import smtplib
import textwrap
from dataclasses import dataclass, field
from datetime import date
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Optional

from cert_prep.models import EXAM_DOMAINS, LearnerProfile, get_exam_domains


# ─── Domain weights lookup (AI-102 used as fallback only — per-exam lookup ────
# happens inside ProgressAgent.assess() via get_exam_domains(exam_target))  ────
_DOMAIN_WEIGHT: dict[str, float] = {d["id"]: d["weight"] for d in EXAM_DOMAINS}
_DOMAIN_NAME:   dict[str, str]   = {d["id"]: d["name"]   for d in EXAM_DOMAINS}


# ─── Enumerations ────────────────────────────────────────────────────────────

class ReadinessVerdict(str, Enum):
    NOT_READY    = "not_ready"      # < 45 %
    NEEDS_WORK   = "needs_work"     # 45–60 %
    NEARLY_READY = "nearly_ready"   # 60–75 %
    EXAM_READY   = "exam_ready"     # ≥ 75 %


class NudgeLevel(str, Enum):
    DANGER  = "danger"   # red
    WARNING = "warning"  # orange/amber
    INFO    = "info"     # blue
    SUCCESS = "success"  # green


# ─── Input / Output models ────────────────────────────────────────────────────

@dataclass
class DomainProgress:
    """Student's self-assessed progress on one exam domain (1–5 scale)."""
    domain_id:    str
    domain_name:  str
    self_rating:  int     # 1 = barely started … 5 = confident / ready
    hours_spent:  float   # hours invested in this domain so far


@dataclass
class ProgressSnapshot:
    """
    Mid-journey state reported by a returning learner.
    Captured via the Streamlit check-in form.
    """
    total_hours_spent:   float
    weeks_elapsed:       int              # weeks since starting the plan
    domain_progress:     list[DomainProgress]
    done_practice_exam:  str              # "yes" | "some" | "no"
    practice_score_pct:  Optional[int]   # 0-100 if done, else None
    email:               Optional[str]   # for weekly summary
    notes:               str             # free-text from student


@dataclass
class Nudge:
    """A single actionable alert/notification for the student."""
    level:   NudgeLevel
    title:   str
    message: str


@dataclass
class DomainStatusLine:
    """Actual vs expected progress for one domain."""
    domain_id:        str
    domain_name:      str
    expected_rating:  float   # 1–5 scale inferred from plan
    actual_rating:    int     # student self-rating
    gap:              float   # actual – expected  (negative = behind)
    status:           str     # "ahead" | "on_track" | "behind" | "critical"


@dataclass
class ReadinessAssessment:
    """
    Output of ProgressAgent.assess().
    All fields consumed by the Streamlit My Progress tab.
    """
    readiness_pct:       float          # 0–100
    verdict:             ReadinessVerdict
    verdict_label:       str            # human-readable
    verdict_colour:      str            # hex
    domain_status:       list[DomainStatusLine]
    nudges:              list[Nudge]
    hours_progress_pct:  float          # hours_spent / total_budget %
    hours_remaining:     float
    weeks_remaining:     int
    recommended_focus:   list[str]      # domain_ids to focus on next
    exam_go_nogo:        str            # "GO" | "CONDITIONAL GO" | "NOT YET"
    go_nogo_colour:      str            # hex
    go_nogo_reason:      str


# ─── Progress Agent ───────────────────────────────────────────────────────────

class ProgressAgent:
    """
    Analyses a mid-journey ProgressSnapshot against the original LearnerProfile
    to produce a ReadinessAssessment with smart nudges.
    """

    _VERDICT_META: dict[ReadinessVerdict, tuple[str, str]] = {
        ReadinessVerdict.NOT_READY:    ("Not Ready",      "#d13438"),
        ReadinessVerdict.NEEDS_WORK:   ("Needs Work",     "#ca5010"),
        ReadinessVerdict.NEARLY_READY: ("Nearly Ready",   "#8a6d00"),
        ReadinessVerdict.EXAM_READY:   ("Exam Ready! 🎉", "#107c10"),
    }

    def assess(
        self,
        profile: LearnerProfile,
        snap: ProgressSnapshot,
    ) -> ReadinessAssessment:

        # ── 1. Weighted domain readiness ──────────────────────────────────────
        # Domain score = self_rating / 5, weighted by exam weight
        # Build per-exam weight lookup so DP-100 / AZ-204 / AZ-305 etc. use
        # their correct weights instead of the AI-102 defaults.
        _exam_domain_list = get_exam_domains(profile.exam_target)
        _exam_weight_map: dict[str, float] = {
            d["id"]: d["weight"] for d in _exam_domain_list
        }
        _fallback_w = 1.0 / len(_exam_domain_list) if _exam_domain_list else 1.0 / len(EXAM_DOMAINS)

        weighted_score = 0.0
        for dp in snap.domain_progress:
            w = _exam_weight_map.get(dp.domain_id, _fallback_w)
            weighted_score += (dp.self_rating / 5.0) * w

        # ── 2. Hours progress ratio ───────────────────────────────────────────
        total_budget = profile.total_budget_hours or 1.0
        hours_progress = min(snap.total_hours_spent / total_budget, 1.0)

        # ── 3. Practice exam bonus ────────────────────────────────────────────
        if snap.done_practice_exam == "yes" and snap.practice_score_pct is not None:
            practice_factor = min(snap.practice_score_pct / 100.0, 1.0)
        elif snap.done_practice_exam == "some":
            practice_factor = 0.50
        else:
            practice_factor = 0.0

        # ── 4. Composite readiness ────────────────────────────────────────────
        # Weights: domain self-assessment 55%, hours 25%, practice 20%
        readiness_raw = (
            weighted_score   * 0.55 +
            hours_progress   * 0.25 +
            practice_factor  * 0.20
        )
        readiness_pct = round(readiness_raw * 100, 1)

        # ── 5. Verdict ────────────────────────────────────────────────────────
        if readiness_pct >= 75:
            verdict = ReadinessVerdict.EXAM_READY
        elif readiness_pct >= 60:
            verdict = ReadinessVerdict.NEARLY_READY
        elif readiness_pct >= 45:
            verdict = ReadinessVerdict.NEEDS_WORK
        else:
            verdict = ReadinessVerdict.NOT_READY

        verdict_label, verdict_colour = self._VERDICT_META[verdict]

        # ── 6. Domain status (actual vs expected) ────────────────────────────
        weeks_elapsed  = max(snap.weeks_elapsed, 1)
        plan_progress  = min(weeks_elapsed / max(profile.weeks_available, 1), 1.0)
        expected_avg   = 1 + (4 * plan_progress)   # expected rating grows 1→5 over the plan

        domain_status: list[DomainStatusLine] = []
        for dp in snap.domain_progress:
            expected = max(1.0, min(5.0, expected_avg))
            gap      = dp.self_rating - expected
            if gap >= 0.5:
                status = "ahead"
            elif gap >= -0.5:
                status = "on_track"
            elif gap >= -1.5:
                status = "behind"
            else:
                status = "critical"
            domain_status.append(DomainStatusLine(
                domain_id       = dp.domain_id,
                domain_name     = dp.domain_name,
                expected_rating = round(expected, 1),
                actual_rating   = dp.self_rating,
                gap             = round(gap, 1),
                status          = status,
            ))

        # ── 7. Nudges ─────────────────────────────────────────────────────────
        nudges = self._build_nudges(profile, snap, readiness_pct, domain_status, hours_progress)

        # ── 8. Recommended focus domains ─────────────────────────────────────
        focus = [
            ds.domain_id for ds in
            sorted(domain_status, key=lambda d: (d.actual_rating, d.gap))
            if ds.status in ("behind", "critical")
        ][:3]
        if not focus:
            # suggest the risk domains from the original profile
            focus = profile.risk_domains[:2]

        # ── 9. Hours remaining ────────────────────────────────────────────────
        hours_remaining = max(0.0, total_budget - snap.total_hours_spent)
        weeks_remaining = max(0, profile.weeks_available - snap.weeks_elapsed)

        # ── 10. GO / NO-GO ────────────────────────────────────────────────────
        go_nogo, go_colour, go_reason = self._go_nogo(
            readiness_pct, snap, weeks_remaining, domain_status,
        )

        return ReadinessAssessment(
            readiness_pct       = readiness_pct,
            verdict             = verdict,
            verdict_label       = verdict_label,
            verdict_colour      = verdict_colour,
            domain_status       = domain_status,
            nudges              = nudges,
            hours_progress_pct  = round(hours_progress * 100, 1),
            hours_remaining     = round(hours_remaining, 1),
            weeks_remaining     = weeks_remaining,
            recommended_focus   = focus,
            exam_go_nogo        = go_nogo,
            go_nogo_colour      = go_colour,
            go_nogo_reason      = go_reason,
        )

    # ── Nudge builder ─────────────────────────────────────────────────────────

    def _build_nudges(
        self,
        profile: LearnerProfile,
        snap: ProgressSnapshot,
        readiness_pct: float,
        domain_status: list[DomainStatusLine],
        hours_progress: float,
    ) -> list[Nudge]:
        nudges: list[Nudge] = []

        # Overall readiness nudge
        if readiness_pct >= 75:
            nudges.append(Nudge(
                level=NudgeLevel.SUCCESS,
                title="You're exam ready! 🎉",
                message=(
                    f"Your readiness score is **{readiness_pct:.0f}%**. "
                    "Book your exam slot now — every extra day is money saved! "
                    "Focus remaining time on practice tests and edge-case topics."
                ),
            ))
        elif readiness_pct >= 60:
            nudges.append(Nudge(
                level=NudgeLevel.WARNING,
                title="Nearly there — final push needed",
                message=(
                    f"You're at **{readiness_pct:.0f}%** readiness. "
                    "You need one more focused study sprint before scheduling your exam. "
                    "Close the gaps in your weakest domains and complete at least one full practice exam."
                ),
            ))
        elif readiness_pct >= 45:
            nudges.append(Nudge(
                level=NudgeLevel.WARNING,
                title="Progress detected — more structured study required",
                message=(
                    f"Readiness is **{readiness_pct:.0f}%**. You're making progress but "
                    "aren't yet ready to sit the exam confidently. "
                    "Increase weekly hours and focus on the flagged critical domains below."
                ),
            ))
        else:
            nudges.append(Nudge(
                level=NudgeLevel.DANGER,
                title="Not yet ready — serious study time needed",
                message=(
                    f"Readiness is **{readiness_pct:.0f}%**. Do not schedule your exam yet. "
                    "Revisit your study plan, consider requesting more time from your employer/schedule, "
                    "and prioritise the weakest domains urgently."
                ),
            ))

        # Hours pacing nudge
        if hours_progress < 0.30 and snap.weeks_elapsed > 1:
            nudges.append(Nudge(
                level=NudgeLevel.DANGER,
                title="⏰ You're behind on study hours",
                message=(
                    f"You've completed only **{snap.total_hours_spent:.0f} h** "
                    f"({hours_progress:.0%} of your {profile.total_budget_hours:.0f} h budget), "
                    "but have already used "
                    f"{snap.weeks_elapsed}/{profile.weeks_available} weeks. "
                    "Consider increasing your daily study blocks to catch up."
                ),
            ))
        elif hours_progress < 0.55 and snap.weeks_elapsed >= profile.weeks_available // 2:
            nudges.append(Nudge(
                level=NudgeLevel.WARNING,
                title="⏰ Halfway through your weeks — check your pacing",
                message=(
                    f"You're {snap.weeks_elapsed}/{profile.weeks_available} weeks in "
                    f"but have only used {hours_progress:.0%} of your study budget. "
                    "Try to add an extra study session each week."
                ),
            ))

        # Critical domain nudges
        critical = [ds for ds in domain_status if ds.status == "critical"]
        if critical:
            names = ", ".join(
                ds.domain_name.replace("Implement ", "").replace(" Solutions", "")
                for ds in critical
            )
            nudges.append(Nudge(
                level=NudgeLevel.DANGER,
                title=f"🚨 {len(critical)} domain(s) critically behind",
                message=(
                    f"**{names}** — your self-rating is significantly below where it should be "
                    "at this point in your plan. Dedicate your next 2–3 study sessions exclusively "
                    "to these topics."
                ),
            ))

        # No practice exam nudge
        if snap.done_practice_exam == "no" and snap.weeks_elapsed >= 2:
            nudges.append(Nudge(
                level=NudgeLevel.INFO,
                title="📝 No practice exam taken yet",
                message=(
                    "Practice exams are one of the strongest predictors of actual exam success. "
                    "Take a timed practice test on Microsoft Learn or MeasureUp this week — "
                    "even a partial one — to benchmark your readiness objectively."
                ),
            ))

        # Practice exam low score
        if (snap.done_practice_exam == "yes"
                and snap.practice_score_pct is not None
                and snap.practice_score_pct < 65):
            nudges.append(Nudge(
                level=NudgeLevel.WARNING,
                title=f"📝 Practice score {snap.practice_score_pct}% — below pass threshold",
                message=(
                    "Microsoft certification exams typically require ~70% to pass. Your practice score suggests "
                    "targeted revision is still needed. Focus on the domains where you lost "
                    "marks in the practice exam, not broad re-reading."
                ),
            ))

        return nudges

    # ── GO / NO-GO logic ──────────────────────────────────────────────────────

    def _go_nogo(
        self,
        readiness_pct: float,
        snap: ProgressSnapshot,
        weeks_remaining: int,
        domain_status: list[DomainStatusLine],
    ) -> tuple[str, str, str]:
        critical_count = sum(1 for ds in domain_status if ds.status == "critical")

        if readiness_pct >= 75 and critical_count == 0:
            return (
                "GO",
                "#107c10",
                "Your readiness score and domain coverage both clear the threshold. "
                "You are ready to book your exam.",
            )
        elif readiness_pct >= 65 and critical_count <= 1 and weeks_remaining >= 1:
            return (
                "CONDITIONAL GO",
                "#8a6d00",
                f"You're close — one more targeted study week should get you over the line. "
                f"{'Close the gap on 1 critical domain first. ' if critical_count else ''}"
                "Book a date ~2 weeks out to maintain urgency.",
            )
        else:
            reasons = []
            if readiness_pct < 65:
                reasons.append(f"readiness is {readiness_pct:.0f}% (target ≥75%)")
            if critical_count > 1:
                reasons.append(f"{critical_count} domains critically behind schedule")
            if weeks_remaining == 0 and readiness_pct < 65:
                reasons.append("no study weeks remaining but score not sufficient")
            return (
                "NOT YET",
                "#d13438",
                "Do not book the exam yet. " + "; ".join(reasons).capitalize() + ".",
            )


# ─── Weekly summary e-mail ────────────────────────────────────────────────────

def generate_weekly_summary(
    profile: LearnerProfile,
    snap: ProgressSnapshot,
    assessment: ReadinessAssessment,
) -> str:
    """
    Returns a self-contained HTML string suitable for sending as an e-mail body.
    Also usable as an in-app preview.
    """
    today = date.today().strftime("%B %d, %Y")
    domain_rows = ""
    for ds in assessment.domain_status:
        gap_html = ""
        if ds.status == "critical":
            gap_html = "<span style='color:#d13438;font-weight:700;'>🚨 Critical</span>"
        elif ds.status == "behind":
            gap_html = "<span style='color:#ca5010;'>⚠ Behind</span>"
        elif ds.status == "on_track":
            gap_html = "<span style='color:#0078d4;'>◑ On track</span>"
        else:
            gap_html = "<span style='color:#107c10;'>✓ Ahead</span>"

        domain_rows += f"""
        <tr>
          <td style="padding:6px 10px;border-bottom:1px solid #eeeeee;">{ds.domain_name}</td>
          <td style="padding:6px 10px;border-bottom:1px solid #eeeeee;text-align:center;">
            {"⭐" * ds.actual_rating}{"☆" * (5 - ds.actual_rating)} ({ds.actual_rating}/5)
          </td>
          <td style="padding:6px 10px;border-bottom:1px solid #eeeeee;text-align:center;">{gap_html}</td>
        </tr>"""

    nudge_html = ""
    level_bg = {
        NudgeLevel.DANGER:  "#fde7f3",
        NudgeLevel.WARNING: "#fff4ce",
        NudgeLevel.INFO:    "#eef6ff",
        NudgeLevel.SUCCESS: "#e9f7ee",
    }
    level_border = {
        NudgeLevel.DANGER:  "#d13438",
        NudgeLevel.WARNING: "#ca5010",
        NudgeLevel.INFO:    "#0078d4",
        NudgeLevel.SUCCESS: "#107c10",
    }
    for n in assessment.nudges[:4]:
        bg  = level_bg.get(n.level, "#f5f5f5")
        bdr = level_border.get(n.level, "#888")
        nudge_html += f"""
        <div style="margin:8px 0;padding:10px 14px;background:{bg};
                    border-left:4px solid {bdr};border-radius:6px;">
          <b>{n.title}</b><br/>
          <span style="font-size:0.9em;">{n.message.replace("**","<b>",1).replace("**","</b>",1)}</span>
        </div>"""

    verdict_colour = assessment.verdict_colour
    go_colour      = assessment.go_nogo_colour

    html = textwrap.dedent(f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family:Segoe UI,Arial,sans-serif;max-width:640px;margin:auto;
                 background:#f9f9f9;padding:20px;">
      <div style="background:linear-gradient(135deg,#5C2D91,#B4009E);color:white;
                  padding:20px 24px;border-radius:12px;margin-bottom:20px;">
        <h2 style="margin:0;">📊 Weekly Study Progress Report</h2>
        <p style="margin:4px 0 0;opacity:0.85;">{profile.student_name} · {profile.exam_target} · {today}</p>
      </div>

      <div style="display:flex;gap:12px;margin-bottom:16px;">
        <div style="flex:1;background:white;border-left:4px solid {verdict_colour};
                    border-radius:8px;padding:12px 16px;box-shadow:0 2px 6px rgba(0,0,0,0.06);">
          <div style="font-size:0.75rem;color:#888;font-weight:600;text-transform:uppercase;">
            Readiness Score
          </div>
          <div style="font-size:1.6rem;font-weight:700;color:{verdict_colour};">
            {assessment.readiness_pct:.0f}%
          </div>
          <div style="font-size:0.85rem;color:{verdict_colour};font-weight:600;">
            {assessment.verdict_label}
          </div>
        </div>
        <div style="flex:1;background:white;border-left:4px solid {go_colour};
                    border-radius:8px;padding:12px 16px;box-shadow:0 2px 6px rgba(0,0,0,0.06);">
          <div style="font-size:0.75rem;color:#888;font-weight:600;text-transform:uppercase;">
            Exam Decision
          </div>
          <div style="font-size:1.6rem;font-weight:700;color:{go_colour};">
            {assessment.exam_go_nogo}
          </div>
          <div style="font-size:0.85rem;color:#555;">{assessment.go_nogo_reason[:80]}…</div>
        </div>
        <div style="flex:1;background:white;border-left:4px solid #0078d4;
                    border-radius:8px;padding:12px 16px;box-shadow:0 2px 6px rgba(0,0,0,0.06);">
          <div style="font-size:0.75rem;color:#888;font-weight:600;text-transform:uppercase;">
            Hours Studied
          </div>
          <div style="font-size:1.6rem;font-weight:700;color:#0078d4;">
            {snap.total_hours_spent:.0f} h
          </div>
          <div style="font-size:0.85rem;color:#555;">
            of {profile.total_budget_hours:.0f} h ({assessment.hours_progress_pct:.0f}%)
          </div>
        </div>
      </div>

      <h3 style="color:#5C2D91;margin:16px 0 8px;">🔔 This Week's Nudges</h3>
      {nudge_html}

      <h3 style="color:#5C2D91;margin:16px 0 8px;">📚 Domain Progress</h3>
      <table style="width:100%;border-collapse:collapse;background:white;
                    border-radius:8px;overflow:hidden;box-shadow:0 2px 6px rgba(0,0,0,0.06);">
        <thead>
          <tr style="background:#5C2D91;color:white;">
            <th style="padding:8px 10px;text-align:left;">Domain</th>
            <th style="padding:8px 10px;text-align:center;">Self-Rating</th>
            <th style="padding:8px 10px;text-align:center;">Status</th>
          </tr>
        </thead>
        <tbody>
          {domain_rows}
        </tbody>
      </table>

      <p style="margin-top:24px;font-size:0.8rem;color:#888;text-align:center;">
        Generated by <b>Cert Prep Agent</b> · Microsoft Agents League ·
        <a href="http://localhost:8501" style="color:#5C2D91;">Open app</a>
      </p>
    </body>
    </html>
    """).strip()
    return html


# ─── Email dispatch ───────────────────────────────────────────────────────────

def send_simple_email(
    smtp_host: str,
    smtp_port: int,
    to_emails: "str | list[str]",
    subject: str,
    body_text: str,
    sender_email: str,
    sender_pass: str,
    pdf_bytes: Optional[bytes] = None,
    pdf_filename: str = "report.pdf",
) -> tuple[bool, str]:
    """
    Pure-library SMTP helper — all credentials supplied as arguments.
    No .env configuration required.

    Parameters
    ----------
    smtp_host     : e.g. "smtp.gmail.com"
    smtp_port     : e.g. 587  (STARTTLS) or 465 (SSL)
    to_emails     : single address string or list of addresses
    subject       : email subject line
    body_text     : plain text OR HTML body (auto-detected)
    sender_email  : the Gmail / SMTP account used to authenticate and send
    sender_pass   : app password (Gmail: myaccount.google.com → Security →
                    App passwords → generate a 16-char password)
    pdf_bytes     : optional raw PDF bytes to attach
    pdf_filename  : filename shown to recipient (default "report.pdf")

    Returns
    -------
    (True,  "Sent successfully")
    (False, "<error description>")

    Gmail quickstart
    ----------------
    1. Enable 2-Step Verification on your Google account
    2. Go to myaccount.google.com → Security → App passwords
    3. Generate a 16-char app password for "Mail / Windows Computer"
    4. Pass that password as sender_pass — no .env changes needed
    """
    if not sender_email or not sender_pass:
        return False, "sender_email and sender_pass are required."

    recipients = [to_emails] if isinstance(to_emails, str) else list(to_emails)

    # Detect HTML vs plain text
    is_html = body_text.strip().startswith("<")
    mime_subtype = "html" if is_html else "plain"

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"]    = sender_email
    msg["To"]      = ", ".join(recipients)

    alt_part = MIMEMultipart("alternative")
    alt_part.attach(MIMEText(body_text, mime_subtype, "utf-8"))
    msg.attach(alt_part)

    if pdf_bytes:
        pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
        pdf_part.add_header("Content-Disposition", "attachment", filename=pdf_filename)
        msg.attach(pdf_part)

    try:
        if smtp_port == 465:
            import ssl
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ctx, timeout=15) as server:
                server.login(sender_email, sender_pass)
                server.sendmail(sender_email, recipients, msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.login(sender_email, sender_pass)
                server.sendmail(sender_email, recipients, msg.as_string())
        attach_note = " (PDF attached)" if pdf_bytes else ""
        return True, f"Email sent successfully{attach_note}!"
    except smtplib.SMTPAuthenticationError:
        return False, (
            "Authentication failed. Check your SMTP username and password/API key. "
            "SendGrid: username is 'apikey', password is your API Key. "
            "Mailgun/SES/ACS: use the SMTP credentials from your provider dashboard. "
            "Gmail: use an App Password (myaccount.google.com → Security → App passwords)."
        )
    except Exception as exc:
        return False, f"Failed to send email: {exc}"


def attempt_send_email(
    to_address: str,
    subject: str,
    html_body: str,
    pdf_bytes: Optional[bytes] = None,
    pdf_filename: str = "CertPrep_Report.pdf",
) -> tuple[bool, str]:
    """
    Send an email with optional PDF attachment using stdlib smtplib.
    Credentials and server config are read from env vars:
      SMTP_HOST  (default: smtp.sendgrid.net)
      SMTP_PORT  (default: 587)
      SMTP_USER  SendGrid: literal string 'apikey'; Gmail: your@gmail.com
      SMTP_PASS  SendGrid: API key; Gmail: 16-char App Password
      SMTP_FROM  (default: SMTP_USER)
    """
    _user = os.getenv("SMTP_USER", "")
    _pass = os.getenv("SMTP_PASS", "")

    if not _user or not _pass:
        return False, (
            "Email not configured. Set SMTP_USER and SMTP_PASS "
            "in your .env file (or Streamlit secrets)."
        )

    _host = os.getenv("SMTP_HOST", "smtp.sendgrid.net")
    _port = int(os.getenv("SMTP_PORT", "587"))
    _from = os.getenv("SMTP_FROM", _user)

    return send_simple_email(
        smtp_host=_host,
        smtp_port=_port,
        to_emails=to_address,
        subject=subject,
        body_text=html_body,
        sender_email=_from,
        sender_pass=_pass,
        pdf_bytes=pdf_bytes,
        pdf_filename=pdf_filename,
    )


# ─── PDF report generators ────────────────────────────────────────────────────

def _rl_colour(hex_str: str):
    """Convert a CSS hex colour string to a reportlab Color."""
    from reportlab.lib import colors as rl_colors
    h = hex_str.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
    return rl_colors.Color(r, g, b)


def generate_profile_pdf(
    profile: "LearnerProfile",
    plan=None,
    lp=None,
    raw=None,
) -> bytes:
    """
    Build a study-plan PDF for a newly profiled learner.
    Returns raw PDF bytes.

    Parameters
    ----------
    profile : LearnerProfile
    plan    : StudyPlan (optional) — adds a study-plan task table
    lp      : LearningPath (optional) — adds a learning-path module table
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, KeepTogether,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
    )

    styles = getSampleStyleSheet()
    PURPLE = _rl_colour("#5C2D91")
    DARK   = _rl_colour("#1f2937")
    MUTED  = _rl_colour("#6b7280")
    GREEN  = _rl_colour("#16a34a")
    RED    = _rl_colour("#dc2626")
    AMBER  = _rl_colour("#d97706")
    BLUE   = _rl_colour("#2563eb")
    WHITE  = rl_colors.white
    LIGHT  = _rl_colour("#f3f4ff")

    h1 = ParagraphStyle("H1", parent=styles["Heading1"],
                         textColor=WHITE, fontSize=16, leading=20, spaceAfter=4)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"],
                         textColor=PURPLE, fontSize=12, leading=15, spaceBefore=12, spaceAfter=4)
    body = ParagraphStyle("Body", parent=styles["Normal"],
                           textColor=DARK, fontSize=9, leading=13)
    small = ParagraphStyle("Small", parent=styles["Normal"],
                            textColor=MUTED, fontSize=8, leading=11)
    centre = ParagraphStyle("Centre", parent=styles["Normal"],
                             alignment=TA_CENTER, fontSize=9, leading=13)

    PRIORITY_COLOUR = {
        "critical": RED, "high": AMBER, "medium": BLUE,
        "low": MUTED, "skip": MUTED, "review": GREEN,
    }

    story = []
    today = date.today().strftime("%B %d, %Y")

    # ── Header banner ─────────────────────────────────────────────────────────
    banner_data = [[Paragraph(
        f"<b>📊 Your Personalised Study Plan</b><br/>"
        f"<font size='10'>{profile.student_name} · {profile.exam_target} · {today}</font>",
        h1,
    )]]
    banner_table = Table(banner_data, colWidths=[doc.width])
    banner_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), PURPLE),
        ("ROWPADDING",  (0, 0), (-1, -1), 10),
        ("TOPPADDING",  (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("ROUNDEDCORNERS", [8]),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 0.4 * cm))

    # ── Study setup summary (4-box KPI row) ───────────────────────────────────
    story.append(Paragraph("Study Setup", h2))
    kpi_data = [
        ["Exam Target", "Study Budget", "Hours / Week", "Duration"],
        [
            Paragraph(f"<b>{profile.exam_target}</b>", centre),
            Paragraph(f"<b>{profile.total_budget_hours:.0f} h</b>", centre),
            Paragraph(f"<b>{profile.hours_per_week:.0f} h</b>", centre),
            Paragraph(f"<b>{profile.weeks_available} weeks</b>", centre),
        ],
    ]
    kpi_w = doc.width / 4
    kpi_table = Table(kpi_data, colWidths=[kpi_w] * 4)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), PURPLE),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("BACKGROUND",    (0, 1), (-1, 1), LIGHT),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ROWPADDING",    (0, 0), (-1, -1), 6),
        ("GRID",          (0, 0), (-1, -1), 0.5, rl_colors.lightgrey),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 0.3 * cm))

    # Role / goal — from RawStudentInput (LearnerProfile has neither field)
    _bg   = getattr(raw, "background_text", None) if raw else None
    _goal = getattr(raw, "goal_text", None) if raw else None
    if _bg:
        story.append(Paragraph(f"<b>Background:</b> {_bg[:300]}", body))
    if _goal:
        story.append(Paragraph(f"<b>Goal:</b> {_goal[:300]}", body))
    story.append(Spacer(1, 0.3 * cm))

    # ── Domain readiness table ─────────────────────────────────────────────────
    story.append(Paragraph("Domain Readiness", h2))
    story.append(HRFlowable(width="100%", thickness=1, color=PURPLE))
    story.append(Spacer(1, 0.15 * cm))

    # Build exam-weight lookup from registry (DomainProfile has no exam_weight field)
    from cert_prep.models import get_exam_domains as _get_exam_domains
    _wt_lookup = {
        d["id"]: d.get("weight", 0.0)
        for d in _get_exam_domains(profile.exam_target)
    }

    dr_header = ["Domain", "Weight", "Confidence", "Level", "Priority"]
    dr_rows   = [dr_header]
    for dp in profile.domain_profiles:
        _wt = _wt_lookup.get(dp.domain_id)
        _wt_str = f"{_wt * 100:.0f}%" if _wt else "—"
        # Derive priority from skip_recommended + confidence_score
        # (DomainProfile has no .priority field — that lives on StudyTask)
        if dp.skip_recommended:
            _prio = "skip"
        elif dp.confidence_score < 0.30:
            _prio = "critical"
        elif dp.confidence_score < 0.50:
            _prio = "high"
        elif dp.confidence_score < 0.70:
            _prio = "medium"
        else:
            _prio = "low"
        prio_cell = Paragraph(
            _prio.title(),
            ParagraphStyle("P", parent=body,
                           textColor=PRIORITY_COLOUR.get(_prio, DARK)),
        )
        dr_rows.append([
            dp.domain_name.replace("Implement ", "").replace(" Solutions", ""),
            _wt_str,
            f"{dp.confidence_score * 100:.0f}%",
            dp.knowledge_level.replace("_", " ").title(),
            prio_cell,
        ])
    col_w = [doc.width * f for f in [0.38, 0.12, 0.14, 0.18, 0.18]]
    dr_table = Table(dr_rows, colWidths=col_w)
    dr_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), PURPLE),
        ("TEXTCOLOR",   (0, 0), (-1, 0), WHITE),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 8),
        ("ALIGN",       (1, 0), (-1, -1), "CENTER"),
        ("ALIGN",       (0, 0), (0, -1), "LEFT"),
        ("ROWPADDING",  (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
        ("GRID",        (0, 0), (-1, -1), 0.4, rl_colors.lightgrey),
    ]))
    story.append(dr_table)

    # ── Study Plan tasks ───────────────────────────────────────────────────────
    if plan and plan.tasks:
        story.append(Spacer(1, 0.4 * cm))
        story.append(Paragraph("Study Plan Schedule", h2))
        story.append(HRFlowable(width="100%", thickness=1, color=PURPLE))
        story.append(Spacer(1, 0.15 * cm))

        sp_header = ["Domain", "Weeks", "Hours", "Priority", "Starting Level"]
        sp_rows   = [sp_header]
        for t in plan.tasks:
            week_str = (f"{t.start_week}–{t.end_week}"
                        if t.start_week != t.end_week else str(t.start_week))
            prio_cell = Paragraph(
                t.priority.title(),
                ParagraphStyle("P2", parent=body,
                               textColor=PRIORITY_COLOUR.get(t.priority, DARK)),
            )
            sp_rows.append([
                t.domain_name.replace("Implement ", "").replace(" Solutions", ""),
                f"Wk {week_str}",
                f"{t.total_hours:.0f} h",
                prio_cell,
                t.knowledge_level.replace("_", " ").title(),
            ])
        _domain_h = sum(t.total_hours for t in plan.tasks)
        _review_h = max(0.0, profile.total_budget_hours - _domain_h)
        sp_rows.append([
            "🏁 Review & Practice Exam",
            f"Wk {plan.review_start_week}",
            f"{_review_h:.0f} h",
            Paragraph("Review", ParagraphStyle("P3", parent=body, textColor=GREEN)),
            "—",
        ])
        sp_rows.append([
            Paragraph("<b>TOTAL</b>", body),
            f"1–{plan.total_weeks}",
            Paragraph(f"<b>{profile.total_budget_hours:.0f} h</b>", body),
            "—", "—",
        ])
        col_w2 = [doc.width * f for f in [0.34, 0.13, 0.12, 0.18, 0.23]]
        sp_table = Table(sp_rows, colWidths=col_w2)
        sp_table.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), PURPLE),
            ("TEXTCOLOR",   (0, 0), (-1, 0), WHITE),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, -1), 8),
            ("ALIGN",       (1, 0), (-1, -1), "CENTER"),
            ("ALIGN",       (0, 0), (0, -1), "LEFT"),
            ("ROWPADDING",  (0, 0), (-1, -1), 5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
            ("GRID",        (0, 0), (-1, -1), 0.4, rl_colors.lightgrey),
        ]))
        story.append(sp_table)

    # ── Learning Path summary ─────────────────────────────────────────────────
    if lp and lp.all_modules:
        story.append(Spacer(1, 0.4 * cm))
        story.append(Paragraph("Curated Learning Path", h2))
        story.append(HRFlowable(width="100%", thickness=1, color=PURPLE))
        story.append(Spacer(1, 0.15 * cm))
        story.append(Paragraph(
            f"<b>{len(lp.all_modules)} modules curated</b> · "
            f"Estimated time: <b>{lp.total_hours_est:.0f} h</b> "
            f"({lp.total_hours_est/max(profile.total_budget_hours,1)*100:.0f}% of budget)",
            body,
        ))
        story.append(Spacer(1, 0.15 * cm))

        lp_header = ["Module", "Duration", "Difficulty", "Type"]
        lp_rows   = [lp_header]
        for m in lp.all_modules[:30]:  # cap at 30 rows
            lp_rows.append([
                Paragraph(m.title, ParagraphStyle("Lp", parent=body, fontSize=7.5)),
                f"{m.duration_min} min",
                m.difficulty.title(),
                m.module_type.replace("-", " ").title(),
            ])
        if len(lp.all_modules) > 30:
            lp_rows.append([f"… and {len(lp.all_modules) - 30} more modules", "", "", ""])

        col_w3 = [doc.width * f for f in [0.52, 0.14, 0.17, 0.17]]
        lp_table = Table(lp_rows, colWidths=col_w3)
        lp_table.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), PURPLE),
            ("TEXTCOLOR",   (0, 0), (-1, 0), WHITE),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, -1), 7.5),
            ("ALIGN",       (1, 0), (-1, -1), "CENTER"),
            ("ALIGN",       (0, 0), (0, -1), "LEFT"),
            ("ROWPADDING",  (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
            ("GRID",        (0, 0), (-1, -1), 0.4, rl_colors.lightgrey),
        ]))
        story.append(lp_table)

    # ── Risk domains callout ──────────────────────────────────────────────────
    if profile.risk_domains:
        story.append(Spacer(1, 0.4 * cm))
        story.append(Paragraph("⚠ Risk Domains — Priority Focus Areas", h2))
        risk_names = [
            d.domain_name for d in profile.domain_profiles
            if d.domain_id in profile.risk_domains
        ]
        story.append(Paragraph(
            "These domains have high exam weight but low current confidence. "
            "Allocate extra study time here first: " +
            ", ".join(r.replace("Implement ", "") for r in risk_names),
            body,
        ))

    # ── Footer ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.6 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=rl_colors.lightgrey))
    story.append(Paragraph(
        f"Generated by <b>Cert Prep Multi-Agent System</b> · Microsoft Agents League · {today}",
        ParagraphStyle("Footer", parent=styles["Normal"],
                       textColor=MUTED, fontSize=7.5, alignment=TA_CENTER),
    ))

    doc.build(story)
    return buf.getvalue()


def generate_assessment_pdf(
    profile: "LearnerProfile",
    snap: "ProgressSnapshot",
    assessment: "ReadinessAssessment",
) -> bytes:
    """
    Build a weekly progress report PDF.
    Returns raw PDF bytes.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors as rl_colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
    )

    styles = getSampleStyleSheet()
    PURPLE = _rl_colour("#5C2D91")
    DARK   = _rl_colour("#1f2937")
    MUTED  = _rl_colour("#6b7280")
    GREEN  = _rl_colour("#107c10")
    RED    = _rl_colour("#d13438")
    AMBER  = _rl_colour("#ca5010")
    BLUE   = _rl_colour("#0078d4")
    WHITE  = rl_colors.white
    LIGHT  = _rl_colour("#f3f4ff")

    h1  = ParagraphStyle("H1", parent=styles["Heading1"],
                          textColor=WHITE, fontSize=16, leading=20, spaceAfter=4)
    h2  = ParagraphStyle("H2", parent=styles["Heading2"],
                          textColor=PURPLE, fontSize=12, leading=15, spaceBefore=12, spaceAfter=4)
    body = ParagraphStyle("Body", parent=styles["Normal"],
                           textColor=DARK, fontSize=9, leading=13)
    small = ParagraphStyle("Small", parent=styles["Normal"],
                            textColor=MUTED, fontSize=8, leading=11)
    centre = ParagraphStyle("Centre", parent=styles["Normal"],
                             textColor=DARK, alignment=TA_CENTER, fontSize=9)

    STATUS_COLOUR = {
        "ahead":    GREEN,
        "on_track": BLUE,
        "behind":   AMBER,
        "critical": RED,
    }
    NUDGE_COLOUR = {
        "danger":  RED,
        "warning": AMBER,
        "info":    BLUE,
        "success": GREEN,
    }

    story = []
    today = date.today().strftime("%B %d, %Y")

    # ── Header banner ─────────────────────────────────────────────────────────
    verdict_hex = assessment.verdict_colour
    banner_data = [[Paragraph(
        f"<b>📊 Weekly Progress Report</b><br/>"
        f"<font size='10'>{profile.student_name} · {profile.exam_target} · {today}</font>",
        h1,
    )]]
    banner_table = Table(banner_data, colWidths=[doc.width])
    banner_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), PURPLE),
        ("ROWPADDING",    (0, 0), (-1, -1), 10),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 0.4 * cm))

    # ── KPI row: Readiness | Go/No-Go | Hours ─────────────────────────────────
    kpi_data = [
        ["Readiness Score", "Exam Decision", "Hours Studied", "Budget Remaining"],
        [
            Paragraph(f"<b><font color='{verdict_hex}'>{assessment.readiness_pct:.0f}%</font></b><br/>"
                      f"<font size='8'>{assessment.verdict_label}</font>", centre),
            Paragraph(f"<b><font color='{assessment.go_nogo_colour}'>{assessment.exam_go_nogo}</font></b>",
                      centre),
            Paragraph(f"<b>{snap.total_hours_spent:.0f} h</b><br/>"
                      f"<font size='8'>of {profile.total_budget_hours:.0f} h "
                      f"({assessment.hours_progress_pct:.0f}%)</font>", centre),
            Paragraph(f"<b>{assessment.hours_remaining:.0f} h</b><br/>"
                      f"<font size='8'>{assessment.weeks_remaining} weeks left</font>", centre),
        ],
    ]
    kpi_w = doc.width / 4
    kpi_table = Table(kpi_data, colWidths=[kpi_w] * 4)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), PURPLE),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ROWPADDING",    (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT]),
        ("GRID",          (0, 0), (-1, -1), 0.5, rl_colors.lightgrey),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 0.15 * cm))
    story.append(Paragraph(f"Exam decision reason: {assessment.go_nogo_reason[:120]}", small))

    # ── Domain status table ────────────────────────────────────────────────────
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Domain Progress", h2))
    story.append(HRFlowable(width="100%", thickness=1, color=PURPLE))
    story.append(Spacer(1, 0.15 * cm))

    ds_header = ["Domain", "Expected", "Your Rating", "Gap", "Status"]
    ds_rows   = [ds_header]
    for ds in assessment.domain_status:
        status_cell = Paragraph(
            ds.status.replace("_", " ").title(),
            ParagraphStyle("DS", parent=body,
                           textColor=STATUS_COLOUR.get(ds.status, DARK)),
        )
        stars = "★" * ds.actual_rating + "☆" * (5 - ds.actual_rating)
        gap_str = f"{ds.gap:+.1f}"
        gap_cell = Paragraph(
            gap_str,
            ParagraphStyle("Gap", parent=body,
                           textColor=GREEN if ds.gap >= 0 else RED),
        )
        ds_rows.append([
            ds.domain_name.replace("Implement ", "").replace(" Solutions", ""),
            f"{ds.expected_rating:.1f}/5",
            f"{stars} ({ds.actual_rating}/5)",
            gap_cell,
            status_cell,
        ])
    col_w4 = [doc.width * f for f in [0.33, 0.12, 0.22, 0.12, 0.21]]
    ds_table = Table(ds_rows, colWidths=col_w4)
    ds_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), PURPLE),
        ("TEXTCOLOR",   (0, 0), (-1, 0), WHITE),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 8),
        ("ALIGN",       (1, 0), (-1, -1), "CENTER"),
        ("ALIGN",       (0, 0), (0, -1), "LEFT"),
        ("ROWPADDING",  (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
        ("GRID",        (0, 0), (-1, -1), 0.4, rl_colors.lightgrey),
    ]))
    story.append(ds_table)

    # ── Nudges ─────────────────────────────────────────────────────────────────
    if assessment.nudges:
        story.append(Spacer(1, 0.4 * cm))
        story.append(Paragraph("🔔 Study Insights & Nudges", h2))
        story.append(HRFlowable(width="100%", thickness=1, color=PURPLE))
        story.append(Spacer(1, 0.15 * cm))
        for n in assessment.nudges[:5]:
            n_colour = NUDGE_COLOUR.get(n.level.value, MUTED)
            clean_msg = n.message.replace("**", "")
            nudge_row = [[Paragraph(
                f"<b>{n.title}</b><br/>"
                f"<font size='8' color='#{hex(int(n_colour.red * 255))[2:].zfill(2)}"
                f"{hex(int(n_colour.green * 255))[2:].zfill(2)}"
                f"{hex(int(n_colour.blue * 255))[2:].zfill(2)}'>"
                f"{clean_msg[:180]}</font>",
                ParagraphStyle("N", parent=body, textColor=DARK),
            )]]
            nudge_table = Table(nudge_row, colWidths=[doc.width])
            nudge_table.setStyle(TableStyle([
                ("BACKGROUND",  (0, 0), (-1, -1), LIGHT),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING",  (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("BOX",         (0, 0), (-1, -1), 0.5, rl_colors.lightgrey),
            ]))
            story.append(nudge_table)
            story.append(Spacer(1, 0.15 * cm))

    # ── Practice exam summary ─────────────────────────────────────────────────
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph("Practice Exam Status", h2))
    pe_done = {"yes": "✓ Completed", "some": "◑ Partially done", "no": "✗ Not yet taken"}.get(
        snap.done_practice_exam, "Unknown"
    )
    pe_score = (f"  ·  Score: {snap.practice_score_pct}%"
                if snap.practice_score_pct is not None else "")
    story.append(Paragraph(f"{pe_done}{pe_score}", body))
    if snap.notes:
        story.append(Paragraph(f"<i>Student notes:</i> {snap.notes[:200]}", small))

    # ── Footer ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.6 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=rl_colors.lightgrey))
    story.append(Paragraph(
        f"Generated by <b>Cert Prep Multi-Agent System</b> · Microsoft Agents League · {today}",
        ParagraphStyle("Footer", parent=styles["Normal"],
                       textColor=MUTED, fontSize=7.5, alignment=TA_CENTER),
    ))

    doc.build(story)
    return buf.getvalue()


# ─── Intake welcome email (HTML body) ────────────────────────────────────────

def generate_intake_summary_html(
    profile: "LearnerProfile",
    plan=None,
    lp=None,
) -> str:
    """
    Returns an HTML email body to send immediately after a learner
    completes the intake form and their study plan is generated.
    """
    today = date.today().strftime("%B %d, %Y")

    domain_rows_html = ""
    # Build weight lookup from registry (DomainProfile has no .exam_weight or .priority)
    from cert_prep.models import get_exam_domains as _get_exam_domains_html
    _wt_lkp = {
        d["id"]: d.get("weight", 0.0)
        for d in _get_exam_domains_html(profile.exam_target)
    }
    for dp in profile.domain_profiles:
        conf_pct = int(dp.confidence_score * 100)
        bar_color = ("#107c10" if conf_pct >= 70 else
                     "#ca5010" if conf_pct >= 40 else "#d13438")
        _wt = _wt_lkp.get(dp.domain_id)
        _wt_str = f"{_wt * 100:.0f}%" if _wt else "—"
        if dp.skip_recommended:
            _prio = "Skip"
        elif dp.confidence_score < 0.30:
            _prio = "Critical"
        elif dp.confidence_score < 0.50:
            _prio = "High"
        elif dp.confidence_score < 0.70:
            _prio = "Medium"
        else:
            _prio = "Low"
        domain_rows_html += f"""
        <tr>
          <td style="padding:6px 10px;border-bottom:1px solid #eee;">
            {dp.domain_name.replace("Implement ", "").replace(" Solutions", "")}
          </td>
          <td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:center;">
            {_wt_str}
          </td>
          <td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:center;">
            <span style="color:{bar_color};font-weight:600;">{conf_pct}%</span>
          </td>
          <td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:center;">
            {_prio}
          </td>
        </tr>"""

    plan_html = ""
    if plan and plan.tasks:
        rows = ""
        for t in plan.tasks:
            w = f"Wk {t.start_week}–{t.end_week}" if t.start_week != t.end_week else f"Wk {t.start_week}"
            rows += f"""
            <tr>
              <td style="padding:5px 8px;border-bottom:1px solid #eee;">
                {t.domain_name.replace("Implement ", "").replace(" Solutions","")}</td>
              <td style="padding:5px 8px;border-bottom:1px solid #eee;text-align:center;">{w}</td>
              <td style="padding:5px 8px;border-bottom:1px solid #eee;text-align:center;">{t.total_hours:.0f} h</td>
              <td style="padding:5px 8px;border-bottom:1px solid #eee;text-align:center;">{t.priority.title()}</td>
            </tr>"""
        plan_html = f"""
        <h3 style="color:#5C2D91;margin:16px 0 8px;">📅 Study Plan Schedule</h3>
        <table style="width:100%;border-collapse:collapse;background:white;
                      border-radius:8px;overflow:hidden;box-shadow:0 2px 6px rgba(0,0,0,0.06);">
          <thead>
            <tr style="background:#5C2D91;color:white;">
              <th style="padding:7px 8px;text-align:left;">Domain</th>
              <th style="padding:7px 8px;text-align:center;">Weeks</th>
              <th style="padding:7px 8px;text-align:center;">Hours</th>
              <th style="padding:7px 8px;text-align:center;">Priority</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>"""

    lp_html = ""
    if lp and lp.all_modules:
        lp_html = f"""
        <div style="margin:16px 0;padding:12px 16px;background:#eef6ff;
                    border-left:4px solid #0078d4;border-radius:6px;">
          <b>📚 Learning Path:</b> {len(lp.all_modules)} curated MS Learn modules ·
          Estimated study time: <b>{lp.total_hours_est:.0f} h</b>
          ({lp.total_hours_est / max(profile.total_budget_hours,1)*100:.0f}% of your budget).
          Open the app to browse all modules with direct links.
        </div>"""

    return textwrap.dedent(f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family:Segoe UI,Arial,sans-serif;max-width:640px;margin:auto;
                 background:#f9f9f9;padding:20px;">
      <div style="background:linear-gradient(135deg,#5C2D91,#B4009E);color:white;
                  padding:20px 24px;border-radius:12px;margin-bottom:20px;">
        <h2 style="margin:0;">🎓 Your Study Plan is Ready!</h2>
        <p style="margin:4px 0 0;opacity:0.85;">
          {profile.student_name} · {profile.exam_target} · {today}
        </p>
      </div>

      <div style="display:flex;gap:12px;margin-bottom:16px;">
        <div style="flex:1;background:white;border-left:4px solid #5C2D91;
                    border-radius:8px;padding:12px 16px;box-shadow:0 2px 6px rgba(0,0,0,0.06);">
          <div style="font-size:0.7rem;color:#888;font-weight:600;text-transform:uppercase;">Study Budget</div>
          <div style="font-size:1.4rem;font-weight:700;color:#5C2D91;">{profile.total_budget_hours:.0f} h</div>
          <div style="font-size:0.8rem;color:#555;">{profile.hours_per_week:.0f} h/wk × {profile.weeks_available} wks</div>
        </div>
        <div style="flex:1;background:white;border-left:4px solid #0078d4;
                    border-radius:8px;padding:12px 16px;box-shadow:0 2px 6px rgba(0,0,0,0.06);">
          <div style="font-size:0.7rem;color:#888;font-weight:600;text-transform:uppercase;">Exam Target</div>
          <div style="font-size:1.1rem;font-weight:700;color:#0078d4;">{profile.exam_target}</div>
          <div style="font-size:0.8rem;color:#555;">{len(profile.domain_profiles)} domains assessed</div>
        </div>
        <div style="flex:1;background:white;border-left:4px solid #107c10;
                    border-radius:8px;padding:12px 16px;box-shadow:0 2px 6px rgba(0,0,0,0.06);">
          <div style="font-size:0.7rem;color:#888;font-weight:600;text-transform:uppercase;">Risk Domains</div>
          <div style="font-size:1.4rem;font-weight:700;color:#107c10;">{len(profile.risk_domains)}</div>
          <div style="font-size:0.8rem;color:#555;">flagged for extra focus</div>
        </div>
      </div>

      <h3 style="color:#5C2D91;margin:16px 0 8px;">📊 Domain Readiness Snapshot</h3>
      <table style="width:100%;border-collapse:collapse;background:white;
                    border-radius:8px;overflow:hidden;box-shadow:0 2px 6px rgba(0,0,0,0.06);">
        <thead>
          <tr style="background:#5C2D91;color:white;">
            <th style="padding:7px 10px;text-align:left;">Domain</th>
            <th style="padding:7px 10px;text-align:center;">Weight</th>
            <th style="padding:7px 10px;text-align:center;">Confidence</th>
            <th style="padding:7px 10px;text-align:center;">Priority</th>
          </tr>
        </thead>
        <tbody>{domain_rows_html}</tbody>
      </table>

      {plan_html}
      {lp_html}

      <div style="margin:20px 0;padding:12px 16px;background:#FFF8E1;
                  border-left:4px solid #F57C00;border-radius:6px;">
        <b>📎 Your full study plan PDF is attached</b> — save it for offline reference.
      </div>

      <p style="margin-top:24px;font-size:0.8rem;color:#888;text-align:center;">
        Generated by <b>Cert Prep Agent</b> · Microsoft Agents League ·
        <a href="http://localhost:8501" style="color:#5C2D91;">Open app</a>
      </p>
    </body>
    </html>
    """).strip()
