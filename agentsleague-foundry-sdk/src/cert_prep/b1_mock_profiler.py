"""
b1_mock_profiler.py — Rule-based LearnerProfile generator (Tier 3 fallback)
============================================================================
Produces a LearnerProfile from RawStudentInput using pure Python keyword
matching and rule tables — no Azure credentials or network calls required.

This module serves three roles:
  1. **Tier 3 fallback** — used by LearnerProfilingAgent when neither
     the Foundry SDK nor Azure OpenAI is configured.
  2. **Unit test fixture** — all 299 tests use the mock profiler so they
     run offline in under 3 seconds.
  3. **Demo / quick-start** — the app is fully functional out-of-the-box
     with no .env configuration needed.

Algorithm (three passes)
------------------------
  Pass 1 — Experience Level
    Scans `background_text` for keyword sets mapped to ExperienceLevel values.
    Highest-scoring keyword wins.  Example mappings:
      "data scientist", "machine learning" → EXPERT_ML
      "architect", "azure"                 → ADVANCED_AZURE
      "developer", "engineer"              → INTERMEDIATE
      (no strong match)                    → BEGINNER

  Pass 2 — Domain Confidence Scores
    Base scores are derived from:
      a) Existing certifications — _CERT_DOMAIN_BOOST_BY_TARGET maps each
         held cert to the domain IDs it strengthens (per target exam).
      b) Background keyword co-occurrence — domain-specific terms in
         `background_text` raise the score on a linear scale [0.10, 0.75].
      c) ExperienceLevel baseline — EXPERT_ML and ADVANCED_AZURE start
         higher than BEGINNER to reflect general platform fluency.

  Pass 3 — Concern Topics → Risk Domains + Penalty
    Each concern topic is mapped to a domain ID.  Matched domains:
      • Receive a −0.15 confidence penalty (min floor: 0.05).
      • Are added to `risk_domains` so downstream agents front-load them.

  Post-processing
    • Derives `knowledge_level` from confidence thresholds:
        < 0.30 → UNKNOWN,  0.30–0.50 → WEAK,
        0.50–0.70 → MODERATE,  ≥ 0.70 → STRONG
    • Detects `skip_recommended` when confidence ≥ 0.80 (near-expert).
    • Builds `analogy_map` for ML/data-science backgrounds.
    • Selects `learning_style` from preferred_style text keywords.

Public API
----------
  generate_mock_profile(raw: RawStudentInput) → LearnerProfile

Consumers
---------
  b0_intake_agent.py   — calls generate_mock_profile() as Tier 3 fallback
  streamlit_app.py     — calls directly when live_mode=False
  tests/*              — all tests that need a LearnerProfile use this
"""

from __future__ import annotations

import re
from cert_prep.models import (
    EXAM_DOMAINS,
    DomainKnowledge,
    ExperienceLevel,
    LearnerProfile,
    LearningStyle,
    RawStudentInput,
    get_exam_domains,
)

# ── Keyword sets ──────────────────────────────────────────────────────────────

# Maps held certification → domain IDs that get a confidence boost,
# keyed by target exam so each cert's domain IDs are respected.
_CERT_DOMAIN_BOOST_BY_TARGET: dict[str, dict[str, list[str]]] = {
    "AI-102": {
        "AZ-104": ["plan_manage"],
        "AZ-305": ["plan_manage"],
        "AZ-900": ["plan_manage"],
        "DP-100": ["generative_ai", "document_intelligence"],
        "AI-900": ["plan_manage", "computer_vision", "nlp"],
        "AZ-400": ["plan_manage"],
    },
    "AI-900": {
        "AZ-900": ["ai_workloads", "ml_fundamentals"],
        "AZ-104": ["ai_workloads"],
        "AI-102": ["cv_fundamentals", "nlp_fundamentals", "genai_fundamentals", "ai_workloads"],
        "DP-100": ["ml_fundamentals", "genai_fundamentals"],
        "AZ-204": ["ai_workloads"],
    },
    "AZ-204": {
        "AZ-104": ["azure_security", "monitoring_optimize"],
        "AZ-900": ["compute_solutions"],
        "AZ-305": ["compute_solutions", "azure_security", "monitoring_optimize"],
        "AZ-400": ["compute_solutions", "monitoring_optimize"],
        "AI-102": ["azure_services_integration"],
    },
    "DP-100": {
        "AZ-900": ["ml_solution_design"],
        "AZ-104": ["ml_solution_design"],
        "AI-900": ["explore_train_models"],
        "AI-102": ["explore_train_models", "ml_solution_design"],
        "AZ-204": ["ml_solution_design", "deploy_retrain"],
    },
    "AZ-305": {
        "AZ-104": ["identity_governance", "infrastructure_solutions"],
        "AZ-204": ["infrastructure_solutions", "data_storage_solutions"],
        "AZ-900": ["identity_governance"],
        "AZ-400": ["infrastructure_solutions", "identity_governance"],
        "AZ-500": ["identity_governance", "business_continuity"],
        "AI-102": ["data_storage_solutions", "identity_governance"],
    },
}

