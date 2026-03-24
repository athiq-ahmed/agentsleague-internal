# User Guide — CertPrep MAF

> **Version:** 1.0  
> **Last updated:** 2026-03-24

Welcome to **CertPrep AI**, your Microsoft certification preparation assistant powered by the Microsoft Agent Framework.

---

## Getting Started

### Launch the app

```bash
cd agentsleague-maf
streamlit run streamlit_app.py
```

Open `http://localhost:8501` in your browser.

---

## The Chat Interface

CertPrep uses a conversational chat interface. You interact naturally with the AI — it routes your messages to the right specialist agent automatically.

**Tips for best results:**
- Be specific: mention the exam code (e.g., `AI-102`, `DP-100`, `AZ-900`)
- State your experience level upfront (e.g., "I'm new to Azure AI")
- Mention your weekly study hours budget (e.g., "I have 10 hours a week for 8 weeks")

---

## Step-by-Step Walkthrough

### Step 1 — Start a New Preparation

Type a message like:
> "I want to prepare for AI-102. I'm a software engineer with 2 years of Python experience and about 12 hours per week for 6 weeks."

The **TriageAgent** will greet you and hand off to the **CertPrep workflow**.

---

### Step 2 — Learner Profiling

The **ProfilerAgent** will ask a series of questions to build your learner profile:

- Target exam (e.g., AI-102)
- Current role and experience level
- Preferred learning style (LINEAR, LAB_FIRST, or REFERENCE)
- Per-domain confidence rating (0 = no knowledge, 1 = expert)
- Existing certifications (if any)
- Weekly study hours and total weeks available

Answer naturally in conversation — the agent extracts structured data from your responses.

---

### Step 3 — Study Plan Generation

The **StudyPlanAgent** builds a personalised study plan using the **Largest Remainder Method** to allocate your study hours across exam domains in proportion to their exam weight.

You will see:
- Number of weeks and hours per domain
- Domains ordered by priority (risk domains first)
- Any prerequisite gaps flagged

The **PathCuratorAgent** runs in parallel, searching **Microsoft Learn** for 2–3 recommended modules per domain.

---

### Step 4 — Progress Checkpoint (HITL Gate 1)

After you report study progress, the **ProgressAgent** computes your **ReadinessScore**:

```
ReadinessScore = 0.55 × avg_confidence
               + 0.25 × hours_utilisation_ratio
               + 0.20 × practice_test_ratio
```

When your score reaches 0.45 or above, the system **pauses and asks you to decide**:

> "You've reached a readiness score of 62%. Would you like to:  
> - **A** — Take a practice assessment now  
> - **B** — Continue studying"

Type **A** or **B** to continue. Your choice and progress are saved to a checkpoint — if you close the browser and return, the session resumes where you left off.

---

### Step 5 — Practice Assessment (HITL Gate 2)

If you choose to take the assessment, the **AssessmentAgent** generates a **10–15 question domain-weighted quiz** based on your exam blueprint and confidence profile.

The quiz is delivered in chat. Answer each question one per line, for example:
```
B
A
C
A,C
B
```

Your answers are scored after submission. You will receive:
- Overall percentage score
- Per-domain breakdown
- Readiness verdict: **GO**, **CONDITIONAL**, or **NOT_READY**

---

### Step 6 — Certification Recommendation

If your verdict is **GO**, the **CertRecommendationAgent** provides:
- Final **GO / CONDITIONAL / NOT YET** recommendation
- Confidence note and any corrective actions for weak domains
- 2 next certification suggestions based on the **SYNERGY_MAP**
- A motivational note with scheduling advice

---

## Resuming a Session

CertPrep uses checkpoint storage — your progress is saved automatically. If you close the browser or the session times out:

1. Re-open `http://localhost:8501`
2. Click **🔄 New Session** only if you want to start over — otherwise, your previous conversation and HITL gate state will be restored.

> **Note:** Checkpoint files are stored in `~/.certprep_maf/checkpoints/`. Each session gets its own file named by session ID.

---

## Sidebar Features

| Control | Description |
|---------|-------------|
| **Session ID** | Unique identifier for your current session (first 8 chars shown) |
| **🔄 New Session** | Clears all session state and starts fresh |
| **About** | Lists all 7 agents, framework, checkpoint storage, and tracing info |

---

## Supported Exams

| Exam | Full Name |
|------|-----------|
| **AI-102** | Designing and Implementing a Microsoft Azure AI Solution |
| **DP-100** | Designing and Implementing a Data Science Solution on Azure |
| **AZ-900** | Microsoft Azure Fundamentals |

More exams can be added by extending `_EXAM_BLUEPRINTS` in `src/maf/agents/study_plan_agent.py`.

---

## Common Questions

**Can I change my exam target mid-session?**  
Yes — just tell the agent "I want to switch to DP-100" and the OrchestratorAgent will re-route to a new profiling session.

**What happens if my score is NOT_READY?**  
The system automatically rebuilds a focused study plan targeting only your weak domains. You will not be told to book the exam until your ReadinessScore reaches the threshold.

**Is my data saved between app restarts?**  
Checkpoint files in `~/.certprep_maf/checkpoints/` persist between Streamlit restarts. For full persistence across machines, configure a shared storage backend (planned for Phase 2).

**What if I don't have Azure credentials?**  
The app requires `AZURE_AI_PROJECT_CONNECTION_STRING` to start agent runs. Without it, you will see an error in the chat. Configure your `.env` file before launching.
