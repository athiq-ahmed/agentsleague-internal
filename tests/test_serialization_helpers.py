"""
Tests for serialization / deserialization helper patterns used in streamlit_app.py.

These tests validate:
1. _dc_filter  — unknown keys are silently dropped; known keys are retained
2. ReadinessVerdict coercion — invalid enum values fall back to NEEDS_WORK
3. NudgeLevel coercion      — invalid enum values fall back to INFO
4. ProgressSnapshot round-trip — extra/missing keys handled gracefully
5. ReadinessAssessment round-trip — invalid verdict handled gracefully
6. StudyPlan round-trip — extra keys from schema evolution handled
7. LearningPath round-trip — extra keys handled
8. Assessment round-trip — extra keys handled
9. AssessmentResult round-trip — extra keys handled
"""
import dataclasses
import pytest

# Ensure src/ is on path (conftest.py already does this, but be explicit)
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cert_prep.b1_2_progress_agent import (
    ProgressSnapshot, DomainProgress,
    ReadinessAssessment, ReadinessVerdict, NudgeLevel, Nudge,
    DomainStatusLine,
)
from cert_prep.b1_1_study_plan_agent import StudyPlan, StudyTask, PrereqInfo
from cert_prep.b1_1_learning_path_curator import LearningPath, LearningModule
from cert_prep.b2_assessment_agent import (
    Assessment, AssessmentResult, QuizQuestion, QuestionFeedback,
)


# ─── Helper: the _dc_filter pattern ─────────────────────────────────────────

def dc_filter(cls, d: dict) -> dict:
    """Mirror of the _dc_filter helper in streamlit_app.py."""
    known = {f.name for f in dataclasses.fields(cls)}
    return {k: v for k, v in d.items() if k in known}


# ─── _dc_filter logic ────────────────────────────────────────────────────────

class TestDcFilter:
    def test_drops_unknown_keys(self):
        raw = {"domain_id": "d1", "domain_name": "D1", "self_rating": 3, "hours_spent": 5.0, "FUTURE_FIELD": "oops"}
        filtered = dc_filter(DomainProgress, raw)
        assert "FUTURE_FIELD" not in filtered
        assert "domain_id" in filtered

    def test_retains_all_known_keys(self):
        raw = {"domain_id": "d1", "domain_name": "D1", "self_rating": 3, "hours_spent": 5.0}
        filtered = dc_filter(DomainProgress, raw)
        assert set(filtered.keys()) == {"domain_id", "domain_name", "self_rating", "hours_spent"}

    def test_unknown_key_without_filter_causes_type_error(self):
        """Demonstrate why _dc_filter is needed: extra keys crash the constructor."""
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            DomainProgress(domain_id="d1", domain_name="D1", self_rating=3, hours_spent=5.0,
                           FUTURE_FIELD="oops")  # type: ignore[call-arg]

    def test_filtered_dict_constructs_cleanly(self):
        raw = {"domain_id": "d1", "domain_name": "D1", "self_rating": 3, "hours_spent": 5.0,
               "FUTURE_FIELD": "oops"}
        dp = DomainProgress(**dc_filter(DomainProgress, raw))
        assert dp.domain_id == "d1"


# ─── ReadinessVerdict coercion ────────────────────────────────────────────────

class TestReadinessVerdictCoercion:
    def test_valid_verdict_coerces(self):
        assert ReadinessVerdict("exam_ready") == ReadinessVerdict.EXAM_READY

    def test_invalid_verdict_raises_value_error(self):
        """Demonstrate the raw enum call fails on stale/invalid values."""
        with pytest.raises(ValueError):
            ReadinessVerdict("stale_verdict_that_no_longer_exists")

    def test_safe_coerce_pattern_falls_back_to_needs_work(self):
        """The pattern used in _readiness_assessment_from_dict must not raise."""
        _valid_verdicts = {e.value for e in ReadinessVerdict}
        raw_value = "stale_verdict_that_no_longer_exists"
        verdict = ReadinessVerdict(raw_value) if raw_value in _valid_verdicts else ReadinessVerdict.NEEDS_WORK
        assert verdict == ReadinessVerdict.NEEDS_WORK

    def test_safe_coerce_uses_real_value_when_valid(self):
        _valid_verdicts = {e.value for e in ReadinessVerdict}
        for v in ["exam_ready", "nearly_ready", "needs_work", "not_ready"]:
            result = ReadinessVerdict(v) if v in _valid_verdicts else ReadinessVerdict.NEEDS_WORK
            assert isinstance(result, ReadinessVerdict)

    def test_missing_verdict_key_falls_back(self):
        """If 'verdict' key is absent from stored JSON, should not KeyError."""
        _valid_verdicts = {e.value for e in ReadinessVerdict}
        raw = {}
        raw_val = raw.get("verdict", "")
        verdict = ReadinessVerdict(raw_val) if raw_val in _valid_verdicts else ReadinessVerdict.NEEDS_WORK
        assert verdict == ReadinessVerdict.NEEDS_WORK


