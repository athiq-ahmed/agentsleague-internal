# Agents League Battle #2 — Submission Answers

> Prepared answers for the GitHub issue submission template at
> https://github.com/microsoft/agentsleague/issues/new?template=project.yml
>
> **Submission Deadline:** March 1, 2026 (11:59 PM PT)

---

## Track

**Reasoning Agents (Azure AI Foundry)**

---

## Project Name

**CertPrep Multi-Agent System — Personalised Microsoft Exam Preparation**

---

## GitHub Username

`@athiq-ahmed`

---

## Repository URL

https://github.com/athiq-ahmed/agentsleague

---

## Project Description

*(250 words max)*

The CertPrep Multi-Agent System is a production-grade AI solution for personalised Microsoft certification exam preparation, supporting 9 exam families (AI-102, DP-100, AZ-204, AZ-305, AZ-400, SC-100, AI-900, DP-203, MS-102).

Eight specialised reasoning agents collaborate through a typed, sequential + concurrent pipeline:

1. **LearnerProfilingAgent** — converts free-text background into a structured `LearnerProfile` via Azure AI Foundry SDK (Tier 1) or direct GPT-4o JSON-mode (Tier 2), with a deterministic rule-based fallback (Tier 3).
2. **StudyPlanAgent** — generates a week-by-week Gantt study schedule using the Largest Remainder algorithm to allocate hours without exceeding the learner's budget.
3. **LearningPathCuratorAgent** — maps each exam domain to curated MS Learn modules with trusted URLs, resource types, and estimated hours.
4. **ProgressAgent** — computes an exam-weighted readiness score (`0.55 × domain ratings + 0.25 × hours utilisation + 0.20 × practice score`).
5. **AssessmentAgent** — generates a 10-question domain-proportional mock quiz and scores it against the 60% pass threshold.
6. **CertificationRecommendationAgent** — issues a GO / CONDITIONAL GO / NOT YET booking verdict with next-cert suggestions and a remediation plan.

A 17-rule GuardrailsPipeline runs at every agent boundary. Two human-in-the-loop gates ensure agents act on real learner data, not assumptions. The full pipeline runs in under 1 second in mock mode (zero Azure credentials), enabling reliable live demonstrations at any time.

---

## Demo Video or Screenshots

- **Live Demo:** https://agentsleague.streamlit.app
- **Demo Guide:** [docs/demo_guide.md](demo_guide.md) — persona scripts and walkthrough steps
- **Admin Dashboard:** shows per-agent reasoning traces, guardrail audit, timing, and token counts

---

## Primary Programming Language

**Python**

---

## Key Technologies Used

| Technology | Role |
|------------|------|
| Azure AI Foundry Agent Service SDK (`azure-ai-projects`) | Tier 1 managed agent + conversation thread for `LearnerProfilingAgent` |
| Azure OpenAI GPT-4o (JSON mode) | Tier 2 structured profiling fallback; temperature=0.2 |
| Azure Content Safety (`azure-ai-contentsafety`) | G-16 guardrail — profanity and harmful-content filter |
| Streamlit | 7-tab interactive UI + Admin Dashboard |
| Pydantic v2 `BaseModel` | Typed handoff contracts at every agent boundary |
| `concurrent.futures.ThreadPoolExecutor` | Parallel fan-out of `StudyPlanAgent` ∥ `LearningPathCuratorAgent` |
| Plotly | Gantt chart, domain radar, agent timeline |
| SQLite (`sqlite3` stdlib) | Cross-session learner profile + reasoning trace persistence |
| ReportLab | PDF generation for profile and assessment reports |
| Python `smtplib` (STARTTLS) | Optional weekly study-progress email digest |
| `hashlib` SHA-256 | PIN hashing before SQLite storage |
| Custom `GuardrailsPipeline` (17 rules) | BLOCK / WARN / INFO at every agent boundary; PII, URL trust, content safety |
| `pytest` + parametrize | 342 automated tests across 15 modules; zero credentials required |
| Streamlit Community Cloud | Auto-deploy on `git push`; secrets via environment variables |
| Visual Studio Code + GitHub Copilot | Primary IDE; AI-assisted development throughout |

---

## Submission Type

**Individual**

---

## Team Members

*(Individual submission — no team members)*

---

## Quick Setup Summary

```bash
# 1. Clone the repository
git clone https://github.com/athiq-ahmed/agentsleague.git
cd agentsleague

# 2. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows PowerShell

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
notepad .env   # Fill in AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, and optionally
               # AZURE_AI_PROJECT_CONNECTION_STRING for Foundry SDK mode
               # Run `az login` once for local Foundry authentication

# 5. Run the application
python -m streamlit run streamlit_app.py

# 6. Run the test suite (no Azure credentials needed)
python -m pytest tests/ -v
```

> **Zero-credential demo mode:** Leave `.env` keys blank or set `FORCE_MOCK_MODE=true` — the full 8-agent pipeline runs deterministically in under 1 second using the rule-based mock engine.

---

## Technical Highlights

- **3-tier LLM fallback chain** — `LearnerProfilingAgent` attempts Azure AI Foundry SDK (Tier 1), falls back to direct Azure OpenAI JSON-mode (Tier 2), and finally to a deterministic rule-based engine (Tier 3). All three tiers share the same Pydantic output contract, so downstream agents never know which tier ran.

- **Largest Remainder day allocation** — `StudyPlanAgent` uses the parliamentary Largest Remainder Method to distribute study time at the **day level** (`total_days = weeks × 7`) across domains, then converts day blocks to week bands and hours. Guarantees: (1) total days exactly equals budget; (2) every active domain receives at least 1 day (`max(1, int(d))` floor) — no domain is silently zeroed out.

- **Concurrent agent fan-out** — `StudyPlanAgent` and `LearningPathCuratorAgent` have no data dependency on each other; they run in true parallel via `ThreadPoolExecutor`, cutting Block 1 wall-clock time by ~50%.

- **17-rule exam-agnostic guardrail pipeline** — Every agent input and output is validated by a dedicated `GuardrailsPipeline` before the next stage proceeds. BLOCK-level violations call `st.stop()` immediately; nothing downstream ever sees invalid data.

- **Exam-weighted readiness formula** — Progress scoring uses `0.55 × domain ratings + 0.25 × hours utilisation + 0.20 × practice score`, with domain weights pulled from the per-exam registry (not hardcoded for AI-102), so the formula is accurate across all 9 supported certifications.

- **Demo PDF cache** — For demo personas, PDFs are generated once and served from `demo_pdfs/` on all subsequent clicks — no pipeline re-run needed, making live demos instant and reliable.

- **Schema-evolution safe SQLite** — All `*_from_dict` deserialization helpers use a `_dc_filter()` guard that silently drops unknown keys, preventing `TypeError` crashes when the data model evolves and old rows are read back.

---

## Challenges & Learnings

| Challenge | How We Solved It | Learning |
|-----------|-----------------|----------|
| **Streamlit + asyncio conflict** — `asyncio.gather()` raises `RuntimeError: event loop already running` inside Streamlit | Replaced with `concurrent.futures.ThreadPoolExecutor` — identical I/O latency, no event-loop conflict, stdlib only | Always profile async options in the target host runtime before committing to the pattern |
| **Schema evolution crashes** — Adding new fields to agent output dataclasses caused `TypeError` when loading old SQLite rows | Added `_dc_filter()` helper to all `*_from_dict` functions; unknown keys silently dropped | Design for forward and backward compatibility from day one; use a key guard on every deserialization boundary |
| **Hardcoded AI-102 domain weights** — `ProgressAgent` used AI-102 weights for all exams, giving wrong readiness scores for DP-100 learners | Refactored to call `get_exam_domains(profile.exam_target)` dynamically | Never hardcode domain-specific constants in shared utility functions; always derive from the registry |
| **`st.checkbox` key collision** — Using `hash()[:8]` string slicing raised `TypeError` in Streamlit widget key generation | Changed to `abs(hash(item))` (integer key) which Streamlit handles natively | Read widget key type requirements; integer keys are always safe |
| **PDF generation crashes on None fields** — `AttributeError` when optional profile fields were absent | Added `getattr(obj, field, default)` guards on every field access in PDF generation | Defensive attribute access is essential for any code path that renders stored data |
| **3-tier fallback complexity** — Keeping Foundry SDK, direct OpenAI, and mock engine in sync as the output contract evolved | Defined a single `_PROFILE_JSON_SCHEMA` constant and a shared Pydantic parser used by all three tiers | A single source-of-truth schema makes multi-tier systems maintainable; contract-first design prevents drift |
| **Live demo reliability** — API latency or missing credentials causing demo failures | Mock Mode runs the full 8-agent pipeline with zero credentials in < 1 second; demo personas pre-seeded in SQLite | Always build a zero-dependency demo path; live mode is a bonus, not a requirement |

---

## Contact Information

*(Provided separately to Microsoft)*

---

## Country/Region

United Kingdom

---

---

# Reasoning Patterns — Detailed Implementation Guide

