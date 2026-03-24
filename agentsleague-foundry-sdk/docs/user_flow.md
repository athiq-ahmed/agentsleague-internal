# User Flow — Certification Preparation Multi-Agent System

> **Audience:** Product reviewers, UX evaluators, and stakeholders wanting to understand how learners and administrators interact with the system.  
> **Format:** Master pipeline topology, per-scenario ASCII flows, and step-by-step prose walkthroughs for all eight scenarios.

---

## Master Pipeline Topology

```
 Browser (Student)
     │
     │  Open app
     ▼
 ┌───────────────────────────────────────────────────────────┐
 │  Login Screen                                                          │
 │  ┌────────────────┐  ┌───────────────────────────┐          │
 │  │ New → Register │  │ Returning → Login + restore  │          │
 │  └─────┬────────┘  └──────────┬────────────────┘          │
 └─────────────────────┬───────────┬─────────────────────────┘
                      │ new user   │ returning user
                      ▼           │
              Intake Form         │ profile loaded from SQLite
                      │           │
                      ▼           ▼
              ┌──────────────────────────────┐
              │  GuardrailsPipeline [G-01 → G-05]     │
              │  BLOCK → st.stop() | PASS → continue  │
              └───────────────┬──────────────┘
                             │ PASS
                             ▼
              ┌──────────────────────────────┐
              │  B0  LearnerProfilingAgent            │
              │  Tier 1: Foundry SDK                  │
              │  Tier 2: Azure OpenAI gpt-4o           │
              │  Tier 3: Rule-based mock (always on)  │
              └───────────────┬──────────────┘
                             │ LearnerProfile
              ┌───────────────┬──────────────┘
              │  GuardrailsPipeline [G-06 → G-08]    │
              └───────────────┬──────────────┘
                             │ PASS
               ┌──────────┴──────────┐
               │ Thread A          │ Thread B
               ▼                  ▼
 ┌───────────────────┐ ┌───────────────────┐
 │ B1.1a StudyPlanAgent  │ │ B1.1b LearningPath    │
 │ Largest Remainder     │ │ Curator + G-17 check  │
 └──────────┬────────┘ └──────────┬────────┘
               └──────────┴──────────┘
                             │ persisted to SQLite
                             ▼
                    ┌───────────────────┐
                    │  7-Tab UI renders         │
                    └───────────────────┘
             ┌───────┴────────┴────────┴───────┐
             ▼              ▼              ▼              ▼
         Tab 1–3       HITL Gate 1      HITL Gate 2    Tab 4
        (read-only)    Tab 5 Progress   Tab 6 Quiz   (unlocks after
                           │               │          quiz submitted)
                           ▼               ▼
                    B1.2 ProgressAgent  B2 AssessmentAgent
                    readiness formula   configurable quiz (5–30, default 10)
                           │               │
                    ┌──────┴──────┐       │ scored result
                    ▼      ▼      ▼       ▼
                   GO    COND   NOT      B3 CertRecommendationAgent
                         GO    YET ───► Rebuild plan → B1.1a
                    └──────┘       │
                                   ▼
                          Tab 4: Recommendations
                               Booking checklist
                               or Remediation plan
```

---

## Table of Contents

