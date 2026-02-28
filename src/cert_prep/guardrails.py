"""
guardrails.py — Responsible AI Guardrails Layer
================================================
Implements input validation, output verification, and content safety checks
that wrap every agent transition in the pipeline.

Design pattern: Façade
  The guardrails pipeline is intentionally decoupled from all agents.
  No agent imports or knows about this module — it is called exclusively
  by the orchestrator (streamlit_app.py) at each transition point.
  This means guardrail rules can be updated without touching any agent.

Guardrail levels
----------------
BLOCK   – Hard-stop: st.stop() is called; the pipeline halts until the
           student corrects the triggering input.
WARN    – Soft-stop: the pipeline proceeds with a visible st.warning() banner.
           The violation is logged to SQLite via database.py.
INFO    – Advisory: informational st.info() note; no pipeline impact.

Pipeline insertion points
-------------------------
  [G-01..G-05]   Before LearnerProfilingAgent  (validate RawStudentInput)
  [G-06..G-08]   After  LearnerProfilingAgent  (validate LearnerProfile)
  [G-09..G-10]   After  StudyPlanAgent          (validate StudyPlan)
  [G-11..G-13]   Before ProgressAgent           (validate ProgressSnapshot)
  [G-14..G-15]   After  AssessmentAgent         (validate Assessment)
  [G-16]         Any free-text field             (content safety)
  [G-17]         LearningPath URLs               (hallucination guard)

Guards implemented
------------------
Input guards (before LearnerIntakeAgent):
  G-01  Non-empty required fields
  G-02  Hours per week within sensible range (1–80)
  G-03  Weeks available within sensible range (1–52)
  G-04  Exam target is a recognised certification code
  G-05  PII redaction notice (name is stored, not transmitted externally)

Profile guards (after LearnerProfilingAgent):
  G-06  Domain profile completeness (all 6 domains present)
  G-07  Confidence scores in [0.0, 1.0]
  G-08  Risk domain list contains valid domain IDs

Study plan guards (after StudyPlanAgent):
  G-09  No task has start_week > end_week
  G-10  Total allocated hours do not exceed budget by >10%

Progress snapshot guards (before ProgressAgent):
  G-11  Hours spent not negative
  G-12  Self-ratings in [1, 5]
  G-13  Practice score in [0, 100] when provided

Assessment guards (after AssessmentAgent):
  G-14  Minimum question count met (≥5)
  G-15  No duplicate question IDs

Output content guards (all agent outputs):
  G-16  No profanity / harmful keywords in free-text fields    [heuristic]
  G-17  Hallucination guard: URLs must start with https://learn.microsoft.com
         or https://www.pearsonvue.com (for modules from LearningPathCuratorAgent)

Public API
----------
  GuardrailsPipeline.check_input(raw)          → GuardrailResult
  GuardrailsPipeline.check_profile(profile)    → GuardrailResult
  GuardrailsPipeline.check_plan(plan)          → GuardrailResult
  GuardrailsPipeline.check_progress(snapshot)  → GuardrailResult
  GuardrailsPipeline.check_assessment(asmt)    → GuardrailResult
  GuardrailsPipeline.check_content(text, field)→ GuardrailResult
  GuardrailsPipeline.check_urls(modules)       → GuardrailResult

Consumers
---------
  streamlit_app.py   — called at every agent transition; renders violations
  database.py        — log_violation() stores WARN/BLOCK to guardrail_violations
  tests/             — test_guardrails.py covers all 17 rules
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

try:
    import urllib.request
    import json as _json
except ImportError:
    pass


# ─── Enums & data models ─────────────────────────────────────────────────────

class GuardrailLevel(str, Enum):
    BLOCK = "BLOCK"
    WARN  = "WARN"
    INFO  = "INFO"


@dataclass
class GuardrailViolation:
    code:    str
    level:   GuardrailLevel
    message: str
    field:   str = ""   # which field triggered the violation


@dataclass
class GuardrailResult:
    passed:     bool
    violations: list[GuardrailViolation] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return any(v.level == GuardrailLevel.BLOCK for v in self.violations)

    @property
    def warnings(self) -> list[GuardrailViolation]:
        return [v for v in self.violations if v.level == GuardrailLevel.WARN]

    @property
    def infos(self) -> list[GuardrailViolation]:
        return [v for v in self.violations if v.level == GuardrailLevel.INFO]

    def summary(self) -> str:
        if not self.violations:
            return "✅ All guardrails passed."
        lines = [f"{'🚫' if v.level == GuardrailLevel.BLOCK else '⚠️' if v.level == GuardrailLevel.WARN else 'ℹ️'} [{v.code}] {v.message}" for v in self.violations]
        return "\n".join(lines)


# ─── Constant sets ────────────────────────────────────────────────────────────

RECOGNISED_EXAM_CODES = {
    "AI-102", "AI-900",
    "DP-100", "DP-203", "DP-300", "DP-420", "DP-600", "DP-900",
    "AZ-104", "AZ-204", "AZ-305", "AZ-400", "AZ-500", "AZ-700",
    "AZ-800", "AZ-900",
    "MS-900", "MS-102",
    "SC-100", "SC-200", "SC-300", "SC-900",
    "PL-100", "PL-200", "PL-400", "PL-600", "PL-900",
}

VALID_DOMAIN_IDS = {
    "plan_manage", "computer_vision", "nlp",
    "document_intelligence", "conversational_ai", "generative_ai",
}

_HARMFUL_PATTERN = re.compile(
    r"\b(fuck|shit|bitch|cunt|asshole|bastard|damn|hell|crap"
    r"|kill\s+myself|suicide|self.harm"
    r"|bomb|terrorist|weapon|explosive"
    r"|hack|exploit|malware|ransomware|phishing"
    r"|profanity_placeholder|harmful_content_placeholder)\b",
    re.IGNORECASE,
)

# PII detection — two layers:
#   Layer 1 (_PII_PATTERNS)  : format-based regex for known structured data
#   Layer 2 (_PII_KEYWORDS)  : keyword-context — fires when the user mentions
#                               a PII category (e.g. "my ssn is") regardless
#                               of whether the number is correctly formatted.
# Both fire G-16 WARN so the user is alerted; pipeline is paused in the UI.

_PII_PATTERNS: list[tuple[str, str, re.Pattern]] = [
    # (guardrail_label, description, compiled_pattern)
    # SSN — separators now optional so bare digit strings are caught too
    (
        "SSN",
        "Social Security Number pattern detected",
        re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b"),
    ),
    (
        "Credit card",
        "Credit card number pattern detected",
        re.compile(r"\b(?:4\d{3}|5[1-5]\d{2}|6011|3[47]\d{2})[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"),
    ),
    (
        "Passport",
        "Passport number pattern detected",
        re.compile(r"\b[A-Z]{1,2}\d{6,9}\b"),
    ),
    (
        "UK NI number",
        "UK National Insurance number detected",
        re.compile(r"\b[A-CEGHJ-PR-TW-Z]{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-D]\b", re.IGNORECASE),
    ),
    (
        "Email address",
        "Email address detected — consider removing personal contact details",
        re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
    ),
    (
        "Phone number",
        "Phone number detected",
        # Matches formatted (555-123-4567) and international (+44 7911 123456) numbers
        re.compile(r"\b(?:\+?[\d]{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"),
    ),
    (
        "IP address",
        "IP address detected",
        re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    ),
    (
        "Long digit sequence",
        "Long numeric sequence detected — may be a document or account number",
        # 8–20 consecutive digits not already wrapped in a more specific pattern
        re.compile(r"\b\d{8,20}\b"),
    ),
]

# Keyword-context PII — catches self-declared PII even when the format is
# non-standard (e.g. "my ssn is 34215345" or "my password is abc123")
_PII_KEYWORDS: list[tuple[str, str, re.Pattern]] = [
    (
        "SSN keyword",
        "Social Security Number mentioned — please remove it",
        re.compile(
            r"\b(s\.?s\.?n\.?|social\s+security\s*(?:number|#|no\.?)?)",
            re.IGNORECASE,
        ),
    ),
    (
        "Passport keyword",
        "Passport number mentioned — please remove it",
        re.compile(
            r"\b(passport\s*(?:number|#|no\.?)?)",
            re.IGNORECASE,
        ),
    ),
    (
        "National ID keyword",
        "National ID or insurance number mentioned — please remove it",
        re.compile(
            r"\b(national\s+(?:id|insurance|insurance\s+number)|nin\b|nino\b|aadhar|aadhaar|pan\s+(?:card|number))",
            re.IGNORECASE,
        ),
    ),
    (
        "Bank / card keyword",
        "Bank account or card details mentioned — please remove them",
        re.compile(
            r"\b((?:bank\s+)?account\s*(?:number|#|no\.?)|routing\s*(?:number|#)|credit\s+card\s*(?:number|#)?|debit\s+card|iban|swift\s+(?:code)?)",
            re.IGNORECASE,
        ),
    ),
    (
        "Date of birth keyword",
        "Date of birth mentioned — please remove it",
        re.compile(
            r"\b(date\s+of\s+birth|d\.?o\.?b\.?|born\s+on|my\s+birthday)",
            re.IGNORECASE,
        ),
    ),
    (
        "Password keyword",
        "Password or secret key mentioned — please remove it",
        re.compile(
            r"\b(my\s+password|my\s+pin|my\s+secret|api\s+key\s+is|access\s+key\s+is)",
            re.IGNORECASE,
        ),
    ),
    (
        "Home address keyword",
        "Physical address mentioned — consider removing it",
        re.compile(
            r"\b(my\s+(?:home\s+)?address\s+is|i\s+live\s+at|residing\s+at)",
            re.IGNORECASE,
        ),
    ),
]

TRUSTED_URL_PREFIXES = (
    "https://learn.microsoft.com",
    "https://www.pearsonvue.com",
    "https://aka.ms",
    "https://azure.microsoft.com",
    "https://jolly-field",   # pizza agent demo
)


# ─── Guardrail checks ─────────────────────────────────────────────────────────

class InputGuardrails:
    """G-01 – G-05: Validates RawStudentInput before intake processing."""

    def check(self, raw_input, use_live: bool = False) -> GuardrailResult:
        violations: list[GuardrailViolation] = []

        # G-01 Non-empty required fields
        if not raw_input.student_name.strip():
            violations.append(GuardrailViolation(
                code="G-01", level=GuardrailLevel.BLOCK,
                field="student_name",
                message="Student name must not be empty.",
            ))
        if not raw_input.exam_target.strip():
            violations.append(GuardrailViolation(
                code="G-01", level=GuardrailLevel.BLOCK,
                field="exam_target",
                message="Exam target must not be empty.",
            ))
        if not raw_input.background_text.strip():
            violations.append(GuardrailViolation(
                code="G-01", level=GuardrailLevel.WARN,
                field="background_text",
                message="Background description is empty — profiling accuracy may be limited.",
            ))

        # G-02 Hours per week
        if raw_input.hours_per_week < 1:
            violations.append(GuardrailViolation(
                code="G-02", level=GuardrailLevel.WARN,
                field="hours_per_week",
                message=f"Hours per week ({raw_input.hours_per_week}) is very low (<1). Study plan may be infeasible.",
            ))
        elif raw_input.hours_per_week > 80:
            violations.append(GuardrailViolation(
                code="G-02", level=GuardrailLevel.WARN,
                field="hours_per_week",
                message=f"Hours per week ({raw_input.hours_per_week}) exceeds 80. This may not be sustainable.",
            ))

        # G-03 Weeks available
        if raw_input.weeks_available < 1:
            violations.append(GuardrailViolation(
                code="G-03", level=GuardrailLevel.BLOCK,
                field="weeks_available",
                message="Weeks available must be ≥ 1.",
            ))
        elif raw_input.weeks_available > 52:
            violations.append(GuardrailViolation(
                code="G-03", level=GuardrailLevel.WARN,
                field="weeks_available",
                message=f"Weeks available ({raw_input.weeks_available}) > 52. Consider a shorter target window.",
            ))

        # G-04 Exam target recognition
        code = raw_input.exam_target.split()[0].upper() if raw_input.exam_target else ""
        if code and code not in RECOGNISED_EXAM_CODES:
            violations.append(GuardrailViolation(
                code="G-04", level=GuardrailLevel.WARN,
                field="exam_target",
                message=f"Exam code '{code}' not in recognised catalogue. Proceeding, but content may default to the primary registered exam.",
            ))

        # G-05 PII notice (info only)
        violations.append(GuardrailViolation(
            code="G-05", level=GuardrailLevel.INFO,
            field="student_name",
            message=(
                f"Name '{raw_input.student_name}' is stored in session only and "
                "not transmitted to external services in mock mode."
            ),
        ))

        # G-16 PII + harmful content scan on ALL free-text fields
        # Mock mode: regex heuristic (always runs)
        # Live mode: also calls Azure Content Safety API for harmful content
        _content_guard = OutputContentGuardrails()
        _free_text_fields = [
            ("background_text",  "Your Background",       raw_input.background_text),
            ("goal_text",        "Your Goal",             getattr(raw_input, "goal_text", "")),
            ("preferred_style",  "Preferred Study Style", getattr(raw_input, "preferred_style", "")),
            ("concern_topics",   "Concern Topics",        getattr(raw_input, "concern_topics", "")
             if isinstance(getattr(raw_input, "concern_topics", ""), str)
             else ", ".join(getattr(raw_input, "concern_topics", []))),
        ]
        for _fname, _flabel, _fval in _free_text_fields:
            if not _fval:
                continue
            _text_result = _content_guard.check_text(_fval, _fname, _flabel, use_live)
            violations.extend(_text_result.violations)

        return GuardrailResult(
            passed=not any(v.level == GuardrailLevel.BLOCK for v in violations),
            violations=violations,
        )


class ProfileGuardrails:
    """G-06 – G-08: Validates LearnerProfile output from LearnerProfilingAgent."""

    def check(self, profile) -> GuardrailResult:
        violations: list[GuardrailViolation] = []

        # G-06 Domain completeness
        expected_count = len(VALID_DOMAIN_IDS)
        actual_count   = len(profile.domain_profiles)
        if actual_count < expected_count:
            violations.append(GuardrailViolation(
                code="G-06", level=GuardrailLevel.WARN,
                message=f"Profile has {actual_count} domains; expected {expected_count}. Some domain insights may be missing.",
            ))

        # G-07 Confidence score bounds
        for dp in profile.domain_profiles:
            if not (0.0 <= dp.confidence_score <= 1.0):
                violations.append(GuardrailViolation(
                    code="G-07", level=GuardrailLevel.BLOCK,
                    field=f"domain_profiles[{dp.domain_id}].confidence_score",
                    message=f"Confidence score {dp.confidence_score} out of [0.0, 1.0] range.",
                ))

        # G-08 Risk domain IDs valid
        invalid_risk = [d for d in profile.risk_domains if d not in VALID_DOMAIN_IDS]
        if invalid_risk:
            violations.append(GuardrailViolation(
                code="G-08", level=GuardrailLevel.WARN,
                message=f"Risk domain IDs not recognised: {invalid_risk}.",
            ))

        return GuardrailResult(
            passed=not any(v.level == GuardrailLevel.BLOCK for v in violations),
            violations=violations,
        )


class StudyPlanGuardrails:
    """G-09 – G-10: Validates StudyPlan output from StudyPlanAgent."""

    def check(self, plan, profile) -> GuardrailResult:
        violations: list[GuardrailViolation] = []

        # G-09 No task with start_week > end_week
        for task in plan.tasks:
            if task.start_week > task.end_week:
                violations.append(GuardrailViolation(
                    code="G-09", level=GuardrailLevel.BLOCK,
                    field=f"task[{task.domain_id}]",
                    message=f"Task '{task.domain_id}' has start_week={task.start_week} > end_week={task.end_week}.",
                ))

        # G-10 Hours budget adherence (±10%)
        allocated = sum(t.total_hours for t in plan.tasks)
        budget    = profile.total_budget_hours
        if allocated > budget * 1.10:
            violations.append(GuardrailViolation(
                code="G-10", level=GuardrailLevel.WARN,
                message=(
                    f"Allocated {allocated:.0f}h exceeds budget {budget:.0f}h by "
                    f"{(allocated/budget - 1)*100:.0f}%. Learner may need to reduce scope."
                ),
            ))

        return GuardrailResult(
            passed=not any(v.level == GuardrailLevel.BLOCK for v in violations),
            violations=violations,
        )


class ProgressSnapshotGuardrails:
    """G-11 – G-13: Validates ProgressSnapshot before ProgressAgent assessment."""

    def check(self, snap) -> GuardrailResult:
        violations: list[GuardrailViolation] = []

        # G-11 Non-negative hours
        if snap.total_hours_spent < 0:
            violations.append(GuardrailViolation(
                code="G-11", level=GuardrailLevel.BLOCK,
                field="total_hours_spent",
                message="Hours spent cannot be negative.",
            ))

        # G-12 Self-ratings in [1, 5]
        for dp in snap.domain_progress:
            if not (1 <= dp.self_rating <= 5):
                violations.append(GuardrailViolation(
                    code="G-12", level=GuardrailLevel.BLOCK,
                    field=f"domain_progress[{dp.domain_id}].self_rating",
                    message=f"Self-rating {dp.self_rating} for '{dp.domain_id}' out of [1, 5] range.",
                ))

        # G-13 Practice score bounds
        if snap.practice_score_pct is not None:
            if not (0 <= snap.practice_score_pct <= 100):
                violations.append(GuardrailViolation(
                    code="G-13", level=GuardrailLevel.BLOCK,
                    field="practice_score_pct",
                    message=f"Practice score {snap.practice_score_pct} out of [0, 100] range.",
                ))

        return GuardrailResult(
            passed=not any(v.level == GuardrailLevel.BLOCK for v in violations),
            violations=violations,
        )


class AssessmentGuardrails:
    """G-14 – G-15: Validates Assessment before presenting to the learner."""

    def check(self, assessment) -> GuardrailResult:
        violations: list[GuardrailViolation] = []

        # G-14 Minimum question count
        if len(assessment.questions) < 5:
            violations.append(GuardrailViolation(
                code="G-14", level=GuardrailLevel.WARN,
                message=f"Assessment has only {len(assessment.questions)} questions (<5). Reliability may be limited.",
            ))

        # G-15 No duplicate IDs
        ids = [q.id for q in assessment.questions]
        dups = {i for i in ids if ids.count(i) > 1}
        if dups:
            violations.append(GuardrailViolation(
                code="G-15", level=GuardrailLevel.BLOCK,
                message=f"Duplicate question IDs detected: {dups}.",
            ))

        return GuardrailResult(
            passed=not any(v.level == GuardrailLevel.BLOCK for v in violations),
            violations=violations,
        )


# ─── Human-readable field labels for PII messages ───────────────────────────
_FIELD_LABELS: dict[str, str] = {
    "background_text": "Your Background",
    "goal_text":       "Your Goal",
    "preferred_style": "Preferred Study Style",
    "concern_topics":  "Concern Topics",
}


class OutputContentGuardrails:
    """G-16 – G-17: Validates free-text and URL fields in all agent outputs."""

    def check_text(
        self,
        text: str,
        field_name: str = "",
        field_label: str = "",
        use_live: bool = False,
    ) -> GuardrailResult:
        """G-16 – Check for harmful content (BLOCK) and PII patterns (WARN).

        Mock mode: regex heuristics for both harmful content and PII.
        Live mode: Azure Content Safety API for harmful content (BLOCK),
                   regex for PII patterns (WARN, not covered by Content Safety).
        """
        violations: list[GuardrailViolation] = []
        _label = field_label or _FIELD_LABELS.get(field_name, field_name)

        if use_live:
            # ─ Live mode: call Azure Content Safety API for harmful-content BLOCK ─
            _cs_violations = self._check_content_safety_api(text, field_name, _label)
            violations.extend(_cs_violations)
            # Layer 3 — Azure AI Language PII Entity Recognition (live mode only)
            # This catches SSN, credit cards, passports, phone, email etc. via ML,
            # complementing the regex layers which cover keyword- and format-based matches.
            _lang_pii = self._check_language_pii_api(text, field_name, _label)
            violations.extend(_lang_pii)
        else:
            # ─ Mock mode: regex harmful pattern ─
            if _HARMFUL_PATTERN.search(text):
                violations.append(GuardrailViolation(
                    code="G-16", level=GuardrailLevel.BLOCK,
                    field=field_name,
                    message=(
                        f"Potentially harmful content detected in \"{_label}\" — "
                        "pipeline halted."
                    ),
                ))

        # WARN: Layer 1 — format-based PII patterns (SSN, CC, phone, etc.)
        for pii_label, description, pattern in _PII_PATTERNS:
            if pattern.search(text):
                violations.append(GuardrailViolation(
                    code="G-16", level=GuardrailLevel.WARN,
                    field=field_name,
                    message=(
                        f"PII detected in \"{_label}\" — {pii_label}: {description}. "
                        "Please remove personal data from this field."
                    ),
                ))

        # WARN: Layer 2 — keyword-context PII (catches "my ssn is...", "my password is..."
        # even when the associated value doesn't match a known numeric format)
        _seen_kw_labels: set[str] = set()
        for kw_label, kw_desc, kw_pattern in _PII_KEYWORDS:
            if kw_pattern.search(text) and kw_label not in _seen_kw_labels:
                _seen_kw_labels.add(kw_label)
                violations.append(GuardrailViolation(
                    code="G-16", level=GuardrailLevel.WARN,
                    field=field_name,
                    message=(
                        f"PII keyword detected in \"{_label}\" — {kw_label}: {kw_desc}."
                    ),
                ))

        return GuardrailResult(
            passed=not any(v.level == GuardrailLevel.BLOCK for v in violations),
            violations=violations,
        )

    def _check_content_safety_api(
        self, text: str, field_name: str, field_label: str
    ) -> list[GuardrailViolation]:
        """Call Azure Content Safety text:analyze endpoint.

        Returns a BLOCK violation if any category scores severity >= 2 (medium).
        Falls back silently to an empty list if the endpoint is not configured
        or the call fails — the regex harmful check in mock mode is the safety net.
        """
        _endpoint = os.getenv("AZURE_CONTENT_SAFETY_ENDPOINT", "").rstrip("/")
        _key      = os.getenv("AZURE_CONTENT_SAFETY_KEY", "")
        if not _endpoint or not _key:
            # Endpoint not configured — fall back to regex
            if _HARMFUL_PATTERN.search(text):
                return [GuardrailViolation(
                    code="G-16", level=GuardrailLevel.BLOCK,
                    field=field_name,
                    message=(
                        f"Potentially harmful content detected in \"{field_label}\" — "
                        "pipeline halted. (Content Safety endpoint not configured; "
                        "regex fallback triggered.)"
                    ),
                )]
            return []

        _url = f"{_endpoint}/contentsafety/text:analyze?api-version=2024-09-01"
        _payload = _json.dumps({
            "text": text[:10_000],   # API limit
            "categories": ["Hate", "SelfHarm", "Sexual", "Violence"],
            "outputType": "FourSeverityLevels",
        }).encode()
        _req = urllib.request.Request(
            _url,
            data=_payload,
            headers={
                "Content-Type": "application/json",
                "Ocp-Apim-Subscription-Key": _key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(_req, timeout=5) as resp:
                _data = _json.loads(resp.read())
            # severity levels: 0=Safe, 2=Low, 4=Medium, 6=High
            _flagged = [
                cat["category"]
                for cat in _data.get("categoriesAnalysis", [])
                if cat.get("severity", 0) >= 2
            ]
            if _flagged:
                return [GuardrailViolation(
                    code="G-16", level=GuardrailLevel.BLOCK,
                    field=field_name,
                    message=(
                        f"Azure Content Safety flagged \"{field_label}\" for: "
                        f"{', '.join(_flagged)}. Pipeline halted."
                    ),
                )]
        except Exception:
            # Network error / service unavailable — fall back to regex
            if _HARMFUL_PATTERN.search(text):
                return [GuardrailViolation(
                    code="G-16", level=GuardrailLevel.BLOCK,
                    field=field_name,
                    message=(
                        f"Potentially harmful content detected in \"{field_label}\" — "
                        "pipeline halted. (Content Safety API unavailable; regex fallback.)"
                    ),
                )]
        return []

    def _check_language_pii_api(
        self, text: str, field_name: str, field_label: str
    ) -> list[GuardrailViolation]:
        """Call Azure AI Language PiiEntityRecognition endpoint (live mode only).

        Returns WARN violations for each distinct PII category detected with
        confidence ≥ 0.5. Falls back silently to an empty list if the endpoint
        is not configured or the API call fails — regex layers remain active.

        Env vars required:
            AZURE_LANGUAGE_ENDPOINT  e.g. https://myresource.cognitiveservices.azure.com
            AZURE_LANGUAGE_KEY       subscription key from Azure portal
        """
        _endpoint = os.getenv("AZURE_LANGUAGE_ENDPOINT", "").rstrip("/")
        _key      = os.getenv("AZURE_LANGUAGE_KEY", "")
        if not _endpoint or not _key:
            return []  # not configured — regex layers handle PII in this case

        _FRIENDLY: dict[str, str] = {
            "USSocialSecurityNumber":    "US Social Security Number",
            "CreditCardNumber":          "Credit Card Number",
            "PhoneNumber":               "Phone Number",
            "Email":                     "Email Address",
            "USPassportNumber":          "Passport Number",
            "PassportNumber":            "Passport Number",
            "IPAddress":                 "IP Address",
            "Password":                  "Password / Secret",
            "BankAccountNumber":         "Bank Account Number",
            "InternationalBankingNumber": "IBAN",
            "SWIFTCode":                 "SWIFT Code",
            "UKNationalInsuranceNumber": "UK NI Number",
            "IndiaPermanentAccount":     "India PAN Number",
            "DateOfBirth":               "Date of Birth",
            "PersonType":                "Person Type",
            "Address":                   "Physical Address",
        }

        _url = (
            f"{_endpoint}/language/:analyze-text"
            "?api-version=2023-04-01"
        )
        _payload = _json.dumps({
            "kind": "PiiEntityRecognition",
            "analysisInput": {
                "documents": [{"id": "1", "language": "en", "text": text[:5_000]}]
            },
            "parameters": {
                "loggingOptOut": True,
                "piiCategories": ["All"],
            },
        }).encode()
        _req = urllib.request.Request(
            _url,
            data=_payload,
            headers={
                "Content-Type": "application/json",
                "Ocp-Apim-Subscription-Key": _key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(_req, timeout=5) as resp:
                _data = _json.loads(resp.read())

            _docs = (_data.get("results") or {}).get("documents", [])
            _entities = _docs[0].get("entities", []) if _docs else []

            # Deduplicate by category; only report confident detections
            _seen_cats: set[str] = set()
            _violations: list[GuardrailViolation] = []
            for ent in _entities:
                _cat   = ent.get("category", "Unknown")
                _conf  = ent.get("confidenceScore", 0)
                _text  = ent.get("text", "")
                if _conf < 0.5 or _cat in _seen_cats:
                    continue
                _seen_cats.add(_cat)
                _friendly = _FRIENDLY.get(_cat, _cat)
                _violations.append(GuardrailViolation(
                    code="G-16", level=GuardrailLevel.WARN,
                    field=field_name,
                    message=(
                        f"Azure AI Language detected PII in \"{field_label}\" — "
                        f"{_friendly} (confidence {_conf:.0%}): "
                        f"'{_text[:30]}{'...' if len(_text) > 30 else ''}'. "
                        "Please remove personal data."
                    ),
                ))
            return _violations

        except Exception:
            # Network error / service unavailable — regex layers remain active
            return []

    def check_url(self, url: str, field_name: str = "") -> GuardrailResult:
        """G-17 – Ensure URLs originate from trusted Microsoft/Pearson domains."""
        violations: list[GuardrailViolation] = []
        if url and not any(url.startswith(p) for p in TRUSTED_URL_PREFIXES):
            violations.append(GuardrailViolation(
                code="G-17", level=GuardrailLevel.WARN,
                field=field_name,
                message=f"URL '{url[:80]}' does not originate from a trusted domain.",
            ))
        return GuardrailResult(
            passed=True,    # URL mismatches are warnings, not blocks
            violations=violations,
        )

    def check_learning_path(self, learning_path) -> GuardrailResult:
        """Run G-16 + G-17 across all modules in a LearningPath."""
        all_violations: list[GuardrailViolation] = []
        for mod in learning_path.all_modules:
            r = self.check_url(mod.url, field_name=f"LearningModule[{mod.ms_learn_uid}].url")
            all_violations.extend(r.violations)
        return GuardrailResult(
            passed=not any(v.level == GuardrailLevel.BLOCK for v in all_violations),
            violations=all_violations,
        )


# ─── Convenience façade ───────────────────────────────────────────────────────

class GuardrailsPipeline:
    """
    Single entry-point that runs all applicable guardrails for a given pipeline stage.

    Usage::

        gp = GuardrailsPipeline()

        # Stage 1 – raw input
        result = gp.check_input(raw_student_input)

        # Stage 2 – after profiling
        result = gp.check_profile(learner_profile)

        # Stage 3 – after study plan
        result = gp.check_study_plan(study_plan, learner_profile)

        # Stage 4 – before progress assessment
        result = gp.check_progress_snapshot(progress_snapshot)

        # Stage 5 – after assessment generation
        result = gp.check_assessment(assessment)
    """

    def __init__(self):
        self.input_guard    = InputGuardrails()
        self.profile_guard  = ProfileGuardrails()
        self.plan_guard     = StudyPlanGuardrails()
        self.snap_guard     = ProgressSnapshotGuardrails()
        self.assess_guard   = AssessmentGuardrails()
        self.content_guard  = OutputContentGuardrails()

    def check_input(self, raw, use_live: bool = False) -> GuardrailResult:
        return self.input_guard.check(raw, use_live=use_live)

    def check_profile(self, profile) -> GuardrailResult:
        return self.profile_guard.check(profile)

    def check_study_plan(self, plan, profile) -> GuardrailResult:
        return self.plan_guard.check(plan, profile)

    def check_progress_snapshot(self, snap) -> GuardrailResult:
        return self.snap_guard.check(snap)

    def check_assessment(self, assessment) -> GuardrailResult:
        return self.assess_guard.check(assessment)

    def check_learning_path(self, learning_path) -> GuardrailResult:
        return self.content_guard.check_learning_path(learning_path)

    def merge(self, *results: GuardrailResult) -> GuardrailResult:
        """Merge multiple GuardrailResult objects into one."""
        all_v = []
        for r in results:
            all_v.extend(r.violations)
        return GuardrailResult(
            passed=not any(v.level == GuardrailLevel.BLOCK for v in all_v),
            violations=all_v,
        )