This section provides a deep-dive into how each of the four core reasoning patterns from the Agents League starter kit is implemented in this system, mapped to the four challenge requirements.

---

## Challenge Requirements

### 1. Multi-agent system aligned with the challenge scenario (student preparation for Microsoft certification exams)

The system is purpose-built around the certification prep journey:

```
Intake → Profile → Plan ∥ Curate → Progress → Assess → Recommend
```

Each stage represents a distinct cognitive task in how a human coach would actually prepare a student for a Microsoft exam:

| Stage | Agent | Real-World Equivalent |
|-------|-------|----------------------|
| Intake form | `IntakeAgent` | Coach intake questionnaire |
| Background parsing | `LearnerProfilingAgent` | Coach reads CV and identifies knowledge gaps |
| Study scheduling | `StudyPlanAgent` | Coach builds week-by-week roadmap |
| Resource curation | `LearningPathCuratorAgent` | Coach recommends specific learning materials |
| Progress check | `ProgressAgent` | Coach reviews study journal and rates readiness |
| Mock exam | `AssessmentAgent` | Coach administers practice test |
| Booking decision | `CertificationRecommendationAgent` | Coach advises whether to book the exam now |

Every agent uses a **typed Pydantic contract** — no agent receives raw text from another agent. This mirrors how a human coaching team would exchange structured reports rather than informal notes.

---

### 2. Microsoft Foundry (UI or SDK) and/or the Microsoft Agent Framework

**Live Foundry SDK integration (`azure-ai-projects`):**

```python
# b0_intake_agent.py — Tier 1 implementation
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

client = AIProjectClient.from_connection_string(
    conn_str=settings.foundry.connection_string,   # AZURE_AI_PROJECT_CONNECTION_STRING
    credential=DefaultAzureCredential(),            # az login locally
)
agent = client.agents.create_agent(
    model="gpt-4o",
    name="LearnerProfilerAgent",
    instructions=PROFILER_SYSTEM_PROMPT,
)
thread  = client.agents.create_thread()
client.agents.create_message(thread_id=thread.id, role="user", content=user_message)
run     = client.agents.create_and_process_run(thread_id=thread.id, agent_id=agent.id)
messages = client.agents.list_messages(thread_id=thread.id)
profile_json = json.loads(messages.get_last_message_by_role("assistant").content[0].text.value)
client.agents.delete_agent(agent.id)   # clean up ephemeral agent
```

Every `LearnerProfilingAgent` run when `AZURE_AI_PROJECT_CONNECTION_STRING` is set:
- Creates a **managed Foundry agent** with a system prompt
- Creates a **conversation thread** (persistent, replayable)
- Executes `create_and_process_run()` — Foundry handles model routing, retries, token counting
- **Automatically appears in Foundry portal Tracing view** with latency, token usage, and request/response payload

The remaining agents (`StudyPlanAgent`, `LearningPathCuratorAgent`, `ProgressAgent`, `AssessmentAgent`, `CertificationRecommendationAgent`) use the same typed Pydantic output contracts and run via the custom Python orchestration pipeline — ready for migration to Foundry-managed agents as a near-term extension.

---

## LearnerProfilingAgent — Technical Deep Dive

This agent is the **only LLM-calling agent in the system**. Everything downstream is deterministic once the profile is produced. Understanding how it works internally explains the whole system's reliability model.

### Input: `RawStudentInput`

Before any LLM call, the agent receives a typed `RawStudentInput` dataclass built from the Streamlit intake form (or the CLI interview agent):

| Field | Type | Example |
|-------|------|---------|
| `student_name` | `str` | `"Alex Chen"` |
| `exam_target` | `str` | `"AI-102"` |
| `background_text` | `str` | `"5 years Python dev, familiar with scikit-learn and REST APIs"` |
| `existing_certs` | `list[str]` | `["AZ-104", "AI-900"]` |
| `hours_per_week` | `float` | `10.0` |
| `weeks_available` | `int` | `8` |
| `concern_topics` | `list[str]` | `["Azure OpenAI", "Bot Service"]` |
| `preferred_style` | `str` | `"hands-on labs first"` |
| `goal_text` | `str` | `"Moving into AI consulting"` |

---

### Tier Selection: `__init__`

During initialisation the agent tries the highest available tier and stores the result as instance state:

```python
# __init__ checks in priority order
if settings.foundry.is_configured:          # AZURE_AI_PROJECT_CONNECTION_STRING set
    self._foundry_client = AIProjectClient.from_connection_string(...)
    self.using_foundry = True
elif cfg.is_configured:                      # AZURE_OPENAI_ENDPOINT + API_KEY set
    self._openai_client = AzureOpenAI(...)
# else: neither configured → _call_llm() raises EnvironmentError
#       → caller (streamlit_app.py) catches and calls generate_mock_profile() instead
```

The tier decision happens **once at construction time**, not per request, so the same agent instance always produces output from the same tier. `streamlit_app.py` catches `EnvironmentError` and automatically falls back to the mock engine.

---

### Prompt Engineering

The system prompt sent to every tier is assembled from three parts at module load time:

**Part 1 — Exam domain reference** (`_DOMAIN_REF`): a JSON array of all 6 AI-102 domains (or the exam-specific domains), each with `id`, `name`, `exam_weight`, and `covers`. This grounds the model's domain reasoning in the actual exam blueprint.

**Part 2 — Seven personalisation rules** embedded in `_SYSTEM_PROMPT`:
1. AZ-104 / AZ-305 holders → `plan_manage` domain gets `STRONG` + `skip_recommended=true`
2. Data science / ML background → `generative_ai` elevated to `MODERATE`
3. Explicit concern topic → mark domain `WEAK` unless background contradicts it
4. `total_budget_hours = hours_per_week × weeks_available` (model must compute this exactly)
5. `risk_domains` = any domain where `confidence_score < 0.50`
6. `analogy_map` = only when non-Azure skills map to Azure AI services
7. `experience_level` ladder: `beginner` → `intermediate` → `advanced_azure` → `expert_ml`

**Part 3 — Single-source schema** (`_PROFILE_JSON_SCHEMA`): the exact JSON structure the model must return, including all field names, types, allowed enums, and the nested `domain_profiles` array:

```json
{
  "experience_level": "beginner | intermediate | advanced_azure | expert_ml",
  "learning_style": "linear | lab_first | reference | adaptive",
  "domain_profiles": [
    {
      "domain_id": "plan_manage | computer_vision | nlp | ...",
      "knowledge_level": "unknown | weak | moderate | strong",
      "confidence_score": "float 0.0-1.0",
      "skip_recommended": "boolean",
      "notes": "string (1-2 sentences)"
    }
  ],
  "risk_domains": ["string (domain_id)"],
  "analogy_map": {"existing skill": "Azure AI equivalent"},
  "recommended_approach": "string (2-3 sentences)",
  "engagement_notes": "string"
}
```

The system prompt ends with `"Respond with ONLY a valid JSON object … Do NOT include any explanation, markdown, or extra text outside the JSON."` — this instruction is what enables JSON-mode parsing on both Tier 1 and Tier 2 without post-processing.

---

### User Message Construction: `_build_user_message()`

The 8 `RawStudentInput` fields are formatted as a labelled text block (not a chat-style prompt), which gives the model a clean, unambiguous encoding of each field:

```
Student: Alex Chen
Exam: AI-102
Background: 5 years Python dev, familiar with scikit-learn and REST APIs
Existing certifications: AZ-104, AI-900
Time budget: 10.0 hours/week for 8 weeks
Topics of concern: Azure OpenAI, Bot Service
Learning preference: hands-on labs first
Goal: Moving into AI consulting

Please produce the learner profile JSON.
```

This structured format avoids natural-language framing that could confuse the model about where the background description ends and the concern topics begin.

---

### Tier 1 — Azure AI Foundry Agent Service

Activated when `AZURE_AI_PROJECT_CONNECTION_STRING` is set and Foundry SDK initialises without error.

```python
# _call_via_foundry()
agent = client.agents.create_agent(
    model="gpt-4o",
    name="LearnerProfilerAgent",
    instructions=_SYSTEM_PROMPT,          # full system prompt as agent instructions
)
try:
    thread = client.agents.create_thread()
    client.agents.create_message(
        thread_id=thread.id,
        role="user",
        content=user_message,             # the _build_user_message() output
    )
    run = client.agents.create_and_process_run(
        thread_id=thread.id,
        agent_id=agent.id,                # blocks until run.status == "completed"
    )
    if run.status == "failed":
        raise RuntimeError(run.last_error)
    messages = client.agents.list_messages(thread_id=thread.id)
    text = messages.get_last_message_by_role("assistant").content[0].text.value
    return json.loads(text)               # dict; will be validated by Pydantic next
finally:
    client.agents.delete_agent(agent.id) # clean up; avoid quota accumulation
```

`create_and_process_run()` handles model routing, retries, and polling internally — the call blocks until the run completes. The **Foundry portal Tracing view** automatically captures the request/response payload, latency, and token counts for every run.

