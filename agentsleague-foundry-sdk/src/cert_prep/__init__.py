"""
cert_prep — Microsoft Certification Prep Multi-Agent System
============================================================
Package containing all agents, data models, configuration, and
persistence utilities for the CertPrep pipeline.

Module map
----------
  models.py                    Shared dataclasses, Pydantic models, enums,
                               and the multi-exam domain registry.
  config.py                    Settings loaded from .env; three-tier detection.
  database.py                  SQLite persistence layer (single students table).
  guardrails.py                17-rule responsible AI guardrail pipeline.
  agent_trace.py               Lightweight AgentStep / RunTrace audit log.

  b0_intake_agent.py           Block 0: Intake (CLI) + Profiling (LLM / mock).
  b1_mock_profiler.py          Tier 3 rule-based profiler (no Azure needed).
  b1_1_study_plan_agent.py     Block 1.1a: Gantt study plan (Largest Remainder).
  b1_1_learning_path_curator.py Block 1.1b: MS Learn module curation.
  b1_2_progress_agent.py       Block 1.2: Readiness scorer + PDF + SMTP utils.
  b2_assessment_agent.py       Block 2: Domain-weighted quiz + scoring.
  b3_cert_recommendation_agent.py Block 3: Booking guidance + next-cert path.

Pipeline order
--------------
  GuardrailsPipeline [G-01..G-05] → B0 (LearnerProfilingAgent)
  → GuardrailsPipeline [G-06..G-08]
  ┌── B1.1a (StudyPlanAgent)         ─┐  parallel via ThreadPoolExecutor
  └── B1.1b (LearningPathCuratorAgent)─┘
  → GuardrailsPipeline [G-09..G-10]
  ** HITL Gate 1: student submits progress check-in **
  → B1.2 (ProgressAgent) → GuardrailsPipeline [G-11..G-13]
  ** HITL Gate 2: student submits 30-question quiz **
  → B2 (AssessmentAgent) → GuardrailsPipeline [G-14..G-15]
  → B3 (CertRecommendationAgent)
"""
__version__ = "0.1.0"
