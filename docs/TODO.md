# 📋 Project TODO — Agents League Battle #2

> **Owner:** Athiq Ahmed  
> **Project:** Microsoft Certification Prep Multi-Agent System  
> **Track:** Reasoning Agents with Microsoft Foundry  
> **Subscription:** Pay-As-You-Go (recommended) or MSDN/Visual Studio  
> **Last updated:** 2026-02-25

---

## 1️⃣ Azure Services to Enable

### A. Azure OpenAI Service ⭐ (Primary — powers all agents)

| Setting | Value |
|---------|-------|
| **Resource Group** | `rg-agentsleague` |
| **Region** | `East US 2` or `Sweden Central` (best GPT-4o availability) |
| **Pricing tier** | `S0` (Standard) |
| **Model to deploy** | `gpt-4o` (version `2024-11-20` or latest) |
| **Deployment name** | `gpt-4o` |
| **TPM quota** | Request at least `30K` tokens/min |

**How to set up:**
1. Portal → **Create a resource** → search "Azure OpenAI" → **Create**
2. Pick `rg-agentsleague`, region, name (e.g. `aoai-agentsleague`)
3. After deployment → **Keys and Endpoint** blade → copy:
   - `AZURE_OPENAI_ENDPOINT` (e.g. `https://aoai-agentsleague.openai.azure.com`)
   - `AZURE_OPENAI_API_KEY` (Key 1)
4. **Model deployments** → **Create new deployment**:
   - Model: `gpt-4o`, Deployment name: `gpt-4o`, TPM: `30K`
5. Paste into `.env`:
   ```
   AZURE_OPENAI_ENDPOINT=https://aoai-agentsleague.openai.azure.com
   AZURE_OPENAI_API_KEY=<your-key>
   AZURE_OPENAI_DEPLOYMENT=gpt-4o
   AZURE_OPENAI_API_VERSION=2024-12-01-preview
   ```
6. Test: `.venv\Scripts\python.exe -c "from src.cert_prep.config import get_config; c=get_config(); print(c)"`

- [ ] Resource created
- [ ] Model deployed
- [x] `.env` template created & auto live-mode wired in `streamlit_app.py`

---

### B. Azure AI Foundry (Agent orchestration + evaluation)

| Setting | Value |
|---------|-------|
| **Hub name** | `hub-agentsleague` |
| **Project name** | `certprep-agents` |
| **Region** | Same as OpenAI resource |
| **Connected service** | Link your Azure OpenAI resource |

