# 📋 Changelog — CertPrep MAF

All notable changes to this project are documented here in reverse-chronological order.

---

| Date | Change | Details |
|------|--------|---------|
| **2026-03-24** | **Package renamed: cert_prep_maf → maf** | Flattened `src/cert_prep_maf/maf/` → `src/maf/`. All 24 import references updated. sys.path bootstrap merged into `src/maf/__init__.py`. |
| **2026-03-24** | **README.md created** | Full project README with architecture diagram, feature table, structure tree, setup instructions, and supported exams. |
| **2026-03-24** | **docs/ folder created** | 10 documents: technical_documentation, user_guide, user_flow, demo_guide, azure_ai_cost_guide, qna_playbook, unit_test_scenarios, lessons, changelog, TODO. |
| **2026-03-24** | **streamlit_app.py** | New Streamlit entry point using HandoffBuilder shell. Lazy agent init via `_get_shell()`. Session ID in sidebar. New Session reset button. |
| **2026-03-24** | **otel.py** | `configure_otel_providers()` — TracerProvider + MeterProvider wired to Azure Monitor. Optional ConsoleSpanExporter via `OTEL_CONSOLE=true`. |
| **2026-03-24** | **workflow/handoff_shell.py** | `build_handoff_shell()` — TriageAgent + `start_cert_prep_workflow` trigger tool + `HandoffBuilder` routing to `CertPrepWorkflow`. |
| **2026-03-24** | **workflow/certprep_workflow.py** | `CertPrepWorkflow` — `WorkflowBuilder` pipeline: 7 agents, 3 executors, fan-out edge (StudyPlan → PathCurator), FileCheckpointStorage, max_iterations=8. |
| **2026-03-24** | **workflow/executors.py** | `ProgressGateway` (HITL Gate 1), `QuizGateway` (HITL Gate 2), `ReadinessRouter` (GO/CONDITIONAL/NOT_READY). All with checkpoint save/restore. |
| **2026-03-24** | **7 MAF Agent classes** | OrchestratorAgent, ProfilerAgent, StudyPlanAgent (+ `get_exam_domains`), PathCuratorAgent (+ MCPStreamableHTTPTool), ProgressAgent (+ `compute_readiness_score`), AssessmentAgent (+ `score_quiz_responses`), CertRecommendationAgent (+ `get_next_cert_suggestions`). |
| **2026-03-24** | **7 versioned prompt files** | orchestrator.md, profiler.md, study_plan.md, path_curator.md, progress.md, assessment.md, cert_recommendation.md — all under `src/maf/prompts/`. |
| **2026-03-24** | **guardrails_middleware.py** | `InputGuardrailsMiddleware`, `ToolCallLimiterMiddleware` (MAX_MCP_CALLS=12), `OutputPIIMiddleware`. Wraps foundry-sdk 17-rule `GuardrailsPipeline`. |
| **2026-03-24** | **learner_profile_provider.py** | `LearnerProfileProvider(BaseContextProvider)` — injects 8 learner context fields into every agent via `before_run()`. |
| **2026-03-24** | **handoff_tools.py** | 7 `@tool` handoff functions for all agent-to-agent transitions. |
| **2026-03-24** | **src/maf/__init__.py** | Package init + sys.path bootstrap to `agentsleague-foundry-sdk/src` for model reuse. |
| **2026-03-24** | **requirements.txt** | MAF packages pinned at `1.0.0b260212`. azure-ai-projects, azure-identity, azure-monitor-opentelemetry, opentelemetry-semantic-conventions-ai, streamlit, python-dotenv. |
| **2026-03-24** | **.env.sample** | Template with AZURE_AI_PROJECT_CONNECTION_STRING, AZURE_AI_MODEL_DEPLOYMENT, APPLICATIONINSIGHTS_CONNECTION_STRING, MCP_MSLEARN_URL. |
| **2026-03-24** | **Project initialised** | `agentsleague-maf/` folder created. MAF upgrade of `agentsleague-foundry-sdk` begins. |
