"""
b3_cert_recommendation_agent.py — Certification Recommendation Agent (Block 3)
===============================================================================
Terminal agent in the pipeline.  After the learner passes (or fails) the
readiness assessment, this agent produces a structured CertRecommendation
with exam logistics, a next-cert progression path, and — when the learner
is not yet ready — a targeted remediation plan.

---------------------------------------------------------------------------
Agent: CertificationRecommendationAgent
---------------------------------------------------------------------------
  Input:   AssessmentResult + LearnerProfile
  Output:  CertRecommendation
  Pattern: Decision Tree Planner

  Branching logic:
    score ≥ 70%  → ready_to_book = True
                   Returns booking checklist, ExamInfo, next-cert suggestion.
    score < 70%  → ready_to_book = False
                   Returns per-domain remediation steps, suggested re-attempt
                   timeline, and the weakest domains to re-study.

  Next-cert progression (SYNERGY_MAP):
    AI-102 → AZ-204   DP-100 → AI-102   AZ-204 → AZ-305
    AI-900 → AI-102   AZ-305 → AZ-400   AZ-900 → AI-102
    (default fallback → AZ-305 for unrecognised exam codes)

---------------------------------------------------------------------------
Data models defined in this file
---------------------------------------------------------------------------
  ExamInfo            Logistics: exam code, passing score, format, scheduling URL
  NextCertSuggestion  Suggested follow-on certification with rationale
  CertRecommendation  Full recommendation: ready_to_book, exam_info,
                      next_cert_suggestions, remediation_plan, summary

---------------------------------------------------------------------------
Architecture role
---------------------------------------------------------------------------
  AssessmentAgent (B2) → CertificationRecommendationAgent (B3)
                           → (optional) ExamPlannerAgent / booking flow

---------------------------------------------------------------------------
Consumers
---------------------------------------------------------------------------
  streamlit_app.py   — Tab 6: renders exam logistics, booking checklist,
                       next-cert roadmap, or remediation plan
  database.py        — save_cert_recommendation() persists rec JSON
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ─── Data models ─────────────────────────────────────────────────────────────

@dataclass
class ExamInfo:
    """Logistics for the target Microsoft certification exam."""
    exam_code:          str
    exam_name:          str
    passing_score:      int     = 700   # Microsoft uses 1000-point scale; ~700 to pass
    question_count:     str     = "40–60"
    duration_minutes:   int     = 100
    languages:          list    = field(default_factory=lambda: ["English"])
    scheduling_url:     str     = "https://www.pearsonvue.com/microsoft"
    exam_format:        str     = "Multiple choice, drag-and-drop, case studies"
    online_proctored:   bool    = True
    cost_usd:           int     = 165
    free_practice_url:  str     = "https://learn.microsoft.com/en-us/certifications/practice-assessments-for-microsoft-certifications"


@dataclass
class NextCertSuggestion:
    """A suggested next certification to pursue after the current target."""
    exam_code:    str
    exam_name:    str
    rationale:    str
    difficulty:   str    = "intermediate"    # foundational | intermediate | advanced | expert
    learn_url:    str    = ""
    timeline_est: str    = ""    # e.g. "3–6 months"


@dataclass
class CertRecommendation:
    """Output of the CertificationRecommendationAgent."""
    student_name:           str
    target_exam:            str
    go_for_exam:            bool
    confidence_label:       str    = ""     # "High", "Medium", "Low"
    exam_info:              Optional[ExamInfo] = None
    next_cert_suggestions:  list   = field(default_factory=list)   # list[NextCertSuggestion]
    remediation_plan:       Optional[str] = None
    booking_checklist:      list   = field(default_factory=list)
    summary:                str    = ""


# ─── Exam catalogue ──────────────────────────────────────────────────────────

_EXAM_CATALOGUE: dict[str, ExamInfo] = {
    "AI-102": ExamInfo(
        exam_code="AI-102",
        exam_name="Designing and Implementing a Microsoft Azure AI Solution",
        passing_score=700,
        question_count="40–60",
        duration_minutes=100,
        cost_usd=165,
        free_practice_url=(
            "https://learn.microsoft.com/credentials/certifications/practice/assessment?assessmentId=61&assessment-type=practice"
        ),
    ),
    "DP-100": ExamInfo(
        exam_code="DP-100",
        exam_name="Designing and Implementing a Data Science Solution on Azure",
        passing_score=700,
        question_count="40–60",
        duration_minutes=100,
        cost_usd=165,
    ),
    "AZ-204": ExamInfo(
        exam_code="AZ-204",
        exam_name="Developing Solutions for Microsoft Azure",
        passing_score=700,
        question_count="40–60",
        duration_minutes=130,
        cost_usd=165,
    ),
    "AZ-305": ExamInfo(
        exam_code="AZ-305",
        exam_name="Designing Microsoft Azure Infrastructure Solutions",
        passing_score=700,
        question_count="40–60",
        duration_minutes=120,
        cost_usd=165,
    ),
}

# Next-cert paths keyed by current cert
_NEXT_CERT_MAP: dict[str, list[dict]] = {
    "AI-102": [
        {
            "code": "DP-100",
            "name": "Azure Data Scientist Associate",
            "rationale": (
                "Extends your AI skills into ML model training, Azure ML pipelines, "
                "and MLOps — the natural next step for an Azure AI Engineer."
            ),
            "difficulty": "intermediate",
            "learn_url": "https://learn.microsoft.com/certifications/azure-data-scientist/",
            "timeline": "3–5 months",
        },
        {
            "code": "AZ-305",
            "name": "Azure Solutions Architect Expert",
            "rationale": (
                "Broadens your scope to full Azure architecture — valuable if you want "
                "to design end-to-end AI-powered solutions at scale."
            ),
            "difficulty": "expert",
            "learn_url": "https://learn.microsoft.com/certifications/azure-solutions-architect/",
            "timeline": "4–6 months",
        },
        {
            "code": "AI-900",
            "name": "Azure AI Fundamentals",
            "rationale": (
                "If you haven't already, AI-900 is a quick confidence-booster that "
                "validates your foundational AI knowledge with Microsoft."
            ),
            "difficulty": "foundational",
            "learn_url": "https://learn.microsoft.com/certifications/azure-ai-fundamentals/",
            "timeline": "2–4 weeks",
        },
    ],
    "DP-100": [
        {
            "code": "AI-102",
            "name": "Azure AI Engineer Associate",
            "rationale": (
                "Complements DP-100 by covering Azure AI services (Vision, Language, "
                "Speech, Bot) — together they make a comprehensive AI stack."
            ),
            "difficulty": "intermediate",
            "learn_url": "https://learn.microsoft.com/certifications/azure-ai-engineer/",
            "timeline": "3–5 months",
        },
    ],
    "AZ-204": [
        {
            "code": "AI-102",
            "name": "Azure AI Engineer Associate",
            "rationale": (
                "Your AZ-204 SDK knowledge transfers directly to AI-102 — you already "
                "understand REST calls and Azure resource management."
            ),
            "difficulty": "intermediate",
            "learn_url": "https://learn.microsoft.com/certifications/azure-ai-engineer/",
            "timeline": "2–4 months",
        },
    ],
}

# Booking checklist items
_BOOKING_CHECKLIST = [
    "Review the official AI-102 exam skills outline at learn.microsoft.com",
    "Complete the free official practice assessment (link above) within the last 2 weeks",
    "Score ≥ 700/1000 on at least one timed practice test",
    "Reserve your exam slot ≥ 3 days ahead at Pearson VUE (online or test centre)",
    "Prepare valid government-issued photo ID",
    "Ensure stable internet + webcam if taking online-proctored exam",
    "Join the Microsoft Learn Study Hall Discord for last-minute Q&A",
]


class CertificationRecommendationAgent:
    """
    Block 3 — Certification Recommendation Agent.

    Decides whether to recommend immediate exam scheduling or a remediation loop,
    then suggests a next-step certification path.

    Usage::

        agent = CertificationRecommendationAgent()
        rec   = agent.recommend(profile, assessment_result)
        # or without an assessment:
        rec   = agent.recommend_from_readiness(profile, readiness_assessment)
    """

    GO_THRESHOLD_PCT    = 70.0    # assessment score ≥ 70 → go
    STRONG_GO_THRESHOLD = 85.0

    def recommend(self, profile, assessment_result) -> CertRecommendation:
        """Recommend based on AssessmentResult (quiz scores)."""
        score = assessment_result.score_pct
        go    = score >= self.GO_THRESHOLD_PCT

        if score >= self.STRONG_GO_THRESHOLD:
            confidence = "High"
        elif score >= self.GO_THRESHOLD_PCT:
            confidence = "Medium"
        else:
            confidence = "Low"

        target_code = profile.exam_target.split()[0].upper()  # e.g. "AI-102"
        exam_info   = _EXAM_CATALOGUE.get(target_code)
        next_certs  = self._build_next_certs(target_code)

        remediation = None
        if not go:
            remediation = (
                f"You scored {score:.0f}%. "
                f"Recommended remediation: {assessment_result.recommendation}\n\n"
                "Suggested cycle: 2–3 more weeks of targeted study → retake assessment."
            )

        summary = (
            f"{profile.student_name} scored **{score:.0f}%** on the readiness quiz. "
            + ("✅ Ready to book the exam!" if go
               else "❌ Remediation recommended before booking.")
        )

        return CertRecommendation(
            student_name=profile.student_name,
            target_exam=target_code,
            go_for_exam=go,
            confidence_label=confidence,
            exam_info=exam_info,
            next_cert_suggestions=next_certs,
            remediation_plan=remediation,
            booking_checklist=_BOOKING_CHECKLIST if go else [],
            summary=summary,
        )

    def recommend_from_readiness(self, profile, readiness_assessment) -> CertRecommendation:
        """Recommend based on ProgressAgent ReadinessAssessment (self-reported)."""
        verdict = readiness_assessment.exam_go_nogo
        score   = readiness_assessment.readiness_pct

        go = verdict in ("GO", "CONDITIONAL GO")
        confidence = "High" if score >= 80 else ("Medium" if score >= 65 else "Low")

        target_code = profile.exam_target.split()[0].upper()
        exam_info   = _EXAM_CATALOGUE.get(target_code)
        next_certs  = self._build_next_certs(target_code)

        remediation = None
        if not go:
            weak = [
                s.domain_name for s in readiness_assessment.domain_status
                if s.status in ("behind", "critical")
            ]
            remediation = (
                f"Overall readiness: {score:.0f}% ({verdict}). "
                f"Focus areas: {', '.join(weak) if weak else 'general study'}."
            )

        summary = (
            f"{profile.student_name} — readiness {score:.0f}% → "
            + ("Schedule the exam! 🎉" if go else "More prep needed 📖")
        )

        return CertRecommendation(
            student_name=profile.student_name,
            target_exam=target_code,
            go_for_exam=go,
            confidence_label=confidence,
            exam_info=exam_info,
            next_cert_suggestions=next_certs,
            remediation_plan=remediation,
            booking_checklist=_BOOKING_CHECKLIST if go else [],
            summary=summary,
        )

    # ── private helpers ───────────────────────────────────────────────────────

    def _build_next_certs(self, target_code: str) -> list[NextCertSuggestion]:
        raw = _NEXT_CERT_MAP.get(target_code, [])
        return [
            NextCertSuggestion(
                exam_code=r["code"],
                exam_name=r["name"],
                rationale=r["rationale"],
                difficulty=r["difficulty"],
                learn_url=r.get("learn_url", ""),
                timeline_est=r.get("timeline", ""),
            )
            for r in raw
        ]
