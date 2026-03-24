# Technical Documentation — CertPrep MAF

> **Version:** 1.0  
> **Framework:** Microsoft Agent Framework (MAF)  
> **Last updated:** 2026-03-24

---

## 1. Overview

CertPrep MAF is the Microsoft Agent Framework upgrade of the original `agentsleague-foundry-sdk` project. It replaces hand-coded Python orchestration with a full MAF `WorkflowBuilder` pipeline, adds real MCP tool use against Microsoft Learn, introduces 3 middleware types, 2 HITL checkpoint gates, and Azure Application Insights distributed tracing.

All existing business logic (data models, guardrails, exam domain blueprints) is reused via a `sys.path` injection from `agentsleague-foundry-sdk/src`. Only orchestration and I/O are new.

---

## 2. Architecture

### 2.1 Pipeline Topology

```
HandoffBuilder Shell
  └── TriageAgent (conversational entry point)
         │  handoff trigger: start_cert_prep_workflow()
         ▼
WorkflowBuilder Pipeline  (max_iterations=8 · FileCheckpointStorage)
  ├── OrchestratorAgent      ← triage & routing
  ├── ProfilerAgent          ← LearnerProfile elicitation
  ├── StudyPlanAgent         ← Largest Remainder allocation
  ├── PathCuratorAgent       ← MS Learn MCP search (fan-out target)
  ├── ProgressAgent          ← ReadinessScore formula + HITL Gate 1
  │     └── ProgressGateway  ← [HITL] learner decides: quiz now or study more
  ├── AssessmentAgent        ← domain-weighted quiz + HITL Gate 2
  │     └── QuizGateway      ← [HITL] collect quiz answers
  │     └── ReadinessRouter  ← GO / CONDITIONAL / NOT_READY routing
  └── CertRecommendationAgent ← final GO/CONDITIONAL/NOT YET + next certs
```

### 2.2 Package Structure

```
src/maf/
├── __init__.py                   sys.path bootstrap (reuses foundry-sdk models)
├── otel.py                       OpenTelemetry + Azure Monitor
├── learner_profile_provider.py   BaseContextProvider
├── handoff_tools.py              7 @tool handoff functions
├── guardrails_middleware.py      3 middleware types
├── prompts/                      Versioned agent system prompts (.md)
├── agents/                       MAF Agent builder classes
└── workflow/                     WorkflowBuilder, HandoffBuilder, Executors
```

---

## 3. Agent Specifications

### 3.1 OrchestratorAgent

| Property | Value |
|----------|-------|
| File | `src/maf/agents/orchestrator_agent.py` |
| Prompt | `src/maf/prompts/orchestrator.md` |
| Tools | 6 handoff tools (to all specialist agents) |
| Role | Triage: reads session state and routes to the correct next agent |

**Routing rules:**
1. New learner with no profile → `ProfilerAgent`
2. Profile exists, no study plan → `StudyPlanAgent` + fan-out `PathCuratorAgent`
3. Returning learner with plan → `ProgressAgent`
4. ReadinessScore ≥ 0.45 → `AssessmentAgent`
5. Score < 0.45 after assessment → rebuild via `StudyPlanAgent`
6. Quiz completed with GO verdict → `CertRecommendationAgent`

### 3.2 ProfilerAgent

| Property | Value |
|----------|-------|
| File | `src/maf/agents/profiler_agent.py` |
| Prompt | `src/maf/prompts/profiler.md` |
| Tools | `handoff_to_orchestrator` |
| Temperature | 0.2 (recommended in prompt) |
| Output | JSON matching `LearnerProfile` schema from foundry-sdk |

Elicits: exam target, experience level, role, hours/week budget, preferred learning style, existing certifications, and per-domain self-confidence ratings (0.0–1.0).

### 3.3 StudyPlanAgent

| Property | Value |
|----------|-------|
| File | `src/maf/agents/study_plan_agent.py` |
| Prompt | `src/maf/prompts/study_plan.md` |
| Tools | `get_exam_domains` (inline @tool), `handoff_to_curator` |

**Algorithm: Largest Remainder Method**

