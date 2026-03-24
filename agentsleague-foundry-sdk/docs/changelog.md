# 📋 Changelog — Agents League Battle #2

All notable changes to this project are documented here in reverse-chronological order.

---

| Date | Change | Details |
|------|--------|---------|
| **2026-02-28** | **Demo UX + Admin Dashboard polish** | Both sidebar scenario buttons (Novice + Expert) now represent **Alex Chen** at different experience levels; Expert prefill defaults role to *Data Analyst / Scientist*; login card updated to "Returning · DP-100" for AI Expert; Admin Dashboard demo/synthetic data warning removed; agent I/O cards drop internal `id:` label; status badge changed from low-contrast green "success" to white **✓ Completed / ⚠ Review / ✗ Failed** |
| **2026-02-27** | **Expert demo scenario → AI-102; both personas now AI-102** | Changed second demo persona (Priyanka Sharma) from DP-100 data scientist to AI-102 expert; seed uses `INSERT OR REPLACE` so DB row refreshes on next app start; cache-aware spinner added then refined to keep cache internal; hero text updated to reflect actual stack (Azure Content Safety + SQLite) |
| **2026-02-27** | **Live mode default + rerun survival** | `_live_mode_pref` non-widget session key added; defaults to `True` when Azure credentials are present; survives partial reruns caused by sidebar demo scenario button clicks |
| **2026-02-27** | **SQLite-backed LLM response cache — 352 tests** | `database.py` adds `llm_response_cache` table; `b0_intake_agent._call_llm()` wraps every Foundry/OpenAI call with SHA-256 cache key (`tier :: model :: prompt`); cache hit skips API call entirely; eliminates repeat latency (p50 3–5 s → ~0 ms on cache hit); write/read errors silently swallowed — pipeline never fails due to cache; suite grown 342 → **352 passing** |
| **2026-03-01** | **Agent evaluation suite — 342 tests** | Added `test_agent_evals.py`: 7 rubric-based eval classes (E1–E7), 53 tests covering all 6 agents + full pipeline; suite grown 289 → **342 passing** |
| **2026-02-25** | **Comprehensive audit — 289 tests** | Full proactive audit of every tab, block, and section; 5 bugs fixed; 34 new tests added (`test_serialization_helpers.py` + extended `test_progress_agent.py`); suite grown 255 → **289 passing** |
| **2026-02-25** | **Serialization hardening** | `_dc_filter()` helper added; all 6 `*_from_dict` helpers silently drop unknown keys — prevents `TypeError` crashes on schema-evolution round-trips from SQLite |
| **2026-02-25** | **Safe enum coercion** | `ReadinessVerdict` / `NudgeLevel` casts fall back to `NEEDS_WORK`/`INFO` instead of raising `ValueError` on stale stored values |
| **2026-02-25** | **Per-exam domain weights** | `ProgressAgent.assess()` now calls `get_exam_domains(profile.exam_target)` — DP-100, AZ-204, AZ-305, AI-900 readiness uses correct per-exam weights |
| **2026-02-25** | **Checklist key fix** | Booking-checklist `st.checkbox` key simplified from `hash()[:8]` (TypeError) to `abs(hash(_item))` |
| **2026-02-25** | **Admin Dashboard type fix** | `history_df` `risk_count` fallback changed from `"—"` (str) to `None` so `NumberColumn` renders cleanly |
| **2026-02-25** | **`exam_weight_pct` fix** | `Recommendations` tab: `getattr` fallback with equal-weight distribution (commit `cb78946`) |
| **Earlier** | **Demo PDF cache system** | `demo_pdfs/` folder + `_get_or_generate_pdf()` — demo personas serve PDFs from disk on repeat clicks |
| **Earlier** | **PDF generation stability** | Fixed `AttributeError` crashes in `generate_profile_pdf()` and `generate_intake_summary_html()` |
| **Earlier** | **Technical documentation** | Added `docs/technical_documentation.md` — 850-line deep-dive into agent internals, algorithms, data models |
| **Earlier** | **9-cert registry** | Expanded from 5 to 9 exam families with full domain-weight matrices |
| **Earlier** | **Email digest** | SMTP simplified to env-vars only — no UI config needed |
