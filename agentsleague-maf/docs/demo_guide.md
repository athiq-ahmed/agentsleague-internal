# Demo Guide — CertPrep MAF

> **Audience:** Competition judges, live demo presenters  
> **Duration:** 5–8 minutes  
> **Last updated:** 2026-03-24

---

## Pre-Demo Checklist

```bash
# 1. Confirm environment
python -m py_compile streamlit_app.py src/maf/agents/*.py src/maf/workflow/*.py

# 2. Confirm .env is filled with live Azure credentials
grep -c "AZURE_AI_PROJECT_CONNECTION_STRING=" .env   # should be 1, not empty

# 3. Kill any stale port 8501 process (macOS/Linux)
lsof -ti:8501 | xargs kill -9 2>/dev/null; echo "Port clear"

# 4. Launch
streamlit run streamlit_app.py
```

Open `http://localhost:8501`.

---

## Demo Flow (5-Minute Version)

### Segment 1 — New Learner Setup (90 sec)

Start with an empty session (use the **🔄 New Session** button in the sidebar).

Type in the chat:
> "I want to prepare for AI-102. I'm a cloud developer, 3 years Python, never used Azure AI before. I have 10 hours per week for 8 weeks."

**What to highlight to judges:**
- TriageAgent greeting and handoff trigger (`start_cert_prep_workflow`)
- ProfilerAgent eliciting structured learner data from free text
- OrchestratorAgent routing to StudyPlan + PathCurator fan-out

Wait for the study plan and MS Learn modules to appear. Point out:
- "The StudyPlanAgent uses the Largest Remainder algorithm — no rounding loss"
- "PathCuratorAgent made live calls to `learn.microsoft.com/api/mcp` — these are real module titles and URLs"

---

### Segment 2 — Progress Check + HITL Gate 1 (90 sec)

Type:
> "I've studied for 5 weeks, 50 hours total. My confidence is now around 0.65 on average across all domains."

**What to highlight:**
- ProgressAgent formula (`0.55 × confidence + 0.25 × hours_util + 0.20 × practice`)
- The HITL pause: show the "A or B?" prompt appearing in the chat
- Explain: "This is Gate 1 — the workflow is suspended, waiting for real learner input. The checkpoint is saved to disk."

Type: `A`

---

### Segment 3 — Quiz + HITL Gate 2 (90 sec)

**What to highlight:**
- AssessmentAgent generating domain-weighted questions at temperature 0.7
- "Gate 2: workflow suspended again — answers are collected before scoring"
- Show the formatted quiz markdown

Answer the quiz (you can use pre-prepared answers for speed), then show the scoring result and ReadinessRouter routing decision.

---

### Segment 4 — Certification Recommendation (60 sec)

After a GO verdict, show CertRecommendationAgent output:
- Decision badge (GO / CONDITIONAL / NOT YET)
- SYNERGY_MAP next-cert suggestions
- Motivational note

---

### Segment 5 — Live MAF Observability (optional, 60 sec)

Open Azure Application Insights in the portal. Go to **Live Metrics** or **Transaction search** and show:
- Spans for each agent invocation
- `certprep-maf` service name on all spans
- Latency per agent step

---

## Extended Demo Scenarios

### Demo B — Guardrail Block (G-16 PII)

Type:
> "My SSN is 123-45-6789, I want to prepare for AZ-900."

Show the BLOCK response. Highlight that:  
- No agent was invoked
- InputGuardrailsMiddleware caught it during `before_run()`
- The pipeline never started

### Demo C — NOT_READY Remediation Loop

Use these answers to score below 60%:
- Answer all questions: `A` (most will be wrong)
- ReadinessScore < 60% → NOT_READY
- ReadinessRouter routes back to StudyPlanAgent
- Show the rebuilt plan focusing on weak domains

### Demo D — MCP URL Trust Check

Tell the judge: "PathCuratorAgent only accepts URLs from three trusted domains." 

Show `path_curator.md` prompt rule: `learn.microsoft.com`, `docs.microsoft.com`, `aka.ms`.  
Explain that G-17 in the middleware blocks any hallucinated or external URL.

---

## Talking Points for Judges

**"Is this really multi-agent or just one big prompt?"**  
Each of the 7 agents is a separate `Agent(client=AzureAIClient)` object with its own versioned system prompt (.md file), its own set of tools, and its own context provider injection. They are independently runnable and testable.

**"How does the MAF framework differ from the previous foundry-sdk version?"**  
The foundry-sdk version had a single `streamlit_app.py` with 200+ lines of hand-coded if/else orchestration. MAF replaces that entirely with `WorkflowBuilder` — typed edges, fan-out, HITL executors, and checkpoint storage — all declarative.

**"What happens if the learner closes the browser mid-quiz?"**  
`FileCheckpointStorage` serialises the full `WorkflowContext` to disk. The `pending_quiz` and `quiz_answers` states survive the browser close. With a URL-persisted session ID (Phase 2 roadmap), the learner would land back exactly at Gate 2.

**"Why not just use a single GPT-4o call with a long system prompt?"**  
Five structural advantages: (1) Per-agent expertise — each agent has a focused, versioned prompt. (2) Testable isolation — each agent's input/output contract is individually unit-testable. (3) HITL gates — the WorkflowBuilder suspends mid-pipeline; a single call cannot do this. (4) Per-step guardrails — middleware fires on every agent, not once at the start. (5) OTEL tracing — per-agent latency is measured separately.

---

## Demo Reset

To start a completely clean demo:
1. Click **🔄 New Session** in the sidebar
2. Delete checkpoint files: `rm -rf ~/.certprep_maf/checkpoints/`
3. You are ready for the next demo run
