"""OrchestratorAgent – triage and route to the correct specialist agent."""

from __future__ import annotations

from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from microsoft.agents.core import Agent
from microsoft.agents.azure import AzureAIClient

from maf.handoff_tools import (
    handoff_to_profiler,
    handoff_to_study_plan,
    handoff_to_curator,
    handoff_to_progress,
    handoff_to_assessment,
    handoff_to_cert_rec,
)
from maf.learner_profile_provider import LearnerProfileProvider
from maf.guardrails_middleware import build_middleware


_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "orchestrator.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


class OrchestratorAgent:
    """Builds and returns the MAF Agent for orchestration / triage."""

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
        azure_ai_client = AzureAIClient(
            project_client=self._project_client,
        )
        middleware = build_middleware()
        return Agent(
            client=azure_ai_client,
            name="OrchestratorAgent",
            model=self._model,
            instructions=_load_prompt(),
            tools=[
                handoff_to_profiler,
                handoff_to_study_plan,
                handoff_to_curator,
                handoff_to_progress,
                handoff_to_assessment,
                handoff_to_cert_rec,
            ],
            context_providers=[self._profile_provider],
            middleware=middleware,
        )
