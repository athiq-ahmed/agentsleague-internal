"""StudyPlanAgent – generates a domain-weighted study plan using Largest Remainder."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from azure.ai.projects import AIProjectClient
from microsoft.agents.core import Agent, tool
from microsoft.agents.azure import AzureAIClient

from maf.handoff_tools import handoff_to_orchestrator, handoff_to_curator
from maf.learner_profile_provider import LearnerProfileProvider
from maf.guardrails_middleware import build_middleware

# ------------------------------------------------------------------
# Exam domain blueprints – weights must sum to 1.0
# Extend this dict as new exams are added.
# ------------------------------------------------------------------
_EXAM_BLUEPRINTS: dict[str, list[dict[str, Any]]] = {
    "AI-102": [
        {"domain_id": "azure_ai_services", "domain_name": "Plan and manage Azure AI services", "weight": 0.25},
        {"domain_id": "computer_vision", "domain_name": "Implement Computer Vision Solutions", "weight": 0.20},
        {"domain_id": "nlp", "domain_name": "Implement Natural Language Processing Solutions", "weight": 0.20},
        {"domain_id": "knowledge_mining", "domain_name": "Implement Knowledge Mining and Document Intelligence", "weight": 0.15},
        {"domain_id": "generative_ai", "domain_name": "Implement Generative AI Solutions", "weight": 0.20},
    ],
    "DP-100": [
        {"domain_id": "design_ml", "domain_name": "Design and prepare a machine learning solution", "weight": 0.20},
        {"domain_id": "explore_data", "domain_name": "Explore data and train models", "weight": 0.25},
        {"domain_id": "prepare_data", "domain_name": "Prepare and engineer features", "weight": 0.20},
        {"domain_id": "train_models", "domain_name": "Find the best model using AutoML", "weight": 0.15},
        {"domain_id": "deploy_manage", "domain_name": "Deploy and retrain a model", "weight": 0.20},
    ],
    "AZ-900": [
        {"domain_id": "cloud_concepts", "domain_name": "Describe cloud concepts", "weight": 0.25},
        {"domain_id": "azure_architecture", "domain_name": "Describe Azure architecture and services", "weight": 0.35},
        {"domain_id": "azure_mgmt", "domain_name": "Describe Azure management and governance", "weight": 0.30},
        {"domain_id": "pricing", "domain_name": "Describe cost management in Azure", "weight": 0.10},
    ],
}


@tool
def get_exam_domains(exam_target: str) -> str:
    """Return the domain blueprint for a given exam as a JSON string."""
    blueprint = _EXAM_BLUEPRINTS.get(exam_target.upper(), [])
    if not blueprint:
        return json.dumps({"error": f"No blueprint found for {exam_target}. Use AI-102, DP-100, or AZ-900."})
    return json.dumps({"exam_target": exam_target, "domains": blueprint})


_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "study_plan.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


class StudyPlanAgent:
    """Builds and returns the MAF Agent for study plan generation."""

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
            name="StudyPlanAgent",
            model=self._model,
            instructions=_load_prompt(),
            tools=[get_exam_domains, handoff_to_orchestrator, handoff_to_curator],
            context_providers=[self._profile_provider],
            middleware=middleware,
        )