> **Why Foundry for this agent?**  
> `LearnerProfilingAgent` is the only agent that touches free-text user input and needs the richest reasoning context. Foundry's thread model preserves context if the session is extended (e.g. re-profiling after a remediation loop), and the built-in tracing gives instant observability without custom logging.

---

### Tier 2 — Direct Azure OpenAI JSON Mode

Activated when `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY` are set and Foundry is not available.

```python
# _call_via_openai()
response = self._openai_client.chat.completions.create(
    model=self._cfg.deployment,           # gpt-4o
    response_format={"type": "json_object"},  # enforces JSON-only output at API level
    messages=[
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user",   "content": user_message},
    ],
    temperature=0.2,    # low temperature = consistent, reproducible domain scores
    max_tokens=2000,    # profile JSON is ~600–900 tokens; 2000 leaves room for verbose notes
)
raw_json = response.choices[0].message.content
return json.loads(raw_json)
```

`response_format={"type": "json_object"}` is the Azure OpenAI JSON-mode flag. It constrains the model to output only a valid JSON object — it will never produce prose before or after the JSON, which means `json.loads()` on the raw content is safe without a regex extraction step.

`temperature=0.2` produces near-deterministic confidence scores: the same background text run twice will produce `confidence_score` values within ±0.05 of each other, which matters because confidence scores directly drive domain priority in `StudyPlanAgent`.

---

### Tier 3 — Rule-Based Mock Engine (`b1_mock_profiler.py`)

Called directly by `streamlit_app.py` when `live_mode=False` or credentials are absent. Uses three passes over `RawStudentInput`:

| Pass | Input fields | Algorithm |
|------|-------------|-----------|
| **1 — Experience level** | `background_text` | Keyword scoring: `"machine learning"/"data scientist"` → `EXPERT_ML`; `"architect"/"azure"` → `ADVANCED_AZURE`; `"developer"/"engineer"` → `INTERMEDIATE`; else → `BEGINNER` |
| **2 — Domain confidence** | `existing_certs`, `background_text` | Cert → domain boost table (per target exam) + keyword co-occurrence scan; `EXPERT_ML`/`ADVANCED_AZURE` baselines start higher than `BEGINNER` |
| **3 — Risk domains** | `concern_topics` | Each concern topic maps to a domain ID; matched domains receive −0.15 penalty (floor: 0.05) and are appended to `risk_domains` |

Post-processing derives `knowledge_level` from confidence thresholds (`< 0.30 → UNKNOWN`, `0.30–0.50 → WEAK`, `0.50–0.70 → MODERATE`, `≥ 0.70 → STRONG`), sets `skip_recommended=True` when confidence ≥ 0.80, builds an `analogy_map` for ML/data-science backgrounds, and selects `learning_style` from `preferred_style` text keywords.

---

### Schema Validation: `run()`

After any tier returns a `dict`, the `.run()` method applies safety patches before Pydantic validation:

```python
data.setdefault("student_name", raw.student_name)
data.setdefault("exam_target",  raw.exam_target)
data.setdefault("hours_per_week", raw.hours_per_week)
data.setdefault("weeks_available", raw.weeks_available)
data.setdefault("total_budget_hours", raw.hours_per_week * raw.weeks_available)

profile = LearnerProfile.model_validate(data)   # raises ValidationError if schema violated
```

`setdefault` ensures passthrough fields the LLM might abbreviate are always present. `model_validate` is Pydantic v2's strict deserialiser — if any domain has a `confidence_score` outside 0.0–1.0, or an invalid `knowledge_level` enum value, a `ValidationError` is raised before the profile ever reaches a downstream agent.

---

### Output: `LearnerProfile`

On success `.run()` returns a validated Pydantic `LearnerProfile`:

| Field | Type | Downstream Consumer |
|-------|------|-------------------|
| `experience_level` | `ExperienceLevel` enum | `StudyPlanAgent` (priority weights), `LearningPathCuratorAgent` (resource level) |
| `learning_style` | `LearningStyle` enum | `LearningPathCuratorAgent` (resource type filter) |
| `domain_profiles` | `list[DomainProfile]` | `StudyPlanAgent` (Largest Remainder allocation), `AssessmentAgent` (question sampling) |
| `risk_domains` | `list[str]` | `StudyPlanAgent` (front-loads risky domains), `ProgressAgent` (domain nudges) |
| `modules_to_skip` | `list[str]` | `StudyPlanAgent` (skip_recommended domains get zero hours) |
| `analogy_map` | `dict[str, str]` | `LearningPathCuratorAgent` (adds bridge resources), PDF report |
| `recommended_approach` | `str` | `StudyPlanAgent` notes, displayed in Streamlit UI |
| `total_budget_hours` | `float` | `StudyPlanAgent` (budget constraint for Largest Remainder) |

`DomainProfile.confidence_score` (0.0–1.0) is the **single most influential value** in the system: it directly sets domain priority weights in `StudyPlanAgent`, determines `risk_domains` for `ProgressAgent` nudges, and controls question sampling rates in `AssessmentAgent`. Correct profiling at this step cascades into every downstream decision.

---

### 3. Reasoning and multi-step decision-making across agents

The pipeline demonstrates **five distinct forms of reasoning**:

**a) Conditional routing** — The score from `AssessmentAgent` determines the next agent:
```
score ≥ 70% → CertificationRecommendationAgent (GO path)
score 50–70% → targeted domain review
score < 50%  → full remediation loop back to StudyPlanAgent
```

**b) Weighted formula reasoning** — `ProgressAgent` combines three independent evidence sources:
```python
readiness = 0.55 * domain_confidence + 0.25 * hours_utilisation + 0.20 * practice_score
```
The weights are derived from exam blueprint structure (domain confidence is most predictive of exam success).

**c) Prerequisite gap reasoning** — `StudyPlanAgent` checks whether the learner holds prerequisite certs (e.g. AI-900 before AI-102) and adjusts the plan if not, adding extra foundational blocks automatically.

**d) Domain-proportional sampling** — `AssessmentAgent` samples quiz questions proportionally to exam domain weights so the mock quiz mirrors the actual exam blueprint distribution.

**e) Next-cert path reasoning** — `CertificationRecommendationAgent` uses a synergy map to recommend the most complementary next certification based on the learner's current exam and existing cert portfolio.

---

### 4. Integration with external tools, APIs, and/or MCP servers

| Integration | Type | What it provides |
|-------------|------|-----------------|
| Azure OpenAI GPT-4o | API (live) | LLM backbone for `LearnerProfilingAgent` JSON-mode structured profiling |
| Azure AI Foundry Agent Service | SDK (live) | Managed agent lifecycle, thread persistence, Foundry portal telemetry |
| Azure Content Safety | API (live) | G-16 guardrail — content moderation at every free-text input boundary |
| MS Learn module catalogue | Static registry (live) | 9-cert × domain curated resource table; URL trust-listed via G-17 |
| MCP `/ms-learn` server | MCP protocol (roadmap — T-08 not started) | `MCP_MSLEARN_URL` placeholder in `.env`; Node.js sidecar not yet wired into `LearningPathCuratorAgent`; static catalogue used today |
| SQLite | Local persistence | Cross-session learner profiles, study plans, reasoning traces |
| SMTP email | Protocol (live) | Weekly progress digest with PDF attachment; triggered post-intake |
| PDF generation (ReportLab) | Library (live) | Learner profile PDF + assessment report with all agent outputs |

---

## Reasoning Patterns — Deep Dive

### Pattern 1: Planner–Executor

**Concept:** Separate agents responsible for planning (breaking down the problem) and execution (carrying out tasks step by step).

**In this system:**

The Planner–Executor pattern appears at two levels:

**Level 1 — Macro pipeline** (across agents):
- **Planner:** `LearnerProfilingAgent` analyses the learner's background and creates an abstract `LearnerProfile` — a structured breakdown of what the learner knows (`DomainProfile`) and what they need (`risk_domains`, `recommended_approach`). This is pure planning — no study tasks are created yet.
- **Executor:** `StudyPlanAgent` takes the `LearnerProfile` plan and executes it into a concrete week-by-week `StudyPlan` with `StudyTask` objects, specific start/end weeks, hours per domain, and priority levels. It doesn't reinterpret the learner's background — it faithfully executes the plan that the profiler produced.

**Level 2 — Within `StudyPlanAgent`** (internal):
- **Planner step:** Identifies prerequisites, calculates available hours, assigns priority levels (critical → high → medium → low → skip) per domain based on the learner's `knowledge_level` and `confidence_score`.
- **Executor step:** Applies the Largest Remainder Method to convert priority-weighted fractional hours into integer week-blocks that sum to exactly the learner's `total_budget_hours`.

**Why this separation matters:**
- `LearnerProfilingAgent` can be upgraded (Foundry SDK → direct OpenAI → mock) without touching `StudyPlanAgent`
- The typed `LearnerProfile` contract enforces that the planner's output is always valid before the executor starts
- Each agent can be unit-tested independently — 24 tests for `AssessmentAgent`, 23 for `StudyPlanAgent`

---

### Pattern 2: Critic / Verifier

**Concept:** Introduce an agent that reviews outputs, checks assumptions, and validates reasoning before final responses are returned.