```
total_days = study_weeks × 7
quota[d]   = weight[d] × total_days
floor[d]   = max(1, int(quota[d]))        # no domain gets zero
remainder[d] = quota[d] - floor[d]
remaining  = total_days - sum(floor)
# Top-k remainders get +1 day each (k = remaining)
hours[d]   = days[d] × hours_per_day
```

Exam blueprints supported: AI-102, DP-100, AZ-900 (extend via `_EXAM_BLUEPRINTS` dict).

### 3.4 PathCuratorAgent

| Property | Value |
|----------|-------|
| File | `src/maf/agents/path_curator_agent.py` |
| Prompt | `src/maf/prompts/path_curator.md` |
| Tools | `MCPStreamableHTTPTool(url=MCP_MSLEARN_URL)`, `handoff_to_orchestrator` |
| MCP cap | Max 12 tool calls per run (enforced by `ToolCallLimiterMiddleware`) |

Searches Microsoft Learn for 2–3 modules per domain, ordered by risk priority and learning style. Only URLs from `learn.microsoft.com`, `docs.microsoft.com`, or `aka.ms` are included (guardrail G-17).

### 3.5 ProgressAgent

| Property | Value |
|----------|-------|
| File | `src/maf/agents/progress_agent.py` |
| Prompt | `src/maf/prompts/progress.md` |
| Tools | `compute_readiness_score` (inline @tool), `handoff_to_assessment` |

**ReadinessScore formula:**
```
ReadinessScore = 0.55 × avg_confidence
               + 0.25 × min(hours_logged / budget_hours, 1.0)
               + 0.20 × (practice_passed / practice_total)
```

| Score | Status |
|-------|--------|
| ≥ 0.75 | READY |
| 0.45–0.74 | PROGRESSING |
| < 0.45 | NOT_READY |

Triggers HITL Gate 1 (ProgressGateway) when score crosses 0.45.

### 3.6 AssessmentAgent

| Property | Value |
|----------|-------|
| File | `src/maf/agents/assessment_agent.py` |
| Prompt | `src/maf/prompts/assessment.md` |
| Tools | `score_quiz_responses` (inline @tool), `handoff_to_cert_rec` |
| Temperature | 0.7 (for question variety) |
| Quiz size | 10–15 questions, domain-weighted |

Question difficulty skew:
- Confident domains (≥ 0.70): 60% hard, 40% medium
- Weak domains (< 0.70): 40% hard, 40% medium, 20% easy

Triggers HITL Gate 2 (QuizGateway) to collect answers before scoring.

**Readiness verdicts:**

| overall_pct | Verdict |
|-------------|---------|
| ≥ 80% | GO |
| 60–79% | CONDITIONAL |
| < 60% | NOT_READY |

### 3.7 CertRecommendationAgent

| Property | Value |
|----------|-------|
| File | `src/maf/agents/cert_recommendation_agent.py` |
| Prompt | `src/maf/prompts/cert_recommendation.md` |
| Tools | `get_next_cert_suggestions` (inline @tool) |

**SYNERGY_MAP** (next cert suggestions):
```
AI-102 → DP-100, AZ-305
DP-100 → AI-102, DP-203
AZ-305 → AZ-104, AI-102
AZ-204 → AZ-305, AZ-400
AZ-900 → AZ-104, AI-900
AI-900 → AI-102, DP-100
SC-900 → SC-300, SC-200
```

---

## 4. Workflow Layer

### 4.1 WorkflowBuilder (`workflow/certprep_workflow.py`)

- Entry: `OrchestratorAgent`
- Fan-out: `StudyPlanAgent` → `PathCuratorAgent` (concurrent)
- Sequential edges: Orchestrator → Profiler → StudyPlan → PathCurator → Progress
- Executor edges: Progress → ProgressGateway, Assessment → ReadinessRouter
- Storage: `FileCheckpointStorage(directory=~/.certprep_maf/checkpoints)`
- Max iterations: 8 (prevents infinite NOT_READY loops)

### 4.2 HITL Executors (`workflow/executors.py`)

**ProgressGateway** (Gate 1)
- Fires when ProgressAgent emits `readiness_status ∈ {READY, PROGRESSING}` with score ≥ 0.45
- Pauses workflow; asks learner: "Take assessment now (A) or keep studying (B)?"
- A → routes to AssessmentAgent; B → routes to PathCuratorAgent
- State saved to checkpoint: `progress_snapshot`

