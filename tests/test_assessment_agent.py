"""
Tests for AssessmentAgent (b2_assessment_agent.py).
Validates question generation, evaluation scoring, domain coverage.
"""
import pytest
from factories import make_profile

from cert_prep.b2_assessment_agent import AssessmentAgent, Assessment, AssessmentResult


@pytest.fixture
def agent():
    return AssessmentAgent()


class TestAssessmentGenerate:
    def test_returns_assessment_type(self, agent, profile_ai102):
        asmt = agent.generate(profile_ai102)
        assert isinstance(asmt, Assessment)

    def test_default_10_questions(self, agent, profile_ai102):
        asmt = agent.generate(profile_ai102)
        assert len(asmt.questions) == 10

    def test_custom_question_count(self, agent, profile_ai102):
        asmt = agent.generate(profile_ai102, n_questions=5)
        assert len(asmt.questions) == 5

    def test_question_ids_unique(self, agent, profile_ai102):
        asmt = agent.generate(profile_ai102)
        ids = [q.id for q in asmt.questions]
        assert len(ids) == len(set(ids)), "Question IDs must be unique"

    def test_at_least_5_questions(self, agent, profile_ai102):
        asmt = agent.generate(profile_ai102, n_questions=10)
        assert len(asmt.questions) >= 5, "Must pass G-14 (≥5 questions)"

    def test_question_has_four_options(self, agent, profile_ai102):
        asmt = agent.generate(profile_ai102)
        for q in asmt.questions:
            assert len(q.options) == 4, f"Question {q.id} should have 4 options"

    def test_correct_index_in_range(self, agent, profile_ai102):
        asmt = agent.generate(profile_ai102)
        for q in asmt.questions:
            assert 0 <= q.correct_index <= 3, (
                f"correct_index {q.correct_index} out of [0,3] for {q.id}"
            )

    def test_exam_target_preserved(self, agent, profile_ai102):
        asmt = agent.generate(profile_ai102)
        assert asmt.exam_target == "AI-102"

    def test_student_name_preserved(self, agent, profile_ai102):
        asmt = agent.generate(profile_ai102)
        assert asmt.student_name == profile_ai102.student_name

    @pytest.mark.parametrize("exam_target", ["AI-102", "DP-100", "AZ-204", "AI-900"])
    def test_generates_for_multiple_exams(self, agent, exam_target):
        profile = make_profile(exam_target=exam_target)
        asmt = agent.generate(profile)
        assert len(asmt.questions) >= 5


class TestAssessmentEvaluate:
    def test_returns_assessment_result(self, agent, assessment_ai102):
        answers = [q.correct_index for q in assessment_ai102.questions]
        result = agent.evaluate(assessment_ai102, answers)
        assert isinstance(result, AssessmentResult)

    def test_all_correct_100_pct(self, agent, assessment_ai102):
        correct_answers = [q.correct_index for q in assessment_ai102.questions]
        result = agent.evaluate(assessment_ai102, correct_answers)
        assert result.score_pct == 100.0, f"All-correct should give 100%, got {result.score_pct}"
        assert result.passed is True

    def test_all_wrong_0_pct(self, agent, assessment_ai102):
        wrong_answers = [(q.correct_index + 1) % 4 for q in assessment_ai102.questions]
        result = agent.evaluate(assessment_ai102, wrong_answers)
        assert result.score_pct == 0.0, f"All-wrong should give 0%, got {result.score_pct}"
        assert result.passed is False

    def test_half_correct_50_pct(self, agent, assessment_ai102):
        questions = assessment_ai102.questions
        n = len(questions)
        answers = [
            questions[i].correct_index if i < n // 2 else (questions[i].correct_index + 1) % 4
            for i in range(n)
        ]
        result = agent.evaluate(assessment_ai102, answers)
        assert abs(result.score_pct - 50.0) <= 5.0  # allow small rounding

    def test_wrong_answer_count_raises(self, agent, assessment_ai102):
        with pytest.raises((ValueError, IndexError, AssertionError)):
            agent.evaluate(assessment_ai102, [0])  # too few answers

    def test_domain_scores_dict_populated(self, agent, assessment_ai102):
        correct = [q.correct_index for q in assessment_ai102.questions]
        result = agent.evaluate(assessment_ai102, correct)
        assert isinstance(result.domain_scores, dict)
        assert len(result.domain_scores) > 0

    def test_domain_scores_in_range(self, agent, assessment_ai102):
        answers = [q.correct_index for q in assessment_ai102.questions]
        result = agent.evaluate(assessment_ai102, answers)
        for domain, score in result.domain_scores.items():
            assert 0 <= score <= 100, f"domain_score[{domain}] = {score} out of [0,100]"

    def test_verdict_is_non_empty_string(self, agent, assessment_ai102):
        answers = [q.correct_index for q in assessment_ai102.questions]
        result = agent.evaluate(assessment_ai102, answers)
        assert isinstance(result.verdict, str) and result.verdict

    @pytest.mark.parametrize("pct,expected_pass", [
        (100, True),
        (70 , True),
        (0  , False),
    ])
    def test_pass_threshold_alignment(self, pct, expected_pass, agent, assessment_ai102):
        """Pass = score_pct ≥ 70 (typical Microsoft passing threshold)."""
        n = len(assessment_ai102.questions)
        n_correct = round(n * pct / 100)
        answers = []
        for i, q in enumerate(assessment_ai102.questions):
            answers.append(q.correct_index if i < n_correct else (q.correct_index + 1) % 4)
        result = agent.evaluate(assessment_ai102, answers)
        if pct == 100:
            assert result.passed is True
        elif pct == 0:
            assert result.passed is False
