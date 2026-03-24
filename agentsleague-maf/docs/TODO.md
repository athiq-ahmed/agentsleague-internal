# 📋 Project TODO — CertPrep MAF

> **Owner:** Athiq Ahmed  
> **Project:** Microsoft Certification Prep — MAF Upgrade  
> **Track:** Reasoning Agents with Microsoft Foundry  
> **Last updated:** 2026-03-24

---

## 1️⃣ Azure Services to Enable

### A. Azure AI Foundry ⭐ (Required)

| Setting | Value |
|---------|-------|
| **Hub name** | `hub-agentsleague` |
| **Project name** | `certprep-maf` |
| **Region** | East US 2 or Sweden Central |
| **Connected service** | Link your Azure OpenAI resource (gpt-4o) |

**How to set up:**
1. Go to [ai.azure.com](https://ai.azure.com) → **Create project**
2. Create or select a Hub → name the project `certprep-maf`
3. Under **Connected resources** → attach Azure OpenAI resource
4. **Settings** → copy the **Project Connection String**
5. Add to `.env`:
   ```
   AZURE_AI_PROJECT_CONNECTION_STRING=<your-connection-string>
   AZURE_AI_MODEL_DEPLOYMENT=gpt-4o
   ```

- [ ] Hub + Project created
- [ ] OpenAI resource connected
- [ ] Connection string added to `.env`
- [ ] `pip install -r requirements.txt` run successfully

---

### B. Azure OpenAI (gpt-4o)

| Setting | Value |
|---------|-------|
| **Resource name** | `aoai-agentsleague` |
| **Region** | East US 2 |
| **Model** | `gpt-4o` (version `2024-11-20`) |
| **Deployment name** | `gpt-4o` |
| **TPM quota** | 30K tokens/min |

- [ ] Resource created
- [ ] gpt-4o model deployed
- [ ] Keys added to `.env`

---

### C. Azure Application Insights (Optional — OTEL tracing)

| Setting | Value |
|---------|-------|
| **Resource name** | `certprep-maf-insights` |
| **Region** | East US 2 |

```bash
az monitor app-insights component create \
  --app certprep-maf-insights \
  --resource-group rg-agentsleague \
  --location eastus2
```

Copy connection string → add to `.env`:
```
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=...
```

- [ ] Resource created
- [ ] Connection string in `.env`
- [ ] Spans visible in portal (Transaction search → `certprep-maf`)

---

### D. Azure Content Safety (Optional — G-16 upgrade)

Regex-based G-16 is active by default. For the live Azure Content Safety API:

```
AZURE_CONTENT_SAFETY_ENDPOINT=https://<name>.cognitiveservices.azure.com
AZURE_CONTENT_SAFETY_KEY=<key>
```

- [ ] Resource created (F0 free tier sufficient for dev)
- [ ] Endpoint and key added to `.env`

---

### E. MS Learn MCP Endpoint

Public endpoint — no Azure resource needed.

Default: `https://learn.microsoft.com/api/mcp`

To override: `MCP_MSLEARN_URL=https://learn.microsoft.com/api/mcp` in `.env`

- [x] `MCPStreamableHTTPTool` wired in `PathCuratorAgent`
- [x] `ToolCallLimiterMiddleware` caps calls at 12
- [ ] Verify live endpoint returns modules in demo environment

---

## 2️⃣ Development Tasks

### 🔴 Must Do (Before Submission)

- [ ] **Fill real Azure credentials** in `.env` — app requires `AZURE_AI_PROJECT_CONNECTION_STRING`
- [ ] **End-to-end smoke test** — run `streamlit run streamlit_app.py` and complete one full session (profiling → plan → progress → assessment → recommendation)
- [ ] **Verify MCP integration** — confirm PathCuratorAgent returns real MS Learn module titles (not empty)
- [ ] **Verify HITL Gate 1** — walk through the A/B prompt and confirm checkpoint saves to `~/.certprep_maf/checkpoints/`
- [ ] **Verify HITL Gate 2** — walk through quiz, confirm scores are computed correctly
- [ ] **Create tests/ folder** — implement unit tests against `docs/unit_test_scenarios.md`

### 🟡 Should Do (Strengthens Submission)

- [ ] **Wire Application Insights** — confirm agent spans appear in portal
- [ ] **Add DP-100 exam to demo flow** — test PathCuratorAgent with DP-100 domains
- [ ] **Record demo video** (3–5 min) showing:
  - New learner flow through all 7 agents
  - HITL Gate 1 and Gate 2 pauses
  - MS Learn module search result
  - Final GO recommendation with SYNERGY_MAP
- [ ] **Add AZ-204 and AZ-305 blueprints** to `_EXAM_BLUEPRINTS` in `study_plan_agent.py`

### 🟢 Nice to Have

- [ ] Deploy to Azure Container Apps
- [ ] Replace `FileCheckpointStorage` with Cosmos DB-backed storage
- [ ] Add Streamlit URL-param session ID persistence (so browser close doesn't lose HITL state)
- [ ] Add `azure-ai-evaluation` eval harness for per-agent coherence/relevance metrics
- [ ] Add DP-420, AZ-500 exam blueprints to expand catalogue

---

## 3️⃣ Cost Estimate (Monthly)

| Service | Tier | Est. Cost |
|---------|------|-----------|
| Azure OpenAI (gpt-4o) | ~50K tokens/day | ~$10–25/mo |
| Azure AI Foundry | Free project tier | $0 |
| Application Insights | < 1GB/day | ~$0–5/mo |
| Content Safety | F0 free tier | $0 |
| MS Learn MCP | Public free endpoint | $0 |
| **Total dev/test** | | **~$10–30/mo** |

> 💡 Set a **budget alert at $50** in Cost Management.

---

## ✅ Completed

- [x] `agentsleague-maf/` folder created
- [x] `requirements.txt` with pinned MAF packages (`1.0.0b260212`)
- [x] `.env.sample` template
- [x] `src/maf/__init__.py` with sys.path bootstrap
- [x] `src/maf/learner_profile_provider.py` — `BaseContextProvider` implementation
- [x] `src/maf/handoff_tools.py` — 7 `@tool` handoff functions
- [x] `src/maf/guardrails_middleware.py` — 3 MAF middleware types wrapping 17-rule GuardrailsPipeline
- [x] `src/maf/otel.py` — OTEL + Azure Monitor configuration
- [x] 7 versioned prompt `.md` files (orchestrator, profiler, study_plan, path_curator, progress, assessment, cert_recommendation)
- [x] 7 MAF Agent builder classes
- [x] `workflow/executors.py` — ProgressGateway, QuizGateway, ReadinessRouter
- [x] `workflow/certprep_workflow.py` — WorkflowBuilder pipeline
- [x] `workflow/handoff_shell.py` — HandoffBuilder outer shell
- [x] `streamlit_app.py` — new Streamlit entry point
- [x] `README.md` — project overview and setup guide
- [x] Package renamed from `cert_prep_maf/maf` → `maf` (all imports updated)
- [x] `docs/` folder with 10 documents matching foundry-sdk structure

---

## 🚀 Sprint — Current (March 2026 Submission)

> **Rule:** One task `[IN PROGRESS]` at a time. Only mark `[DONE]` after smoke test passes.

| # | Task | Status | Notes |
|---|------|--------|-------|
| T-01 | Fill Azure credentials in `.env` | 🔲 NOT STARTED | Required before any live test |
| T-02 | End-to-end Streamlit smoke test | 🔲 NOT STARTED | Full session: profile → plan → assessment → rec |
| T-03 | Verify MCP live module search | 🔲 NOT STARTED | PathCuratorAgent confirms MS Learn returning content |
| T-04 | Create tests/ folder + 50 unit tests | 🔲 NOT STARTED | Against `docs/unit_test_scenarios.md` |
| T-05 | Record demo video | 🔲 NOT STARTED | See `docs/demo_guide.md` for segments |
| T-06 | Add AZ-204 / AZ-305 blueprints | 🔲 NOT STARTED | Extend `_EXAM_BLUEPRINTS` in study_plan_agent.py |
| T-07 | Wire Application Insights | 🔲 NOT STARTED | Confirm spans in portal |

---

## 📝 Quick Reference

| Item | Value |
|------|-------|
| Run app | `streamlit run streamlit_app.py` |
| Checkpoint dir | `~/.certprep_maf/checkpoints/` |
| Reset checkpoints | `rm -rf ~/.certprep_maf/checkpoints/` |
| Source models | `agentsleague-foundry-sdk/src/cert_prep/models.py` |
| Prompt files | `src/maf/prompts/*.md` |
| MAF packages | `agent-framework-core==1.0.0b260212` |
