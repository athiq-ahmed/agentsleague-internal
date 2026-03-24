"""
b1_1_learning_path_curator.py — Learning Path Curator Agent (Block 1.1b)
=========================================================================
Maps exam domains in a LearnerProfile to curated Microsoft Learn modules,
producing a personalised reading list ordered by study priority.
Runs in parallel with StudyPlanAgent (via ThreadPoolExecutor) so neither
agent waits on the other.

---------------------------------------------------------------------------
Agent: LearningPathCuratorAgent
---------------------------------------------------------------------------
  Input:   LearnerProfile
  Output:  LearningPath (list of LearningModule; one bucket per domain)
  Pattern: Sequential with Critic (G-17 URL trust validation)

Key behaviours
--------------
  1. Style-aware module ordering
     Learners with learning_style=LAB_FIRST see labs before videos.
     REFERENCE learners see documentation modules first.
     LINEAR learners receive modules in progressive difficulty order.

  2. Priority-based selection
     Each domain in _MODULE_CATALOGUE has 3–5 candidate modules.
     The agent selects the top 2–3 based on (style_match, priority).

  3. G-17 URL trust guard (Critic step)
     Every module URL is validated against TRUSTED_URL_PREFIXES.
     Non-approved URLs are silently removed and reported via a WARN
     guardrail violation.  Only learn.microsoft.com, docs.microsoft.com,
     aka.ms, and pearsonvue.com URLs pass the filter.

  4. Total hours estimate
     Sums all module duration_min fields and exposes total_hours_est on
     LearningPath so the UI can show "Estimated X hours of reading".

---------------------------------------------------------------------------
Data models defined in this file
---------------------------------------------------------------------------
  LearningModule    One MS Learn module: url, domain, duration, priority
  LearningPath      Curated list + per-domain buckets + total hours

---------------------------------------------------------------------------
Live vs mock
---------------------------------------------------------------------------
The mock implementation returns hard-coded MS Learn module metadata that
mirrors the real catalogue.  A live implementation could call:
  GET https://learn.microsoft.com/api/catalog/?locale=en-us&type=modules
and filter results by module tags matching each exam domain.

---------------------------------------------------------------------------
Consumers
---------------------------------------------------------------------------
  streamlit_app.py   — runs LearningPathCuratorAgent().run() in parallel
  database.py        — save_learning_path() persists learning_path_json
  b1_2_progress_agent.py — generate_profile_pdf() embeds module list in PDF
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


# ─── Data models ─────────────────────────────────────────────────────────────

@dataclass
class LearningModule:
    """A single Microsoft Learn module or learning path entry."""
    title:        str
    url:          str
    domain_id:    str
    duration_min: int    = 30       # estimated completion in minutes
    difficulty:   str   = "intermediate"   # beginner | intermediate | advanced
    module_type:  str   = "module"  # module | learning-path | collection
    priority:     str   = "core"    # core | supplemental | optional
    ms_learn_uid: str   = ""        # unique ID for deep-linking


@dataclass
class LearningPath:
    """Curated learning path output from LearningPathCuratorAgent."""
    student_name:     str
    exam_target:      str
    curated_paths:    dict = field(default_factory=dict)   # domain_id → list[LearningModule]
    all_modules:      list = field(default_factory=list)   # flat list, priority-sorted
    total_hours_est:  float = 0.0
    skipped_domains:  list = field(default_factory=list)   # domain IDs that were skipped
    summary:          str  = ""


# ─── MS Learn module catalogue (mock / offline) ───────────────────────────────
# Each tuple: (title, relative_url, duration_min, difficulty, type, priority)

_LEARN_CATALOGUE: dict[str, list[tuple]] = {
    "plan_manage": [
        (
            "Plan and manage an Azure AI solution",
            "https://learn.microsoft.com/en-us/training/paths/prepare-for-ai-engineering/",
            120, "intermediate", "learning-path", "core",
            "ai-102-plan-manage",
        ),
        (
            "Secure Azure AI services",
            "https://learn.microsoft.com/en-us/training/modules/secure-ai-services/",
            45, "intermediate", "module", "core",
            "secure-ai-services",
        ),
        (
            "Monitor Azure AI services",
            "https://learn.microsoft.com/en-us/training/modules/monitor-ai-services/",
            30, "intermediate", "module", "core",
            "monitor-ai-services",
        ),
        (
            "Implement responsible AI with Azure AI Content Safety",
            "https://learn.microsoft.com/en-us/training/modules/intro-to-azure-content-safety/",
            40, "intermediate", "module", "supplemental",
            "azure-content-safety",
        ),
    ],
    "computer_vision": [
        (
            "Create computer vision solutions with Azure AI Vision",
            "https://learn.microsoft.com/en-us/training/paths/create-computer-vision-solutions-azure-ai/",
            180, "intermediate", "learning-path", "core",
            "create-computer-vision",
        ),
        (
            "Analyze images with the Azure AI Vision service",
            "https://learn.microsoft.com/en-us/training/modules/analyze-images/",
            60, "beginner", "module", "core",
            "analyze-images",
        ),
        (
            "Classify images with a custom Azure AI Vision model",
            "https://learn.microsoft.com/en-us/training/modules/custom-model-ai-vision-image-classification/",
            45, "intermediate", "module", "core",
            "custom-vision-classification",
        ),
        (
            "Detect, analyze, and recognize faces",
            "https://learn.microsoft.com/en-us/training/modules/detect-analyze-recognize-faces/",
            50, "intermediate", "module", "core",
            "detect-faces",
        ),
        (
            "Read text with Azure AI Vision",
            "https://learn.microsoft.com/en-us/training/modules/read-text-images-documents-with-computer-vision-service/",
            40, "beginner", "module", "core",
            "read-text-vision",
        ),
        (
            "Analyze video with Azure AI Video Indexer",
            "https://learn.microsoft.com/en-us/training/modules/analyze-video/",
            35, "intermediate", "module", "supplemental",
            "analyze-video",
        ),
    ],
    "nlp": [
        (
            "Develop natural language processing solutions with Azure AI Language",
            "https://learn.microsoft.com/en-us/training/paths/develop-language-solutions-azure-ai/",
            200, "intermediate", "learning-path", "core",
            "nlp-learning-path",
        ),
        (
            "Analyze text with Azure AI Language",
            "https://learn.microsoft.com/en-us/training/modules/analyze-text-with-text-analytics-service/",
            60, "beginner", "module", "core",
            "analyze-text",
        ),
        (
            "Build a conversational language understanding model",
            "https://learn.microsoft.com/en-us/training/modules/build-language-understanding-model/",
            55, "intermediate", "module", "core",
            "clu-model",
        ),
        (
            "Create a question answering solution",
            "https://learn.microsoft.com/en-us/training/modules/create-question-answer-solution-ai-language/",
            50, "intermediate", "module", "core",
            "question-answering",
        ),
        (
            "Translate text and speech with Azure AI",
            "https://learn.microsoft.com/en-us/training/modules/translate-text-with-translation-service/",
            40, "beginner", "module", "supplemental",
            "translate-text",
        ),
    ],
    "document_intelligence": [
        (
            "Extract data from forms with Azure Document Intelligence",
            "https://learn.microsoft.com/en-us/training/paths/extract-data-from-forms-document-intelligence/",
            150, "intermediate", "learning-path", "core",
            "document-intelligence-path",
        ),
        (
            "Get started with Azure AI Document Intelligence",
            "https://learn.microsoft.com/en-us/training/modules/intro-to-form-recognizer/",
            45, "beginner", "module", "core",
            "intro-document-intelligence",
        ),
        (
            "Implement an Azure AI Search solution",
            "https://learn.microsoft.com/en-us/training/paths/implement-knowledge-mining-azure-cognitive-search/",
            180, "intermediate", "learning-path", "core",
            "azure-search-path",
        ),
        (
            "Enrich your search index using language understanding models",
            "https://learn.microsoft.com/en-us/training/modules/enrich-search-index-using-language-models/",
            40, "advanced", "module", "supplemental",
            "enrich-search-index",
        ),
    ],
    "conversational_ai": [
        (
            "Create conversational AI solutions",
            "https://learn.microsoft.com/en-us/training/paths/create-conversational-ai-solutions/",
            160, "intermediate", "learning-path", "core",
            "conversational-ai-path",
        ),
        (
            "Build a bot with the Azure Bot Service",
            "https://learn.microsoft.com/en-us/training/modules/design-bot-conversation-flow/",
            55, "intermediate", "module", "core",
            "bot-service",
        ),
        (
            "Create a bot with Bot Framework Composer",
            "https://learn.microsoft.com/en-us/training/modules/create-bot-with-bot-framework-composer/",
            60, "intermediate", "module", "supplemental",
            "bot-framework-composer",
        ),
    ],
    "generative_ai": [
        (
            "Develop generative AI solutions with Azure OpenAI Service",
            "https://learn.microsoft.com/en-us/training/paths/develop-ai-solutions-azure-openai/",
            200, "intermediate", "learning-path", "core",
            "generative-ai-path",
        ),
        (
            "Get started with Azure OpenAI Service",
            "https://learn.microsoft.com/en-us/training/modules/get-started-openai/",
            50, "beginner", "module", "core",
            "get-started-openai",
        ),
        (
            "Apply prompt engineering with Azure OpenAI Service",
            "https://learn.microsoft.com/en-us/training/modules/apply-prompt-engineering-azure-openai/",
            45, "intermediate", "module", "core",
            "prompt-engineering",
        ),
        (
            "Build natural language solutions with Azure OpenAI Service",
            "https://learn.microsoft.com/en-us/training/modules/build-language-solution-azure-openai/",
            50, "intermediate", "module", "core",
            "openai-nlp",
        ),
        (
            "Implement Retrieval Augmented Generation (RAG) with Azure OpenAI",
            "https://learn.microsoft.com/en-us/training/modules/use-own-data-azure-openai/",
            55, "advanced", "module", "core",
            "openai-rag",
        ),
        (
            "Generate images with Azure OpenAI DALL-E models",
            "https://learn.microsoft.com/en-us/training/modules/generate-images-azure-openai/",
            35, "intermediate", "module", "supplemental",
            "openai-dalle",
        ),
    ],

    # ── DP-100: Azure Data Scientist Associate ────────────────────────────────
    "ml_solution_design": [
        (
            "Introduction to Azure Machine Learning",
            "https://learn.microsoft.com/en-us/training/modules/intro-to-azure-machine-learning-service/",
            60, "beginner", "module", "core",
            "intro-aml",
        ),
        (
            "Make data available in Azure Machine Learning",
            "https://learn.microsoft.com/en-us/training/modules/make-data-available-azure-machine-learning/",
            45, "intermediate", "module", "core",
            "aml-data-assets",
        ),
        (
            "Work with compute resources in Azure Machine Learning",
            "https://learn.microsoft.com/en-us/training/modules/work-with-compute-in-aml/",
            40, "intermediate", "module", "core",
            "aml-compute",
        ),
        (
            "Design an Azure Machine Learning operations solution",
            "https://learn.microsoft.com/en-us/training/modules/design-machine-learning-operations-solution/",
            50, "advanced", "module", "supplemental",
            "aml-mlops-design",
        ),
    ],
    "explore_train_models": [
        (
            "Train models with scripts in Azure Machine Learning",
            "https://learn.microsoft.com/en-us/training/modules/train-model-command-job-azure-machine-learning/",
            60, "intermediate", "module", "core",
            "aml-train-scripts",
        ),
        (
            "Use AutoML to train a classification or regression model",
            "https://learn.microsoft.com/en-us/training/modules/use-automated-machine-learning/",
            55, "beginner", "module", "core",
            "aml-automl",
        ),
        (
            "Tune hyperparameters with Azure Machine Learning",
            "https://learn.microsoft.com/en-us/training/modules/perform-hyperparameter-tuning-azure-machine-learning-pipelines/",
            55, "intermediate", "module", "core",
            "aml-hyperparam",
        ),
        (
            "Run pipelines in Azure Machine Learning",
            "https://learn.microsoft.com/en-us/training/modules/run-pipelines-azure-machine-learning/",
            50, "intermediate", "module", "core",
            "aml-pipelines",
        ),
        (
            "Evaluate & improve models using Responsible AI dashboard",
            "https://learn.microsoft.com/en-us/training/modules/use-responsible-ai-dashboard-azure-machine-learning/",
            40, "intermediate", "module", "supplemental",
            "aml-rai-dashboard",
        ),
    ],
    "prepare_deployment": [
        (
            "Track model training with MLflow in Azure Machine Learning",
            "https://learn.microsoft.com/en-us/training/modules/train-models-training-mlflow-jobs/",
            45, "intermediate", "module", "core",
            "aml-mlflow-tracking",
        ),
        (
            "Register an MLflow model in Azure Machine Learning",
            "https://learn.microsoft.com/en-us/training/modules/register-mlflow-model-azure-machine-learning/",
            40, "intermediate", "module", "core",
            "aml-mlflow-register",
        ),
        (
            "Deploy a model to a managed online endpoint",
            "https://learn.microsoft.com/en-us/training/modules/deploy-model-managed-online-endpoint/",
            50, "intermediate", "module", "core",
            "aml-online-endpoint",
        ),
    ],
    "deploy_retrain": [
        (
            "Deploy a model to a batch endpoint",
            "https://learn.microsoft.com/en-us/training/modules/deploy-model-batch-endpoint/",
            45, "intermediate", "module", "core",
            "aml-batch-endpoint",
        ),
        (
            "Monitor models in Azure Machine Learning",
            "https://learn.microsoft.com/en-us/training/modules/monitor-models-azure-machine-learning/",
            40, "intermediate", "module", "core",
            "aml-monitor",
        ),
        (
            "Monitor data and model quality in production pipelines",
            "https://learn.microsoft.com/en-us/training/modules/monitor-data-drift-azure-machine-learning/",
            45, "advanced", "module", "supplemental",
            "aml-data-drift",
        ),
    ],

    # ── AI-900: Azure AI Fundamentals ─────────────────────────────────────────
    "ai_workloads": [
        (
            "Get started with AI on Azure",
            "https://learn.microsoft.com/en-us/training/modules/get-started-ai-fundamentals/",
            45, "beginner", "module", "core",
            "ai900-get-started",
        ),
        (
            "Responsible AI principles and practices",
            "https://learn.microsoft.com/en-us/training/modules/responsible-ai-principles/",
            30, "beginner", "module", "core",
            "ai900-responsible-ai",
        ),
    ],
    "ml_fundamentals": [
        (
            "Explore Azure Machine Learning fundamentals",
            "https://learn.microsoft.com/en-us/training/modules/use-automated-machine-learning/",
            60, "beginner", "module", "core",
            "ai900-ml-fundamentals",
        ),
        (
            "Train and evaluate regression models",
            "https://learn.microsoft.com/en-us/training/modules/train-evaluate-regression-models/",
            65, "beginner", "module", "supplemental",
            "ai900-regression",
        ),
        (
            "Train and evaluate classification models",
            "https://learn.microsoft.com/en-us/training/modules/train-evaluate-classification-models/",
            60, "beginner", "module", "supplemental",
            "ai900-classification",
        ),
    ],
    "cv_fundamentals": [
        (
            "Explore computer vision in Microsoft Azure",
            "https://learn.microsoft.com/en-us/training/modules/explore-computer-vision-microsoft-azure/",
            50, "beginner", "module", "core",
            "ai900-cv-fundamentals",
        ),
        (
            "Analyze images with Azure AI Vision",
            "https://learn.microsoft.com/en-us/training/modules/analyze-images/",
            45, "beginner", "module", "supplemental",
            "ai900-analyze-images",
        ),
    ],
    "nlp_fundamentals": [
        (
            "Explore natural language processing",
            "https://learn.microsoft.com/en-us/training/modules/explore-natural-language-processing/",
            50, "beginner", "module", "core",
            "ai900-nlp-fundamentals",
        ),
        (
            "Analyze text with Azure AI Language",
            "https://learn.microsoft.com/en-us/training/modules/analyze-text-with-text-analytics-service/",
            45, "beginner", "module", "supplemental",
            "ai900-text-analytics",
        ),
    ],
    "genai_fundamentals": [
        (
            "Fundamentals of Generative AI",
            "https://learn.microsoft.com/en-us/training/modules/fundamentals-generative-ai/",
            45, "beginner", "module", "core",
            "ai900-genai",
        ),
        (
            "Fundamentals of Azure OpenAI Service",
            "https://learn.microsoft.com/en-us/training/modules/explore-azure-openai/",
            40, "beginner", "module", "core",
            "ai900-azure-openai",
        ),
        (
            "Fundamentals of Responsible Generative AI",
            "https://learn.microsoft.com/en-us/training/modules/responsible-generative-ai/",
            35, "beginner", "module", "supplemental",
            "ai900-responsible-genai",
        ),
    ],

    # ── AZ-204: Azure Developer Associate ─────────────────────────────────────
    "compute_solutions": [
        (
            "Explore Azure App Service",
            "https://learn.microsoft.com/en-us/training/modules/explore-azure-app-service/",
            50, "intermediate", "module", "core",
            "az204-app-service",
        ),
        (
            "Implement Azure Functions",
            "https://learn.microsoft.com/en-us/training/modules/implement-azure-functions/",
            55, "intermediate", "module", "core",
            "az204-functions",
        ),
        (
            "Explore containerised solutions with Azure Container Instances",
            "https://learn.microsoft.com/en-us/training/modules/create-run-container-images-azure-container-instances/",
            45, "intermediate", "module", "core",
            "az204-containers",
        ),
        (
            "Deploy containerised workloads to Azure Kubernetes Service",
            "https://learn.microsoft.com/en-us/training/modules/aks-deploy-container-app/",
            60, "advanced", "module", "supplemental",
            "az204-aks",
        ),
    ],
    "azure_storage": [
        (
            "Develop solutions that use Azure Blob storage",
            "https://learn.microsoft.com/en-us/training/modules/work-azure-blob-storage/",
            55, "intermediate", "module", "core",
            "az204-blob",
        ),
        (
            "Develop solutions that use Azure Cosmos DB",
            "https://learn.microsoft.com/en-us/training/modules/develop-solutions-that-use-azure-cosmos-db/",
            60, "intermediate", "module", "core",
            "az204-cosmos",
        ),
        (
            "Develop for Azure Cache for Redis",
            "https://learn.microsoft.com/en-us/training/modules/develop-for-azure-cache-for-redis/",
            40, "intermediate", "module", "supplemental",
            "az204-redis",
        ),
    ],
    "azure_security": [
        (
            "Implement authentication and authorisation using Microsoft Identity",
            "https://learn.microsoft.com/en-us/training/modules/implement-authentication-by-using-microsoft-authentication-library/",
            50, "intermediate", "module", "core",
            "az204-auth-msal",
        ),
        (
            "Implement secure Azure solutions with Key Vault and Managed Identity",
            "https://learn.microsoft.com/en-us/training/modules/implement-azure-key-vault/",
            50, "intermediate", "module", "core",
            "az204-key-vault",
        ),
        (
            "Implement API Management policies",
            "https://learn.microsoft.com/en-us/training/modules/explore-api-management/",
            45, "intermediate", "module", "supplemental",
            "az204-apim",
        ),
    ],
    "monitoring_optimize": [
        (
            "Instrument solutions to support monitoring and logging",
            "https://learn.microsoft.com/en-us/training/modules/instrument-apps-with-azure-monitor/",
            45, "intermediate", "module", "core",
            "az204-monitor",
        ),
        (
            "Integrate caching and content delivery",
            "https://learn.microsoft.com/en-us/training/modules/develop-for-storage-cdns/",
            35, "intermediate", "module", "supplemental",
            "az204-cdn",
        ),
    ],
    "azure_services_integration": [
        (
            "Develop event-based solutions with Event Grid and Event Hubs",
            "https://learn.microsoft.com/en-us/training/modules/develop-event-based-solutions/",
            45, "intermediate", "module", "core",
            "az204-event-grid",
        ),
        (
            "Develop message-based solutions with Service Bus and Queue Storage",
            "https://learn.microsoft.com/en-us/training/modules/discover-azure-message-queue/",
            45, "intermediate", "module", "core",
            "az204-service-bus",
        ),
    ],

    # ── AZ-305: Azure Solutions Architect Expert ──────────────────────────────
    "identity_governance": [
        (
            "Design authentication and authorisation solutions",
            "https://learn.microsoft.com/en-us/training/modules/design-authentication-authorization-solutions/",
            65, "advanced", "module", "core",
            "az305-auth",
        ),
        (
            "Design a governance solution with Azure Policy and Management Groups",
            "https://learn.microsoft.com/en-us/training/modules/enterprise-scale-organization/",
            55, "advanced", "module", "core",
            "az305-governance",
        ),
        (
            "Design for cost optimisation and monitoring",
            "https://learn.microsoft.com/en-us/training/modules/design-monitor-solution/",
            50, "advanced", "module", "supplemental",
            "az305-monitor-cost",
        ),
    ],
    "data_storage_solutions": [
        (
            "Design a data storage solution for relational data",
            "https://learn.microsoft.com/en-us/training/modules/design-data-storage-solution-for-relational-data/",
            60, "advanced", "module", "core",
            "az305-relational-db",
        ),
        (
            "Design a data storage solution for non-relational data",
            "https://learn.microsoft.com/en-us/training/modules/design-data-storage-solution-for-non-relational-data/",
            55, "advanced", "module", "core",
            "az305-non-relational-db",
        ),
        (
            "Design data integration solutions",
            "https://learn.microsoft.com/en-us/training/modules/design-data-integration/",
            50, "advanced", "module", "supplemental",
            "az305-data-integration",
        ),
    ],
    "business_continuity": [
        (
            "Design a solution for backup and disaster recovery",
            "https://learn.microsoft.com/en-us/training/modules/design-solution-for-backup-disaster-recovery/",
            55, "advanced", "module", "core",
            "az305-bcdr",
        ),
        (
            "Design for high availability",
            "https://learn.microsoft.com/en-us/training/modules/design-for-high-availability/",
            45, "advanced", "module", "core",
            "az305-ha",
        ),
    ],
    "infrastructure_solutions": [
        (
            "Design a compute solution",
            "https://learn.microsoft.com/en-us/training/modules/design-compute-solution/",
            60, "advanced", "module", "core",
            "az305-compute",
        ),
        (
            "Design a network solution",
            "https://learn.microsoft.com/en-us/training/modules/design-network-solutions/",
            65, "advanced", "module", "core",
            "az305-network",
        ),
        (
            "Design an application architecture",
            "https://learn.microsoft.com/en-us/training/modules/design-application-architecture/",
            60, "advanced", "module", "core",
            "az305-app-arch",
        ),
        (
            "Design migrations to Azure",
            "https://learn.microsoft.com/en-us/training/modules/design-migrations/",
            55, "advanced", "module", "supplemental",
            "az305-migrations",
        ),
    ],
    # ── DP-100: Azure Data Scientist Associate ────────────────────────────────
    "ml_solution_design": [
        (
            "Create and manage an Azure Machine Learning workspace",
            "https://learn.microsoft.com/en-us/training/modules/intro-to-azure-machine-learning-service/",
            45, "beginner", "module", "core",
            "dp100-create-workspace",
        ),
        (
            "Work with data in Azure Machine Learning",
            "https://learn.microsoft.com/en-us/training/modules/work-with-data-in-aml/",
            50, "intermediate", "module", "core",
            "dp100-work-data",
        ),
        (
            "Work with compute in Azure Machine Learning",
            "https://learn.microsoft.com/en-us/training/modules/work-with-compute-in-aml/",
            50, "intermediate", "module", "core",
            "dp100-work-compute",
        ),
    ],
    "explore_train_models": [
        (
            "Make predictions with Azure Machine Learning AutoML",
            "https://learn.microsoft.com/en-us/training/modules/automate-model-selection-with-azure-automl/",
            50, "intermediate", "module", "core",
            "dp100-automl",
        ),
        (
            "Find the best classification model with Automated Machine Learning",
            "https://learn.microsoft.com/en-us/training/modules/find-best-classification-model-automated-machine-learning/",
            45, "intermediate", "module", "supplemental",
            "dp100-automl-classif",
        ),
        (
            "Use MLflow to track Jupyter Notebooks",
            "https://learn.microsoft.com/en-us/training/modules/use-mlflow-to-track-jupyter-notebooks/",
            40, "intermediate", "module", "core",
            "dp100-mlflow-track",
        ),
        (
            "Tune hyperparameters with Azure Machine Learning",
            "https://learn.microsoft.com/en-us/training/modules/perform-hyperparameter-tuning-azure-machine-learning-pipelines/",
            55, "advanced", "module", "core",
            "dp100-hparam-tune",
        ),
    ],
    "prepare_deployment": [
        (
            "Register an MLflow model in Azure Machine Learning",
            "https://learn.microsoft.com/en-us/training/modules/register-and-deploy-model-with-amls/",
            60, "intermediate", "module", "core",
            "dp100-register-model",
        ),
        (
            "Convert a model to ONNX with MLflow",
            "https://learn.microsoft.com/en-us/training/modules/convert-model-onnx/",
            40, "intermediate", "module", "supplemental",
            "dp100-onnx",
        ),
        (
            "Deploy an MLflow model to an online endpoint",
            "https://learn.microsoft.com/en-us/training/modules/deploy-mlflow-model-to-managed-online-endpoint/",
            55, "advanced", "module", "core",
            "dp100-deploy-mlflow",
        ),
    ],
    "deploy_retrain": [
        (
            "Deploy a model to a managed online endpoint in Azure ML",
            "https://learn.microsoft.com/en-us/training/modules/deploy-model-managed-online-endpoint/",
            60, "advanced", "module", "core",
            "dp100-online-endpoint",
        ),
        (
            "Run batch inference using Azure Machine Learning batch endpoints",
            "https://learn.microsoft.com/en-us/training/modules/run-batch-inference-using-azure-machine-learning-endpoints/",
            55, "advanced", "module", "core",
            "dp100-batch-endpoint",
        ),
        (
            "Monitor models with Azure Machine Learning",
            "https://learn.microsoft.com/en-us/training/modules/monitor-models-with-azure-machine-learning/",
            50, "advanced", "module", "core",
            "dp100-monitor",
        ),
        (
            "Retrain and update machine learning models with ML pipelines",
            "https://learn.microsoft.com/en-us/training/modules/retrain-update-models-with-azure-machine-learning-pipeline/",
            55, "advanced", "module", "core",
            "dp100-retrain-pipeline",
        ),
    ],
}

# Priority bump for risk domains
_RISK_PRIORITY_BOOST = {"supplemental": "core", "optional": "supplemental"}


class LearningPathCuratorAgent:
    """
    Block 1.1 — Learning Path Curator Agent.

    Selects and orders Microsoft Learn modules for a learner based on:
    - Their domain knowledge levels (skip strong domains)
    - Risk domains (promote supplemental → core)
    - Learning style preferences
    - Estimated study budget

    Usage::

        agent = LearningPathCuratorAgent()
        path  = agent.curate(profile)
    """

    # Guardrail: cap total curated hours to 2× budget so the list stays manageable
    MAX_HOURS_MULTIPLIER = 2.0

    def curate(self, profile) -> LearningPath:
        """Return a `LearningPath` personalised for the given `LearnerProfile`."""
        from cert_prep.models import DomainKnowledge

        curated: dict[str, list[LearningModule]] = {}
        all_modules: list[LearningModule] = []
        skipped: list[str] = []
        budget_minutes = profile.total_budget_hours * 60 * self.MAX_HOURS_MULTIPLIER
        spent_minutes  = 0.0

        # Process domains ordered by priority: risk first, then regular, skip last
        sorted_profiles = sorted(
            profile.domain_profiles,
            key=lambda dp: (
                0 if dp.domain_id in profile.risk_domains else
                2 if dp.skip_recommended else
                1
            ),
        )

        for dp in sorted_profiles:
            raw_modules = _LEARN_CATALOGUE.get(dp.domain_id, [])
            domain_modules: list[LearningModule] = []

            # Skip strong domains that were already flagged
            if dp.skip_recommended and dp.knowledge_level.value in ("strong",):
                skipped.append(dp.domain_id)
                curated[dp.domain_id] = []
                continue

            for item in raw_modules:
                title, url, dur, diff, mtype, pri, uid = item

                # Boost priority for risk domains
                if dp.domain_id in profile.risk_domains:
                    pri = _RISK_PRIORITY_BOOST.get(pri, pri)

                # For advanced learners, skip beginner-only modules unless risk domain
                if (
                    diff == "beginner"
                    and dp.knowledge_level.value in ("moderate", "strong")
                    and dp.domain_id not in profile.risk_domains
                ):
                    pri = "optional"

                # Respect budget cap
                if spent_minutes + dur > budget_minutes and pri == "optional":
                    continue

                mod = LearningModule(
                    title=title,
                    url=url,
                    domain_id=dp.domain_id,
                    duration_min=dur,
                    difficulty=diff,
                    module_type=mtype,
                    priority=pri,
                    ms_learn_uid=uid,
                )
                domain_modules.append(mod)
                all_modules.append(mod)
                spent_minutes += dur

            curated[dp.domain_id] = domain_modules

        # Sort flat list: core → supplemental → optional; then by domain risk
        _pri_order = {"core": 0, "supplemental": 1, "optional": 2}
        all_modules.sort(key=lambda m: (
            _pri_order.get(m.priority, 9),
            0 if m.domain_id in profile.risk_domains else 1,
        ))

        total_hours = sum(m.duration_min for m in all_modules) / 60.0

        summary = (
            f"Curated **{len(all_modules)} MS Learn modules** across "
            f"**{len(curated) - len(skipped)} active domains** "
            f"(~{total_hours:.1f}h total). "
            f"{len(skipped)} domain(s) skipped based on strong prior knowledge."
        )

        return LearningPath(
            student_name=profile.student_name,
            exam_target=profile.exam_target,
            curated_paths=curated,
            all_modules=all_modules,
            total_hours_est=total_hours,
            skipped_domains=skipped,
            summary=summary,
        )
