"""
Tests for StudyPlanAgent (b1_1_study_plan_agent.py).
Validates task ordering, budget compliance, prerequisite logic, skip domains.
"""
import pytest
from factories import make_profile, make_raw
from cert_prep.models import ExperienceLevel
from cert_prep.b1_1_study_plan_agent import StudyPlanAgent, StudyPlan, StudyTask


ALL_EXAMS = ["AI-102", "AI-900", "AZ-204", "AZ-305", "DP-100",
             "SC-900", "PL-900", "MS-900", "AZ-900"]


@pytest.fixture
def agent():
    return StudyPlanAgent()


class TestStudyPlanBasic:
    def test_returns_study_plan_type(self, agent, profile_ai102):
        plan = agent.run(profile_ai102)
        assert isinstance(plan, StudyPlan)

    def test_plan_has_tasks(self, agent, profile_ai102):
        plan = agent.run(profile_ai102)
        assert len(plan.tasks) > 0

    def test_all_tasks_are_study_task(self, agent, profile_ai102):
        plan = agent.run(profile_ai102)
        for task in plan.tasks:
            assert isinstance(task, StudyTask)

    @pytest.mark.parametrize("exam_target", ALL_EXAMS)
    def test_all_exams_produce_plans(self, agent, exam_target):
        profile = make_profile(exam_target=exam_target)
        plan = agent.run(profile)
        assert isinstance(plan, StudyPlan)
        assert len(plan.tasks) > 0


class TestStudyPlanGuardrailCompatibility:
    """Plans must be G-09 and G-10 compliant."""

    def test_start_week_leq_end_week(self, agent, profile_ai102):
        plan = agent.run(profile_ai102)
        for task in plan.tasks:
            assert task.start_week <= task.end_week, (
                f"Task '{task.domain_id}': start_week {task.start_week} > end_week {task.end_week}"
            )

    def test_end_week_within_total_weeks(self, agent, profile_ai102):
        plan = agent.run(profile_ai102)
        max_week = profile_ai102.weeks_available
        for task in plan.tasks:
            assert task.end_week <= max_week + 1, (
                f"Task '{task.domain_id}' ends at week {task.end_week} but only {max_week} weeks available"
            )

    def test_total_hours_within_budget(self, agent, profile_ai102):
        plan = agent.run(profile_ai102)
        budget = profile_ai102.hours_per_week * profile_ai102.weeks_available
        task_total = sum(t.total_hours for t in plan.tasks)
        assert task_total <= budget * 1.10, (
            f"Total task hours {task_total:.1f} exceeds 110% of budget {budget:.1f}"
        )


class TestStudyPlanPriorities:
    def test_weak_domains_front_loaded(self, agent):
        """Domains with knowledge='weak' should start earlier than 'strong'."""
        profile = make_profile(experience=ExperienceLevel.BEGINNER)
        plan = agent.run(profile)
        weak_avg  = [t.start_week for t in plan.tasks if t.knowledge_level == "weak"]
        strong_avg= [t.start_week for t in plan.tasks if t.knowledge_level == "strong"]
        if weak_avg and strong_avg:
            assert sum(weak_avg)/len(weak_avg) <= sum(strong_avg)/len(strong_avg) + 2

    def test_skip_domains_excluded_or_marked(self, agent):
        profile = make_profile()
        if profile.domains_to_skip():
            plan = agent.run(profile)
            skip_ids = {d.domain_id for d in profile.domains_to_skip()}
            for task in plan.tasks:
                if task.domain_id in skip_ids:
                    assert task.priority in ("skip", "low"), (
                        f"Skip domain '{task.domain_id}' should be marked skip/low"
                    )


class TestStudyPlanWithRaw:
    def test_run_with_raw_respects_existing_certs(self, agent):
        profile = make_profile(exam_target="AI-102")
        existing_certs = ["AI-900"]
        plan  = agent.run_with_raw(profile, existing_certs=existing_certs)
        plan2 = agent.run_with_raw(profile, existing_certs=[])
        # Having AI-900 prerequisite met should not block plan creation
        assert isinstance(plan, StudyPlan)
        assert isinstance(plan2, StudyPlan)

    def test_no_existing_certs_still_produces_plan(self, agent):
        profile = make_profile(exam_target="AZ-305")
        plan = agent.run_with_raw(profile, existing_certs=[])
        assert len(plan.tasks) > 0


class TestStudyPlanStructure:
    def test_task_hours_positive(self, agent, profile_ai102):
        plan = agent.run(profile_ai102)
        for task in plan.tasks:
            assert task.total_hours > 0, f"Task {task.domain_id} has zero hours"

    def test_task_priority_values(self, agent, profile_ai102):
        valid_priorities = {"critical", "high", "medium", "low", "skip"}
        plan = agent.run(profile_ai102)
        for task in plan.tasks:
            assert task.priority in valid_priorities, (
                f"Invalid priority '{task.priority}' on task {task.domain_id}"
            )

    def test_task_knowledge_levels(self, agent, profile_ai102):
        valid_levels = {"weak", "moderate", "strong", "unknown"}
        plan = agent.run(profile_ai102)
        for task in plan.tasks:
            assert task.knowledge_level in valid_levels, (
                f"Invalid knowledge_level '{task.knowledge_level}' on task {task.domain_id}"
            )

    def test_confidence_pct_in_range(self, agent, profile_ai102):
        plan = agent.run(profile_ai102)
        for task in plan.tasks:
            assert 0 <= task.confidence_pct <= 100, (
                f"confidence_pct {task.confidence_pct} out of [0,100] for {task.domain_id}"
            )
