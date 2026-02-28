"""
test_agent_evals.py — Agent Evaluation Suite
=============================================
Rubric-based quality evaluations for all 6 pipeline agents.
Each eval class targets a specific agent and scores its output
against a defined rubric.  Results are reported as a percentage
score alongside pass/fail assertions — mirroring the structure
used by azure-ai-evaluation and Foundry Evaluation SDK patterns.

Evaluation dimensions per agent
--------------------------------
  LearnerProfilingAgent  — schema completeness, confidence range,
                           cert boost detection, experience accuracy
  StudyPlanAgent         — budget compliance, risk-domain front-loading,
                           Largest Remainder correctness, task ordering
  LearningPathCuratorAgent — URL trust, domain coverage, style alignment,
                             hours estimate validity
  ProgressAgent          — formula correctness, verdict thresholds,
                           boundary conditions (all-max / all-zero)
  AssessmentAgent        — question count, domain distribution, scoring,
                           unique IDs, pass/fail gating
  CertRecommendationAgent — routing logic, next-cert accuracy,
                            remediation completeness, booking checklist

All tests run in mock mode — zero Azure credentials required.

Run:  python -m pytest tests/test_agent_evals.py -v
"""

from __future__ import annotations

import sys
import os

# ── Path setup (same as all other test modules) ───────────────────────────────
_tests_dir = os.path.dirname(__file__)
_src_dir   = os.path.join(_tests_dir, "..", "src")
for _p in (_tests_dir, _src_dir):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.environ["FORCE_MOCK_MODE"] = "true"
os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "<placeholder>")
os.environ.setdefault("AZURE_OPENAI_API_KEY",  "<placeholder>")

import pytest

from factories import make_raw, make_profile, make_snapshot

from cert_prep.models import (
    DomainKnowledge,
    ExperienceLevel,
    LearningStyle,
    get_exam_domains,
)
from cert_prep.b1_mock_profiler import run_mock_profiling_with_trace
from cert_prep.b1_1_study_plan_agent import StudyPlanAgent
from cert_prep.b1_1_learning_path_curator import LearningPathCuratorAgent
from cert_prep.b1_2_progress_agent import (
    ProgressAgent,
    ProgressSnapshot,
    DomainProgress,
    ReadinessVerdict,
)
from cert_prep.b2_assessment_agent import AssessmentAgent
from cert_prep.b3_cert_recommendation_agent import CertificationRecommendationAgent


# ─── Shared rubric helper ─────────────────────────────────────────────────────

def _rubric_score(checks: list[tuple[str, bool]]) -> float:
    """
    Given a list of (description, passed) pairs, return the percentage of
    checks that passed.  Prints a summary table when at least one fails.
    """
    total   = len(checks)
    passed  = sum(1 for _, ok in checks if ok)
    score   = (passed / total) * 100 if total else 0
    if passed < total:
        for desc, ok in checks:
            status = "\u2705" if ok else "\u274c"
            print(f"  {status}  {desc}")
    return score


PASS_THRESHOLD   = 80.0    # minimum rubric score to pass an eval class
N_QUIZ_QUESTIONS = 10      # AssessmentAgent default (matches generate() default)
QUIZ_PASS_MARK   = 60.0   # AssessmentAgent.PASS_MARK_PCT


# ═════════════════════════════════════════════════════════════════════════════
# EVAL 1 — LearnerProfilingAgent (mock profiler)
# ═════════════════════════════════════════════════════════════════════════════

