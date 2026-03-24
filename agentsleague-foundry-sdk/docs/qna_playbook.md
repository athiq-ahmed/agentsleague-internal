# Q&A Playbook — Certification Preparation Multi-Agent System

> Designed for competition judges and technical reviewers evaluating the Certification Preparation entry for Agents League 2026. Covers multi-agent architecture, key design decisions, scoring dimensions, and frequently asked technical questions.

---

## Table of Contents

1. [Elevator Pitch](#1-elevator-pitch)
2. [Why Multi-Agent](#2-why-multi-agent)
3. [Agent Inventory](#3-agent-inventory)
4. [Guardrails Deep Dive](#4-guardrails-deep-dive)
5. [Study Plan Algorithm](#5-study-plan-algorithm)
6. [Readiness Formula](#6-readiness-formula)
7. [End-to-End Data Flow](#7-end-to-end-data-flow)
8. [Concurrent Execution Argument](#8-concurrent-execution-argument)
9. [Azure AI Services Mapping](#9-azure-ai-services-mapping)
10. [Production Deployment Path](#10-production-deployment-path)
11. [Competition Scoring Self-Assessment](#11-competition-scoring-self-assessment)

---

## 1. Elevator Pitch

> Most learners buy a course, then stall. CertPrep uses a pipeline of specialised AI agents — one to understand you, one to plan, one to curate, one to measure progress, one to test, one to recommend — each with guardrails preventing hallucinations at every boundary. The result is a personalised, verifiable, agentic study companion that knows when you are ready to book, and which cert to pursue next.

**Three differentiators:**

| Differentiator | Description |
|---|---|
| Agent specialisation | Each agent has a single, bounded responsibility. No monolithic prompt doing everything. |
| Guardrail enforcement | 17 rules, BLOCK and WARN levels, applied between every phase. All violations auditable in Admin Dashboard. |
| HITL loops | Two human-in-the-loop gates. The system checks real learner progress before advancing. |

---

## 2. Why Multi-Agent

### Bounded Complexity

A single GPT-4 prompt doing all 6 phases would require ~4000 tokens of instruction and degrades on edge cases. Each agent has one task:

- **LearnerProfiler:** background text → domain confidence scores
- **StudyPlanAgent:** domain scores → weekly schedule
- **LearningPathCurator:** domain scores → MS Learn module list
- **ProgressAgent:** self-ratings + practice score → readiness percentage
- **AssessmentAgent:** domain weaknesses → 10 questions (5–30 configurable)
- **CertRecommender:** quiz score → booking decision + next cert

### Parallelism

StudyPlanAgent and LearningPathCuratorAgent are independent. Both take LearnerProfile as input and produce different outputs. Running them in parallel (ThreadPoolExecutor) halves wall-clock time.

```python
with ThreadPoolExecutor(max_workers=2) as pool:
    f_plan = pool.submit(StudyPlanAgent().run, profile)
    f_path = pool.submit(LearningPathCuratorAgent().run, profile)
    plan   = f_plan.result()
    path   = f_path.result()
```

The Admin Dashboard shows measured parallel execution time. Typical: 12–35ms in mock mode.

### Independent Testability

Each agent has a clean interface: `run(input) -> output`. They can be unit-tested, swapped, and mocked independently. The orchestrator does not know how profiling works — it only cares about the LearnerProfile contract.

### Graduated Safety

Different agents have different failure modes. A hallucinated module URL is a different problem from a hallucinated study plan duration. Each phase has its own guardrail set applied at the right boundary.

### Human Checkpoints

Two HITL gates interrupt the pipeline:
- **Gate 1:** How much have you studied? How confident do you feel?
- **Gate 2:** Answer a domain-weighted quiz (default 10 questions, configurable 5–30).

The agents produce the inputs for these gates and interpret the outputs — humans provide the data.

---

## 3. Agent Inventory

| # | Agent | Module | Input | Output | Notes |
|---|---|---|---|---|---|
| 0 | Intake Guard | guardrails.py (G-01..G-05) | RawStudentInput | GuardrailResult | PII + content safety |
| 1 | Learner Profiler | b0_intake_agent.py | RawStudentInput | LearnerProfile | Three-tier fallback: Foundry SDK → Azure OpenAI → rule-based mock |
| 2 | Study Planner | b1_1_study_plan_agent.py | LearnerProfile | StudyPlan | Largest Remainder allocation |
| 3 | Path Curator | b1_1_learning_path_curator.py | LearnerProfile | LearningPath | 9 exam families; curated MS Learn modules per family |
| 4 | Progress Tracker | b1_2_progress_agent.py | ProgressSnapshot | ReadinessAssessment + PDF | PDF reports via reportlab; SMTP email |
| 5 | Assessment | b2_assessment_agent.py | LearnerProfile | AssessmentResult | 10-question adaptive quiz (5–30 configurable) |
| 6 | Cert Recommender | b3_cert_recommendation_agent.py | AssessmentResult | CertRecommendation | GO / CONDITIONAL GO / NOT YET |

---

## 4. Guardrails Deep Dive

### G-02 — Exam Registry Validation

The exam code must exist in `EXAM_DOMAIN_REGISTRY`. This prevents any downstream agent from running against an unknown exam with no domain definitions.

```python
if raw.exam_target not in EXAM_DOMAIN_REGISTRY:
    return GuardrailViolation(
        code    = 'G-02',
        level   = GuardrailLevel.BLOCK,
        message = f"Exam code '{raw.exam_target}' is not in the supported registry."
    )
```

Without this guardrail: StudyPlanAgent receives a LearnerProfile with 0 domains → Largest Remainder divides by zero.

### G-17 — URL Origin Allowlist

Every URL returned by LearningPathCuratorAgent is checked against a trusted origin set.

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

### All 17 Rules

| Code | Phase | Level | Check |
|------|-------|-------|-------|
| G-01 | Intake | WARN | Background text is empty — profiling accuracy may be limited |
| G-02 | Intake | BLOCK | exam_target not in EXAM_DOMAINS registry |
| G-03 | Intake | BLOCK | hours_per_week outside range [1, 80] |
| G-04 | Intake | BLOCK | weeks_available outside range [1, 52] |
| G-05 | Intake | INFO | No concern topics provided (optional field) |
| G-06 | Profile | BLOCK | domain_profiles count != expected domain count for exam |
| G-07 | Profile | BLOCK | any confidence_score outside [0.0, 1.0] |
| G-08 | Profile | WARN | risk_domains contains IDs not in the exam's registry |
| G-09 | Study Plan | BLOCK | any task has start_week > end_week |
| G-10 | Study Plan | WARN | total allocated hours exceed 110% of budget |
| G-11 | Progress | BLOCK | hours_spent is negative |
| G-12 | Progress | BLOCK | any domain_rating outside [1, 5] |
| G-13 | Progress | BLOCK | practice_exam_score outside [0, 100] |
| G-14 | Quiz | WARN | assessment contains fewer than 5 questions |
| G-15 | Quiz | BLOCK | duplicate question_id values detected |
| G-16 | Content | BLOCK/WARN | harmful keyword (BLOCK) or PII pattern — SSN/CC/email (WARN) |
| G-17 | URL | WARN | URL not on approved learn.microsoft.com allowlist |

### Audit Trail

Every violation is persisted to the `guardrail_violations` SQLite table. Admin Dashboard shows colour-coded violations. Judges can verify guardrails are actually firing — not just present in code.

---

## 5. Study Plan Algorithm

### Largest Remainder Allocation

The algorithm works at the **day level**: `total_days = study_weeks × 7` (one week reserved as review buffer). Each active domain's weight is `exam_domain_weight × priority_multiplier` where multipliers are: critical=2.0, high=1.5, medium=1.0, low=0.5, skip=0.0 (priority is derived from the domain's knowledge level and whether it is a risk domain). Day blocks are then converted to week bands and hours: `week_hours = (alloc_days / 7) × hours_per_week`.

**Worked example: Alex Chen, AI-102, 12hr/wk × 9 study weeks = 63 total days**

| Domain | Priority | Rel. Weight | Normalised | Raw Days | Floor (≥1) | Final |
|--------|---------|-------------|------------|----------|-----------|-------|
| D1 | high | 0.338 | 0.191 | 12.0 | 12 | 12 |
| D2 | critical | 0.360 | 0.204 | 12.8 | 12 | 13 |
| D3 | critical | 0.360 | 0.204 | 12.8 | 12 | 13 |
| D4 | medium | 0.175 | 0.099 | 6.2 | 6 | 6 |
| D5 | high | 0.338 | 0.191 | 12.0 | 12 | 12 |
| D6 | low | 0.070 | 0.040 | 2.5 | 2 | 2 |
| skip | skip | 0.000 | — | — | 1 min | — |
| **Total** | | | 1.000 | 58.3 → 63 | 56 | **63** |

Sum of floored = 56. Deficit = −7. Top 7 remainder slots get +1 each. Sum = exactly 63 days.

**Key properties:** (1) Sum of allocated days always equals `total_days` exactly — no days lost to rounding. (2) Every active domain gets at least 1 day (`max(1, int(d))` floor) — no domain is silently zeroed out.

---

## 6. Readiness Formula

```
readiness = 0.55 × c_bar + 0.25 × h_u + 0.20 × p
```

Where:
- `c_bar` = mean normalised confidence = (1/|D|) × Σ (r_d − 1) / 4  (rating 1–5 → 0–1)
- `h_u` = hours utilisation = min(hours_spent / hours_budget, 1.0)
- `p` = practice score proportion = practice_score / 100

**Worked example:**

Ratings: [3, 2, 2, 3, 2, 4] → c_bar = (0.50+0.25+0.25+0.50+0.25+0.75)/6 = 0.417  
Hours spent=8, budget=12 → h_u = 0.667  
Practice score=45 → p = 0.45  

readiness = 0.55×0.417 + 0.25×0.667 + 0.20×0.45 = 0.229 + 0.167 + 0.090 = **0.486 → 48.6%**

Verdict: **NOT YET** (below 50%)

**Weight rationale:** Confidence (0.55) is highest because it directly measures domain knowledge. Hours (0.25) rewards effort. Practice score (0.20) is a proxy for exam readiness.

---

## 7. End-to-End Data Flow

```
Browser
  |
  v
streamlit_app.py (orchestrator)
  |
  +-- [G-01..G-05] BLOCK -> user corrects form
  |
  +-- Profiler Agent
  |    Mock: b1_mock_profiler.py (rule engine)
  |    Live: LearnerProfilingAgent -> Azure OpenAI GPT-4o
  |    Output: LearnerProfile -> SQLite
  |
  +-- [G-06..G-08] BLOCK -> bug in profiler
  |
  +-- ThreadPoolExecutor
  |    +-- StudyPlanAgent -> StudyPlan -> SQLite
  |    +-- LearningPathCuratorAgent -[G-17]-> LearningPath -> SQLite
  |
  +-- [G-09..G-10] WARN, [G-17] WARN
  |
  +-- HITL Gate 1 (Tab 5) -> user fills form
  |    +-- ProgressAgent -> ReadinessAssessment
  |
  +-- HITL Gate 2 (Tab 6) -> user answers quiz
  |    +-- AssessmentAgent -> AssessmentResult -> SQLite
  |
  +-- CertRecommendationAgent -> CertRecommendation -> SQLite
       |
       v
     Tab 6: booking decision + next cert + remediation plan
```

---

## 8. Concurrent Execution Argument

**Claim:** StudyPlanAgent and LearningPathCuratorAgent run in parallel.

**Evidence visible to judges:**
1. Admin Dashboard shows `Parallel agents completed in Xms` with measured timing
2. Timing recorded in `st.session_state['parallel_agent_ms']` and shown in Tab 1 Agent Trace
3. Both agent outputs appear atomically in the trace

**Why safe to parallelise:** Both agents take LearnerProfile as read-only input. Neither writes to shared mutable state. SQLite writes happen in the orchestrator after thread completion.

**GIL note:** For pure Python, the GIL limits CPU parallelism. However, both agents in mock mode are I/O-bound (SQLite reads). In live mode they make HTTP calls that release the GIL. ThreadPoolExecutor correctly overlaps both cases.

---

## 9. Azure AI Services Mapping

| Azure Service | Role in CertPrep | Benefit |
|---|---|---|
| Azure OpenAI (GPT-4o) | LearnerProfilingAgent in live mode | Structured JSON output, low temperature |
| Azure AI Foundry | Agent orchestration — Tier 1 SDK live for `LearnerProfilingAgent`; production roadmap for all agents | Native multi-agent patterns, Connected Agent support |
| Azure AI Search | Knowledge retrieval for module catalogue | Semantic search over MS Learn content |
| Azure Cosmos DB | Production learner data store | Global distribution, sub-10ms reads, session TTL |
| Azure Monitor | Telemetry, guardrail violation alerts | Built-in dashboard, alert rules for BLOCK events |
| Azure Key Vault | Secrets management in production | API key rotation without code deployment |
| Azure Container Apps | Streamlit hosting in production | Auto-scale, managed TLS, GitHub Actions CD |
| Azure Content Safety | G-16 live content filtering — HTTP POST to `contentsafety/text:analyze`; severity ≥ 2 = BLOCK; regex fallback when unconfigured | Managed harmful-content detection; 4-category coverage (Hate/SelfHarm/Sexual/Violence) |
| Azure AI Evaluation | LLM-as-judge quality metrics via `eval_harness.py` — Coherence, Relevance, Fluency per profiling run | Programmatic agent quality measurement without manual labelling |

### AI Foundry Production Migration

Current build: `streamlit_app.py` is the orchestrator, calling agents as Python functions.

Production target:

```
AI Foundry Project
+-- Agent: LearnerProfilerAgent     (Azure OpenAI tool) — LIVE (Tier 1)
+-- Agent: StudyPlanAgent           (Python function tool)
+-- Agent: LearningPathCuratorAgent (Azure AI Search tool)
+-- Agent: ProgressTrackerAgent     (Python function tool)
+-- Agent: AssessmentAgent          (Python function tool)
+-- Agent: CertRecommenderAgent     (Python function tool)

Orchestrator: AI Foundry Thread + Assistant API
  -> Supervisor routes tasks to specialist agents
  -> Thread memory maintains context across HITL gates
  -> azure-ai-evaluation SDK for agent quality metrics (LIVE — eval_harness.py)
```

---

## 10. Production Deployment Path

### Phase 1 — Current (Competition)
- SQLite (local file)
- Mock profiler (rule engine) + Azure OpenAI optional; three-tier fallback (Foundry SDK → OpenAI → mock)
- Azure Content Safety API live on G-16 (`_check_content_safety_api`)
- `azure-ai-evaluation` SDK wired (`eval_harness.py` — Coherence, Relevance, Fluency)
- Streamlit Community Cloud
- 9 exam families, 342 automated tests, 6-tab Streamlit UI

### Phase 2 — Production MVP
- Azure Cosmos DB replaces SQLite
- Azure OpenAI always-on (GPT-4o)
- Azure Container Apps for hosting
- Azure Key Vault + Azure Monitor

### Phase 3 — Full AI Foundry Migration
- AI Foundry multi-agent threads
- Connected Agents (LearnerProfiler sub-calls LearningPathCurator)
- Azure AI Search integration for live MS Learn catalogue
- `azure-ai-evaluation` bias + bias dataset (B-01) — Needs labelled test set across 9 cert families

### Phase 4 — Futuristic Vision (12+ months)

| Feature | Technology |
|---|---|
| Voice intake | Azure Speech + GPT-4o |
| Real-time MS Learn progress sync | Microsoft Graph API |
| Cohort analysis | Azure ML + Cosmos DB analytics |
| Dynamic question bank | Azure AI Search semantic ranker |
| Exam score correlation | Pearson VUE API |

---

## 11. Competition Scoring Self-Assessment

| Dimension | Max | Our Score | Justification |
|---|---|---|---|
| Technical Innovation | 25 | 23 | 8-agent pipeline, LR allocation algorithm, 17-rule guardrail framework, HITL gates, PDF report generation |
| Azure Services Usage | 20 | 18 | GPT-4o live mode, AI Foundry roadmap, 8 services documented |
| Problem Impact | 20 | 19 | Real problem (cert failure rate), personalised plans, booking readiness gate; 9-exam catalogue |
| Demo Quality | 20 | 18 | 7 seeded demo students across 9 exam families, Gantt + radar charts, PDF download, Admin audit dashboard |
| Code Quality | 15 | 13 | Typed models (Pydantic), guardrail separation, parallel execution evidence |
| **Total** | **100** | **91** | |

### Expected Judge Questions

**Q: Does the system produce any tangible output beyond a web UI?**  
A: Yes. The Progress Tracker generates PDF reports (profile + study plan PDF, readiness progress PDF) via `reportlab`. These are downloadable from the Profile and Progress tabs and can be emailed automatically on intake completion via `smtplib` SMTP. The PDF contains domain confidence scores, weekly study plan, and readiness assessment.

**Q: Is this really multi-agent or just one big prompt?**  
A: Each agent is a separate Python class with its own typed input-output contract. They are independently callable and testable. Admin Dashboard shows each agent step with individual timing.

**Q: How do you prevent hallucinations?**  
A: Three mechanisms: (1) 17 guardrail rules with BLOCK/WARN levels between every phase, (2) `response_format=json_object` for all GPT-4o calls with Pydantic validation, (3) URL allowlisting (G-17) prevents hallucinated links from reaching users.

**Q: What is the HITL value-add?**  
A: The ProgressAgent cannot know how the learner actually felt studying. Gate 1 captures self-ratings and hours spent. Gate 2 provides a configurable diagnostic quiz (default 10 questions, 5–30 via slider) identifying weak domains for remediation. Without these gates, the system only recommends based on background text — no feedback loop.

**Q: Why Largest Remainder for study plan?**  
A: It guarantees every available study day is allocated to exactly one domain with no rounding loss. The algorithm works at the day level (`total_days = study_weeks × 7`), then converts days → hours. Standard round-to-nearest loses days when total_days is not divisible by domain count. The `max(1, int(d))` floor also prevents any active domain from receiving zero time. LR is O(n log n) and produces provably optimal integer allocations given a fixed total.

**Q: Can this scale beyond one learner?**  
A: SQLite scales to thousands of learners (read-heavy workload). The orchestrator is stateless (all state in SQLite + session_state). Replacing SQLite with Cosmos DB requires changing only the `database.py` connection string.

**Q: What is novel versus a RAG chatbot?**  
A: Five differences: (1) Structured per-domain confidence scores, not free-text answers; (2) Deterministic study plan via LR algorithm; (3) Readiness gating that tells users when NOT to book; (4) Next-cert recommendation with synergy map; (5) Multi-student admin view with full audit trail.
