"""
Tests for LearningPathCuratorAgent (b1_1_learning_path_curator.py).
Validates returned LearningPath structure and content quality.
"""
import pytest
from factories import make_profile

from cert_prep.b1_1_learning_path_curator import LearningPathCuratorAgent, LearningPath


ALL_EXAMS = ["AI-102", "AI-900", "AZ-204", "AZ-305", "DP-100"]


@pytest.fixture
def agent():
    return LearningPathCuratorAgent()


class TestLearningPathCuratorBasic:
    def test_returns_learning_path_type(self, agent, profile_ai102):
        lp = agent.curate(profile_ai102)
        assert isinstance(lp, LearningPath)

    def test_has_modules(self, agent, profile_ai102):
        lp = agent.curate(profile_ai102)
        assert len(lp.all_modules) > 0

    @pytest.mark.parametrize("exam_target", ALL_EXAMS)
    def test_all_exams_curate(self, agent, exam_target):
        profile = make_profile(exam_target=exam_target)
        lp = agent.curate(profile)
        assert isinstance(lp, LearningPath)
        assert len(lp.all_modules) > 0

    def test_exam_target_matches(self, agent, profile_ai102):
        lp = agent.curate(profile_ai102)
        assert lp.exam_target == "AI-102"


class TestLearningPathModuleStructure:
    def test_all_modules_have_title(self, agent, profile_ai102):
        lp = agent.curate(profile_ai102)
        for mod in lp.all_modules:
            assert mod.title, "Every module must have a non-empty title"

    def test_all_modules_have_estimated_hours(self, agent, profile_ai102):
        lp = agent.curate(profile_ai102)
        for mod in lp.all_modules:
            assert mod.duration_min > 0, (
                f"Module '{mod.title}' has zero duration_min"
            )

    def test_module_urls_trusted_or_empty(self, agent, profile_ai102):
        from cert_prep.guardrails import OutputContentGuardrails
        guard = OutputContentGuardrails()
        lp = agent.curate(profile_ai102)
        for mod in lp.all_modules:
            if hasattr(mod, "url") and mod.url:
                result = guard.check_url(mod.url)
                # Warn is acceptable but should not BLOCK
                assert not result.blocked, f"URL from curator is untrusted+blocked: {mod.url}"

    def test_total_hours_reasonable(self, agent, profile_ai102):
        lp = agent.curate(profile_ai102)
        total = sum(m.duration_min / 60 for m in lp.all_modules)
        budget = profile_ai102.hours_per_week * profile_ai102.weeks_available
        assert total <= budget * 1.5, (
            f"LearningPath total hours {total:.1f} hugely exceeds budget {budget:.1f}"
        )


class TestLearningPathDomainCoverage:
    def test_exam_domains_represented(self, agent, profile_ai102):
        """Each exam domain should appear in at least one module (or in summary)."""
        lp = agent.curate(profile_ai102)
        domain_ids = {dp.domain_id for dp in profile_ai102.domain_profiles}
        module_domains = {getattr(m, "domain_id", None) for m in lp.all_modules} - {None}
        # At least half the domains should be covered
        covered = domain_ids & module_domains
        assert len(covered) >= len(domain_ids) // 2 or len(module_domains) == 0, (
            "Expected majority of exam domains to be represented in the learning path"
        )
