# User Guide — Certification Prep Multi-Agent System

> Step-by-step walkthrough for learners and admins.  
> No technical background required for Sections 1–6.

---

## Application Flow at a Glance

```
 ┌────────────────────────────────────────┐
 │  LOGIN SCREEN                              │
 │  ┌─────────────┐  ┌─────────────────┐ │
 │  │ New User     │  │ Returning User  │ │
 │  │ enter name   │  │ enter name+PIN  │ │
 │  │ + 4-digit PIN│  │ → plan restored │ │
 │  └─────┬──────┘  └───────┬─────────┘ │
 └──────────────┬────────┬────────────────────┘
                │ new user │ returning
                ▼         │
          INTAKE FORM     │ skip to 6-tab UI
          fill all fields │
          ↓               │
  [Create My AI Study Plan]
          │
          ▼
  AI analyses your background + goals
  (8 agents run in ~1 second)
          │
          ▼
 ┌────────────────────────────────────────┐
 │  7-TAB PANEL                               │
 ├────────────────────────────────────────│
 │ Tab 1: 🗺️ Domain Map                       │
 │   • Domain confidence bars                 │
 │   • Exam score contribution chart          │
 │   • Download PDF / Email buttons           │
 ├────────────────────────────────────────│
 │ Tab 2: 📅 Study Setup                      │
 │   • Prerequisite gap check                 │
 │   • Gantt chart (domain × week)            │
 │   • Hour allocation per domain             │
 ├────────────────────────────────────────│
 │ Tab 3: 📚 Learning Path                    │
 │   • MS Learn module cards per domain       │
 │   • Links, module types, estimated hours   │
 ├────────────────────────────────────────│
 │ Tab 4: 💡 Recommendations                  │
 │   • Learning style + risk domain cards     │
 │   • Prioritised study action plan          │
 │   • Exam booking guidance + next cert path │
 │   • Remediation plan (if quiz done)        │
 ├────────────────────────────────────────│
 │ Tab 5: 📈 My Progress  ◄ HUMAN IN THE LOOP │
 │   Fill: hours studied + domain ratings     │
 │         + practice exam score             │
 │   ↓ submit                                 │
 │   AI computes readiness %                  │
 │   ┌────────┬─────────┬─────────┐     │
 │   │  GO ✓  │ COND GO ⚠️ │ NOT YET ❌ │     │
 │   └────────┴─────────┴─────────┘     │
 │           └─────────────── NOT YET → Regenerate plan
 ├────────────────────────────────────────│
 │ Tab 6: 🧪 Knowledge Check  ◄ HITL ►       │
 │   5–30 questions (domain-weighted)         │
 │   answer all → [Submit Quiz]               │
 │   │                                       │
 │   ├─ score ≥ 60% → PASS ✓                │
 │   └─ score < 60% → FAIL + domain gaps      │
 ├────────────────────────────────────────│
 │ Tab 7: 📄 Raw JSON                         │
 │   Full session data • Profile JSON         │
 │   Download profile as .json file           │
 └────────────────────────────────────────┘
```

---

## Installation & Setup

### Option A — Use the Live Hosted App (no setup required)

