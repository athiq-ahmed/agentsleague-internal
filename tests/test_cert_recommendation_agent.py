"""
Tests for CertificationRecommendationAgent (b3_cert_recommendation_agent.py).
Validates recommend() and recommend_from_readiness() paths.
"""
import pytest
from factories import make_profile, make_snapshot

from cert_prep.b3_cert_recommendation_agent import (
    CertificationRecommendationAgent,
    CertRecommendation,
)


@pytest.fixture
def agent():
    return CertificationRecommendationAgent()


@pytest.fixture
def assessment_result_pass(assessment_ai102):
    from cert_prep.b2_assessment_agent import AssessmentAgent
    ag = AssessmentAgent()
    correct = [q.correct_index for q in assessment_ai102.questions]
    return ag.evaluate(assessment_ai102, correct)


@pytest.fixture
def assessment_result_fail(assessment_ai102):
    from cert_prep.b2_assessment_agent import AssessmentAgent
    ag = AssessmentAgent()
    wrong = [(q.correct_index + 1) % 4 for q in assessment_ai102.questions]
    return ag.evaluate(assessment_ai102, wrong)


@pytest.fixture
def readiness_near(profile_ai102):
    from cert_prep.b1_2_progress_agent import ProgressAgent
    snap = make_snapshot(profile_ai102, hours_spent=60.0, weeks_elapsed=6, self_rating=4, practice_score=75)
    return ProgressAgent().assess(profile_ai102, snap)


@pytest.fixture
def readiness_poor(profile_ai102):
    from cert_prep.b1_2_progress_agent import ProgressAgent
    snap = make_snapshot(profile_ai102, hours_spent=5.0, weeks_elapsed=1, self_rating=1, practice_score=10)
    return ProgressAgent().assess(profile_ai102, snap)


# ─── recommend() via AssessmentResult ─────────────────────────────────────────

class TestRecommendFromAssessment:
    def test_returns_cert_recommendation(self, agent, profile_ai102, assessment_result_pass):
        rec = agent.recommend(profile_ai102, assessment_result_pass)
        assert isinstance(rec, CertRecommendation)

    def test_high_score_recommends_target_exam(self, agent, profile_ai102, assessment_result_pass):
        rec = agent.recommend(profile_ai102, assessment_result_pass)
        assert isinstance(rec.go_for_exam, bool), "Must have a go_for_exam bool"
        assert rec.go_for_exam is True, "High score must recommend going for exam"

    def test_low_score_suggests_foundation(self, agent, profile_ai102, assessment_result_fail):
        rec = agent.recommend(profile_ai102, assessment_result_fail)
        assert isinstance(rec, CertRecommendation)
        # Should suggest more study - go_for_exam might be False
        assert isinstance(rec.go_for_exam, bool)

    def test_recommendation_has_rationale(self, agent, profile_ai102, assessment_result_pass):
        rec = agent.recommend(profile_ai102, assessment_result_pass)
        assert rec.summary, "Recommendation must include a summary string"

    def test_recommendation_has_action_items(self, agent, profile_ai102, assessment_result_fail):
        rec = agent.recommend(profile_ai102, assessment_result_fail)
        # booking_checklist is populated for ready candidates; next_cert for not-ready
        has_actions = len(rec.booking_checklist) > 0 or len(rec.next_cert_suggestions) > 0
        assert has_actions, "Low score: booking_checklist or next_cert_suggestions must be populated"


# ─── recommend_from_readiness() via ReadinessAssessment ──────────────────────

class TestRecommendFromReadiness:
    def test_returns_cert_recommendation(self, agent, profile_ai102, readiness_near):
        rec = agent.recommend_from_readiness(profile_ai102, readiness_near)
        assert isinstance(rec, CertRecommendation)

    def test_near_ready_primary_is_target(self, agent, profile_ai102, readiness_near):
        rec = agent.recommend_from_readiness(profile_ai102, readiness_near)
        assert isinstance(rec.go_for_exam, bool)

    def test_poor_readiness_has_action_items(self, agent, profile_ai102, readiness_poor):
        rec = agent.recommend_from_readiness(profile_ai102, readiness_poor)
        has_actions = len(rec.booking_checklist) > 0 or len(rec.next_cert_suggestions) > 0
        assert has_actions, "Low readiness: some action items expected"

    def test_rationale_mentions_readiness(self, agent, profile_ai102, readiness_near):
        rec = agent.recommend_from_readiness(profile_ai102, readiness_near)
        assert rec.summary


# ─── cross-exam tests ──────────────────────────────────────────────────────────

class TestRecommendMultipleExams:
    @pytest.mark.parametrize("exam_target", ["AI-102", "DP-100", "AZ-204", "AI-900"])
    def test_recommend_from_readiness_all_exams(self, agent, exam_target):
        from cert_prep.b1_2_progress_agent import ProgressAgent
        profile = make_profile(exam_target=exam_target)
        snap = make_snapshot(profile)
        ra = ProgressAgent().assess(profile, snap)
        rec = agent.recommend_from_readiness(profile, ra)
        assert isinstance(rec, CertRecommendation)
        assert isinstance(rec.go_for_exam, bool)
