"""
Comprehensive tests for all 17 guardrail rules (G-01 through G-17).
Covers every BLOCK / WARN / INFO level across all guard classes.
"""
import pytest
from dataclasses import dataclass, field
from typing import Optional

from factories import make_raw, make_profile, make_snapshot

from cert_prep.guardrails import (
    GuardrailsPipeline,
    InputGuardrails,
    ProfileGuardrails,
    StudyPlanGuardrails,
    ProgressSnapshotGuardrails,
    AssessmentGuardrails,
    OutputContentGuardrails,
    GuardrailLevel,
    GuardrailResult,
)
from cert_prep.models import RawStudentInput, DomainProfile, DomainKnowledge


# ─── Helper: extract violations by code ──────────────────────────────────────

def violations_for(result: GuardrailResult, code: str):
    return [v for v in result.violations if v.code == code]


def blocks_for(result: GuardrailResult, code: str):
    return [v for v in result.violations if v.code == code and v.level == GuardrailLevel.BLOCK]


# ─── G-01: Required fields ────────────────────────────────────────────────────

class TestG01RequiredFields:
    def test_empty_student_name_blocks(self):
        raw = make_raw()
        raw.student_name = ""
        result = InputGuardrails().check(raw)
        assert blocks_for(result, "G-01"), "Empty name must BLOCK"

    def test_empty_exam_target_blocks(self):
        raw = make_raw()
        raw.exam_target = ""
        result = InputGuardrails().check(raw)
        assert blocks_for(result, "G-01"), "Empty exam target must BLOCK"

    def test_empty_background_warns(self):
        raw = make_raw(background="")
        result = InputGuardrails().check(raw)
        g01 = [v for v in result.violations if v.code == "G-01" and v.level == GuardrailLevel.WARN]
        assert g01, "Empty background must WARN (not block)"
        assert not result.blocked, "Empty background alone must not BLOCK"

    def test_valid_input_no_g01_blocks(self):
        raw = make_raw()
        result = InputGuardrails().check(raw)
        assert not blocks_for(result, "G-01")


# ─── G-02: Hours per week ─────────────────────────────────────────────────────

class TestG02HoursPerWeek:
    def test_zero_hours_warns(self):
        raw = make_raw(hours_per_week=0.0)
        result = InputGuardrails().check(raw)
        g02 = violations_for(result, "G-02")
        assert g02, "Zero hours/week must trigger G-02"

    def test_negative_hours_warns(self):
        raw = make_raw(hours_per_week=-5.0)
        result = InputGuardrails().check(raw)
        assert violations_for(result, "G-02")

    def test_excessive_hours_warns(self):
        raw = make_raw(hours_per_week=100.0)
        result = InputGuardrails().check(raw)
        assert violations_for(result, "G-02"), ">80 h/week must warn"

    def test_boundary_80_no_warn(self):
        raw = make_raw(hours_per_week=80.0)
        result = InputGuardrails().check(raw)
        assert not violations_for(result, "G-02"), "Exactly 80 h/week is acceptable"

    def test_normal_hours_no_warn(self):
        raw = make_raw(hours_per_week=10.0)
        result = InputGuardrails().check(raw)
        assert not violations_for(result, "G-02")


# ─── G-03: Weeks available ────────────────────────────────────────────────────

class TestG03WeeksAvailable:
    def test_zero_weeks_blocks(self):
        raw = make_raw(weeks=0)
        result = InputGuardrails().check(raw)
        assert blocks_for(result, "G-03"), "0 weeks must BLOCK"
        assert result.blocked

    def test_negative_weeks_blocks(self):
        raw = make_raw(weeks=-2)
        result = InputGuardrails().check(raw)
        assert blocks_for(result, "G-03")

    def test_excessive_weeks_warns(self):
        raw = make_raw(weeks=60)
        result = InputGuardrails().check(raw)
        g03 = violations_for(result, "G-03")
        assert g03

    def test_boundary_52_no_warn(self):
        raw = make_raw(weeks=52)
        result = InputGuardrails().check(raw)
        assert not violations_for(result, "G-03")

    def test_normal_weeks_passes(self):
        raw = make_raw(weeks=8)
        result = InputGuardrails().check(raw)
        assert not violations_for(result, "G-03")


# ─── G-04: Exam code recognition ──────────────────────────────────────────────