**QuizGateway** (Gate 2)
- Fires when AssessmentAgent emits `assessment_quiz_generated`
- Presents formatted quiz; pauses workflow; collects learner answers
- Routes back to AssessmentAgent with `ctx.state["quiz_answers"]`
- State saved to checkpoint: `pending_quiz`, `quiz_answers`

**ReadinessRouter**
- Deterministic post-assessment routing:
  - GO → CertRecommendationAgent
  - CONDITIONAL → PathCuratorAgent (with `weak_domains` in state)
  - NOT_READY → StudyPlanAgent (rebuild plan)
- State saved to checkpoint: `assessment_result`

### 4.3 HandoffBuilder Shell (`workflow/handoff_shell.py`)

Provides a lightweight `TriageAgent` as the user-facing entry point. Greets the learner, identifies exam target, then hands off to the `CertPrepWorkflow` via `start_cert_prep_workflow()` trigger tool.

---

## 5. Middleware

Defined in `src/maf/guardrails_middleware.py`, assembled by `build_middleware()`.

| Class | MAF Type | Rules applied |
|-------|----------|---------------|
| `InputGuardrailsMiddleware` | `AgentContextMiddleware` | G-01 to G-05: input length, encoding, PII keyword scan, harmful content. BLOCK raises `ValueError`; WARN logs warning. |
| `ToolCallLimiterMiddleware` | `FunctionContextMiddleware` | Caps MCP tool call count at 12 per agent run. Raises after limit. |
| `OutputPIIMiddleware` | `ChatContextMiddleware` | G-16: PII pattern scan on agent responses. Sets `ctx.state["_pii_in_response"]`. |

All middleware wraps the existing 17-rule `GuardrailsPipeline` from `agentsleague-foundry-sdk/src/cert_prep/guardrails.py`.

---

## 6. Context Provider

`LearnerProfileProvider(BaseContextProvider)` in `src/maf/learner_profile_provider.py`:

- Registered on all agents via `context_providers=[profile_provider]`
- `set_profile(profile: LearnerProfile)` stores the current learner
- `before_run(ctx)` injects into agent context:
  - `learner_name`, `exam_target`, `experience_level`, `preferred_style`
  - `avg_confidence`, `risk_domains`, `modules_to_skip`, `budget_hours`

---

## 7. OTEL & Telemetry (`src/maf/otel.py`)

`configure_otel_providers()` wires:
1. `TracerProvider` with `BatchSpanProcessor` → `AzureMonitorTraceExporter`
2. `MeterProvider` with `PeriodicExportingMetricReader` → `AzureMonitorMetricExporter`
3. Optional `ConsoleSpanExporter` (set `OTEL_CONSOLE=true`)
4. `SERVICE_NAME = "certprep-maf"` on all spans

Called once at Streamlit startup before any agent runs.

---

## 8. Data Models (Reused from foundry-sdk)

All models live in `agentsleague-foundry-sdk/src/cert_prep/models.py` and are imported via the `sys.path` bootstrap in `src/maf/__init__.py`.

| Model | Fields (key) |
|-------|-------------|
| `LearnerProfile` | `name`, `exam_target`, `experience_level`, `preferred_style`, `domain_profiles`, `total_budget_hours` |
| `DomainProfile` | `domain_id`, `domain_name`, `confidence`, `hours_allocated`, `modules` |
| `StudyPlan` | `domains`, `total_weeks`, `hours_per_week`, `start_date`, `prereq_gap` |
| `LearningPath` | `exam_target`, `domains`, `total_hours_estimate` |
| `ProgressSnapshot` | `readiness_score`, `readiness_status`, `hours_logged`, `domain_progress` |
| `ReadinessAssessment` | `readiness_pct`, `verdict`, `weak_domains`, `nudges` |
| `AssessmentResult` | `score_pct`, `passed`, `domain_scores`, `weak_domains` |
| `CertRecommendation` | `decision`, `overall_pct`, `next_cert_suggestions`, `corrective_actions` |

---

## 9. Guardrails Reference

Full 17-rule pipeline from foundry-sdk, wrapped in MAF middleware:

