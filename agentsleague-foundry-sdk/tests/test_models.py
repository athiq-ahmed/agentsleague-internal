"""
Tests for data models: RawStudentInput, DomainProfile, LearnerProfile,
get_exam_domains registry, and model helper methods.
"""
import pytest
from factories import make_raw, make_profile

from cert_prep.models import (
    RawStudentInput,
    LearnerProfile,
    DomainProfile,
    DomainKnowledge,
    ExperienceLevel,
    LearningStyle,
    EXAM_DOMAIN_REGISTRY,
    get_exam_domains,
    EXAM_DOMAINS,
)


# ─── RawStudentInput ──────────────────────────────────────────────────────────

class TestRawStudentInput:
    def test_basic_construction(self):
        raw = make_raw()
        assert raw.student_name == "Test User"
        assert raw.exam_target  == "AI-102"
        assert raw.hours_per_week == 10.0
        assert raw.weeks_available == 8

    def test_email_defaults_empty(self):
        raw = make_raw()
        assert raw.email == ""

    def test_email_field_set(self):
        raw = make_raw(email="user@example.com")
        assert raw.email == "user@example.com"

    def test_total_budget_calculation(self):
        """hours_per_week × weeks_available = total study budget."""
        raw = make_raw(hours_per_week=15.0, weeks=6)
        assert raw.hours_per_week * raw.weeks_available == pytest.approx(90.0)

    def test_existing_certs_default_empty(self):
        raw = make_raw()
        assert raw.existing_certs == []

    def test_existing_certs_set(self):
        raw = make_raw(certs=["AZ-900", "AI-900"])
        assert "AZ-900" in raw.existing_certs
        assert len(raw.existing_certs) == 2

    def test_all_exam_targets_constructable(self):
        for code in ["AI-102", "AI-900", "AZ-204", "AZ-305", "DP-100"]:
            raw = make_raw(exam_target=code)
            assert raw.exam_target == code


# ─── get_exam_domains registry ────────────────────────────────────────────────

class TestExamDomainRegistry:
    def test_all_registered_exams_return_non_empty(self):
        for code in ["AI-102", "AI-900", "AZ-204", "DP-100", "AZ-305"]:
            domains = get_exam_domains(code)
            assert len(domains) >= 4, f"{code} should have ≥4 domains"

    def test_unknown_exam_returns_fallback(self):
        """Unregistered exam codes fall back to AI-102 domain blueprint."""
        domains = get_exam_domains("ZZ-999")
        assert domains == EXAM_DOMAINS

    def test_domain_dicts_have_required_keys(self):
        for code, domain_list in EXAM_DOMAIN_REGISTRY.items():
            for d in domain_list:
                assert "id"     in d, f"{code}: domain missing 'id'"
                assert "name"   in d, f"{code}: domain missing 'name'"
                assert "weight" in d, f"{code}: domain missing 'weight'"

    def test_domain_weights_sum_to_approx_one(self):
        for code, domain_list in EXAM_DOMAIN_REGISTRY.items():
            total = sum(d["weight"] for d in domain_list)
            assert 0.95 <= total <= 1.05, \
                f"{code} weights sum to {total:.3f}, expected ~1.0"

    def test_domain_ids_unique_per_exam(self):
        for code, domain_list in EXAM_DOMAIN_REGISTRY.items():
            ids = [d["id"] for d in domain_list]
            assert len(ids) == len(set(ids)), \
                f"{code} has duplicate domain IDs: {ids}"

    def test_dp100_domains_registered(self):
        dp100 = get_exam_domains("DP-100")
        ids = [d["id"] for d in dp100]
        assert "explore_train_models" in ids

    def test_az204_domains_registered(self):
        az204 = get_exam_domains("AZ-204")
        ids = [d["id"] for d in az204]
        assert "compute_solutions" in ids

    def test_case_insensitive_lookup(self):
        lower = get_exam_domains("ai-102")
        upper = get_exam_domains("AI-102")
        assert lower == upper


# ─── DomainProfile ────────────────────────────────────────────────────────────

class TestDomainProfile:
    def test_confidence_score_bounds(self):
        dp = DomainProfile(
            domain_id="plan_manage",
            domain_name="Plan & Manage",
            knowledge_level=DomainKnowledge.MODERATE,
            confidence_score=0.65,
            skip_recommended=False,
            notes="",
        )
        assert 0.0 <= dp.confidence_score <= 1.0

    def test_confidence_score_zero(self):
        dp = DomainProfile(
            domain_id="nlp",
            domain_name="NLP",
            knowledge_level=DomainKnowledge.UNKNOWN,
            confidence_score=0.0,
            skip_recommended=False,
            notes="",
        )
        assert dp.confidence_score == 0.0

    def test_confidence_score_one(self):
        dp = DomainProfile(
            domain_id="nlp",
            domain_name="NLP",
            knowledge_level=DomainKnowledge.STRONG,
            confidence_score=1.0,
            skip_recommended=True,
            notes="",
        )
        assert dp.confidence_score == 1.0

    def test_pydantic_rejects_out_of_range_confidence(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            DomainProfile(
                domain_id="nlp",
                domain_name="NLP",
                knowledge_level=DomainKnowledge.STRONG,
                confidence_score=1.5,   # invalid
                skip_recommended=False,
                notes="",
            )


# ─── LearnerProfile helpers ───────────────────────────────────────────────────

class TestLearnerProfile:
    def test_domains_to_skip_returns_skip_ids(self):
        profile = make_profile()
        # Override one domain as skip
        profile.domain_profiles[0].skip_recommended = True
        skips = profile.domains_to_skip()
        assert profile.domain_profiles[0].domain_id in skips

    def test_domains_to_skip_empty_when_none_skipped(self):
        profile = make_profile()
        for dp in profile.domain_profiles:
            dp.skip_recommended = False
        assert profile.domains_to_skip() == []

    def test_weak_domains_returns_unknown_and_weak(self):
        profile = make_profile()
        profile.domain_profiles[0].knowledge_level = DomainKnowledge.UNKNOWN
        profile.domain_profiles[1].knowledge_level = DomainKnowledge.WEAK
        weak = profile.weak_domains()
        assert profile.domain_profiles[0].domain_id in weak
        assert profile.domain_profiles[1].domain_id in weak

    def test_domain_by_id_found(self):
        profile = make_profile()
        first_id = profile.domain_profiles[0].domain_id
        dp = profile.domain_by_id(first_id)
        assert dp is not None
        assert dp.domain_id == first_id

    def test_domain_by_id_not_found_returns_none(self):
        profile = make_profile()
        dp = profile.domain_by_id("nonexistent_domain_xyz")
        assert dp is None

    def test_total_budget_hours_matches_input(self):
        profile = make_profile(hours_per_week=12.0, weeks=10)
        assert profile.total_budget_hours == pytest.approx(120.0)

    @pytest.mark.parametrize("exam", ["AI-102", "DP-100", "AZ-204", "AZ-305"])
    def test_profile_constructable_for_all_exams(self, exam):
        profile = make_profile(exam_target=exam)
        assert profile.exam_target == exam
        assert len(profile.domain_profiles) >= 4
