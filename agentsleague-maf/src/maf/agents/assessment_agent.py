"""AssessmentAgent – generates domain-weighted quiz and manages HITL Gate 2."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from azure.ai.projects import AIProjectClient
from microsoft.agents.core import Agent, tool
from microsoft.agents.azure import AzureAIClient

from maf.handoff_tools import handoff_to_orchestrator, handoff_to_cert_rec
from maf.learner_profile_provider import LearnerProfileProvider
from maf.guardrails_middleware import build_middleware


_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "assessment.md"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


@tool
def score_quiz_responses(
    questions_json: str,
    answers_json: str,
) -> str:
    """Score the learner's answers against the correct answers and return domain scores.

    Args:
        questions_json: JSON array of questions, each with 'domain_id', 'correct_answer'.
        answers_json: JSON array of learner answers in same order as questions.
    """
    questions: list[dict[str, Any]] = json.loads(questions_json)
    answers: list[str] = json.loads(answers_json)

    domain_correct: dict[str, int] = {}
    domain_total: dict[str, int] = {}

    for i, (q, a) in enumerate(zip(questions, answers)):
        did = q.get("domain_id", "unknown")
        domain_total[did] = domain_total.get(did, 0) + 1
        if str(a).strip().upper() == str(q.get("correct_answer", "")).strip().upper():
            domain_correct[did] = domain_correct.get(did, 0) + 1

    total_q = len(questions)
    total_correct = sum(domain_correct.values())
    overall_pct = round(total_correct / total_q * 100, 1) if total_q else 0.0

    if overall_pct >= 80:
        verdict = "GO"
    elif overall_pct >= 60:
        verdict = "CONDITIONAL"
    else:
        verdict = "NOT_READY"

    domain_scores = [
        {
            "domain_id": did,
            "questions": domain_total[did],
            "correct": domain_correct.get(did, 0),
            "score_pct": round(domain_correct.get(did, 0) / domain_total[did] * 100, 1),
        }
        for did in domain_total
    ]
    weak_domains = [d["domain_id"] for d in domain_scores if d["score_pct"] < 65]

    result = {
        "overall_pct": overall_pct,
        "total_questions": total_q,
        "total_correct": total_correct,
        "readiness_verdict": verdict,
        "domain_scores": domain_scores,
        "weak_domains": weak_domains,
    }
    return json.dumps(result)


class AssessmentAgent:
    """Builds and returns the MAF Agent for practice assessment."""

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
            name="AssessmentAgent",
            model=self._model,
            instructions=_load_prompt(),
            tools=[score_quiz_responses, handoff_to_orchestrator, handoff_to_cert_rec],
            context_providers=[self._profile_provider],
            middleware=middleware,
        )
