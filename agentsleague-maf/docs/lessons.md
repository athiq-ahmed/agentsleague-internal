# 📚 Lessons Learned — CertPrep MAF

> **Purpose:** After every correction, bug fix, or AI-assisted change, record the lesson here.
> This file is the **compounding intelligence layer** — correct earlier, compound faster.
>
> **When to update:** Any time a task is corrected, reverted, or required a non-obvious fix.
> **Format:** Add to the TOP of the log (newest first).

---

## Log

### 2026-03-24 — Package renamed: cert_prep_maf → maf

| Field | Details |
|-------|---------|
| **What went wrong** | Initial package was created as `src/cert_prep_maf/maf/` — two levels of nesting adding no value. Every import was `from cert_prep_maf.maf.X import` which is verbose and unintuitive. |
| **Root cause** | Package name was chosen as a mirror of the foundry-sdk name (`cert_prep`) without reconsidering whether the wrapper level was needed in a greenfield MAF project. |
| **Fix applied** | Moved `src/cert_prep_maf/maf/` → `src/maf/`. Updated all 24 import references across agents, workflow, and Streamlit app. Merged sys.path bootstrap into `src/maf/__init__.py`. |
| **Prevention rule** | For any new project, decide final package name before creating files. A flat `src/<package>/` is almost always better than `src/<project>/<package>/`. Check with `find src/ -type d` before writing the first import. |

---

### 2026-03-24 — Initial MAF implementation created

| Field | Details |
|-------|---------|
| **Decision** | Adopted WorkflowBuilder as primary orchestration pattern (not just HandoffBuilder). Added FileCheckpointStorage for HITL gate persistence. Used 3 middleware types matching all three MAF middleware base classes. |
| **Key pattern learned** | WorkflowBuilder + HandoffBuilder are complementary, not alternatives. HandoffBuilder handles the outer "what do you want?" conversation; WorkflowBuilder handles the inner deterministic pipeline. Use both. |
| **MCP lesson** | `MCPStreamableHTTPTool` is registered as a tool on a specific agent (`PathCuratorAgent`), not globally. This keeps MCP scope narrow and prevents accidental MS Learn queries from other agents. |
| **Checkpoint lesson** | `FileCheckpointStorage` requires the checkpoint directory to exist or be auto-created. Use `Path.home() / ".certprep_maf" / "checkpoints"` for cross-platform consistency. |
| **OTEL lesson** | `configure_otel_providers()` must be called before any agent runs. In Streamlit, call it at module level (outside of function definitions) so it runs once on startup, not on every rerender. |

---

## Meta-Rules (Extracted from All Lessons)

1. **Flat package structure** — `src/maf/` not `src/project/maf/`. Decide name before writing first file.
2. **WorkflowBuilder + HandoffBuilder** — use both: HandoffBuilder for conversational triage, WorkflowBuilder for the deterministic pipeline inside.
3. **MCP tool scope** — register `MCPStreamableHTTPTool` only on the agent that needs it; do not add it globally.
4. **OTEL at startup** — call `configure_otel_providers()` once at module import time, not inside Streamlit callbacks.
5. **Checkpoint directory** — use `Path.home() / ".app" / "checkpoints"` pattern for cross-platform storage.
6. **Import from foundry-sdk** — verify the `sys.path` bootstrap resolves correctly before writing any import statement. Run a quick `python -c "from maf import *"` check.
7. **Grep before documenting** — before describing any feature as "active", grep the actual source files to confirm it is wired. Never document from memory.
8. **Versioned prompts** — keep all system prompts in `.md` files under `prompts/`. Never inline long instructions directly in Python strings — they become untestable and version-untrackable.