# Legacy flat map (fallback for unknown target exams)
_CERT_DOMAIN_BOOST: dict[str, list[str]] = {
    "AZ-104": ["plan_manage"],
    "AZ-305": ["plan_manage"],
    "AZ-900": ["plan_manage"],
    "DP-100": ["generative_ai", "document_intelligence"],
    "AI-900": ["plan_manage", "computer_vision", "nlp"],
    "AZ-400": ["plan_manage"],
}

_BG_ML_KEYWORDS       = {"scikit", "sklearn", "pytorch", "tensorflow", "keras",
                         "data scientist", "data science", "machine learning",
                         "ml engineer", "mlops", "numpy", "pandas", "jupyter",
                         "huggingface", "hugging face", "transformers", "llm"}
_BG_AZURE_INFRA       = {"az-104", "az-305", "az-204", "architect", "devops",
                         "infrastructure", "bicep", "terraform", "arm template"}
_BG_DEV_KEYWORDS      = {"developer", "software engineer", "python", "c#", ".net",
                         "java", "rest api", "api", "backend", "full stack"}

_CONCERN_DOMAIN_MAP: list[tuple[re.Pattern, str]] = [
    # AI-102 domains
    (re.compile(r"openai|generative|gen ai|dall.?e|gpt|rag",        re.I), "generative_ai"),
    (re.compile(r"bot|copilot|power virtual|conversation|dialog",   re.I), "conversational_ai"),
    (re.compile(r"vision|image|face|ocr|video|custom vision",       re.I), "computer_vision"),
    (re.compile(r"nlp|language|sentiment|ner|text|translator|clu",  re.I), "nlp"),
    (re.compile(r"document|form|invoice|cognitive search|knowledge",re.I), "document_intelligence"),
    (re.compile(r"security|monitor|responsible|compliance|governance|cost", re.I), "plan_manage"),
    # AI-900 domains
    (re.compile(r"responsible|ethics|fairness|bias|transparency",   re.I), "ai_workloads"),
    (re.compile(r"machine learning|regression|classification|cluster|automl", re.I), "ml_fundamentals"),
    (re.compile(r"image|photo|object detect|ocr|face recogn",       re.I), "cv_fundamentals"),
    (re.compile(r"language|text analys|key phrase|sentiment|qa",    re.I), "nlp_fundamentals"),
    (re.compile(r"llm|copilot|prompt|openai|generative",            re.I), "genai_fundamentals"),
    # AZ-204 domains
    (re.compile(r"app service|function|container|kubernetes|docker|aks", re.I), "compute_solutions"),
    (re.compile(r"blob|storage|cosmos|queue|table|cache",            re.I), "azure_storage"),
    (re.compile(r"key vault|identity|msal|oauth|rbac|sas token",    re.I), "azure_security"),
    (re.compile(r"monitor|app insights|logging|trace|performance",  re.I), "monitoring_optimize"),
    (re.compile(r"api management|event grid|service bus|event hub", re.I), "azure_services_integration"),
    # DP-100 domains
    (re.compile(r"workspace|compute|datastore|environment|mlops",    re.I), "ml_solution_design"),
    (re.compile(r"feature engineer|hyperparam|training|automl|pandas|spark", re.I), "explore_train_models"),
    (re.compile(r"mlflow|model register|scoring|inference package",  re.I), "prepare_deployment"),
    (re.compile(r"endpoint|batch|drift|retrain|pipeline",           re.I), "deploy_retrain"),
    # AZ-305 domains
    (re.compile(r"entra|active directory|policy|governance|rbac|cost optim", re.I), "identity_governance"),
    (re.compile(r"database|cosmos db|sql|blob|file|migration|data integration", re.I), "data_storage_solutions"),
    (re.compile(r"backup|disaster recovery|site recovery|ha|sla",   re.I), "business_continuity"),
    (re.compile(r"network|vnet|load balanc|microservice|api gateway|migration", re.I), "infrastructure_solutions"),
]

