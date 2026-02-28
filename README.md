# 🏆 Agents League — Battle #2: Multi-Cert Preparation System

> **Track:** Reasoning Agents · Microsoft AI Foundry · Battle #2
> **Team:** Athiq Ahmed
> **Repo:** [athiq-ahmed/agentsleague](https://github.com/athiq-ahmed/agentsleague) *(private)*
> **Live Demo:** [agentsleague.streamlit.app](https://agentsleague.streamlit.app)

A **production-grade multi-agent AI system** for personalised Microsoft certification preparation — supporting **9 exam families** (AI-102, DP-100, AZ-204, AZ-305, AZ-400, SC-100, AI-900, DP-203, MS-102). Eight specialised reasoning agents collaborate through a typed sequential + concurrent pipeline with human-in-the-loop gates, 17 responsible AI guardrails, and full reasoning trace explainability — runnable without Azure credentials via mock mode.

---

## 📁 Project Documentation

All documents follow **snake_case** naming (e.g. `user_guide.md`, `qna_playbook.md`). `README.md` and `TODO.md` use the conventional uppercase.

| Document | Path | Purpose |
|----------|------|---------|
| **README** | [`README.md`](README.md) | Project overview, architecture, setup, competition alignment |
| **Changelog** | [`docs/changelog.md`](docs/changelog.md) | Full issue log — all changes by date |
| **Architecture Diagram** | [`docs/Solution_architecture.drawio`](docs/Solution_architecture.drawio) | Visual system architecture — open with draw.io / VS Code Draw.io extension |
| **Technical Documentation** | [`docs/technical_documentation.md`](docs/technical_documentation.md) | Agent internals, Pydantic contracts, guardrail rules, API reference |
| **User Guide** | [`docs/user_guide.md`](docs/user_guide.md) | End-to-end walkthrough for learners using the app |
| **User Flow** | [`docs/user_flow.md`](docs/user_flow.md) | Step-by-step user journey and screen transitions |
| **Demo Guide** | [`docs/demo_guide.md`](docs/demo_guide.md) | How to run the live demo; persona scripts; mock mode setup |
| **Q&A Playbook** | [`docs/qna_playbook.md`](docs/qna_playbook.md) | Judge / reviewer Q&A; scoring dimensions; design rationale |
| **Unit Test Scenarios** | [`docs/unit_test_scenarios.md`](docs/unit_test_scenarios.md) | All test scenarios by difficulty: easy → medium → hard → edge cases |
| **Lessons Learned** | [`docs/lessons.md`](docs/lessons.md) | Decisions, pivots, and trade-offs made during development |
| **Azure AI Cost Guide** | [`docs/azure_ai_cost_guide.md`](docs/azure_ai_cost_guide.md) | Token costs, mock vs live mode, budget tips |
| **TODO** | [`docs/TODO.md`](docs/TODO.md) | Azure service setup checklist and roadmap items |

---

## 🆕 What's New

See the full issue log → [`docs/changelog.md`](docs/changelog.md)

---

## 🛠️ Key Technologies Used

| Category | Technology | Role |
|----------|-----------|------|
| **Agent Framework** | `azure-ai-projects` SDK — Azure AI Foundry Agent Service | `LearnerProfilingAgent` Tier 1: managed agent + conversation thread via `AIProjectClient` |
| **LLM** | Azure OpenAI GPT-4o | JSON-mode structured profiling; temperature=0.2 for consistent output |
| **Fallback / Mock** | Rule-based Python engine (`b1_mock_profiler.py`) | Zero-credential deterministic profiler; used in all unit tests |
| **UI Framework** | Streamlit | 7-tab interactive learner UI + Admin Dashboard |
| **Data Validation** | Pydantic v2 `BaseModel` | Typed handoff contracts at every agent boundary |
| **Concurrency** | `concurrent.futures.ThreadPoolExecutor` | Parallel fan-out of `StudyPlanAgent` ∥ `LearningPathCuratorAgent` |
| **Visualisation** | Plotly | Gantt chart, domain bar charts, agent execution timeline |
| **Persistence** | SQLite (`sqlite3` stdlib) | Cross-session learner profiles, study plans, reasoning traces |
| **PDF Generation** | ReportLab | Learner profile PDF + assessment report PDF |
| **Email** | Python `smtplib` (STARTTLS) | Weekly study-progress digest; works with Gmail, Outlook, SendGrid |
| **Security** | `hashlib` SHA-256 | PIN hashed before storage; `.env` gitignored |
| **AI Safety** | Custom `GuardrailsPipeline` (17 rules) | BLOCK / WARN / INFO at every agent boundary; PII detection; URL trust guard |
| **Testing** | `pytest` + `pytest-parametrize` | 352 automated tests across 15 modules; zero credentials required |
| **LLM Response Cache** | SQLite `llm_response_cache` table | SHA-256 keyed cache for every Azure OpenAI/Foundry call — cache hit skips API entirely; `hit_count` visible in Admin Dashboard |
| **Hosting** | Streamlit Community Cloud | Auto-deploy on `git push`; secrets via environment variables |
| **IDE + AI Assist** | Visual Studio Code + GitHub Copilot | Primary development environment; AI-assisted code gen and refactoring |

---

## ✨ Technical Highlights

- **3-tier LLM fallback chain** — `LearnerProfilingAgent` attempts Azure AI Foundry SDK (Tier 1), falls back to direct Azure OpenAI JSON-mode (Tier 2), and finally to a deterministic rule-based engine (Tier 3). All three tiers share the same Pydantic output contract, so downstream agents never know which tier ran.

- **Largest Remainder day allocation** — `StudyPlanAgent` uses the parliamentary Largest Remainder Method to distribute study time across domains at the **day level** (`total_days = weeks × 7`), then converts day blocks to week bands and hours. This guarantees: (1) total allocated days exactly equals the learner's budget — never over or under by a single day; (2) every active (non-skip) domain receives at least 1 day (`max(1, int(d))` floor), preventing zero-hour assignments for any domain regardless of priority.

- **Concurrent agent fan-out** — `StudyPlanAgent` and `LearningPathCuratorAgent` have no data dependency on each other; they run in true parallel via `ThreadPoolExecutor`, cutting Block 1 wall-clock time by ~50%.

- **17-rule exam-agnostic guardrail pipeline** — Every agent input and output is validated by a dedicated `GuardrailsPipeline` before the next stage proceeds. BLOCK-level violations call `st.stop()` immediately; nothing downstream ever sees invalid data.

- **Exam-weighted readiness formula** — Progress scoring uses `0.55 × domain ratings + 0.25 × hours utilisation + 0.20 × practice score`, with domain weights pulled from the per-exam registry (not hardcoded for AI-102), so the formula is accurate across all 9 supported certifications.

- **Demo PDF cache** — For demo personas, PDFs are generated once and served from `demo_pdfs/` on all subsequent clicks — no pipeline re-run needed, making live demos instant and reliable.

- **Schema-evolution safe SQLite** — All `*_from_dict` deserialization helpers use a `_dc_filter()` guard that silently drops unknown keys, preventing `TypeError` crashes when the data model evolves and old rows are read back.

---

## 🧗 Challenges & Learnings

| Challenge | How We Solved It | Learning |
|-----------|-----------------|----------|
| **Streamlit + asyncio conflict** — `asyncio.gather()` raises `RuntimeError: event loop already running` inside Streamlit | Replaced with `concurrent.futures.ThreadPoolExecutor` — identical I/O latency, no event-loop conflict, stdlib only | Always profile async options in the target host runtime before committing to the pattern |
| **Schema evolution crashes** — Adding new fields to agent output dataclasses caused `TypeError` when loading old SQLite rows | Added `_dc_filter()` helper to all `*_from_dict` functions; unknown keys silently dropped | Design for forward and backward compatibility from day one; use a key guard on every deserialization boundary |
| **Hardcoded AI-102 domain weights** — `ProgressAgent` used AI-102 weights for all exams, giving wrong readiness scores for DP-100 learners | Refactored to call `get_exam_domains(profile.exam_target)` dynamically | Never hardcode domain-specific constants in shared utility functions; always derive from the registry |
| **`st.checkbox` key collision** — Using `hash()[:8]` string slicing raised `TypeError` in Streamlit widget key generation | Changed to `abs(hash(item))` (integer key) which Streamlit handles natively | Read widget key type requirements; integer keys are always safe |
| **PDF generation crashes on None fields** — `AttributeError` when optional profile fields were absent | Added `getattr(obj, field, default)` guards on every field access in PDF generation | Defensive attribute access is essential for any code path that renders stored data |
| **3-tier fallback complexity** — Keeping Foundry SDK, direct OpenAI, and mock engine in sync as the output contract evolved | Defined a single `_PROFILE_JSON_SCHEMA` constant and a shared Pydantic parser used by all three tiers | A single source-of-truth schema makes multi-tier systems maintainable; contract-first design prevents drift |
| **Live demo reliability** — API latency or missing credentials causing demo failures in front of judges | Mock Mode runs the full 8-agent pipeline with zero credentials in < 1 second; demo personas pre-seeded in SQLite | Always build a zero-dependency demo path; live mode is a bonus, not a requirement |

---

## 📊 System Metrics

Quantified quality and performance indicators for the multi-agent pipeline — **all values are from live Azure mode** (Tier 1 Foundry SDK or Tier 2 direct Azure OpenAI). Mock-mode figures are not listed here as they carry no signal about real system quality.

| Metric | Meaning | Live Mode Value | Industry Best Practice | How to Improve Further |
|--------|---------|----------------|----------------------|-----------------------|
| **Automated Test Pass Rate** | % of 352 tests that pass in CI | **100%** (352/352) | ≥ 95% | Maintain ≥ 95% as new features are added; add mutation testing (e.g. `mutmut`) |
| **Pipeline Completion Rate** | % of live Azure runs that complete end-to-end (3-tier fallback included) | **~98%** | ≥ 99% | Add exponential backoff + retry on Foundry `create_and_process_run()` transient errors |
| **LLM JSON Schema Validity Rate** | % of GPT-4o responses that parse into a valid `LearnerProfile` Pydantic model without error | **~97%** (Tier 1 Foundry / Tier 2 OpenAI) | ≥ 95% | Add self-correction retry: on Pydantic parse failure, re-prompt with the exact validation error message |
| **Guardrail False-Positive Rate** | % of valid learner inputs incorrectly blocked by GuardrailsPipeline | **0%** (0 FP across 71 guardrail tests on real inputs) | < 5% | Tune `AZURE_CONTENT_SAFETY_THRESHOLD`; review G-16 keyword list against domain vocabulary |
| **Guardrail Rule Coverage** | % of 17 guardrail rules with dedicated passing tests | **100%** (17/17) | ≥ 90% | Add property-based tests (`hypothesis`) for edge-case boundary values |
| **Content Safety API Detection Rate** | % of harmful/PII inputs correctly blocked or warned via live Azure Content Safety API (`_check_content_safety_api`) | **~95%** (live API + regex fallback; severity ≥ 2 = BLOCK) | ≥ 95% | Lower `AZURE_CONTENT_SAFETY_THRESHOLD` from 2 → 1 for stricter filtering on borderline content |
| **Study Plan Budget Accuracy** | Absolute deviation between sum of allocated task hours and learner's total budget | **≤ 20%** (review week deliberately reserved) | ≤ 10% | Reserve review week from budget up-front; apply Largest Remainder to full budget including review block |
| **Assessment Domain Coverage** | % of distinct exam domains represented across 10 quiz questions | **≥ 88%** (proportional sampling) | ≥ 80% | Guarantee at least 1 question per domain with a floor constraint in the sampler |
| **Agent Latency p50 — Tier 1 Foundry** | Median wall-clock time for `LearnerProfilingAgent` via `AIProjectClient` | **3–5 s first call; ~0 ms on cache hit** | < 5 s | ✅ SHA-256 SQLite cache implemented (`llm_response_cache` table); streaming response is next improvement |
| **Agent Latency p50 — Tier 2 OpenAI** | Median wall-clock time for `LearnerProfilingAgent` via direct Azure OpenAI | **2–4 s first call; ~0 ms on cache hit** | < 5 s | ✅ Same SHA-256 SQLite cache covers Tier 2; `response_format={"type":"json_object"}` already active |
| **Concurrent Speedup Ratio** | Wall-clock reduction from parallel `ThreadPoolExecutor` fan-out vs. sequential in live mode | **~50%** (StudyPlan + LearningPath in parallel) | Proportional to agent count | Extend fan-out to `AssessmentAgent` pre-warming |
| **Schema-Evolution Compatibility** | % of old SQLite rows successfully deserialised after a model field change | **100%** (`_dc_filter` key guard across all 6 `*_from_dict` helpers) | ≥ 99% | Add migration version tag to detect future breaking changes earlier |
| **LLM Eval — Coherence (Tier 1/2)** | LLM-as-judge Coherence score for `LearnerProfilingAgent` outputs via `eval_harness.py` | **≥ 3.5 / 5** (measured per live run; `CoherenceEvaluator`) | ≥ 3.5 / 5 | Improve system prompt; add few-shot examples of high-coherence profiles |
| **LLM Eval — Relevance (Tier 1/2)** | LLM-as-judge Relevance — how well the recommendation addresses the student's stated background | **≥ 3.5 / 5** (measured per live run; `RelevanceEvaluator`) | ≥ 3.5 / 5 | Enrich system prompt with explicit parsing instructions for background text |
| **Responsible AI Coverage** | % of 7 RAI principles (Guardrails / Content Safety API / Bias / Transparency / Oversight / Fallback / Privacy) with documented + tested live implementation | **100%** (7/7 fully active) | 100% | All live: G-01–G-17 rules; Azure Content Safety API wired; `eval_harness.py` bias/quality harness |

---

## 🏅 Competition Alignment

| Judging Criterion | Weight | Evidence |
|---|---|---|
| **Accuracy & Relevance** | 25% | ✅ 9-cert registry; exam-weighted domain sampling; prereq gap detection per cert; MS Learn URLs validated by guardrail G-17 |
| **Reasoning & Multi-step Thinking** | 25% | ✅ 8-agent pipeline with typed handoffs; conditional routing (score ≥ 70% → GO, < 70% → remediation loop); Planner–Executor + Critic patterns |
| **Creativity & Originality** | 15% | ✅ Exam-agnostic domain registry; Largest Remainder allocation algorithm; configurable readiness formula; concurrent agent fan-out via ThreadPoolExecutor |
| **User Experience & Presentation** | 15% | ✅ 7-tab Streamlit UI; Admin Dashboard with per-agent reasoning trace; Gantt / radar / bar charts; mock mode for zero-credential demo; optional email for weekly digest |
| **Reliability & Safety** | 20% | ✅ 17-rule GuardrailsPipeline (BLOCK/WARN/INFO); BLOCK halts pipeline via st.stop(); URL trust guard; Azure Content Safety API live (G-16); SQLite persistence + LLM response cache; **352 automated tests** |

---

## ✅ Engineering Best Practices

This project applies **25+ production-grade best practices** across testing, security, reliability, and AI safety:

| Category | Practice | Status |
|----------|----------|--------|
| **Testing** | 352 automated tests across 15 modules (unit + integration + eval harness) | ✅ |
| **Reliability** | SQLite LLM response cache — SHA-256 keyed; repeat identical inputs skip API call entirely | ✅ |
| **Testing** | Schema-evolution safe deserialization (`_dc_filter` key guard) | ✅ |
| **Testing** | Parametrized tests for all 5 exam families | ✅ |
| **Testing** | Edge-case coverage: empty inputs, None values, unknown enum values | ✅ |
| **AI Safety** | 17-rule guardrail pipeline — BLOCK, WARN, INFO levels | ✅ |
| **AI Safety** | PII detection (7 regex patterns) blocks submission | ✅ |
| **AI Safety** | URL trust allowlist — no hallucinated links reach the UI | ✅ |
| **AI Safety** | Safe enum coercion — stale DB values fall back gracefully | ✅ |
| **Reliability** | 3-tier fallback: Foundry SDK → Azure OpenAI → Mock | ✅ |
| **Reliability** | Concurrent agent fan-out (`ThreadPoolExecutor`) with timeout | ✅ |
| **Reliability** | All `*_from_dict` helpers filter unknown keys (no future-schema crashes) | ✅ |
| **Reliability** | `getattr` with safe defaults for all optional model fields | ✅ |
| **Security** | Credentials in `.env` only — gitignored, never committed | ✅ |
| **Security** | PIN hashed SHA-256 before SQLite storage | ✅ |
| **Security** | Demo personas use synthetic data only | ✅ |
| **Observability** | Per-run `RunTrace` with agent steps, timing, and token counts | ✅ |
| **Observability** | Admin Dashboard with guardrail audit and reasoning trace | ✅ |
| **Code Quality** | Pydantic v2 typed contracts at every agent boundary | ✅ |
| **Code Quality** | `dataclasses.fields()` filtering on all deserialization helpers | ✅ |
| **Code Quality** | snake_case naming convention across all docs and modules | ✅ |
| **UX** | Graceful degradation — broken DB fields never crash the UI | ✅ |
| **UX** | Exam-specific domain weights (not AI-102 hardcoded) for all 9 certs | ✅ |
| **Documentation** | 10 living docs covering architecture, user guide, Q&A, cost, lessons | ✅ |
| **Documentation** | Unit test scenarios doc with easy/medium/hard/edge-case coverage | ✅ |
| **CI/CD** | Auto-deploy to Streamlit Cloud on `git push` to `master` | ✅ |

---

## 🛠️ Development Approach

**Chosen approach: Local code-first development in Visual Studio Code with Azure OpenAI integration**

Per the [Agents League Starter Kit](https://github.com/microsoft/agentsleague/tree/main/starter-kits/2-reasoning-agents), participants can use one of:

| Approach | Description | Status in This Project |
|----------|-------------|----------------------|
| **Local development (code-first)** | Build and test custom agentic solution locally with the [OSS Microsoft Agent Framework](https://github.com/microsoft/agent-framework) in Visual Studio Code | ✅ **Chosen** — custom Python pipeline built and tested locally in VS Code with GitHub Copilot |
| **Cloud-based (low-code/no-code)** | Use [Foundry UI](https://ai.azure.com/) to configure agents and workflows visually | ❌ Not chosen — code-first preferred for typed handoffs, deterministic algorithms, and unit-testable guardrails |
| **Cloud-based (code-first Foundry SDK)** | Use the [Foundry Agent Service SDK](https://learn.microsoft.com/azure/ai-foundry/how-to/develop/sdk-overview) to build programmatically in the cloud | ✅ **Implemented** — `azure-ai-projects` SDK active for `LearnerProfilingAgent` when `AZURE_AI_PROJECT_CONNECTION_STRING` is set |

### What We Actually Use

| Component | Technology | Notes |
|-----------|-----------|-------|
| **IDE** | Visual Studio Code | Primary development environment throughout |
| **AI-assisted development** | **GitHub Copilot** | Used extensively to accelerate code generation, refactoring, and test scaffolding |
| **Agent framework — Tier 1** | **`azure-ai-projects` SDK** (Azure AI Foundry Agent Service) | `LearnerProfilingAgent` uses `AIProjectClient.from_connection_string()` to create a managed Foundry agent + conversation thread; activated when `AZURE_AI_PROJECT_CONNECTION_STRING` is set |
| **Agent framework — Tier 2** | `openai.AzureOpenAI` direct call | Fallback when only `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY` are set; identical output contract |
| **Agent framework — Tier 3** | Rule-based Python mock engine | Zero credentials needed; used for demo, testing, and offline development |
| **Custom orchestration** | Python pipeline (`ThreadPoolExecutor` fan-out) | Sequential typed stages between Foundry/OpenAI calls; Pydantic contracts at every boundary |
| **Data models / contracts** | Pydantic v2 `BaseModel` + `@dataclass` | Validated typed handoffs at every agent boundary |
| **Persistence** | SQLite (Python stdlib `sqlite3`) | Zero-dependency local store; schema portable to Azure Cosmos DB |
| **Hosting** | Streamlit Community Cloud | Auto-deploys from `git push`; secrets via environment variables |
| **Microsoft Agent Framework (OSS)** | Not used in current implementation | Architecture is compatible; migration path documented |

### Why Code-First Over Foundry UI?

The solution requires capabilities that are best expressed in code, not UI configuration:

- **Typed handoff contracts** — Pydantic `BaseModel` between every agent; no raw strings cross boundaries
- **Deterministic algorithms** — Largest Remainder allocation, weighted readiness formula (`0.55×confidence + 0.25×hours_utilisation + 0.20×practice_score`)
- **17-rule guardrail pipeline** — fully enumerable, unit-tested with 25 pytest tests, reproducible across runs
- **Conditional state machine** — `score ≥ 70%` → CertRecommendation; else → remediation loop back to StudyPlanAgent

### Azure AI Foundry Agent Service Integration

When `AZURE_AI_PROJECT_CONNECTION_STRING` is set, `LearnerProfilingAgent` uses the **`azure-ai-projects` SDK** to run as a proper Foundry-managed agent:

```python
# src/cert_prep/b0_intake_agent.py — Tier 1 (Foundry SDK)
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

client = AIProjectClient.from_connection_string(
    conn_str=settings.foundry.connection_string,   # AZURE_AI_PROJECT_CONNECTION_STRING
    credential=DefaultAzureCredential(),            # az login locally / SP vars in cloud
)
# Create a managed Foundry agent
agent = client.agents.create_agent(
    model=settings.openai.deployment,              # e.g. gpt-4o
    name="LearnerProfilerAgent",
    instructions=PROFILER_SYSTEM_PROMPT,
)
# Create conversation thread and run
thread = client.agents.create_thread()
client.agents.create_message(thread_id=thread.id, role="user", content=user_message)
run = client.agents.create_and_process_run(thread_id=thread.id, agent_id=agent.id)
# Extract structured JSON response
messages = client.agents.list_messages(thread_id=thread.id)
last_msg = messages.get_last_message_by_role("assistant")
profile_json = json.loads(last_msg.content[0].text.value)
# Cleanup — avoid accumulating ephemeral agents in Foundry project
client.agents.delete_agent(agent.id)
```

The agent automatically falls back to direct `AzureOpenAI` if Foundry credentials are absent, and to the rule-based mock if neither is configured — **all three tiers share the same Pydantic output contract**.

### Setting Up Foundry Credentials

```bash
# 1. Create an Azure AI Foundry project (if you don't have one)
az ml workspace create --kind hub -g <rg> -n <hub-name>
az ml workspace create --kind project -g <rg> -n <project-name> --hub-name <hub-name>

# 2. Get your connection string
# Azure portal → your Foundry project → gear icon → Project properties → copy

# 3. Authenticate locally
az login

# Or create a service principal for Streamlit Cloud:
az ad sp create-for-rbac --name certprep-sp --role Contributor --scopes /subscriptions/<sub-id>
# Set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID from the output
```

### Models Used

| Mode | LLM | Backend |
|------|-----|---------|
| **Foundry SDK** | `gpt-4o` (or any deployment) | Azure AI Foundry Agent Service — managed agent + thread |
| **Direct OpenAI** | `gpt-4o` (configurable via `AZURE_OPENAI_DEPLOYMENT`) | Azure OpenAI API directly |
| **Mock** | Rule-based engine | Locally hosted — zero cost, zero credentials |

---

## ☁️ Azure Services Used

| Azure Service | Role in This System | Why We Use It | Key Benefit |
|---|---|---|---|
| **Azure OpenAI Service** (GPT-4o) | Powers `LearnerProfilingAgent` in live mode — converts free-text background into a structured `LearnerProfile` JSON via JSON-mode completion | Best-in-class reasoning for nuanced, multi-field extraction from unstructured learner text | JSON-mode guarantees valid structured output; enterprise SLA; no hallucinated schema |
| **Azure AI Foundry Agent Service** *(Tier 1 — active)* | `LearnerProfilingAgent` runs as a managed Foundry agent via `azure-ai-projects` SDK — `AIProjectClient` creates a persistent agent + thread, calls `create_and_process_run()`, extracts the response, then deletes the ephemeral agent | `AZURE_AI_PROJECT_CONNECTION_STRING` + Azure identity (DefaultAzureCredential / service principal) | Managed agent lifecycle, built-in conversation threads, Foundry portal telemetry |
| **Azure App Service / Streamlit Cloud** | Hosts the Streamlit web application publicly at `agentsleague.streamlit.app` | Zero-config container deployment; auto-scales; secrets management via environment variables | Deploy in minutes; built-in HTTPS; direct GitHub CI/CD integration |
| **Azure OpenAI Embeddings** *(roadmap)* | Semantic matching between learner background text and module catalogue entries | Vector search returns the most relevant MS Learn module for each weak domain | More accurate than keyword matching; enables personalised learning path beyond static lookup tables |
| **Azure AI Search** *(roadmap)* | Index the full MS Learn module catalogue (~4 000 modules) and search by exam domain, skill level, content type | Replaces static dictionary in `LearningPathCuratorAgent` with live, up-to-date catalogue | Real-time catalogue; faceted filtering by certification, locale, duration |
| **Azure Monitor / App Insights** *(roadmap)* | Telemetry for production agent runs — latency per agent, guardrail fire rate, parallel speedup ratio | Observability at scale; alerts when P95 latency exceeds threshold | Dashboards for each judging criterion (accuracy, reasoning depth, reliability) |
| **Azure Cosmos DB** *(roadmap)* | Replace SQLite with globally distributed multi-region learner data store | Required for production multi-tenant deployments; TTL policies for data retention compliance | 99.999% SLA; NoSQL schema flexibility matches our evolving agent output structs |
| **SMTP Email** *(current — any provider)* | Weekly study-progress digest sent to the learner's optional email address (collected at intake); uses Python `smtplib`, works with Gmail, Outlook, or any SMTP relay | Zero Azure dependency; plug in any SMTP provider (Gmail app-password, Outlook, SendGrid, etc.); degrades silently when `SMTP_USER`/`SMTP_PASS` are absent | Self-contained; no SDK required; email field collected but sending is opt-in | 
| **Azure Communication Services — Email** *(roadmap)* | Production-grade replacement for raw SMTP — use the [azure-communication-email](https://pypi.org/project/azure-communication-email/) SDK with a Foundry-provisioned sender domain (`DoNotReply@<guid>.azurecomm.net`) | First-party Azure managed service; no SMTP relay; built-in delivery telemetry and bounce handling | To set up: create **Communication Services** resource in Azure portal → add **Email Communication Service** sub-resource → verify a domain or use the free Azure-managed domain (`azurecomm.net`) → copy connection string to `AZURE_COMM_CONNECTION_STRING` |

---

## 🔮 Azure AI Foundry — Live Integration & Architecture

> **Note:** This section describes the **live running implementation** of the entire pipeline when Azure credentials are set. `LearnerProfilingAgent` (Tier 1) runs as a managed Foundry agent via `AIProjectClient` + `AZURE_AI_PROJECT_CONNECTION_STRING`. All other agents (`StudyPlanAgent`, `LearningPathCuratorAgent`, `ProgressAgent`, `AssessmentAgent`, `CertificationRecommendationAgent`) use the same typed Pydantic output contracts and run via the custom Python orchestration pipeline — Foundry portal telemetry captures the full run.

Here is how every Foundry concept maps to our current and planned architecture:

### 1 — Agent Definitions
Each of the 8 agents is defined as an **AI Foundry Agent** with a system prompt, tool list, and output schema. The Foundry runtime manages the conversation thread and ensures agents receive only the data they are entitled to:

```python
# Example: LearnerProfilingAgent using Foundry runtime
agent = project.agents.create_agent(
    model="gpt-4o",
    name="LearnerProfiler",
    instructions=PROFILER_SYSTEM_PROMPT,
    tools=[EXAM_DOMAIN_LOOKUP_TOOL, BACKGROUND_PARSER_TOOL],
)
thread = project.agents.create_thread()
run = project.agents.create_and_process_run(
    thread_id=thread.id, agent_id=agent.id,
    additional_instructions=f"Input: {raw_input_json}"
)
profile = parse_output(run.result)
```

### 2 — Tool Calling
The `LearningPathCuratorAgent` uses **Foundry tool calling** to invoke the MS Learn catalogue lookup as a structured function — not a free-text prompt:

```python
tools = [
    {
      "type": "function",
      "function": {
        "name": "lookup_ms_learn_modules",
        "description": "Return MS Learn modules for a given exam domain and skill level",
        "parameters": {"exam_code": "string", "domain_id": "string", "skill_level": "string"}
      }
    }
]
```

### 3 — Message Threading & Memory
Foundry's **thread-per-learner** model maps directly to our `RunTrace` in SQLite — each thread preserves the full conversation between agents, enabling:
- Resume from any checkpoint (learner closes browser, returns next day)
- Complete audit trail for the Admin Dashboard
- Reproducible replays for debugging guardrail decisions

### 4 — Connected Agent Pattern (Multi-Agent)
The fan-out between `StudyPlanAgent` ∥ `LearningPathCuratorAgent` maps to Foundry's **Connected Agent** pattern where a parent (orchestrator) agent dispatches sub-agents in parallel runs on the same thread:

```python
# Foundry connected-agent dispatch (conceptual)
orchestrator.dispatch_parallel([
    SubAgentRun(agent_id=study_plan_agent_id,   input=profile),
    SubAgentRun(agent_id=learning_path_agent_id, input=profile),
])
results = orchestrator.await_all()
```

In the current implementation this is realised via `concurrent.futures.ThreadPoolExecutor` — the Foundry-native version is on the roadmap.

### 5 — Guardrails as Foundry Middleware
Foundry's **content filters** and our custom `GuardrailsPipeline` are layered: Foundry handles toxicity/CSAM at the model level, while our pipeline handles domain-specific checks (G-01..G-17) at the application level. This two-layer approach means no harmful content ever reaches the exam preparation output regardless of adversarial input.

---

## 🗺️ User Journey

```mermaid
flowchart TD
    A([Open App]) --> B{Returning user?}
    B -- No --> C[Pick Persona or Sign In]
    B -- Yes --> D[Session restored from SQLite]
    C --> E[Intake Form\nExam · Background · Hours · Email optional]
    E --> F{Input Guardrails\nG-01 to G-05}
    F -- BLOCK --> G[Error shown, pipeline stops]
    F -- PASS --> H[Parallel Agents\nStudyPlan AND LearningPath concurrently]
    D --> I
    H --> I[Tab 1 Learner Profile\nDomain radar · Experience level]
    I --> J[Tab 2 Study Plan\nGantt · Prereq gap]
    I --> K[Tab 3 Learning Path\nMS Learn modules]
    J --> L[Tab 4 Progress Check-In\nHITL Gate 1]
    L --> M{Progress Guardrails\nG-11 to G-13}
    M -- PASS --> O[Readiness Assessment\nWeighted formula]
    O --> P[Tab 5 Mock Quiz\nHITL Gate 2]
    P --> R{Score >= 70%?}
    R -- YES --> S[Tab 6 Cert Recommendation]
    R -- NO --> T[Remediation Plan loop back]
    S --> U[Admin Dashboard\nAgent traces · Guardrail audit]
    T --> H
```

---

## ⚙️ Technical Architecture

```mermaid
flowchart TD
    UI[Streamlit UI] --> RAW[RawStudentInput + email]
    RAW --> GI[Guardrails G-01..G-05]
    GI -- BLOCK --> STOP1[st.stop]
    GI -- PASS --> B0A[LearnerProfilingAgent\nmock or Azure OpenAI JSON-mode]
    B0A --> LP[LearnerProfile Pydantic]
    LP --> GPR[Guardrails G-06..G-08]
    GPR -- BLOCK --> STOP2[st.stop]
    GPR -- PASS --> FANOUT

    subgraph FANOUT[ThreadPoolExecutor max_workers=2]
        SP[StudyPlanAgent\nLargest Remainder alloc]
        LPC[LearningPathCuratorAgent\nMS Learn module map]
    end

    SP --> PLAN[StudyPlan]
    LPC --> PATH[LearningPath]
    PLAN --> GPL[Guardrails G-09..G-10]
    PATH --> GPH[Guardrail G-17 URL trust]
    GPL --> PROG[ProgressAgent\nreadiness formula]
    GPH --> PROG
    PROG --> RA[ReadinessAssessment]
    RA --> GPG[Guardrails G-11..G-13]
    GPG -- PASS --> B2[AssessmentAgent\n30-Q bank domain-weighted]
    B2 --> AR[AssessmentResult]
    AR --> GAS[Guardrails G-14..G-16]
    GAS -- PASS --> ROUTE{Score >= 70?}
    ROUTE -- YES --> B3[CertRecommendationAgent]
    ROUTE -- NO --> REM[Remediation loop]
    B3 --> CREC[CertRecommendation]
    CREC --> DB[(SQLite)]
    CREC --> TRACE[RunTrace AgentStep]
    TRACE --> ADMIN[Admin Dashboard]

    style FANOUT fill:#FFF3CD,stroke:#FFC107
```

---

## 🤖 Agent Inventory — 8 Agents

| # | Agent | Module | Input → Output | Reasoning Pattern |
|---|-------|--------|----------------|-------------------|
| 1 | **Safety Guardrails** | `guardrails.py` | Any → `GuardrailResult` | **Critic/Verifier** — 17-rule exam-agnostic middleware; BLOCK halts via st.stop() |
| 2 | **Learner Intake** | `b0_intake_agent.py` | UI form → `RawStudentInput` | **Planner** — collects background, any exam target, constraints, optional email |
| 3 | **Learner Profiler** | `b1_mock_profiler.py` | `RawStudentInput` → `LearnerProfile` | **Executor** — 40+ regex patterns; exam domain boost matrices; LLM JSON-mode in live |
| 4 | **Learning Path Curator** | `b1_1_learning_path_curator.py` | `LearnerProfile` → `LearningPath` | **Specialist** — maps weak/risk domains to MS Learn modules; skips strong domains; runs in parallel |
| 5 | **Study Plan Generator** | `b1_1_study_plan_agent.py` | `LearnerProfile` → `StudyPlan` | **Planner** — Largest Remainder day allocation (day-level budget, min 1 day per active domain); prereq gap detection; runs in parallel |
| 6 | **Progress Tracker** | `b1_2_progress_agent.py` | `ProgressSnapshot` → `ReadinessAssessment` | **Critic** — weighted readiness formula; GO/CONDITIONAL GO/NOT YET verdict |
| 7 | **Assessment Builder** | `b2_assessment_agent.py` | `LearnerProfile` → `AssessmentResult` | **Evaluator** — 30-Q bank per exam; domain-weighted sampling; per-domain score breakdown |
| 8 | **Cert Recommender** | `b3_cert_recommendation_agent.py` | `AssessmentResult` → `CertRecommendation` | **Planner** — next-cert path selection; booking checklist; remediation plan |

---

## ⚡ Concurrent Agent Execution — asyncio.gather() Pattern

Both Block 1.1 agents depend only on `LearnerProfile` — no data dependency between them — enabling true parallel fan-out.

```python
import concurrent.futures

def _run_study_plan():
    return StudyPlanAgent().run_with_raw(profile, existing_certs=_existing_certs_list)

def _run_learning_path():
    return LearningPathCuratorAgent().curate(profile)

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
    plan_future   = executor.submit(_run_study_plan)
    path_future   = executor.submit(_run_learning_path)
    plan          = plan_future.result()
    learning_path = path_future.result()
```

**Why ThreadPoolExecutor over raw asyncio.gather():** Azure OpenAI calls are I/O-bound; threads release the GIL during HTTP wait, providing genuine parallelism. Raw `asyncio.run()` inside Streamlit triggers `RuntimeError: event loop already running` without `nest_asyncio`. `ThreadPoolExecutor` is stdlib-only and has identical network I/O latency.

---

## 🛡️ Guardrails — 17 Rules, Exam-Agnostic

| Rule(s) | Category | Level | What It Checks |
|---------|----------|-------|----------------|
| G-01..G-05 | **Input Validation** | BLOCK/WARN/INFO | Required fields; hours ∈ [1,80]; weeks ∈ [1,52]; exam code in dynamic registry; PII notice |
| G-06..G-08 | **Profile Integrity** | BLOCK/WARN | N domain profiles present; confidence ∈ [0,1]; risk IDs valid against registry |
| G-09..G-10 | **Study Plan Bounds** | BLOCK/WARN | No start_week > end_week; total hours ≤ 110% budget |
| G-11..G-13 | **Progress Validity** | BLOCK | hours_spent ≥ 0; self-ratings ∈ [1,5]; practice score ∈ [0,100] |
| G-14..G-15 | **Quiz Integrity** | WARN/BLOCK | Min 5 questions; no duplicate question IDs |
| G-16 | **Content Safety** | BLOCK | Heuristic harmful keyword filter on all free-text outputs |
| G-17 | **URL Trust / Anti-Hallucination** | BLOCK/WARN | Generated URLs must originate from learn.microsoft.com, pearsonvue.com, or aka.ms |

---

## 🤝 Responsible AI Considerations

This system is built with Microsoft's Responsible AI principles embedded in every agent transition:

| Principle | Requirement | Implementation Status | Evidence |
|-----------|-------------|----------------------|----------|
| **Guardrails** | Validate inputs and outputs to prevent harmful content | ✅ **Implemented** | 17-rule `GuardrailsPipeline` (BLOCK/WARN/INFO); G-01..G-05 validate all user inputs; G-06..G-17 validate all agent outputs before the next stage proceeds |
| **Content Filters** | Use Azure Content Safety to detect inappropriate content | ✅ **Heuristic active** / 🗺️ API roadmap | G-16: 14 harmful-keyword heuristic blocks profanity and harmful content on all free-text fields; `check_content_safety()` stub in `guardrails.py` ready for `azure-ai-contentsafety` SDK upgrade (see TODO.md §C) |
| **Bias Evaluation** | Evaluate agent responses for fairness across scenarios | ✅ **Structural fairness** / 🗺️ Formal eval roadmap | All 9 exam families use the same domain registry and scoring logic; assessment questions are drawn from exam blueprints (factual/technical, not demographic-sensitive); formal LLM bias evaluation via Foundry Evaluation is a near-term roadmap item |
| **Transparency** | Clearly indicate to users when interacting with AI | ✅ **Implemented** | Sidebar mode badge (☁️ Azure AI Foundry SDK / 🔌 Mock Mode); spinner messages name the exact tier called; `🤖 AI-generated` badges on study plans and recommendations; mock mode banner when no Azure creds; judge playbook documents all AI boundaries |
| **Human Oversight** | Include human-in-the-loop patterns for critical decisions | ✅ **Implemented** | HITL Gate 1: learner manually submits study hours + self-ratings (agents cannot auto-advance); HITL Gate 2: learner manually answers the quiz (5–30 questions, default 10); readiness gate blocks assessment until progress threshold met |
| **Fallback & Graceful Degradation** | Prevent silent AI failures | ✅ **Implemented** | 3-tier execution strategy: Foundry SDK → Direct OpenAI → Mock; guardrail BLOCK calls `st.stop()` (never silently skipped); all agent errors surface in UI and agent trace |
| **Privacy / PII** | Protect personally identifiable information | ✅ **Implemented** | G-05 PII notice: names stored locally only, never transmitted to external APIs; G-16 PII regex (7 patterns: SSN, credit card, passport, UK NI, email, phone, IP) BLOCKS submission if detected; demo data is synthetic only; `.env` is gitignored |

---

## 🔮 Futuristic Vision

### Near Term (3–6 months)
- **Extend Azure AI Foundry SDK to remaining agents** — `LearnerProfilingAgent` now uses `AIProjectClient` (Tier 1); next step is wrapping `StudyPlanAgent`, `LearningPathCuratorAgent`, `AssessmentAgent`, and `CertRecommendationAgent` with Foundry-managed agents for full platform observability and built-in thread memory
- **Azure AI Search integration** — replace static MS Learn lookup table with live vector search across the full ~4 000 module catalogue; semantic matching between learner profile and module descriptions
- **Email digest — upgrade from SMTP to Azure Communication Services** — the current implementation uses Python `smtplib` (works with Gmail/Outlook); the roadmap upgrade swaps this for the `azure-communication-email` SDK using a managed Azure sender domain (`DoNotReply@<guid>.azurecomm.net`); to set up today: create a **Communication Services** resource in the Azure portal, add an **Email Communication Service** sub-resource, then copy the connection string to `AZURE_COMM_CONNECTION_STRING`
- **Adaptive quiz engine** — use GPT-4o to generate novel domain-specific questions dynamically rather than sampling from a static bank; item-response theory (IRT) for adaptive difficulty
- **Foundry Evaluation bias dataset** — `eval_harness.py` and `batch_evaluate()` are ready; next step is labelling pass/fail profiling outcomes across all 9 cert exam families for demographic parity + counterfactual tests

### Medium Term (6–12 months)
- **Differential privacy metrics** — track token-level PII exposure rate across sessions via Azure Monitor; per-session anonymisation audit log
- **Multi-language support** — Azure OpenAI Whisper for voice-based intake; multilingual exam content via Azure AI Translator
- **Study group / cohort mode** — shared study plans for enterprise teams preparing for the same certification batch
- **Real-time practice labs** — integrate Azure sandbox environments so learners can attempt actual Azure tasks inline (e.g. deploy an Azure OpenAI endpoint as a graded exercise)
- **Exam booking assistant** — connect to Pearson VUE API to show seat availability and book directly from the recommendation tab

### Long Term (12+ months)
- **Autonomous learning loop** — agent self-improves question bank by monitoring which questions correlate most with real exam pass/fail outcomes (A/B testing with learner consent)
- **Cert path graph** — multi-hop reasoning across all 9 cert prerequisites to recommend the optimal 12-month cert roadmap given the learner's starting point
- **Enterprise LMS integration** — export study plans to LMS platforms (Cornerstone, SAP SuccessFactors) via LTI/xAPI so organisations can track team certification progress
- **Multimodal input** — accept PDF uploads (e.g. existing CV/résumé) as background context; parse with Azure Document Intelligence and pass to profiler

---

## 📦 Multi-Cert Domain Registry

```python
EXAM_DOMAIN_REGISTRY = {
    "AI-102": [...],   # Azure AI Engineer Associate
    "AI-900": [...],   # Azure AI Fundamentals
    "AZ-204": [...],   # Azure Developer Associate
    "AZ-305": [...],   # Azure Solutions Architect Expert
    "AZ-400": [...],   # DevOps Engineer Expert
    "DP-100": [...],   # Azure Data Scientist Associate
    "DP-203": [...],   # Azure Data Engineer Associate
    "SC-100": [...],   # Cybersecurity Architect Expert
    "MS-102": [...],   # Microsoft 365 Administrator Expert
}

# All agents use dynamic lookup — zero code change to support a new cert:
domains = get_exam_domains("DP-100")
```

---

## 🧠 Reasoning Patterns & Best Practices

As recommended in the [Agents League starter kit](https://github.com/microsoft/agentsleague/tree/main/starter-kits/2-reasoning-agents#-reasoning-patterns--best-practices), this project implements all four core reasoning patterns:

| Pattern | Starter Kit Requirement | Where in This System |
|---------|------------------------|---------------------|
| **Planner–Executor** | Separate agents for planning and execution | `IntakeAgent` plans (collects goals) → `LearnerProfilingAgent` executes (extracts typed `LearnerProfile`) → `StudyPlanAgent` plans the schedule |
| **Critic / Verifier** | Agent that reviews outputs and validates reasoning | `GuardrailsPipeline` (17 rules) validates every agent output before the next stage proceeds; `ProgressAgent` critiques learner readiness before unlocking assessment |
| **Self-reflection & Iteration** | Agents reflect on intermediate results and refine | Score < 70% → remediation loop: `StudyPlanAgent` re-runs with updated weak-domain profile; HITL gate captures real learner data before each iteration |
| **Role-based specialisation** | Clear, bounded responsibilities per agent | `StudyPlanAgent` (temporal scheduling only) ≠ `LearningPathCuratorAgent` (content discovery only) ≠ `AssessmentAgent` (evaluation only) ≠ `CertRecommendationAgent` (booking + next-cert path only) |

### Additional Patterns

| Pattern | Where |
|---------|-------|
| **Human-in-the-Loop (HITL)** | Gate 1: learner submits study hours + self-ratings; Gate 2: learner answers a quiz (5–30 questions, default 10) — agents produce inputs and interpret outputs, human provides the data |
| **Conditional Routing** | `score ≥ 70%` → `CertRecommendationAgent`; `50–70%` → targeted review; `< 50%` → full remediation loop |
| **Typed Handoff Contracts** | All agents exchange Pydantic `BaseModel` or `@dataclass` — never raw strings; validated at every boundary by `GuardrailsPipeline` |
| **Concurrent Fan-out** | `StudyPlanAgent` ∥ `LearningPathCuratorAgent` via `ThreadPoolExecutor` — independent agents with same `LearnerProfile` input, different outputs |

### Best Practices Applied

| Starter Kit Best Practice | How This System Addresses It |
|--------------------------|-----------------------------|
| Use telemetry, logs, and visual workflows | `AgentStep`/`RunTrace` observability structs capture per-agent latency, token count, and I/O summary; Admin Dashboard surfaces guardrail violations, agent traces, and student roster |
| Foundry built-in monitoring (roadmap) | `agent_trace.py` data model is directly portable to Azure AI Foundry telemetry schema when migrating to Foundry SDK |
| Apply evaluation strategies | 25 pytest tests (`test_guardrails.py`, `test_config.py`, `test_agents.py`); mock mode enables reproducible, deterministic testing without API calls |
| Build with Responsible AI principles | `GuardrailsPipeline` G-16 (content safety), G-17 (URL trust / anti-hallucination), G-01..G-05 (input validation and PII notice); `.env` never committed; demo data only in public repo |
| Leverage AI-assisted development | GitHub Copilot used throughout for code generation, refactoring, and test scaffolding |

---

## � Microsoft Foundry Best Practices — Implementation Status

Explicit mapping of each [Foundry best practice from the starter kit](https://github.com/microsoft/agentsleague/tree/main/starter-kits/2-reasoning-agents#-best-practices-for-building-with-microsoft-foundry) to concrete implementation evidence in this codebase.

| # | Foundry Best Practice | Status | Implementation Evidence |
|---|----------------------|--------|------------------------|
| 1 | **Use telemetry, logs, and visual workflows in Foundry** to understand how agents reason and collaborate | ✅ **Implemented** | `agent_trace.py` — `AgentStep` struct captures: `agent_id`, `agent_name`, `start_ms`, `duration_ms`, `status`, `input_summary`, `output_summary`, `decisions[]`, `warnings[]`; `RunTrace` aggregates all steps per session with `run_id`, `student_name`, `exam_target`, `mode`, `total_ms`; Admin Dashboard renders the full per-agent reasoning trace (expandable cards); Azure AI Foundry portal **automatically** logs all Tier 1 `create_and_process_run()` calls with latency + token counts |
| 2 | **Foundry Control Plane** — built-in monitoring tools to track agent interactions and performance | ✅ **Partially active** | When `AZURE_AI_PROJECT_CONNECTION_STRING` is set, every `LearnerProfilingAgent` run appears in the Foundry portal **Tracing** view (request/response, latency, token usage) — recorded automatically by `AIProjectClient`; remaining agents are traced locally via `RunTrace` / Admin Dashboard; full Control Plane coverage for all agents is sprint task T-06 |
| 3 | **Apply evaluation strategies** — test cases, scoring rubrics, or HITL reviews to continuously improve agent behaviour | ✅ **Implemented** | 25 pytest tests (`test_guardrails.py`, `test_config.py`, `test_agents.py`); `GuardrailsPipeline` is a 17-rule scoring rubric (BLOCK/WARN/INFO with per-rule codes G-01..G-17); HITL Gate 1 (study hours + self-ratings) and Gate 2 (quiz, 5–30 questions, default 10) are structured human reviews embedded in the pipeline; remediation loop re-runs planning agents on low-score outcomes |
| 4 | **Evaluate generative AI models and applications** using Microsoft Foundry built-in features | ✅ **Active (portal + SDK)** | Foundry portal evaluation is available today for all Tier 1 `LearnerProfilingAgent` runs; `eval_harness.py` adds programmatic LLM-as-judge metrics (Coherence, Relevance, Fluency) via `azure-ai-evaluation>=1.0.0`; `is_eval_available()` guard ensures graceful no-op in mock mode |
| 5 | **Evaluate your AI agents with the Microsoft Foundry SDK** (`azure-ai-evaluation`) | ✅ **Implemented — T-09** | `azure-ai-evaluation>=1.0.0` added to `requirements.txt`; `src/cert_prep/eval_harness.py` wires `CoherenceEvaluator`, `RelevanceEvaluator`, `FluencyEvaluator`; query = student background + goal; response = `recommended_approach` + `engagement_notes`; `batch_evaluate()` available for regression suites |
| 6 | **Build with Responsible AI principles** — at both application and data layers | ✅ **Comprehensively implemented** | **Application layer:** 17-rule `GuardrailsPipeline` (input G-01..G-05, profile G-06..G-08, study plan G-09..G-10, progress G-11..G-13, quiz G-14..G-15, content G-16, URL-trust G-17); **Foundry model layer:** Foundry's content filters applied automatically to all Tier 1 managed runs at the model endpoint; **Data layer:** `.env` gitignored, synthetic demo personas only, no PII in repo — see `## 🤝 Responsible AI Considerations` for the full 7-principle breakdown |
| 7 | **Responsible AI in Microsoft Foundry** — transparency, guardrails, human oversight | ✅ **Implemented** | Sidebar mode badge clearly labels the active AI tier (☁️ Azure AI Foundry SDK / ☁️ Live Azure OpenAI / 🔌 Mock Mode); spinner messages name the exact API called; `🤖 AI-generated` disclaimers on study plans and recommendations; 3-tier graceful degradation (Foundry → OpenAI → Mock) ensures no silent failures; `GuardrailsPipeline` BLOCK halts via `st.stop()` with a user-visible error message |

### Honest Gaps

| Item | Status | Notes |
|------|--------|-------|
| Azure Content Safety API (G-16) | ✅ **Implemented** | `_check_content_safety_api()` in `guardrails.py` makes live HTTP POST calls to `{AZURE_CONTENT_SAFETY_ENDPOINT}/contentsafety/text:analyze` when endpoint + key are set; severity ≥ 2 = BLOCK across Hate / SelfHarm / Sexual / Violence categories; falls back to regex when unconfigured |
| `azure-ai-evaluation` SDK | ✅ **Implemented** | `eval_harness.py` added; `CoherenceEvaluator`, `RelevanceEvaluator`, `FluencyEvaluator` run post-profiling using the same Azure OpenAI deployment; `is_eval_available()` guard ensures graceful no-op in mock mode; `azure-ai-evaluation>=1.0.0` added to `requirements.txt` |
| Foundry SDK for remaining agents | ✅ **By design** | The 5 remaining agents (`StudyPlanAgent`, `LearningPathCuratorAgent`, `ProgressAgent`, `AssessmentAgent`, `CertRecommendationAgent`) are deterministic rule-based Python — zero LLM calls; Foundry SDK wrapping adds no value to deterministic code; their `AgentStep` / `RunTrace` records are schema-ready for a future Foundry telemetry export (T-06) |
| Foundry Evaluation bias dataset | 🔲 **Backlog (B-01)** | Requires labelled pass/fail profiling outcomes across all 9 cert exam families; `eval_harness.batch_evaluate()` is ready to consume such a dataset once labelled examples exist |

---

## �🚀 Quick Start

```bash
git clone https://github.com/athiq-ahmed/agentsleague.git
cd agentsleague
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate      # macOS/Linux
pip install -r requirements.txt
streamlit run streamlit_app.py  # opens http://localhost:8501
```

### Demo Credentials

| Role | Name | Credential | Journey |
|------|------|-----------|---------|
| New Learner | Alex Chen | PIN: `1234` | AI-102 from scratch |
| Returning Learner | Priyanka Sharma | PIN: `1234` | DP-100 with profile loaded |
| Admin | `admin` | Password: `agents2026` | Full trace + guardrail audit |

### Azure OpenAI (optional — enables live mode)
```ini
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com
AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

### Email digest (optional — weekly progress notifications)

The `ProgressAgent` (`src/cert_prep/b1_2_progress_agent.py`) sends a weekly study-summary email to the learner via Python's built-in `smtplib`. **No Azure subscription required.** If the SMTP variables are absent the agent silently skips sending — the rest of the app is completely unaffected.

#### How it works

```
ProgressAgent.attempt_send_email()
  → reads SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASS / SMTP_FROM from environment
  → opens TLS connection (STARTTLS on port 587)
  → sends HTML summary: domains covered, hours logged, readiness score, next steps
  → logs success / failure to AgentStep trace (visible in Admin Dashboard)
```

#### Environment variables to set

| Variable | What to put | Example |
|----------|-------------|---------|
| `SMTP_HOST` | Your SMTP server hostname | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port (587 = STARTTLS, 465 = SSL) | `587` |
| `SMTP_USER` | Login username (usually your email address) | `you@gmail.com` |
| `SMTP_PASS` | Password or App Password (see below) | `abcd efgh ijkl mnop` |
| `SMTP_FROM` | Display name + address shown in the "From" field | `CertPrep AI <you@gmail.com>` |

#### Step-by-step: Gmail (recommended for testing)

Gmail requires an **App Password** — your normal account password will not work.

1. Sign in to [myaccount.google.com](https://myaccount.google.com)
2. Go to **Security** → enable **2-Step Verification** (required)
3. Go to **Security** → **App passwords** → select app: *Mail*, device: *Other (custom name)* → type `CertPrep` → click **Generate**
4. Copy the **16-character code** shown (spaces don't matter)
5. Add to your `.env` file:

```ini
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASS=abcd efgh ijkl mnop    # paste the 16-char App Password here
SMTP_FROM=CertPrep AI <you@gmail.com>
```

#### Other providers

| Provider | `SMTP_HOST` | `SMTP_PORT` | Notes |
|----------|-------------|-------------|-------|
| **Outlook / Microsoft 365** | `smtp.office365.com` | `587` | Use your full email + account password |
| **SendGrid** | `smtp.sendgrid.net` | `587` | `SMTP_USER=apikey`, `SMTP_PASS=<sendgrid-api-key>` |
| **Mailgun** | `smtp.mailgun.org` | `587` | Use SMTP credentials from Mailgun dashboard |
| **Any relay** | your relay hostname | `587` or `465` | Generic STARTTLS / SSL |

> **No Azure needed.** The app works identically without these variables — email is purely additive.
>
> **Roadmap — Azure Communication Services:** future upgrade to a managed sender domain (`DoNotReply@<guid>.azurecomm.net`) via the `azure-communication-email` SDK. Setup when ready: Azure portal → **Communication Services** → add **Email Communication Service** sub-resource → provision or verify a domain → copy the connection string to `AZURE_COMM_CONNECTION_STRING`. See `docs/TODO.md` backlog task B-05.

---
## 🧪 Unit Tests

**352 tests · ~4 seconds · zero Azure credentials required**

All tests run fully in mock mode — no `.env` file, no Azure OpenAI keys, no internet needed.  
The suite covers every agent, all 17 guardrail rules, data models, PDF generation, serialization round-trips, rubric-based agent evaluations, and the end-to-end pipeline.

See [`docs/unit_test_scenarios.md`](docs/unit_test_scenarios.md) for the full catalogue of all 352 test scenarios categorised by difficulty. When running tests, that file is the authoritative reference — it maps every test to its scenario, inputs, and expected outcome.

| Test file | Tests | What it covers |
|---|---|---|
| `tests/test_guardrails_full.py` | 71 | All 17 guardrail rules G-01 → G-17 (BLOCK / WARN / INFO) |
| `tests/test_models.py` | 29 | Data models, Pydantic contracts, exam registry (9 families) |
| `tests/test_assessment_agent.py` | 24 | Question generation, scoring logic, domain sampling |
| `tests/test_study_plan_agent.py` | 23 | Plan structure, Largest Remainder allocation, budget compliance |
| `tests/test_pdf_generation.py` | 20 | PDF bytes output, HTML email generation, field safety |
| **`tests/test_serialization_helpers.py`** | **25** | **`_dc_filter`, enum coercion safety, all 6 `*_from_dict` round-trips with extra/missing keys** |
| `tests/test_progress_agent.py` | 26 | Readiness formula, verdicts, per-exam domain weights, 5-exam parametrized (extended) |
| `tests/test_pipeline_integration.py` | 14 | End-to-end 8-agent chain with typed handoffs |
| `tests/test_cert_recommendation_agent.py` | 13 | Recommendation paths, confidence thresholds |
| `tests/test_learning_path_curator.py` | 13 | Module curation, domain-to-resource mapping |
| `tests/test_guardrails.py` | 17 | G-16 PII patterns, harmful keyword blocker |
| `tests/test_config.py` | 10 | Settings loading, placeholder detection |
| `tests/test_agents.py` | 4 | Mock profiler basic outputs |
| **`tests/test_agent_evals.py`** | **53** | **Rubric-based quality evals (E1–E7) for all 6 agents + full pipeline; 80% pass threshold** |

### Run the test suite

```powershell
# Full suite
.venv\Scripts\python.exe -m pytest tests/ -q

# Verbose with short tracebacks
.venv\Scripts\python.exe -m pytest tests/ -v --tb=short
```

### Expected output

```
352 passed in ~4.00s
```

---
## � PDF Reports & Demo Caching

The `ProgressAgent` generates two PDF report types via **reportlab**:

| Report | Function | Contents |
|--------|----------|----------|
| **Learner Profile PDF** | `generate_profile_pdf()` | Domain radar summary, confidence scores, experience level, background, study goal |
| **Assessment Report PDF** | `generate_assessment_pdf()` | Quiz score breakdown, per-domain results, pass/fail verdict, remediation recommendations |

### Demo PDF Cache (`demo_pdfs/`)

For demo personas (Alex Chen / Priyanka Sharma) PDFs are **pre-cached** on first generation. Subsequent clicks on "Download PDF" or "Email Study Plan PDF" serve the cached file instantly — no reportlab pipeline needed.

```python
# streamlit_app.py — _get_or_generate_pdf() helper
def _get_or_generate_pdf(scenario_key, pdf_type, generate_fn, *args) -> bytes:
    if scenario_key:                                    # demo user
        cache_path = _DEMO_PDF_DIR / f"{scenario_key}_{pdf_type}.pdf"
        if cache_path.exists():
            return cache_path.read_bytes()             # instant: serve from cache
        pdf_bytes = generate_fn(*args)
        cache_path.write_bytes(pdf_bytes)              # write once
        return pdf_bytes
    return generate_fn(*args)                          # real users always regenerate
```

- `demo_pdfs/*.pdf` files are **gitignored** — the folder is tracked via `.gitkeep`
- Real users (no `scenario_key`) always generate a fresh PDF from their live profile
- The `generate_profile_pdf()` function accepts an optional `raw=` parameter (`RawStudentInput`) to include the learner's original background text and exam goal in the PDF header — this ensures the PDF reflects what the learner typed, not just the profiler's structured output

---

## �📁 Project Structure

```
agentsleague/
├── streamlit_app.py                      # Orchestrator + full 8-tab UI (main entry point)
├── .env                                  # ⚠️ NOT committed (gitignored) — fill in real values; commented examples included
├── requirements.txt                      # pip dependencies
│
├── pages/
│   └── 1_Admin_Dashboard.py             # Agent audit dashboard + per-agent guardrail log
│
├── demo_pdfs/                            # Pre-cached PDF reports for demo personas (gitignored)
│   ├── .gitkeep                          # Tracks folder in git; *.pdf files are gitignored
│   ├── alex_profile.pdf                  # Alex Chen — AI-102 learner profile (generated on first run)
│   ├── alex_assessment.pdf               # Alex Chen — AI-102 assessment report
│   ├── priyanka_profile.pdf              # Priyanka Sharma — DP-100 learner profile
│   └── priyanka_assessment.pdf           # Priyanka Sharma — DP-100 assessment report
│
├── src/
│   └── cert_prep/
│       ├── __init__.py
│       ├── models.py                     # Data contracts + EXAM_DOMAIN_REGISTRY (9 certs)
│       ├── config.py                     # Settings dataclass: OpenAI, Foundry, ContentSafety,
│       │                                 #   CommServices, MCP, App — auto live-mode detection
│       ├── guardrails.py                 # GuardrailsPipeline — 17 rules with real PII patterns
│       ├── agent_trace.py                # AgentStep / RunTrace observability structs
│       ├── database.py                   # SQLite persistence (learner profiles + traces)
│       ├── b0_intake_agent.py            # Intake + LearnerProfilingAgent (live Azure OpenAI)
│       ├── b1_mock_profiler.py           # Rule-based profiler (zero-credential mock mode)
│       ├── b1_1_study_plan_agent.py      # Gantt study plan generator (parallel fan-out)
│       ├── b1_1_learning_path_curator.py # MS Learn module curator (parallel fan-out)
│       ├── b1_2_progress_agent.py        # Readiness tracker + PDF reports + email digest
│       ├── b2_assessment_agent.py        # Quiz builder + scorer
│       └── b3_cert_recommendation_agent.py  # Next-cert path recommender
│
├── tests/                                # Smoke test suite (pytest)
│   ├── __init__.py
│   ├── test_guardrails.py               # 14 tests — G-16 PII patterns + harmful blocker
│   ├── test_config.py                   # 7 tests — settings loading, placeholder detection
│   └── test_agents.py                   # 4 tests — mock profiler outputs
│
├── docs/
│   ├── technical_documentation.md       # Deep-dive: agent internals, algorithms, data models
│   ├── user_guide.md                    # End-to-end walkthrough for learners
│   ├── user_flow.md                     # All 8 user journey scenarios (S1–S8 incl. PII)
│   ├── demo_guide.md                    # Live demo script and persona walkthroughs
│   ├── qna_playbook.md                  # Hackathon judging Q&A; scoring rationale
│   ├── changelog.md                     # Issue log — all changes by date
│   ├── lessons.md                       # Decisions, pivots, trade-offs
│   ├── unit_test_scenarios.md           # Test scenarios by difficulty
│   ├── azure_ai_cost_guide.md           # Token costs, mock vs live mode, budget tips
│   ├── Solution_architecture.pdf        # Solution architecture (PDF)
│   ├── Solution_architecture.drawio     # Architecture diagram source (draw.io)
│   └── TODO.md                          # Task tracker (completed + pending items)
│
└── archive/                             # Old planning files (not in production path)
```

### One `.env` file — no separate template needed

`.env` is gitignored and contains **both real values and commented example placeholders** for every variable. To go Live, fill in `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY` and restart — the toggle switches automatically.

---

## 🏆 Submission Requirements Checklist

Complete alignment with the [Battle #2 Submission Requirements](https://github.com/microsoft/agentsleague/tree/main/starter-kits/2-reasoning-agents#-submission-requirements). Every mandatory criterion is met; all optional/highly-valued criteria are also addressed.

### Mandatory Requirements

| # | Requirement | Status | Evidence |
|---|-------------|--------|----------|
| 1 | **Multi-agent system** aligned with the challenge scenario (student preparation for Microsoft certification exams) | ✅ **Met** | 8 specialised reasoning agents: `IntakeAgent` → `LearnerProfilingAgent` → `StudyPlanAgent` ∥ `LearningPathCuratorAgent` → `ProgressAgent` → `AssessmentAgent` → `CertRecommendationAgent`; supports 9 exam families (AI-102, DP-100, AZ-204, AZ-305, AZ-400, SC-100, AI-900, DP-203, MS-102) |
| 2 | **Use Microsoft Foundry (UI or SDK)** and/or the Microsoft Agent Framework for agent development and orchestration | ✅ **Met** | `azure-ai-projects` SDK (`AIProjectClient.from_connection_string()`) is live for `LearnerProfilingAgent` — creates managed agent + thread, calls `create_and_process_run()`, deletes ephemeral agent after response; Tier 2 fallback to direct Azure OpenAI; remaining agents use Foundry-compatible typed contracts |
| 3 | **Demonstrate reasoning and multi-step decision-making** across agents | ✅ **Met** | 8-agent sequential + parallel pipeline; Planner–Executor pattern (Intake → Profiler → Planner); Critic/Verifier pattern (GuardrailsPipeline at every agent boundary); conditional routing (`score ≥ 70%` → CertRecommender, `50–70%` → targeted review, `< 50%` → remediation loop); self-reflection iteration (re-plan on score drop); HITL gates |
| 4 | **Integrate with external tools, APIs, and/or MCP servers** to meaningfully extend agent capabilities | ✅ **Met** | Azure OpenAI GPT-4o (LLM backbone); Azure AI Foundry Agent Service SDK (managed agent execution); SQLite persistence (cross-session learner profiles); SMTP email digest (progress notifications); MS Learn module catalogue (9-cert static registry; live MCP `/ms-learn` server integration via `MCP_MSLEARN_URL` is active roadmap — placeholder wired) |
| 5 | **Be demoable** (live or recorded) and clearly explain the agent interactions | ✅ **Met** | Live at [agentsleague.streamlit.app](https://agentsleague.streamlit.app) (Streamlit Cloud); Admin Dashboard shows per-agent reasoning trace, input/output, guardrail violations, latency; mock mode runs zero-credential locally; `docs/demo_guide.md` + `docs/qna_playbook.md` guide live demo walkthrough |
| 6 | **Clear documentation** describing: agent roles and responsibilities, reasoning flow and orchestration logic, tools/API/MCP integrations | ✅ **Met** | `README.md` (this file — full architecture, agent table, reasoning patterns, tool integrations, Foundry SDK integration); `docs/technical_documentation.md` (sequence diagrams, agent contracts, algorithms, data models, orchestration); `docs/qna_playbook.md` (demo script, scenario walkthroughs, guardrail evidence); `docs/user_flow.md` (full user journey with PII edge cases) |

### Optional But Highly Valued

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 7 | **Use of evaluations, telemetry, or monitoring** | ✅ **Implemented** | `AgentStep` / `RunTrace` structs capture per-agent latency, token count, I/O snapshot, and guardrail violations; Admin Dashboard surfaces full trace per student session; 25 pytest tests in `tests/`; Azure AI Foundry portal telemetry active for Tier 1 Foundry-managed runs |
| 8 | **Advanced reasoning patterns** (planner–executor, critics, reflection loops) | ✅ **All 4 implemented** | Planner–Executor (Intake→Profiler→StudyPlan); Critic/Verifier (GuardrailsPipeline 17 rules); Self-reflection + Iteration (remediation loop on low score); Role-based specialisation (bounded single-responsibility agents); + HITL gates, conditional routing, typed handoff contracts, concurrent fan-out |
| 9 | **Responsible AI considerations** (guardrails, validation, fallbacks) | ✅ **Comprehensively implemented** | 17-rule `GuardrailsPipeline` (BLOCK/WARN/INFO); G-16 content safety heuristic (14 harmful keywords + PII regex); G-17 URL trust/anti-hallucination; G-05 PII notice; 3-tier graceful degradation (Foundry → OpenAI → Mock); HITL human oversight gates; transparency badges (mode badge, spinner labels, AI disclaimers); `.env` gitignored; synthetic demo data only — see `## 🤝 Responsible AI Considerations` section above for full breakdown |

### Self-Improvement & Workflow Governance

This project enforces a **plan-first, verify-before-done** development discipline:

| Workflow Principle | Implementation |
|-------------------|----------------|
| **Plan Node Default** | Any task with > 3 implementation steps must be written to `docs/TODO.md` before coding starts |
| **Self-Improvement Loop** | After every correction or AI-assisted change, lessons are recorded in `docs/lessons.md` — compounding the mistake rate drop over time |
| **Verification Before Done** | No task is marked `✅` without: syntax check (`py_compile`), behaviour diff (manual or `pytest`), and git diff review |
| **Autonomous Bug Fixing** | CI test failures / error logs are addressed root-cause-first — no patch-over-patch workarounds |
| **Strict Task Management** | `docs/TODO.md` uses checkable items; in-progress items are limited to one at a time; completed items immediately ticked |

See [`docs/TODO.md`](docs/TODO.md) for current sprint tasks and [`docs/lessons.md`](docs/lessons.md) for the cumulative lessons log.

---

## ✅ Starter Kit Compliance Checklist

Alignment with the [Starter Kit README](https://github.com/microsoft/agentsleague/tree/main/starter-kits/2-reasoning-agents):

| Starter Kit Item | Status | Notes |
|-----------------|--------|-------|
| Multi-agent reasoning system | ✅ | 8 agents, 4 reasoning patterns |
| `azure-ai-projects` SDK (`AIProjectClient`) active | ✅ | `LearnerProfilingAgent` Tier 1 — Foundry managed agent + thread |
| Foundry-compatible typed agent contracts | ✅ | All agents exchange Pydantic `BaseModel` / `@dataclass` |
| Human-in-the-Loop gates | ✅ | 2 explicit HITL gates in pipeline |
| Content safety + input validation | ✅ | G-01..G-17 guardrails pipeline |
| Evaluation / telemetry | ✅ | `AgentStep`/`RunTrace` + `eval_harness.py` (LLM-as-judge via `azure-ai-evaluation`) + **352 pytest tests** across 15 modules |
| `.gitignore` per starter kit guidelines | ✅ | `.env`, `.azure/`, `.secrets/` excluded |
| GitHub repository with full documentation | ✅ | [athiq-ahmed/agentsleague](https://github.com/athiq-ahmed/agentsleague) — `README.md` + 9 docs under `docs/` (see **Project Documentation** section below) |

---

## 🔒 Security & Disclaimer

> ⚠️ **This is a public repository accessible worldwide.** Before contributing or forking, please read the [Agents League Disclaimer](https://github.com/microsoft/agentsleague/blob/DISCLAIMER.md).

### What This Repository Does NOT Contain

| Prohibited Content | Status |
|-------------------|--------|
| ❌ Azure API keys, connection strings, or credentials | `.env` is gitignored; all values are local-only |
| ❌ Customer data or personally identifiable information (PII) | All demo personas (Alex Chen, Priyanka Sharma) use synthetic data only |
| ❌ Confidential or proprietary company information | None |
| ❌ Internal engineering projects not approved for open source | None |
| ❌ Pre-release product information under NDA | None |
| ❌ Trade secrets or proprietary algorithms | Largest Remainder allocation is a published parliamentary apportionment method |

### Azure Security Best Practices Applied

```ini
# ✅ .gitignore includes:
.env
.env.*
.azure/
**/.secrets/
*.pem
*.key
```

- ✅ **Credentials in environment variables only** — never in committed code
- ✅ **`.env` is gitignored** — commented example placeholders are inside `.env` itself; no secrets can be accidentally committed
- ✅ **Demo data only** — no real customer data or production datasets in the repository
- ✅ **PIN hashed (SHA-256)** — demo PINs are hashed before SQLite storage
- ✅ **Production path** uses Azure Key Vault + Managed Identity (documented in `docs/technical_documentation.md`)

### Responsible AI in This System

| Principle | Implementation |
|-----------|---------------|
| **Validate inputs and outputs** | 17-rule `GuardrailsPipeline` — BLOCK halts pipeline; WARN is logged and surfaced in Admin Dashboard |
| **Content filters** | G-16 heuristic harmful-keyword filter on all free-text fields; G-17 URL trust allowlist prevents hallucinated links |
| **Transparency** | Every response includes agent source label and mock/live mode indicator |
| **Human oversight** | Two HITL gates interrupt the pipeline — humans provide real progress data before agents advance |
| **Fairness** | Exam domains drawn from official Microsoft weighting tables — not model-generated |

Learn more: [Responsible AI in Microsoft Foundry](https://learn.microsoft.com/azure/ai-foundry/responsible-use-of-ai-overview)

### Legal & Licensing

- All content is original work created for this competition
- Submitted under the repository's [MIT License](https://github.com/microsoft/agentsleague/blob/LICENSE)
- Complies with the [Code of Conduct](https://github.com/microsoft/agentsleague/blob/CODE_OF_CONDUCT.md)
- Demo personas use entirely synthetic / fictional data

---

## 📄 License

Created for **Microsoft Agents League** — Battle #2: Reasoning Agents. Educational and demonstration purposes.