1. [S1 — New Learner: First-Time Happy Path](#s1--new-learner-first-time-happy-path)
2. [S2 — Returning Learner: Session Restore](#s2--returning-learner-session-restore)
3. [S3 — Live Azure OpenAI Mode](#s3--live-azure-openai-mode)
4. [S4 — Admin Audit Dashboard](#s4--admin-audit-dashboard)
5. [S5 — Remediation Loop: Score Below Threshold](#s5--remediation-loop-score-below-threshold)
6. [S6 — Edit Profile: Re-running the Pipeline](#s6--edit-profile-re-running-the-pipeline)
7. [S7 — Guardrail BLOCK Scenarios](#s7--guardrail-block-scenarios)
8. [S8 — PII in Background Text](#s8--pii-in-background-text)

---

## S1 — New Learner: First-Time Happy Path

```
 Browser
   │ open app
   ▼
 Login Screen → Register (name + PIN)  →  logged in
   │
   ▼
 Sidebar: click scenario card → intake form pre-filled
   │
   ▼
 [G-01–G-05 all PASS]
   │
   ▼
 B0 Mock Profiler → LearnerProfile (INTERMEDIATE, LAB_FIRST, 6 domains)
   │
   ▼
 [G-06–G-08 all PASS]
   │
   ├───────────────────┐
   ▼ Thread A          ▼ Thread B
 B1.1a StudyPlan    B1.1b LearningPath  (parallel, ~12ms)
   └───────────────────┘
   │ persisted to SQLite
   ▼
 7-tab UI renders: Tab 1 (radar + PDF download)
   │
   ▼
 Tab 5 → HITL Gate 1: fill progress form → submit
   │
   ▼
 B1.2 ProgressAgent → readiness 74% → GO ✓
   │
   ▼
 Tab 6 → HITL Gate 2: answer questions (5–30, default 10) → submit
   │
   ▼
 B2 AssessmentAgent → score 78% → PASS
   │
   ▼
 B3 CertRecommendationAgent → ready to book + next cert AZ-204
   │
   ▼
 Tab 4: Recommendations / Booking checklist displayed
```

**Persona:** Alex Chen — a developer with 2 years of Azure experience targeting the AI-102 exam in 10 weeks, studying 8 hours per week.

**Preconditions:** No prior account. Mock mode active (no Azure credentials set).

1. Alex opens the app in a browser. The landing screen shows a login panel with three demo persona cards and a custom registration form.

2. Alex types a chosen username and a 4-digit PIN, then clicks **Register**. The system creates a new account in SQLite, stores the PIN as a SHA-256 hash, and logs Alex in.

3. In the sidebar, Alex sees the demo scenario cards. Alex clicks the **Alex Chen — AI-102** card. The intake form fields are immediately pre-filled with Alex's background text, exam target, hours per week, and study weeks.

4. The **Create My AI Study Plan** button becomes active because a scenario was selected with a non-empty background. Alex clicks it.

5. The guardrail pipeline runs input checks G-01 through G-05. All pass (background is filled, exam target is valid, hours and weeks are in range). No guardrail banners appear.

6. The `LearnerProfilingAgent` (B0) runs in mock mode, parsing Alex's background text using keyword rules. It identifies Alex as `INTERMEDIATE` experience level with `LAB_FIRST` learning style and distributes confidence scores across all six AI-102 domains.

7. After the profile is built, the guardrail pipeline runs profile checks G-06 through G-08. The number of `DomainProfile` objects matches the six-domain AI-102 registry. All confidence scores are in range. No violations.

8. The `StudyPlanAgent` (B1.1a) and `LearningPathCuratorAgent` (B1.1b) run in parallel. The study plan allocates 80 study hours across the six domains using the Largest Remainder algorithm. The learning path curator selects 3 Microsoft Learn modules per domain, ordered with labs first to match Alex's learning style.

9. On completion, the seven-tab UI renders. Alex is on **Tab 1: 🗺️ Domain Map**, which shows a domain radar chart, confidence score bars, and an exam score contribution bar chart. Two buttons appear at the bottom: **Download PDF Report** and an email button showing "No email configured" (greyed out with a tooltip).

10. Alex clicks **Download PDF Report**. A multi-page PDF downloads immediately, containing the domain confidence breakdown, study plan Gantt table, and full learning path.

11. Alex navigates to **Tab 2: Study Setup**, which shows a Gantt chart with colour-coded study blocks per domain and a weekly hour breakdown. A note indicates no prerequisite gap (AZ-900 is listed as owned).

12. Alex navigates to **Tab 3: Learning Path**, which shows 18 MS Learn module cards across all six domains. Each card shows a clickable link to `learn.microsoft.com`, the module type (lab, module, or learning path), and estimated hours.

13. After several study weeks, Alex returns to the app and navigates to **Tab 5: My Progress**. The progress check-in form appears. Alex fills in hours spent (32 out of 80), rates each domain's self-confidence on a 1–5 slider, enters a practice exam score of 74, and submits.

14. The `ProgressAgent` computes the readiness percentage using the weighted formula and returns a **GO** verdict (readiness above 70%). A green success banner appears. The nudges section lists one suggestion: "Computer Vision scored below 0.50 — complete 2 additional practice labs."

15. Alex navigates to **Tab 6: Knowledge Check**. A quiz appears (10 questions by default, adjustable via slider to 5–30), with questions distributed across all six AI-102 domains proportionally. Alex answers all questions and clicks **Submit Quiz**.

16. The `AssessmentAgent` scores the submission with a weighted domain score of 78%. The result panel shows PASS, a domain-by-domain breakdown bar chart, and highlights Computer Vision as the lowest scoring domain at 63%.

17. The `CertRecommendationAgent` (B3) runs and the result appears in **Tab 4: Recommendations**. Alex is marked as ready to book the real exam. The booking checklist includes steps for Pearson VUE registration, accepted ID types, and the recommended study week before booking. The next-cert recommendation suggests AZ-204 as the logical progression after AI-102.

---

## S2 — Returning Learner: Session Restore

```
 Browser
   │ open app
   ▼
 Login Screen → enter existing name + PIN → Login
   │
   ▼
 SQLite lookup → row found
   │
   ▼
 Session state populated:
   LearnerProfile + StudyPlan + LearningPath
   + ProgressSnapshot + ReadinessAssessment
   (no agents re-run)
   │
   ▼
 7-tab UI renders immediately (all tabs populated, read-only)
   │
   ├─ Tab 1: domain radar + PDF download  (available)
   ├─ Tab 2: Gantt chart                  (available)
   ├─ Tab 3: learning path modules        (available)
   ├─ Tab 4: cert recommendations         (available)
   ├─ Tab 5: last readiness assessment    (interactive for new update)
   ├─ Tab 6: last quiz score              (interactive for re-take)
   └─ Tab 7: raw JSON                     (available)
```

**Persona:** Priyanka Sharma — a data scientist who previously completed the DP-100 study plan and saved all results. Returning to review her plan after two weeks away.

**Preconditions:** Priyanka has a prior account with a saved learner profile, study plan, learning path, and progress snapshot in SQLite.

1. Priyanka opens the app and types her username and PIN, then clicks **Login**.

2. The system finds a prior profile in SQLite. Session state is populated immediately with her `LearnerProfile`, `StudyPlan`, `LearningPath`, and the most recent `ProgressSnapshot` and `ReadinessAssessment` — no agents re-run.

3. The seven-tab UI renders with a notification at the top: "Welcome back, Priyanka — your DP-100 plan has been restored."

4. All tabs are populated. Priyanka can see her domain confidence radar (Tab 1), her study Gantt chart (Tab 2), her 12 learning path modules (Tab 3), her cert recommendations (Tab 4), her last readiness verdict — **CONDITIONAL GO** at 61% — with the domain nudges from her previous session (Tab 5), and her last quiz score (68%) in Tab 6.

5. The data is in read-only viewing mode. Priyanka can download her PDF using the button on Tab 1 and review her entire history without triggering any agent calls.

6. If Priyanka wants to update her progress or re-take the quiz, she navigates to Tabs 5 and 6 respectively, which remain interactive for new submissions.

---

## S3 — Live Azure OpenAI Mode

```
 App starts with AZURE_OPENAI_ENDPOINT + KEY in .env
   │
   ▼
 Sidebar badge: • Azure OpenAI: gpt-4o (green)
   │
   ▼
 Intake form submitted → [G-01–G-05 PASS]
   │
   ▼
 B0 LearnerProfilingAgent  (three-tier attempt)
   │
   ├── Tier 1: Foundry SDK (AZURE_AI_PROJECT_CONNECTION_STRING set?)
   │         └─► success → LearnerProfile
   │
   ├── Tier 2: Azure OpenAI gpt-4o JSON mode  (3–8 seconds)
   │         └─► success → LearnerProfile
   │
   └── Tier 3: Rule-based mock  (auto-fallback if JSON malformed)
             └─► LearnerProfile + WARN logged
   │
   ▼
 All downstream agents (B1.1a, B1.1b, B1.2, B2, B3) unchanged
   (deterministic — no LLM calls below B0)
   │
   ▼
 Admin trace: mode = azure_openai | B0 token_count > 0 | duration ~5s
```

**Persona:** A demo organiser running the app with Azure OpenAI credentials set for a live demonstration.

**Preconditions:** `.env` file or Streamlit secrets contain valid `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` values.

1. The app starts. The sidebar mode badge shows **Azure OpenAI: gpt-4o** in green, replacing the default **Mock Mode** badge.

2. A learner fills in the intake form with a custom background description and clicks **Create My AI Study Plan**.

3. After guardrail input checks pass, the `LearnerProfilingAgent` (B0) attempts to use the Azure AI Foundry Agent Service SDK first (Tier 1). If `AZURE_AI_PROJECT_CONNECTION_STRING` is not set, it falls back to the direct Azure OpenAI API call (Tier 2).

4. A spinner with the message "Analysing your background with Azure OpenAI gpt-4o…" appears while the LLM call completes. This typically takes 3–8 seconds.

5. The LLM response is parsed into a `LearnerProfile`. If the JSON is malformed or missing required fields, the profiler automatically falls back to the rule-based mock engine (Tier 3) and logs a WARN in the trace.

6. From this point, the pipeline is identical to mock mode — all downstream agents (B1.1a, B1.1b, B1.2, B2, B3) are deterministic and do not call the LLM. Only B0 uses the LLM.

7. In the Admin Dashboard trace log, the run appears with `mode: azure_openai` and the B0 step shows non-zero `token_count` and a `duration_ms` of several thousand milliseconds versus under 50ms in mock mode.

---

## S4 — Admin Audit Dashboard

```
 Browser → /pages/1_Admin_Dashboard
   │
   ▼
 Admin login form → ADMIN_USERNAME + ADMIN_PASSWORD
   │ wrong → error banner
   │ correct
   ▼
 ┌───────────────────────────────────┐
 │  Admin Dashboard (reads only SQLite)  │
 ├───────────────────────────────────│
 │ Student Roster      (all students)    │
 │ Agent Trace Log     (per-run cards)   │
 │ Guardrail Audit     (all violations)  │
 └───────────────────────────────────┘
   │
   └─ Violation: G-16 WARN → amber row
   └─ Violation: G-03 BLOCK → red row
   └─ Trace card: mode badge (mock=grey | azure=blue)
                each AgentStep: name + duration_ms
```

**Persona:** An administrator or facilitator reviewing learner activity after a group demo event.

**Preconditions:** `ADMIN_USERNAME` and `ADMIN_PASSWORD` are set in `.env`. The event had 8 unique learner sessions.

1. The admin navigates to `/pages/1_Admin_Dashboard` in the browser.

2. An admin login form appears. The admin enters their credentials and clicks **Login**. A wrong password shows an error; a correct one advances to the dashboard.

3. The **Student Roster** section renders a table with all 8 students, their exam targets, registration dates, and whether they completed the full pipeline or stopped mid-way.

4. The **Agent Trace Log** section shows a card per pipeline run, colour-bordered by mode (grey for mock, blue for Azure OpenAI). Each card lists every `AgentStep` with its name, duration in milliseconds, and a truncated output summary.

5. The **Parallel Execution** row within trace cards shows the wall-clock time for the `StudyPlanAgent` + `LearningPathCuratorAgent` fan-out — consistently under 30ms in mock mode.

6. The **Guardrail Audit** section provides a searchable table of all guardrail violations across all sessions. Violations at level BLOCK appear with a red indicator, WARN with amber, and INFO with blue. The admin can filter by code (e.g., G-03 to see everyone who entered invalid study hours).

7. The admin notices three G-16 WARN violations from one session. They click to expand and see that the learner's background text contained an email address pattern. The pipeline was not blocked; the PII WARN was logged and the pipeline continued.

---

## S5 — Remediation Loop: Score Below Threshold

```
 Tab 5 → HITL Gate 1
   │ 20hrs studied, ratings 2-3/5, practice 42%
   ▼
 B1.2 ProgressAgent
   readiness = 0.55×47% + 0.25×50% + 0.20×42% = 47.4%
   │
   ▼
 Verdict: NOT YET ❌
   │
   ▼
 2 weak domains identified → nudges displayed
   │
   ▼
 [Regenerate Study Plan] button shown
   │ user clicks
   ▼
 Weak domain confidence reset to 0.25 (WEAK)
   │
   ├───────────────────┐
   ▼ Thread A          ▼ Thread B
 B1.1a StudyPlan    B1.1b LearningPath  (re-run, parallel)
 (weak domains      (additional labs
  front-loaded)      for weak domains)
   └───────────────────┘
   │
   ▼
 Tab 2 refreshes → rebalanced Gantt chart
   │
   ▼
 Learner studies → returns for new Gate 1 check-in
```

**Persona:** Jordan — a learner who submitted their progress check-in with only 20 hours studied out of 40 budgeted and a practice score of 42%.

**Preconditions:** Jordan has a study plan; this is their first progress check-in submission.

1. Jordan fills in the progress form showing 20 hours spent, domain ratings of mostly 2s and 3s, and a practice exam score of 42. Jordan submits.

2. The `ProgressAgent` computes: readiness = 0.55 × 47% + 0.25 × 50% + 0.20 × 42% = 47.4%. Verdict: **NOT YET**.

3. A red warning panel appears: "You're not quite ready — we recommend more preparation before booking." Below it, the nudges section lists two specific domains to re-focus on, with suggested module types.

4. A **Regenerate Study Plan** button appears. Jordan clicks it.

5. The system resets the domain confidence scores for the two weak domains to `WEAK` (confidence 0.25) and re-runs `StudyPlanAgent` with the updated profile. The new plan front-loads the weak domains into the first three weeks and increases their allocated hours.

6. `LearningPathCuratorAgent` also re-runs and presents additional lab-type resources for the weak domains.

7. Tab 2 refreshes with the regenerated Gantt chart. Jordan can see the rebalanced allocation and returns to studying.

---

## S6 — Edit Profile: Re-running the Pipeline

```
 Tab 1 (Learner Profile)
   │
   ▼
 [Edit Profile] button → clicked
   │
   ▼
 6 tabs collapse → intake form re-appears (pre-filled)
   │ user changes exam: AI-900 → AI-102
   │ clicks [Update Plan]
   ▼
 [G-01–G-05 PASS]
   │
   ▼
 B0 → new LearnerProfile (6 AI-102 domains)
   │
   ├───────────────────┐
   ▼ Thread A          ▼ Thread B
 B1.1a StudyPlan    B1.1b LearningPath  (parallel)
 (AI-102 6 domains)  (AI-102 modules)
   └───────────────────┘
   │ replaces prior SQLite records
   ▼
 6-tab UI re-renders with AI-102 content
 "✓ Your plan has been updated for AI-102"
```

**Persona:** Sam — a learner who initially targeted AI-900 but updated their goal to AI-102 after one week.

**Preconditions:** Sam has a complete profile and study plan for AI-900 in session state.

1. Sam navigates to Tab 1 (Learner Profile). An **Edit Profile** button appears in the top-right corner of the profile card.

2. Sam clicks **Edit Profile**. The six tabs collapse and the intake form re-appears, pre-filled with Sam's current values — the background text, study hours (8 hours per week), and study weeks (8 weeks). The exam target dropdown shows AI-900 selected.

3. Sam changes the exam target from AI-900 to AI-102 and clicks **Update Plan**.

4. The guardrail input checks run again. All pass. The full 8-agent pipeline re-runs from the beginning: B0 (profiling), B1.1a + B1.1b (parallel plan and path), and the output replaces all prior session state and SQLite records for Sam.

5. The six tabs re-render with AI-102 content. The profile card shows six domains instead of five, and the study plan Gantt reflects the longer AI-102 scope. A subtle banner confirms: "Your plan has been updated for AI-102."

---

## S7 — Guardrail BLOCK Scenarios

```
 Intake form submitted
   │
   ▼
 GuardrailsPipeline
   │
   ├── G-02: exam = "AZ-999" not in registry
   │         └─► BLOCK ❌  red banner  → st.stop()
   │                     user must fix exam code
   │
   ├── G-03: hours_per_week = 0.5  (outside [1, 80])
   │         └─► BLOCK ❌  red banner  → st.stop()
   │
   ├── G-04: weeks = 60  (outside [1, 52])
   │         └─► BLOCK ❌  red banner  → st.stop()
   │
   └── G-10: allocated hours > 110% of budget
             └─► WARN ⚠️  amber banner → pipeline continues

 All BLOCK violations: no agent runs, violation logged to SQLite
 All WARN violations:  pipeline proceeds, violation logged
```

**Persona:** A learner who makes several common input mistakes on the intake form.

### Scenario 7a — Invalid Exam Target

1. The learner types "AZ-999" into the exam target field and submits. The G-02 BLOCK rule fires. A red banner reads: "AZ-999 is not a supported exam. Please select from the supported list." `st.stop()` halts the pipeline. The learner must correct the exam target before proceeding.

### Scenario 7b — Hours Out of Range

1. A learner sets hours per week to 0.5, below the minimum of 1. The G-03 BLOCK fires with the message: "Hours per week must be between 1 and 80." The pipeline halts. The learner changes the slider to 5 and resubmits successfully.

### Scenario 7c — Weeks Out of Range

1. A learner enters 60 weeks, above the maximum of 52. The G-04 BLOCK fires: "Weeks available must be between 1 and 52." The pipeline halts.

### Scenario 7d — Study Plan Hours Overrun

1. In an edge case where the total allocated hours exceed 110% of the budget (G-10), a WARN banner appears with the message: "Allocated study hours exceed your weekly budget by more than 10% — the plan may be overloaded." Unlike BLOCKs, the pipeline continues and the learner can proceed, noting the advisory.

---

## S8 — PII in Background Text

```
 Intake form → background text field
   │
   ▼
 GuardrailsPipeline G-16 content scanner
   │
   ├── Email pattern detected  (sam@company.com)
   │         └─► WARN ⚠️  amber banner
   │              pipeline continues
   │              PII not forwarded to LLM (mock mode)
   │
   ├── Credit card pattern detected  (16-digit sequence)
   │         └─► WARN ⚠️  amber banner
   │              pipeline continues
   │              user advised to remove before live session
   │
   └── Harmful keyword detected  (prohibited blocklist)
             └─► BLOCK ❌  red banner  → st.stop()
                  violation code + timestamp logged
                  content itself NOT persisted
```

**Persona:** A learner who accidentally pastes personal information into the background text field.

### Scenario 8a — Email Address (WARN, continues)

1. The learner types a background description that includes their email address: "I'm an engineer at company.com — contact me at sam@company.com for more details."

2. The G-16 content scanner detects the email pattern `sam@company.com`. A WARN-level amber banner appears: "[G-16] Personal email address detected in your background text — please review before submitting to an AI service." The pipeline continues. In mock mode, the email address is not forwarded to any LLM.

### Scenario 8b — Credit Card Number (WARN, continues)

1. A learner copies from a notes document that accidentally contains a card number in sequence: "My Pearson VUE booking ref was near 4111 1111 1111 1111 in my notes."

2. G-16 detects the credit card pattern. An amber banner warns the learner. The pipeline continues but the learner is advised to remove the number before proceeding with a live Azure OpenAI session.

### Scenario 8c — Harmful Keyword (BLOCK, halts)

1. A learner's background text contains a flagged keyword from the prohibited content blocklist.

2. G-16 fires at BLOCK level. A red banner appears: "[G-16] Your background text contains content that cannot be processed. Please revise it." `st.stop()` prevents any agent from running. The violation is logged to SQLite for admin review, but the content itself is never persisted — only the violation code and timestamp are stored.
