# agentsleague-maf

**CertPrep AI** — Microsoft certification preparation assistant built on the **Microsoft Agent Framework (MAF)**.

This project is the MAF upgrade of [`agentsleague-foundry-sdk`](../agentsleague-foundry-sdk/README.md).
It reuses all existing models, guardrails, and business logic from that project while adding a full
agent orchestration layer with LLM-backed agents, MCP tool integration, HITL gates, and Azure telemetry.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                HandoffBuilder Shell                 │
│  TriageAgent  ──handoff──▶  CertPrepWorkflow        │
└─────────────────────────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  WorkflowBuilder    │
                    │  (max_iterations=8) │
                    └──────────┬──────────┘
                               │
           ┌───────────────────▼───────────────────┐
           │           OrchestratorAgent            │  triage / routing
           └───────────────────┬───────────────────┘
                               │
              ┌────────────────▼────────────────┐
              │          ProfilerAgent           │  elicit learner profile
              └────────────────┬────────────────┘
                               │
         ┌─────────────────────▼──────────────────────┐
         │           StudyPlanAgent                    │  Largest Remainder allocation
         │         (@tool get_exam_domains)            │
         └────────────┬───────────────────────────────┘
                      │  fan-out
         ┌────────────▼───────────────────────────────┐
         │         PathCuratorAgent                   │  MS Learn MCP search
         │      (MCPStreamableHTTPTool)               │
         └────────────┬───────────────────────────────┘
                      │
         ┌────────────▼───────────────────────────────┐
         │          ProgressAgent                     │  ReadinessScore formula
         │      (@tool compute_readiness_score)       │
         └────────────┬───────────────────────────────┘
                      │
            ┌─────────▼─────────┐
            │  ProgressGateway  │  ◀─── HITL Gate 1 (learner decision)
            └─────────┬─────────┘
                      │ A: take assessment
         ┌────────────▼───────────────────────────────┐
         │         AssessmentAgent                    │  domain-weighted quiz
         │       (@tool score_quiz_responses)         │
         └────────────┬───────────────────────────────┘
                      │
            ┌─────────▼─────────┐
            │   QuizGateway     │  ◀─── HITL Gate 2 (collect answers)
            └─────────┬─────────┘
                      │
            ┌─────────▼─────────┐
            │ ReadinessRouter   │  GO / CONDITIONAL / NOT_READY
            └─────────┬─────────┘
                      │ GO
         ┌────────────▼───────────────────────────────┐
         │      CertRecommendationAgent               │  GO/CONDITIONAL/NOT YET
         │   (@tool get_next_cert_suggestions)        │  + SYNERGY_MAP next certs
         └────────────────────────────────────────────┘
```

---

## Key Features

| Feature | Implementation |
|---|---|
| **All 6 agents LLM-backed** | Every agent = `Agent(client=AzureAIClient, model=gpt-4o)` |
| **MCP tool integration** | `MCPStreamableHTTPTool(url=MS_LEARN_URL)` in PathCuratorAgent |
| **WorkflowBuilder pipeline** | Sequential + fan-out edges, max 8 iterations |
| **HandoffBuilder shell** | TriageAgent → CertPrepWorkflow conversational handoff |
| **HITL Gate 1** | `ProgressGateway` — learner decides: quiz now or keep studying |
| **HITL Gate 2** | `QuizGateway` — collects quiz answers before scoring |
| **Checkpoint persistence** | `FileCheckpointStorage` — resumes across browser refreshes |
| **3 middleware types** | Input guardrails / MCP call limiter / Output PII check |
| **OTEL tracing** | `configure_otel_providers()` → Azure Application Insights |
| **Model reuse** | `src/maf/__init__.py` injects `agentsleague-foundry-sdk/src` into `sys.path` |

---

## Project Structure

```
agentsleague-maf/
├── .env.sample              # Environment variable template
├── requirements.txt         # Python dependencies (MAF packages pinned)
├── streamlit_app.py         # Streamlit entry point
└── src/maf/
    ├── __init__.py          # sys.path bootstrap (reuses foundry-sdk models)
    ├── otel.py              # OpenTelemetry + Azure Monitor setup
    ├── learner_profile_provider.py  # BaseContextProvider for all agents
    ├── handoff_tools.py     # 7 @tool handoff functions
    ├── guardrails_middleware.py     # 3 middleware types
    ├── prompts/             # Versioned agent system prompts (.md)
    │   ├── orchestrator.md
    │   ├── profiler.md
    │   ├── study_plan.md
    │   ├── path_curator.md
    │   ├── progress.md
    │   ├── assessment.md
    │   └── cert_recommendation.md
    ├── agents/              # MAF Agent builder classes (one per agent)
    │   ├── orchestrator_agent.py
    │   ├── profiler_agent.py
    │   ├── study_plan_agent.py
    │   ├── path_curator_agent.py
    │   ├── progress_agent.py
    │   ├── assessment_agent.py
    │   └── cert_recommendation_agent.py
    └── workflow/            # WorkflowBuilder, HandoffBuilder, Executors
        ├── executors.py         # ProgressGateway, QuizGateway, ReadinessRouter
        ├── certprep_workflow.py # WorkflowBuilder pipeline wiring
        └── handoff_shell.py     # HandoffBuilder outer conversational shell
```

---

## Prerequisites

- Python 3.11+
- An [Azure AI Foundry](https://ai.azure.com) project with a GPT-4o deployment
- (Optional) Azure Application Insights for telemetry

---

## Setup

```bash
# 1. Clone and navigate
cd agentsleague-maf

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.sample .env
# Edit .env and fill in your Azure AI project connection string and model deployment
```

### `.env` variables

| Variable | Description |
|---|---|
| `AZURE_AI_PROJECT_CONNECTION_STRING` | Foundry project connection string |
| `AZURE_AI_MODEL_DEPLOYMENT` | GPT-4o deployment name (default: `gpt-4o`) |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | App Insights (optional) |
| `MCP_MSLEARN_URL` | MS Learn MCP endpoint (default: `https://learn.microsoft.com/api/mcp`) |

---

## Running

```bash
streamlit run streamlit_app.py
```

The app will open in your browser at `http://localhost:8501`.

---

## Supported Exams

| Exam | Domains |
|---|---|
| **AI-102** | Azure AI Services, Computer Vision, NLP, Knowledge Mining, Generative AI |
| **DP-100** | Design ML, Explore Data, Feature Engineering, AutoML, Deploy & Retrain |
| **AZ-900** | Cloud Concepts, Azure Architecture, Mgmt & Governance, Pricing |

Additional exams can be added by extending `_EXAM_BLUEPRINTS` in [study_plan_agent.py](src/maf/agents/study_plan_agent.py).

---

## Relationship to agentsleague-foundry-sdk

This project **does not duplicate** any business logic. The `src/maf/__init__.py` bootstrap
adds `../agentsleague-foundry-sdk/src` to `sys.path`, so the following are imported directly:

- `cert_prep.models` — `LearnerProfile`, `StudyPlan`, `LearningPath`, etc.
- `cert_prep.guardrails` — 17-rule `GuardrailsPipeline`
- `cert_prep.config` — `AzureFoundryConfig`, `McpConfig`, `AppConfig`

The MAF layer replaces only the orchestration and I/O — all core logic stays in one place.

---

## MAF Packages Used

```
agent-framework-core==1.0.0b260212
agent-framework-azure-ai==1.0.0b260212
agent-framework-orchestrations==1.0.0b260212
agent-framework-devui==1.0.0b260212
agent-framework-chatkit==1.0.0b260212
```
