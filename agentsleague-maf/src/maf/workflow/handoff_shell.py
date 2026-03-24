"""HandoffBuilder shell – conversational outer shell for CertPrep.

The HandoffBuilder wraps the WorkflowBuilder pipeline as a target agent.
A lightweight TriageAgent handles free-text greetings and routes them
into the workflow, while the workflow handles all specialist logic.

Usage:
    runtime = build_handoff_shell(workflow)
    response = await runtime.process_message(session_id, user_message)
"""

from __future__ import annotations

import os
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from microsoft.agents.core import Agent, tool
from microsoft.agents.azure import AzureAIClient
from microsoft.agents.orchestrations import HandoffBuilder

from maf.workflow.certprep_workflow import CertPrepWorkflow


_TRIAGE_INSTRUCTIONS = """\
You are the CertPrep assistant — a friendly concierge for Microsoft certification preparation.

Your ONLY job is to:
1. Greet the learner warmly.
2. Understand what they want:
   - Starting preparation for a certification → hand off to the CertPrep workflow.
   - Asking a general question about certifications → answer briefly, then offer to start prep.
   - Anything off-topic → politely decline and redirect.
3. Hand off to the CertPrepWorkflow agent to handle all specialist tasks.

Do NOT attempt to build study plans, generate quizzes, or profile learners yourself.
Always delegate those to the workflow agent.
"""


@tool
def start_cert_prep_workflow(exam_target: str, user_message: str) -> str:
    """Signal that the learner wants to start or continue certification preparation.

    Args:
        exam_target: The exam code the learner is preparing for, e.g. 'AI-102'.
        user_message: The learner's original message.
    """
    return f"Starting CertPrep workflow for {exam_target}: {user_message}"


def build_handoff_shell(
    workflow: CertPrepWorkflow | None = None,
    project_client: AIProjectClient | None = None,
    model_deployment: str | None = None,
) -> HandoffBuilder:
    """Build and return a HandoffBuilder runtime wrapping the CertPrepWorkflow.

    Args:
        workflow: An already-built CertPrepWorkflow; creates one if None.
        project_client: Azure AI project client; reads env var if None.
        model_deployment: Model deployment name; reads env var if None.
    """
    if project_client is None:
        conn_str = os.environ["AZURE_AI_PROJECT_CONNECTION_STRING"]
        project_client = AIProjectClient.from_connection_string(
            conn_str=conn_str,
            credential=DefaultAzureCredential(),
        )

    model = model_deployment or os.environ.get("AZURE_AI_MODEL_DEPLOYMENT", "gpt-4o")
    azure_ai_client = AzureAIClient(project_client=project_client)

    # Lightweight triage/concierge agent — entry point for the user
    triage_agent = Agent(
        client=azure_ai_client,
        name="TriageAgent",
        model=model,
        instructions=_TRIAGE_INSTRUCTIONS,
        tools=[start_cert_prep_workflow],
    )

    # CertPrepWorkflow acts as the "specialist" handoff target
    if workflow is None:
        workflow = CertPrepWorkflow(
            project_client=project_client,
            model_deployment=model,
        )

    # HandoffBuilder wires the triage agent to the workflow
    shell = (
        HandoffBuilder(entry_agent=triage_agent)
        .add_agent(workflow._workflow)
        .add_handoff(
            source="triage_agent",
            target="certprep_workflow",
            trigger_tool=start_cert_prep_workflow,
        )
    )

    return shell.build()
