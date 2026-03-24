# Unit Test Scenarios — CertPrep MAF

> **Last updated:** 2026-03-24  
> **Test suite:** `tests/` (to be created)  
> **Run:** `python -m pytest tests/ -q`

This file is the **authoritative test scenario catalogue**. When "do unit test" is requested, run the full suite against this file and add new scenarios at the bottom.

---

## Test Modules (Planned)

| Module | Tests (target) | What it covers |
|--------|---------------|----------------|
| `test_maf_agents.py` | ~20 | Agent builder smoke tests (each `.build()` returns `Agent`) |
| `test_study_plan_agent.py` | ~20 | `get_exam_domains`, LR allocation, domain weighting |
| `test_progress_agent.py` | ~20 | `compute_readiness_score`, thresholds, formula accuracy |
| `test_assessment_agent.py` | ~15 | `score_quiz_responses`, verdict thresholds, domain scoring |
| `test_cert_rec_agent.py` | ~10 | `get_next_cert_suggestions`, SYNERGY_MAP lookup |
| `test_guardrails_middleware.py` | ~20 | All 3 middleware types: block/warn/pass scenarios |
| `test_workflow_executors.py` | ~15 | ProgressGateway, QuizGateway, ReadinessRouter routing |
| `test_learner_profile_provider.py` | ~10 | Context injection, before_run() field population |
| `test_otel.py` | ~5 | `configure_otel_providers` smoke test (no-op without SDK) |
| `test_pipeline_integration.py` | ~10 | End-to-end: profile → plan → progress → assessment → rec |

---

## Scenarios by Difficulty

### Easy — Type & Value Checks

| # | Scenario | Location | Check |
|---|----------|----------|-------|
| E-01 | `OrchestratorAgent.build()` returns an `Agent` instance | `test_maf_agents.py` | `isinstance(agent, Agent)` |
| E-02 | All 7 agent builders instantiate without error | `test_maf_agents.py` | no exception raised |
| E-03 | `get_exam_domains("AI-102")` returns 5 domains | `test_study_plan_agent.py` | `len(domains) == 5` |
| E-04 | `get_exam_domains("DP-100")` returns 5 domains | `test_study_plan_agent.py` | `len(domains) == 5` |
| E-05 | `get_exam_domains("AZ-900")` returns 4 domains | `test_study_plan_agent.py` | `len(domains) == 4` |
| E-06 | `get_exam_domains("UNKNOWN")` returns error JSON | `test_study_plan_agent.py` | `"error"` in result |
| E-07 | `compute_readiness_score(1.0, 20, 20)` returns score ~0.75 | `test_progress_agent.py` | `abs(score - 0.75) < 0.05` |
| E-08 | `compute_readiness_score(0.0, 0, 20)` returns score 0.0 | `test_progress_agent.py` | `score == 0.0` |
| E-09 | `score_quiz_responses` returns `overall_pct` float | `test_assessment_agent.py` | `isinstance(pct, float)` |
| E-10 | `get_next_cert_suggestions("AI-102")` returns 2 suggestions | `test_cert_rec_agent.py` | `len(suggestions) == 2` |

### Medium — Logic & Formula Checks

| # | Scenario | Location | Check |
|---|----------|----------|-------|
| M-01 | Perfect confidence + full hours → READY status | `test_progress_agent.py` | `status == "READY"` |
| M-02 | Zero confidence → NOT_READY status | `test_progress_agent.py` | `status == "NOT_READY"` |
| M-03 | Score 0.52 → PROGRESSING status | `test_progress_agent.py` | `status == "PROGRESSING"` |
| M-04 | AI-102 domain weights sum to 1.0 | `test_study_plan_agent.py` | `abs(sum(weights) - 1.0) < 0.01` |
| M-05 | DP-100 domain weights sum to 1.0 | `test_study_plan_agent.py` | same |
| M-06 | AZ-900 domain weights sum to 1.0 | `test_study_plan_agent.py` | same |
| M-07 | 10/10 correct answers → GO verdict | `test_assessment_agent.py` | `verdict == "GO"` |
| M-08 | 5/10 correct answers → NOT_READY verdict | `test_assessment_agent.py` | `verdict == "NOT_READY"` |
| M-09 | 7/10 correct answers → CONDITIONAL verdict | `test_assessment_agent.py` | `verdict == "CONDITIONAL"` |
| M-10 | `hours_logged > budget_hours` caps utilisation at 1.0 | `test_progress_agent.py` | `hours_util <= 1.0` |
| M-11 | `build_middleware()` returns list of 3 middleware objects | `test_guardrails_middleware.py` | `len(middleware) == 3` |
| M-12 | `InputGuardrailsMiddleware` BLOCK on PII input | `test_guardrails_middleware.py` | `ValueError` raised |
| M-13 | `ToolCallLimiterMiddleware` counter starts at 0 | `test_guardrails_middleware.py` | counter assertion |
| M-14 | SYNERGY_MAP: AI-102 first suggestion is DP-100 | `test_cert_rec_agent.py` | `suggestions[0]["cert"] == "DP-100"` |
| M-15 | `LearnerProfileProvider.before_run()` injects `exam_target` | `test_learner_profile_provider.py` | key present in context |

