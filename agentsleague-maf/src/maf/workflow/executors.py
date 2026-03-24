"""Workflow Executors for CertPrep – HITL gates and routing logic.

Three Executor subclasses:
  - ProgressGateway   : HITL Gate 1 – pauses after progress check for learner decision
  - ReadinessRouter   : Deterministic edge — routes NOT_READY back to study plan
  - QuizGateway       : HITL Gate 2 – collects quiz answers before scoring
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from microsoft.agents.orchestrations import (
    Executor,
    WorkflowContext,
    WorkflowResult,
    HumanInput,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared dataclasses (serialised into checkpoint state)
# ---------------------------------------------------------------------------

@dataclass
class ProgressCheckRequest:
    """Captures the progress snapshot that triggered Gate 1."""
    readiness_score: float
    readiness_status: str
    hours_logged: float
    budget_hours: float
    domain_progress: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class QuizRequest:
    """Captures the generated quiz awaiting learner answers (Gate 2)."""
    questions: list[dict[str, Any]] = field(default_factory=list)
    exam_target: str = ""


# ---------------------------------------------------------------------------
# ProgressGateway – HITL Gate 1
# ---------------------------------------------------------------------------

class ProgressGateway(Executor):
    """Pause after the ProgressAgent runs and ask if the learner wants a quiz."""

    NAME = "progress_gateway"

    @Executor.handler("progress_agent_output")
    async def on_progress_output(
        self, ctx: WorkflowContext, data: dict[str, Any]
    ) -> WorkflowResult:
        """Called when ProgressAgent emits its output JSON."""
        try:
            payload = json.loads(data.get("content", "{}"))
        except json.JSONDecodeError:
            payload = {}

        status = payload.get("readiness_status", "")
        score = payload.get("readiness_score", 0.0)

        # Store progress snapshot in workflow state
        ctx.state["progress_snapshot"] = payload

        if status in ("READY", "PROGRESSING") and score >= 0.45:
            # Raise HITL gate — ask learner what to do next
            return WorkflowResult.request_human_input(
                HumanInput(
                    prompt=(
                        f"You've reached a readiness score of **{score:.0%}** ({status}).\n\n"
                        "Would you like to:\n"
                        "- **A** – Take a practice assessment now\n"
                        "- **B** – Continue studying\n\n"
                        "Enter A or B:"
                    ),
                    context={"gate": "progress_gate_1", "score": score},
                )
            )
        # NOT_READY – continue to study plan without gating
        return WorkflowResult.continue_to("study_plan_agent")

    @Executor.response_handler("progress_gate_1")
    async def on_learner_decision(
        self, ctx: WorkflowContext, human_response: HumanInput
    ) -> WorkflowResult:
        """Route based on learner's Gate 1 answer."""
        answer = (human_response.response or "").strip().upper()
        if answer == "A":
            logger.info("Learner chose assessment; routing to AssessmentAgent.")
            return WorkflowResult.continue_to("assessment_agent")
        # Default: continue studying
        logger.info("Learner chose to continue studying; routing to PathCuratorAgent.")
        return WorkflowResult.continue_to("path_curator_agent")

    async def on_checkpoint_save(self, ctx: WorkflowContext) -> dict[str, Any]:
        return {"progress_snapshot": ctx.state.get("progress_snapshot")}

    async def on_checkpoint_restore(
        self, ctx: WorkflowContext, state: dict[str, Any]
    ) -> None:
        if state.get("progress_snapshot"):
            ctx.state["progress_snapshot"] = state["progress_snapshot"]


# ---------------------------------------------------------------------------
# ReadinessRouter – deterministic routing after Assessment
# ---------------------------------------------------------------------------

