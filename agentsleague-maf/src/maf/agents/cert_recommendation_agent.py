"""CertRecommendationAgent – issues GO/CONDITIONAL/NOT YET and next-cert suggestions."""

from __future__ import annotations

import json
from pathlib import Path

from azure.ai.projects import AIProjectClient
from microsoft.agents.core import Agent, tool
from microsoft.agents.azure import AzureAIClient

from maf.handoff_tools import handoff_to_orchestrator
from maf.learner_profile_provider import LearnerProfileProvider
from maf.guardrails_middleware import build_middleware


_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "cert_recommendation.md"

_SYNERGY_MAP: dict[str, list[str]] = {
    "AI-102": ["DP-100", "AZ-305", "SC-900"],
    "DP-100": ["AI-102", "DP-203", "DP-300"],
    "AZ-305": ["AZ-104", "AI-102", "DP-203"],
    "AZ-204": ["AZ-305", "AZ-400"],
    "AZ-900": ["AZ-104", "AI-900", "DP-900"],
    "AI-900": ["AI-102", "DP-100"],
    "SC-900": ["SC-300", "SC-200"],
}


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


@tool
def get_next_cert_suggestions(current_exam: str, experience_level: str = "intermediate") -> str:
    """Return the top 2 next certification suggestions based on SYNERGY_MAP.

    Args:
        current_exam: The exam just completed, e.g. 'AI-102'.
        experience_level: 'beginner', 'intermediate', or 'professional'.
    """
    suggestions = _SYNERGY_MAP.get(current_exam.upper(), [])[:2]
    result = {
        "current_exam": current_exam,
        "next_suggestions": [
            {"cert": cert, "rationale": f"Complements {current_exam} skills"}
            for cert in suggestions
        ],
    }
    return json.dumps(result)


class CertRecommendationAgent:
    """Builds and returns the MAF Agent for certification recommendations."""

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
            name="CertRecommendationAgent",
            model=self._model,
            instructions=_load_prompt(),
            tools=[get_next_cert_suggestions, handoff_to_orchestrator],
            context_providers=[self._profile_provider],
            middleware=middleware,
        )