class TestG04ExamCode:
    @pytest.mark.parametrize("code", ["AI-102", "AI-900", "AZ-204", "AZ-305", "DP-100"])
    def test_registered_exam_codes_pass(self, code):
        raw = make_raw(exam_target=code)
        result = InputGuardrails().check(raw)
        assert not violations_for(result, "G-04"), f"{code} must not trigger G-04"

    def test_unknown_exam_code_warns(self):
        raw = make_raw(exam_target="ZZ-999")
        result = InputGuardrails().check(raw)
        g04 = violations_for(result, "G-04")
        assert g04, "Unknown exam code must warn"
        assert g04[0].level == GuardrailLevel.WARN, "G-04 must WARN, not BLOCK"
        assert not result.blocked

    def test_exam_code_with_name_parses_correctly(self):
        """'AI-102 Azure AI Engineer' – code extracted from first word."""
        raw = make_raw(exam_target="AI-102 Azure AI Engineer")
        result = InputGuardrails().check(raw)
        assert not violations_for(result, "G-04")


# ─── G-05: PII notice ─────────────────────────────────────────────────────────

class TestG05PiiNotice:
    def test_g05_info_always_present(self):
        raw = make_raw()
        result = InputGuardrails().check(raw)
        g05 = violations_for(result, "G-05")
        assert g05, "G-05 must always fire as INFO"
        assert g05[0].level == GuardrailLevel.INFO

    def test_g05_does_not_block(self):
        raw = make_raw()
        result = InputGuardrails().check(raw)
        assert not result.blocked, "G-05 info must never block pipeline"


# ─── G-06: Domain profile completeness ───────────────────────────────────────

class TestG06DomainCompleteness:
    def test_incomplete_domain_profiles_warns(self):
        profile = make_profile()
        profile.domain_profiles = profile.domain_profiles[:2]  # only 2 of 6
        result = ProfileGuardrails().check(profile)
        g06 = violations_for(result, "G-06")
        assert g06, "< expected domain count must warn"

    def test_full_domain_profiles_no_warn(self):
        profile = make_profile()
        result = ProfileGuardrails().check(profile)
        assert not violations_for(result, "G-06")


# ─── G-07: Confidence score bounds ───────────────────────────────────────────

class TestG07ConfidenceScoreBounds:
    def test_negative_confidence_blocks(self):
        profile = make_profile()
        # Bypass pydantic validation via object.__setattr__
        object.__setattr__(profile.domain_profiles[0], "confidence_score", -0.1)
        result = ProfileGuardrails().check(profile)
        assert blocks_for(result, "G-07"), "Negative confidence must BLOCK"

    def test_over_one_confidence_blocks(self):
        profile = make_profile()
        object.__setattr__(profile.domain_profiles[0], "confidence_score", 1.1)
        result = ProfileGuardrails().check(profile)
        assert blocks_for(result, "G-07")

    def test_boundary_values_pass(self):
        profile = make_profile()
        object.__setattr__(profile.domain_profiles[0], "confidence_score", 0.0)
        object.__setattr__(profile.domain_profiles[1], "confidence_score", 1.0)
        result = ProfileGuardrails().check(profile)
        assert not blocks_for(result, "G-07")


# ─── G-08: Risk domain IDs valid ──────────────────────────────────────────────

class TestG08RiskDomains:
    def test_invalid_risk_domain_warns(self):
        profile = make_profile()
        profile.risk_domains = ["invalid_domain_xyz"]
        result = ProfileGuardrails().check(profile)
        assert violations_for(result, "G-08"), "Invalid risk domain ID must warn"

    def test_valid_risk_domains_pass(self):
        profile = make_profile()
        profile.risk_domains = ["plan_manage", "nlp"]
        result = ProfileGuardrails().check(profile)
        assert not violations_for(result, "G-08")


# ─── G-09: Study task start ≤ end ────────────────────────────────────────────

class TestG09TaskWeekOrder:
    def test_start_after_end_blocks(self):
        from cert_prep.b1_1_study_plan_agent import StudyTask, StudyPlan
        profile = make_profile()
        bad_task = StudyTask(
            domain_id="plan_manage", domain_name="Plan",
            start_week=5, end_week=3,  # inverted!
            total_hours=10.0, priority="medium",
            knowledge_level="moderate", confidence_pct=55,
        )

        @dataclass
        class FakePlan:
            tasks: list

        fp = FakePlan(tasks=[bad_task])
        result = StudyPlanGuardrails().check(fp, profile)
        assert blocks_for(result, "G-09"), "start_week > end_week must BLOCK"

    def test_valid_task_weeks_pass(self):
        from cert_prep.b1_1_study_plan_agent import StudyPlanAgent
        profile = make_profile()
        plan = StudyPlanAgent().run(profile)
        result = StudyPlanGuardrails().check(plan, profile)
        assert not blocks_for(result, "G-09")


# ─── G-10: Hours budget adherence ────────────────────────────────────────────