class ReadinessRouter(Executor):
    """Route AssessmentAgent output to CertRec or back to study plan."""

    NAME = "readiness_router"

    @Executor.handler("assessment_agent_output")
    async def on_assessment_output(
        self, ctx: WorkflowContext, data: dict[str, Any]
    ) -> WorkflowResult:
        """Route based on readiness_verdict from AssessmentAgent."""
        try:
            payload = json.loads(data.get("content", "{}"))
        except json.JSONDecodeError:
            payload = {}

        verdict = payload.get("readiness_verdict", "NOT_READY")
        ctx.state["assessment_result"] = payload

        if verdict == "GO":
            return WorkflowResult.continue_to("cert_recommendation_agent")
        if verdict == "CONDITIONAL":
            # Put weak domains into state so study plan can focus on them
            ctx.state["weak_domains"] = payload.get("weak_domains", [])
            return WorkflowResult.continue_to("path_curator_agent")
        # NOT_READY — rebuild study plan
        ctx.state["weak_domains"] = payload.get("weak_domains", [])
        return WorkflowResult.continue_to("study_plan_agent")

    async def on_checkpoint_save(self, ctx: WorkflowContext) -> dict[str, Any]:
        return {"assessment_result": ctx.state.get("assessment_result")}

    async def on_checkpoint_restore(
        self, ctx: WorkflowContext, state: dict[str, Any]
    ) -> None:
        if state.get("assessment_result"):
            ctx.state["assessment_result"] = state["assessment_result"]


# ---------------------------------------------------------------------------
# QuizGateway – HITL Gate 2
# ---------------------------------------------------------------------------

class QuizGateway(Executor):
    """Present the quiz to the learner and wait for answers before scoring."""

    NAME = "quiz_gateway"

    @Executor.handler("assessment_quiz_generated")
    async def on_quiz_ready(
        self, ctx: WorkflowContext, data: dict[str, Any]
    ) -> WorkflowResult:
        """Called when AssessmentAgent has generated quiz questions."""
        try:
            payload = json.loads(data.get("content", "{}"))
        except json.JSONDecodeError:
            payload = {}

        questions = payload.get("questions", [])
        ctx.state["pending_quiz"] = payload

        if not questions:
            logger.warning("QuizGateway received empty questions list; skipping gate.")
            return WorkflowResult.continue_to("assessment_agent")

        # Build prompt text
        quiz_text = self._format_quiz(questions)

        return WorkflowResult.request_human_input(
            HumanInput(
                prompt=(
                    f"Here is your **{len(questions)}-question practice quiz** "
                    f"for {payload.get('exam_target', 'the exam')}.\n\n"
                    f"{quiz_text}\n\n"
                    "Please answer each question (e.g., A, B, C, D or A,C for multi-select), "
                    "one per line:"
                ),
                context={"gate": "quiz_gate_2", "question_count": len(questions)},
            )
        )

    @Executor.response_handler("quiz_gate_2")
    async def on_answers_received(
        self, ctx: WorkflowContext, human_response: HumanInput
    ) -> WorkflowResult:
        """Parse answers and store them, then continue to scoring."""
        raw = human_response.response or ""
        answers = [line.strip() for line in raw.strip().splitlines() if line.strip()]
        ctx.state["quiz_answers"] = answers
        return WorkflowResult.continue_to("assessment_agent")

    async def on_checkpoint_save(self, ctx: WorkflowContext) -> dict[str, Any]:
        return {
            "pending_quiz": ctx.state.get("pending_quiz"),
            "quiz_answers": ctx.state.get("quiz_answers"),
        }

    async def on_checkpoint_restore(
        self, ctx: WorkflowContext, state: dict[str, Any]
    ) -> None:
        for key in ("pending_quiz", "quiz_answers"):
            if state.get(key) is not None:
                ctx.state[key] = state[key]

    @staticmethod
    def _format_quiz(questions: list[dict[str, Any]]) -> str:
        lines: list[str] = []
        for i, q in enumerate(questions, start=1):
            lines.append(f"**Q{i}.** {q.get('question', '')}")
            for opt_key in ("A", "B", "C", "D"):
                opt_text = q.get(f"option_{opt_key}")
                if opt_text:
                    lines.append(f"   {opt_key}. {opt_text}")
            lines.append("")
        return "\n".join(lines)