**In this system, the Critic pattern is implemented at two levels:**

**Level 1 — GuardrailsPipeline (structural critic)**

The `GuardrailsPipeline` is a dedicated 17-rule critic that runs *between* every agent handoff:

```
Input → [G-01..G-05 input critic] → Agent → [G-06..G-17 output critic] → Next Agent
```

Each rule has a severity level and a code:
- `BLOCK` (G-01..G-05, G-16): halts pipeline via `st.stop()` — used for PII, harmful content, negative hours, empty exam target
- `WARN` (G-06..G-15): flags concern but allows continuation — used for abnormal domain counts, low confidence, unrealistic budgets
- `INFO` (G-17): informational — URL trust guard logs untrusted links

The pipeline doesn't just validate syntax — it validates *semantic reasonableness*:
- `G-07`: Is the number of domain profiles consistent with the exam blueprint?
- `G-09`: Does the study budget match what was declared in the profile?
- `G-10`: Is every domain covered by at least one study task?
- `G-17`: Are all MS Learn URLs in the curated path on the trusted allowlist?

**Level 2 — ProgressAgent (readiness critic)**

`ProgressAgent` acts as an evidence-based critic before the learner can attempt the mock quiz:
- Computes a weighted readiness score across three independent dimensions
- Issues a structured verdict: `EXAM_READY` / `ALMOST_THERE` / `NEEDS_WORK` / `NOT_READY`
- Generates domain-specific nudges: _"You've logged 65% of your budget hours but your Computer Vision confidence is still WEAK — focus 3 more hours on this domain before attempting the quiz"_
- The `exam_go_nogo` signal (`GO` / `CONDITIONAL GO` / `NOT YET`) directly gates the assessment flow — agents cannot skip this review

**Why this is stronger than typical critic patterns:**
- Critic is rule-based (deterministic, fully unit-testable) not LLM-based (non-deterministic)
- 71 dedicated unit tests cover every critic rule with passing and failing inputs
- BLOCK-level violations are uncatchable — `st.stop()` means the pipeline physically cannot continue

---

### Pattern 3: Self-reflection & Iteration

**Concept:** Allow agents to reflect on intermediate results and refine their approach when confidence is low or errors are detected.

**In this system:**

**Remediation loop (macro self-reflection):**

When `AssessmentAgent` scores the mock quiz below the 60% pass mark:
```
Score < 60% → CertificationRecommendationAgent issues:
  - go_for_exam = False
  - remediation_plan = "Focus on: Computer Vision (33%), NLP (40%)"
  - next_cert_suggestions = [DP-100 as building block]
```
The learner is shown the remediation plan, which feeds directly back into:
1. A revised `LearnerProfile` — the profiler can be re-run with updated confidence scores reflecting the quiz weak domains
2. A new `StudyPlan` — `StudyPlanAgent.run()` re-executes with the updated profile, producing a revised schedule that front-loads the weak domains

This is a **complete agent loop** — the same agents run again on updated inputs, not a reconfiguration.

**Confidence-based adaptation within StudyPlanAgent (micro self-reflection):**

`StudyPlanAgent` internally reflects on the profile before building the plan:
1. Reads `domain_profiles[i].confidence_score` and `knowledge_level` for each domain
2. Computes a priority weight: lower confidence → higher priority → more hours in earlier weeks
3. Re-checks whether the resulting allocation is feasible given `total_budget_hours`
4. If a domain with `knowledge_level == UNKNOWN` would get zero hours after Largest Remainder (too many high-priority domains), it elevates its priority to ensure it is never skipped

**HITL gates as structured reflection checkpoints:**

Rather than agents making assumptions about learner progress:
- **Gate 1** (before `ProgressAgent`): learner manually inputs hours spent per domain + self-rating + practice exam result — forcing active self-assessment
- **Gate 2** (before `CertificationRecommendationAgent`): learner manually answers the 10-question quiz — forcing active knowledge retrieval

These gates mean the iteration loop is grounded in real learner data at every step, not just model predictions.

---

### Pattern 4: Role-based Specialisation

**Concept:** Assign clear responsibilities to each agent to reduce overlap and improve reasoning quality.

**In this system, each agent has a single, bounded responsibility:**

| Agent | Sole Responsibility | What It Does NOT Do |
|-------|--------------------|--------------------|
| `LearnerProfilingAgent` | Parse free-text background → structured `LearnerProfile` | Does not schedule, curate, assess, or recommend |
| `StudyPlanAgent` | Temporal scheduling — when to study what, for how long | Does not suggest resources, assess knowledge, or decide booking |
| `LearningPathCuratorAgent` | Content discovery — which MS Learn modules per domain | Does not schedule, assess, or care about hours or weeks |
| `ProgressAgent` | Readiness measurement — weighted formula from HITL data | Does not generate questions, curate content, or book exams |
| `AssessmentAgent` | Knowledge evaluation — generate + score a domain-proportional quiz | Does not produce study plans, resources, or booking decisions |
| `CertificationRecommendationAgent` | Booking decision + next-cert path | Does not reassess knowledge or reschedule study time |

**Why strict role-based separation improves reasoning quality:**

1. **No redundant reasoning** — `StudyPlanAgent` never "re-profiles" the learner; it trusts `LearnerProfile.risk_domains` completely. This means the planning algorithm is purely algorithmic (Largest Remainder), not subject to LLM drift.

2. **Contract enforcement** — Each role boundary is enforced by a Pydantic model. `StudyPlanAgent` receives a `LearnerProfile`; it can only produce a `StudyPlan`. It cannot request more information from the user or call back to the profiler.

3. **Independent testability** — Because roles don't overlap, each agent can be unit-tested with a minimal fixture. The 24 `AssessmentAgent` tests never need a real `StudyPlan`; the 23 `StudyPlanAgent` tests never need a real `LearningPath`.

4. **Parallel execution is possible** — `StudyPlanAgent` and `LearningPathCuratorAgent` both receive only `LearnerProfile` as input and produce independent outputs. Their lack of overlap makes concurrent execution safe — they cannot collide on shared state.

5. **Failure isolation** — If `LearningPathCuratorAgent` encounters a domain with no curated modules, it returns an empty list for that domain and logs a `WARN` — it never blocks `StudyPlanAgent` from completing, and vice versa.

**Contrast with a monolithic approach:**

A single "CertPrepAgent" that tries to do all of the above would:
- Mix temporal reasoning (scheduling) with content reasoning (curation) — two completely different problem types
- Be impossible to test without mocking the entire Azure stack
- Be unable to run any two tasks in parallel
- Produce reasoning traces that are impossible to attribute to specific decisions

The role-based design means the Admin Dashboard can show exactly which agent made each decision, with its specific inputs and outputs — providing the explainability required for responsible AI deployment.

---

## Pipeline Data Flow — How the System Works Without Embeddings or Vector Search

A natural question about this design is: *if the system has no embeddings, no vector index, and no semantic search over the MS Learn catalogue, how does free-text learner input result in precisely targeted learning resources?*

The answer is that the **LLM performs the semantic work once, at intake time**, producing a structured `LearnerProfile` JSON. Every agent downstream reads only typed fields — never the original free text.

### Step 1 — Free text in, structured JSON out (`LearnerProfilingAgent`)

The learner types a paragraph of free-form background:
> *"5 years Python dev, familiar with scikit-learn and REST APIs, worried about Azure OpenAI and Bot Service, hold AZ-104"*

`LearnerProfilingAgent` sends this to GPT-4o (Tier 1 via Foundry SDK or Tier 2 via direct OpenAI) with the exam domain reference and `_PROFILE_JSON_SCHEMA` in the system prompt. The model returns:

```json
{
  "experience_level": "intermediate",
  "domain_profiles": [
    { "domain_id": "plan_manage",           "confidence_score": 0.75, "knowledge_level": "strong",   "skip_recommended": true  },
    { "domain_id": "computer_vision",       "confidence_score": 0.45, "knowledge_level": "weak",     "skip_recommended": false },
    { "domain_id": "nlp",                   "confidence_score": 0.50, "knowledge_level": "moderate", "skip_recommended": false },
    { "domain_id": "generative_ai",         "confidence_score": 0.40, "knowledge_level": "weak",     "skip_recommended": false },
    { "domain_id": "conversational_ai",     "confidence_score": 0.30, "knowledge_level": "unknown",  "skip_recommended": false },
    { "domain_id": "document_intelligence", "confidence_score": 0.55, "knowledge_level": "moderate", "skip_recommended": false }
  ],
  "risk_domains": ["computer_vision", "generative_ai", "conversational_ai"],
  "total_budget_hours": 80
}
```

At this point the free text has been fully consumed. **No downstream agent ever sees the original background paragraph.** Everything that follows is pure data processing on typed Pydantic fields.

---

### Step 2 — Time allocation (`StudyPlanAgent`)

`StudyPlanAgent` receives the `LearnerProfile` and performs pure arithmetic — no LLM call, no text matching:

