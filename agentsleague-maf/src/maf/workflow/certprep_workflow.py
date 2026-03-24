"""CertPrepWorkflow – WorkflowBuilder pipeline wiring all 6 specialist agents.

Topology (sequential with HITL gates and a conditional loop):

  [OrchestratorAgent]
       |
  [ProfilerAgent]  ──────────────────────────────────────────────┐
       |                                                          │
  [StudyPlanAgent] ─── fan-out ───> [PathCuratorAgent]           │
       |                                 |                        │
       └─────────────────────────────────┘                        │
       |                                                          │
  [ProgressAgent]  ── HITL Gate 1 (ProgressGateway) ──┐          │
       |                                               │          │
       │                                    A: [AssessmentAgent]  │
       │                                     HITL Gate 2          │
       │                                    (QuizGateway)         │
       │                                               │          │
       │         ReadinessRouter                       │          │
       │             GO ──────────────> [CertRecAgent] │          │
       │             CONDITIONAL ─────> [PathCurator]  │          │
       └─────────────NOT_READY ──────> [StudyPlan] ────┘          │
"""

from __future__ import annotations

import os
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from microsoft.agents.orchestrations import WorkflowBuilder, FileCheckpointStorage

from maf.agents import (
    OrchestratorAgent,
    ProfilerAgent,
    StudyPlanAgent,
    PathCuratorAgent,
    ProgressAgent,
    AssessmentAgent,
    CertRecommendationAgent,
)
from maf.learner_profile_provider import LearnerProfileProvider
from maf.workflow.executors import (
    ProgressGateway,
    ReadinessRouter,
    QuizGateway,
)

_DEFAULT_CHECKPOINT_DIR = Path.home() / ".certprep_maf" / "checkpoints"
_DEFAULT_MAX_ITERATIONS = 8


class CertPrepWorkflow:
    """Assembles and exposes the WorkflowBuilder pipeline."""

    def __init__(
        self,
        project_client: AIProjectClient | None = None,
        model_deployment: str | None = None,
        checkpoint_dir: Path | None = None,
        max_iterations: int = _DEFAULT_MAX_ITERATIONS,
        mcp_url: str | None = None,
    ) -> None:
        self._project_client = project_client or self._default_project_client()
        self._model = model_deployment or os.environ.get("AZURE_AI_MODEL_DEPLOYMENT", "gpt-4o")
        self._checkpoint_dir = checkpoint_dir or _DEFAULT_CHECKPOINT_DIR
        self._max_iterations = max_iterations
        self._mcp_url = mcp_url

        # Shared context provider – set a profile before starting
        self.profile_provider = LearnerProfileProvider()

        self._workflow = self._build()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def process_message(self, session_id: str, message: str) -> str:
        """Send a user message into the workflow and return the agent response."""
        return await self._workflow.process_message(
            session_id=session_id,
            message=message,
        )

    # ------------------------------------------------------------------
    # Internal wiring
    # ------------------------------------------------------------------

    def _build(self) -> WorkflowBuilder:
        pc = self._project_client
        model = self._model
        pp = self.profile_provider

        orchestrator = OrchestratorAgent(pc, model, pp).build()
        profiler = ProfilerAgent(pc, model, pp).build()
        study_plan = StudyPlanAgent(pc, model, pp).build()
        path_curator = PathCuratorAgent(pc, model, pp, mcp_url=self._mcp_url).build()
        progress = ProgressAgent(pc, model, pp).build()
        assessment = AssessmentAgent(pc, model, pp).build()
        cert_rec = CertRecommendationAgent(pc, model, pp).build()

        checkpoint_storage = FileCheckpointStorage(
            directory=str(self._checkpoint_dir)
        )

        workflow = (
            WorkflowBuilder(
                entry_agent=orchestrator,
                checkpoint_storage=checkpoint_storage,
                max_iterations=self._max_iterations,
            )
            # --- register all specialist agents ---
            .add_agent(profiler)
            .add_agent(study_plan)
            .add_agent(path_curator)
            .add_agent(progress)
            .add_agent(assessment)
            .add_agent(cert_rec)
            # --- register HITL executors and routers ---
            .add_executor(ProgressGateway())
            .add_executor(ReadinessRouter())
            .add_executor(QuizGateway())
            # --- fan-out: study plan + path curation run concurrently ---
            .add_fan_out_edge(
                source="study_plan_agent",
                targets=["path_curator_agent"],
            )
            # --- sequential edges ---
            .add_edge("orchestrator_agent", "profiler_agent")
            .add_edge("profiler_agent", "study_plan_agent")
            .add_edge("path_curator_agent", "progress_agent")
            # progress_gateway handles progress_agent → assessment_agent / path_curator_agent
            .add_edge("progress_agent", ProgressGateway.NAME)
            # readiness_router handles assessment_agent → cert_rec / path_curator / study_plan
            .add_edge("assessment_agent", ReadinessRouter.NAME)
        )

        return workflow.build()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _default_project_client() -> AIProjectClient:
        conn_str = os.environ["AZURE_AI_PROJECT_CONNECTION_STRING"]
        return AIProjectClient.from_connection_string(
            conn_str=conn_str,
            credential=DefaultAzureCredential(),
        )
