"""
Factory helpers for building test objects.
Imported by conftest.py fixtures AND directly by test modules.
"""
import sys
import os

# Ensure both src/ and tests/ are importable in all test files
_tests_dir = os.path.dirname(__file__)
_src_dir   = os.path.join(_tests_dir, "..", "src")
for _p in (_tests_dir, _src_dir):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Force mock mode (safe to call multiple times)
os.environ["FORCE_MOCK_MODE"] = "true"
os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "<placeholder>")
os.environ.setdefault("AZURE_OPENAI_API_KEY",  "<placeholder>")

from cert_prep.models import (
    RawStudentInput,
    LearnerProfile,
    DomainProfile,
    DomainKnowledge,
    ExperienceLevel,
    LearningStyle,
    get_exam_domains,
)
from cert_prep.b1_2_progress_agent import (
    ProgressSnapshot,
    DomainProgress,
)


def make_raw(
    exam_target: str = "AI-102",
    hours_per_week: float = 10.0,
    weeks: int = 8,
    certs: list | None = None,
    background: str = "I am a Python developer with 5 years Azure experience.",
    goal: str = "I want to pass the AI-102 exam.",
    email: str = "",
) -> RawStudentInput:
    return RawStudentInput(
        student_name    = "Test User",
        exam_target     = exam_target,
        background_text = background,
        existing_certs  = certs or [],
        hours_per_week  = hours_per_week,
        weeks_available = weeks,
        concern_topics  = [],
        preferred_style = "reading",
        goal_text       = goal,
        email           = email,
    )


def make_profile(
    exam_target: str = "AI-102",
    hours_per_week: float = 10.0,
    weeks: int = 8,
    experience: ExperienceLevel = ExperienceLevel.INTERMEDIATE,
    risk_domains: list | None = None,
) -> LearnerProfile:
    domains = get_exam_domains(exam_target)
    domain_profiles = [
        DomainProfile(
            domain_id        = d["id"],
            domain_name      = d["name"],
            knowledge_level  = DomainKnowledge.MODERATE,
            confidence_score = 0.55,
            skip_recommended = False,
            notes            = "Standard test profile",
        )
        for d in domains
    ]
    return LearnerProfile(
        student_name         = "Test User",
        exam_target          = exam_target,
        experience_level     = experience,
        learning_style       = LearningStyle.LINEAR,
        hours_per_week       = hours_per_week,
        weeks_available      = weeks,
        total_budget_hours   = hours_per_week * weeks,
        domain_profiles      = domain_profiles,
        modules_to_skip      = [],
        risk_domains         = risk_domains or [domains[0]["id"]],
        analogy_map          = {},
        recommended_approach = "Standard test approach.",
        engagement_notes     = "Test notes.",
    )


def make_snapshot(
    profile: LearnerProfile,
    hours_spent: float = 40.0,
    weeks_elapsed: int = 4,
    self_rating: int = 3,
    practice_done: str = "some",
    practice_score: int | None = 65,
) -> ProgressSnapshot:
    domains = get_exam_domains(profile.exam_target)
    dp_list = [
        DomainProgress(
            domain_id   = d["id"],
            domain_name = d["name"],
            self_rating = self_rating,
            hours_spent = hours_spent / len(domains),
        )
        for d in domains
    ]
    return ProgressSnapshot(
        total_hours_spent  = hours_spent,
        weeks_elapsed      = weeks_elapsed,
        domain_progress    = dp_list,
        done_practice_exam = practice_done,
        practice_score_pct = practice_score,
        email              = "",
        notes              = "",
    )