**How to set up:**
1. Go to [ai.azure.com](https://ai.azure.com) → **Create project**
2. Create or select a Hub → name the project `certprep-agents`
3. Under **Connected resources** → attach your Azure OpenAI resource
4. **Settings** → copy the **Project Connection String**
5. Add to `.env`:
   ```
   AZURE_AI_PROJECT_CONNECTION_STRING=<your-connection-string>
   ```
6. Install SDK: `pip install azure-ai-projects azure-ai-agents`

- [ ] Hub + Project created
- [ ] OpenAI resource connected
- [x] Connection string placeholder in `.env` (`AZURE_AI_PROJECT_CONNECTION_STRING`)
- [ ] SDK installed (`pip install azure-ai-projects azure-ai-agents`)

---

### C. Azure AI Content Safety (Responsible AI guardrails)

| Setting | Value |
|---------|-------|
| **Resource name** | `aics-agentsleague` |
| **Region** | `East US` or `West Europe` |
| **Pricing tier** | `F0` (Free — 5K transactions/month) or `S0` |

**How to set up:**
1. Portal → **Create a resource** → "Content Safety" → **Create**
2. Copy endpoint + key
3. Add to `.env`:
   ```
   AZURE_CONTENT_SAFETY_ENDPOINT=https://aics-agentsleague.cognitiveservices.azure.com
   AZURE_CONTENT_SAFETY_KEY=<key>
   ```
4. Used by `guardrails.py` for PII filtering and content moderation

- [ ] Resource created
- [x] Placeholder in `.env` (`AZURE_CONTENT_SAFETY_ENDPOINT/KEY/THRESHOLD`)
- [x] Regex-based G-16 heuristic active (7 PII patterns + 14 harmful keywords)
- [x] Upgrade G-16 to use Azure Content Safety API — `_check_content_safety_api()` live in `guardrails.py` (HTTP POST, severity ≥ 2 = BLOCK, regex fallback)

---

### D. SMTP Email (Optional — weekly progress email nudges)

> **Current implementation** uses Python `smtplib` with standard SMTP credentials.  
> Azure Communication Services is a **future roadmap** upgrade — it is **not** available in the current build.

| Setting | Value |
|---------|-------|
| **Required vars** | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM` |
| **Works with** | Gmail, Outlook, SendGrid, or any SMTP relay |
| **Cost** | Free tier available on all major providers |

**How to set up (Gmail example):**
1. Enable **App Passwords** in your Google account (2FA must be on)
2. Create an App Password for "Mail" → copy the 16-character code
3. Add to `.env`:
   ```
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-account@gmail.com
   SMTP_PASS=your-16-char-app-password
   SMTP_FROM=your-account@gmail.com
   ```
4. Used by `b1_2_progress_agent.py` → `attempt_send_email()` for weekly progress summaries

- [ ] SMTP credentials configured in `.env` (optional — app works without it)
- [x] `attempt_send_email()` implemented in `b1_2_progress_agent.py` using `smtplib`
- [x] `pdf_bytes` attachment argument added — PDF auto-attached to all outbound emails
- [x] `generate_profile_pdf()` and `generate_assessment_pdf()` implemented using `reportlab`
- [x] `.env.example` has correct `SMTP_*` placeholder section

---

> 🗺️ **Roadmap — Azure Communication Services (ACS):** When ready to upgrade, create a **Communication Services** resource in the Azure portal → add an **Email Communication Service** sub-resource → verify or use the free Azure-managed domain (`*.azurecomm.net`) → copy connection string to `AZURE_COMM_CONNECTION_STRING`. Then swap `smtplib` for `azure-communication-email` SDK.

---

### E. Microsoft Learn MCP Server (Tool use — real learning paths)

**No Azure resource needed** — runs locally as a sidecar process.

**How to set up:**
1. `npm install -g @microsoftdocs/mcp` (requires Node.js 18+)
2. Or clone: `git clone https://github.com/microsoftdocs/mcp`
3. Start server: `npx @microsoftdocs/mcp`
4. Add to `.env`:
   ```
   MCP_MSLEARN_URL=http://localhost:3001
   ```
5. Used by `learning_path_curator.py` to fetch real MS Learn modules + exam blueprints

- [ ] Node.js 18+ installed
- [ ] MCP server running
- [x] Placeholder in `.env` (`MCP_MSLEARN_URL=http://localhost:3001`)
- [ ] Integrated into Learning Path Curator agent

---

## 2️⃣ Development Tasks

### 🔴 Must Do (Before Submission)

- [ ] **Wire agents to Azure OpenAI** — switch from mock → live for:
  - `intake_agent.py` — LLM-based learner profiling
  - `study_plan_agent.py` — LLM-generated personalised study plans
  - `learning_path_curator.py` — LLM-curated MS Learn modules
  - `assessment_agent.py` — LLM-generated exam-style quiz questions
  - `cert_recommendation_agent.py` — LLM-powered certification path suggestions
- [ ] **Multi-agent orchestration in Foundry**
  - Define agent pipeline: Intake → Profiling → Learning Path → Study Plan → Assessment → Progress
  - Add human-in-the-loop confirmation at readiness gate
- [x] **Evaluation harness** — `src/cert_prep/eval_harness.py`; `CoherenceEvaluator`, `RelevanceEvaluator`, `FluencyEvaluator` via `azure-ai-evaluation>=1.0.0`; `batch_evaluate()` for regression suites; graceful no-op in mock mode
- [ ] **Create Azure resource group** `rg-agentsleague` and provision OpenAI resource
- [ ] **Deploy gpt-4o model** in Azure OpenAI Studio (30K TPM quota)
- [ ] **Fill real values** in `.env` — app auto-switches to live mode once done

### 🟡 Should Do (Strengthens Submission)

- [ ] **MCP integration** — real MS Learn content instead of static mock data
- [x] **Content Safety API** — G-16 upgraded: `_check_content_safety_api()` in `guardrails.py` makes live HTTP POST to Azure Content Safety endpoint; severity ≥ 2 = BLOCK; regex fallback when unconfigured
- [x] **Wire `attempt_send_email()` with SMTP creds** — configure `SMTP_HOST/PORT/USER/PASS/FROM` in `.env` to activate weekly progress summaries; PDF attachment implemented (ACS upgrade is a roadmap item)
- [ ] **Record demo video** (3–5 min) showing:
  - New learner flow → profile generation → study plan → quiz
  - Returning learner → progress tracking → readiness assessment
  - Admin dashboard → agent trace inspection
  - G-16 PII scenario (S8) — user types SSN, sees WARN banner, pipeline continues

### 🟢 Nice to Have

- [x] Add more exam domain blueprints (DP-100, AZ-204, AZ-305, AI-900) to `EXAM_DOMAIN_REGISTRY` — 5 exams, 81 modules total
- [ ] Persistent storage (Cosmos DB or SQLite) for learner profiles across sessions
- [ ] Deploy to Azure App Service or Container Apps
- [ ] Add Bing Grounding for up-to-date exam change announcements

---

## 3️⃣ Cost Estimate (Monthly)

| Service | Tier | Est. Cost |
|---------|------|-----------|
| Azure OpenAI (gpt-4o) | S0, ~50K tokens/day dev usage | ~$5–15/mo |
| AI Foundry | Free tier for project mgmt | $0 |
| Content Safety | F0 free tier | $0 |
| Communication Services | <100 emails | $0 |
| **Total dev/test** | | **~$5–15/mo** |

> 💡 **Tip:** Set a **budget alert** at $20 in Cost Management to avoid surprises.

---

## ✅ Completed

- [x] Project scaffolding & folder structure
- [x] Mock profiler (rule-based inference — works without Azure)
- [x] Streamlit UI with 7 tabs (conditional by user type)
- [x] Study Plan Agent (mock, rule-based)
- [x] Learning Path Curator Agent (mock)
- [x] Assessment Agent (mock quiz generation + scoring)
- [x] Certification Recommendation Agent (mock)
- [x] Progress Agent with readiness assessment + email summary
- [x] Guardrails pipeline (17 rules: G-01 to G-17 — PII filter, anti-cheat, content safety, URL trust)
- [x] Agent trace logging & Admin Dashboard
- [x] Login gate with glassmorphism design (new / existing / admin)
- [x] Tab visibility based on user type
- [x] Genericized naming — supports any Microsoft cert exam
- [x] `.gitignore` updated per starter kit guidelines
- [x] GitHub repo: [athiq-ahmed/agentsleague](https://github.com/athiq-ahmed/agentsleague)
- [x] Creative login page (glassmorphism + gradient design)
- [x] Folder cleanup + archive of old planning files
- [x] Agent orchestration patterns documented (Sequential Pipeline, Typed Handoff, HITL Gates, Conditional Routing)
- [x] Q&A Playbook created (`docs/qna_playbook.md`)
- [x] Guardrails documented across README, architecture, and judge playbook
- [x] `.env` updated — all 15 Azure service fields across 6 sections
- [x] `.env.example` created — safe committed template (placeholders only)
- [x] `config.py` expanded — `Settings` dataclass covering OpenAI + Foundry + Content Safety + Comm + MCP + App
- [x] Auto live-mode detection in `streamlit_app.py` — switches when real Azure creds present
- [x] `load_dotenv()` wired into app startup
- [x] Sidebar Azure mode badge (green = live / grey = mock)
- [x] G-16 upgraded — real 14-keyword harmful pattern + 7 PII regex patterns (SSN, CC, passport, UK NI, email, phone, IP)
- [x] G-16 PII scan added to `InputGuardrails.check()` — fires before any agent runs
- [x] S8 PII scenario documented in `docs/user_flow.md` (sub-scenarios A–D + production upgrade path)
- [x] `tests/` folder created with `test_guardrails.py`, `test_config.py`, `test_agents.py`
- [x] Dev Approach + Reasoning Patterns + Security docs added to README
- [x] SMTP email clarification (`.env.example` + README + TODO.md)
- [x] `azure-ai-projects` Foundry Agent Service SDK integrated (`LearnerProfilingAgent` 3-tier strategy)
- [x] Responsible AI Considerations section added to README (7-principle table)
- [x] Full Submission Requirements Checklist added to README (mandatory + optional)
- [x] Microsoft Foundry Best Practices section added to README (all 6 practices with status)
- [x] Self-improvement loop created: `docs/lessons.md` + sprint tracking in this file
- [x] PDF report generation — `generate_profile_pdf()` + `generate_assessment_pdf()` using `reportlab`
- [x] SMTP email with PDF attachment — `attempt_send_email(pdf_bytes=...)` updated; auto-email on intake
- [x] Download PDF + Email PDF buttons added to Profile and Progress tabs in UI
- [x] Learning path catalogue extended to all 5 exams — AI-102, AI-900, AZ-204, AZ-305, DP-100 (81 modules)
- [x] Hours consistency fix — all 5 display spots use `profile.total_budget_hours` as canonical budget
- [x] Scenario card dimming — `.sb-sc-card.disabled` CSS; inactive card dims when other is selected
- [x] `load_dotenv(override=True)` — live mode `.env` credentials correctly loaded on startup
- [x] Demo cohort seeded — 5 additional students (Marcus Johnson/AZ-204, Sarah Williams/AI-900, David Kim/AZ-305, Fatima Al-Rashid/AI-102, Jordan Baptiste/DP-100) via `src/cert_prep/seed_demo_data.py`
- [x] `docs/technical_documentation.md` — merged comprehensive 22-section doc (arch + tech doc combined, all agents, algorithms, guardrails, testing, deployment)
- [x] `docs/user_flow.md` — rewritten as 8 prose scenario walkthroughs S1–S8 (no broken mermaid)
- [x] `docs/qna_playbook.md` — updated agent inventory, guardrail table, URL allowlist, exam families count
- [x] `docs/demo_guide.md` — updated tab names (6 tabs), button labels, exam catalogue to 9 families
- [x] `docs/user_guide.md` — updated from 7-tab to 6-tab structure with correct tab names
- [x] `exam_weight_pct` AttributeError fixed in Recommendations tab (`getattr` fallback + equal-weight distribution) — commit `cb78946`
- [x] Comprehensive tab/page audit — all 4256 lines of `streamlit_app.py` + `pages/1_Admin_Dashboard.py` audited
- [x] Serialization hardening — `_dc_filter()` helper; all 6 `*_from_dict` helpers now filter unknown keys via `dataclasses.fields()` — schema-evolution safe
- [x] Safe enum coercion — `ReadinessVerdict` / `NudgeLevel` casting wrapped with membership check; fallback to `NEEDS_WORK`/`INFO`
- [x] Per-exam domain weights — `ProgressAgent.assess()` now calls `get_exam_domains(profile.exam_target)` for correct weights per exam
- [x] Checklist key bug fixed — `hash(_item)[:8]` (TypeError) changed to `abs(hash(_item))`
- [x] Admin Dashboard `NumberColumn` type fix — `risk_count` fallback changed from `"—"` (str) to `None`
- [x] `tests/test_serialization_helpers.py` — 25 new tests: `_dc_filter`, enum coercion, all 6 `*_from_dict` round-trips with extra/missing keys
- [x] `tests/test_progress_agent.py` extended — 9 new tests: 5-exam parametrized readiness, per-exam weight validation, fallback weight smoke test
- [x] `docs/unit_test_scenarios.md` — created; full catalogue of all 289 test scenarios (easy/medium/hard/edge cases) — authoritative reference for "do unit test" runs
- [x] All docs updated — README.md, qna_playbook.md, technical_documentation.md, lessons.md — test count 289, new What's New entries, Project Documentation table, 25 best practices, unit_test_scenarios.md created
- [x] `azure-ai-evaluation>=1.0.0` added to `requirements.txt`; `src/cert_prep/eval_harness.py` created (T-09 ✅)
- [x] G-16 Content Safety API live in `guardrails.py` — `_check_content_safety_api()` HTTP POST, severity ≥ 2 = BLOCK (T-07 ✅)
- [x] README Honest Gaps table updated: T-07/T-09 marked Implemented; T-06 clarified as by-design (deterministic agents); Foundry Best Practices rows 4 & 5 updated from Roadmap → Implemented
- [x] README System Metrics redesigned as live-mode-only; stale test counts fixed (299/289 → 342); RAI coverage 85% → 100%
- [x] docs/TODO.md, docs/technical_documentation.md, docs/qna_playbook.md updated — test counts, G-16 status, eval harness module entry

---

## 🚀 Sprint — Current (Feb 2026 Submission)

> **Rule:** Only ONE task `[IN PROGRESS]` at a time. Tasks only marked `[DONE]` after: `py_compile` passes + behaviour verified + git diff reviewed.

| # | Task | Status | Notes |
|---|------|--------|-------|
| T-06 | Extend Azure AI Foundry SDK to remaining 4 agents | 🔲 NOT STARTED | `StudyPlanAgent`, `LearningPathCuratorAgent`, `AssessmentAgent`, `CertRecommendationAgent` — same 3-tier pattern as `LearnerProfilingAgent` |
| T-07 | Upgrade G-16 content safety heuristic → Azure Content Safety API | ✅ DONE | `_check_content_safety_api()` in `guardrails.py` makes live HTTP POST to Azure Content Safety endpoint; severity ≥ 2 = BLOCK; regex fallback when unconfigured |
| T-08 | Wire MCP MS Learn server into `LearningPathCuratorAgent` | 🔲 NOT STARTED | `MCP_MSLEARN_URL` placeholder in `.env`; needs Node.js MCP sidecar + `httpx` client in agent |
| T-09 | Wire `azure-ai-evaluation` SDK for agent quality metrics | ✅ DONE | `src/cert_prep/eval_harness.py` created; `CoherenceEvaluator`, `RelevanceEvaluator`, `FluencyEvaluator`; `azure-ai-evaluation>=1.0.0` in `requirements.txt` |
| T-10 | Record demo video (3–5 min) | 🔲 NOT STARTED | New learner → profile → plan → quiz → recommendation; show Admin Dashboard trace + G-16 PII |
| T-11 | Deploy to Streamlit Cloud with service principal secrets | 🔲 NOT STARTED | Add `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID` to Streamlit Cloud secrets |
| T-12 | Docs overhaul | ✅ DONE | Merged `technical_architecture.md` + `technical_documentation.md`; rewrote `user_flow.md` (prose); updated `qna_playbook.md`, `demo_guide.md`, `user_guide.md`, created `unit_test_scenarios.md` |

### Backlog — Should Do

| # | Task | Notes |
|---|------|-------|
| B-01 | Foundry Evaluation SDK harness (bias + relevance + groundedness metrics) | `azure-ai-evaluation`; test across all 9 cert families |
| B-02 | Azure Monitor / App Insights telemetry | Per-agent latency, guardrail fire rate, parallel speedup |
| B-03 | Add DP-420, AZ-500, AZ-700 exam domains to registry | Extend from 9 to 12 exam families |
| B-04 | Adaptive quiz engine with GPT-4o item generation | IRT-based difficulty scaling; replace static question bank |
| B-05 | Upgrade email SMTP → Azure Communication Services | `azure-communication-email` SDK + ACS resource |

### Verification Checklist (run before every commit)

```powershell
# 1. Syntax check
& ".venv/Scripts/python.exe" -m py_compile streamlit_app.py
& ".venv/Scripts/python.exe" -m py_compile src/cert_prep/b0_intake_agent.py

# 2. Unit tests
& ".venv/Scripts/python.exe" -m pytest tests/ -x -q

# 3. Kill port + launch smoke test
$p = (netstat -ano | Select-String '0.0.0.0:8501 ' | ForEach-Object { ($_ -split '\s+')[-1] } | Select-Object -First 1)
if ($p) { taskkill /PID $p /F }
& ".venv/Scripts/python.exe" -m streamlit run streamlit_app.py

# 4. Git diff review
git diff --stat HEAD
```

---

## 📝 Quick Reference

| Item | Value |
|------|-------|
| Student PIN | `1234` |
| Admin username | `admin` |
| Admin password | `agents2026` |
| GitHub repo | `athiq-ahmed/agentsleague` |
| Python venv | `.venv\Scripts\python.exe` |
| Run app | `streamlit run streamlit_app.py` |
| Mock mode | Works without any Azure credentials |
| Resource group | `rg-agentsleague` (create this first) |
