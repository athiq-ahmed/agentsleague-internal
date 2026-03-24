"""PathCuratorAgent – searches Microsoft Learn via MCP and curates learning modules."""

from __future__ import annotations

import os
from pathlib import Path

from azure.ai.projects import AIProjectClient
from microsoft.agents.core import Agent
from microsoft.agents.azure import AzureAIClient, MCPStreamableHTTPTool

from maf.handoff_tools import handoff_to_orchestrator
from maf.learner_profile_provider import LearnerProfileProvider
from maf.guardrails_middleware import build_middleware


_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "path_curator.md"
_DEFAULT_MCP_URL = "https://learn.microsoft.com/api/mcp"


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


class PathCuratorAgent:
    """Builds and returns the MAF Agent that curates learning paths via MS Learn MCP."""

    def __init__(
        self,
        project_client: AIProjectClient,
        model_deployment: str,
        profile_provider: LearnerProfileProvider,
        mcp_url: str | None = None,
    ) -> None:
        self._project_client = project_client
        self._model = model_deployment
        self._profile_provider = profile_provider
        self._mcp_url = mcp_url or os.environ.get("MCP_MSLEARN_URL", _DEFAULT_MCP_URL)

    def build(self) -> Agent:
        azure_ai_client = AzureAIClient(project_client=self._project_client)
        mcp_tool = MCPStreamableHTTPTool(url=self._mcp_url)
        middleware = build_middleware()
        return Agent(
            client=azure_ai_client,
            name="PathCuratorAgent",
            model=self._model,
            instructions=_load_prompt(),
            tools=[mcp_tool, handoff_to_orchestrator],
            context_providers=[self._profile_provider],
            middleware=middleware,
        )
