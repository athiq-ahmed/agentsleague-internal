# Azure AI Services — Usage Map & Cost Optimisation Guide

> **Audience:** Engineers and product owners reviewing the Cert Prep Multi-Agent app.  
> **Purpose:** Identify every point where an Azure AI service is (or could be) called,
> map it to the exact file and line, estimate real-world costs, and give actionable
> recommendations to keep spend in check.

---

## Table of Contents

1. [Quick Summary](#1-quick-summary)
2. [Service Inventory](#2-service-inventory)
3. [Azure OpenAI — The Only Live Cloud Call](#3-azure-openai--the-only-live-cloud-call)
4. [MS Learn Catalog API — Intentionally Offline](#4-ms-learn-catalog-api--intentionally-offline)
5. [Azure AI Content Safety — Not Yet Integrated](#5-azure-ai-content-safety--not-yet-integrated)
6. [Azure AI Search — Not Yet Integrated](#6-azure-ai-search--not-yet-integrated)
7. [SQLite — Local, Zero Cloud Cost](#7-sqlite--local-zero-cloud-cost)
8. [SMTP / Email Dispatch — Optional, Env-Gated](#8-smtp--email-dispatch--optional-env-gated)
9. [Real Cost Estimates](#9-real-cost-estimates)
10. [Recommendations — Where to Use, Where NOT to Use](#10-recommendations--where-to-use-where-not-to-use)

---

## 1. Quick Summary

| Service | Used Today? | Cloud Cost Incurred? | Gating Mechanism |
|---------|-------------|----------------------|------------------|
| Azure OpenAI GPT-4o | ✅ Optional | Only when `use_live = True` | `use_live` flag — default `False` |
| MS Learn Catalog API | ❌ Offline | None | Hardcoded catalogue, API stubbed |
| Azure AI Content Safety | ❌ Not integrated | None | Heuristic keyword list only |
| Azure AI Search | ❌ Not integrated | None | In-memory Q-bank |
| Azure Communication Services | ❌ Not integrated | None | Raw SMTP only |
| SQLite | ✅ Always on | **Zero** — file on disk | Always active |
| SMTP (any provider) | ✅ Optional | Negligible (env-gated) | `SMTP_HOST/USER/PASS` env vars |

**In demo mode (default), the app makes zero Azure API calls.** The single `use_live = False`
toggle on line 1331 of `streamlit_app.py` gates everything.

---

## 2. Service Inventory

### Where `use_live` lives

```
streamlit_app.py  ·  line 1331
────────────────────────────────
use_live = False          # ← flip to True for live Azure OpenAI calls
```

When `use_live = False`, the app calls `run_mock_profiling_with_trace(raw)` — a fully
deterministic rule-based profiler that produces the same structured `LearnerProfile`
without touching the network.

When `use_live = True`, env vars `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`,
and `AZURE_OPENAI_DEPLOYMENT` are injected at runtime (lines 1740–1742) and a real
`LearnerProfilingAgent` is constructed.

---

## 3. Azure OpenAI — The Only Live Cloud Call

### Call site

| Property | Value |
|----------|-------|
| **File** | `src/cert_prep/b0_intake_agent.py` |
| **Class** | `LearnerProfilingAgent` |
| **Method** | `_call_llm()` — lines ~237–249 |
| **Triggered from** | `streamlit_app.py` lines 1737–1748 |
| **SDK call** | `client.chat.completions.create(...)` |

### Exact call parameters

```python
response = self._client.chat.completions.create(
    model       = self._cfg.deployment,          # default: "gpt-4o"
    response_format = {"type": "json_object"},   # structured JSON output
    messages    = [
        {"role": "system", "content": _SYSTEM_PROMPT},   # ~1,200 tokens
        {"role": "user",   "content": user_message},     # ~200 tokens
    ],
    temperature = 0.2,     # low → deterministic structured output
    max_tokens  = 2000,    # upper cap on output
)
```

### What the LLM actually does

The system prompt sends the full exam domain reference (6 domains, weights, descriptions)
and a strict JSON schema. The user message contains the student's name, exam target,
background text, existing certs, hours per week, topics of concern, and goal.

The LLM maps all of this into a `LearnerProfile` JSON — including per-domain confidence
scores, risk domains, learning style, analogy map, and recommended approach.

**Critically: the LLM is only used here.** All downstream agents (StudyPlanAgent,
LearningPathCuratorAgent, ProgressAgent, AssessmentAgent, CertRecommendationAgent)
are completely deterministic Python logic with no further API calls.

### Token budget per call

| Token type | Estimate | Notes |
|-----------|----------|-------|
| System prompt input | ~1,200 | Domain JSON + schema + rules |
| User message input | ~180 | Student answers, varies slightly |
| **Total input** | **~1,380** | |
| Output (profile JSON) | ~900–1,200 | Typically ~1,000; max capped at 2,000 |
| **Total tokens per call** | **~2,380** | |

### When is this called?

- **Once per form submission** when `use_live = True`.
- A brand-new session (first-time user clicking "Generate My Learning Plan") = 1 API call.
- Returning user reloading a saved profile = **0 API calls** (loaded from SQLite).
- Demo mode (default) = **0 API calls** every time.

---

## 4. MS Learn Catalog API — Intentionally Offline

### Stub location

```
src/cert_prep/b1_1_learning_path_curator.py  ·  line 12
────────────────────────────────────────────────────────
# Reference: GET https://learn.microsoft.com/api/catalog/?locale=en-us&type=modules
# (not called in this build — catalogue is hardcoded for 5 supported exams)
```

### Why not called

The `_LEARN_CATALOGUE` dict (line 58) contains manually curated MS Learn modules
for 5 exams (AI-102, DP-100, AZ-900, AZ-104, DP-900). This was a deliberate demo
decision — the catalog endpoint is public and free, but calling it on every form
submit would add latency (~500 ms) and create a runtime dependency on an external URL.

### Cost impact

**Zero.** The MS Learn Catalog API is free to call. There is no key, no token, no billing.

### When to activate it

For production, replace the `_LEARN_CATALOGUE` dict with a cached API call:

```python
import httpx, functools

@functools.lru_cache(maxsize=1)
def fetch_ms_learn_catalogue() -> dict:
    """Cached at process startup — refreshed only on server restart."""
    url = "https://learn.microsoft.com/api/catalog/?locale=en-us&type=modules"
    return httpx.get(url, timeout=10).json()
```

Cache it at module import time so the API is called once per server restart,
not once per learner.

---

## 5. Azure AI Content Safety — Not Yet Integrated

### Current state

Guardrail `G-16` in `src/cert_prep/guardrails.py` uses a Python keyword list heuristic:

```python
_HARMFUL_KEYWORDS = {"hack", "exploit", "bypass", "jailbreak", ...}
```

This is a blocklist check — it catches obvious abuse but misses nuanced harmful content.

### Cost if integrated

Azure AI Content Safety is priced at **$1.00 per 1,000 text records**.  
One `check_input()` call per form submit → at 1,000 students/month = **$1.00/month**.

### Recommendation

> Add Content Safety only if deploying publicly or handling untrusted input at scale.
> For a demo or internal tool, the heuristic G-16 is sufficient.
> When you do integrate it, call it **once** on the raw free-text fields (`background_text`,
> `goal_text`) only — not on structured dropdown values.

---

## 6. Azure AI Search — Not Yet Integrated

### Current state

`src/cert_prep/b2_assessment_agent.py` uses a 30-item in-memory Python list as the
question bank for each exam. Assessment questions are generated at import time from
a `_QUESTION_BANK` dict — no vector search, no index.

### When to consider it

Only needed if the question bank grows beyond ~500 questions per exam, or if you
want semantic retrieval (e.g. "show me a question similar to this one").

### Cost

Azure AI Search starts at **~$73/month** for the Basic tier. Not justified until the
Q-bank has thousands of records needing fast retrieval.

---

## 7. SQLite — Local, Zero Cloud Cost

### Where it's used

| Operation | File | Triggered when |
|-----------|------|----------------|
| `upsert_student()` | `src/cert_prep/database.py` | Every form submit |
| `save_profile()` | `src/cert_prep/database.py` | Every form submit |
| `save_plan()` | `src/cert_prep/database.py` | After StudyPlanAgent |
| `save_learning_path()` | `src/cert_prep/database.py` | After LearningPathCuratorAgent |
| `save_trace()` | `src/cert_prep/database.py` | If mock trace exists |
| Load returning user | `streamlit_app.py` | On page load (session cookie match) |

SQLite is a local file on the app server — **zero cloud cost, zero latency**.

### Scale limit

SQLite handles concurrent reads easily but serialises writes. For >10 simultaneous
users submitting forms, consider migrating to Azure SQL Serverless or Cosmos DB
(use the serverless tier, pay per RU not per hour).

---

## 8. SMTP / Email Dispatch — Optional, Env-Gated

### Location

```
src/cert_prep/b1_2_progress_agent.py  ·  lines 546–590
Function: attempt_send_email(to_address, subject, html_body, config)
```

### Env vars required

```
SMTP_HOST  (default: smtp.gmail.com)
SMTP_PORT  (default: 587)
SMTP_USER  – sender login
SMTP_PASS  – app password (not main password)
SMTP_FROM  – display From address
```

If these are absent, `attempt_send_email()` returns `False` silently — no crash,
no cost. Email is only triggered from the **My Progress** tab when a student
explicitly requests a weekly summary.

### Cost

Free if using Gmail SMTP or Microsoft 365 SMTP.  
If you later swap this to **Azure Communication Services Email**, cost is
$0.00025 per email — negligible.

---

## 9. Real Cost Estimates

### Scenario: Demo / internal workshop (default `use_live = False`)

| Item | Cost |
|------|------|
| Azure OpenAI | **$0.00** |
| MS Learn API | **$0.00** |
| Content Safety | **$0.00** |
| SQLite / storage | **$0.00** |
| **Total** | **$0.00 / month** |

---

### Scenario: Live deployment — `use_live = True`, GPT-4o (current default model)

Pricing reference: GPT-4o on Azure OpenAI  
- Input: **$2.50 per 1M tokens**  
- Output: **$10.00 per 1M tokens**

| Sessions / month | Input tokens | Output tokens | Input cost | Output cost | **Total** |
|-----------------|-------------|--------------|------------|-------------|-----------|
| 100 | 138,000 | 100,000 | $0.35 | $1.00 | **$1.35** |
| 500 | 690,000 | 500,000 | $1.73 | $5.00 | **$6.73** |
| 1,000 | 1,380,000 | 1,000,000 | $3.45 | $10.00 | **$13.45** |
| 5,000 | 6,900,000 | 5,000,000 | $17.25 | $50.00 | **$67.25** |
| 10,000 | 13,800,000 | 10,000,000 | $34.50 | $100.00 | **$134.50** |

_Assumes ~1,380 input tokens and ~1,000 output tokens per profiling call._

---

### Scenario: `use_live = True` with GPT-4o-mini (recommended swap)

Pricing: GPT-4o-mini  
- Input: **$0.15 per 1M tokens**  
- Output: **$0.60 per 1M tokens**

| Sessions / month | Input cost | Output cost | **Total** | **Saving vs GPT-4o** |
|-----------------|------------|-------------|-----------|----------------------|
| 100 | $0.021 | $0.060 | **$0.08** | 94% cheaper |
| 1,000 | $0.21 | $0.60 | **$0.81** | 94% cheaper |
| 5,000 | $1.04 | $3.00 | **$4.04** | 94% cheaper |
| 10,000 | $2.07 | $6.00 | **$8.07** | 94% cheaper |

---

### Scenario: Add response caching (50% cache-hit rate assumed)

If 50% of learners share the same exam + similar background category, cached profiles
can be reused:

| Sessions / month | Cached | LLM calls | GPT-4o-mini cost |
|-----------------|--------|-----------|-----------------|
| 1,000 | 500 | 500 | **$0.41** |
| 5,000 | 2,500 | 2,500 | **$2.02** |
| 10,000 | 5,000 | 5,000 | **$4.04** |

---

## 10. Recommendations — Where to Use, Where NOT to Use

### ✅ Keep Azure OpenAI for profiling — but optimise it

The **only** place an LLM is genuinely needed is `LearnerProfilingAgent._call_llm()`.
The input is unstructured free text (background, goal, concerns) that cannot be mapped
to structured fields by simple rules alone. This is the right use case.

**Do these three things to cut cost by 90%+:**

#### Rec 1 — Switch from GPT-4o to GPT-4o-mini

> The profiling task is structured JSON extraction from short free-text (~200 words).
> This does **not** require GPT-4o quality reasoning. GPT-4o-mini handles it reliably
> and costs **16–17× less**.

Change in `src/cert_prep/config.py`:
```python
# Before
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

# After
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
```

#### Rec 2 — Add a profile response cache

> Two students with the same exam target, same background category (e.g. "Python developer,
> 3 years"), and same cert holdings will produce near-identical profiles. Cache by a
> hash of `(exam_target, background_category, existing_certs_sorted, hours_per_week_bucket)`.

```python
import hashlib, json

def _cache_key(raw: RawStudentInput) -> str:
    bucket = {"1-5": "low", "6-10": "mid", "11+": "high"}.get(
        str(int(raw.hours_per_week)), "mid"
    )
    payload = {
        "exam": raw.exam_target,
        "certs": sorted(raw.existing_certs),
        "hrs": bucket,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
```

Store the cache in SQLite alongside the profile — no extra service needed.

#### Rec 3 — Reduce `max_tokens` from 2,000 to 1,200

> Actual output for the profile schema is consistently 800–1,100 tokens.
> Setting `max_tokens=1200` reduces the worst-case output billing without
> truncating valid responses.

```python
# In b0_intake_agent.py _call_llm()
max_tokens = 1200,   # was 2000
```

---

### ❌ Do NOT use Azure OpenAI for downstream agents

The following agents are currently deterministic Python and **must stay that way**:

| Agent | Why no LLM needed |
|-------|------------------|
| `StudyPlanAgent` | Arithmetic: allocate hours across phases by weight |
| `LearningPathCuratorAgent` | Lookup table: match domain_id → catalogue modules |
| `ProgressAgent` | Scoring formula: (hours_spent / budget) × 100 |
| `AssessmentAgent` | Random sample from a Q-bank dict — pure Python |
| `CertRecommendationAgent` | Decision tree: score × weight → recommendation |
| `GuardrailsPipeline` | Pattern matching, range checks, keyword lists |

Using GPT-4o for any of these would be engineering waste — they produce **better,
faster, cheaper, and auditable results** as pure Python.

---

### ❌ Do NOT call MS Learn API on every form submit

The catalog changes at most once a month. Fetch it once at server startup and cache
it in memory (or in SQLite with a 24-hour TTL). This eliminates an external
dependency at the most latency-sensitive moment (form submission).

---

### 🔶 Add Azure AI Content Safety only when going public

The current G-16 heuristic is adequate for internal demos. When deploying to
untrusted end users:

1. Call `ContentSafetyClient.analyze_text()` on `background_text` + `goal_text` only.
2. Reject only if `hate`, `violence`, or `self_harm` categories score ≥ `medium`.
3. **Do not** call it on structured fields (dropdowns, sliders, cert codes) — those cannot
   contain harmful content by construction. This limits the call to 2 text fields per
   submission, keeping cost at ~$1/1,000 submissions.

---

### 🔶 Upgrade SMTP to Azure Communication Services for production scale

The current Gmail SMTP fallback is fine for demos. For production:
- Use ACS Email (verified domain, delivery receipts, bounce handling).
- Cost: $0.00025/email (~$2.50 per 10,000 emails) — negligible.
- Change in `b1_2_progress_agent.py`: swap `smtplib` calls for `azure.communication.email`.

---

### Cost optimisation — priority-ordered action list

| Priority | Action | Effort | Monthly saving at 1,000 sessions |
|----------|--------|--------|----------------------------------|
| 🥇 High | Switch to GPT-4o-mini | 1 line in `config.py` | ~$12.64 saved |
| 🥇 High | Keep `use_live=False` in demo/workshop contexts | Config only | ~$13.45 saved |
| 🥈 Medium | Add profile response cache (SQLite) | ~1 day | ~$3–6 at 30% hit rate |
| 🥈 Medium | Reduce `max_tokens` 2000 → 1200 | 1 line | ~$2–4 saved |
| 🥉 Low | Trim system prompt (remove redundant domain desc) | ~2 hours | ~$0.50 saved |
| 🥉 Low | Activate MS Learn API with process-level cache | ~1 day | $0 (free API) |
| — | Add Content Safety (public launch only) | ~1 day | Adds ~$1/1,000 users |

---

*Generated: 2026-02-22 · Source: manual code audit of `streamlit_app.py`, `src/cert_prep/b0_intake_agent.py`, `b1_1_learning_path_curator.py`, `b1_2_progress_agent.py`, `guardrails.py`, `config.py`.*