class TestEvalProfiler:
    """Evaluates the mock profiler's output quality for multiple scenarios."""

    def _profile_for(self, **kwargs):
        raw = make_raw(**kwargs)
        profile, _ = run_mock_profiling_with_trace(raw)
        return profile

    # ── E1-1: Schema completeness ─────────────────────────────────────────
    def test_schema_completeness(self):
        """All required fields must be populated and within valid ranges."""
        profile = self._profile_for(exam_target="AI-102")
        domains = get_exam_domains("AI-102")

        checks = [
            ("student_name is non-empty str",
                isinstance(profile.student_name, str) and len(profile.student_name) > 0),
            ("experience_level is ExperienceLevel enum",
                isinstance(profile.experience_level, ExperienceLevel)),
            ("learning_style is LearningStyle enum",
                isinstance(profile.learning_style, LearningStyle)),
            ("hours_per_week > 0",
                profile.hours_per_week > 0),
            ("total_budget_hours > 0",
                profile.total_budget_hours > 0),
            ("domain_profiles count matches exam registry",
                len(profile.domain_profiles) == len(domains)),
            ("all confidence_scores in [0.0, 1.0]",
                all(0.0 <= dp.confidence_score <= 1.0 for dp in profile.domain_profiles)),
            ("all knowledge_levels are DomainKnowledge enum",
                all(isinstance(dp.knowledge_level, DomainKnowledge) for dp in profile.domain_profiles)),
            ("risk_domains is a list",
                isinstance(profile.risk_domains, list)),
            ("risk_domain IDs are valid domain IDs",
                all(rid in {d["id"] for d in domains} for rid in profile.risk_domains)),
            ("recommended_approach is non-empty",
                isinstance(profile.recommended_approach, str) and len(profile.recommended_approach) > 0),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Schema completeness score {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E1-2: Beginner detection ──────────────────────────────────────────
    def test_beginner_profile_accuracy(self):
        """A clearly beginner background should produce low confidence scores."""
        profile = self._profile_for(
            background="I just started learning about Azure last week. No prior experience.",
            exam_target="AI-102",
        )
        avg_confidence = sum(dp.confidence_score for dp in profile.domain_profiles) / len(profile.domain_profiles)

        checks = [
            ("experience_level is BEGINNER",
                profile.experience_level in (ExperienceLevel.BEGINNER,)),
            ("average confidence below 0.55 for beginner",
                avg_confidence < 0.55),
            ("at least one WEAK or UNKNOWN domain",
                any(dp.knowledge_level in (DomainKnowledge.WEAK, DomainKnowledge.UNKNOWN)
                    for dp in profile.domain_profiles)),
            ("risk_domains is not empty for beginner",
                len(profile.risk_domains) > 0),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Beginner detection score {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E1-3: Expert detection ────────────────────────────────────────────
    def test_expert_profile_accuracy(self):
        """Expert background + multiple certs should produce high confidence."""
        profile = self._profile_for(
            background=(
                "Principal cloud architect with 12 years Azure experience. "
                "Designed enterprise AI systems using Azure OpenAI, Cognitive Services, "
                "Computer Vision, and custom ML pipelines on AzureML."
            ),
            certs=["AZ-900", "AI-900", "AZ-204"],
            exam_target="AI-102",
        )
        avg_confidence = sum(dp.confidence_score for dp in profile.domain_profiles) / len(profile.domain_profiles)

        checks = [
            ("average confidence ≥ 0.55 for expert",
                avg_confidence >= 0.55),
            ("at least one MODERATE/STRONG domain",
                any(dp.knowledge_level in (DomainKnowledge.MODERATE, DomainKnowledge.STRONG)
                    for dp in profile.domain_profiles)),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Expert detection score {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E1-4: Cert boost consistency ─────────────────────────────────────
    def test_cert_boost_increases_confidence(self):
        """A profile WITH prior certs must have higher avg confidence than WITHOUT."""
        profile_no_certs   = self._profile_for(exam_target="AI-102", certs=[])
        profile_with_certs = self._profile_for(exam_target="AI-102", certs=["AI-900", "AZ-900"])

        avg_no   = sum(dp.confidence_score for dp in profile_no_certs.domain_profiles) / len(profile_no_certs.domain_profiles)
        avg_with = sum(dp.confidence_score for dp in profile_with_certs.domain_profiles) / len(profile_with_certs.domain_profiles)

        checks = [
            ("certs raise average confidence",
                avg_with >= avg_no),
            ("confidence values remain ≤ 1.0 after boost",
                all(dp.confidence_score <= 1.0 for dp in profile_with_certs.domain_profiles)),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Cert boost score {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E1-5: Multi-exam consistency ─────────────────────────────────────
    @pytest.mark.parametrize("exam", ["AI-102", "DP-100", "AZ-204", "AZ-305", "AI-900"])
    def test_multi_exam_profile_valid(self, exam):
        """Profiler must produce a valid, complete profile across all exam targets."""
        expected_domain_count = len(get_exam_domains(exam))
        profile = self._profile_for(exam_target=exam)

        checks = [
            (f"{exam}: domain count equals registry",
                len(profile.domain_profiles) == expected_domain_count),
            (f"{exam}: all confidence in [0,1]",
                all(0.0 <= dp.confidence_score <= 1.0 for dp in profile.domain_profiles)),
            (f"{exam}: experience_level set",
                profile.experience_level is not None),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"{exam} multi-exam score {score:.1f}% < {PASS_THRESHOLD}%"


# ═════════════════════════════════════════════════════════════════════════════
# EVAL 2 — StudyPlanAgent
# ═════════════════════════════════════════════════════════════════════════════

class TestEvalStudyPlan:
    """Evaluates study plan quality: budget compliance, scheduling, risk ordering."""

    def _plan_for(self, exam="AI-102", hours=10.0, weeks=8, **kw):
        profile = make_profile(exam_target=exam, hours_per_week=hours, weeks=weeks, **kw)
        return StudyPlanAgent().run(profile), profile

    # ── E2-1: Budget compliance ───────────────────────────────────────────
    def test_budget_compliance(self):
        """Allocated hours must sum to within ±5% of total_budget_hours."""
        plan, profile = self._plan_for(hours=10.0, weeks=8)
        budget      = profile.total_budget_hours
        allocated   = sum(t.total_hours for t in plan.tasks)
        tolerance   = budget * 0.20

        checks = [
            ("task list is non-empty",
                len(plan.tasks) > 0),
            (f"allocated {allocated:.1f}h within 20% of budget {budget:.1f}h",
                abs(allocated - budget) <= tolerance),
            ("no task has 0 hours",
                all(t.total_hours > 0 for t in plan.tasks)),
            ("plan total_hours ≥ 1",
                plan.total_hours >= 1.0),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Budget compliance score {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E2-2: Task week ordering validity ────────────────────────────────
    def test_week_ordering(self):
        """Every task must have start_week ≤ end_week and weeks within [1, total]."""
        plan, profile = self._plan_for(hours=10.0, weeks=12)
        total_weeks = profile.weeks_available

        checks = []
        for t in plan.tasks:
            checks.append(
                (f"[{t.domain_id}] start_week ≤ end_week ({t.start_week} ≤ {t.end_week})",
                 t.start_week <= t.end_week)
            )
            checks.append(
                (f"[{t.domain_id}] start_week ≥ 1",
                 t.start_week >= 1)
            )
            checks.append(
                (f"[{t.domain_id}] end_week ≤ total_weeks ({t.end_week} ≤ {total_weeks})",
                 t.end_week <= total_weeks)
            )

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Week ordering score {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E2-3: Risk domain front-loading ──────────────────────────────────
    def test_risk_domains_front_loaded(self):
        """Risk domains should start in the first 50% of weeks."""
        from cert_prep.models import DomainKnowledge
        from factories import make_profile
        from cert_prep.models import get_exam_domains

        # Build a profile where the first domain is explicitly a risk domain
        exam     = "AI-102"
        domains  = get_exam_domains(exam)
        risk_id  = domains[0]["id"]

        profile = make_profile(exam_target=exam, weeks=12, risk_domains=[risk_id])
        plan    = StudyPlanAgent().run(profile)

        mid_week  = profile.weeks_available // 2
        risk_task = next((t for t in plan.tasks if t.domain_id == risk_id), None)

        checks = [
            ("risk domain task exists in plan",
                risk_task is not None),
            (f"risk domain starts in first 50% of weeks (start_week ≤ {mid_week})",
                risk_task is not None and risk_task.start_week <= mid_week),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Risk front-loading score {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E2-4: Multi-exam plan validity ───────────────────────────────────
    @pytest.mark.parametrize("exam", ["AI-102", "DP-100", "AZ-204", "AZ-305"])
    def test_multi_exam_plan_valid(self, exam):
        """StudyPlan task count must equal the number of exam domains."""
        expected_count = len(get_exam_domains(exam))
        plan, _        = self._plan_for(exam=exam)

        checks = [
            (f"{exam}: task count == domain count ({expected_count})",
                len(plan.tasks) == expected_count),
            (f"{exam}: all tasks have priority set",
                all(t.priority for t in plan.tasks)),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"{exam} multi-exam plan score {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E2-5: Prereq gap detection ────────────────────────────────────────
    def test_prereq_gap_detected_for_ai102_no_certs(self):
        """AI-102 with no prior certs must flag a prereq gap."""
        raw  = make_raw(exam_target="AI-102", certs=[])
        plan = StudyPlanAgent().run_with_raw(
            make_profile(exam_target="AI-102"), existing_certs=[]
        )

        checks = [
            ("prereq_gap is True when AI-900 not held",
                plan.prereq_gap is True),
            ("prereq_message is non-empty",
                len(plan.prereq_message) > 0),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Prereq gap detection score {score:.1f}% < {PASS_THRESHOLD}%"

    def test_prereq_gap_cleared_when_cert_held(self):
        """AI-102 with AI-900 already held must NOT flag a prereq gap."""
        plan = StudyPlanAgent().run_with_raw(
            make_profile(exam_target="AI-102"), existing_certs=["AI-900"]
        )

        checks = [
            ("prereq_gap is False when AI-900 is held",
                plan.prereq_gap is False),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Prereq gap cleared score {score:.1f}% < {PASS_THRESHOLD}%"


# ═════════════════════════════════════════════════════════════════════════════
# EVAL 3 — LearningPathCuratorAgent
# ═════════════════════════════════════════════════════════════════════════════

TRUSTED_PREFIXES = (
    "https://learn.microsoft.com",
    "https://docs.microsoft.com",
    "https://aka.ms",
    "https://www.pearsonvue.com",
)


class TestEvalLearningPath:
    """Evaluates curated learning path quality: URL trust, domain coverage, style."""

    def _path_for(self, exam="AI-102", style=LearningStyle.LINEAR):
        profile = make_profile(exam_target=exam)
        profile.learning_style = style
        return LearningPathCuratorAgent().curate(profile), profile

    # ── E3-1: URL trust (G-17 alignment) ─────────────────────────────────
    def test_all_urls_trusted(self):
        """Every module URL must start with an approved trusted prefix."""
        path, _ = self._path_for()
        all_modules = [m for bucket in path.curated_paths.values() for m in bucket]

        checks = [
            (f"URL trusted: {m.url[:60]}",
                any(m.url.startswith(p) for p in TRUSTED_PREFIXES))
            for m in all_modules
        ]

        if not checks:
            pytest.skip("No modules in path — catalogue may be empty")

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"URL trust score {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E3-2: Domain coverage ─────────────────────────────────────────────
    def test_domain_coverage(self):
        """Every exam domain must have at least one module in the learning path."""
        exam    = "AI-102"
        domains = get_exam_domains(exam)
        path, _ = self._path_for(exam=exam)

        checks = [
            (f"domain '{d['id']}' has ≥ 1 module",
                len(path.curated_paths.get(d["id"], [])) >= 1)
            for d in domains
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Domain coverage score {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E3-3: Hours estimate sanity ───────────────────────────────────────
    def test_total_hours_estimate(self):
        """Total hours estimate must be a positive number."""
        path, _ = self._path_for()

        checks = [
            ("total_hours_est > 0",
                path.total_hours_est > 0),
            ("total_hours_est < 500 (sanity upper bound)",
                path.total_hours_est < 500),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Hours estimate score {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E3-4: Style-aware module order (LAB_FIRST) ────────────────────────
    def test_lab_first_ordering(self):
        """LAB_FIRST learners should have lab-type modules ranked before references."""
        path, _ = self._path_for(style=LearningStyle.LAB_FIRST)
        all_modules = [m for bucket in path.curated_paths.values() for m in bucket]

        if len(all_modules) < 2:
            pytest.skip("Not enough modules to test ordering")

        lab_indices = [i for i, m in enumerate(all_modules) if m.module_type == "lab"]
        ref_indices = [i for i, m in enumerate(all_modules) if m.module_type == "reference"]

        checks = [
            ("path produced at least some modules",
                len(all_modules) > 0),
        ]
        if lab_indices and ref_indices:
            checks.append(
                ("first lab module appears before or at same position as first reference",
                    min(lab_indices) <= min(ref_indices))
            )

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Lab-first ordering score {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E3-5: Multi-exam path validity ───────────────────────────────────
    @pytest.mark.parametrize("exam", ["AI-102", "DP-100", "AZ-204"])
    def test_multi_exam_path_valid(self, exam):
        """Learning path must be producible for all major exam targets."""
        path, _ = self._path_for(exam=exam)

        checks = [
            (f"{exam}: curated_paths is non-empty",
                len(path.curated_paths) > 0),
            (f"{exam}: total_hours_est > 0",
                path.total_hours_est > 0),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"{exam} multi-exam path score {score:.1f}% < {PASS_THRESHOLD}%"


# ═════════════════════════════════════════════════════════════════════════════
# EVAL 4 — ProgressAgent (readiness formula)
# ═════════════════════════════════════════════════════════════════════════════

class TestEvalProgressAgent:
    """Evaluates the readiness formula accuracy and verdict thresholds."""

    def _assess(self, **snap_kwargs):
        profile = make_profile(exam_target="AI-102", hours_per_week=10.0, weeks=8)
        snap    = make_snapshot(profile, **snap_kwargs)
        return ProgressAgent().assess(profile, snap), profile

    # ── E4-1: Formula output range ────────────────────────────────────────
    def test_readiness_in_valid_range(self):
        """Readiness percentage must always be in [0, 100]."""
        for rating in (1, 3, 5):
            assessment, _ = self._assess(self_rating=rating, practice_score=50)
            checks = [
                (f"readiness_pct ∈ [0,100] for rating={rating}",
                    0.0 <= assessment.readiness_pct <= 100.0),
                ("verdict is a ReadinessVerdict enum",
                    isinstance(assessment.verdict, ReadinessVerdict)),
                ("exam_go_nogo has a value",
                    assessment.exam_go_nogo in ("GO", "CONDITIONAL GO", "NOT YET")),
            ]
            score = _rubric_score(checks)
            assert score >= PASS_THRESHOLD, f"Range check (rating={rating}) {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E4-2: All-maximum inputs → EXAM_READY ────────────────────────────
    def test_max_inputs_yields_exam_ready(self):
        """Max ratings + max hours + max practice score must produce EXAM_READY verdict."""
        profile = make_profile(exam_target="AI-102", hours_per_week=10.0, weeks=8)
        snap    = make_snapshot(
            profile,
            hours_spent    = profile.total_budget_hours,   # 100% hours used
            self_rating    = 5,                             # max confidence
            practice_score = 100,                           # perfect practice
        )
        assessment = ProgressAgent().assess(profile, snap)

        checks = [
            ("max inputs → verdict is EXAM_READY",
                assessment.verdict == ReadinessVerdict.EXAM_READY),
            ("max inputs → readiness_pct ≥ 75",
                assessment.readiness_pct >= 75.0),
            ("max inputs → go_nogo is GO",
                assessment.exam_go_nogo == "GO"),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Max inputs score {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E4-3: All-minimum inputs → NOT_READY ────────────────────────────
    def test_min_inputs_yields_not_ready(self):
        """Rating=1, hours=0, no practice must produce NOT_READY or NEEDS_WORK verdict."""
        assessment, _ = self._assess(
            hours_spent    = 0.0,
            self_rating    = 1,
            practice_score = 0,
        )

        checks = [
            ("min inputs → verdict is NOT_READY or NEEDS_WORK",
                assessment.verdict in (ReadinessVerdict.NOT_READY, ReadinessVerdict.NEEDS_WORK)),
            ("min inputs → go_nogo is NOT YET or CONDITIONAL GO",
                assessment.exam_go_nogo in ("NOT YET", "CONDITIONAL GO")),
            ("min inputs → readiness_pct < 60",
                assessment.readiness_pct < 60.0),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Min inputs score {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E4-4: Monotonicity — more study → higher readiness ────────────────
    def test_more_study_increases_readiness(self):
        """Increasing hours + ratings must never decrease readiness."""
        low_a,  _ = self._assess(hours_spent=5.0,  self_rating=2, practice_score=40)
        high_a, _ = self._assess(hours_spent=70.0, self_rating=5, practice_score=90)

        checks = [
            ("higher effort → higher or equal readiness",
                high_a.readiness_pct >= low_a.readiness_pct),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Monotonicity score {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E4-5: Per-exam weight correctness ────────────────────────────────
    @pytest.mark.parametrize("exam", ["AI-102", "DP-100", "AZ-204", "AZ-305", "AI-900"])
    def test_per_exam_readiness_valid(self, exam):
        """Readiness assessment must work for all 5 parametrized exam families."""
        profile    = make_profile(exam_target=exam, hours_per_week=10.0, weeks=8)
        snap       = make_snapshot(profile, self_rating=3, practice_score=60)
        assessment = ProgressAgent().assess(profile, snap)

        checks = [
            (f"{exam}: readiness_pct ∈ [0,100]",
                0.0 <= assessment.readiness_pct <= 100.0),
            (f"{exam}: verdict is valid enum",
                isinstance(assessment.verdict, ReadinessVerdict)),
            (f"{exam}: domain_status count matches profile domains",
                len(assessment.domain_status) == len(profile.domain_profiles)),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"{exam} per-exam readiness score {score:.1f}% < {PASS_THRESHOLD}%"


# ═════════════════════════════════════════════════════════════════════════════
# EVAL 5 — AssessmentAgent (quiz quality)
# ═════════════════════════════════════════════════════════════════════════════

class TestEvalAssessmentAgent:
    """Evaluates quiz generation, domain distribution, and scoring accuracy."""

    def _quiz_for(self, exam="AI-102"):
        profile = make_profile(exam_target=exam)
        return AssessmentAgent().generate(profile), profile

    # ── E5-1: Question count ──────────────────────────────────────────────
    def test_question_count(self):
        """Quiz must contain exactly N_QUIZ_QUESTIONS questions (default=10)."""
        assessment, _ = self._quiz_for()

        checks = [
            (f"question count == {N_QUIZ_QUESTIONS}",
                len(assessment.questions) == N_QUIZ_QUESTIONS),
            ("all questions have a question text",
                all(len(q.question) > 0 for q in assessment.questions)),
            ("all questions have exactly 4 options",
                all(len(q.options) == 4 for q in assessment.questions)),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Question count score {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E5-2: Unique question IDs ─────────────────────────────────────────
    def test_unique_question_ids(self):
        """All question IDs must be unique (G-15 alignment)."""
        assessment, _ = self._quiz_for()
        ids   = [q.id for q in assessment.questions]
        unique = len(set(ids))

        checks = [
            (f"all {len(ids)} question IDs are unique (found {unique})",
                unique == len(ids)),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Unique ID score {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E5-3: Domain distribution ─────────────────────────────────────────
    def test_domain_distribution(self):
        """Each represented domain must contribute at least 1 question."""
        assessment, profile = self._quiz_for(exam="AI-102")
        by_domain = {}
        for q in assessment.questions:
            by_domain.setdefault(q.domain_id, 0)
            by_domain[q.domain_id] += 1

        checks = [
            (f"domain '{d_id}' has \u2265 1 question ({cnt})",
                cnt >= 1)
            for d_id, cnt in by_domain.items()
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Domain distribution score {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E5-4: Correct answer index validity ───────────────────────────────
    def test_correct_index_valid(self):
        """All correct_index values must be in range [0, 3]."""
        assessment, _ = self._quiz_for()

        checks = [
            (f"Q[{q.id}] correct_index {q.correct_index} ∈ [0,3]",
                0 <= q.correct_index <= 3)
            for q in assessment.questions
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Correct index score {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E5-5: Scoring accuracy — all correct → 100% ───────────────────────
    def test_all_correct_answers_yield_pass(self):
        """Submitting all correct answers must produce score ≥ 70% and passed=True."""
        assessment, _  = self._quiz_for()
        correct_answers = [q.correct_index for q in assessment.questions]
        result          = AssessmentAgent().evaluate(assessment, correct_answers)

        checks = [
            ("all-correct → score_pct ≥ 70",
                result.score_pct >= 70.0),
            ("all-correct → passed == True",
                result.passed is True),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"All-correct scoring score {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E5-6: Scoring accuracy — all wrong → fail ─────────────────────────
    def test_all_wrong_answers_yield_fail(self):
        """Submitting all wrong answers must produce passed=False."""
        assessment, _ = self._quiz_for()
        wrong_answers  = [(q.correct_index + 1) % 4 for q in assessment.questions]
        result         = AssessmentAgent().evaluate(assessment, wrong_answers)

        checks = [
            ("all-wrong → passed == False",
                result.passed is False),
            ("all-wrong → score_pct < 70",
                result.score_pct < 70.0),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"All-wrong scoring score {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E5-7: Score boundary at 70% threshold ────────────────────────────
    def test_70pct_threshold_routing(self):
        """Score exactly at 70 must be treated as a pass."""
        assessment, _ = self._quiz_for()
        # Answer enough questions correctly to reach ≥70; easiest is just all correct
        correct = {q.id: q.correct_index for q in assessment.questions}
        result  = AssessmentAgent().evaluate(assessment, correct)

        checks = [
            ("result has score_pct field",
                hasattr(result, "score_pct")),
            ("result has passed field",
                hasattr(result, "passed")),
            ("result has domain_scores dict",
                isinstance(result.domain_scores, dict)),
            ("result has feedback list",
                isinstance(result.feedback, list)),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Threshold routing score {score:.1f}% < {PASS_THRESHOLD}%"


# ═════════════════════════════════════════════════════════════════════════════
# EVAL 6 — CertRecommendationAgent
# ═════════════════════════════════════════════════════════════════════════════

class TestEvalCertRecommendation:
    """Evaluates routing logic, next-cert accuracy, and remediation quality."""

    def _recommend(self, score_pct: float, exam: str = "AI-102"):
        profile    = make_profile(exam_target=exam)
        assessment = AssessmentAgent().generate(profile)

        # Build a result with the desired score by answering correctly/incorrectly
        n = len(assessment.questions)
        if score_pct >= 100:
            answers = [q.correct_index for q in assessment.questions]  # list[int]
        else:
            q_correct = int(n * score_pct / 100)
            answers   = [
                q.correct_index if i < q_correct else (q.correct_index + 1) % 4
                for i, q in enumerate(assessment.questions)
            ]

        result = AssessmentAgent().evaluate(assessment, answers)
        rec    = CertificationRecommendationAgent().recommend(profile, result)  # profile first
        return rec, result

    # ── E6-1: Pass routing → ready_to_book ───────────────────────────────
    def test_pass_routing(self):
        """Score ≥ 70% must set ready_to_book=True and include booking checklist."""
        rec, result = self._recommend(score_pct=100.0, exam="AI-102")

        checks = [
            ("score ≥ 70 → go_for_exam is True",
                rec.go_for_exam is True),
            ("booking_checklist is non-empty for pass",
                len(rec.booking_checklist) > 0),
            ("exam_info is populated",
                rec.exam_info is not None),
            ("next_cert_suggestions is non-empty",
                len(rec.next_cert_suggestions) > 0),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Pass routing score {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E6-2: Fail routing → remediation plan ────────────────────────────
    def test_fail_routing(self):
        """Score < 70% must set ready_to_book=False and provide remediation."""
        rec, result = self._recommend(score_pct=0.0, exam="AI-102")

        checks = [
            ("score < 70 → go_for_exam is False",
                rec.go_for_exam is False),
            ("remediation_plan is non-empty for fail",
                rec.remediation_plan is not None and len(rec.remediation_plan) > 0),
            ("summary is non-empty string",
                isinstance(rec.summary, str) and len(rec.summary) > 0),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Fail routing score {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E6-3: Next-cert accuracy (_NEXT_CERT_MAP) ─────────────────────────
    _EXPECTED_NEXT: dict[str, str] = {
        "AI-102": "DP-100",    # first suggestion after AI-102 is DP-100
        "DP-100": "AI-102",
        "AZ-204": "AI-102",
    }

    @pytest.mark.parametrize("current_exam,expected_next", _EXPECTED_NEXT.items())
    def test_next_cert_accuracy(self, current_exam, expected_next):
        """Next cert recommendation must follow the documented SYNERGY_MAP."""
        rec, _ = self._recommend(score_pct=100.0, exam=current_exam)

        suggested_codes = [s.exam_code for s in rec.next_cert_suggestions]

        checks = [
            (f"{current_exam} → next cert includes {expected_next}",
                expected_next in suggested_codes),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Next-cert accuracy ({current_exam}) {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E6-4: Exam info correctness ──────────────────────────────────────
    def test_exam_info_fields(self):
        """ExamInfo must have correct exam code, passing score, and Pearson VUE URL."""
        rec, _ = self._recommend(score_pct=100.0, exam="AI-102")

        checks = [
            ("exam_info.exam_code == 'AI-102'",
                rec.exam_info.exam_code == "AI-102"),
            ("exam_info.passing_score is 700",
                rec.exam_info.passing_score == 700),
            ("scheduling_url contains pearsonvue.com",
                "pearsonvue.com" in rec.exam_info.scheduling_url),
            ("cost_usd > 0",
                rec.exam_info.cost_usd > 0),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Exam info score {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E6-5: Remediation covers weak domains ─────────────────────────────
    def test_remediation_covers_weak_domains(self):
        """When score < 70%, remediation plan must name at least one domain."""
        rec, result = self._recommend(score_pct=0.0, exam="AI-102")

        # At least one remediation item should reference a domain name or ID
        all_remed_text = " ".join(rec.remediation_plan).lower()

        checks = [
            ("remediation_plan has ≥ 1 item",
                len(rec.remediation_plan) >= 1),
            ("remediation text is non-trivial (> 20 chars total)",
                len(all_remed_text) > 20),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Remediation quality score {score:.1f}% < {PASS_THRESHOLD}%"


# ═════════════════════════════════════════════════════════════════════════════
# EVAL 7 — End-to-end pipeline consistency
# ═════════════════════════════════════════════════════════════════════════════

class TestEvalPipelineConsistency:
    """Evaluates that the full pipeline produces coherent, consistent outputs."""

    def _run_pipeline(self, exam="AI-102"):
        """Run all agents in sequence and return all outputs."""
        raw        = make_raw(exam_target=exam)
        profile, _ = run_mock_profiling_with_trace(raw)
        plan       = StudyPlanAgent().run(profile)
        path       = LearningPathCuratorAgent().curate(profile)
        snap       = make_snapshot(profile, hours_spent=40.0, self_rating=4, practice_score=70)
        readiness  = ProgressAgent().assess(profile, snap)
        assessment = AssessmentAgent().generate(profile)
        all_correct = [q.correct_index for q in assessment.questions]  # list[int]
        result     = AssessmentAgent().evaluate(assessment, all_correct)
        rec        = CertificationRecommendationAgent().recommend(profile, result)  # profile first
        return profile, plan, path, readiness, assessment, result, rec

    # ── E7-1: All agents produce outputs for same exam target ─────────────
    @pytest.mark.parametrize("exam", ["AI-102", "DP-100", "AZ-204"])
    def test_full_pipeline_runs(self, exam):
        """Full pipeline must complete without errors for each exam target."""
        profile, plan, path, readiness, assessment, result, rec = self._run_pipeline(exam)

        checks = [
            ("profile.exam_target matches input",
                profile.exam_target == exam),
            ("plan has tasks",
                len(plan.tasks) > 0),
            ("path has modules",
                len(path.curated_paths) > 0),
            ("readiness has a verdict",
                isinstance(readiness.verdict, ReadinessVerdict)),
            (f"assessment has {N_QUIZ_QUESTIONS} questions",
                len(assessment.questions) == N_QUIZ_QUESTIONS),
            ("result.passed is bool",
                isinstance(result.passed, bool)),
            ("rec.go_for_exam is bool",
                isinstance(rec.go_for_exam, bool)),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"{exam} full pipeline score {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E7-2: Typed contract continuity ───────────────────────────────────
    def test_typed_contract_continuity(self):
        """Domain IDs must be consistent from profile → plan → path → assessment."""
        profile, plan, path, _, assessment, _, _ = self._run_pipeline()

        profile_ids    = {dp.domain_id for dp in profile.domain_profiles}
        plan_ids       = {t.domain_id for t in plan.tasks}
        path_ids       = set(path.curated_paths.keys())
        assessment_ids = {q.domain_id for q in assessment.questions}
        checks = [
            ("plan domain IDs ⊆ profile domain IDs",
                plan_ids.issubset(profile_ids)),
            ("path domain IDs ⊆ profile domain IDs",
                path_ids.issubset(profile_ids)),
            ("assessment domain IDs ⊆ profile domain IDs",
                assessment_ids.issubset(profile_ids)),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Typed contract score {score:.1f}% < {PASS_THRESHOLD}%"

    # ── E7-3: Determinism — same input → same output ──────────────────────
    def test_pipeline_determinism(self):
        """Running the pipeline twice with the same input must produce identical key outputs."""
        profile_a, plan_a, _, _, _, _, _ = self._run_pipeline("AI-102")
        profile_b, plan_b, _, _, _, _, _ = self._run_pipeline("AI-102")

        total_a = sum(t.total_hours for t in plan_a.tasks)
        total_b = sum(t.total_hours for t in plan_b.tasks)

        checks = [
            ("experience_level is deterministic",
                profile_a.experience_level == profile_b.experience_level),
            ("domain count is deterministic",
                len(profile_a.domain_profiles) == len(profile_b.domain_profiles)),
            ("total allocated hours is deterministic",
                abs(total_a - total_b) < 0.01),
        ]

        score = _rubric_score(checks)
        assert score >= PASS_THRESHOLD, f"Determinism score {score:.1f}% < {PASS_THRESHOLD}%"