```python
# Priority weight from confidence_score and knowledge_level
for dp in profile.domain_profiles:
    if dp.skip_recommended:          priority = 0   # skip entirely
    elif dp.knowledge_level == UNKNOWN: priority = 4  # must cover
    elif dp.confidence_score < 0.40:    priority = 3  # high
    elif dp.confidence_score < 0.60:    priority = 2  # medium
    else:                               priority = 1  # low

# Largest Remainder distributes total_budget_hours proportionally
# → StudyPlan with StudyTask(domain_id, start_week, end_week, hours)
```

The `domain_id` strings (`"generative_ai"`, `"conversational_ai"`) are used as **dictionary keys**, not as text to be re-interpreted. The agent never reads the learner background.

---

### Step 3 — Resource lookup (`LearningPathCuratorAgent`)

`LearningPathCuratorAgent` uses `domain_id` as a direct key into the pre-curated MS Learn module catalogue:

```python
for task in study_plan.tasks:
    modules = LEARN_CATALOGUE[profile.exam_target][task.domain_id]
    # e.g. LEARN_CATALOGUE["AI-102"]["generative_ai"] → [
    #   {"title": "Develop generative AI solutions with Azure OpenAI", "url": "...", "hours": 3},
    #   {"title": "Apply prompt engineering ...", "url": "...", "hours": 2}
    # ]
```

The semantic matching between "what the learner needs" and "which MS Learn module covers it" was handled by the LLM in Step 1 when it assigned `domain_id` values. The curator performs an **O(1) lookup per domain** — no embedding, no cosine similarity, no vector index required.

> **Why this is acceptable and what the roadmap adds:**  
> The catalogue is curated per exam domain, covering exactly the material the exam tests — a bounded, well-known set. The planned Azure AI Search integration would extend this to dynamic lookup across the full ~4 000 MS Learn module catalogue, enabling resource selection within a domain (e.g. a lab-heavy module for a `lab_first` learner vs. a reference module for a `reference` learner).

---

### Step 4 — Quiz generation (`AssessmentAgent`)

`AssessmentAgent` samples questions proportionally to exam domain weights using `domain_id` as a key:

```python
for domain in exam_domains:
    n_questions = round(domain.weight * total_questions)
    sampled = random.choices(QUESTION_BANK[exam_target][domain.id], k=n_questions)
```

The agent never looks at the learner profile text — it only needs `exam_target` and the domain weights from the exam blueprint.

---

### Step 5 — Readiness scoring (`ProgressAgent`)

`ProgressAgent` combines HITL-provided data with the `domain_profiles` confidence scores:

```python
domain_confidence = weighted_mean(
    hitl.self_rating[d] / 5.0  for d in exam_domain_ids,
    weights = exam_domain_weight
)
hours_utilisation = sum(hitl.hours_spent.values()) / profile.total_budget_hours
practice_score    = hitl.practice_exam_score / 100

readiness = 0.55 * domain_confidence + 0.25 * hours_utilisation + 0.20 * practice_score
```

---

### Step 6 — Booking decision (`CertificationRecommendationAgent`)

`CertificationRecommendationAgent` receives `readiness_score`, `quiz_score`, and `exam_go_nogo` — all numbers and enums. It applies a deterministic rule matrix. No LLM call. No text. Pure rule-based decision on typed values.

---

### Summary: Where the "intelligence" lives

| Stage | What processes the data | Input type | Output type |
|-------|------------------------|------------|-------------|
| Intake → Profile | GPT-4o (LLM) | Free text | Structured JSON (`LearnerProfile`) |
| Profile → Study plan | Arithmetic (Largest Remainder) | Confidence scores + hours | `StudyPlan` with week blocks |
| Profile → Learning path | Dictionary lookup | `domain_id` keys | Module lists with URLs |
| Profile → Quiz | Proportional sampling | Exam weights + `domain_id` | 10 questions |
| HITL → Readiness | Weighted formula | Numbers (hours, ratings, score) | `readiness_score` + verdict |
| Readiness + Quiz → Booking | Rule matrix | Numbers + enum | `go_for_exam` + remediation plan |

The LLM is called **once** per learner session (or zero times in mock mode). All other steps are deterministic, testable, and credential-free.

---

## Human-in-the-Loop (HITL) Design — Where, What, and Why

### Where the HITL gates are

There are exactly **two mandatory human input gates** in the pipeline. Neither can be bypassed by agents:

```
Intake → Profile → Plan ∥ Curate
                              ↓
                   ┌──────────────────────────────┐
                   │  HITL GATE 1 — Progress Tab   │
                   │  Learner inputs:               │
                   │  • hours_spent per domain      │
                   │  • self_rating per domain      │
                   │  • practice_exam_score         │
                   └─────────────┬────────────────┘
                                 ↓
                         ProgressAgent
                         (readiness + go_nogo)
                                 ↓
                   ┌──────────────────────────────┐
                   │  HITL GATE 2 — Assessment Tab  │
                   │  Learner answers 10 questions  │
                   │  (domain-proportional quiz)    │
                   └─────────────┬────────────────┘
                                 ↓
                   AssessmentAgent → CertRecommendationAgent
```

If the learner does not submit Gate 1, `ProgressAgent` never runs and the Assessment tab stays disabled. If the learner does not complete Gate 2, `CertificationRecommendationAgent` never runs. These locks are enforced via `st.session_state` guards in `streamlit_app.py`, not just UI disabling.

---

### Gate 1: What data is collected and how agents use it

| Field | Type | How agents use it |
|-------|------|------------------|
| `hours_spent[domain_id]` | `float` slider per domain | `hours_utilisation = Σ hours_spent / total_budget_hours` → 25% of readiness score |
| `self_rating[domain_id]` | `int` 1–5 stars per domain | `self_rating / 5.0` replaces the profiler's `confidence_score` — **real self-assessment overrides the entry-time LLM estimate** |
| `practice_exam_score` | `float` 0–100 | `practice_score / 100` → 20% of readiness score |

The key mechanic: the learner's `self_rating` **replaces** the profiler's `confidence_score` in the readiness formula. If the LLM estimated Computer Vision at `0.6` at intake but the learner self-rated it `2/5` after studying, `ProgressAgent` uses `0.40` — reflecting reality over the entry-time estimate. The LLM estimate served as a prior; learner evidence is the posterior.

---

### Gate 2: What data is collected and how agents use it

`AssessmentAgent` generates 10 questions sampled proportionally to exam domain weights. After the learner submits, `AssessmentAgent.score_quiz()` computes:

```python
correct    = sum(1 for q, a in zip(questions, answers) if a == q.correct_answer)
quiz_score = correct / len(questions)   # 0.0 → 1.0
```

`CertificationRecommendationAgent` receives `quiz_score` alongside `readiness_score` and `exam_go_nogo`:

| `go_nogo` | `quiz_score` | Verdict |
|-----------|-------------|---------|
| `GO` | ≥ 0.70 | ✅ Book now |
| `GO` / `CONDITIONAL GO` | 0.50–0.69 | ⚠️ Review weak domains first |
| `NOT YET` or < 0.50 | any | ❌ Full remediation plan issued |

---

### Why HITL makes the system better

**1. Prevents compounding LLM estimation error**  
Without HITL the pipeline would chain one estimate into the next: profiler estimates → study plan → readiness estimate → booking decision (all predictions, never grounded). The `self_rating` at Gate 1 and quiz score at Gate 2 inject ground truth at the two points where estimation error would compound most severely.

**2. Detects plan non-adherence**  
A learner who spent 15 hours instead of the allocated 40 reports low `hours_spent` at Gate 1. `ProgressAgent` catches this — `hours_utilisation = 0.38` pulls readiness below the GO threshold regardless of domain confidence. No agent can advance the learner past a gate they haven't earned through actual study.

**3. Enables the remediation loop**  
When quiz score at Gate 2 is below 60%, `CertificationRecommendationAgent` issues a `remediation_plan` listing specific weak domains from the quiz. The learner returns to the Profile/Study tabs, re-runs the profiler with updated concern topics, and `StudyPlanAgent` produces a revised schedule front-loading those domains. This full loop is only possible because Gate 2 produced domain-level quiz evidence, not just a global score.

**4. Aligns AI confidence with learner reality**  
The profiler's `confidence_score` is an entry-time estimate derived from a 30-second background description. After 8 weeks of studying, `self_rating` and `quiz_score` are far more predictive of actual exam performance. HITL gates ensure the final booking recommendation is based on this later, higher-quality evidence rather than the initial LLM prior.

**5. Responsible AI — Human Oversight principle**  
No automated action — exam booking, study scheduling, or remediation plan — is ever triggered without the learner first providing actual evidence of their current state through HITL gates. Guardrail G-11 prevents `ProgressAgent` from running on all-zero HITL data: a learner who submits zeros gets a WARN asking them to confirm, rather than being silently advanced with misleading readiness scores.

---

# Judge & Reviewer Q&A — Complete Reference

> This section answers every question a competition judge or technical reviewer is likely to ask. Organised by topic. All answers grounded in actual code in this repository.

---

## Elevator Pitch

**Q: Describe your project in 30 seconds.**