| Rule | Level | Description |
|------|-------|-------------|
| G-01 | BLOCK | Input empty or whitespace only |
| G-02 | BLOCK | Input exceeds 2000 characters |
| G-03 | WARN | Input contains non-UTF-8 characters |
| G-04 | BLOCK | Exam code not in supported registry |
| G-05 | WARN | Hours/week > 40 (unrealistic) |
| G-06 | BLOCK | Study plan total hours > 110% of budget |
| G-07 | WARN | Domain confidence all zeros |
| G-08 | BLOCK | Negative hours in study plan |
| G-09 | BLOCK | Study plan has domain with 0 hours |
| G-10 | WARN | Learning path contains no modules |
| G-11 | BLOCK | Assessment has fewer than 3 questions |
| G-12 | WARN | All quiz answers identical |
| G-13 | BLOCK | Score calculation overflow |
| G-14 | WARN | CertRec GO with score < 60% |
| G-15 | BLOCK | Next cert not in known registry |
| G-16 | BLOCK/WARN | PII or harmful content via Azure Content Safety API (regex fallback) |
| G-17 | BLOCK | URL not in approved domain allowlist |

---

## 10. Environment Configuration

| Variable | Required | Purpose |
|----------|----------|---------|
| `AZURE_AI_PROJECT_CONNECTION_STRING` | Yes | Foundry project connection |
| `AZURE_AI_MODEL_DEPLOYMENT` | Yes | GPT-4o deployment name |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | No | App Insights tracing |
| `MCP_MSLEARN_URL` | No | MS Learn MCP endpoint (default: `https://learn.microsoft.com/api/mcp`) |
| `OTEL_CONSOLE` | No | Set `true` to enable console span exporter |

---

## 11. Supported Exam Blueprints

Defined in `agents/study_plan_agent.py → _EXAM_BLUEPRINTS`:

| Exam | Domains | Weights |
|------|---------|---------|
| AI-102 | Azure AI Services, Computer Vision, NLP, Knowledge Mining, Generative AI | 0.25 / 0.20 / 0.20 / 0.15 / 0.20 |
| DP-100 | Design ML, Explore Data, Feature Engineering, AutoML, Deploy & Retrain | 0.20 / 0.25 / 0.20 / 0.15 / 0.20 |
| AZ-900 | Cloud Concepts, Azure Architecture, Management & Governance, Pricing | 0.25 / 0.35 / 0.30 / 0.10 |

---

## 12. Production Deployment Path

### Phase 1 — Current (MAF Competition Build)
- Streamlit + FileCheckpointStorage (local)
- GPT-4o via Azure AI Foundry `AIProjectClient`
- MS Learn MCP via `MCPStreamableHTTPTool`
- Azure Application Insights distributed tracing
- 3 middleware types, 2 HITL gates, 8 agents

### Phase 2 — Production MVP
- Replace `FileCheckpointStorage` with Azure Cosmos DB checkpoint storage
- Azure Container Apps for hosting
- Azure Key Vault for secrets
- Azure Monitor dashboards for agent latency and guardrail fire rate

### Phase 3 — Full Scale
- Multi-tenant learner isolation
- `azure-ai-evaluation` bias + groundedness evals per agent
- Azure AI Search as MCP fallback for offline MS Learn content
- Real-time progress sync via Microsoft Graph API

---

## 13. Competition Scoring Self-Assessment

| Dimension | Max | Our Score | Justification |
|-----------|-----|-----------|---------------|
| Technical Innovation | 25 | 24 | WorkflowBuilder + HandoffBuilder + 3 middleware types + 2 HITL gates + MCP + OTEL — full MAF stack |
| Azure Services Usage | 20 | 19 | GPT-4o via AI Foundry SDK, MS Learn MCP, App Insights, Content Safety guardrails |
| Problem Impact | 20 | 19 | Real cert failure problem, personalised plans, booking readiness gate, SYNERGY_MAP next-cert |
| Demo Quality | 20 | 18 | Live agents, HITL gate demos, Streamlit chat UI, OTEL traces visible in App Insights |
| Code Quality | 15 | 14 | Typed models, MAF patterns, versioned prompts, middleware separation, checkpoint persistence |
| **Total** | **100** | **94** | |