_STYLE_MAP: list[tuple[re.Pattern, LearningStyle]] = [
    (re.compile(r"lab|hands.on|practice|build|project|do", re.I),  LearningStyle.LAB_FIRST),
    (re.compile(r"reference|card|cheat|quick|api|doc",    re.I),   LearningStyle.REFERENCE),
    (re.compile(r"structured|linear|step|order|chapter|book", re.I), LearningStyle.LINEAR),
]

_ANALOGY_MAP_ML: dict[str, str] = {
    "scikit-learn pipeline":   "Azure ML Pipeline",
    "PyTorch / TensorFlow":    "Azure Machine Learning (custom model training)",
    "Jupyter notebooks":       "Azure Machine Learning Notebooks",
    "Hugging Face models":     "Azure OpenAI / Azure AI Model Catalog",
    "Custom NLP (spaCy/NLTK)": "Azure AI Language (CLU, NER, Sentiment)",
    "Vector search / FAISS":   "Azure AI Search (vector indexing)",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _text(*fields: str) -> str:
    """Combine multiple text fields into a single searchable string."""
    return " ".join(fields).lower()


def _infer_experience(raw: RawStudentInput) -> ExperienceLevel:
    combined = _text(raw.background_text, *raw.existing_certs)
    if any(k in combined for k in _BG_ML_KEYWORDS):
        return ExperienceLevel.EXPERT_ML
    certs_upper = {c.upper() for c in raw.existing_certs}
    if {"AZ-104", "AZ-305", "AZ-400"} & certs_upper:
        return ExperienceLevel.ADVANCED_AZURE
    if any(k in combined for k in _BG_AZURE_INFRA):
        return ExperienceLevel.INTERMEDIATE
    if any(k in combined for k in _BG_DEV_KEYWORDS):
        return ExperienceLevel.INTERMEDIATE
    return ExperienceLevel.BEGINNER


def _infer_style(raw: RawStudentInput) -> LearningStyle:
    text = _text(raw.preferred_style, raw.background_text)
    for pattern, style in _STYLE_MAP:
        if pattern.search(text):
            return style
    return LearningStyle.ADAPTIVE


def _boosted_domains(certs: list[str], target_exam: str = "AI-102") -> set[str]:
    """Return domain IDs that get a confidence boost based on held certs and target exam."""
    exam_boost_map = _CERT_DOMAIN_BOOST_BY_TARGET.get(
        target_exam.upper(), _CERT_DOMAIN_BOOST
    )
    boosted: set[str] = set()
    for cert in certs:
        for key, domains in exam_boost_map.items():
            if key.upper() in cert.upper():
                boosted.update(domains)
    return boosted


def _risk_domains_from_concerns(concern_topics: list[str]) -> set[str]:
    risk: set[str] = set()
    concern_text = " ".join(concern_topics)
    for pattern, domain_id in _CONCERN_DOMAIN_MAP:
        if pattern.search(concern_text):
            risk.add(domain_id)
    return risk


def _domain_profile(
    domain: dict,
    boosted:    set[str],
    risk:       set[str],
    experience: ExperienceLevel,
    is_ml_bg:   bool,
) -> dict:
    did = domain["id"]

    # Base score by experience
    base = {
        ExperienceLevel.BEGINNER:       0.15,
        ExperienceLevel.INTERMEDIATE:   0.35,
        ExperienceLevel.ADVANCED_AZURE: 0.45,
        ExperienceLevel.EXPERT_ML:      0.40,
    }[experience]

    # Apply cert boost
    if did in boosted:
        base = min(base + 0.45, 0.92)

    # ML-background bump for generative_ai and document_intelligence
    if is_ml_bg:
        if did == "generative_ai":
            base = min(base + 0.20, 0.75)
        if did == "document_intelligence":
            base = min(base + 0.10, 0.60)

    # Concern penalises confidence unless already boosted
    if did in risk and did not in boosted:
        base = max(base - 0.15, 0.10)

    # Assign knowledge level
    if base >= 0.80:
        level = DomainKnowledge.STRONG
    elif base >= 0.55:
        level = DomainKnowledge.MODERATE
    elif base >= 0.30:
        level = DomainKnowledge.WEAK
    else:
        level = DomainKnowledge.UNKNOWN

    skip = level == DomainKnowledge.STRONG

    # Notes
    if did in boosted:
        notes = f"Prior certification maps to this domain. Confidence elevated; likely skippable with a quick self-test."
    elif did in risk:
        notes = f"Flagged as a concern topic. Recommend dedicated lab time and extra practice questions."
    elif level == DomainKnowledge.UNKNOWN:
        notes = "No prior exposure detected. Full study path required from fundamentals."
    elif level == DomainKnowledge.MODERATE:
        notes = "Some transferable knowledge detected. Focus on Azure-specific APIs and configuration patterns."
    else:
        notes = "Foundational knowledge inferred from background. Targeted review recommended."

    return {
        "domain_id":        did,
        "domain_name":      domain["name"],
        "knowledge_level":  level.value,
        "confidence_score": round(base, 2),
        "skip_recommended": skip,
        "notes":            notes,
    }


# ── Public API ────────────────────────────────────────────────────────────────

def run_mock_profiling_with_trace(raw: RawStudentInput):   # -> tuple[LearnerProfile, RunTrace]
    """
    Same as run_mock_profiling but also returns a full RunTrace
    for admin dashboard inspection.
    """
    from cert_prep.agent_trace import build_mock_trace, RunTrace
    profile = run_mock_profiling(raw)
    trace: RunTrace = build_mock_trace(raw, profile)
    return profile, trace


def run_mock_profiling(raw: RawStudentInput) -> LearnerProfile:
    """
    Generate a realistic LearnerProfile using rule-based inference.
    Domains are derived from the target exam (raw.exam_target) so the
    Knowledge Coverage radar reflects the correct certification.
    No LLM call required — safe to use before Azure credentials are configured.
    """
    experience = _infer_experience(raw)
    style      = _infer_style(raw)
    exam_domains = get_exam_domains(raw.exam_target)
    boosted    = _boosted_domains(raw.existing_certs, raw.exam_target)
    risk       = _risk_domains_from_concerns(raw.concern_topics)
    is_ml      = experience == ExperienceLevel.EXPERT_ML

    domain_profiles = [
        _domain_profile(d, boosted, risk, experience, is_ml)
        for d in exam_domains
    ]

    modules_to_skip = [
        dp["domain_name"]
        for dp in domain_profiles
        if dp["skip_recommended"]
    ]

    risk_domain_ids = [
        dp["domain_id"]
        for dp in domain_profiles
        if dp["confidence_score"] < 0.50
    ]

    analogy_map = _ANALOGY_MAP_ML if is_ml else {}

    # Build recommended approach
    skip_count = len(modules_to_skip)
    risk_count = len(risk_domain_ids)
    total_hours = raw.hours_per_week * raw.weeks_available

    approach_parts = [
        f"Based on your background as {raw.background_text[:80].strip()}, "
        f"the system has classified you as {experience.value.replace('_', ' ')}. "
    ]
    if skip_count:
        approach_parts.append(
            f"{skip_count} domain(s) can be covered quickly with a self-test "
            f"({', '.join(modules_to_skip[:2])}) freeing up time for weaker areas. "
        )
    if risk_count:
        approach_parts.append(
            f"Priority focus recommended on {risk_count} risk domain(s). "
        )
    approach_parts.append(
        f"With {total_hours:.0f} total study hours across "
        f"{raw.weeks_available} weeks, a structured plan is achievable."
    )

    engagement_notes = (
        "Recommended reminder cadence: Monday recap, Wednesday lab nudge, Friday milestone check. "
        "Tone: encouraging and goal-oriented. Highlight exam-day countdown in weekly summaries."
    )

    return LearnerProfile.model_validate(
        {
            "student_name":        raw.student_name,
            "exam_target":         raw.exam_target,
            "experience_level":    experience.value,
            "learning_style":      style.value,
            "hours_per_week":      raw.hours_per_week,
            "weeks_available":     raw.weeks_available,
            "total_budget_hours":  total_hours,
            "domain_profiles":     domain_profiles,
            "modules_to_skip":     modules_to_skip,
            "risk_domains":        risk_domain_ids,
            "analogy_map":         analogy_map,
            "recommended_approach": " ".join(approach_parts),
            "engagement_notes":    engagement_notes,
        }
    )
