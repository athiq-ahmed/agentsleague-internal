# User Flow — CertPrep MAF

> **Format:** Prose scenario walkthroughs  
> **Last updated:** 2026-03-24

Each scenario describes a realistic learner journey through the MAF pipeline, including the HITL gate interactions and agent handoffs.

---

## S1 — New Learner, First-Time Setup (AI-102)

Alex opens the app and types:
> "I'd like to prepare for the AI-102 exam. I'm a software developer with 3 years of Python experience but I've never used Azure AI services."

**TriageAgent** greets Alex, identifies the exam target (`AI-102`), and calls `start_cert_prep_workflow()` to hand off to the workflow.

**OrchestratorAgent** detects no profile exists for this session and routes to **ProfilerAgent**.

**ProfilerAgent** asks Alex:
1. Preferred learning style? → "I prefer hands-on labs."
2. Per-domain confidence on a 0–1 scale for: Azure AI Services, Computer Vision, NLP, Knowledge Mining, Generative AI?
3. How many hours per week can you study? → "10 hours, for 8 weeks."
4. Any existing certifications? → "AZ-900"

Agent builds and returns a `LearnerProfile` JSON with `preferred_style=LAB_FIRST`, `existing_certs=["AZ-900"]`, and per-domain confidence scores.

**OrchestratorAgent** routes to **StudyPlanAgent** + fan-out to **PathCuratorAgent**.

**StudyPlanAgent** uses `get_exam_domains("AI-102")` to get the domain blueprint, then applies the Largest Remainder Method to allocate 80 total hours (10 hrs × 8 weeks) across 5 domains. Weak domains get earlier placement.

In parallel, **PathCuratorAgent** searches MS Learn:
- `MCPStreamableHTTPTool` query: `"AI-102 Azure AI Vision hands-on"` → returns 3 modules
- Repeats for each of the 5 domains (up to 12 MCP calls total)
- Returns a curated `LearningPath` with URLs from `learn.microsoft.com`

Alex receives the study plan and learning path in the chat.

---

## S2 — Returning Learner, Progress Check

Alex returns after 3 weeks of studying:
> "I've completed the Computer Vision modules and spent about 27 hours. My confidence in that domain is now 0.8."

**OrchestratorAgent** detects an existing profile and routes to **ProgressAgent**.

**ProgressAgent** calls `compute_readiness_score`:
- `avg_confidence = 0.52` (weighted, 1 domain improved)
- `hours_util = 27/80 = 0.34`
- `practice_ratio = 0.0` (no practice tests yet)
- `ReadinessScore = 0.55 × 0.52 + 0.25 × 0.34 + 0.0 = 0.37` → **NOT_READY**

Agent replies:
> "Your readiness score is 37% — NOT_READY. Keep going! Focus next on NLP and Knowledge Mining."

No HITL gate fires (score < 0.45). Routes back to OrchestratorAgent.

---

## S3 — HITL Gate 1 Triggered (ProgressGateway)

After 5 weeks, Alex returns again:
> "I've now spent 52 hours total. My confidence across all domains has improved — I'd say 0.65 average."

**ProgressAgent** computes:
- `ReadinessScore = 0.55 × 0.65 + 0.25 × 0.65 + 0.0 = 0.52` → **PROGRESSING**

Score ≥ 0.45 → **ProgressGateway fires (HITL Gate 1)**.

Workflow pauses and presents:
> "You've reached a readiness score of **52%** (PROGRESSING).
> Would you like to:
> - **A** — Take a practice assessment now  
> - **B** — Continue studying"

Alex types: `A`

**ProgressGateway** routes to **AssessmentAgent**. State is checkpointed.

---

## S4 — HITL Gate 2 (QuizGateway) — Quiz Administration

**AssessmentAgent** generates a 12-question domain-weighted quiz for AI-102.

**QuizGateway fires (HITL Gate 2)** — workflow pauses and presents the quiz:

