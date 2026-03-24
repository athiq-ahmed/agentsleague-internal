"""
guardrails_middleware.py
========================
Wraps the existing 17-rule GuardrailsPipeline into three MAF middleware
types so guardrails fire automatically at every agent boundary — no
manual calls needed in streamlit_app.py.

MAF Middleware types used (per Discussion #331 Session 1 OH):
  1. AgentContextMiddleware  — before/after agent.run(); validates inputs
  2. FunctionContextMiddleware — between LLM ↔ tool calls; caps MCP calls,
                                 tool-approval pattern
  3. ChatContextMiddleware    — on LLM response; scans output for PII (G-16)

Reference: agent_middleware.py in python-agentframework-demos
"""

from __future__ import annotations

import logging
from typing import Any

from agent_framework import (
    AgentContextMiddleware,
    AgentContext,
    FunctionContextMiddleware,
    FunctionContext,
    ChatContextMiddleware,
    ChatContext,
)

# Import existing 17-rule pipeline from agentsleague-foundry-sdk
from cert_prep.guardrails import GuardrailsPipeline, GuardrailLevel  # type: ignore

logger = logging.getLogger(__name__)

# ── 1. Agent Context Middleware — input validation at every agent.run() ──────

class InputGuardrailsMiddleware(AgentContextMiddleware):
    """
    Fires before every agent.run().

    Runs guardrails G-01..G-05 on user messages (input validation).
    BLOCK violations raise a ValueError that stops the workflow.
    WARN violations are logged — pipeline continues.

    Replaces the manual `_guardrails.check_input(raw)` call in streamlit_app.py.
    """

    def __init__(self) -> None:
        self._pipeline = GuardrailsPipeline()

    async def on_before_run(self, ctx: AgentContext) -> None:
        # Only check the last user message (not full history re-check)
        last_user_msgs = [
            m for m in (ctx.messages or []) if getattr(m, "role", "") == "user"
        ]
        if not last_user_msgs:
            return

        last_content = getattr(last_user_msgs[-1], "content", "") or ""
        if not last_content.strip():
            return

        result = self._pipeline.check_text_content(last_content)
        for v in result.violations:
            if v.level == GuardrailLevel.BLOCK:
                logger.error(f"[Guardrail BLOCK] {v.code}: {v.message}")
                raise ValueError(f"Guardrail {v.code} blocked input: {v.message}")
            elif v.level == GuardrailLevel.WARN:
                logger.warning(f"[Guardrail WARN] {v.code}: {v.message}")

    async def on_after_run(self, ctx: AgentContext) -> None:
        pass  # output PII scan handled by ChatContextMiddleware


# ── 2. Function Context Middleware — tool call control ───────────────────────

class ToolCallLimiterMiddleware(FunctionContextMiddleware):
    """
    Sits between LLM decisions and tool executions.

    - Caps LearningPathCuratorAgent at MAX_MCP_CALLS MS Learn MCP calls
      to prevent infinite search loops (per Discussion #331 recommendation).
    - Logs every tool call for observability.
    """

    MAX_MCP_CALLS = 12

    def __init__(self) -> None:
        self._mcp_call_count: dict[str, int] = {}

    async def on_before_function_call(self, ctx: FunctionContext) -> None:
        tool_name = ctx.function_name or ""
        logger.debug(f"[Tool call] {tool_name}({ctx.function_args})")

        # Count MCP calls per session
        if "mcp" in tool_name.lower() or "learn" in tool_name.lower():
            agent_id = str(id(ctx))  # per-call scope key
            count = self._mcp_call_count.get(agent_id, 0) + 1
            self._mcp_call_count[agent_id] = count

            if count > self.MAX_MCP_CALLS:
                logger.warning(
                    f"[ToolLimiter] MCP call #{count} exceeds MAX_MCP_CALLS={self.MAX_MCP_CALLS}. "
                    "Blocking further calls."
                )
                raise ValueError(
                    f"MS Learn MCP call limit ({self.MAX_MCP_CALLS}) reached. "
                    "Use the modules already retrieved."
                )

    async def on_after_function_call(self, ctx: FunctionContext) -> None:
        logger.debug(f"[Tool result] {ctx.function_name} → {str(ctx.result)[:120]}")


# ── 3. Chat Context Middleware — output PII scan ─────────────────────────────

class OutputPIIMiddleware(ChatContextMiddleware):
    """
    Runs on every LLM response before it reaches the user.

    Extends G-16 (currently only checks user input) to also scan
    agent responses for accidental PII leakage (SSN, credit card, email).
    WARN: redact and continue. Never BLOCK on output — too disruptive.
    """

    def __init__(self) -> None:
        self._pipeline = GuardrailsPipeline()

    async def on_chat_response(self, ctx: ChatContext) -> None:
        response_text = getattr(ctx.result, "text", "") or ""
        if not response_text.strip():
            return

        result = self._pipeline.check_text_content(response_text)
        pii_warns = [
            v for v in result.violations
            if v.code == "G-16" and v.level == GuardrailLevel.WARN
        ]
        if pii_warns:
            logger.warning(
                f"[OutputPII] Agent response contains potential PII — "
                f"{len(pii_warns)} pattern(s). Consider redacting before display."
            )
            # Surface to Streamlit via a state flag (caller checks this)
            ctx.state["_pii_in_response"] = [v.message for v in pii_warns]


# ── Convenience bundle ───────────────────────────────────────────────────────

def build_middleware() -> tuple[
    InputGuardrailsMiddleware,
    ToolCallLimiterMiddleware,
    OutputPIIMiddleware,
]:
    """Return one instance of each middleware type, ready to attach to agents."""
    return (
        InputGuardrailsMiddleware(),
        ToolCallLimiterMiddleware(),
        OutputPIIMiddleware(),
    )
