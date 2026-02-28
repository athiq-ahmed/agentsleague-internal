"""
models.py — Shared data models for the CertPrep Multi-Agent System
===================================================================
Single authoritative definition of every data class, Pydantic model,
and enumeration that crosses an agent boundary.  Nothing in the
pipeline passes raw dicts between agents — every handoff uses one of
the types defined here.

---------------------------------------------------------------------------
Enumerations
---------------------------------------------------------------------------
  DomainKnowledge      UNKNOWN | WEAK | MODERATE | STRONG
  LearningStyle        LINEAR | LAB_FIRST | REFERENCE | ADAPTIVE
  ExperienceLevel      BEGINNER | INTERMEDIATE | ADVANCED_AZURE | EXPERT_ML

---------------------------------------------------------------------------
Exam Domain Registry (the "blueprint" for each certification)
---------------------------------------------------------------------------
  EXAM_DOMAINS         AI-102 domain list (also used as the system default)
  AI900_DOMAINS        AI-900 blueprint
  AZ204_DOMAINS        AZ-204 blueprint
  DP100_DOMAINS        DP-100 blueprint
  AZ305_DOMAINS        AZ-305 blueprint
  EXAM_DOMAIN_REGISTRY dict[exam_code → list[domain_dict]]  — central lookup
                       used by every agent and the guardrails pipeline
  get_exam_domains(code) → helper; falls back to EXAM_DOMAINS if code unknown
  DOMAIN_IDS           flat list of AI-102 domain ID strings (legacy compat.)

---------------------------------------------------------------------------
Pipeline data models (dataclasses + Pydantic)
---------------------------------------------------------------------------
  RawStudentInput      Entry point — intake form data captured by the UI.
                       Validated by GuardrailsPipeline [G-01..G-05] before
                       any agent sees it.

  DomainProfile        Per-domain profiling row inside LearnerProfile.
                       Pydantic model; `confidence_score` is range-validated
                       by Field(ge=0.0, le=1.0).

  LearnerProfile       Output of B0 (LearnerProfilingAgent).
                       Consumed by B1.1a (StudyPlanAgent),
                                    B1.1b (LearningPathCuratorAgent),
                                    B1.2  (ProgressAgent),
                                    B2    (AssessmentAgent),
                                    B3    (CertRecommendationAgent).
                       Provides helper methods: weak_domains(),
                       domains_to_skip(), domain_by_id().

---------------------------------------------------------------------------
Consumers (who imports this module)
---------------------------------------------------------------------------
  b0_intake_agent.py            builds RawStudentInput + LearnerProfile
  b1_1_study_plan_agent.py      reads LearnerProfile → builds StudyPlan
  b1_1_learning_path_curator.py reads LearnerProfile → builds LearningPath
  b1_2_progress_agent.py        reads LearnerProfile + ProgressSnapshot
  b2_assessment_agent.py        reads LearnerProfile → generates quiz
  b3_cert_recommendation_agent  reads LearnerProfile + AssessmentResult
  guardrails.py                 validates RawStudentInput + LearnerProfile
  database.py                   serialises / deserialises all models to SQLite
  streamlit_app.py              orchestrates the whole pipeline
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ─── Enumerations ────────────────────────────────────────────────────────────

class DomainKnowledge(str, Enum):
    """How well the student already knows a domain."""
    UNKNOWN  = "unknown"   # never studied
    WEAK     = "weak"      # aware but not confident
    MODERATE = "moderate"  # working knowledge
    STRONG   = "strong"    # confident – candidate for skip


class LearningStyle(str, Enum):
    """Preferred learning modality inferred from student description."""
    LINEAR    = "linear"     # structured, step-by-step
    LAB_FIRST = "lab_first"  # hands-on before reading theory
    REFERENCE = "reference"  # quick-scan cards, API docs
    ADAPTIVE  = "adaptive"   # let the system decide per domain


class ExperienceLevel(str, Enum):
    """Overall AI/Azure background of the student."""
    BEGINNER       = "beginner"       # no prior Azure or AI services exposure
    INTERMEDIATE   = "intermediate"   # some Azure; limited AI services hands-on
    ADVANCED_AZURE = "advanced_azure" # strong Azure IaC/admin; new to AI services
    EXPERT_ML      = "expert_ml"      # data science / ML engineering background


# ─── Microsoft Exam Domain Registry ─────────────────────────────────────────

# Default / sample domain blueprint (AI-102).  The system is exam-agnostic;
# swap or extend via EXAM_DOMAIN_REGISTRY for any Microsoft certification.

EXAM_DOMAINS: list[dict] = [
    {
        "id":     "plan_manage",
        "name":   "Plan & Manage Azure AI Solutions",
        "weight": 0.175,   # midpoint of 15–20 %
        "description": (
            "Security, monitoring, responsible AI, cost management, "
            "resource provisioning and deployment of Azure AI services."
        ),
    },
    {
        "id":     "computer_vision",
        "name":   "Implement Computer Vision Solutions",
        "weight": 0.225,
        "description": (
            "Azure AI Vision, Custom Vision, Face API, Video Indexer, "
            "image classification, object detection, OCR."
        ),
    },
    {
        "id":     "nlp",
        "name":   "Implement NLP Solutions",
        "weight": 0.225,
        "description": (
            "Azure AI Language, CLU, sentiment analysis, NER, "
            "text summarisation, question answering, translator."
        ),
    },
    {
        "id":     "document_intelligence",
        "name":   "Implement Document Intelligence & Knowledge Mining",
        "weight": 0.175,
        "description": (
            "Azure AI Document Intelligence, Cognitive Search, "
            "custom skills, indexers, knowledge stores."
        ),
    },
    {
        "id":     "conversational_ai",
        "name":   "Implement Conversational AI Solutions",
        "weight": 0.10,
        "description": (
            "Azure Bot Service, Bot Framework Composer, Adaptive Dialogs, "
            "CLU channel integration, Power Virtual Agents."
        ),
    },
    {
        "id":     "generative_ai",
        "name":   "Implement Generative AI Solutions",
        "weight": 0.10,
        "description": (
            "Azure OpenAI Service, prompt engineering, RAG patterns, "
            "content filters, DALL-E, responsible generative AI."
        ),
    },
]

DOMAIN_IDS = [d["id"] for d in EXAM_DOMAINS]


# ─── Additional exam domain blueprints ───────────────────────────────────────

# AI-900 – Azure AI Fundamentals (official exam objectives, 5 skill areas)
AI900_DOMAINS: list[dict] = [
    {
        "id":     "ai_workloads",
        "name":   "AI Workloads & Considerations",
        "weight": 0.175,
        "description": (
            "Common AI workload types, responsible AI principles, "
            "fairness, reliability, privacy, transparency and accountability."
        ),
    },
    {
        "id":     "ml_fundamentals",
        "name":   "Machine Learning Fundamentals on Azure",
        "weight": 0.225,
        "description": (
            "Core ML concepts, supervised/unsupervised learning, "
            "regression, classification, clustering, Azure Machine Learning studio."
        ),
    },
    {
        "id":     "cv_fundamentals",
        "name":   "Computer Vision Workloads",
        "weight": 0.175,
        "description": (
            "Image classification, object detection, OCR, facial analysis, "
            "Azure AI Vision service, Custom Vision."
        ),
    },
    {
        "id":     "nlp_fundamentals",
        "name":   "Natural Language Processing Workloads",
        "weight": 0.175,
        "description": (
            "Text analysis, key phrase extraction, sentiment, named entity recognition, "
            "question answering, Azure AI Language service."
        ),
    },
    {
        "id":     "genai_fundamentals",
        "name":   "Generative AI Workloads",
        "weight": 0.25,
        "description": (
            "Large language models, Azure OpenAI, prompt engineering basics, "
            "Copilot experiences, responsible generative AI."
        ),
    },
]

# AZ-204 – Azure Developer Associate (5 skill areas)
AZ204_DOMAINS: list[dict] = [
    {
        "id":     "compute_solutions",
        "name":   "Develop Azure Compute Solutions",
        "weight": 0.275,
        "description": (
            "Azure App Service, Azure Functions, containers, "
            "Docker, Azure Kubernetes Service, deployment strategies."
        ),
    },
    {
        "id":     "azure_storage",
        "name":   "Develop for Azure Storage",
        "weight": 0.175,
        "description": (
            "Blob storage, Cosmos DB, Azure Table storage, "
            "Azure Queue storage, caching strategies."
        ),
    },
    {
        "id":     "azure_security",
        "name":   "Implement Azure Security",
        "weight": 0.225,
        "description": (
            "Azure Key Vault, Managed Identity, Microsoft Entra ID, "
            "OAuth2, MSAL, RBAC, SAS tokens."
        ),
    },
    {
        "id":     "monitoring_optimize",
        "name":   "Monitor, Troubleshoot & Optimize",
        "weight": 0.175,
        "description": (
            "Application Insights, Azure Monitor, logging, distributed tracing, "
            "caching with Redis, CDN, performance optimisation."
        ),
    },
    {
        "id":     "azure_services_integration",
        "name":   "Connect & Consume Azure Services",
        "weight": 0.175,
        "description": (
            "API Management, Event Grid, Event Hubs, Service Bus, "
            "Azure Logic Apps, Azure Relay, webhooks."
        ),
    },
]

# DP-100 – Azure Data Scientist Associate (4 skill areas)
DP100_DOMAINS: list[dict] = [
    {
        "id":     "ml_solution_design",
        "name":   "Design & Prepare an ML Solution",
        "weight": 0.225,
        "description": (
            "Azure Machine Learning workspace, compute resources, "
            "datastores, data assets, environments, MLOps fundamentals."
        ),
    },
    {
        "id":     "explore_train_models",
        "name":   "Explore Data & Train Models",
        "weight": 0.375,
        "description": (
            "Data exploration with pandas/Spark, feature engineering, "
            "AutoML, training scripts, hyperparameter tuning, responsible AI dashboards."
        ),
    },
    {
        "id":     "prepare_deployment",
        "name":   "Prepare a Model for Deployment",
        "weight": 0.225,
        "description": (
            "MLflow tracking, model registration, batch/real-time inference, "
            "scoring scripts, deployment packages."
        ),
    },
    {
        "id":     "deploy_retrain",
        "name":   "Deploy & Retrain a Model",
        "weight": 0.175,
        "description": (
            "Managed online endpoints, batch endpoints, model monitoring, "
            "data drift detection, retraining pipelines."
        ),
    },
]

# AZ-305 – Azure Solutions Architect Expert (4 skill areas)
AZ305_DOMAINS: list[dict] = [
    {
        "id":     "identity_governance",
        "name":   "Design Identity, Governance & Monitoring",
        "weight": 0.275,
        "description": (
            "Microsoft Entra ID, RBAC, Azure Policy, Management Groups, "
            "Azure Monitor, Log Analytics, cost optimisation strategies."
        ),
    },
    {
        "id":     "data_storage_solutions",
        "name":   "Design Data Storage Solutions",
        "weight": 0.275,
        "description": (
            "Relational and non-relational databases, Azure SQL, Cosmos DB, "
            "Blob storage, Azure Files, data integration and migration patterns."
        ),
    },
    {
        "id":     "business_continuity",
        "name":   "Design Business Continuity Solutions",
        "weight": 0.125,
        "description": (
            "High availability, disaster recovery, Azure Site Recovery, "
            "backup strategies, SLA planning."
        ),
    },
    {
        "id":     "infrastructure_solutions",
        "name":   "Design Infrastructure Solutions",
        "weight": 0.325,
        "description": (
            "Compute, networking, application architecture, microservices, "
            "API Management, containerised workloads, migration strategies."
        ),
    },
]


# ─── Multi-exam registry ──────────────────────────────────────────────────────

EXAM_DOMAIN_REGISTRY: dict[str, list[dict]] = {
    "AI-102": EXAM_DOMAINS,
    "AI-900": AI900_DOMAINS,
    "AZ-204": AZ204_DOMAINS,
    "DP-100": DP100_DOMAINS,
    "AZ-305": AZ305_DOMAINS,
}


def get_exam_domains(exam_code: str) -> list[dict]:
    """Return domain list for *exam_code*, falling back to the AI-102 blueprint."""
    return EXAM_DOMAIN_REGISTRY.get(exam_code.upper(), EXAM_DOMAINS)


# ─── Block 1 Input Model ─────────────────────────────────────────────────────

@dataclass
class RawStudentInput:
    """
    Raw, unprocessed input collected by LearnerIntakeAgent.
    This is the exact information the student provides – no inference yet.
    """
    student_name:      str
    exam_target:       str                    # e.g. "AI-102"
    background_text:   str                    # free-text background description
    existing_certs:    list[str]              # e.g. ["AZ-104", "AZ-305"]
    hours_per_week:    float                  # e.g. 10.0
    weeks_available:   int                    # e.g. 8
    concern_topics:    list[str]              # e.g. ["Azure OpenAI", "Bot Service"]
    preferred_style:   str                    # free-text learning preference
    goal_text:         str                    # why they want to pass
    email:             str = ""              # optional contact email (used for weekly digest)


# ─── Block 1 Output Models ───────────────────────────────────────────────────

class DomainProfile(BaseModel):
    """Per-domain profiling result produced by LearnerProfilingAgent."""
    domain_id:          str
    domain_name:        str
    knowledge_level:    DomainKnowledge
    confidence_score:   float = Field(ge=0.0, le=1.0,
                                      description="0=no knowledge, 1=expert")
    skip_recommended:   bool  = Field(
        description="True if student's background makes this domain coverable quickly"
    )
    notes:              str   = Field(description="1–2 sentence rationale")


class LearnerProfile(BaseModel):
    """
    Structured learner profile output of Block 1 (Intake + Profiling).
    This is passed downstream to Block 1.1 (Learning Path Planner).
    """
    student_name:        str
    exam_target:         str
    experience_level:    ExperienceLevel
    learning_style:      LearningStyle
    hours_per_week:      float
    weeks_available:     int
    total_budget_hours:  float

    domain_profiles:     list[DomainProfile] = Field(
        description="One entry per exam domain, in blueprint order"
    )
    modules_to_skip:     list[str] = Field(
        description="Human-readable module names that can be safely skipped"
    )
    risk_domains:        list[str] = Field(
        description="Domain IDs most likely to need remediation"
    )
    analogy_map:         dict[str, str] = Field(
        description="Existing skill → Azure AI equivalent (empty if not applicable)"
    )
    recommended_approach: str = Field(
        description="2–3 sentence personalisation summary for downstream agents"
    )
    engagement_notes:    str = Field(
        description="Motivational tone and reminder cadence recommendation"
    )

    # ── Derived helpers ──────────────────────────────────────────────────────

    def domains_to_skip(self) -> list[str]:
        return [dp.domain_id for dp in self.domain_profiles if dp.skip_recommended]

    def weak_domains(self) -> list[str]:
        return [
            dp.domain_id for dp in self.domain_profiles
            if dp.knowledge_level in (DomainKnowledge.UNKNOWN, DomainKnowledge.WEAK)
        ]

    def domain_by_id(self, domain_id: str) -> Optional[DomainProfile]:
        return next((d for d in self.domain_profiles if d.domain_id == domain_id), None)