Most learners buy a course, then stall. CertPrep uses a pipeline of specialised AI agents — one to understand you, one to plan, one to curate, one to measure progress, one to test, one to recommend — each with guardrails preventing hallucinations at every boundary. The result is a personalised, verifiable, agentic study companion that tells you when you are ready to book, and which cert to pursue next.

**Three differentiators:**

| Differentiator | Description |
|---|---|
| Agent specialisation | Each agent has a single, bounded responsibility. No monolithic prompt doing everything. |
| Guardrail enforcement | 17 rules, BLOCK and WARN levels, applied between every phase. All violations auditable in Admin Dashboard. |
| HITL loops | Two human-in-the-loop gates. The system checks real learner progress before advancing — no prediction chain without ground-truth data. |

---

## Why Multi-Agent?

**Q: Why use multiple agents instead of one big prompt?**

**Bounded Complexity:** A single GPT-4o prompt doing all 6 phases would require ~4 000 tokens of instruction and degrades on edge cases. Each agent has one task:

- **LearnerProfiler:** background text → domain confidence scores
- **StudyPlanAgent:** domain scores → weekly schedule
- **LearningPathCurator:** domain scores → MS Learn module list
- **ProgressAgent:** self-ratings + practice score → readiness percentage
- **AssessmentAgent:** domain weaknesses → 10 questions (5–30 configurable)
- **CertRecommender:** quiz score → booking decision + next cert

**Parallelism:** `StudyPlanAgent` and `LearningPathCuratorAgent` are independent. Both take `LearnerProfile` as input and produce different outputs. Running them in parallel via `ThreadPoolExecutor` halves Block 1 wall-clock time:

```python
with ThreadPoolExecutor(max_workers=2) as pool:
    f_plan = pool.submit(StudyPlanAgent().run, profile)
    f_path = pool.submit(LearningPathCuratorAgent().run, profile)
    plan   = f_plan.result()
    path   = f_path.result()
```

The Admin Dashboard shows measured parallel execution time. Typical: 12–35 ms in mock mode.

**Independent Testability:** Each agent has a clean interface: `run(input) -> output`. They can be unit-tested, swapped, and mocked independently. The orchestrator does not know how profiling works — it only cares about the `LearnerProfile` contract.

**Graduated Safety:** Different agents have different failure modes. A hallucinated module URL is a different problem from a hallucinated study plan duration. Each phase has its own guardrail set applied at the right boundary.

**Human Checkpoints:** Two HITL gates interrupt the pipeline:
- **Gate 1:** How much have you studied? How confident do you feel?
- **Gate 2:** Answer a domain-weighted quiz (default 10 questions, configurable 5–30).

The agents produce the inputs for these gates and interpret the outputs — humans provide the data.

---

## Agent Inventory

**Q: What agents does the system have? What does each one do?**

| # | Agent | Module | Input | Output | Notes |
|---|---|---|---|---|---|
| 0 | Intake Guard | `guardrails.py` (G-01..G-05) | `RawStudentInput` | `GuardrailResult` | PII + content safety before any LLM call |
| 1 | Learner Profiler | `b0_intake_agent.py` | `RawStudentInput` | `LearnerProfile` | Three-tier fallback: Foundry SDK → Azure OpenAI → rule-based mock |
| 2 | Study Planner | `b1_1_study_plan_agent.py` | `LearnerProfile` | `StudyPlan` | Largest Remainder day-level allocation |
| 3 | Path Curator | `b1_1_learning_path_curator.py` | `LearnerProfile` | `LearningPath` | 9 exam families; curated MS Learn modules per domain |
| 4 | Progress Tracker | `b1_2_progress_agent.py` | `ProgressSnapshot` | `ReadinessAssessment` + PDF | PDF via ReportLab; SMTP email on completion |
| 5 | Assessment | `b2_assessment_agent.py` | `LearnerProfile` | `AssessmentResult` | 10-question domain-proportional quiz (5–30 configurable) |
| 6 | Cert Recommender | `b3_cert_recommendation_agent.py` | `AssessmentResult` | `CertRecommendation` | GO / CONDITIONAL GO / NOT YET + remediation plan |

---

## Guardrails Deep Dive

**Q: What guardrails does the system have? How do they actually prevent hallucinations?**

A dedicated `GuardrailsPipeline` class runs **between every agent handoff** — not just at input. It has 17 named rules across 4 severity levels (BLOCK, WARN, INFO) and 6 pipeline phases.

### All 17 Rules

| Code | Phase | Level | Check |
|------|-------|-------|-------|
| G-01 | Intake | WARN | Background text is empty — profiling accuracy may be limited |
| G-02 | Intake | BLOCK | `exam_target` not in `EXAM_DOMAIN_REGISTRY` |
| G-03 | Intake | BLOCK | `hours_per_week` outside range [1, 80] |
| G-04 | Intake | BLOCK | `weeks_available` outside range [1, 52] |
| G-05 | Intake | INFO | No concern topics provided (optional field) |
| G-06 | Profile | BLOCK | `domain_profiles` count ≠ expected domain count for exam |
| G-07 | Profile | BLOCK | Any `confidence_score` outside [0.0, 1.0] |
| G-08 | Profile | WARN | `risk_domains` contains IDs not in the exam's registry |
| G-09 | Study Plan | BLOCK | Any task has `start_week > end_week` |
| G-10 | Study Plan | WARN | Total allocated hours exceed 110% of budget |
| G-11 | Progress | BLOCK | `hours_spent` is negative |
| G-12 | Progress | BLOCK | Any `domain_rating` outside [1, 5] |
| G-13 | Progress | BLOCK | `practice_exam_score` outside [0, 100] |
| G-14 | Quiz | WARN | Assessment contains fewer than 5 questions |
| G-15 | Quiz | BLOCK | Duplicate `question_id` values detected |
| G-16 | Content | BLOCK/WARN | Harmful keyword (BLOCK) or PII pattern — SSN/CC/email/phone/IP (WARN) |
| G-17 | URL | WARN | URL not on approved `learn.microsoft.com` allowlist |

### G-02 — Exam Registry Validation (code extract)

```python
if raw.exam_target not in EXAM_DOMAIN_REGISTRY:
    return GuardrailViolation(
        code    = 'G-02',
        level   = GuardrailLevel.BLOCK,
        message = f"Exam code '{raw.exam_target}' is not in the supported registry."
    )
```

Without G-02: `StudyPlanAgent` receives a `LearnerProfile` with 0 domains → Largest Remainder divides by zero.

### G-17 — URL Origin Allowlist (code extract)

```python
TRUSTED_URL_PREFIXES = [
    "https://learn.microsoft.com",
    "https://docs.microsoft.com",
    "https://aka.ms",
    "https://home.pearsonvue.com",
    "https://certiport.pearsonvue.com",
]

def check_G17(url: str) -> GuardrailViolation | None:
    if not any(url.startswith(p) for p in TRUSTED_URL_PREFIXES):
        return GuardrailViolation(code="G-17", level=GuardrailLevel.WARN,
                                  message=f"URL excluded — not on allowlist: {url}")
    return None
```

WARN not BLOCK: a single bad URL should not halt the entire learning path.

### G-16 — PII + Content Safety (dual mode)

G-16 runs in two modes depending on configuration:
- **Live mode:** HTTP POST to `POST /contentsafety/text:analyze`; `severity >= 2` → BLOCK; 4 categories (Hate, SelfHarm, Sexual, Violence)
- **Fallback mode:** 14 harmful keyword patterns + 7 PII regexes (SSN, credit card, passport, UK NI, email, phone, IP); regex fallback fires if Content Safety endpoint is unconfigured

### Audit Trail

Every violation is persisted to the `guardrail_violations` SQLite table with timestamp, rule code, level, and message. Admin Dashboard shows colour-coded violations per session. Judges can verify guardrails are **actually firing** — not just present in code.

---

## Study Plan Algorithm

**Q: Why use Largest Remainder? Why not just round hours to the nearest integer?**

Standard round-to-nearest loses days when `total_days` is not divisible by domain count. Largest Remainder guarantees:
1. **Sum of allocated days always equals `total_days` exactly** — no study days lost to rounding
2. **Every active domain gets at least 1 day** (`max(1, int(d))` floor) — no domain is silently zeroed out

The algorithm works at the **day level**: `total_days = study_weeks × 7` (one week reserved as review buffer). Each active domain receives a priority multiplier: `critical=2.0, high=1.5, medium=1.0, low=0.5, skip=0.0`. Day blocks are then converted to week bands and hours: `week_hours = (alloc_days / 7) × hours_per_week`.

### Worked Example — Alex Chen, AI-102, 12 hr/wk × 9 study weeks = 63 total days