class TestG10HoursBudget:
    def test_over_budget_warns(self):
        from cert_prep.b1_1_study_plan_agent import StudyTask

        @dataclass
        class FakePlan:
            tasks: list

        profile = make_profile(hours_per_week=10.0, weeks=8)
        # Total budget = 80h; inject tasks summing to 100h (+25%)
        tasks = [
            StudyTask("d1", "D1", 1, 2, 50.0, "high", "weak", 30),
            StudyTask("d2", "D2", 3, 4, 50.0, "medium", "moderate", 55),
        ]
        fp = FakePlan(tasks=tasks)
        result = StudyPlanGuardrails().check(fp, profile)
        assert violations_for(result, "G-10"), "Over-budget plan must warn"

    def test_within_budget_passes(self):
        from cert_prep.b1_1_study_plan_agent import StudyPlanAgent
        profile = make_profile()
        plan = StudyPlanAgent().run(profile)
        result = StudyPlanGuardrails().check(plan, profile)
        assert not violations_for(result, "G-10")


# ─── G-11–G-13: Progress snapshot ────────────────────────────────────────────

class TestG11G13ProgressSnapshot:
    def test_negative_hours_blocks(self):
        profile = make_profile()
        snap = make_snapshot(profile, hours_spent=-1.0)
        result = ProgressSnapshotGuardrails().check(snap)
        assert blocks_for(result, "G-11")

    def test_self_rating_below_1_blocks(self):
        profile = make_profile()
        snap = make_snapshot(profile)
        snap.domain_progress[0].self_rating = 0  # invalid
        result = ProgressSnapshotGuardrails().check(snap)
        assert blocks_for(result, "G-12")

    def test_self_rating_above_5_blocks(self):
        profile = make_profile()
        snap = make_snapshot(profile)
        snap.domain_progress[0].self_rating = 6  # invalid
        result = ProgressSnapshotGuardrails().check(snap)
        assert blocks_for(result, "G-12")

    def test_practice_score_below_0_blocks(self):
        profile = make_profile()
        snap = make_snapshot(profile, practice_score=-5)
        result = ProgressSnapshotGuardrails().check(snap)
        assert blocks_for(result, "G-13")

    def test_practice_score_above_100_blocks(self):
        profile = make_profile()
        snap = make_snapshot(profile, practice_score=105)
        result = ProgressSnapshotGuardrails().check(snap)
        assert blocks_for(result, "G-13")

    def test_valid_snapshot_passes(self):
        profile = make_profile()
        snap = make_snapshot(profile)
        result = ProgressSnapshotGuardrails().check(snap)
        assert not result.blocked

    def test_none_practice_score_ok(self):
        profile = make_profile()
        snap = make_snapshot(profile, practice_done="no", practice_score=None)
        result = ProgressSnapshotGuardrails().check(snap)
        assert not violations_for(result, "G-13")


# ─── G-14–G-15: Assessment guardrails ────────────────────────────────────────

class TestG14G15Assessment:
    def _make_question(self, q_id):
        from cert_prep.b2_assessment_agent import QuizQuestion
        return QuizQuestion(
            id=q_id, domain_id="plan_manage", domain_name="Plan",
            question="Q?", options=["A","B","C","D"],
            correct_index=0, explanation="Because", difficulty="easy",
        )

    def test_too_few_questions_warns(self):
        from cert_prep.b2_assessment_agent import Assessment
        asmt = Assessment(
            student_name="Test", exam_target="AI-102",
            questions=[self._make_question(f"q{i}") for i in range(3)],
        )
        result = AssessmentGuardrails().check(asmt)
        assert violations_for(result, "G-14"), "< 5 questions must warn"

    def test_enough_questions_no_g14(self):
        from cert_prep.b2_assessment_agent import Assessment
        asmt = Assessment(
            student_name="Test", exam_target="AI-102",
            questions=[self._make_question(f"q{i}") for i in range(10)],
        )
        result = AssessmentGuardrails().check(asmt)
        assert not violations_for(result, "G-14")

    def test_duplicate_question_ids_blocks(self):
        from cert_prep.b2_assessment_agent import Assessment
        q = self._make_question("dup_id")
        asmt = Assessment(
            student_name="Test", exam_target="AI-102",
            questions=[q, q],  # same object = same id
        )
        result = AssessmentGuardrails().check(asmt)
        assert blocks_for(result, "G-15"), "Duplicate IDs must BLOCK"

    def test_unique_ids_pass(self):
        from cert_prep.b2_assessment_agent import Assessment
        asmt = Assessment(
            student_name="Test", exam_target="AI-102",
            questions=[self._make_question(f"q{i}") for i in range(10)],
        )
        result = AssessmentGuardrails().check(asmt)
        assert not blocks_for(result, "G-15")


# ─── G-16: Content safety (harmful + PII) ────────────────────────────────────