# ─── NudgeLevel coercion ─────────────────────────────────────────────────────

class TestNudgeLevelCoercion:
    def test_valid_values_coerce(self):
        for v in ["danger", "warning", "info", "success"]:
            assert NudgeLevel(v) in NudgeLevel

    def test_invalid_level_falls_back_to_info(self):
        _valid = {e.value for e in NudgeLevel}
        level_raw = "critical"   # not a current NudgeLevel value
        result = NudgeLevel(level_raw) if level_raw in _valid else NudgeLevel.INFO
        assert result == NudgeLevel.INFO


# ─── ProgressSnapshot round-trip ─────────────────────────────────────────────

def _progress_snapshot_from_dict(d: dict) -> ProgressSnapshot:
    """Local mirror of the fixed streamlit_app.py helper."""
    d2 = dc_filter(ProgressSnapshot, d)
    d2["domain_progress"] = [
        DomainProgress(**dc_filter(DomainProgress, dp))
        for dp in d.get("domain_progress", [])
    ]
    return ProgressSnapshot(**d2)


class TestProgressSnapshotFromDict:
    def _base_dict(self):
        return {
            "total_hours_spent": 20.0,
            "weeks_elapsed":     3,
            "domain_progress":   [
                {"domain_id": "d1", "domain_name": "D1", "self_rating": 4, "hours_spent": 10.0},
            ],
            "done_practice_exam": "no",
            "practice_score_pct": None,
            "email":             "test@example.com",
            "notes":             "",
        }

    def test_round_trip_clean_dict(self):
        snap = _progress_snapshot_from_dict(self._base_dict())
        assert snap.total_hours_spent == 20.0
        assert len(snap.domain_progress) == 1

    def test_extra_top_level_key_handled(self):
        d = self._base_dict()
        d["FUTURE_FIELD"] = "unknown"
        snap = _progress_snapshot_from_dict(d)  # must not raise TypeError
        assert snap.total_hours_spent == 20.0

    def test_extra_nested_dp_key_handled(self):
        d = self._base_dict()
        d["domain_progress"][0]["EXTRA"] = "x"
        snap = _progress_snapshot_from_dict(d)   # must not raise
        assert snap.domain_progress[0].domain_id == "d1"

    def test_empty_domain_progress_list(self):
        d = self._base_dict()
        d["domain_progress"] = []
        snap = _progress_snapshot_from_dict(d)
        assert snap.domain_progress == []


# ─── StudyPlan round-trip ─────────────────────────────────────────────────────

def _study_plan_from_dict(d: dict) -> StudyPlan:
    d2 = dc_filter(StudyPlan, d)
    d2["tasks"] = [StudyTask(**dc_filter(StudyTask, t)) for t in d.get("tasks", [])]
    d2["prerequisites"] = [PrereqInfo(**dc_filter(PrereqInfo, p)) for p in d.get("prerequisites", [])]
    return StudyPlan(**d2)


_STUDY_PLAN_DICT = {
    "student_name": "Alice",
    "exam_target":  "AI-102",
    "total_weeks":  8,
    "total_hours":  80.0,
    "tasks": [
        {
            "domain_id": "ai102_d1", "domain_name": "Domain 1",
            "start_week": 1, "end_week": 2, "total_hours": 10.0,
            "priority": "high", "knowledge_level": "beginner", "confidence_pct": 30.0,
        }
    ],
    "review_start_week": 7,
    "prerequisites": [],
    "prereq_gap":    False,
    "prereq_message": "",
    "plan_summary":  "Good plan",
}


class TestStudyPlanFromDict:
    def test_clean_round_trip(self):
        plan = _study_plan_from_dict(_STUDY_PLAN_DICT)
        assert plan.student_name == "Alice"
        assert len(plan.tasks) == 1

    def test_extra_top_level_key_dropped(self):
        d = {**_STUDY_PLAN_DICT, "FUTURE_KEY": "oops"}
        plan = _study_plan_from_dict(d)   # must not raise
        assert plan.student_name == "Alice"

    def test_extra_task_key_dropped(self):
        d = {**_STUDY_PLAN_DICT, "tasks": [{**_STUDY_PLAN_DICT["tasks"][0], "NEW_FIELD": "x"}]}
        plan = _study_plan_from_dict(d)   # must not raise
        assert plan.tasks[0].domain_id == "ai102_d1"


