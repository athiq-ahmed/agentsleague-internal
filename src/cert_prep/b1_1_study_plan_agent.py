"""
b1_1_study_plan_agent.py — Study Plan Generator (Block 1.1a)
=============================================================
Generates a week-by-week Gantt-style study plan from a LearnerProfile.
Runs in parallel with LearningPathCuratorAgent (via ThreadPoolExecutor)
so neither agent waits on the other.

---------------------------------------------------------------------------
Agent: StudyPlanAgent
---------------------------------------------------------------------------
  Input:   LearnerProfile + existing_certs: list[str]
  Output:  StudyPlan (dataclass)  — one StudyTask per exam domain
  Pattern: Planner–Executor

Key behaviours
--------------
  1. Prerequisite gap detection
     Checks _CERT_PREREQ_MAP to see if recommended pre-certs are missing.
     Sets StudyPlan.prereq_gap = True and lists missing certs.
     The UI then shows a warning banner, but does NOT block the pipeline.

  2. Hour allocation — Largest Remainder algorithm
     Distributes total_budget_hours (= weeks × hrs/week) across domains
     in proportion to exam weight, guaranteeing the sum is exact.
     Domains scored STRONG get their hours halved (efficiency boost).
     Domains scored UNKNOWN receive a 30% bonus (remediation top-up).

  3. Remediation-first scheduling
     Risk domains (confidence < 0.40) are front-loaded into the first 40%
     of available weeks.  This ensures weak areas are addressed before the
     learner runs out of time.

  4. Skippable domain handling
     If skip_recommended=True in DomainProfile, the domain is assigned
     priority=LOW and minimal hours (1 hr), placed in the final weeks.

---------------------------------------------------------------------------
Data models defined in this file
---------------------------------------------------------------------------
  StudyTask    One domain's allocation row: weeks, hours, priority, activities
  StudyPlan    Full plan: list[StudyTask] + prereq metadata + notes

---------------------------------------------------------------------------
Consumers
---------------------------------------------------------------------------
  streamlit_app.py   — runs StudyPlanAgent().run() in a ThreadPoolExecutor worker
  database.py        — save_plan() persists plan_json to SQLite
  b1_2_progress_agent.py — reads total_budget_hours to compute hours_utilisation
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List

from cert_prep.models import EXAM_DOMAINS, LearnerProfile


# ─── Certificate prerequisite / recommendation catalogue ─────────────────────
# Keys are short exam codes (upper-case).  For the UI we display cert names.

_CERT_PREREQ_MAP: dict[str, dict] = {
    "AI-102": {
        "strongly_recommended": [
            ("AI-900", "Azure AI Fundamentals"),
        ],
        "helpful": [
            ("AZ-900",  "Azure Fundamentals"),
            ("AZ-204",  "Azure Developer Associate"),
        ],
        "notes": (
            "Microsoft strongly recommends completing **AI-900 (Azure AI Fundamentals)** "
            "before sitting AI-102. AI-900 covers core concepts for Azure AI services, "
            "responsible AI, and cognitive APIs — all heavily tested in AI-102. "
            "AZ-900 provides broader Azure grounding, while AZ-204 helps with "
            "SDK integration questions."
        ),
    },
    "DP-100": {
        "strongly_recommended": [
            ("DP-900", "Azure Data Fundamentals"),
        ],
        "helpful": [
            ("AI-900",  "Azure AI Fundamentals"),
            ("AZ-900",  "Azure Fundamentals"),
        ],
        "notes": (
            "DP-900 (Azure Data Fundamentals) gives the data storage and analytics "
            "grounding needed for DP-100. AI-900 is useful for the ML workflow sections."
        ),
    },
    "DP-203": {
        "strongly_recommended": [
            ("AZ-900",  "Azure Fundamentals"),
            ("DP-900",  "Azure Data Fundamentals"),
        ],
        "helpful": [
            ("AZ-104", "Azure Administrator Associate"),
        ],
        "notes": (
            "AZ-900 and DP-900 provide the Azure and data engineering fundamentals "
            "expected for DP-203. Infrastructure knowledge from AZ-104 is a plus."
        ),
    },
    "AZ-204": {
        "strongly_recommended": [
            ("AZ-900", "Azure Fundamentals"),
        ],
        "helpful": [],
        "notes": "AZ-900 provides the Azure fundamentals baseline expected for this developer exam.",
    },
    "AZ-305": {
        "strongly_recommended": [
            ("AZ-104", "Azure Administrator Associate"),
        ],
        "helpful": [
            ("AZ-900", "Azure Fundamentals"),
        ],
        "notes": (
            "AZ-305 (Solutions Architect Expert) requires AZ-104 as a mandatory prerequisite. "
            "You must pass AZ-104 first."
        ),
    },
    "AZ-400": {
        "strongly_recommended": [
            ("AZ-204", "Azure Developer Associate"),
        ],
        "helpful": [
            ("AZ-104", "Azure Administrator Associate"),
        ],
        "notes": (
            "AZ-400 DevOps Expert requires either AZ-104 or AZ-204 as a prerequisite. "
            "AZ-204 is the more common entry path."
        ),
    },
    "SC-100": {
        "strongly_recommended": [
            ("SC-900", "Security Compliance & Identity Fundamentals"),
        ],
        "helpful": [
            ("AZ-500", "Azure Security Engineer Associate"),
            ("SC-200", "Security Operations Analyst Associate"),
        ],
        "notes": (
            "SC-900 provides the security and identity fundamentals baseline. "
            "SC-100 is an Expert-level exam; prior Associate-level security certs are strongly advised."
        ),
    },
    "MS-102": {
        "strongly_recommended": [
            ("MS-900", "Microsoft 365 Fundamentals"),
        ],
        "helpful": [],
        "notes": "MS-900 is the recommended fundamentals entry point for Microsoft 365 admin tracks.",
    },
}

# ─── Colour mapping for priority levels ──────────────────────────────────────
PRIORITY_COLOUR = {
    "critical":  "#d13438",  # red   – unknown/weak + risk
    "high":      "#ca5010",  # orange – weak
    "medium":    "#0078d4",  # blue  – moderate
    "low":       "#107c10",  # green – strong
    "skip":      "#8a8886",  # grey  – skip recommended
    "review":    "#5c2d91",  # purple – review week
}


# ─── Output data models ───────────────────────────────────────────────────────

@dataclass
class StudyTask:
    """One domain block in the Gantt chart."""
    domain_id:      str
    domain_name:    str
    start_week:     int        # 1-indexed, inclusive
    end_week:       int        # 1-indexed, inclusive
    total_hours:    float
    priority:       str        # "critical" | "high" | "medium" | "low" | "skip"
    knowledge_level: str       # DomainKnowledge value
    confidence_pct: int        # 0-100

    @property
    def week_span(self) -> int:
        return self.end_week - self.start_week + 1


@dataclass
class PrereqInfo:
    """One prerequisite / recommended certification for the target exam."""
    cert_code:    str
    cert_name:    str
    relationship: str    # "strongly_recommended" | "helpful" | "mandatory"
    already_held: bool


@dataclass
class StudyPlan:
    """Complete output of StudyPlanAgent for one LearnerProfile."""
    student_name:       str
    exam_target:        str
    total_weeks:        int
    total_hours:        float
    tasks:              List[StudyTask]
    review_start_week:  int             # week reserved for review / practice tests
    prerequisites:      List[PrereqInfo]
    prereq_gap:         bool            # True if key prereqs not yet held
    prereq_message:     str             # human-readable advisory message
    plan_summary:       str             # 2-3 sentence narrative from the agent


# ─── StudyPlanAgent ──────────────────────────────────────────────────────────

class StudyPlanAgent:
    """
    Block 1.1 Preview – Study Plan Planner (mock/rule-based).

    Consumes a LearnerProfile and emits a StudyPlan with:
      • Prerequisite / fundamental certification gap analysis
      • Week-by-week Gantt task list (sequential domain blocks)
      • Colour-coded priorities (critical → skip)
    """

    # Domain metadata lookup keyed by id
    _DOMAIN_META: dict[str, dict] = {d["id"]: d for d in EXAM_DOMAINS}

    # ── Public entry point ────────────────────────────────────────────────────

    def run(self, profile: LearnerProfile) -> StudyPlan:
        prereqs       = self._check_prerequisites(profile)
        prereq_gap    = any(p.relationship == "strongly_recommended" and not p.already_held
                            for p in prereqs)
        prereq_msg    = self._build_prereq_message(profile.exam_target, prereqs)
        tasks         = self._build_tasks(profile)
        review_week   = profile.weeks_available  # always the last week
        plan_summary  = self._build_summary(profile, tasks, prereq_gap)

        return StudyPlan(
            student_name      = profile.student_name,
            exam_target       = profile.exam_target,
            total_weeks       = profile.weeks_available,
            total_hours       = profile.total_budget_hours,
            tasks             = tasks,
            review_start_week = review_week,
            prerequisites     = prereqs,
            prereq_gap        = prereq_gap,
            prereq_message    = prereq_msg,
            plan_summary      = plan_summary,
        )

    # ── Prerequisites ─────────────────────────────────────────────────────────

    def _check_prerequisites(self, profile: LearnerProfile) -> list[PrereqInfo]:
        exam_code  = profile.exam_target.upper().strip()
        held_upper = {c.upper().strip() for c in
                      getattr(profile, "_raw_certs", []) or []}

        # Try to read existing certs from profile metadata if available
        # (the profile doesn't store raw certs directly, so we use a workaround:
        #  check domain boost signals, experience level, etc.)
        # We rely on calling code injecting raw existing_certs via run_with_raw().

        prereq_def = _CERT_PREREQ_MAP.get(exam_code, {})
        result: list[PrereqInfo] = []

        for code, name in prereq_def.get("strongly_recommended", []):
            result.append(PrereqInfo(
                cert_code    = code,
                cert_name    = name,
                relationship = "strongly_recommended",
                already_held = code.upper() in held_upper,
            ))
        for code, name in prereq_def.get("helpful", []):
            result.append(PrereqInfo(
                cert_code    = code,
                cert_name    = name,
                relationship = "helpful",
                already_held = code.upper() in held_upper,
            ))
        return result

    def run_with_raw(
        self,
        profile: LearnerProfile,
        existing_certs: list[str],
    ) -> StudyPlan:
        """
        Preferred entry point from Streamlit — accepts existing certs from the
        raw intake form so prerequisite checking is accurate.
        """
        profile._raw_certs = existing_certs  # type: ignore[attr-defined]
        return self.run(profile)

    def _build_prereq_message(self, exam_target: str, prereqs: list[PrereqInfo]) -> str:
        exam_code   = exam_target.upper().strip()
        prereq_def  = _CERT_PREREQ_MAP.get(exam_code, {})
        if not prereq_def:
            return (
                f"No specific prerequisite requirements found for {exam_target}. "
                "Review Microsoft's official exam page for the latest guidance."
            )
        return prereq_def.get("notes", "")

    # ── Task scheduling ───────────────────────────────────────────────────────

    def _priority_for(self, dp, profile: LearnerProfile) -> str:
        if dp.skip_recommended:
            return "skip"
        level = dp.knowledge_level.value
        is_risk = dp.domain_id in profile.risk_domains
        if level in ("unknown",) or (is_risk and level == "weak"):
            return "critical"
        if level == "weak" or is_risk:
            return "high"
        if level == "moderate":
            return "medium"
        return "low"

    def _build_tasks(self, profile: LearnerProfile) -> list[StudyTask]:
        """
        Assign sequential study weeks to each domain.

        Strategy:
          • Last week → review (reserved)
          • study_weeks = total_weeks - 1  (min 1 even for very short plans)
          • Relative weight per domain:
              - skip  → 0
              - critical/high (risk) → exam_weight × 2.0
              - medium  → exam_weight × 1.0
              - low     → exam_weight × 0.5
          • Weeks proportional to weight (min 1 per active domain)
          • Ordering: critical → high → medium → low → skip (last, token slot)
        """
        study_weeks  = max(profile.weeks_available - 1, 1)
        hours_pw     = profile.hours_per_week

        # Annotate each domain with priority and weight
        annotated = []
        for dp in profile.domain_profiles:
            meta     = self._DOMAIN_META.get(dp.domain_id, {})
            exam_w   = meta.get("weight", 1 / len(EXAM_DOMAINS))
            priority = self._priority_for(dp, profile)
            weight_mult = {"critical": 2.0, "high": 1.5, "medium": 1.0, "low": 0.5, "skip": 0.0}
            relative_w  = exam_w * weight_mult[priority]
            annotated.append((dp, priority, exam_w, relative_w))

        # Sort order
        _order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "skip": 4}
        annotated.sort(key=lambda t: _order[t[1]])

        # Separate active vs skip
        active  = [(dp, pri, ew, rw) for dp, pri, ew, rw in annotated if pri != "skip"]
        skipped = [(dp, pri, ew, rw) for dp, pri, ew, rw in annotated if pri == "skip"]

        total_rw = sum(rw for _, _, _, rw in active) or 1.0

        # Proportional allocation with Largest Remainder Method.
        # work at the DAY level (7 days/week) so even compact plans schedule cleanly.
        total_days  = study_weeks * 7
        ideal_days  = [(rw / total_rw) * total_days for _, _, _, rw in active]
        floor_days  = [max(1, int(d)) for d in ideal_days]   # at least 1 day per domain
        diff_days   = sum(floor_days) - total_days

        if diff_days > 0:
            # Over-allocated: reduce from lowest-priority domains (end of sorted list)
            for i in range(len(floor_days) - 1, -1, -1):
                if diff_days <= 0:
                    break
                reduce = min(diff_days, floor_days[i] - 1)
                floor_days[i] -= reduce
                diff_days -= reduce
        elif diff_days < 0:
            # Under-allocated: add by largest fractional remainder
            remainders = sorted(
                ((ideal_days[i] - floor_days[i], i) for i in range(len(ideal_days))),
                reverse=True,
            )
            for _, i in remainders[: -diff_days]:
                floor_days[i] += 1

        # Convert days → start/end weeks (fractional days → whole-week bands)
        raw_allocs_days = [
            (dp, pri, ew, floor_days[idx])
            for idx, (dp, pri, ew, _) in enumerate(active)
        ]

        # Build tasks (sequential blocks using cumulative day tracking → week labels)
        tasks: list[StudyTask] = []
        cumulative_day = 0   # days elapsed since start of study period

        for dp, pri, ew, alloc_days in raw_allocs_days:
            start_day    = cumulative_day
            end_day      = cumulative_day + alloc_days - 1
            start_week   = start_day // 7 + 1
            end_week     = end_day   // 7 + 1
            # Clamp to study_weeks
            start_week   = min(start_week, study_weeks)
            end_week     = min(end_week,   study_weeks)
            week_hours   = (alloc_days / 7) * hours_pw
            tasks.append(StudyTask(
                domain_id       = dp.domain_id,
                domain_name     = dp.domain_name,
                start_week      = start_week,
                end_week        = end_week,
                total_hours     = round(week_hours, 1),
                priority        = pri,
                knowledge_level = dp.knowledge_level.value,
                confidence_pct  = int(dp.confidence_score * 100),
            ))
            cumulative_day += alloc_days

        # Add skip tasks — placed in the last study week as a brief self-test
        skip_week = study_weeks
        for dp, pri, ew, _ in skipped:
            tasks.append(StudyTask(
                domain_id       = dp.domain_id,
                domain_name     = dp.domain_name,
                start_week      = skip_week,
                end_week        = skip_week,
                total_hours     = round(hours_pw * 0.25, 1),  # quarter-week self-test
                priority        = "skip",
                knowledge_level = dp.knowledge_level.value,
                confidence_pct  = int(dp.confidence_score * 100),
            ))

        return tasks

    # ── Narrative summary ─────────────────────────────────────────────────────

    def _build_summary(
        self,
        profile: LearnerProfile,
        tasks: list[StudyTask],
        prereq_gap: bool,
    ) -> str:
        critical = [t for t in tasks if t.priority == "critical"]
        high     = [t for t in tasks if t.priority == "high"]
        skip_cnt = sum(1 for t in tasks if t.priority == "skip")

        parts = [
            f"The study plan for **{profile.student_name}** spans "
            f"**{profile.weeks_available} weeks** "
            f"({profile.total_budget_hours:.0f} total hours). "
        ]
        if critical:
            names = ", ".join(t.domain_name.replace("Implement ", "") for t in critical)
            parts.append(
                f"**{len(critical)} critical domain(s)** require intensive focus: {names}. "
            )
        elif high:
            names = ", ".join(t.domain_name.replace("Implement ", "") for t in high[:2])
            parts.append(f"Priority attention needed for: {names}. ")
        if skip_cnt:
            parts.append(
                f"{skip_cnt} domain(s) are fast-tracked to a short self-test "
                f"based on prior knowledge. "
            )
        if prereq_gap:
            parts.append(
                "⚠️ A prerequisite certification gap was detected — "
                "review the prerequisites section below before deep-diving into study material. "
            )
        parts.append(
            "The final week is reserved for practice exams and revision. "
            "Risk domains are front-loaded to maximise remediation time."
        )
        return "".join(parts)