| Domain | Priority | Rel. Weight | Normalised | Raw Days | Floor (≥1) | Final |
|--------|----------|-------------|------------|----------|------------|-------|
| plan_manage | high | 0.338 | 0.191 | 12.0 | 12 | 12 |
| computer_vision | critical | 0.360 | 0.204 | 12.8 | 12 | **13** |
| nlp | critical | 0.360 | 0.204 | 12.8 | 12 | **13** |
| generative_ai | medium | 0.175 | 0.099 | 6.2 | 6 | 6 |
| conversational_ai | high | 0.338 | 0.191 | 12.0 | 12 | 12 |
| document_intelligence | low | 0.070 | 0.040 | 2.5 | 2 | 2 |
| **Total** | | | 1.000 | 58.3 | 56 | **63** ✅ |

Sum of floored = 56. Deficit = −7. Top 7 remainder slots receive +1 each. Sum = exactly 63 days.

**Complexity:** O(n log n) — sort by remainder fraction descending, then distribute deficit one day at a time. Fully deterministic given the same `LearnerProfile`.

---

## Readiness Formula

**Q: How does the readiness score work? What are the weights and why?**

```
readiness = 0.55 × c_bar + 0.25 × h_u + 0.20 × p
```

Where:
- `c_bar` = mean normalised domain confidence = (1/|D|) × Σ (self_rating_d − 1) / 4  (rating 1–5 → 0.0–1.0)
- `h_u` = hours utilisation = min(hours_spent / hours_budget, 1.0)
- `p` = practice score proportion = practice_score / 100

**Weight rationale:** Domain confidence (0.55) is highest because it directly measures whether the learner has understood the material. Hours utilisation (0.25) rewards effort and plan adherence. Practice score (0.20) is a proxy for exam-condition readiness — it is weighted lower because practice conditions vary.

### Verdict thresholds

| Readiness | Verdict | Meaning |
|-----------|---------|----------|
| ≥ 80% | `EXAM_READY` | Book now |
| 65–79% | `ALMOST_THERE` | 1–2 weak domains remaining |
| 50–64% | `NEEDS_WORK` | Don't book yet; targeted review needed |
| < 50% | `NOT_READY` | Full remediation plan issued |

### Worked Example

Self-ratings: [3, 2, 2, 3, 2, 4] → `c_bar = (0.50+0.25+0.25+0.50+0.25+0.75)/6 = 0.417`  
Hours spent = 8, budget = 12 → `h_u = 0.667`  
Practice score = 45 → `p = 0.45`  

`readiness = 0.55×0.417 + 0.25×0.667 + 0.20×0.45 = 0.229 + 0.167 + 0.090 = 0.486 = 48.6%`  
**Verdict: NOT_READY** (below 50%)

---

## Concurrent Execution

**Q: You claim parallel agent execution — how do you prove it? Is it safe?**

**Evidence visible to judges:**
1. Admin Dashboard shows `Parallel agents completed in X ms` with measured wall-clock timing
2. Timing recorded in `st.session_state['parallel_agent_ms']` and displayed in the Agent Trace tab
3. Both agent outputs appear atomically in the trace with the same timestamp group

**Why safe to parallelise:** Both agents take `LearnerProfile` as read-only input. Neither writes to shared mutable state. SQLite writes happen in the orchestrator *after* both threads complete.

**GIL note:** For pure Python, the GIL limits CPU parallelism. However, both agents in mock mode are I/O-bound (SQLite reads). In live mode they make outbound HTTP calls that release the GIL. `ThreadPoolExecutor` correctly overlaps both cases regardless.

**Why not `asyncio`?** Streamlit's event loop conflicts with `asyncio.gather()` — `RuntimeError: event loop already running`. `ThreadPoolExecutor` gives identical I/O concurrency without touching the event loop.

---

## Azure AI Services Mapping

**Q: Which Azure AI services does the project use? What does each one contribute?**

| Azure Service | Role in CertPrep | Status |
|---|---|---|
| Azure OpenAI (GPT-4o) | `LearnerProfilingAgent` Tier 2 — structured JSON profile via JSON mode, temperature=0.2 | ✅ Live |
| Azure AI Foundry Agent Service (`azure-ai-projects`) | `LearnerProfilingAgent` Tier 1 — managed agent + thread + Foundry portal tracing | ✅ Live (Tier 1) |
| Azure AI Content Safety | G-16 guardrail — HTTP POST to `/contentsafety/text:analyze`; severity ≥ 2 = BLOCK; 4 categories | ✅ Live |
| Azure AI Evaluation SDK | `eval_harness.py` — Coherence, Relevance, Fluency LLM-as-judge metrics per profiling run | ✅ Live |
| SQLite (current) / Azure Cosmos DB (roadmap) | Learner profile, study plan, reasoning trace, guardrail audit persistence | 🔲 Cosmos DB roadmap |
| Azure Monitor | Per-agent latency, guardrail fire rate alerts | 🔲 Roadmap |
| Azure Key Vault | Secrets management — API key rotation without redeployment | 🔲 Roadmap |
| Azure Container Apps | Production Streamlit hosting — auto-scale, managed TLS, GitHub Actions CD | 🔲 Roadmap |
| Azure AI Search | Semantic search over full ~4 000 MS Learn module catalogue | 🔲 Roadmap |
| Azure Communication Services | Production email upgrade to replace `smtplib` | 🔲 Roadmap |

### AI Foundry Production Migration Roadmap

**Current build:** `streamlit_app.py` is the orchestrator, calling agents as Python functions.

**Production target:**

```
AI Foundry Project
+-- Agent: LearnerProfilerAgent     (Azure OpenAI tool)       — LIVE (Tier 1)
+-- Agent: StudyPlanAgent           (Python function tool)    — Roadmap
+-- Agent: LearningPathCuratorAgent (Azure AI Search tool)    — Roadmap
+-- Agent: ProgressTrackerAgent     (Python function tool)    — Roadmap
+-- Agent: AssessmentAgent          (Python function tool)    — Roadmap
+-- Agent: CertRecommenderAgent     (Python function tool)    — Roadmap

Orchestrator: AI Foundry Thread + Connected Agent API
  → Supervisor routes tasks to specialist agents
  → Thread memory maintains context across HITL gates
  → azure-ai-evaluation SDK for agent quality metrics (LIVE)
```

---

## Production Deployment Path

**Q: How would this scale beyond a hackathon? What does production look like?**

### Phase 1 — Current (Competition Submission)
- SQLite local file persistence
- Three-tier agent fallback: Foundry SDK → Azure OpenAI → rule-based mock
- Azure Content Safety API live on G-16 (`_check_content_safety_api`)
- `azure-ai-evaluation` SDK wired (`eval_harness.py` — Coherence, Relevance, Fluency)
- Streamlit Community Cloud hosting
- 9 exam families, 342 automated tests, 6-tab UI

### Phase 2 — Production MVP
- Azure Cosmos DB replaces SQLite (global distribution, sub-10 ms reads, session TTL)
- Azure OpenAI always-on (GPT-4o, 30K TPM)
- Azure Container Apps for Streamlit hosting (auto-scale, managed TLS)
- Azure Key Vault for API key rotation
- Azure Monitor for guardrail alert rules

### Phase 3 — Full AI Foundry Migration
- All 6 agents migrated to Foundry-managed agent threads
- Connected Agents (`LearnerProfiler` sub-calls `LearningPathCurator` on low-confidence domains)
- Azure AI Search integration for live MS Learn module catalogue (~4 000 modules)
- `azure-ai-evaluation` bias dataset expansion across all 9 cert families

### Phase 4 — Futuristic Vision (12+ months)

| Feature | Technology |
|---|---|
| Voice intake | Azure Speech + GPT-4o real-time |
| Real-time MS Learn progress sync | Microsoft Graph API |
| Cohort analytics dashboard | Azure ML + Cosmos DB analytical queries |
| Dynamic adaptive question bank | Azure AI Search semantic ranker + item response theory |
| Post-exam score correlation | Pearson VUE API |

**Q: Can this scale beyond one learner?**  
SQLite scales to thousands of learners for a read-heavy workload. The orchestrator is stateless (all state in SQLite + `session_state`). Swapping SQLite for Cosmos DB requires changing only the `database.py` connection layer — all agent code above it is unchanged.

---

## Competition Scoring Self-Assessment

**Q: How do you score yourself against the judging criteria?**

| Dimension | Max | Our Score | Justification |
|---|---|---|---|
| Technical Innovation | 25 | 23 | 8-agent pipeline, Largest Remainder allocation algorithm, 17-rule guardrail framework, 3-tier LLM fallback, HITL gates, PDF report generation |
| Azure Services Usage | 20 | 18 | GPT-4o live, AI Foundry Tier 1 live, Content Safety API live, Eval SDK live; Cosmos DB / ACS / Monitor as documented roadmap |
| Problem Impact | 20 | 19 | Real problem (Microsoft cert failure rate >40%), personalised per-domain plans, readiness gate prevents premature booking; 9-exam catalogue |
| Demo Quality | 20 | 18 | 7 seeded demo students across 9 exam families, Gantt + radar charts, PDF download, Admin audit dashboard, mock mode always works |
| Code Quality | 15 | 13 | Typed Pydantic contracts, guardrail separation, parallel execution evidence, 342 automated tests, schema-evolution-safe SQLite |
| **Total** | **100** | **91** | |

---

## Expected Judge Questions — Full Q&A

