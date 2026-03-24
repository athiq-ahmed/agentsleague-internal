# Q&A Playbook — CertPrep MAF

> **Audience:** Competition judges, technical reviewers  
> **Last updated:** 2026-03-24

This playbook provides authoritative answers to expected judge questions about the CertPrep MAF system.

---

## Agent Architecture

**Q: Is this really multi-agent or just one big prompt?**  
A: 7 separate `Agent(client=AzureAIClient)` objects, each with its own versioned system prompt (`.md` file), its own tool set, and its own middleware stack. They are independently callable and unit-testable. The `WorkflowBuilder` wires them with typed edges and HITL executors — no shared monolithic prompt exists.

**Q: Why use WorkflowBuilder instead of a single supervisor agent?**  
A: `WorkflowBuilder` gives us three things a supervisor agent cannot: (1) typed, auditable edge routing; (2) HITL gates that suspend the workflow and resume after real human input; (3) `FileCheckpointStorage` that serialises pipeline state to disk — the workflow survives browser closes and Streamlit restarts.

**Q: How does HandoffBuilder differ from WorkflowBuilder?**  
A: `HandoffBuilder` is the outer conversational shell — a lightweight `TriageAgent` that greets the user and hands off to the `CertPrepWorkflow` (WorkflowBuilder pipeline) when an exam intent is detected. `WorkflowBuilder` is the deterministic inner pipeline that runs all 7 specialist agents.

**Q: What does the OrchestratorAgent actually do?**  
A: It reads session state and implements 6 routing rules defined in `prompts/orchestrator.md`. It routes new learners to ProfilerAgent, triggers study plan + path curation for learners without a plan, sends returning learners to ProgressAgent, escalates to AssessmentAgent when score ≥ 0.45, and routes to CertRecommendationAgent on a GO verdict.

---

## Microsoft Agent Framework (MAF)

**Q: Which MAF patterns are used?**  
A: All four core patterns: (1) `WorkflowBuilder` — primary sequential pipeline with fan-out; (2) `HandoffBuilder` — outer conversational triage; (3) `FileCheckpointStorage` — HITL state persistence; (4) 3 middleware types — `AgentContextMiddleware`, `FunctionContextMiddleware`, `ChatContextMiddleware`.

**Q: What version of MAF is used?**  
A: `agent-framework-core==1.0.0b260212` and matching versions of the azure-ai, orchestrations, devui, and chatkit packages (all `1.0.0b260212`).

**Q: How is `BaseContextProvider` used?**  
A: `LearnerProfileProvider(BaseContextProvider)` is registered on all 7 agents. Its `before_run()` method injects learner name, exam target, experience level, learning style, confidence average, risk domains, and skip domains into the agent context before every run — eliminating the need to pass context through every tool call parameter.

---

## MCP Integration

**Q: How is MCP used?**  
A: `MCPStreamableHTTPTool(url="https://learn.microsoft.com/api/mcp")` is registered as a tool on `PathCuratorAgent`. The agent calls it up to 12 times (enforced by `ToolCallLimiterMiddleware`) to search for modules by exam domain and learning style. All returned URLs are validated against a trusted-domain allowlist (G-17): `learn.microsoft.com`, `docs.microsoft.com`, `aka.ms`.

**Q: What happens if the MCP endpoint is unavailable?**  
A: The `PathCuratorAgent` returns whatever modules it collected before the failure. The `ToolCallLimiterMiddleware` will also raise if the cap is hit. In both cases, the workflow continues with partial results rather than failing the entire session.

**Q: Why cap MCP calls at 12?**  
A: Each MCP call is an outbound HTTP request with non-trivial latency (100–500ms). 12 calls × 5 domains = sufficient coverage at ~2 modules per domain while keeping PathCuratorAgent latency under 6 seconds.

---

## Guardrails & Safety

**Q: How do you prevent hallucinations?**  
A: Three mechanisms: (1) `InputGuardrailsMiddleware` — 17-rule `GuardrailsPipeline` from foundry-sdk runs before every agent; BLOCK raises before the LLM is invoked. (2) Structured JSON output — agents are instructed to return JSON matching typed model schemas. (3) URL allowlisting (G-17) — `OutputPIIMiddleware` and `PathCuratorAgent` prompt both block URLs not from `learn.microsoft.com`, `docs.microsoft.com`, or `aka.ms`.

