"""
learner_profile_provider.py
============================
MAF BaseContextProvider that injects the current learner's profile
into every agent run automatically, without manual passing.

Mirrors the UserProfileProvider pattern from the Banking Assistant
(app/backend/app/common/user_profile_provider.py) but carries
CertPrep-specific fields: exam target, weak domains, study budget.

Usage
-----
    provider = LearnerProfileProvider()
    provider.set_profile(learner_profile)  # call after profiling step

    agent = Agent(
        client=azure_ai_client,
        instructions=...,
        context_providers=[provider],
    )
"""

from __future__ import annotations

from typing import Any

from agent_framework import AgentSession, BaseContextProvider, SessionContext


class LearnerProfileProvider(BaseContextProvider):
    """Injects learner context into every agent before each run.

    After LearnerProfilingAgent completes, call set_profile() once.
    All downstream agents (StudyPlan, Assessment, etc.) then receive
    the learner's name, exam, experience level, weak domains, and
    study budget automatically — no manual argument passing needed.
    """

    DEFAULT_SOURCE_ID = "learner_profile_provider"

    def __init__(self, source_id: str = DEFAULT_SOURCE_ID, **kwargs: Any):
        super().__init__(source_id)
        self._profile: Any | None = None

    def set_profile(self, profile: Any) -> None:
        """Call this immediately after LearnerProfilingAgent.run() returns."""
        self._profile = profile

    def has_profile(self) -> bool:
        return self._profile is not None

    async def before_run(
        self,
        *,
        agent: Any,
        session: AgentSession | None,
        context: SessionContext,
        state: dict[str, Any],
    ) -> None:
        """Inject learner context before each agent call."""
        if self._profile is None:
            return

        p = self._profile
        weak = ", ".join(p.risk_domains) if p.risk_domains else "none"
        skip = ", ".join(p.modules_to_skip) if p.modules_to_skip else "none"
        avg_conf = (
            sum(d.confidence_score for d in p.domain_profiles) / len(p.domain_profiles)
            if p.domain_profiles else 0.0
        )

        context.add_context(
            f"=== CURRENT LEARNER CONTEXT ===\n"
            f"Name:             {p.student_name}\n"
            f"Target exam:      {p.exam_target}\n"
            f"Experience level: {p.experience_level.value}\n"
            f"Learning style:   {p.preferred_style.value}\n"
            f"Avg confidence:   {avg_conf:.0%}\n"
            f"Risk domains:     {weak}\n"
            f"Domains to skip:  {skip}\n"
            f"Budget:           {p.hours_per_week}hr/wk × {p.weeks_available} weeks\n"
            f"================================"
        )
