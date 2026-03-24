"""
handoff_tools.py
================
MAF @tool-decorated handoff functions shared across agents.

Each agent that can hand off declares the matching tool in its
Agent(tools=[...]) list.  The HandoffBuilder middleware intercepts
the tool call and routes the conversation to the target agent.

Pattern mirrors Banking Assistant:
  app/backend/app/agents/foundry_v2/handoff_orchestrator.py
"""

from agent_framework import tool


@tool(
    name="handoff_to_OrchestratorAgent",
    description="Return control to the orchestrator to re-evaluate pipeline stage.",
)
def handoff_to_orchestrator(context: str | None = None) -> str:
    """Hand control back to the triage/orchestrator agent."""
    return "Handoff to OrchestratorAgent"


@tool(
    name="handoff_to_LearnerProfilingAgent",
    description="Profile the learner from their background text and goals.",
)
def handoff_to_profiler(context: str | None = None) -> str:
    """Hand off to the learner profiling agent (Block 0)."""
    return "Handoff to LearnerProfilingAgent"


@tool(
    name="handoff_to_StudyPlanAgent",
    description="Generate a week-by-week Gantt study plan for the learner.",
)
def handoff_to_study_plan(context: str | None = None) -> str:
    """Hand off to the study plan agent (Block 1.1a)."""
    return "Handoff to StudyPlanAgent"


@tool(
    name="handoff_to_LearningPathCuratorAgent",
    description="Curate MS Learn modules from learn.microsoft.com for the learner's exam domains.",
)
def handoff_to_curator(context: str | None = None) -> str:
    """Hand off to the learning path curator agent (Block 1.1b)."""
    return "Handoff to LearningPathCuratorAgent"


@tool(
    name="handoff_to_ProgressAgent",
    description="Assess learner readiness from self-reported study progress and confidence ratings.",
)
def handoff_to_progress(context: str | None = None) -> str:
    """Hand off to the progress agent (Block 1.2 — HITL Gate 1)."""
    return "Handoff to ProgressAgent"


@tool(
    name="handoff_to_AssessmentAgent",
    description="Generate a domain-weighted quiz and evaluate the learner's answers.",
)
def handoff_to_assessment(context: str | None = None) -> str:
    """Hand off to the assessment agent (Block 2 — HITL Gate 2)."""
    return "Handoff to AssessmentAgent"


@tool(
    name="handoff_to_CertRecommendationAgent",
    description="Recommend next certification and produce GO / NOT YET verdict with booking checklist.",
)
def handoff_to_cert_rec(context: str | None = None) -> str:
    """Hand off to the cert recommendation agent (Block 3)."""
    return "Handoff to CertRecommendationAgent"