class TestG16ContentSafety:
    def setup_method(self):
        self.guard = OutputContentGuardrails()

    # Harmful / BLOCK
    @pytest.mark.parametrize("text", [
        "I want to hack the system",
        "This contains malware",
        "Let me exploit the exam platform",
        "ransomware will fix this",
    ])
    def test_harmful_keywords_block(self, text):
        result = self.guard.check_text(text, "field")
        assert result.blocked, f"'{text}' must BLOCK"

    # PII / WARN (not block)
    @pytest.mark.parametrize("text,label", [
        ("My SSN is 123-45-6789", "SSN"),
        ("Card: 4111 1111 1111 1111", "Credit card"),
        ("Email me at user@domain.com", "Email in bio"),
        ("Call (555) 123-4567", "Phone number"),
        ("Server at 192.168.0.1", "IP address"),
    ])
    def test_pii_warns_but_does_not_block(self, text, label):
        result = self.guard.check_text(text, "background_text")
        pii_v = [v for v in result.violations if v.code == "G-16" and v.level == GuardrailLevel.WARN]
        assert pii_v, f"PII ({label}) must trigger G-16 WARN"
        assert not result.blocked, f"PII alone must not BLOCK: {label}"

    # Clean text
    @pytest.mark.parametrize("text", [
        "I am a senior software engineer with 8 years of Python.",
        "AI-102 Azure AI Engineer is my target certification.",
        "I want to build RAG solutions using Azure OpenAI.",
        "Pass the exam and get the badge!",
    ])
    def test_clean_text_no_g16(self, text):
        result = self.guard.check_text(text, "background_text")
        g16 = violations_for(result, "G-16")
        assert not g16, f"Clean text must not trigger G-16: {text!r}"


# ─── G-17: URL trust ─────────────────────────────────────────────────────────

class TestG17UrlTrust:
    def setup_method(self):
        self.guard = OutputContentGuardrails()

    @pytest.mark.parametrize("url", [
        "https://learn.microsoft.com/en-us/training/paths/prepare-for-ai-engineering/",
        "https://www.pearsonvue.com/microsoft",
        "https://aka.ms/azureopenai",
        "https://azure.microsoft.com/en-us/products/ai-services/",
    ])
    def test_trusted_urls_pass(self, url):
        result = self.guard.check_url(url)
        assert not violations_for(result, "G-17"), f"Trusted URL flagged: {url}"
        assert not result.blocked

    @pytest.mark.parametrize("url", [
        "https://randomsite.example.com/ai-102",
        "http://shady.phishing.site/cert",
        "https://notmicrosoft.ai/exam",
    ])
    def test_untrusted_urls_warn(self, url):
        result = self.guard.check_url(url)
        assert violations_for(result, "G-17"), f"Untrusted URL must warn: {url}"
        assert not result.blocked, "G-17 must WARN, never BLOCK"

    def test_empty_url_no_violation(self):
        result = self.guard.check_url("")
        assert not violations_for(result, "G-17")


# ─── GuardrailsPipeline façade ────────────────────────────────────────────────

class TestGuardrailsPipeline:
    def test_check_input_delegates_correctly(self):
        raw = make_raw()
        pipeline = GuardrailsPipeline()
        result = pipeline.check_input(raw)
        assert isinstance(result, GuardrailResult)

    def test_check_profile_delegates_correctly(self):
        profile = make_profile()
        pipeline = GuardrailsPipeline()
        result = pipeline.check_profile(profile)
        assert isinstance(result, GuardrailResult)

    def test_merge_combines_violations(self):
        pipeline = GuardrailsPipeline()
        raw1 = make_raw()
        raw2 = make_raw()
        raw2.student_name = ""
        r1 = pipeline.check_input(raw1)
        r2 = pipeline.check_input(raw2)
        merged = pipeline.merge(r1, r2)
        assert len(merged.violations) == len(r1.violations) + len(r2.violations)

    def test_merge_blocked_if_any_blocked(self):
        pipeline = GuardrailsPipeline()
        raw_bad = make_raw()
        raw_bad.student_name = ""
        r_bad = pipeline.check_input(raw_bad)
        raw_ok = make_raw()
        r_ok = pipeline.check_input(raw_ok)
        merged = pipeline.merge(r_ok, r_bad)
        assert merged.blocked

    def test_full_pipeline_valid_input_not_blocked(self):
        from cert_prep.b1_1_study_plan_agent import StudyPlanAgent
        pipeline = GuardrailsPipeline()
        raw     = make_raw()
        profile = make_profile()
        plan    = StudyPlanAgent().run(profile)
        snap    = make_snapshot(profile)

        r_input   = pipeline.check_input(raw)
        r_profile = pipeline.check_profile(profile)
        r_plan    = pipeline.check_study_plan(plan, profile)
        r_snap    = pipeline.check_progress_snapshot(snap)

        assert not r_input.blocked
        assert not r_profile.blocked
        assert not r_plan.blocked
        assert not r_snap.blocked
