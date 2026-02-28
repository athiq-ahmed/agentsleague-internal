"""
End-to-end pipeline integration tests.
Runs the full agent chain in mocked mode (no Azure):
Intake → Profile → StudyPlan → LearningPath → Progress → Assessment → Recommendation
"""
import pytest
from factories import make_raw, make_profile, make_snapshot

from cert_prep.b0_intake_agent import LearnerProfilingAgent  # noqa: F401 (kept for reference; init requires Azure)  
from cert_prep.b1_1_study_plan_agent import StudyPlanAgent
from cert_prep.b1_1_learning_path_curator import LearningPathCuratorAgent
from cert_prep.b1_2_progress_agent import ProgressAgent, ReadinessVerdict
from cert_prep.b2_assessment_agent import AssessmentAgent
from cert_prep.b3_cert_recommendation_agent import CertificationRecommendationAgent
from cert_prep.guardrails import GuardrailsPipeline


@pytest.fixture(scope="module")
def pipeline_agents():
    return {
        "study_plan": StudyPlanAgent(),
        "lp"        : LearningPathCuratorAgent(),
        "progress"  : ProgressAgent(),
        "assessment": AssessmentAgent(),
        "recommend" : CertificationRecommendationAgent(),
        "guardrails": GuardrailsPipeline(),
    }


class TestFullPipelineAI102:
    """Run entire chain for AI-102 and assert each stage produces expected output."""

    def test_intake_produces_profile(self, pipeline_agents):
        """LearnerProfilingAgent requires Azure, so we simulate with factory."""
        profile = make_profile(exam_target="AI-102")
        assert profile.exam_target == "AI-102"
        assert len(profile.domain_profiles) > 0

    def test_study_plan_valid(self, pipeline_agents, profile_ai102):
        plan = pipeline_agents["study_plan"].run(profile_ai102)
        assert len(plan.tasks) > 0
        for task in plan.tasks:
            assert task.start_week <= task.end_week

    def test_learning_path_valid(self, pipeline_agents, profile_ai102):
        lp = pipeline_agents["lp"].curate(profile_ai102)
        assert len(lp.all_modules) > 0

    def test_progress_assessment_valid(self, pipeline_agents, profile_ai102, snapshot_ai102):
        ra = pipeline_agents["progress"].assess(profile_ai102, snapshot_ai102)
        assert 0 <= ra.readiness_pct <= 100
        assert ra.verdict

    def test_assessment_valid(self, pipeline_agents, profile_ai102, assessment_ai102):
        assert len(assessment_ai102.questions) >= 5
        ids = [q.id for q in assessment_ai102.questions]
        assert len(ids) == len(set(ids))

    def test_evaluation_valid(self, pipeline_agents, assessment_ai102):
        ag = pipeline_agents["assessment"]
        correct = [q.correct_index for q in assessment_ai102.questions]
        result = ag.evaluate(assessment_ai102, correct)
        assert result.score_pct == 100.0
        assert result.passed is True

    def test_recommendation_from_assessment(self, pipeline_agents, profile_ai102, assessment_ai102):
        ag_eval = pipeline_agents["assessment"]
        correct = [q.correct_index for q in assessment_ai102.questions]
        result = ag_eval.evaluate(assessment_ai102, correct)
        rec = pipeline_agents["recommend"].recommend(profile_ai102, result)
        assert isinstance(rec.go_for_exam, bool)

    def test_recommendation_from_readiness(self, pipeline_agents, profile_ai102, snapshot_ai102):
        ra  = pipeline_agents["progress"].assess(profile_ai102, snapshot_ai102)
        rec = pipeline_agents["recommend"].recommend_from_readiness(profile_ai102, ra)
        assert isinstance(rec.go_for_exam, bool)


class TestGuardrailsInPipeline:
    """Guardrails must pass silently for a clean end-to-end run."""

    def test_guardrails_not_blocked_on_valid_data(self, pipeline_agents, profile_ai102, snapshot_ai102):
        gp = pipeline_agents["guardrails"]
        raw    = make_raw()
        plan   = pipeline_agents["study_plan"].run(profile_ai102)

        r1 = gp.check_input(raw)
        r2 = gp.check_profile(profile_ai102)
        r3 = gp.check_study_plan(plan, profile_ai102)
        r4 = gp.check_progress_snapshot(snapshot_ai102)

        for r, name in [(r1,"input"),(r2,"profile"),(r3,"study_plan"),(r4,"snapshot")]:
            assert not r.blocked, f"Guardrail stage '{name}' unexpectedly blocked"


class TestPipelineCrossExam:
    @pytest.mark.parametrize("exam_target", ["AI-900", "AZ-204", "DP-100"])
    def test_minimal_pipeline(self, exam_target):
        profile = make_profile(exam_target=exam_target)
        snap    = make_snapshot(profile)

        plan    = StudyPlanAgent().run(profile)
        lp      = LearningPathCuratorAgent().curate(profile)
        ra      = ProgressAgent().assess(profile, snap)
        rec     = CertificationRecommendationAgent().recommend_from_readiness(profile, ra)

        assert len(plan.tasks) > 0
        assert len(lp.all_modules) > 0
        assert 0 <= ra.readiness_pct <= 100
        assert isinstance(rec.go_for_exam, bool)


class TestPipelineEdgeCases:
    def test_beginner_profile_full_pipeline(self):
        from cert_prep.models import ExperienceLevel
        profile = make_profile(exam_target="AI-900", experience=ExperienceLevel.BEGINNER, weeks=4)
        snap    = make_snapshot(profile, hours_spent=5.0, self_rating=1, practice_score=20)
        ra      = ProgressAgent().assess(profile, snap)
        assert ra.verdict in (ReadinessVerdict.NOT_READY, ReadinessVerdict.NEEDS_WORK, ReadinessVerdict.NEARLY_READY, ReadinessVerdict.EXAM_READY)

    def test_expert_profile_full_pipeline(self):
        from cert_prep.models import ExperienceLevel
        profile = make_profile(exam_target="AZ-305", experience=ExperienceLevel.EXPERT_ML, weeks=4)
        snap    = make_snapshot(profile, hours_spent=40.0, self_rating=5, practice_score=90)
        ra      = ProgressAgent().assess(profile, snap)
        assert ra.readiness_pct >= 45  # expert starting point should be reasonable
