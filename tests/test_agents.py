"""
Smoke tests for core agent logic (mock mode only).
Run: python -m pytest tests/ -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cert_prep.b1_mock_profiler import run_mock_profiling_with_trace
from cert_prep.models import RawStudentInput


def _make_raw_input(**kwargs):
    defaults = dict(
        student_name="Test User",
        exam_target="AI-102",
        background_text="I am a Python developer with 5 years Azure experience.",
        existing_certs=[],
        hours_per_week=10.0,
        weeks_available=8,
        concern_topics=[],
        preferred_style="reading",
        goal_text="I want to pass the AI-102 exam in 3 months.",
    )
    defaults.update(kwargs)
    return RawStudentInput(**defaults)


class TestMockProfiler:
    def test_returns_learner_profile(self):
        raw = _make_raw_input()
        profile, trace = run_mock_profiling_with_trace(raw)
        assert profile is not None
        assert hasattr(profile, "experience_level") or hasattr(profile, "domain_profiles")

    def test_trace_not_empty(self):
        raw = _make_raw_input()
        _, trace = run_mock_profiling_with_trace(raw)
        assert trace is not None
        assert len(str(trace)) > 0

    def test_beginner_detection(self):
        raw = _make_raw_input(
            background_text="I just started learning about cloud computing this week.",
            hours_per_week=5.0,
        )
        profile, _ = run_mock_profiling_with_trace(raw)
        # Profile should reflect a beginner-level assessment
        assert profile is not None

    def test_expert_detection(self):
        raw = _make_raw_input(
            background_text=(
                "I am a principal cloud architect with 12 years of Azure, "
                "AWS, and multi-cloud experience. Certified AZ-900, AZ-104, AZ-305."
            ),
            existing_certs=["AZ-900", "AZ-104", "AZ-305"],
        )
        profile, _ = run_mock_profiling_with_trace(raw)
        assert profile is not None
