# Unit Test Scenarios — Certification Prep Multi-Agent System

> **Last updated:** 2026-02-26  
> **Test suite:** `tests/` — 14 modules, **299 tests passing**  
> **Run:** `python -m pytest tests/ -q`

When "do unit test" is requested, run the full suite against this file and add any new scenarios at the bottom.

---

## Test Modules

| Module | Tests | What it covers |
|--------|-------|----------------|
| `test_models.py` | 29 | RawStudentInput, DomainProfile, LearnerProfile, exam registry |
| `test_agents.py` | 4 | Agent pipeline smoke tests |
| `test_study_plan_agent.py` | 23 | StudyPlanAgent: allocations, Gantt, prereqs |
| `test_learning_path_curator.py` | 13 | LearningPathCuratorAgent: module curation |
| `test_progress_agent.py` | 26 | ProgressAgent: readiness formula, verdicts, multi-exam |
| `test_assessment_agent.py` | 24 | AssessmentAgent: question generation, scoring |
| `test_cert_recommendation_agent.py` | 13 | CertRecommendationAgent: GO/NO-GO logic |
| `test_guardrails.py` | 17 | 17-rule guardrail pipeline basics |
| `test_guardrails_full.py` | 69 | Full guardrail coverage: BLOCK/WARN/INFO |
| `test_pdf_generation.py` | 30 | PDF generation + weekly summary HTML validity |
| `test_pipeline_integration.py` | 14 | End-to-end multi-agent pipeline |
| `test_config.py` | 10 | Config: env vars, mock/live mode switching |
| `test_serialization_helpers.py` | 25 | Deserialization helpers: key-filter, enum coercion, round-trips |

---

## Scenarios by Difficulty

### Easy — Type & Value Checks

| # | Scenario | Location | Check |
|---|----------|----------|-------|
| E-01 | `RawStudentInput.email` defaults to `""` | `test_models.py::TestRawStudentInput` | `assert raw.email == ""` |
| E-02 | `LearnerProfile` has at least 1 domain profile | `test_models.py` | `assert len(profile.domain_profiles) > 0` |
| E-03 | `ReadinessAssessment.readiness_pct` is a float | `test_progress_agent.py` | `isinstance(ra.readiness_pct, float)` |
| E-04 | `ReadinessVerdict` is a string enum | `test_progress_agent.py` | `isinstance(ra.verdict, str)` |
| E-05 | `StudyPlan.total_weeks` is an int | `test_study_plan_agent.py` | `isinstance(plan.total_weeks, int)` |
| E-06 | Every exam domain dict has `id`, `name`, `weight` keys | `test_models.py::TestExamDomainRegistry` | key membership check |
| E-07 | `CertRecommendation.go_for_exam` is a bool | `test_cert_recommendation_agent.py` | `isinstance(rec.go_for_exam, bool)` |
| E-08 | `AssessmentResult.score_pct` is ∈ [0, 100] | `test_assessment_agent.py` | range assertion |
| E-09 | `Assessment.questions` is a list | `test_assessment_agent.py` | `isinstance(asmt.questions, list)` |
| E-10 | `_dc_filter` retains known keys | `test_serialization_helpers.py` | dict key equality check |

### Medium — Logic & Formula Checks

| # | Scenario | Location | Check |
|---|----------|----------|-------|
| M-01 | Perfect ratings → `EXAM_READY` verdict | `test_progress_agent.py` | `verdict == ReadinessVerdict.EXAM_READY` |
| M-02 | Zero inputs → `NOT_READY` verdict | `test_progress_agent.py` | `readiness_pct < 45` |
| M-03 | Domain weights per exam sum to ≈ 1.0 | `test_progress_agent.py` | `abs(sum - 1.0) < 0.05` |
| M-04 | Study plan hours ≤ 110% of budget | `test_study_plan_agent.py` | guardrail G-09 |
| M-05 | High quiz score → `go_for_exam=True` | `test_cert_recommendation_agent.py` | `rec.go_for_exam is True` |
| M-06 | Low quiz score → remediation plan present | `test_cert_recommendation_agent.py` | `rec.remediation_plan is not None` |
| M-07 | Harmful keyword in input blocked (G-16) | `test_guardrails_full.py` | `result.action == GuardrailAction.BLOCK` |
| M-08 | Untrusted URL blocked (G-17) | `test_guardrails_full.py` | BLOCK action |
| M-09 | `ProgressSnapshot` round-trip from dict | `test_serialization_helpers.py` | clean construction |
| M-10 | `StudyPlan` round-trip from dict | `test_serialization_helpers.py` | clean construction |
| M-11 | All 5 exam families run without error | `test_progress_agent.py` | parametrized: AI-102/DP-100/AZ-204/AZ-305/AI-900 |
| M-12 | PDF bytes returned for valid profile | `test_pdf_generation.py` | `isinstance(pdf, bytes) and len(pdf) > 0` |
| M-13 | Weekly summary is a full HTML document (not a fragment) | `test_pdf_generation.py` | `summary.startswith('<!doctype html')` |
| M-14 | Weekly summary contains `<body>` tag | `test_pdf_generation.py` | tag presence check |
| M-15 | Readiness percentage appears in the email body | `test_pdf_generation.py` | `f"{pct:.0f}%" in summary` |
| M-16 | Nudge divs have `border-left:` CSS for severity bars | `test_pdf_generation.py` | `"border-left:" in summary` |

