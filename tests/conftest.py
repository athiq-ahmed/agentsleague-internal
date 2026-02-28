"""
Shared pytest fixtures for the CertPrep multi-agent test suite.
All fixtures use mock mode — no Azure credentials required.
Factory helpers live in tests/factories.py so they can be imported
directly by test modules as well as being used here.
"""
import sys
import os

_tests_dir = os.path.dirname(__file__)
_src_dir   = os.path.join(_tests_dir, "..", "src")
for _p in (_tests_dir, _src_dir):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Force mock mode — never call Azure during tests
os.environ["FORCE_MOCK_MODE"] = "true"
os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "<placeholder>")
os.environ.setdefault("AZURE_OPENAI_API_KEY",  "<placeholder>")


import pytest

from factories import make_raw, make_profile, make_snapshot

from cert_prep.b1_1_study_plan_agent import StudyPlanAgent
from cert_prep.b2_assessment_agent import AssessmentAgent


# ─── pytest fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def raw_ai102():
    return make_raw(exam_target="AI-102")


@pytest.fixture
def raw_dp100():
    return make_raw(exam_target="DP-100")


@pytest.fixture
def profile_ai102():
    return make_profile(exam_target="AI-102")


@pytest.fixture
def profile_dp100():
    return make_profile(exam_target="DP-100")


@pytest.fixture
def study_plan_ai102(profile_ai102):
    return StudyPlanAgent().run(profile_ai102)


@pytest.fixture
def snapshot_ai102(profile_ai102):
    return make_snapshot(profile_ai102)


@pytest.fixture
def assessment_ai102(profile_ai102):
    return AssessmentAgent().generate(profile_ai102)
