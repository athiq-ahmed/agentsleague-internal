# 📚 Lessons Learned — Self-Improvement Log

> **Purpose:** After every correction, bug fix, or AI-assisted change, record the lesson here.  
> This file is the **compounding intelligence layer** — the mistake rate drops over time because we actively learn from each incident.
>
> **When to update:** Any time a task is corrected, reverted, or required a non-obvious fix.  
> **Format:** Add to the TOP of the log (newest first).

---

## Log

### 2026-02-27 — Metrics table had mock-mode values; docs had stale test counts and "roadmap" labels for shipped features

| Field | Details |
|-------|----------|
| **What went wrong** | README `System Metrics` table mixed mock-mode rows ("Pipeline Completion Rate — Mock", "Agent Latency — Mock") alongside live-mode rows, making it impossible for judges to quickly assess live system quality. Additionally, `Responsible AI Coverage` was listed as 85% with "Content Safety API roadmap" despite the API being fully wired. Test counts stagnated at 289/299 in Competition Alignment, Engineering Best Practices, and Starter Kit Alignment tables. `docs/TODO.md` sprint still showed T-07 and T-09 as NOT STARTED despite both being done. |
| **Root cause** | The metrics section was written before T-07/T-09 were implemented and was never updated in the same commit as the implementation. Mock-mode rows were added for completeness but create noise in a competition context where judges are evaluating live system quality. |
| **Fix applied** | (1) Removed all mock-only metric rows from README. (2) Added "all values are live-mode" header note. (3) Added new rows for Content Safety API detection rate (~95%), T1/T2 latency separately, and LLM eval scores (Coherence/Relevance via `eval_harness.py`). (4) RAI coverage updated 85% → 100%. (5) All stale 289/299 counts updated to 342 across README, `docs/technical_documentation.md`, `docs/qna_playbook.md`. (6) TODO.md T-07/T-09 marked DONE; Content Safety and eval harness items ticked in Completed section. |
| **Prevention rule** | When implementing a feature that closes a "roadmap" item, immediately do a workspace-wide grep for the sprint task ID (e.g. T-07) and the old status text ("NOT STARTED", "roadmap", "stub") — update all matches in the same commit. Metrics tables require a separate pass: grep for mock-only qualifier text and either remove or annotate clearly. |

### 2026-02-25 — Nested f-string `_rows_html` in `st.markdown()` caused raw HTML display

| Field | Details |
|-------|---------|
| **What went wrong** | Azure Services Status panel displayed raw HTML text instead of a rendered checklist when Live Mode toggle was clicked. |
| **Root cause** | `_rows_html` was built via a loop of f-strings (multi-line, deeply indented), then embedded as `{_rows_html}` inside a second outer `st.markdown(f"""...""")` call. Streamlit's markdown pre-processor treated the indented multi-line HTML block as a fenced code block before `unsafe_allow_html` could act on it. |
| **Fix applied** | Replaced the single outer f-string + `_rows_html` pattern with: (1) a flat header `st.markdown()` built via string concatenation (no multi-line f-string nesting), and (2) a loop using `st.columns([0.5, 6.5, 2.0])` where **each column gets its own isolated `st.markdown()` call** — no nesting, no ambiguity. |
| **Prevention rule** | Never embed a multi-line HTML variable via `{var}` inside another `st.markdown()` f-string. Each logical HTML block must be its own standalone `st.markdown()` call. Prefer `st.columns()` over HTML grid CSS for service/checklist rows. |

---

### 2026-02-24 — Foundry Best Practices section initially missing; tasks/ folder wrong location

| Field | Details |
|-------|---------|
| **What went wrong** | The `tasks/` folder was created at workspace root instead of inside `docs/` where all documentation lives. Additionally, the Foundry Best Practices section (telemetry, monitoring, evaluation, Responsible AI) was not explicitly mapped in README despite most of it being implemented. |
| **Root cause** | Files created in the first available path without checking existing folder conventions. Section written as a summary table without explicit traceability to each starter kit bullet point. |
| **Fix applied** | `tasks/lessons.md` → `docs/lessons.md` and `tasks/todo.md` merged into `docs/TODO.md` (sprint section added). New `## 📡 Microsoft Foundry Best Practices — Implementation Status` section added to README with per-bullet honest status, evidence, and honest gaps table. |
| **Prevention rule** | Before creating any new file, run `Get-ChildItem docs/` to check existing folder conventions. When documenting "best practices", explicitly number and map each upstream bullet point rather than summarising. |

---

### 2026-02-24 — Email service reference was wrong across multiple files

| Field | Details |
|-------|---------|
| **What went wrong** | `docs/TODO.md` Section D and several README rows described Azure Communication Services (ACS) as the email implementation. The actual code in `b1_2_progress_agent.py` uses Python `smtplib` reading `SMTP_*` env vars. `AzureCommConfig` in `config.py` is dead code — never called by the email-sending function. |
| **Root cause** | Initial scaffolding was planned with ACS, but the implementation used simpler SMTP. Documentation was not updated to reflect the actual build. |
| **Fix applied** | `.env.example` section [4] rewritten with `SMTP_*` vars; ACS moved to `[4b]` marked "NOT used by current implementation". `docs/TODO.md` Section D rewritten with SMTP setup instructions. README Azure Services table split into "SMTP Email (current)" + "ACS (roadmap)" rows. |
| **Prevention rule** | Before documenting any Azure service as active, grep for its config class / env var pattern in the actual service implementation files to confirm it is called. |

---