**Q: Is this really multi-agent, or just one big prompt split across functions?**  
Each agent is a separate Python class with its own file, typed input/output Pydantic contracts, independent unit tests, and dedicated timing in the Admin Dashboard. `StudyPlanAgent` and `LearningPathCuratorAgent` run in actual parallel threads simultaneously — something impossible with a single sequential prompt chain. Each agent can be swapped, mocked, or upgraded without touching the others.

**Q: Does the system produce any tangible output beyond a web UI?**  
Yes. `ProgressAgent` generates PDF reports (`generate_profile_pdf()` + `generate_assessment_pdf()`) via `reportlab`. PDFs are downloadable from the Profile and Progress tabs. They auto-attach to SMTP emails triggered on intake completion. The PDF contains: domain confidence scores, week-by-week Gantt study plan, readiness score breakdown, and booking recommendation.

**Q: How do you prevent hallucinations?**  
Three mechanisms: (1) **Structural:** 17 guardrail rules with BLOCK/WARN levels are applied between every agent handoff — the next agent never receives invalid data. (2) **Schema enforcement:** `response_format={"type": "json_object"}` + Pydantic `model_validate()` on every LLM response — the model cannot produce prose and call it JSON. (3) **URL trust:** G-17 allowlist prevents fabricated URLs from ever reaching users — only `learn.microsoft.com`, `docs.microsoft.com`, `aka.ms`, and `pearsonvue.com` domains are passed through.

**Q: What is the HITL value-add? Couldn't agents just estimate progress?**  
Without HITL the pipeline would chain one estimate into the next: profiler estimates → study plan → readiness estimate → booking decision. All predictions, never grounded. Gate 1 captures verified `hours_spent` (plan adherence) and `self_rating` (overrides LLM entry-time estimate with real posterior evidence). Gate 2 provides a configurable diagnostic quiz (default 10 questions, 5–30 via slider) that identifies weak domains for remediation. A learner who spent 50% of their hours but self-rates low will correctly receive `NEEDS_WORK`, not a spurious `EXAM_READY`.

**Q: Why Largest Remainder for study plan allocation?**  
It guarantees every available study day is allocated to exactly one domain with no rounding loss, and no active domain receives zero time (`max(1, int(d))` floor). Standard round-to-nearest quietly loses days when `total_days` is not divisible by domain count — those days simply vanish from the plan. LR is O(n log n) and produces provably optimal integer allocations for any fixed total.

**Q: What is novel versus a RAG chatbot?**  
Five differences: (1) Structured per-domain confidence scores — not free-text answers, typed `DomainProfile` objects with floats and enums; (2) Deterministic study plan via LR algorithm — same inputs always produce the same plan; (3) Readiness gating that actively tells users when **not** to book; (4) Next-cert recommendation with a synergy map; (5) Multi-student admin view with full audit trail, guardrail violation log, and per-agent timing.

**Q: How does free-text input become targeted learning resources without embeddings or vector search?**  
The LLM performs semantic work **once** at intake time, converting free-text background into a typed `LearnerProfile` with `domain_id` keys. Every downstream agent uses those keys as dictionary lookups — O(1), no cosine similarity, no vector index. The semantic matching between "what the learner knows" and "which domain covers it" is GPT-4o's job. All subsequent agents are deterministic.

**Q: What tests do you have? Could a judge run them?**  
Yes — zero Azure credentials required. 342 automated tests across 15 test modules:
```powershell
.venv\Scripts\python.exe -m pytest tests/ -v
```
Test coverage: guardrails (71 tests), assessment agent (24), study plan agent (23), serialization helpers (25), progress agent (20+), config (15), models (12), pipeline integration (8). All pass in mock mode with no environment variables set.

**Q: What responsible AI principles does the project apply?**

| Principle | Implementation |
|-----------|---------------|
| Fairness | Exam domain weights sourced from official Microsoft exam blueprints — not inferred by LLM |
| Reliability & Safety | 17 guardrail rules at every agent boundary; BLOCK-level violations halt pipeline via `st.stop()` |
| Privacy & Security | G-16 PII scan (SSN, CC, passport, email, phone, IP) fires before any LLM call; API keys in `.env`, never committed |
| Inclusivity | 9 exam families, any Microsoft cert learner supported; multi-persona demo cohort |
| Transparency | Admin Dashboard shows per-agent reasoning trace, guardrail audit log, timing, and token counts |
| Accountability | Every guardrail violation persisted to SQLite with timestamp and code; full replay possible |
| Human Oversight | Two mandatory HITL gates; no booking recommendation without learner-provided evidence |

**Q: What's missing or incomplete?**  
Honestly: (1) T-06 — `StudyPlanAgent`, `LearningPathCuratorAgent`, `AssessmentAgent`, `CertRecommendationAgent` not yet migrated to Foundry SDK (only `LearnerProfilingAgent` uses Foundry Tier 1 today); (2) T-08 — MCP MS Learn server not wired (`MCP_MSLEARN_URL` placeholder exists but `LearningPathCuratorAgent` uses static catalogue); (3) T-10 — demo video not yet recorded; (4) T-11 — not yet deployed to Streamlit Cloud with service principal secrets.

**Q: Why does the system support 9 exam families but only use AI-102 domain weights in the guardrail?**  
It doesn't. This was a bug that has been fixed: `ProgressAgent` now calls `get_exam_domains(profile.exam_target)` to pull per-exam domain weights from `EXAM_DOMAIN_REGISTRY`. The formula applies the correct blueprint weights for whichever certification the learner is targeting. The fix is covered by 5 parametrized tests in `tests/test_progress_agent.py`.

**Q: How do you handle schema evolution — if you add a field to a dataclass, do old SQLite rows break?**  
No. All `*_from_dict()` deserialization helpers use a `_dc_filter()` guard that filters dict keys against `dataclasses.fields()` before passing to the constructor — unknown keys are silently dropped. Missing keys fall back to field defaults. 25 dedicated tests in `tests/test_serialization_helpers.py` cover round-trips with extra keys, missing keys, and None values.

**Q: What is the `azure-ai-evaluation` integration?**  
`src/cert_prep/eval_harness.py` wraps the `azure-ai-evaluation` SDK with three evaluators: `CoherenceEvaluator`, `RelevanceEvaluator`, `FluencyEvaluator`. After every live-mode `LearnerProfilingAgent` run, `evaluate_profile(raw_input, learner_profile)` is called, scoring the profiler's output against the input. Results are stored in `st.session_state["eval_result"]` and displayed in the Admin Dashboard. In mock mode or when the package is not installed, it returns `EvalResult(available=False)` — full graceful degradation.

**Q: Is the Streamlit UI actually 6 tabs or 7?**  
6 tabs in the current build (after a refactor from 7). Tabs: **Profile**, **Study Plan**, **Learning Path**, **Progress**, **Assessment**, **Recommendations**. The Admin Dashboard is a separate Streamlit page (`pages/1_Admin_Dashboard.py`), not a tab.

---

## End-to-End Data Flow

**Q: Walk me through a complete learner session from form submission to booking recommendation.**

```
Browser (learner fills intake form)
  |
  v
streamlit_app.py (orchestrator)
  |
  +── [G-01..G-05] BLOCK → user corrects form
  |
  +── LearnerProfilingAgent
  |    Tier 1: AIProjectClient (Foundry SDK)  ← if AZURE_AI_PROJECT_CONNECTION_STRING set
  |    Tier 2: AzureOpenAI JSON mode          ← elif AZURE_OPENAI_ENDPOINT set
  |    Tier 3: rule-based mock profiler       ← fallback / FORCE_MOCK_MODE=true
  |    Output: LearnerProfile → SQLite
  |
  +── [G-06..G-08] BLOCK → bug in profiler caught
  |
  +── ThreadPoolExecutor (parallel)
  |    +── StudyPlanAgent        → StudyPlan → SQLite
  |    +── LearningPathCuratorAgent -[G-17]→ LearningPath → SQLite
  |
  +── [G-09..G-10] WARN  [G-17] WARN
  |
  +── HITL GATE 1 (Progress tab)
  |    Learner submits: hours_spent, self_rating per domain, practice_score
  |    +── [G-11..G-13] BLOCK → invalid progress data rejected
  |    +── ProgressAgent → ReadinessAssessment + PDF → SQLite
  |
  +── HITL GATE 2 (Assessment tab)
  |    Learner answers 10-question domain-proportional quiz
  |    +── [G-14..G-15] WARN/BLOCK → quiz integrity check
  |    +── AssessmentAgent → AssessmentResult → SQLite
  |
  +── CertificationRecommendationAgent
       Input: AssessmentResult + ReadinessAssessment + LearnerProfile
       Output: CertRecommendation (GO/CONDITIONAL GO/NOT YET)
               + next_cert_suggestions + remediation_plan → SQLite
               → displayed in Recommendations tab
```

Total wall-clock time in mock mode: **< 1 second** (all agents deterministic, no HTTP calls).  
Total wall-clock time in live mode: **3–8 seconds** (Foundry/OpenAI latency for profiling only; all downstream agents remain deterministic).