# ─── LearningPath round-trip ──────────────────────────────────────────────────

def _learning_path_from_dict(d: dict) -> LearningPath:
    d2 = dc_filter(LearningPath, d)
    d2["all_modules"] = [LearningModule(**dc_filter(LearningModule, m)) for m in d.get("all_modules", [])]
    cp = d.get("curated_paths", {})
    d2["curated_paths"] = {
        k: [LearningModule(**dc_filter(LearningModule, m)) for m in v]
        for k, v in cp.items()
    }
    return LearningPath(**d2)


class TestLearningPathFromDict:
    def _base(self):
        return {
            "student_name": "Alice",
            "exam_target":  "AI-102",
            "curated_paths": {"ai102_d1": [{"title": "Mod1", "url": "https://x", "domain_id": "ai102_d1"}]},
            "all_modules":  [{"title": "Mod1", "url": "https://x", "domain_id": "ai102_d1"}],
            "total_hours_est": 5.0,
            "skipped_domains": [],
            "summary": "A summary",
        }

    def test_clean_round_trip(self):
        lp = _learning_path_from_dict(self._base())
        assert lp.student_name == "Alice"
        assert len(lp.all_modules) == 1

    def test_extra_top_key_dropped(self):
        d = {**self._base(), "GHOST_FIELD": 99}
        lp = _learning_path_from_dict(d)   # must not raise
        assert lp.student_name == "Alice"

    def test_extra_module_key_dropped(self):
        b = self._base()
        b["all_modules"][0]["deprecated_field"] = "gone"
        lp = _learning_path_from_dict(b)   # must not raise
        assert lp.all_modules[0].title == "Mod1"


# ─── Assessment / AssessmentResult round-trips ───────────────────────────────

def _assessment_from_dict(d: dict) -> Assessment:
    d2 = dc_filter(Assessment, d)
    d2["questions"] = [QuizQuestion(**dc_filter(QuizQuestion, q)) for q in d.get("questions", [])]
    return Assessment(**d2)


def _assessment_result_from_dict(d: dict) -> AssessmentResult:
    d2 = dc_filter(AssessmentResult, d)
    d2["feedback"] = [QuestionFeedback(**dc_filter(QuestionFeedback, f)) for f in d.get("feedback", [])]
    return AssessmentResult(**d2)


class TestAssessmentFromDict:
    def test_extra_top_key_dropped(self):
        d = {
            "student_name": "Alice", "exam_target": "AI-102",
            "questions": [],
            "total_marks": 10, "pass_mark_pct": 60.0,
            "FUTURE_FIELD": "x",
        }
        asmt = _assessment_from_dict(d)
        assert asmt.student_name == "Alice"

    def test_extra_question_key_dropped(self):
        q = {
            "id": "q1", "domain_id": "d1", "domain_name": "D1",
            "question": "Q?", "options": ["A", "B", "C", "D"],
            "correct_index": 0, "explanation": "Because A",
            "GHOST_KEY": "oops",
        }
        d = {"student_name": "Alice", "exam_target": "AI-102", "questions": [q],
             "total_marks": 1, "pass_mark_pct": 60.0}
        asmt = _assessment_from_dict(d)
        assert asmt.questions[0].id == "q1"


class TestAssessmentResultFromDict:
    def test_extra_top_key_dropped(self):
        d = {
            "student_name": "Alice", "exam_target": "AI-102",
            "score_pct": 75.0, "passed": True,
            "correct_count": 3, "total_count": 4,
            "domain_scores": {}, "feedback": [],
            "DEPRECATED_FIELD": "old",
        }
        result = _assessment_result_from_dict(d)
        assert result.score_pct == 75.0

    def test_extra_feedback_key_dropped(self):
        f = {
            "question_id": "q1", "correct": True,
            "learner_index": 0, "correct_index": 0,
            "explanation": "Right!", "NEW_FIELD": "x",
        }
        d = {
            "student_name": "Alice", "exam_target": "AI-102",
            "score_pct": 75.0, "passed": True,
            "correct_count": 1, "total_count": 1,
            "domain_scores": {}, "feedback": [f],
        }
        result = _assessment_result_from_dict(d)
        assert result.feedback[0].question_id == "q1"
