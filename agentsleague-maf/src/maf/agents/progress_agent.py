"""ProgressAgent – computes ReadinessScore and manages HITL Gate 1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from azure.ai.projects import AIProjectClient
from microsoft.agents.core import Agent, tool
from microsoft.agents.azure import AzureAIClient

from maf.handoff_tools import handoff_to_orchestrator, handoff_to_assessment
from maf.learner_profile_provider import LearnerProfileProvider
from maf.guardrails_middleware import build_middleware


_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "progress.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


@tool
def compute_readiness_score(
    avg_confidence: float,
    hours_logged: float,
    budget_hours: float,
    practice_tests_passed: int = 0,
    total_practice_tests: int = 0,
) -> str:
    """Compute the ReadinessScore using the weighted formula and return JSON result."""
    hours_util = min(hours_logged / budget_hours, 1.0) if budget_hours > 0 else 0.0
    practice_ratio = (
        practice_tests_passed / total_practice_tests if total_practice_tests > 0 else 0.0
    )
    score = 0.55 * avg_confidence + 0.25 * hours_util + 0.20 * practice_ratio

    if score >= 0.75:
        status = "READY"
    elif score >= 0.45:
        status = "PROGRESSING"
    else:
        status = "NOT_READY"

    result: dict[str, Any] = {
        "readiness_score": round(score, 4),
        "readiness_status": status,
        "breakdown": {
            "confidence_contribution": round(0.55 * avg_confidence, 4),
            "hours_contribution": round(0.25 * hours_util, 4),
            "practice_contribution": round(0.20 * practice_ratio, 4),
        },
    }
    return json.dumps(result)


class ProgressAgent:
    """Builds and returns the MAF Agent for progress tracking."""

    def __init__(
        self,
        project_client: AIProjectClient,
        model_deployment: str,
        profile_provider: LearnerProfileProvider,
    ) -> None:
        self._project_client = project_client
        self._model = model_deployment
        self._profile_provider = profile_provider

    def build(self) -> Agent:
        azure_ai_client = AzureAIClient(project_client=self._project_client)
        middleware = build_middleware()
        return Agent(
            client=azure_ai_client,
            name="ProgressAgent",
            model=self._model,
            instructions=_load_prompt(),
            tools=[compute_readiness_score, handoff_to_orchestrator, handoff_to_assessment],
            context_providers=[self._profile_provider],
            middleware=middleware,
        )
