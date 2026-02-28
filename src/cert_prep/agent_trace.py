"""
agent_trace.py — Lightweight audit log for agent pipeline runs
==============================================================
Every agent step in the pipeline emits an AgentStep record.  The
orchestrator (streamlit_app.py) collects all steps into a RunTrace
and stores it in st.session_state["run_trace"].  The Admin Dashboard
(pages/1_Admin_Dashboard.py) reads RunTrace objects from SQLite to
render per-student pipeline timing and decision timelines.

Data model
----------
  AgentStep      One agent's contribution: timing, status, decisions, warnings.
  RunTrace       Full trace for a single pipeline run; ordered list of AgentSteps.

Key fields
----------
  AgentStep.status          "success" | "repaired" | "skipped"
  AgentStep.duration_ms     Wall-clock milliseconds for that agent
  AgentStep.decisions       Human-readable list of choices the agent made
  AgentStep.warnings        Any non-fatal issues detected by the agent
  AgentStep.detail          Arbitrary extra dict for agent-specific metadata
  RunTrace.mode             "mock" | "azure_openai" | "foundry"
  RunTrace.total_ms         End-to-end pipeline wall time

Consumers
---------
  streamlit_app.py             builds AgentStep per agent; assembles RunTrace
  pages/1_Admin_Dashboard.py   renders RunTrace as a timeline + latency chart
  database.py                  serialises/deserialises RunTrace as JSON blob

Note: _ms() and make_step() are private helpers used only by streamlit_app.py
to construct demo/mock step latencies with realistic random jitter.
"""

from __future__ import annotations

import time
import random
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentStep:
    """One agent's contribution inside a pipeline run."""
    agent_id:     str
    agent_name:   str
    icon:         str
    start_ms:     float            # wall-clock ms (relative to run start)
    duration_ms:  float
    status:       str               # "success" | "repaired" | "skipped"
    input_summary: str
    output_summary: str
    decisions:     list[str] = field(default_factory=list)
    warnings:      list[str] = field(default_factory=list)
    detail:        dict[str, Any] = field(default_factory=dict)


@dataclass
class RunTrace:
    """Full trace for a single profiling run."""
    run_id:       str
    student_name: str
    exam_target:  str
    timestamp:    str
    mode:         str
    total_ms:     float
    steps:        list[AgentStep] = field(default_factory=list)

    def append(self, step: AgentStep) -> None:
        self.steps.append(step)


def _ms(base: float, lo: int, hi: int) -> float:
    return base + random.randint(lo, hi)