### Hard — Integration & Boundary Checks

| # | Scenario | Location | Check |
|---|----------|----------|-------|
| H-01 | Full pipeline: intake → profile → plan → path | `test_pipeline_integration.py` | all agent outputs non-None |
| H-02 | Concurrent `StudyPlanAgent ∥ LearningPathCuratorAgent` | `test_pipeline_integration.py` | both return correct types |
| H-03 | Guardrail BLOCK halts pipeline (no plan generated) | `test_guardrails_full.py` | downstream step not reached |
| H-04 | `ProgressAgent` with all-5 ratings for non-AI-102 exam gives ≥ 50% | `test_progress_agent.py` | parametrized 3 exams |
| H-05 | `AssessmentResult` with all-correct answers → `passed=True` | `test_assessment_agent.py` | `result.passed is True` |
| H-06 | `AssessmentResult` with all-wrong answers → `passed=False` | `test_assessment_agent.py` | `result.passed is False` |
| H-07 | PDF renders with `plan=None` (no crash) | `test_pdf_generation.py` | no exception raised |
| H-08 | Config falls back to mock when no Azure env vars | `test_config.py` | `config.mode == "mock"` |
| H-09 | Prereq gap detected for exam with hard prereqs | `test_study_plan_agent.py` | `plan.prereq_gap is True` |
| H-10 | Weekly summary HTML structure consistent across AI-102/DP-100/AZ-204 | `test_pdf_generation.py` | parametrized doctype + body check |

### Edge Cases — Boundary & Schema Safety

| # | Scenario | Location | Check |
|---|----------|----------|-------|
| X-01 | Unknown dict key dropped silently (`_dc_filter`) | `test_serialization_helpers.py::TestDcFilter` | no `TypeError` |
| X-02 | Extra `FUTURE_FIELD` in stored `StudyPlan` JSON → no crash | `test_serialization_helpers.py` | construction succeeds |
| X-03 | Stale `ReadinessVerdict` value falls back to `NEEDS_WORK` | `test_serialization_helpers.py` | `verdict == NEEDS_WORK` |
| X-04 | Missing `verdict` key falls back to `NEEDS_WORK` | `test_serialization_helpers.py` | no `KeyError` |
| X-05 | Invalid `NudgeLevel` value falls back to `INFO` | `test_serialization_helpers.py` | `level == INFO` |
| X-06 | Unrecognised `domain_id` in `ProgressSnapshot` uses fallback weight | `test_progress_agent.py` | readiness ∈ [0, 100] |
| X-07 | Empty `domain_progress` list → no crash | `test_serialization_helpers.py` | `snap.domain_progress == []` |
| X-08 | `hours_per_week=0` does not divide by zero | `test_models.py` | no `ZeroDivisionError` |
| X-09 | `existing_certs=[]` is accepted | `test_models.py` | `raw.existing_certs == []` |
| X-10 | `LearningPath` with extra module key → no crash | `test_serialization_helpers.py` | construction succeeds |
| X-11 | `AssessmentResult` with extra feedback key → no crash | `test_serialization_helpers.py` | construction succeeds |
| X-12 | Unknown exam code falls back to AI-102 registry | `test_models.py` | `domains == EXAM_DOMAINS` |
| X-13 | Nudge messages raw `**` count stays ≤ 8 in rendered HTML | `test_pdf_generation.py` | `summary.count('**') <= 8` |
| X-14 | Weekly summary contains nudges section heading | `test_pdf_generation.py` | `'nudge'` or `'this week'` in summary |

---

## How to Add New Scenarios

1. Write the test in the appropriate `tests/test_*.py` module.
2. Add a row here under the right difficulty heading.
3. Run `python -m pytest tests/ -q` and confirm the total count increases.
4. Update the **Tests** count in the table at the top of this file.