**Q: What is the HITL value-add? Why not just ask the LLM?**  
A: The LLM cannot know how the learner actually felt studying or verify hours claimed. Gate 1 captures self-reported readiness and suspends the pipeline until the learner explicitly decides whether to take the assessment. Gate 2 collects quiz answers from the real human before scoring — the model cannot pre-fill these. Without HITL gates, the system would recommend based entirely on background text with no feedback loop.

**Q: What guardrail rules are active?**

| Rule | Level | Trigger |
|------|-------|---------|
| G-01 | BLOCK | Empty/whitespace input |
| G-02 | BLOCK | Input > 2000 characters |
| G-03 | WARN | Non-UTF-8 characters |
| G-04 | BLOCK | Unknown exam code |
| G-05 | WARN | Hours/week > 40 |
| G-06 | BLOCK | Study plan > 110% of budget |
| G-07 | WARN | All confidence scores = 0 |
| G-08 | BLOCK | Negative study hours |
| G-09 | BLOCK | Domain with 0 hours in plan |
| G-10 | WARN | Empty learning path |
| G-11 | BLOCK | Quiz fewer than 3 questions |
| G-12 | WARN | All quiz answers identical |
| G-13 | BLOCK | Score calculation overflow |
| G-14 | WARN | GO verdict with score < 60% |
| G-15 | BLOCK | Next cert not in known registry |
| G-16 | BLOCK/WARN | PII / harmful content (Azure Content Safety + regex fallback) |
| G-17 | BLOCK | URL outside approved domains |

---

## Algorithms

**Q: Why Largest Remainder for study plan allocation?**  
A: It guarantees every available study day is allocated to exactly one domain with no rounding loss. The algorithm: compute fractional day quotas from domain weights, take the floor (min 1), then award +1 to the top-k remainder fractions until all days are distributed. Standard round-to-nearest loses days when total_days is not divisible by domain count. LR is O(n log n) and produces provably optimal integer allocations.

**Q: What is the ReadinessScore formula?**  
A:
```
0.55 × avg_confidence
+ 0.25 × min(hours_logged / budget_hours, 1.0)
+ 0.20 × (practice_tests_passed / practice_tests_total)
```
Weights reflect: self-reported domain confidence is the strongest predictor; hours utilisation matters but is capped at 1.0; practice test completion adds a modest signal.

**Q: What does the SYNERGY_MAP provide?**  
A: It maps each completed exam to 2–3 complementary next certifications based on skill overlap. For example, AI-102 → DP-100 (deeper ML) and AZ-305 (solution architecture for AI workloads). The map keeps recommendations opinionated and concise rather than listing all Microsoft certs.

---

## Scalability & Deployment

**Q: Can this scale beyond one learner?**  
A: Yes. `FileCheckpointStorage` uses per-session files — each session ID gets its own isolated checkpoint. Replacing `FileCheckpointStorage` with an Azure Cosmos DB-backed implementation (Phase 2 roadmap) requires changing only the storage constructor.

**Q: What is the deployment path?**  
- **Current:** Streamlit + local FileCheckpointStorage
- **Phase 2:** Azure Container Apps + Cosmos DB checkpoint storage + Key Vault
- **Phase 3:** Multi-tenant isolation, AI Foundry evaluation harness, Azure AI Search MCP fallback

**Q: Where is agent latency measured?**  
A: Each agent span is emitted to Azure Application Insights via `configure_otel_providers()`. The `SERVICE_NAME=certprep-maf` tag appears on all spans. Per-agent latency is visible in Application Insights → Transaction search → filter by `certprep-maf`.

---

## Data Models

**Q: Where do the data models live?**  
A: All models (`LearnerProfile`, `StudyPlan`, `LearningPath`, `ProgressSnapshot`, `ReadinessAssessment`, `AssessmentResult`, `CertRecommendation`) are defined in `agentsleague-foundry-sdk/src/cert_prep/models.py`. They are imported via a `sys.path` injection in `src/maf/__init__.py` — no duplication.

**Q: Are models typed?**  
A: Yes — Python dataclasses with full field-level typing. The foundry-sdk models include `_dc_filter()` helpers that silently drop unknown keys on deserialization, making them forward-compatible with schema evolution.
