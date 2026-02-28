# 🏆 Agents League — Live Demo Guide

> **Agents League Battle #2 · Certification Prep Multi-Agent System**  
> A complete end-to-end walkthrough of all demo scenarios, agent outputs, and the Admin Dashboard.  
> Built for judges, evaluators, and curious engineers.

---

## Table of Contents

1. [Quick Access](#quick-access)
2. [Application Overview](#application-overview)
3. [How to Run a Demo](#how-to-run-a-demo)
4. [Scenario 1 — AI Beginner (Alex Chen, AI-102)](#scenario-1--ai-beginner-alex-chen-ai-102)
5. [Scenario 2 — Data Professional (Priyanka Sharma, DP-100)](#scenario-2--data-professional-priyanka-sharma-dp-100)
6. [PDF Reports & Email](#pdf-reports--email)
7. [Admin Dashboard Walkthrough](#admin-dashboard-walkthrough)
8. [Learning Tabs Deep-Dive](#learning-tabs-deep-dive)
9. [Responsible AI Guardrails in Action](#responsible-ai-guardrails-in-action)
10. [Architecture at a Glance](#architecture-at-a-glance)
11. [Judging Criteria Checklist](#judging-criteria-checklist)

---

## Quick Access

| Resource | Link |
|----------|------|
| **Live app** | [agentsleague.streamlit.app](https://agentsleague.streamlit.app) |
| **GitHub repo** | [athiq-ahmed/agentsleague](https://github.com/athiq-ahmed/agentsleague) |
| **Local run** | `python -m streamlit run streamlit_app.py` |

**Credentials**

| Role | Username | Password / PIN |
|------|----------|--------------|
| Demo student | *(any name)* | `1234` |
| Admin | `admin` | `agents2026` |

---

## Application Overview

The **Cert Prep Multi-Agent System** turns a 10-minute intake form into a complete, personalised certification study plan. Eight specialised AI agents collaborate in a typed sequential pipeline:

```
Intake Agent
  └──► Safety Guardrails
         └──► Learner Profiling Agent
                ├──► Study Plan Agent  ──────────────────────────────────┐
                └──► Learning Path Curator                               │
                       └──► Progress Agent (HITL Gate 1)                 │
                              └──► Assessment Agent (HITL Gate 2)        │
                                     ├── PASS (≥60%) → Cert Recommender ┤
                                     └── FAIL (<60%) → Remediation loop ┘
```

All agents run in **mock mode by default** — zero Azure OpenAI cost, instant sub-second response. Live mode activates automatically when real Azure credentials are present in `.env`. Set `FORCE_MOCK_MODE=false` to force live mode explicitly.

![Application home screen — intake form](screenshots/01_home_intake_form.png)
*Caption: Home screen showing the two-column intake form, demo scenario buttons in the sidebar, and the Agents League branding.*

---

## How to Run a Demo

### Option A — One-Click Scenario (recommended for live demos)

1. Open the app at `http://localhost:8501` (or the Streamlit Cloud URL)
2. Enter **any name** and PIN `1234` on the login screen
3. In the **left sidebar**, click one of the two scenario buttons:
   - 🌱 **AI Beginner · AI-102** — loads Alex Chen's profile
   - 📊 **Data Professional · DP-100** — loads Priyanka Sharma's profile
4. Review the pre-filled form, then click **Create My AI Study Plan**
5. The seven output tabs appear instantly

### Option B — Custom Profile

1. Fill the intake form manually with any background, exam target, hours per week, and concern topics
2. Click **Create My AI Study Plan**

### Resetting Between Demos

Click **↩ Reset scenario** in the sidebar at any time to clear all state and start fresh.

---

## Scenario 1 — AI Beginner (Alex Chen, AI-102)

**Persona:** Recent CS graduate, no cloud or Azure experience, 12 hours/week available over 10 weeks, wants to break into AI engineering.

### Step 1 — Load the Scenario

Click **🌱 AI Beginner · AI-102** in the sidebar. The form fills automatically:

| Field | Value |
|-------|-------|
| Name | Alex Chen |
| Exam | AI-102 – Azure AI Engineer Associate |
| Background | Recent CS graduate, basic Python, no cloud experience |
| Prior certs | *(none)* |
| Hours / week | 12 |
| Study weeks | 10 |
| Concern topics | Azure Cognitive Services, Azure OpenAI, Bot Service |
| Learning style | Hands-on labs + Practice tests |
| Goal | Break into AI engineering as a first job |
| Motivation | Career growth |

![Alex Chen scenario — pre-filled intake form](screenshots/02_alex_prefill_form.png)
*Caption: Intake form pre-filled for Alex Chen. All fields populated from the sidebar scenario button.*

### Step 2 — Generate the Profile

Click **Create My AI Study Plan**. All eight agents run in under a second (mock mode).

![Profile generation loading](screenshots/03_alex_generating.png)
*Caption: Spinner shown while agents run. In mock mode this resolves in <1 second.*

### Step 3 — Learner Profile (Tab 1)

The **Learner Profile** tab shows Alex's readiness across all AI-102 exam domains as a coloured radar chart + sortable table, plus an exam score contribution bar chart and PDF download button:

- 🔴 **Red** domains (< 40% confidence) — highest priority gaps
- 🟠 **Orange** domains (40–64%) — needs work
- 🟢 **Green** domains (≥ 65%) — solid, can skim

**Expected output for Alex (beginner):** Nearly all domains in red/orange — the system correctly identifies a comprehensive study need with no skip recommendations.

![Alex — Domain Map radar chart](screenshots/04_alex_domain_map.png)
*Caption: Domain Map for Alex Chen. Red-dominant radar confirms beginner status. No domains are skip-recommended.*

### Step 4 — Study Setup (Tab 2)

Shows the parsed study schedule:

- **Total available hours** = 12 h/week × 10 weeks = **120 hours**
- Hours broken down by domain priority
- Warning displayed if total hours appear insufficient for the exam

![Alex — Study Setup hours breakdown](screenshots/05_alex_study_setup.png)
*Caption: Study Setup tab showing 120 total hours distributed across AI-102 domains based on confidence scores.*

### Step 5 — Learning Path (Tab 3)

The **Learning Path** tab shows a week-by-week curated curriculum with:
- Microsoft Learn modules linked per domain
- Estimated time per module
- Prerequisites flagged where applicable

**For Alex:** A 10-week full curriculum starting from Azure fundamentals before advancing to Cognitive Services and OpenAI.

![Alex — Learning Path weekly plan](screenshots/06_alex_learning_path.png)
*Caption: Learning Path for Alex Chen — week-by-week breakdown with module links.*

### Step 6 — Recommendations (Tab 4)

The **Recommendations** tab shows:

- Learning style card + risk-domain cards + Agent-recommended study approach
- Predicted Readiness Outlook metrics
- Prioritised Study Action Plan per domain
- Exam Booking Guidance (populated after the quiz is submitted or progress gate is passed)
  - GO path: Pearson VUE booking checklist
  - NOT YET path: Remediation plan with domain-specific resources + next cert recommendation (AI-102 → AZ-204)

**For Alex:** Likely a NOT YET or CONDITIONAL GO on first visit — risk-domain cards will flag computer vision and generative AI as priority focus areas.

![Alex — Recommendations panel](screenshots/07_alex_recommendations.png)
*Caption: Recommendations panel showing readiness indicator, risk domains, and suggested pre-study steps.*

### Step 7 — My Progress (Tab 5)

First visit shows a **Progress Check-In** form (HITL gate 1) — the learner self-reports hours studied and confidence. Submit to unlock the full progress analytics.

![Alex — Progress Check-In form](screenshots/08_alex_progress_gate.png)
*Caption: Human-in-the-loop gate 1 — learner submits self-reported progress before analytics unlock.*

### Step 8 — Knowledge Check (Tab 6)

Use the slider to choose 5–30 questions (default 10). All selected questions must be answered before the Submit button activates. After submission the `AssessmentAgent` scores the quiz with domain-weighted scoring. Score ≥ 60% → **PASS** badge. Score < 60% → **FAIL** with per-domain breakdown and weak domain highlights.

![Alex — Knowledge Check quiz in progress](screenshots/09_alex_quiz.png)
*Caption: Knowledge Check tab showing a quiz for the Azure OpenAI domain.*

![Alex — Quiz result with score < 60%](screenshots/10_alex_quiz_fail.png)
*Caption: Readiness Gate result for Alex — score below 60% triggers the REMEDIATION path with targeted review links.*

---

## Scenario 2 — Data Professional (Priyanka Sharma, DP-100)

**Persona:** 5-year data analyst, experienced in scikit-learn and Azure ML. Holds AZ-900 + AI-900. Targeting DP-100 in 6 weeks at 8 hrs/week. Goal: move into Azure ML Engineer role.

### Step 1 — Load the Scenario

Click **📊 Data Professional · DP-100** in the sidebar.

| Field | Value |
|-------|-------|
| Name | Priyanka Sharma |
| Exam | DP-100 – Azure Data Scientist Associate |
| Background | 5 yrs data analytics, Python, scikit-learn, Azure ML experiments |
| Prior certs | AZ-900, AI-900 |
| Hours / week | 8 |
| Study weeks | 6 |
| Concern topics | Hyperparameter tuning, model deployment, MLflow, data drift |
| Learning style | Video tutorials + Hands-on labs |
| Goal | Earn DP-100 for Azure ML Engineer role switch |
| Motivation | Role switch + Career growth |

![Priyanka — pre-filled intake form](screenshots/11_priyanka_prefill_form.png)
*Caption: Intake form pre-filled for Priyanka Sharma. Prior cert field shows AZ-900, AI-900.*

### Step 2 — Contrasting Domain Map

With an existing Python + Azure ML background, Priyanka's Domain Map looks starkly different from Alex's:

- Several domains in **green** (skip-recommended)
- Only concern areas (MLflow, data drift, deployment) remain orange/red
- Agent correctly detects prior certs and applies credit

**Key differentiator to highlight in the demo:** Same system, completely different output — the agents correctly personalise based on experience level.

![Priyanka — Domain Map — mostly green with targeted gaps](screenshots/12_priyanka_domain_map.png)
*Caption: Domain Map for Priyanka — mostly green with targeted gaps in MLflow and model monitoring. Green domains are skip-recommended.*

### Step 3 — Compressed Study Plan

- **Total hours** = 8 × 6 = 48 hours — focused, not exhaustive
- Skip-recommended domains free up hours for weak areas
- Study plan is materially shorter and more targeted than Alex's

![Priyanka — Study Setup — 48-hour compressed plan](screenshots/13_priyanka_study_setup.png)
*Caption: Study Setup for Priyanka — 48 hours distributed across only non-skip domains.*

### Step 4 — Cert Recommendation: GO Path

Because Priyanka holds prior certs and has strong fundamentals, the Readiness Gate score is typically above 60% — she is placed on the **GO** path immediately.

![Priyanka — Readiness Gate passes — GO badge](screenshots/14_priyanka_go_path.png)
*Caption: Readiness Gate result for Priyanka — GO path badge with cert booking recommendation.*

### Step 5 — Side-by-Side Comparison

| Dimension | Alex Chen (Beginner) | Priyanka Sharma (Expert) |
|-----------|---------------------|--------------------------|
| Study hours | 120 hrs | 48 hrs |
| Skip-recommended domains | 0 | 3–4 |
| Risk domains | 5–6 | 1–2 |
| Readiness path | REMEDIATE | GO |
| Pre-study suggestion | AZ-900 prep | None |
| Quiz pass rate (demo) | ~55% | ~82% |

This contrast is the **core showpiece** of the multi-agent personalisation.

---

## PDF Reports & Email

The system can generate and email PDF study reports at two points in the workflow:

### Automatic Welcome Email (on intake submission)

If SMTP credentials are configured in `.env` **and** the student entered an email address in the intake form, the system automatically sends a welcome PDF immediately after the study plan is generated. The PDF contains:
- Learner profile snapshot (experience level, domain confidence scores)
- Personalised study plan with domain priorities and hours breakdown
- Learning path module list

### Manual PDF Download (Profile tab)

In the **Learner Profile** tab, scroll below the domain chart to find:
1. **⬇️ Download PDF** — downloads the profile + study plan as a PDF file
2. **📧 Email Study Plan PDF** — type an email address and click send; the same PDF is emailed via SMTP

### Progress Report PDF (Progress tab)

In the **My Progress** tab, after completing the progress check-in:
1. **⬇️ Download PDF** — downloads a progress report with readiness scores and domain breakdown
2. **📤 Email + PDF** — emails the progress report PDF to the address on file

### Requirements

```env
# .env — all five SMTP vars required for email to activate
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-account@gmail.com
SMTP_PASS=your-16-char-app-password
SMTP_FROM=your-account@gmail.com
```

> **Demo tip:** PDF download works in all modes (mock + live) without any Azure credentials. Email requires SMTP vars.

---

## Admin Dashboard Walkthrough

Access: click **🔐 Admin Dashboard** in the sidebar (admin users only).  
Credentials: username `admin`, password `agents2026`.

### Student Cohort Table

The dashboard opens with a live student registry table showing all students who have run the pipeline. The demo database ships pre-seeded with **7 students** spanning multiple exam families:

| Student | Exam | Status |
|---------|------|--------|
| Alex Chen | AI-102 | Demo scenario |
| Priyanka Sharma | DP-100 | Demo scenario |
| Marcus Johnson | AZ-204 | CONDITIONAL GO |
| Sarah Williams | AI-900 | GO (84% quiz) |
| David Kim | AZ-305 | NOT YET (early stage) |
| Fatima Al-Rashid | AI-102 | GO (88% quiz) |
| Jordan Baptiste | DP-100 | NOT YET (mid progress) |

Each row shows: Level, Avg Confidence, Risk domain count, Plan status, Readiness %, Quiz score, GO/NO-GO verdict.

Six metric cards showing Run ID, Student, Exam Target, Timestamp, Mode (mock/live), and Total execution time:

![Admin — Run Summary cards](screenshots/15_admin_run_summary.png)
*Caption: Run Summary section — 6 uniform metric cards showing the profiling run metadata.*

### Agent Execution Timeline (Gantt Chart)

A horizontal Gantt chart showing each agent's start time and duration in milliseconds. In mock mode all bars are tiny (< 50 ms each). In live Azure OpenAI mode, Profiler and Domain Scorer bars grow to 3–5 seconds each.

![Admin — Gantt chart agent timeline](screenshots/16_admin_gantt.png)
*Caption: Agent Execution Timeline Gantt — 6 agents shown with colour-coded bars by agent type.*

### Per-Agent Interaction Log

Every agent card shows:
- **Agent name + colour band** with status badge (success / warning)
- **📨 Input** — what data the agent received
- **📤 Output** — what the agent produced
- **⚙️ Rules / Decisions Applied** — the guardrail rule IDs that fired

![Admin — Per-Agent card for Learner Profiling Agent](screenshots/17_admin_agent_card_profiler.png)
*Caption: Per-Agent card for Learner Profiling Agent — input received from Intake Agent, output LearnerProfile with confidence scores.*

![Admin — Per-Agent card for Domain Confidence Scorer](screenshots/18_admin_agent_card_scorer.png)
*Caption: Domain Confidence Scorer card showing per-domain scores and rules applied.*

![Admin — Per-Agent card for Readiness Gate](screenshots/19_admin_agent_card_gate.png)
*Caption: Readiness Gate card — decisions section shows the exact threshold rule used (≥ 70% = GO).*

### Domain Decision Audit Trail

A Plotly colour-coded table + horizontal bar chart showing the final per-domain outcome: confidence score, knowledge level, skip recommendation, and risk flag.

![Admin — Domain Decision Audit Trail table and bar chart](screenshots/20_admin_audit_trail.png)
*Caption: Domain Decision Audit Trail — colour-coded by confidence band. Red = high priority, green = ready.*

### Session History

A full dataframe of all profiling runs in the current browser session, including student name, exam, mode, and average confidence.

![Admin — Session History table](screenshots/21_admin_session_history.png)
*Caption: Session History table — shows all runs generated in this session with key metrics.*

---

## Learning Tabs Deep-Dive

After generating a profile, seven output tabs appear across the top of the page:

| Tab | What it shows | Key agent |
|-----|--------------|----------|
| **1 · 🗺️ Domain Map** | Domain radar, confidence scores, exam score contribution chart, PDF download | Learner Profiling Agent |
| **2 · 📅 Study Setup** | Gantt chart, prerequisite gap check, weekly hour breakdown | Study Plan Agent |
| **3 · 📚 Learning Path** | MS Learn module cards with links, module types, estimated hours | Learning Path Curator |
| **4 · 💡 Recommendations** | Learning style + risk-domain cards, Predicted Readiness Outlook, Study Action Plan, Exam Booking Guidance (GO or NOT YET) | Cert Recommendation Agent |
| **5 · 📈 My Progress** | HITL Gate 1 check-in form → ReadinessAssessment with readiness %, domain breakdown | Progress Agent |
| **6 · 🧪 Knowledge Check** | HITL Gate 2 — configurable quiz (5–30 questions, default 10) → scored result with domain breakdown; 60% pass threshold | Assessment Agent |
| **7 · 📄 Raw JSON** | Raw student input JSON + generated learner profile JSON + download button | *(display only)* |

Each tab has a **↑ Back to top** anchor and a one-liner purpose caption.

---

## Responsible AI Guardrails in Action

The `GuardrailsPipeline` runs **at every agent transition** — 17 rules across 6 categories:

| Category | Rules | Effect |
|----------|-------|--------|
| PII Detection | Names/emails in background text | WARN — flags detected PII |
| Content Safety | Hateful, harmful, or off-topic text | BLOCK — pipeline halts |
| Data Validation | Missing required fields | BLOCK |
| Confidence Bounds | Scores outside 0–1 range | BLOCK |
| Scope Guard | Non-Microsoft exam targets | WARN |
| Session Integrity | Tampered or missing session state | BLOCK |

**Demo tip:** On the intake form, try typing `sarah@email.com` in the background field. The guardrail fires a PII warning badge visible in **Tab 7 (Raw JSON)** and in the Admin Dashboard per-agent card for the Intake Agent.

---

## Architecture at a Glance

```
streamlit_app.py (UI Layer)
│
├── src/cert_prep/
│   ├── b0_intake_agent.py          Intake + PII check
│   ├── guardrails.py               17-rule cross-cutting middleware
│   ├── b1_mock_profiler.py         Learner Profiling Agent
│   ├── b1_1_learning_path_curator.py  Learning Path Curator Agent
│   ├── b1_1_study_plan_agent.py    Study Plan Agent
│   ├── b1_2_progress_agent.py      Progress Tracking Agent
│   ├── b2_assessment_agent.py      Knowledge Check + Readiness Gate
│   ├── b3_cert_recommendation_agent.py  Cert Recommendation Agent
│   ├── agent_trace.py              RunTrace / AgentStep telemetry models
│   ├── models.py                   Pydantic data contracts
│   ├── config.py                   USE_MOCK flag, Azure credentials
│   └── database.py                 SQLite student registry
│
└── pages/
    └── 1_Admin_Dashboard.py        Admin-only agent interaction inspector
```

**Data contracts (Pydantic):**  
`RawStudentInput` → `LearnerProfile` → `StudyPlan` / `LearningPath` → `ReadinessAssessment` → `CertRecommendation`

Every agent receives and returns a typed Pydantic model — no raw-string hand-offs, no hallucination-prone free-form dictionaries.

---

## Judging Criteria Checklist

| ✅ PDF report download | Profile + Progress PDFs | `⬇️ Download PDF` buttons | reportlab |
| ✅ Email PDF to learner | SMTP with attachment | `📧 Email Study Plan PDF` buttons | smtplib + MIME |
| ✅ Multi-agent orchestration | 8 specialised agents, typed sequential pipeline | |
| ✅ Agent handoffs | Pydantic contract at every boundary | |
| ✅ Human-in-the-Loop | HITL gate 1 (Progress Check-In) + HITL gate 2 (Quiz submit) | |
| ✅ Conditional routing | Readiness Gate: GO vs REMEDIATE path | |
| ✅ Responsible AI | 17 guardrail rules, BLOCK/WARN/INFO levels | |
| ✅ Explainability | Full per-agent trace in Admin Dashboard | |
| ✅ Production quality | Pydantic models, error handling, session management | |
| ✅ Personalisation | Identical system → completely different plans for Alex vs Priyanka | |
| ✅ No-cost demo mode | All scenarios run without Azure credentials | |
| ✅ Real-time UI | Streamlit app with plotly charts, gantt, radar, tables | |
| ✅ 9-exam families | AI-102, AI-900, AZ-204, AZ-305, AZ-400, DP-100, DP-203, SC-100, MS-102 | |

---

> **Screenshots:** All `docs/screenshots/*.png` files should be captured from a live demo session.  
> Run the app locally, execute both scenarios, and save screenshots using the filenames referenced above.  
> The Admin Dashboard screenshots require signing in as `admin` / `agents2026` and clicking through after running a scenario first.

---

*Last updated: February 2026 · Agents League Battle #2*