> "Here is your **12-question practice quiz** for AI-102.
>
> **Q1.** Which Azure service provides optical character recognition (OCR)?  
>    A. Azure Translator  
>    B. Azure AI Vision  
>    C. Azure Cognitive Search  
>    D. Azure Speech"

Alex answers all 12 questions, one per line:
```
B
A
C
...
```

**QuizGateway** stores answers in `ctx.state["quiz_answers"]` and routes back to **AssessmentAgent** for scoring.

Scoring result: 9/12 correct = 75% → **CONDITIONAL**

**ReadinessRouter** detects CONDITIONAL and routes to **PathCuratorAgent** with `weak_domains=["knowledge_mining", "generative_ai"]`.

---

## S5 — Remediation Loop

**PathCuratorAgent** searches MS Learn specifically for the 2 weak domains:
- `"AI-102 knowledge mining certification"` → 2 modules
- `"AI-102 Azure OpenAI generative AI"` → 3 modules

Alex receives a focused 2-domain remediation module list.

After 2 more weeks, Alex reports progress again. This time ReadinessScore reaches 0.71, HITL Gate 1 fires again, Alex takes the quiz again, scores 88% → **GO** verdict.

**ReadinessRouter** routes to **CertRecommendationAgent**.

---

## S6 — Final Certification Recommendation

**CertRecommendationAgent** evaluates:
- overall_pct = 88% ≥ 80%, all domains ≥ 65% → **GO**
- Calls `get_next_cert_suggestions("AI-102")` → `["DP-100", "AZ-305"]`

Alex receives:
> "🎉 **Recommendation: GO!**
> You're ready to book AI-102. Your score of 88% is strong across all 5 domains.
>
> **Next certifications to consider:**
> - **DP-100** — Complements AI-102 with a deeper ML engineering focus.
> - **AZ-305** — Strengthens solution architecture for AI workloads on Azure.
>
> **Schedule your exam within 2 weeks to keep momentum!**"

---

## S7 — PII Input Blocked (InputGuardrailsMiddleware)

A learner types:
> "My SSN is 123-45-6789, can you build a plan for AZ-900?"

**InputGuardrailsMiddleware** (`AgentContextMiddleware`) fires during `before_run()`:
- G-16 PII pattern scan matches SSN regex `\d{3}-\d{2}-\d{4}`
- Action: **BLOCK** — raises `ValueError` before any agent runs

Learner sees:
> "⚠️ Your message contains sensitive personal information (SSN pattern detected). Please remove it and try again."

No agent is invoked. No data is logged.

---

## S8 — MCP Call Limit Enforced (ToolCallLimiterMiddleware)

**PathCuratorAgent** begins searching MS Learn. The prompt instructs up to 12 calls.

**ToolCallLimiterMiddleware** (`FunctionContextMiddleware`) tracks each `MCPStreamableHTTPTool` invocation. On the 13th call attempt, the middleware raises an exception and the agent is forced to return with the modules collected so far.

This prevents runaway MCP usage and keeps latency predictable.

---

## S9 — Session Resumed After Browser Close

Alex closes the browser during HITL Gate 2 (quiz is on screen, waiting for answers).

When Alex reopens the app:
- `session_id` is not in `st.session_state` → new session is created
- **Limitation (current build):** The session ID is not persisted in the browser — Alex must manually enter or bookmark the session ID to resume mid-HITL.
- `FileCheckpointStorage` has the `pending_quiz` state saved — it can be restored if the session ID is known.

> **Roadmap:** Browser-side session persistence (LocalStorage or URL param) is planned as a production enhancement.

---

## S10 — Unknown Exam Code

A learner types: `"I want to prepare for SC-400."`

**OrchestratorAgent** routes to **ProfilerAgent** → **StudyPlanAgent**.

`get_exam_domains("SC-400")` returns:
```json
{"error": "No blueprint found for SC-400. Use AI-102, DP-100, or AZ-900."}
```

**StudyPlanAgent** replies to the learner:
> "SC-400 is not yet in our blueprint catalogue. I can prepare plans for AI-102, DP-100, or AZ-900. Which would you like?"

OrchestratorAgent holds until the learner selects a supported exam.