### Hard — Integration & Boundary Checks

| # | Scenario | Location | Check |
|---|----------|----------|-------|
| H-01 | Full pipeline: profile provider → study plan → progress → assessment | `test_pipeline_integration.py` | all outputs non-None |
| H-02 | `ProgressGateway` routes score ≥ 0.45 to HITL | `test_workflow_executors.py` | `WorkflowResult.request_human_input` returned |
| H-03 | `ProgressGateway` routes score < 0.45 to study_plan_agent | `test_workflow_executors.py` | `WorkflowResult.continue_to("study_plan_agent")` |
| H-04 | `ReadinessRouter` GO → cert_recommendation_agent | `test_workflow_executors.py` | target == cert_recommendation_agent |
| H-05 | `ReadinessRouter` CONDITIONAL → path_curator_agent | `test_workflow_executors.py` | target == path_curator_agent |
| H-06 | `ReadinessRouter` NOT_READY → study_plan_agent | `test_workflow_executors.py` | target == study_plan_agent |
| H-07 | `QuizGateway` with empty questions skips gate | `test_workflow_executors.py` | routes back to assessment_agent |
| H-08 | `QuizGateway` checkpoint save/restore round-trip | `test_workflow_executors.py` | `pending_quiz` survives save/restore |
| H-09 | `configure_otel_providers()` is a no-op without SDK | `test_otel.py` | no exception raised |
| H-10 | `PathCuratorAgent.build()` includes MCPStreamableHTTPTool | `test_maf_agents.py` | tool type in agent.tools |

### Edge Cases — Boundary & Schema Safety

| # | Scenario | Location | Check |
|---|----------|----------|-------|
| X-01 | `get_exam_domains` with lowercase exam → still works | `test_study_plan_agent.py` | `.upper()` normalisation |
| X-02 | `compute_readiness_score` with `budget_hours=0` → no division by zero | `test_progress_agent.py` | no `ZeroDivisionError` |
| X-03 | `compute_readiness_score` with `total_practice_tests=0` → `practice_ratio=0.0` | `test_progress_agent.py` | safe default |
| X-04 | `score_quiz_responses` with 0 questions → no division by zero | `test_assessment_agent.py` | no `ZeroDivisionError` |
| X-05 | `score_quiz_responses` with mismatched answer count → no crash | `test_assessment_agent.py` | `zip` truncates safely |
| X-06 | `InputGuardrailsMiddleware` WARN (not BLOCK) on mild keyword | `test_guardrails_middleware.py` | no exception, warning logged |
| X-07 | `ToolCallLimiterMiddleware` raises on 13th call | `test_guardrails_middleware.py` | exception on `_call_count > 12` |
| X-08 | `get_next_cert_suggestions` for unknown exam returns empty | `test_cert_rec_agent.py` | `suggestions == []` |
| X-09 | `LearnerProfileProvider` with no profile set → graceful before_run | `test_learner_profile_provider.py` | no `AttributeError` |
| X-10 | `CertPrepWorkflow` init with missing env var → descriptive `KeyError` | `test_pipeline_integration.py` | `KeyError("AZURE_AI_PROJECT_CONNECTION_STRING")` |

---

## How to Add New Scenarios

1. Write the test in the appropriate `tests/test_*.py` module.
2. Add a row in the correct difficulty section above.
3. Run `python -m pytest tests/ -q` and confirm the count increases.
4. Update the **Tests (target)** count in the module table.