### 2026-02-24 — Azure AI Foundry config existed but was never called

| Field | Details |
|-------|---------|
| **What went wrong** | `AzureFoundryConfig` and `AZURE_AI_PROJECT_CONNECTION_STRING` existed in `config.py` and `.env.example` but `LearnerProfilingAgent` only instantiated `AzureOpenAI` directly — Foundry SDK was never invoked. Documentation incorrectly described Foundry as active. |
| **Root cause** | Config scaffolding was added speculatively but the implementation was never wired to it. |
| **Fix applied** | `LearnerProfilingAgent` rebuilt with 3-tier execution: Tier 1 `AIProjectClient` (Foundry Agent Service SDK), Tier 2 direct `AzureOpenAI`, Tier 3 raise `EnvironmentError`. `using_foundry` flag exposed for UI reporting. `azure-ai-projects>=1.0.0b9` and `azure-identity>=1.19.0` added to `requirements.txt` and installed. |
| **Prevention rule** | When a config class is added (`is_configured` property), immediately grep all agent files to verify it is actually referenced in the constructor or method. If not, mark it `# [STUB — not wired in production]` in comments. |

---

### 2026-02-24 — Streamlit app crash loop (exit code 1) not diagnosed early enough

| Field | Details |
|-------|---------|
| **What went wrong** | Multiple `streamlit run` cycles all exited with code 1 without clear error surfacing. |
| **Root cause** | Process from previous run was still binding port 8501; additionally, an import error in a refactored agent file caused the crash. |
| **Fix applied** | Added `taskkill` + `netstat` port-cleanup step before each launch; added `py_compile` syntax check as first verification step before any launch attempt. |
| **Prevention rule** | **Verification order:** (1) `py_compile` first, (2) kill port 8501, (3) then launch. Never launch without step 1. |

---

### 2026-02-24 — README "What We Actually Use" table had stale Foundry status

| Field | Details |
|-------|---------|
| **What went wrong** | After Foundry SDK integration was implemented in code, the README still showed the Foundry row as "🗺️ Roadmap". |
| **Root cause** | Code and documentation were updated in separate passes; the README table was missed in the first multi-replace batch. |
| **Fix applied** | Second `multi_replace_string_in_file` pass targeted the exact table row text. |
| **Prevention rule** | When implementing a feature, do a `grep_search README.md` for the feature name immediately after the code change to find all stale documentation references in one pass. |

---

## Meta-Rules (Extracted from All Lessons)

1. **Grep before doc** — before describing a service/library as "active", grep for its usage in actual implementation files.
2. **py_compile first** — before any `streamlit run`, always run `py_compile` and confirm exit 0.
3. **Kill port, then launch** — always clear port 8501 before starting a new Streamlit process.
4. **Same-pass doc update** — when implementing a feature, update docs in the same commit, not a follow-up.
5. **Config stub tagging** — stub config classes that are not yet wired to implementations must be tagged `# [STUB — not wired in production]` so they are not mistakenly documented as active.
6. **Check folder conventions first** — before creating any new file, run `Get-ChildItem docs/` to confirm where similar files live; never create a new top-level folder for documentation.
7. **Explicit bullet traceability** — when documenting "best practices", number and individually map each upstream requirement bullet to code evidence rather than writing a summary; gaps must be explicitly labelled.

---

### Lesson 8 — Comprehensive Tab/Page Audit: Schema-Evolution Safety & Per-Exam Domain Weights

| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Session commit** | `997dde7` |
| **Tests before** | 255 passing |
| **Tests after** | 289 passing (+34) |

**Root causes & fixes applied:**

| # | Bug | Root Cause | Fix |
|---|-----|-----------|-----|
| 1 | `*_from_dict` helpers crash on schema-evolved SQLite JSON | `**d` unpacking passes all keys including unknown ones added by future schema changes | Added `_dc_filter(cls, d)` helper using `dataclasses.fields()` to whitelist only valid keys; applied to all 6 helpers |
| 2 | `ReadinessVerdict(d["verdict"])` raises `ValueError` on stale stored values | Enum cast has no safety fallback | Added membership check: `if raw_val in {e.value for e in ReadinessVerdict}` before cast; fallback to `NEEDS_WORK` |
| 3 | `NudgeLevel(n["level"])` same issue | Same | Added membership check with fallback to `NudgeLevel.INFO` |
| 4 | `hash(_item)[:8]` TypeError in booking checklist | `hash()` returns `int`, not subscriptable | Simplified to `abs(hash(_item))` |
| 5 | Admin Dashboard `history_df` `risk_count = "—"` (str) breaks `NumberColumn` | Mixed types in pandas column with typed column config | Changed fallback to `None` (pandas treats as NaN → NumberColumn renders blank correctly) |
| 6 | `ProgressAgent.assess()` uses `_DOMAIN_WEIGHT` (AI-102 only) for all exams | Module-level dict built from `EXAM_DOMAINS` only | Changed to call `get_exam_domains(profile.exam_target)` inside `assess()` to build per-exam weight map |

**Key learnings:**
- Always use `dataclasses.fields()` filtering before `**dict` unpacking into constructors — never assume JSON from persistent storage matches the current schema
- Enum casts from persisted strings must be validated before calling the constructor; use `.value` membership sets
- `hash()` always returns `int` in Python — never subscriptable
- Mixed-type pandas columns should use `None`/`np.nan` as empty value, never strings, when the column is typed
- Per-exam domain weights must be resolved at call time, not at module import time, for multi-cert systems