def build_mock_trace(raw, profile) -> RunTrace:
    """
    Generate a realistic-looking agent trace for a mock profiling run.
    Timing values are randomised within plausible ranges to look authentic.
    """
    import datetime, uuid

    start = 0.0
    trace = RunTrace(
        run_id       = str(uuid.uuid4())[:8].upper(),
        student_name = raw.student_name,
        exam_target  = raw.exam_target,
        timestamp    = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        mode         = "Mock (rule-based)",
        total_ms     = 0,
    )

    # ── Step 0: Safety Guardrails ───────────────────────────────────────────
    d0 = random.randint(12, 28)
    trace.append(AgentStep(
        agent_id      = "safety",
        agent_name    = "Policy & Safety Guardrails",
        icon          = "🛡️",
        start_ms      = start,
        duration_ms   = d0,
        status        = "success",
        input_summary = f"Raw intake text from '{raw.student_name}'",
        output_summary= "No PII risks, no harmful content detected. Input cleared.",
        decisions     = ["PII scan: PASS", "Harmful content filter: PASS", "Anti-cheating check: PASS"],
        detail        = {"pii_entities_found": 0, "content_flags": 0},
    ))
    start += d0

    # ── Step 1: Learner Intake Agent ────────────────────────────────────────
    d1 = random.randint(18, 45)
    certs = ", ".join(raw.existing_certs) if raw.existing_certs else "None"
    trace.append(AgentStep(
        agent_id      = "intake",
        agent_name    = "Learner Intake & Profiling",
        icon          = "📥",
        start_ms      = start,
        duration_ms   = d1,
        status        = "success",
        input_summary = f"8-field form: name='{raw.student_name}', exam='{raw.exam_target}', "
                        f"certs=[{certs}], {raw.hours_per_week}h/wk × {raw.weeks_available}wks",
        output_summary= f"Structured RawStudentInput dataclass created. "
                        f"{len(raw.concern_topics)} concern topics captured.",
        decisions     = [
            f"Exam target validated: {raw.exam_target}",
            f"Time budget computed: {raw.hours_per_week * raw.weeks_available:.0f} h total",
            f"Concern topics parsed: {len(raw.concern_topics)}",
        ],
        detail        = {
            "fields_collected": 8,
            "concern_topics": raw.concern_topics,
            "existing_certs": raw.existing_certs,
        },
    ))
    start += d1

    # ── Step 2: Learner Profiling Agent ─────────────────────────────────────
    d2 = random.randint(180, 420)   # LLM call simulation
    skip_count = len(profile.modules_to_skip)
    risk_count = len(profile.risk_domains)
    trace.append(AgentStep(
        agent_id      = "profiling",
        agent_name    = "Learner Profiling Agent (LLM)",
        icon          = "🧠",
        start_ms      = start,
        duration_ms   = d2,
        status        = "success",
        input_summary = f"RawStudentInput → system prompt with AI-102 domain registry + personalisation rules",
        output_summary= f"LearnerProfile generated: level={profile.experience_level.value}, "
                        f"style={profile.learning_style.value}, "
                        f"{skip_count} skip candidates, {risk_count} risk domains.",
        decisions     = [
            f"Experience level inferred: {profile.experience_level.value.replace('_',' ').title()}",
            f"Learning style inferred: {profile.learning_style.value.replace('_',' ').title()}",
            f"Domains to skip: {profile.modules_to_skip or ['None']}",
            f"Risk domains flagged: {profile.risk_domains or ['None']}",
        ],
        warnings      = (["⚠ Azure OpenAI not configured – using mock profiler"] ),
        detail        = {
            "model":          "mock-rule-engine",
            "tokens_in":      random.randint(420, 680),
            "tokens_out":     random.randint(310, 480),
            "temperature":    0.2,
            "domain_profiles": {
                dp.domain_id: {
                    "level":      dp.knowledge_level.value,
                    "confidence": dp.confidence_score,
                    "skip":       dp.skip_recommended,
                }
                for dp in profile.domain_profiles
            },
        },
    ))
    start += d2

    # ── Step 3: Domain Confidence Scorer ────────────────────────────────────
    d3 = random.randint(8, 20)
    avg_conf = sum(dp.confidence_score for dp in profile.domain_profiles) / len(profile.domain_profiles)
    trace.append(AgentStep(
        agent_id      = "scorer",
        agent_name    = "Domain Confidence Scorer",
        icon          = "📊",
        start_ms      = start,
        duration_ms   = d3,
        status        = "success",
        input_summary = "6 domain profiles from Profiling Agent",
        output_summary= f"Average confidence: {avg_conf:.0%}. "
                        f"Domains above 50% threshold: "
                        f"{sum(1 for dp in profile.domain_profiles if dp.confidence_score >= 0.5)}/6.",
        decisions     = [
            f"{dp.domain_name}: {dp.confidence_score:.0%} → "
            f"{'PASS' if dp.confidence_score >= 0.50 else 'RISK'}"
            for dp in profile.domain_profiles
        ],
        detail        = {"threshold": 0.50, "avg_confidence": round(avg_conf, 3)},
    ))
    start += d3

    # ── Step 4: Readiness Gate ───────────────────────────────────────────────
    d4 = random.randint(5, 14)
    ready_domains = sum(1 for dp in profile.domain_profiles if dp.confidence_score >= 0.70)
    is_ready = ready_domains == len(profile.domain_profiles) and avg_conf >= 0.75
    gate_status = "Passed – route to study plan" if is_ready else "Failed – route to learning path with remediation flags"
    trace.append(AgentStep(
        agent_id      = "gate",
        agent_name    = "Readiness Gate",
        icon          = "🚦",
        start_ms      = start,
        duration_ms   = d4,
        status        = "success",
        input_summary = f"Confidence scores + risk domains from Scorer",
        output_summary= f"Gate decision: {gate_status}",
        decisions     = [
            f"Overall avg confidence: {avg_conf:.0%} (threshold 75%)",
            f"Domains above 70%: {ready_domains}/{len(profile.domain_profiles)}",
            f"Decision: {'✓ PROCEED' if is_ready else '⚠ PROCEED WITH REMEDIATION FLAGS'}",
        ],
        detail        = {
            "gate_passed":     is_ready,
            "risk_domain_ids": profile.risk_domains,
            "skip_domain_ids": profile.domains_to_skip(),
        },
    ))
    start += d4

    # ── Step 5: Analogy Mapper (only if ML background) ──────────────────────
    if profile.analogy_map:
        d5 = random.randint(10, 22)
        trace.append(AgentStep(
            agent_id      = "analogy",
            agent_name    = "Skill Analogy Mapper",
            icon          = "🔁",
            start_ms      = start,
            duration_ms   = d5,
            status        = "success",
            input_summary = "Expert-ML background detected in profile",
            output_summary= f"{len(profile.analogy_map)} analogy mappings generated "
                            "(existing skills → Azure AI equivalents).",
            decisions     = [f"{k} → {v}" for k, v in profile.analogy_map.items()],
            detail        = {"analogy_map": profile.analogy_map},
        ))
        start += d5

    # ── Step 6: Engagement Scheduler ────────────────────────────────────────
    d6 = random.randint(6, 15)
    trace.append(AgentStep(
        agent_id      = "engagement",
        agent_name    = "Engagement & Reminder Scheduler",
        icon          = "🔔",
        start_ms      = start,
        duration_ms   = d6,
        status        = "success",
        input_summary = f"Learning style: {profile.learning_style.value}, "
                        f"{profile.weeks_available} weeks, {profile.hours_per_week}h/wk",
        output_summary= "Reminder cadence configured. Engagement tone set.",
        decisions     = [
            "Monday: weekly recap email",
            "Wednesday: lab nudge notification",
            "Friday: milestone progress check",
            f"Tone: {'encouraging + deadline-aware' if profile.experience_level.value == 'beginner' else 'professional + efficiency-focused'}",
        ],
        detail        = {"cadence": "Mon/Wed/Fri", "engagement_notes": profile.engagement_notes},
    ))
    start += d6

    trace.total_ms = start
    return trace
