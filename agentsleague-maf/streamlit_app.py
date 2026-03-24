"""CertPrep MAF – Streamlit entry point.

Run with:
    streamlit run streamlit_app.py
"""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

load_dotenv(Path(__file__).parent / ".env", override=False)

# Add source packages to path (done by maf.__init__ but imported explicitly here)
import sys
_src = Path(__file__).parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

# Configure OTEL once at startup (no-op if packages missing)
from maf.otel import configure_otel_providers
configure_otel_providers(
    enable_console_exporter=os.environ.get("OTEL_CONSOLE", "false").lower() == "true"
)


# ---------------------------------------------------------------------------
# Streamlit page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="CertPrep AI Assistant (MAF)",
    page_icon="🎓",
    layout="centered",
)


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------

def _init_session() -> None:
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "workflow" not in st.session_state:
        st.session_state.workflow = None
    if "shell" not in st.session_state:
        st.session_state.shell = None


def _get_shell():
    """Lazily initialise the HandoffBuilder shell (cached in session state)."""
    if st.session_state.shell is None:
from maf.workflow.handoff_shell import build_handoff_shell
            from maf.workflow.certprep_workflow import CertPrepWorkflow

        with st.spinner("Initialising agents…"):
            workflow = CertPrepWorkflow()
            st.session_state.workflow = workflow
            st.session_state.shell = build_handoff_shell(workflow=workflow)
    return st.session_state.shell


def _run_async(coro):
    """Run an async coroutine from a synchronous Streamlit context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("closed")
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

def main() -> None:
    _init_session()

    st.title("🎓 CertPrep AI Assistant")
    st.caption("Powered by Microsoft Agent Framework · Azure AI Foundry · MS Learn MCP")

    # Sidebar – session info & reset
    with st.sidebar:
        st.header("Session")
        st.text(f"ID: {st.session_state.session_id[:8]}…")

        if st.button("🔄 New Session"):
            for key in ("session_id", "messages", "workflow", "shell"):
                st.session_state.pop(key, None)
            st.rerun()

        st.markdown("---")
        st.header("About")
        st.markdown(
            """
**Agents**
- OrchestratorAgent (triage)
- ProfilerAgent
- StudyPlanAgent
- PathCuratorAgent (MS Learn MCP)
- ProgressAgent (HITL Gate 1)
- AssessmentAgent (HITL Gate 2)
- CertRecommendationAgent

**Framework**: Microsoft Agent Framework  
**Checkpoint**: FileCheckpointStorage  
**Tracing**: Azure Application Insights
"""
        )

    # Chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Welcome message (once)
    if not st.session_state.messages:
        welcome = (
            "👋 Welcome to CertPrep AI!\n\n"
            "I can help you prepare for Microsoft certifications like **AI-102**, **DP-100**, "
            "**AZ-900**, and more.\n\n"
            "Tell me which exam you're targeting to get started!"
        )
        with st.chat_message("assistant"):
            st.markdown(welcome)
        st.session_state.messages.append({"role": "assistant", "content": welcome})

    # Chat input
    if user_input := st.chat_input("Type your message…"):
        # Show user message
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Get agent response
        shell = _get_shell()
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                try:
                    response = _run_async(
                        shell.process_message(
                            session_id=st.session_state.session_id,
                            message=user_input,
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    response = f"⚠️ An error occurred: {exc}"

            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()