Open [agentsleague.streamlit.app](https://agentsleague.streamlit.app) in any browser — no installation needed.  
Skip straight to [Getting Started](#getting-started).

---

### Option B — Run Locally

**Prerequisites:** Python 3.10 or higher, Git

#### 1. Clone the repo

```bash
git clone https://github.com/athiq-ahmed/agentsleague.git
cd agentsleague
```

#### 2. Create and activate a virtual environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

#### 3. Install dependencies

```bash
pip install -r requirements.txt
```

#### 4. Configure environment variables

The app runs fully in **Mock Mode** with zero configuration — no Azure credentials are required for a complete local demo.

To enable live Azure AI features, open the `.env` file and fill in the relevant values:

```bash
# Windows
notepad .env

# macOS / Linux
nano .env
```

| Variable | Required for | Where to get it |
|----------|-------------|-----------------|
| `AZURE_AI_PROJECT_CONNECTION_STRING` | **Tier 1** — Foundry managed agent | Azure portal → Foundry project → gear icon → Project properties |
| `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY` | **Tier 2** — Direct Azure OpenAI | Azure portal → Azure OpenAI resource → Keys and Endpoint |
| `SMTP_USER` + `SMTP_PASS` | Email digest (optional) | Gmail App Password or any SMTP provider |

> **Leave all variables blank** to run in Mock Mode — the full app works without any Azure subscription.

#### 5. Run the app

```bash
streamlit run streamlit_app.py
```

App opens at **`http://localhost:8501`**

#### 6. Run the test suite (optional)

```bash
python -m pytest tests/ -q
# Expected: 342 passed in ~3s  (zero credentials required)
```

---

## Getting Started

### First-Time Login

1. Open the app (local: `http://localhost:8501` or live: `agentsleague.streamlit.app`)
2. You land on the **Welcome tab** — the sidebar shows your progress tracker
3. Enter your **Name** and a **4-digit PIN** you'll remember
4. Click **Let's Begin** — your session is created and saved

> **Returning user?** Enter the same name and PIN from your last session. Your study plan and previous results will be restored automatically.

### Demo Personas (for testing)

| Persona | What to use it for |
|---------|-------------------|
| **New Learner** (any name, PIN `1234`) | See the full flow from scratch with no certs |
| **AI Pro** (add AZ-104 + AI-900 in certs field) | See domain boosts and shorter plan |
| **Admin** (username `admin`, password `agents2026`) | View the Admin Dashboard |

---

## Tab-by-Tab Walkthrough

The app starts with an **intake form**. After submitting it, **seven output tabs** appear across the top of the page. Complete them in order — some tabs unlock only after earlier ones are filled in.

---

### Intake Form — 📋 Setup

**What it does:** Collects everything the AI profiler needs to build your personalised plan.

**Fields to fill:**
| Field | What to enter | Example |
|-------|--------------|---------|
| Target Exam | The Microsoft certification you're preparing for | `AI-102` |
| Background | Your professional background in 2–3 sentences | "I'm a Python developer with 2 years of REST API experience, new to Azure" |
| Existing Certifications | Any certs you already hold (comma-separated) | `AZ-900, AI-900` |
| Hours per Week | Realistic study hours you can commit | `8` |
| Weeks Available | How many weeks until your exam | `12` |
| Concern Topics | Areas you're unsure about (free text) | "OpenAI, computer vision, managing deployments" |
| Learning Style | How you learn best | Select: Hands-on / Linear / Reference / Mix |

**Tips:**
- Be specific in the Background field — "Python developer with REST APIs" gets a better profile than "software engineer"
- Enter *all* certs you hold, even AI-900 or AZ-900 — each one boosts relevant domain scores
- Concern topics lets the system front-load areas you're weakest in

**Click:** `Create My AI Study Plan` — this runs the profiler and generates your plan.

---

### Tab 1: �️ Domain Map

**What it does:** Shows your starting knowledge level for each exam domain as a visual map, plus your PDF download and email buttons.

**Sections on this tab:**
- **Exam Score Contribution** (bar chart): Shows how heavily each domain is weighted on the real exam.
- **Your Confidence per Domain** (bar chart): Initial confidence score from 0–100% based on your background + existing certs.
- **Domain Knowledge Table**: Lists each domain with your `Knowledge Level` (UNKNOWN / WEAK / MODERATE / STRONG) and `Confidence %`.
- **Learning Style Badge**: Your inferred learning style (e.g., LAB_FIRST, LINEAR) and what it means for how resources will be selected.
- **Download PDF Report** / **Email PDF**: Download or send your profile + study plan as a PDF.

**How to read it:**
- Domains with a 🔴 **WEAK** badge are your **risk domains** — the plan will allocate more time here
- Domains with a ✅ **STRONG** badge may have reduced time allocation (you already know this material)
- Compare the weight chart vs confidence chart — a high-weight + low-confidence domain is your biggest risk

---

### Tab 2: 📚 Study Setup

**What it does:** Shows your personalised week-by-week study plan and prerequisite gap check.

**Sections:**
1. **Prerequisite Check** — Lists strongly recommended (⚠️ required) and helpful (💡 optional) prior certifications for your target exam. A red warning banner appears if you're missing strongly-recommended certs.

2. **Study Timeline (Gantt Chart)** — A visual bar chart showing which domains you study in which weeks. Risk domains appear early; review period at the end.

3. **Module Allocation Table** — Each domain with: start week, end week, hours allocated, and priority level (CRITICAL / HIGH / MEDIUM / LOW).

4. **Quick Summary Card** — Total weeks, total hours, number of risk domains, and any prereq gap note.

**How to read the Gantt:**
- Each horizontal bar = one study domain
- Bar position = which weeks you study it
- CRITICAL priority domains appear first (top of chart)
- The final "Review" row is your mock exam prep week

**Tips:**
- If you see a prereq gap warning, consider doing the recommended cert first — it will boost your confidence in multiple domains
- You can change your hours/week input and regenerate the plan from Tab 1

---

### Tab 3: 🛤️ Learning Path

**What it does:** Shows curated learning resources for each domain — mapped to your specific domains and learning style.

**Structure:**
- Each domain has its own expandable section
- Each section contains a list of **MS Learn modules** with: module title, estimated duration, difficulty tag, and a direct link to learn.microsoft.com
- Modules tagged `[LAB]` are hands-on exercises
- Modules tagged `[REFERENCE]` are documentation/conceptual

**Filtering:**
- Domains you already know strongly (`modules_to_skip`) may appear collapsed with a ℹ️ note: "Your profile suggests strong prior knowledge — review optional"
- Risk domains appear expanded by default

---

### Tab 4: � Recommendations

**What it does:** A plain-English summary of what your profile means and what to do. This tab is available immediately after plan generation — it does not require the quiz or progress check-in.

**Sections:**
1. **Personalised Recommendation** — Three cards side by side:
   - *Learning Style* — your inferred style (LINEAR, LAB_FIRST, REFERENCE, ADAPTIVE) and budget summary
   - *Focus Domains* — domains flagged as risk areas (confidence below threshold) shown as red tags
   - *Fast-Track Candidates* — domains you can skim or skip shown as green tags
   - Below the cards: the Agent's recommended approach text from the profiler

2. **Predicted Readiness Outlook** — Four metric tiles (Average Confidence %, Domains Ready ≥70%, At-Risk Domain count, Study Budget hours) and a coloured verdict banner:
   - ✅ On Track — First-Attempt Pass Likely
   - ⚠️ Nearly Ready — 1 Remediation Cycle Needed
   - 📖 Structured Full Prep Recommended

3. **Prioritised Study Action Plan** — Every exam domain ranked by urgency with colour-coded cards. Each card shows the urgency label (🚨 Critical / ⚠️ Below threshold / 📈 Building / ✅ Ready / ⏩ Fast-track), a concrete action tip matched to your learning style, and a suggested hour budget.

4. **Exam Booking Guidance** — Populated after you complete the **Knowledge Check** quiz or the **My Progress** check-in:
   - **Exam info tile** (code, passing score, duration, cost, Pearson VUE link)
   - **Pre-Exam Booking Checklist** — interactive checkboxes for GO path
   - **Remediation Plan** — specific domains and resources for NOT YET path
   - **Next Certification Recommendations** — colour-coded cards for 2–3 follow-on certs with rationale and timeline estimates

> **Note:** The booking guidance is derived from the `CertificationRecommendationAgent`. If neither the quiz nor the progress check-in has been submitted yet, the section shows a prompt to complete one of those gates first.

---

### Tab 5: 📈 My Progress

**What it does:** This is your **first Human-in-the-Loop checkpoint** — you must fill this in honestly for readiness scoring to be meaningful.

**Progress Check-In Form** (fill before your readiness score appears):

| Field | What to enter |
|-------|--------------|
| Hours Studied This Week | How many hours you actually studied (use 0 if you haven't started) |
| Domain Self-Rating | Slide each domain from 1 (very unsure) to 5 (confident) |
| Last Practice Exam Score | Your most recent mock exam percentage (0 if none taken) |

**Click:** `Submit Progress Update`

**After submitting:**
- **Readiness Score** (0–100%): Weighted combination of your domain ratings, hours, and practice score
- **Verdict Banner**: GO ✅ / CONDITIONAL GO 🟡 / NOT YET ❌ with explanation
- **Domain Readiness Grid**: Per-domain mini-bar showing readiness percentage
- **Nudge Messages**: Specific recommendations (e.g., "Spend 2 more hours on Computer Vision before exam")

**Readiness Formula (transparent):**
```
Readiness = 55% × (your domain ratings) + 25% × (hours studied / total budget) + 20% × (practice score)
```

**Tips:**
- Be honest with self-ratings — rating yourself 5/5 on everything when you haven't studied doesn't help you prepare
- if readiness is below 70%, the system shows nudge messages and suggests specific resources; below 50% triggers the NOT YET verdict
- Resubmit the form as you study more — readiness updates each time

---

### Tab 6: 🧪 Knowledge Check

**What it does:** This is your **second Human-in-the-Loop checkpoint** — a domain-weighted practice quiz.

**How it works:**
1. Use the **Number of questions slider** to choose how many questions to attempt (5–30; default 10)
2. Click **Generate New Quiz** — questions are sampled proportionally to your exam's domain weights
3. For each question, select one answer (A / B / C / D)
4. Click `Submit Quiz` when all questions are answered

**After submitting:**
- **Score %**: Your percentage correct
- **Domain Breakdown**: Which domains you got right vs wrong
- **Answer Review**: Each question with your answer, correct answer, and explanation

The quiz mirrors the actual exam domain distribution — domains weighted more heavily on the real exam appear more often in your quiz.

**Passing threshold:** 60%

> 💡 After submitting the quiz, the **Recommendations** tab (Tab 4) updates to show personalised exam booking guidance based on your score.

---

### Tab 7: 📄 Raw JSON

**What it does:** Shows the complete raw JSON data behind your session — useful for debugging, sharing your profile with a colleague, or keeping an offline record.

**Sections:**
- **Raw Student Input** — the exact data you entered in the intake form, as a JSON object
- **Generated Learner Profile** — the full `LearnerProfile` produced by the profiling agent, including all domain confidence scores, risk domains, analogy map, and recommended approach
- **⬇️ Download profile as JSON** — saves `learner_profile_<name>.json` to your device

---

## Admin Dashboard

**Access:** Login with username `admin`, password `agents2026`, then navigate to `Admin Dashboard` in the sidebar.

**What you can see:**

1. **Student Roster** — Table of all students: name, target exam, profile date, plan status, last activity

2. **Agent Execution Gantt** — Select a student run to see a Plotly timeline showing:
   - Each agent as a horizontal bar
   - Length = execution time
   - Colour = status (green=success, red=error, grey=skipped)

3. **Guardrail Violation Log** — All violations across all sessions:
   - Code (G-01 to G-17)
   - Level (BLOCK/WARN/INFO)
   - Message
   - Field that triggered it
   - Student + timestamp

4. **Aggregate Stats** — Average per-agent latency, most frequent guardrail violations, total sessions

---

## FAQ

**Q: Can I change my target exam after starting?**
A: Yes — click **Edit Profile** on the Learner Profile tab, change the exam, and click `Create My AI Study Plan` again. A new profile and plan will be generated. Your previous session data is preserved in the database.

**Q: The system says I'm "NOT YET READY" — what should I do?**
A: The remediation plan in the **Recommendations** tab (Tab 4) shows exactly which domains need work and links directly to the relevant MS Learn modules. Focus on those domains, then resubmit your progress in Tab 5 to see your readiness update.

**Q: My reading says 0% readiness even though I've studied a lot.**
A: You need to fill in the **Progress Check-In form** in **Tab 5** first. Until you submit real study data, the system doesn't know about your progress.

**Q: How many questions are in the quiz?**
A: The quiz is configurable via a slider on Tab 6 (Knowledge Check) — choose between 5 and 30 questions; the default is 10. All questions are distributed across exam domains proportionally to the real exam weights.

**Q: Can I retake the quiz?**
A: Yes — click `Generate New Quiz` on Tab 6 to generate a fresh set of domain-weighted questions. You can adjust the question count with the slider each time.

**Q: Does the system use AI / ChatGPT?**
A: By default, all profiling and planning runs in **mock mode** — a rule-based system that works without any AI API. If an Azure OpenAI key is configured in `.env`, the **Learner Profiler** switches to live GPT-4o calls for richer analysis. All other agents (study planner, learning path curator, progress scorer, quiz, cert recommender) are deterministic — they never call an LLM regardless of mode.

**Q: My session data disappeared after closing the browser.**
A: Because your name and PIN were saved to the database, re-enter them on the Welcome tab to restore your plan and progress.

**Q: The Gantt chart shows some domains are skipped — why?**
A: If your profile shows STRONG confidence in a domain (e.g., you hold a cert that covers it), the system marks it as `module_to_skip` and reduces its study time. You can override this by lowering your self-rating in the Progress tab.

---

## Understanding Your Scores

| Score | What It Means |
|-------|--------------|
| Confidence % | Your starting knowledge level for each domain, inferred from your background and certs |
| Readiness % | Current combined score based on study hours, domain ratings, and practice exam |
| Quiz Score % | How well you did on the knowledge check questions |
| Domain Rating | Your own 1–5 self-assessment (1=very weak, 5=confident) |

| Verdict | Quiz Score Range | Meaning |
|---------|----------------|---------|
| ✅ GO | ≥ 60% | Evidence suggests you're ready — book the exam |
| 🟡 CONDITIONAL GO | 50–59% | Close — targeted review recommended before booking |
| ❌ NOT YET | < 50% | More preparation needed — follow the remediation plan |
