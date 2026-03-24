# Domain badge color mapping
LEVEL_COLOUR = {
  "unknown": "#BDBDBD",
  "weak": "#FF6F00",
  "moderate": "#0078D4",
  "strong": "#107C41"
}
# Color constants
BG_DARK = "#F5F5F5"
BG_CARD = "#FFFFFF"
BLUE = "#0078D4"
PURPLE = "#7B2FF2"
GOLD = "#FFB900"
ORANGE = "#FF6F00"
TEXT_PRIMARY = "#1B1B1B"
TEXT_MUTED = "#616161"
BLUE_LITE = "#EFF6FF"
BORDER = "#E1DFDD"
GREEN = "#107C41"
GREEN_LITE = "#F0FFF4"
RED_LITE = "#FFF8F0"
RED = "#CA5010"
# Color constants
BG_DARK = "#F5F5F5"
BG_CARD = "#FFFFFF"
BLUE = "#0078D4"
PURPLE = "#7B2FF2"
GOLD = "#FFB900"
TEXT_PRIMARY = "#1B1B1B"
TEXT_MUTED = "#616161"
BLUE_LITE = "#EFF6FF"
BORDER = "#E1DFDD"
GREEN = "#107C41"
# Color constants
BG_DARK = "#F5F5F5"
BG_CARD = "#FFFFFF"
BLUE = "#0078D4"
PURPLE = "#7B2FF2"
TEXT_PRIMARY = "#1B1B1B"
TEXT_MUTED = "#616161"
BLUE_LITE = "#EFF6FF"
BORDER = "#E1DFDD"
GREEN = "#107C41"
BORDER = "#E1DFDD"
GREEN = "#107C41"
# streamlit_app.py – Microsoft Certification Prep
# Multi-agent certification prep powered by Azure OpenAI & Microsoft Foundry
PINK = "#D63384"
PURPLE_LITE = "#F3E8FF"

import json
import sys
from pathlib import Path
import os
import concurrent.futures
import time

# Load .env into os.environ before any Azure SDK or config imports
try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv(override=True)   # always pick up latest .env values; Streamlit Cloud secrets override via platform
except ImportError:
    pass  # python-dotenv is optional; env vars may already be set

# Color constants
BG_DARK = "#F5F5F5"
BG_CARD = "#FFFFFF"
BLUE = "#0078D4"
TEXT_PRIMARY = "#1B1B1B"
TEXT_MUTED = "#616161"
BLUE_LITE = "#EFF6FF"
BORDER = "#E1DFDD"

# make src/ importable without installing the package
sys.path.insert(0, str(Path(__file__).parent / "src"))

import streamlit as st
import plotly.graph_objects as go

from cert_prep.models import (
    EXAM_DOMAINS,
    EXAM_DOMAIN_REGISTRY,
    DomainKnowledge,
    RawStudentInput,
    LearnerProfile,
    get_exam_domains,
)
from cert_prep.b1_mock_profiler import run_mock_profiling, run_mock_profiling_with_trace
from cert_prep.b1_1_study_plan_agent import StudyPlanAgent, StudyPlan, PRIORITY_COLOUR as PLAN_COLOUR
from cert_prep.b1_2_progress_agent import (
    ProgressAgent, ProgressSnapshot, DomainProgress,
    ReadinessAssessment, DomainStatusLine, Nudge,
    generate_weekly_summary, attempt_send_email, send_simple_email,
    generate_profile_pdf, generate_assessment_pdf,
    generate_intake_summary_html,
    NudgeLevel, ReadinessVerdict,
)
from cert_prep.b1_1_learning_path_curator import LearningPathCuratorAgent, LearningPath, LearningModule
from cert_prep.b2_assessment_agent import (
    AssessmentAgent, Assessment, AssessmentResult,
    QuizQuestion, QuestionFeedback,
)
import dataclasses as _dc
import json as _json_mod


def _dc_to_json(obj) -> str:
    """Serialize a dataclass instance to a JSON string."""
    return _json_mod.dumps(_dc.asdict(obj), default=str)


def _dc_filter(cls, d: dict) -> dict:
    """Return a copy of *d* containing only keys that are valid fields of *cls*.
    Silently drops unknown keys (schema-evolution safety) while preserving all
    recognised keys.  Missing required fields (no default) still raise TypeError
    at construction time — that's intentional and surfaceable.
    """
    _known = {f.name for f in _dc.fields(cls)}
    return {k: v for k, v in d.items() if k in _known}


def _progress_snapshot_from_dict(d: dict) -> ProgressSnapshot:
    d2 = _dc_filter(ProgressSnapshot, d)
    d2["domain_progress"] = [
        DomainProgress(**_dc_filter(DomainProgress, dp))
        for dp in d.get("domain_progress", [])
    ]
    return ProgressSnapshot(**d2)


def _readiness_assessment_from_dict(d: dict) -> ReadinessAssessment:
    # Safely coerce verdict enum — fall back to NEEDS_WORK on stale/invalid values
    _valid_verdicts = {e.value for e in ReadinessVerdict}
    _raw_verdict = d.get("verdict", "")
    verdict = ReadinessVerdict(_raw_verdict) if _raw_verdict in _valid_verdicts else ReadinessVerdict.NEEDS_WORK

    _valid_levels = {e.value for e in NudgeLevel}
    d2 = _dc_filter(ReadinessAssessment, d)
    d2["verdict"] = verdict
    d2["domain_status"] = [
        DomainStatusLine(**_dc_filter(DomainStatusLine, ds))
        for ds in d.get("domain_status", [])
    ]
    d2["nudges"] = [
        Nudge(
            level=NudgeLevel(n["level"]) if n.get("level") in _valid_levels else NudgeLevel.INFO,
            title=n.get("title", ""),
            message=n.get("message", ""),
        )
        for n in d.get("nudges", [])
    ]
    return ReadinessAssessment(**d2)


def _assessment_from_dict(d: dict) -> Assessment:
    d2 = _dc_filter(Assessment, d)
    d2["questions"] = [
        QuizQuestion(**_dc_filter(QuizQuestion, q))
        for q in d.get("questions", [])
    ]
    return Assessment(**d2)


def _assessment_result_from_dict(d: dict) -> AssessmentResult:
    d2 = _dc_filter(AssessmentResult, d)
    d2["feedback"] = [
        QuestionFeedback(**_dc_filter(QuestionFeedback, f))
        for f in d.get("feedback", [])
    ]
    return AssessmentResult(**d2)


def _study_plan_from_dict(d: dict) -> StudyPlan:
    from cert_prep.b1_1_study_plan_agent import StudyTask, PrereqInfo
    d2 = _dc_filter(StudyPlan, d)
    d2["tasks"] = [
        StudyTask(**_dc_filter(StudyTask, t))
        for t in d.get("tasks", [])
    ]
    d2["prerequisites"] = [
        PrereqInfo(**_dc_filter(PrereqInfo, p))
        for p in d.get("prerequisites", [])
    ]
    # Back-compat defaults for fields added after initial DB records were saved
    d2.setdefault("review_start_week", max((t.end_week for t in d2["tasks"]), default=d2.get("total_weeks", 8)))
    d2.setdefault("prereq_gap", False)
    d2.setdefault("prereq_message", "")
    d2.setdefault("plan_summary", "")
    return StudyPlan(**d2)


def _learning_path_from_dict(d: dict) -> LearningPath:
    d2 = _dc_filter(LearningPath, d)
    d2["all_modules"] = [
        LearningModule(**_dc_filter(LearningModule, m))
        for m in d.get("all_modules", [])
    ]
    # curated_paths is dict[str, list[LearningModule]]
    cp = d.get("curated_paths", {})
    d2["curated_paths"] = {
        k: [LearningModule(**_dc_filter(LearningModule, m)) for m in v]
        for k, v in cp.items()
    }
    return LearningPath(**d2)


def _raw_from_dict(d: dict) -> RawStudentInput:
    """Load RawStudentInput from a dict, tolerating extra/missing keys.
    Extra keys from future schema versions are silently dropped.
    Missing keys use dataclass defaults (email defaults to '').
    """
    import dataclasses as _dcs
    _known = {f.name for f in _dcs.fields(RawStudentInput)}
    _filtered = {k: v for k, v in d.items() if k in _known}
    return RawStudentInput(**_filtered)


from cert_prep.b3_cert_recommendation_agent import (
    CertificationRecommendationAgent, CertRecommendation,
)
from cert_prep.guardrails import (
    GuardrailsPipeline, GuardrailResult, GuardrailLevel,
)
from cert_prep.database import (
    init_db, get_student, get_all_students, create_student, upsert_student,
    save_profile, save_plan, save_learning_path, save_progress,
    save_assessment, save_cert_recommendation, save_trace,
)
import plotly.express as px
import datetime

# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Certification Preparation AI – Microsoft Exam Preparation",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Login gate ──────────────────────────────────────────────────────────────
APP_PIN = "1234"
ADMIN_USER = "admin"
ADMIN_PASS = "agents2026"

# ─── Demo PDF cache ────────────────────────────────────────────────────────────
# PDFs for fixed demo scenarios are generated once and stored in demo_pdfs/.
# Subsequent calls (download or email) load the cached file instead of running
# the full reportlab pipeline again.  Real users always regenerate.
_DEMO_PDF_DIR = Path(__file__).parent / "demo_pdfs"


def _get_or_generate_pdf(scenario_key, pdf_type: str, generate_fn, *args) -> bytes:
    """Return a cached PDF for a demo scenario, or generate (and cache) a new one.

    Args:
        scenario_key: sidebar_prefill value (\"alex\" / \"priyanka\") or None/\"\" for real users.
        pdf_type:     Short string used in the filename, e.g. \"profile\" or \"assessment\".
        generate_fn:  Callable that produces the PDF bytes.
        *args:        Forwarded to generate_fn.
    """
    if scenario_key:
        _DEMO_PDF_DIR.mkdir(exist_ok=True)
        _cache_path = _DEMO_PDF_DIR / f"{scenario_key}_{pdf_type}.pdf"
        if _cache_path.exists():
            return _cache_path.read_bytes()
    pdf_bytes = generate_fn(*args)
    if scenario_key:
        try:
            _cache_path.write_bytes(pdf_bytes)
        except Exception:
            pass
    return pdf_bytes


# Default demo accounts for quick login
DEMO_USERS = {
    "new":      {"name": "Alex Chen",    "pin": "1234",       "desc": "First-time user · AI-102"},
    "existing": {"name": "Priya Sharma", "pin": "1234",       "desc": "Existing user · AZ-305 prep"},
    "admin":    {"name": "admin",        "pin": "agents2026", "desc": "Dashboard & traces"},
}


def _load_priyanka_session() -> None:
    """Populate session state for the AI Expert demo user (Priyanka Sharma).
    Builds all objects directly from hardcoded data — no DB required.
    This guarantees the returning-user dashboard is shown even on a fresh
    Streamlit Cloud deployment where the SQLite file does not exist yet.
    Also attempts to persist to DB so the Admin Dashboard shows her cohort row.
    """
    import json as _js
    from cert_prep.b1_1_study_plan_agent import StudyTask, PrereqInfo

    _profile_dict = {
        "student_name": "Priyanka Sharma",
        "exam_target": "DP-100",
        "experience_level": "expert_ml",
        "learning_style": "lab_first",
        "hours_per_week": 8.0,
        "weeks_available": 10,
        "total_budget_hours": 80.0,
        "domain_profiles": [
            {"domain_id": "ml_solution_design",   "domain_name": "Design & Prepare an ML Solution",
             "knowledge_level": "strong",   "confidence_score": 0.82, "skip_recommended": False,
             "notes": "Full Azure ML workspace experience including compute and datastore setup."},
            {"domain_id": "explore_train_models", "domain_name": "Explore Data & Train Models",
             "knowledge_level": "strong",   "confidence_score": 0.88, "skip_recommended": True,
             "notes": "Expert pandas/sklearn; AutoML and responsible AI dashboards familiar."},
            {"domain_id": "prepare_deployment",   "domain_name": "Prepare a Model for Deployment",
             "knowledge_level": "moderate", "confidence_score": 0.61, "skip_recommended": False,
             "notes": "MLflow practiced; deployment packaging and environment YAML need review."},
            {"domain_id": "deploy_retrain",       "domain_name": "Deploy & Retrain a Model",
             "knowledge_level": "moderate", "confidence_score": 0.55, "skip_recommended": False,
             "notes": "Online endpoints used; batch endpoints and model monitoring are gaps."},
        ],
        "modules_to_skip": ["Azure ML workspace intro", "Data fundamentals overview"],
        "risk_domains": ["deploy_retrain", "prepare_deployment"],
        "analogy_map": {
            "scikit-learn Pipeline": "Azure ML Pipeline + Environment",
            "MLflow local tracking": "Azure ML MLflow remote tracking",
            "Kubernetes deployment": "Azure ML managed online endpoints",
        },
        "recommended_approach": (
            "Expert data scientist transitioning to full Azure MLOps. "
            "Weeks 1–3 consolidate deployment packaging; weeks 4–8 focus on "
            "online/batch endpoints, monitoring and retraining pipelines."
        ),
        "engagement_notes": "Lab-first: each concept followed immediately by an Azure ML notebook walkthrough.",
    }

    _raw_dict = {
        "student_name": "Priyanka Sharma",
        "exam_target": "DP-100",
        "background_text": (
            "Senior data scientist with 6 years of ML experience. "
            "Proficient in Python, scikit-learn, XGBoost and MLflow. "
            "Migrating team workflows from local experiments to Azure ML."
        ),
        "existing_certs": ["DP-900", "AZ-900"],
        "hours_per_week": 8.0,
        "weeks_available": 10,
        "concern_topics": ["managed online endpoints", "model monitoring", "batch inference"],
        "preferred_style": "Hands-on labs and notebook walkthroughs",
        "goal_text": "Validate Azure ML expertise and move to Lead MLOps Engineer.",
        "email": "",
    }

    _tasks = [
        StudyTask(domain_id="ml_solution_design",   domain_name="Design & Prepare an ML Solution",
                  start_week=1, end_week=2,   total_hours=14.0, priority="medium",   knowledge_level="strong",   confidence_pct=82),
        StudyTask(domain_id="explore_train_models", domain_name="Explore Data & Train Models",
                  start_week=2, end_week=3,   total_hours=14.0, priority="low",      knowledge_level="strong",   confidence_pct=88),
        StudyTask(domain_id="prepare_deployment",   domain_name="Prepare a Model for Deployment",
                  start_week=3, end_week=6,   total_hours=24.0, priority="high",     knowledge_level="moderate", confidence_pct=61),
        StudyTask(domain_id="deploy_retrain",       domain_name="Deploy & Retrain a Model",
                  start_week=6, end_week=9,   total_hours=24.0, priority="critical", knowledge_level="moderate", confidence_pct=55),
    ]
    _prereqs = [
        PrereqInfo(cert_code="DP-900", cert_name="Azure Data Fundamentals",
                   relationship="helpful", already_held=True),
    ]

    from cert_prep.b1_1_study_plan_agent import StudyPlan as _StudyPlan
    _plan = _StudyPlan(
        student_name="Priyanka Sharma",
        exam_target="DP-100",
        total_weeks=10,
        total_hours=80.0,
        tasks=_tasks,
        review_start_week=10,
        prerequisites=_prereqs,
        prereq_gap=False,
        prereq_message="DP-900 already held. All implicit prerequisites satisfied.",
        plan_summary=(
            "10-week expert-track plan for an experienced data scientist moving to Azure MLOps. "
            "Early weeks rapidly review workspace and training fundamentals. "
            "Final weeks focus on deployment packaging, online/batch endpoints and model monitoring."
        ),
    )

    # ── Build learning path ──────────────────────────────────────────────────
    _lp_modules_raw = [
        LearningModule(title="Design and implement data ingestion pipelines",
            url="https://learn.microsoft.com/en-us/training/modules/design-implement-data-ingestion/",
            domain_id="ml_solution_design", duration_min=60, difficulty="intermediate", module_type="module", priority="core"),
        LearningModule(title="Manage and monitor data engineering workloads on Azure",
            url="https://learn.microsoft.com/en-us/training/paths/data-engineering-with-azure-databricks/",
            domain_id="ml_solution_design", duration_min=120, difficulty="intermediate", module_type="learning-path", priority="core"),
        LearningModule(title="Create and manage a workspace in Azure Machine Learning",
            url="https://learn.microsoft.com/en-us/training/modules/intro-to-azure-machine-learning-service/",
            domain_id="ml_solution_design", duration_min=45, difficulty="beginner", module_type="module", priority="supplemental"),
        LearningModule(title="Explore and analyze data with Python",
            url="https://learn.microsoft.com/en-us/training/paths/explore-data-science-tools-in-azure/",
            domain_id="explore_train_models", duration_min=90, difficulty="intermediate", module_type="learning-path", priority="core"),
        LearningModule(title="Train and evaluate deep learning models",
            url="https://learn.microsoft.com/en-us/training/modules/train-evaluate-deep-learn-models/",
            domain_id="explore_train_models", duration_min=75, difficulty="advanced", module_type="module", priority="core"),
        LearningModule(title="Automate machine learning model selection with Azure Machine Learning",
            url="https://learn.microsoft.com/en-us/training/modules/automate-model-selection-with-azure-automl/",
            domain_id="explore_train_models", duration_min=50, difficulty="intermediate", module_type="module", priority="supplemental"),
        LearningModule(title="Register and deploy machine learning models with Azure ML",
            url="https://learn.microsoft.com/en-us/training/modules/register-and-deploy-model-with-amls/",
            domain_id="prepare_deployment", duration_min=60, difficulty="intermediate", module_type="module", priority="core"),
        LearningModule(title="Make predictions with Azure Machine Learning designer",
            url="https://learn.microsoft.com/en-us/training/modules/score-model-introduction-to-inferencing/",
            domain_id="prepare_deployment", duration_min=45, difficulty="intermediate", module_type="module", priority="core"),
        LearningModule(title="Deploy and consume models with Azure Machine Learning",
            url="https://learn.microsoft.com/en-us/training/paths/deploy-consume-models-azure-machine-learning/",
            domain_id="deploy_retrain", duration_min=120, difficulty="advanced", module_type="learning-path", priority="core"),
        LearningModule(title="Monitor models with Azure Machine Learning",
            url="https://learn.microsoft.com/en-us/training/modules/monitor-models-with-azure-machine-learning/",
            domain_id="deploy_retrain", duration_min=50, difficulty="advanced", module_type="module", priority="core"),
        LearningModule(title="Retrain and update machine learning models with Azure ML pipelines",
            url="https://learn.microsoft.com/en-us/training/modules/retrain-update-models-with-azure-machine-learning-pipeline/",
            domain_id="deploy_retrain", duration_min=55, difficulty="advanced", module_type="module", priority="core"),
    ]
    _curated = {}
    for _mod in _lp_modules_raw:
        _curated.setdefault(_mod.domain_id, []).append(_mod)
    _lp = LearningPath(
        student_name="Priyanka Sharma",
        exam_target="DP-100",
        curated_paths=_curated,
        all_modules=_lp_modules_raw,
        total_hours_est=round(sum(m.duration_min for m in _lp_modules_raw) / 60.0, 1),
        skipped_domains=["explore_train_models"],
        summary=("Curated DP-100 path focused on deployment packaging and MLOps. "
                 "Training and exploration domains are in rapid-review mode."),
    )

    # ── Set session state ─────────────────────────────────────────────────────
    st.session_state["learning_path"]    = _lp
    st.session_state["profile"]          = LearnerProfile.model_validate(_profile_dict)
    st.session_state["raw"]              = RawStudentInput(**{k: v for k, v in _raw_dict.items()
                                                              if k in {f.name for f in _dc.fields(RawStudentInput)}})
    st.session_state["plan"]             = _plan
    st.session_state["intake_submitted"] = True
    st.session_state["is_demo_user"]     = False

    # ── Persist to DB (best-effort — non-fatal if it fails) ───────────────────
    try:
        init_db()
        upsert_student("Priyanka Sharma", "1234", "learner")
        _plan_dict = {
            "student_name": _plan.student_name, "exam_target": _plan.exam_target,
            "total_weeks": _plan.total_weeks, "total_hours": _plan.total_hours,
            "review_start_week": _plan.review_start_week,
            "prereq_gap": _plan.prereq_gap, "prereq_message": _plan.prereq_message,
            "plan_summary": _plan.plan_summary,
            "tasks": [t.__dict__ for t in _plan.tasks],
            "prerequisites": [p.__dict__ for p in _plan.prerequisites],
        }
        save_profile("Priyanka Sharma", _js.dumps(_profile_dict), _js.dumps(_raw_dict), "DP-100")
        save_plan("Priyanka Sharma", _js.dumps(_plan_dict))
        save_learning_path("Priyanka Sharma", _dc_to_json(_lp))
    except Exception:
        pass  # DB write failure is acceptable — session state is already set


@st.cache_resource
def _app_startup() -> None:
    """Initialise DB and seed required demo data — runs once per app process."""
    import json as _js
    import textwrap

    init_db()

    # ── Seed Priyanka Sharma (AI Expert / DP-100 returning user) ─────────────
    # This data lives only in the cloud DB (cert_prep_data.db is git-ignored).
    # Without this seed, Streamlit Cloud would treat her as a new user.
    if not get_student("Priyanka Sharma"):
        upsert_student("Priyanka Sharma", "1234", "learner")

        _profile = {
            "student_name": "Priyanka Sharma",
            "exam_target": "DP-100",
            "experience_level": "expert_ml",
            "learning_style": "lab_first",
            "hours_per_week": 8.0,
            "weeks_available": 10,
            "total_budget_hours": 80.0,
            "domain_profiles": [
                {"domain_id": "ml_solution_design",   "domain_name": "Design & Prepare an ML Solution",
                 "knowledge_level": "strong",   "confidence_score": 0.82, "skip_recommended": False,
                 "notes": "Has full Azure ML workspace experience including compute and datastore setup."},
                {"domain_id": "explore_train_models", "domain_name": "Explore Data & Train Models",
                 "knowledge_level": "strong",   "confidence_score": 0.88, "skip_recommended": True,
                 "notes": "Expert pandas/sklearn user; AutoML and responsible AI dashboards are familiar."},
                {"domain_id": "prepare_deployment",   "domain_name": "Prepare a Model for Deployment",
                 "knowledge_level": "moderate", "confidence_score": 0.61, "skip_recommended": False,
                 "notes": "MLflow logging practiced; deployment packaging and environment YAML need review."},
                {"domain_id": "deploy_retrain",       "domain_name": "Deploy & Retrain a Model",
                 "knowledge_level": "moderate", "confidence_score": 0.55, "skip_recommended": False,
                 "notes": "Online endpoints used in production; batch endpoints and model monitoring are gaps."},
            ],
            "modules_to_skip": ["Azure ML workspace intro", "Data fundamentals overview"],
            "risk_domains": ["deploy_retrain", "prepare_deployment"],
            "analogy_map": {
                "scikit-learn Pipeline": "Azure ML Pipeline + Environment",
                "MLflow local tracking": "Azure ML MLflow remote tracking",
                "Kubernetes deployment": "Azure ML managed online endpoints",
            },
            "recommended_approach": textwrap.dedent("""\
                Priyanka is an expert data scientist transitioning to full Azure MLOps.
                Weeks 1–3 consolidate deployment packaging and environment management.
                Weeks 4–8 focus on online/batch endpoints, monitoring and retraining pipelines."""),
            "engagement_notes": "Lab-first: every concept should follow an Azure ML notebook walkthrough immediately.",
        }

        _raw = {
            "student_name": "Priyanka Sharma",
            "exam_target": "DP-100",
            "background_text": (
                "Senior data scientist with 6 years of ML experience. "
                "Proficient in Python, scikit-learn, XGBoost and MLflow. "
                "Currently migrating team workflows from local experiments to Azure ML."
            ),
            "existing_certs": ["DP-900", "AZ-900"],
            "hours_per_week": 8.0,
            "weeks_available": 10,
            "concern_topics": ["managed online endpoints", "model monitoring", "batch inference pipelines"],
            "preferred_style": "Hands-on labs and real notebook walkthroughs",
            "goal_text": "Validate Azure ML expertise and advance to a Lead MLOps Engineer role.",
            "email": "",
        }

        _plan = {
            "student_name": "Priyanka Sharma",
            "exam_target": "DP-100",
            "total_weeks": 10,
            "total_hours": 80.0,
            "tasks": [
                {"domain_id": "ml_solution_design",   "domain_name": "Design & Prepare an ML Solution",
                 "start_week": 1, "end_week": 2, "total_hours": 14.0, "priority": "medium",
                 "knowledge_level": "strong", "confidence_pct": 82},
                {"domain_id": "explore_train_models", "domain_name": "Explore Data & Train Models",
                 "start_week": 2, "end_week": 3, "total_hours": 14.0, "priority": "low",
                 "knowledge_level": "strong", "confidence_pct": 88},
                {"domain_id": "prepare_deployment",   "domain_name": "Prepare a Model for Deployment",
                 "start_week": 3, "end_week": 6, "total_hours": 24.0, "priority": "high",
                 "knowledge_level": "moderate", "confidence_pct": 61},
                {"domain_id": "deploy_retrain",       "domain_name": "Deploy & Retrain a Model",
                 "start_week": 6, "end_week": 9, "total_hours": 24.0, "priority": "critical",
                 "knowledge_level": "moderate", "confidence_pct": 55},
            ],
            "review_start_week": 10,
            "prerequisites": [
                {"cert_code": "DP-900", "cert_name": "Azure Data Fundamentals",
                 "relationship": "helpful", "already_held": True},
            ],
            "prereq_gap": False,
            "prereq_message": "DP-900 already held. All implicit prerequisites satisfied.",
            "plan_summary": textwrap.dedent("""\
                10-week expert-track plan for an experienced data scientist moving to Azure MLOps.
                Early weeks perform rapid review of workspace and training fundamentals.
                Final stretch focuses on deployment packaging, online/batch endpoints and model monitoring."""),
        }

        _snapshot = {
            "student_name": "Priyanka Sharma",
            "exam_target": "DP-100",
            "week_number": 6,
            "domain_scores": {
                "ml_solution_design":   0.87,
                "explore_train_models": 0.91,
                "prepare_deployment":   0.70,
                "deploy_retrain":       0.58,
            },
            "readiness_pct": 76,
            "hours_logged": 52,
            "hours_remaining": 28,
        }

        _progress_assessment = {
            "student_name": "Priyanka Sharma",
            "exam_target": "DP-100",
            "readiness_pct": 76,
            "exam_go_nogo": "CONDITIONAL GO",
            "weak_area_flags": ["deploy_retrain"],
            "recommendation": textwrap.dedent("""\
                Strong in design and training domains. Complete the remaining deployment and
                retraining labs (weeks 7–9) to reach GO status. On track for exam success."""),
        }

        from cert_prep.database import save_profile, save_plan, save_progress
        save_profile("Priyanka Sharma", _js.dumps(_profile), _js.dumps(_raw), "DP-100")
        save_plan("Priyanka Sharma", _js.dumps(_plan))
        save_progress("Priyanka Sharma", _js.dumps(_snapshot), _js.dumps(_progress_assessment))


_app_startup()


if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["user_type"] = None  # "new", "existing", or "admin"

if not st.session_state["authenticated"]:
    # ── Microsoft Learn-inspired login CSS ───────────────────────────────────
    st.markdown("""
    <style>
      /* Hide sidebar & header, collapse top padding */
      [data-testid="stSidebar"] { display: none; }
      [data-testid="stHeader"] { display: none; }
      .block-container { padding-top: 0 !important; padding-bottom: 0.5rem !important; margin-top: 0 !important; }
      /* MS Learn light background */
      [data-testid="stAppViewContainer"] {
        background: #f5f5f5;
        font-family: 'Segoe UI', -apple-system, system-ui, sans-serif;
      }
      /* ── Blue top banner (half text, half image) ─── */
      .ms-top-bar {
        background: linear-gradient(135deg, #0078D4 0%, #005A9E 100%);
        padding: 1.6rem 3rem 1.8rem 3rem;
        margin: -1rem -3rem 0 -3rem;
        display: grid;
        grid-template-columns: 1fr 1.1fr;
        gap: 2.5rem;
        align-items: center;
      }
      .ms-top-left h1 {
        color: #fff !important; font-size: 2.5rem; font-weight: 600;
        margin: 0 0 18px; font-family: 'Segoe UI', sans-serif;
        letter-spacing: -0.02em; line-height: 1.2;
      }
      .ms-top-left h1 a { display: none !important; }
      .ms-top-left p {
        color: rgba(255,255,255,0.9); font-size: 1rem;
        margin: 0; line-height: 1.65; max-width: 540px;
      }
      .ms-top-right {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        padding: 0;
        align-items: start;
      }
      .hero-visual-col {
        display: flex;
        flex-direction: column;
        gap: 12px;
      }
      .hero-box {
        border-radius: 20px;
        overflow: hidden;
        position: relative;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 7px;
        box-shadow: 0 6px 24px rgba(0,0,0,0.28);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        flex-shrink: 0;
        padding: 12px 6px;
      }
      .hero-box:hover {
        transform: translateY(-4px) scale(1.02);
        box-shadow: 0 12px 32px rgba(0,0,0,0.38);
      }
      .hero-box.tall  { height: 180px; }
      .hero-box.short { height: 100px; }
      .hero-box svg {
        width: 58px; height: 58px;
        filter: drop-shadow(0 2px 8px rgba(0,0,0,0.22));
      }
      .hero-box.short svg { width: 42px; height: 42px; }
      .hb-label {
        color: rgba(255,255,255,0.92);
        font-size: 0.56rem;
        font-weight: 700;
        text-align: center;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        line-height: 1.3;
        padding: 0 4px;
      }
      /* Vivid bento gradients — exact match to design */
      .hero-box.grad1 { background: linear-gradient(145deg, #6C3DD8 0%, #8B34F0 100%); }
      .hero-box.grad2 { background: linear-gradient(145deg, #F0368A 0%, #C2185B 100%); }
      .hero-box.grad3 { background: linear-gradient(145deg, #00C8E0 0%, #0097B2 100%); }
      .hero-box.grad4 { background: linear-gradient(145deg, #2ECC71 0%, #16A34A 100%); }
      .hero-box.grad5 { background: linear-gradient(145deg, #FFC107 0%, #FF8C00 100%); }
      .hero-box.grad6 { background: linear-gradient(145deg, #4A5FD4 0%, #2A3FAA 100%); }
      /* ── Benefit cards (vertical, MS Learn style) ─── */
      .ben-grid {
        display: grid; grid-template-columns: 1fr 1fr; gap: 20px;
        margin: 28px 0 0 0;
        padding: 0;
      }
      .ben-card {
        background: #fff;
        border: 1px solid #E1DFDD;
        border-radius: 10px;
        overflow: hidden;
        transition: box-shadow 0.2s;
      }
      .ben-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.1); }
      .ben-card .card-banner {
        height: 64px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.8rem;
      }
      .ben-card .card-body {
        padding: 18px 22px 22px;
      }
      .ben-card .card-body h4 {
        color: #1B1B1B; font-size: 1.05rem; font-weight: 600;
        margin: 0 0 8px; font-family: 'Segoe UI', sans-serif;
        line-height: 1.3;
      }
      .ben-card .card-body h4 a { display: none !important; }
      .ben-card .card-body p {
        color: #505050; font-size: 0.85rem;
        margin: 0; line-height: 1.6;
      }
      .ben-card .card-body .svc-tag {
        display: inline-block; margin-top: 10px;
        font-size: 0.62rem; font-weight: 700; letter-spacing: 0.06em;
        text-transform: uppercase; border-radius: 20px;
        padding: 3px 10px;
      }
      .banner-blue   { background: linear-gradient(135deg, #EFF6FF 0%, #DCEAFE 100%); }
      .banner-teal   { background: linear-gradient(135deg, #E6FAFA 0%, #CCF5F5 100%); }
      .banner-green  { background: linear-gradient(135deg, #F0FFF4 0%, #D1FAE5 100%); }
      .banner-purple { background: linear-gradient(135deg, #F3E8FF 0%, #E9D5FF 100%); }
      /* Tech stack strip */
      .tech-strip {
        margin-top: 8px; padding: 8px 0 0;
        border-top: 1px solid #E8E6E3;
      }
      .tech-strip-label {
        color: #8A8886; font-size: 0.55rem; text-transform: uppercase;
        letter-spacing: 0.1em; font-weight: 600; margin-bottom: 6px;
      }
      .tech-pills {
        display: flex; flex-wrap: wrap; gap: 6px;
      }
      .tech-pill {
        display: inline-flex; align-items: center; gap: 5px;
        background: #fff; border: 1px solid #E1DFDD;
        border-radius: 20px; padding: 4px 10px 4px 7px;
        font-size: 0.65rem; color: #323130; font-weight: 600;
        font-family: 'Segoe UI', sans-serif; transition: all 0.15s;
      }
      .tech-pill:hover { border-color: #0078D4; background: #F3F9FF; }
      .tech-pill svg, .tech-pill img { width: 16px; height: 16px; }
      .tech-pill .tp-icon { font-size: 0.85rem; line-height: 1; }
      /* ── Sign-in card ───────────────────────────── */
      .signin-card {
        background: #fff;
        border: 1px solid #E1DFDD;
        border-radius: 4px;
        padding: 24px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.06);
      }
      .signin-title {
        text-align: center; color: #1B1B1B; font-size: 1rem;
        font-weight: 600; margin-bottom: 0px;
        font-family: 'Segoe UI', sans-serif;
      }
      .signin-sub {
        text-align: center; color: #616161;
        font-size: 0.7rem; margin-bottom: 6px;
      }
      /* Demo persona cards — HTML card visual + invisible button overlay */
      .dcg [data-testid="column"] { padding: 0 3px !important; }
      .demo-card {
        background: linear-gradient(160deg,#EFF6FF 0%,#DCEAFE 100%);
        border: 1.5px solid #BFD4EF;
        border-radius: 10px;
        padding: 0 8px;
        text-align: center;
        height: 100px;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        cursor: pointer;
        transition: box-shadow 0.18s ease, transform 0.18s ease, background 0.18s ease, border-color 0.18s ease;
        box-shadow: 0 1px 4px rgba(0,120,212,0.07);
        pointer-events: none;
        user-select: none;
        overflow: hidden;
        box-sizing: border-box;
      }
      .demo-card .dc-icon { font-size: 1.35rem; line-height: 1; margin-bottom: 5px; flex-shrink: 0; }
      .demo-card .dc-title { font-size: 0.8rem; font-weight: 700; color: #0C3C78; line-height: 1.2; white-space: nowrap; }
      .demo-card .dc-sub { font-size: 0.67rem; color: #1A56A0; margin-top: 3px; white-space: nowrap; }
      /* Collapse the element-container holding the invisible button so it adds no height */
      div.element-container:has(.demo-card) + div.element-container {
        height: 0 !important;
        min-height: 0 !important;
        overflow: visible !important;
        margin: 0 !important;
        padding: 0 !important;
      }
      /* Invisible button overlays the card above */
      div.element-container:has(.demo-card) + div.element-container .stButton > button {
        height: 100px !important;
        margin-top: -100px !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        opacity: 0 !important;
        cursor: pointer !important;
        position: relative !important;
        z-index: 10 !important;
        width: 100% !important;
      }
      /* Hover: animate the card when the invisible button above it is hovered */
      div.element-container:has(.demo-card):has(+ div.element-container .stButton > button:hover) .demo-card {
        background: linear-gradient(160deg,#DCEAFE 0%,#BDD7F5 100%);
        border-color: #0078D4;
        box-shadow: 0 5px 16px rgba(0,120,212,0.18);
        transform: translateY(-2px);
      }
      /* Quick-login Streamlit buttons */
      .stButton > button {
        background: #0078D4 !important;
        border: none !important;
        border-radius: 4px !important;
        color: #fff !important;
        font-size: 0.7rem !important;
        font-weight: 600 !important;
        padding: 4px 6px !important;
        font-family: 'Segoe UI', sans-serif !important;
        transition: background 0.15s;
      }
      .stButton > button:hover {
        background: #106EBE !important;
      }
      /* Divider */
      .or-sep {
        display: flex; align-items: center; gap: 8px;
        margin: 4px 0; color: #a0a0a0;
        font-size: 0.65rem;
      }
      .or-sep::before, .or-sep::after {
        content: ''; flex: 1; height: 1px;
        background: #E1DFDD;
      }
      /* Radio role selector */
      div[data-testid="stRadio"] label,
      div[data-testid="stRadio"] [role="radiogroup"] label {
        background: #FAFAFA !important;
        border: 1px solid #E1DFDD !important;
        border-radius: 4px !important;
        padding: 9px 14px !important;
        transition: all 0.2s ease; cursor: pointer;
        margin-bottom: 2px !important;
      }
      div[data-testid="stRadio"] label:hover {
        background: #EFF6FF !important;
        border-color: #0078D4 !important;
      }
      /* Force ALL radio label text visible */
      div[data-testid="stRadio"] label *,
      div[data-testid="stRadio"] label span,
      div[data-testid="stRadio"] label p,
      div[data-testid="stRadio"] label div,
      div[data-testid="stRadio"] [role="radiogroup"] label *,
      div[data-testid="stHorizontalRadio"] label *,
      div[data-testid="stHorizontalRadio"] label {
        color: #1B1B1B !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        font-family: 'Segoe UI', sans-serif !important;
      }
      /* Selected radio */
      div[data-testid="stRadio"] label:has(input:checked) {
        background: #EFF6FF !important;
        border-color: #0078D4 !important;
      }
      div[data-testid="stRadio"] label:has(input:checked) *,
      div[data-testid="stRadio"] label:has(input:checked) span,
      div[data-testid="stRadio"] label:has(input:checked) p {
        color: #0078D4 !important;
      }
      div[data-testid="stHorizontalRadio"] label:has(input:checked) {
        background: #EFF6FF !important;
        border-color: #0078D4 !important;
      }
      div[data-testid="stHorizontalRadio"] label:has(input:checked) * {
        color: #0078D4 !important;
      }
      /* Text inputs */
      .stTextInput input {
        background: #fff !important;
        border: 1px solid #E1DFDD !important;
        border-radius: 4px !important;
        color: #1B1B1B !important;
        padding: 10px 12px !important;
        font-size: 0.8rem !important;
        font-family: 'Segoe UI', sans-serif !important;
        width: 100% !important;
        box-sizing: border-box !important;
        height: 44px !important;
        line-height: 1.4 !important;
      }
      .stTextInput input:focus {
        border-color: #0078D4 !important;
        box-shadow: 0 0 0 1px #0078D4 !important;
      }
      .stTextInput input::placeholder { color: #a0a0a0 !important; }
      /* Equal size for all login form inputs */
      .stTextInput, .stTextInput > div {
        width: 100% !important;
      }
      .stTextInput [data-testid="stTextInputRootElement"] {
        height: 44px !important;
      }
      /* Hide password toggle icon + the separator border it sits behind */
      .stTextInput button[kind="icon"],
      .stTextInput [data-testid="stTextInputRootElement"] button,
      .stTextInput [data-testid="stTextInputRootElement"] button ~ div,
      .stTextInput [data-testid="stTextInputRootElement"] > div > div:last-child:has(button),
      [data-testid="InputInstructions"] {
        display: none !important;
        border: none !important;
      }
      /* Remove the right-side border on the input itself */
      .stTextInput input[type="password"] {
        border-right: none !important;
        padding-right: 12px !important;
      }
      /* Submit button — Microsoft blue */
      .stFormSubmitButton button {
        background: #0078D4 !important;
        border: none !important; border-radius: 4px !important;
        padding: 7px !important; font-size: 0.8rem !important;
        font-weight: 600 !important; color: #fff !important;
        font-family: 'Segoe UI', sans-serif !important;
        transition: background 0.15s ease;
      }
      .stFormSubmitButton button:hover {
        background: #106EBE !important;
      }
      .role-desc {
        text-align: center; color: #616161;
        font-size: 0.76rem; margin: 4px 0 8px;
        min-height: 24px;
      }
    </style>
    """, unsafe_allow_html=True)

    # ── Blue top banner (half text, half visual) ────────────────────────────────────
    st.markdown("""
    <div class="ms-top-bar">
      <div class="ms-top-left">
        <h1>Agents League — AI-Powered Certification Prep</h1>
        <p>A production-grade multi-agent system built on <strong style="color:#fff">Azure AI Foundry</strong>.
        Eight specialised reasoning agents — powered by <strong style="color:#fff">Azure OpenAI GPT-4o</strong>,
        safeguarded by <strong style="color:#fff">Azure Content Safety</strong>, and persisted in <strong style="color:#fff">SQLite</strong>
        — deliver personalised study plans, adaptive quizzes, and exam-readiness verdicts for 9 Microsoft certifications.
        (Azure AI Search &amp; Cosmos DB on roadmap)</p>
      </div>
      <div class="ms-top-right">
        <div class="hero-visual-col">
          <div class="hero-box tall grad1">
            <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
              <polygon points="32,5 53,17 53,41 32,53 11,41 11,17" stroke="white" stroke-width="2.5" fill="rgba(255,255,255,0.15)"/>
              <circle cx="32" cy="22" r="4.5" fill="white"/>
              <circle cx="19" cy="34" r="4.5" fill="white"/>
              <circle cx="45" cy="34" r="4.5" fill="white"/>
              <circle cx="32" cy="44" r="3.5" fill="rgba(255,255,255,0.6)"/>
              <line x1="32" y1="26" x2="21" y2="30" stroke="white" stroke-width="1.5"/>
              <line x1="32" y1="26" x2="43" y2="30" stroke="white" stroke-width="1.5"/>
              <line x1="21" y1="38" x2="30" y2="41" stroke="white" stroke-width="1.5"/>
              <line x1="43" y1="38" x2="34" y2="41" stroke="white" stroke-width="1.5"/>
            </svg>
            <div class="hb-label">AI Foundry</div>
          </div>
          <div class="hero-box short grad2">
            <svg viewBox="0 0 52 52" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="26" cy="26" r="9" fill="white"/>
              <ellipse cx="26" cy="26" rx="21" ry="7.5" stroke="white" stroke-width="2.5" fill="none"/>
              <ellipse cx="26" cy="26" rx="21" ry="7.5" stroke="rgba(255,255,255,0.6)" stroke-width="1.5" fill="none" transform="rotate(60 26 26)"/>
            </svg>
            <div class="hb-label">SQLite</div>
          </div>
        </div>
        <div class="hero-visual-col">
          <div class="hero-box short grad3">
            <svg viewBox="0 0 52 52" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="26" cy="26" r="18" stroke="white" stroke-width="2" fill="rgba(255,255,255,0.1)"/>
              <circle cx="26" cy="26" r="11" stroke="white" stroke-width="1.5" fill="rgba(255,255,255,0.1)"/>
              <circle cx="26" cy="26" r="5" fill="white"/>
              <circle cx="26" cy="8" r="3" fill="white"/>
              <circle cx="40" cy="17" r="3" fill="white"/>
              <circle cx="40" cy="35" r="3" fill="white"/>
              <circle cx="26" cy="44" r="3" fill="white"/>
              <circle cx="12" cy="35" r="3" fill="white"/>
              <circle cx="12" cy="17" r="3" fill="white"/>
            </svg>
            <div class="hb-label">Azure OpenAI</div>
          </div>
          <div class="hero-box tall grad4">
            <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="27" cy="27" r="17" stroke="white" stroke-width="3" fill="rgba(255,255,255,0.15)"/>
              <circle cx="27" cy="27" r="8" fill="rgba(255,255,255,0.2)"/>
              <circle cx="27" cy="27" r="3.5" fill="white"/>
              <line x1="40" y1="40" x2="56" y2="57" stroke="white" stroke-width="4" stroke-linecap="round"/>
              <line x1="20" y1="21" x2="34" y2="21" stroke="white" stroke-width="2" stroke-linecap="round"/>
              <line x1="20" y1="27" x2="32" y2="27" stroke="white" stroke-width="2" stroke-linecap="round"/>
              <line x1="20" y1="33" x2="27" y2="33" stroke="white" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <div class="hb-label">AI Search</div>
          </div>
        </div>
        <div class="hero-visual-col">
          <div class="hero-box tall grad5">
            <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="10" cy="20" r="5" fill="white"/>
              <circle cx="10" cy="44" r="5" fill="white"/>
              <circle cx="32" cy="10" r="5" fill="rgba(255,255,255,0.85)"/>
              <circle cx="32" cy="32" r="7" fill="white"/>
              <circle cx="32" cy="54" r="5" fill="rgba(255,255,255,0.85)"/>
              <circle cx="54" cy="20" r="5" fill="white"/>
              <circle cx="54" cy="44" r="5" fill="white"/>
              <line x1="15" y1="21" x2="25" y2="14" stroke="rgba(255,255,255,0.65)" stroke-width="1.5"/>
              <line x1="15" y1="21" x2="25" y2="29" stroke="rgba(255,255,255,0.65)" stroke-width="1.5"/>
              <line x1="15" y1="43" x2="25" y2="35" stroke="rgba(255,255,255,0.65)" stroke-width="1.5"/>
              <line x1="15" y1="43" x2="25" y2="49" stroke="rgba(255,255,255,0.65)" stroke-width="1.5"/>
              <line x1="49" y1="21" x2="39" y2="14" stroke="rgba(255,255,255,0.65)" stroke-width="1.5"/>
              <line x1="49" y1="21" x2="39" y2="29" stroke="rgba(255,255,255,0.65)" stroke-width="1.5"/>
              <line x1="49" y1="43" x2="39" y2="35" stroke="rgba(255,255,255,0.65)" stroke-width="1.5"/>
              <line x1="49" y1="43" x2="39" y2="49" stroke="rgba(255,255,255,0.65)" stroke-width="1.5"/>
            </svg>
            <div class="hb-label">Machine Learning</div>
          </div>
          <div class="hero-box short grad6">
            <svg viewBox="0 0 52 52" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="7" y="13" width="38" height="24" rx="7" fill="rgba(255,255,255,0.18)" stroke="white" stroke-width="2.5"/>
              <circle cx="19" cy="25" r="4" fill="white"/>
              <circle cx="33" cy="25" r="4" fill="white"/>
              <path d="M19 37 L26 46 L33 37" fill="rgba(255,255,255,0.7)" stroke="rgba(255,255,255,0.8)" stroke-width="1.5" stroke-linejoin="round"/>
              <rect x="23" y="6" width="6" height="7" rx="3" fill="white"/>
            </svg>
            <div class="hb-label">Bot Service</div>
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Two-panel layout ─────────────────────────────────────────────────────
    _left, _spacer, _right = st.columns([1.2, 0.08, 0.72])

    # ── LEFT: 4 Benefit cards (2x2 grid) ──────────────────────────────────
    with _left:
        st.markdown("""
        <div class="ben-grid">
          <div class="ben-card">
            <div class="card-banner banner-blue">🎯</div>
            <div class="card-body">
              <h4>Personalised Skill Profiling</h4>
              <p>AI analyses your background and domain knowledge to pinpoint exactly where you stand — data-driven insights across every exam domain.</p>
            </div>
          </div>
          <div class="ben-card">
            <div class="card-banner banner-teal">📅</div>
            <div class="card-body">
              <h4>Smart Study Plans</h4>
              <p>Priority-weighted, week-by-week schedules built around your available hours. Focus on high-impact domains first.</p>
            </div>
          </div>
          <div class="ben-card">
            <div class="card-banner banner-green">✅</div>
            <div class="card-body">
              <h4>Exam-Ready Confidence</h4>
              <p>Track progress with mid-journey check-ins, practice quizzes, and a clear GO / NO-GO readiness verdict.</p>
            </div>
          </div>
          <div class="ben-card">
            <div class="card-banner banner-purple">🧠</div>
            <div class="card-body">
              <h4>Adaptive Learning Paths</h4>
              <p>Curated Microsoft Learn modules matched to your gaps with smart sequencing — learn what matters, skip what you know.</p>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── RIGHT: Sign-in form ──────────────────────────────────────────────────
    with _right:
        st.markdown('<div class="signin-title">Sign In</div>', unsafe_allow_html=True)
        st.markdown('<div class="signin-sub">Pick a demo account or sign in manually</div>', unsafe_allow_html=True)

        # Quick-login: HTML card (visual) + invisible overlay button for click handling
        _d1, _d2, _d3 = st.columns(3, gap="small")
        with _d1:
            st.markdown('''
            <div class="demo-card">
              <div class="dc-icon">🌱</div>
              <div class="dc-title">AI Beginner</div>
              <div class="dc-sub">First-time · AI-102</div>
            </div>
            ''', unsafe_allow_html=True)
            if st.button("​", key="demo_new", use_container_width=True):  # invisible overlay
                upsert_student("Alex Chen", "1234", "learner")
                st.session_state["authenticated"] = True
                st.session_state["login_name"] = "Alex Chen"
                st.session_state["user_type"] = "learner"
                st.session_state["is_demo_user"] = True  # fresh user — show scenario picker
                st.rerun()
        with _d2:
            st.markdown('''
            <div class="demo-card">
              <div class="dc-icon">🏆</div>
              <div class="dc-title">AI Expert</div>
              <div class="dc-sub">Returning · DP-100</div>
            </div>
            ''', unsafe_allow_html=True)
            if st.button("​", key="demo_jordan", use_container_width=True):  # invisible overlay
                upsert_student("Priyanka Sharma", "1234", "learner")
                st.session_state["authenticated"] = True
                st.session_state["login_name"] = "Priyanka Sharma"
                st.session_state["user_type"] = "learner"
                # Build session state directly from hardcoded demo data — no DB dependency
                _load_priyanka_session()
                st.rerun()
        with _d3:
            st.markdown('''
            <div class="demo-card">
              <div class="dc-icon">🔐</div>
              <div class="dc-title">Admin</div>
              <div class="dc-sub">Dashboard &amp; Traces</div>
            </div>
            ''', unsafe_allow_html=True)
            if st.button("​", key="demo_admin", use_container_width=True):  # invisible overlay
                st.session_state["authenticated"] = True
                st.session_state["login_name"] = "Admin"
                st.session_state["user_type"] = "admin"
                st.session_state["admin_logged_in"] = True
                st.switch_page("pages/1_Admin_Dashboard.py")
        st.markdown('<div class="or-sep">or sign in manually</div>', unsafe_allow_html=True)

        # Manual login form (unified — no role selector)
        with st.form("login_form"):
            user_name = st.text_input("Your name", placeholder="Enter your name or 'admin'", label_visibility="collapsed")
            credential = st.text_input("PIN / Password", type="password", placeholder="PIN: 1234", label_visibility="collapsed")
            login_btn = st.form_submit_button("Sign In →", type="primary", use_container_width=True)

        st.markdown("""
        <div class="tech-strip">
          <div class="tech-strip-label">Azure AI &amp; Developer Services powering this app</div>
          <div class="tech-pills">
            <div class="tech-pill">
              <svg viewBox="0 0 23 23"><rect width="11" height="11" fill="#f25022"/><rect x="12" width="11" height="11" fill="#7fba00"/><rect y="12" width="11" height="11" fill="#00a4ef"/><rect x="12" y="12" width="11" height="11" fill="#ffb900"/></svg>
              AI Foundry
            </div>
            <div class="tech-pill">
              <svg viewBox="0 0 16 16" width="16" height="16" fill="none">
                <circle cx="8" cy="8" r="6.5" stroke="#0078D4" stroke-width="1.3"/>
                <circle cx="8" cy="8" r="2.5" fill="#0078D4"/>
                <path d="M8 1.5V4M8 12V14.5M1.5 8H4M12 8H14.5" stroke="#0078D4" stroke-width="1.2" stroke-linecap="round"/>
              </svg>
              Azure OpenAI GPT-4o
            </div>
            <div class="tech-pill">
              <svg viewBox="0 0 16 16" width="16" height="16" fill="none">
                <path d="M8 1.5C5 1.5 2.5 4 2.5 7C2.5 9.5 4 11.6 6.2 12.5L6 14.5H10L9.8 12.5C12 11.6 13.5 9.5 13.5 7C13.5 4 11 1.5 8 1.5Z" fill="#825EE4" opacity="0.2"/>
                <path d="M8 1.5C5 1.5 2.5 4 2.5 7C2.5 9.5 4 11.6 6.2 12.5L6 14.5H10L9.8 12.5C12 11.6 13.5 9.5 13.5 7C13.5 4 11 1.5 8 1.5Z" stroke="#825EE4" stroke-width="1.2"/>
                <path d="M5.5 6.5L8 4.5L10.5 6.5L9.5 9H6.5L5.5 6.5Z" fill="#825EE4"/>
              </svg>
              Microsoft Copilot
            </div>
            <div class="tech-pill">
              <svg viewBox="0 0 16 16" width="16" height="16" fill="none">
                <circle cx="8" cy="3.5" r="2" fill="#0078D4"/>
                <circle cx="2.5" cy="12.5" r="2" fill="#0078D4"/>
                <circle cx="13.5" cy="12.5" r="2" fill="#0078D4"/>
                <path d="M8 5.5L2.5 10.5M8 5.5L13.5 10.5M2.5 12.5H13.5" stroke="#0078D4" stroke-width="1.1"/>
              </svg>
              MCP
            </div>
            <div class="tech-pill"><span class="tp-icon">⚡</span> Streamlit</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Handle login submission
        if login_btn:
            if not user_name.strip():
                st.error("Please enter your name.")
            elif user_name.strip().lower() == ADMIN_USER and credential == ADMIN_PASS:
                # Admin login
                st.session_state["authenticated"] = True
                st.session_state["login_name"] = "Admin"
                st.session_state["user_type"] = "admin"
                st.session_state["admin_logged_in"] = True
                st.rerun()
            elif credential != APP_PIN:
                st.error("Incorrect PIN. Please try again.")
            else:
                # Learner login — upsert student in DB
                _login_nm = user_name.strip()
                upsert_student(_login_nm, APP_PIN, "learner")
                st.session_state["authenticated"] = True
                st.session_state["login_name"] = _login_nm
                st.session_state["user_type"] = "learner"
                # Load existing profile from DB if available
                _db_student = get_student(_login_nm)
                if _db_student and _db_student.get("profile_json"):
                    import json as _json
                    from cert_prep.models import LearnerProfile, RawStudentInput
                    st.session_state["profile"]          = LearnerProfile.model_validate_json(_db_student["profile_json"])
                    st.session_state["intake_submitted"] = True
                    st.session_state["is_demo_user"]     = False  # returning user
                    st.session_state["raw"]              = _raw_from_dict(_json.loads(_db_student["raw_input_json"]))
                    st.session_state["badge"] = _db_student.get("badge", "🧪 Mock mode")
                    if _db_student.get("plan_json"):
                        st.session_state["plan"] = _study_plan_from_dict(_json_mod.loads(_db_student["plan_json"]))
                    if _db_student.get("learning_path_json"):
                        st.session_state["learning_path"] = _learning_path_from_dict(_json_mod.loads(_db_student["learning_path_json"]))
                    if _db_student.get("progress_snapshot_json"):
                        st.session_state["progress_snapshot"] = _progress_snapshot_from_dict(_json_mod.loads(_db_student["progress_snapshot_json"]))
                    if _db_student.get("progress_assessment_json"):
                        st.session_state["progress_assessment"] = _readiness_assessment_from_dict(_json_mod.loads(_db_student["progress_assessment_json"]))
                    st.rerun()
                else:
                    st.session_state["is_demo_user"] = True  # no saved profile — show scenario picker
    st.stop()

# Auto-redirect admin users straight to the Admin Dashboard
if st.session_state.get("user_type") == "admin":
    st.switch_page("pages/1_Admin_Dashboard.py")

LEVEL_ICON = {
    "unknown":  "✗",
    "weak":     "⚠",
    "moderate": "◑",
    "strong":   "✓",
}

# ─── Domain name lookup — built from all supported exam registries ────────────
EXAM_DOMAIN_NAMES = {
    d["id"]: d["name"]
    for domains in EXAM_DOMAIN_REGISTRY.values()
    for d in domains
}

# ─── Azure / Microsoft certification catalogue (5 supported exams) ────────────
AZURE_CERTS = [
    "AI-102 – Azure AI Engineer Associate",
    "AI-900 – Azure AI Fundamentals",
    "AZ-204 – Azure Developer Associate",
    "DP-100 – Azure Data Scientist Associate",
    "AZ-305 – Azure Solutions Architect Expert",
]

DEFAULT_CERT = "AI-102 – Azure AI Engineer Associate"

# ─── Custom CSS (Microsoft Learn light theme) ──────────────────────────────
st.markdown(f"""
<style>
  /* ─ Microsoft Learn Light Theme ─ */
  [data-testid="stAppViewContainer"] {{
    background: {BG_DARK};
    font-family: 'Segoe UI', -apple-system, system-ui, sans-serif;
  }}
  [data-testid="stHeader"] {{
    background: #fff !important;
    border-bottom: 1px solid {BORDER};
  }}

  /* Hide Streamlit default page-nav labels */
  [data-testid="stSidebarNav"] {{ display: none; }}

  /* Hide deploy button & top toolbar */
  [data-testid="stDeployButton"],
  .stDeployButton {{ display: none !important; }}
  [data-testid="stToolbar"],
  [data-testid="stHeader"],
  header[data-testid="stHeader"] {{ display: none !important; }}
  .stApp > header {{ display: none !important; }}

  /* Push main content to top — remove default Streamlit padding */
  .stMainBlockContainer, [data-testid="stMainBlockContainer"] {{
    padding-top: 1rem !important;
  }}
  .block-container {{
    padding-top: 0.3rem !important;
  }}

  /* ── Blue sidebar (post-login) ── */
  [data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #0078D4 0%, #005A9E 100%) !important;
    border-right: none !important;
    width: 270px !important;
    min-width: 270px !important;
    max-width: 270px !important;
  }}
  [data-testid="stSidebar"] [data-testid="stSidebarContent"] {{
    background: transparent !important;
    padding-top: 0 !important;
  }}
  [data-testid="stSidebar"] [data-testid="stSidebarHeader"] {{
    display: none !important;
  }}
  [data-testid="stSidebar"] .stMarkdown p,
  [data-testid="stSidebar"] .stMarkdown li,
  [data-testid="stSidebar"] .stMarkdown span,
  [data-testid="stSidebar"] .stCaption {{
    color: rgba(255,255,255,0.85) !important;
  }}
  [data-testid="stSidebar"] .stMarkdown h1,
  [data-testid="stSidebar"] .stMarkdown h2,
  [data-testid="stSidebar"] .stMarkdown h3 {{
    color: #fff !important;
  }}
  [data-testid="stSidebar"] hr {{
    border-color: rgba(255,255,255,0.15) !important;
  }}
  [data-testid="stSidebar"] .stButton > button {{
    background: rgba(255,255,255,0.08) !important;
    border: none !important;
    color: rgba(255,255,255,0.9) !important;
    text-align: left !important;
    justify-content: flex-start !important;
    border-radius: 8px !important;
    padding: 10px 16px !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    transition: all 0.2s !important;
  }}
  [data-testid="stSidebar"] .stButton > button:hover {{
    background: rgba(255,255,255,0.18) !important;
    color: #fff !important;
  }}
  [data-testid="stSidebarCollapseButton"],
  [data-testid="collapsedControl"] {{ display: none !important; }}

  /* Toggle label — no wrap */
  [data-testid="stToggle"] label p,
  [data-testid="stToggle"] label span,
  [data-testid="stToggle"] p {{ white-space: nowrap !important; min-width: max-content; }}

  /* Sidebar scenario cards */
  .sb-sc-card {{
    background: rgba(255,255,255,0.13);
    border: 1px solid rgba(255,255,255,0.25);
    border-radius: 8px;
    padding: 0 10px;
    height: 42px;
    display: flex; flex-direction: row; align-items: center; gap: 8px;
    cursor: pointer;
    transition: background 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
    pointer-events: none;
    user-select: none;
    margin-bottom: 5px;
    box-sizing: border-box;
    overflow: hidden;
  }}
  .sb-sc-card.active {{
    background: rgba(255,255,255,0.22);
    border-color: rgba(255,255,255,0.55);
    box-shadow: 0 2px 8px rgba(0,0,0,0.18);
  }}
  .sb-sc-card .sbc-icon {{ font-size: 1.1rem; flex-shrink: 0; line-height: 1; }}
  .sb-sc-card .sbc-body {{ display: flex; flex-direction: row; align-items: center; gap: 6px; min-width: 0; flex: 1; overflow: hidden; }}
  .sb-sc-card .sbc-title {{ display: block; font-size: 0.78rem; font-weight: 600; color: rgba(255,255,255,0.92); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1; min-width: 0; }}
  .sb-sc-card.active .sbc-title {{ color: #fff; font-weight: 700; }}
  .sb-sc-card .sbc-badge {{
    display: inline-block; font-size: 0.6rem; font-weight: 700;
    color: rgba(255,255,255,0.75); background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.25);
    border-radius: 10px; padding: 1px 6px;
    white-space: nowrap; flex-shrink: 0; letter-spacing: 0.02em;
  }}
  .sb-sc-card.active .sbc-badge {{ color: #fff; background: rgba(255,255,255,0.2); border-color: rgba(255,255,255,0.4); }}
  .sb-sc-card.disabled {{
    opacity: 0.35;
    background: rgba(0,0,0,0.18);
    border-color: rgba(255,255,255,0.12);
    cursor: not-allowed;
    filter: grayscale(40%);
  }}
  .sb-sc-card.disabled .sbc-title {{ color: rgba(255,255,255,0.45); }}
  .sb-sc-card.disabled .sbc-badge {{ color: rgba(255,255,255,0.35); background: rgba(255,255,255,0.06); border-color: rgba(255,255,255,0.15); }}
  div.element-container:has(.sb-sc-card) {{
    margin-bottom: 0 !important; padding-bottom: 0 !important;
  }}
  div.element-container:has(.sb-sc-card) + div.element-container {{
    margin-top: -46px !important;
    position: relative !important; z-index: 5 !important;
    margin-bottom: 5px !important;
  }}
  div.element-container:has(.sb-sc-card) + div.element-container .stButton > button {{
    height: 42px !important;
    background: transparent !important; border: none !important;
    box-shadow: none !important; opacity: 0 !important;
    cursor: pointer !important; width: 100% !important;
  }}
  div.element-container:has(.sb-sc-card.disabled) + div.element-container .stButton > button {{
    cursor: not-allowed !important;
    pointer-events: none !important;
  }}
  div.element-container:has(.sb-sc-card:not(.active):not(.disabled)):has(+ div.element-container .stButton > button:hover) .sb-sc-card {{
    background: rgba(255,255,255,0.22);
    border-color: rgba(255,255,255,0.45);
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  }}

  /* Intake form card sections */
  .intake-card {{
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 8px 12px;
    margin-bottom: 6px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  }}
  .intake-card h3 {{
    margin: 0 0 4px 0;
    font-size: 0.8rem;
    font-weight: 700;
    color: {TEXT_PRIMARY};
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .intake-card h3 .card-icon {{
    font-size: 0.9rem;
  }}
  /* AI Preview panel */
  .ai-preview {{
    background: linear-gradient(135deg, #f0f4ff 0%, #e8f0fe 100%);
    border: 1px solid #c3d9f7;
    border-radius: 16px;
    padding: 24px 24px;
    position: sticky;
    top: 80px;
  }}
  .ai-preview h3 {{
    margin: 0 0 14px 0;
    font-size: 1.05rem;
    font-weight: 700;
    color: {TEXT_PRIMARY};
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .ai-preview .preview-row {{
    display: flex;
    align-items: flex-start;
    gap: 8px;
    margin-bottom: 8px;
    font-size: 0.82rem;
    color: {TEXT_PRIMARY};
    line-height: 1.5;
  }}
  .ai-preview .preview-row .dot {{
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: {BLUE};
    margin-top: 6px;
    flex-shrink: 0;
  }}
  .ai-preview .preview-label {{
    color: {TEXT_MUTED};
    font-size: 0.72rem;
    font-weight: 600;
    margin-top: 12px;
    margin-bottom: 6px;
  }}
  .ai-preview .preview-bullet {{
    display: flex;
    align-items: flex-start;
    gap: 8px;
    font-size: 0.78rem;
    color: {TEXT_PRIMARY};
    margin-bottom: 4px;
  }}
  .ai-preview .preview-bullet .bdot {{
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: {GREEN};
    margin-top: 5px;
    flex-shrink: 0;
  }}
  /* Hero header */
  .hero-header {{
    margin-bottom: 6px;
  }}
  .hero-header h1 {{
    margin: 0;
    font-size: 1.1rem;
    font-weight: 700;
    color: {TEXT_PRIMARY};
  }}
  .hero-header .hero-title {{
    margin: 1px 0 0;
    font-size: 0.88rem;
    font-weight: 400;
    color: {TEXT_PRIMARY};
    line-height: 1.3;
  }}
  .hero-header .hero-sub {{
    color: {TEXT_MUTED};
    font-size: 0.75rem;
    margin-top: 2px;
  }}
  /* CTA submit button */
  .stFormSubmitButton button {{
    background: linear-gradient(135deg, {BLUE} 0%, #005A9E 100%) !important;
    border: none !important;
    color: #fff !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-size: 0.88rem !important;
    padding: 7px 20px !important;
    letter-spacing: 0.01em;
    box-shadow: 0 4px 14px rgba(0,120,212,0.3) !important;
    transition: all 0.2s !important;
  }}
  .stFormSubmitButton button:hover {{
    background: linear-gradient(135deg, #106EBE 0%, #004578 100%) !important;
    box-shadow: 0 6px 20px rgba(0,120,212,0.4) !important;
    transform: translateY(-1px);
  }}
  /* Tighten widget gaps inside the intake form */
  .stForm .stElementContainer, .stForm [data-testid="stVerticalBlock"] > * {{
    gap: 0 !important;
  }}
  .stForm .stSelectbox, .stForm .stMultiSelect,
  .stForm .stSlider, .stForm .stCheckbox {{
    margin-bottom: 2px !important;
  }}
  div[data-testid="stForm"] .stCaption {{
    margin-top: 2px !important;
  }}
  /* Time commitment info box */
  .time-info {{
    background: #f0f7ff;
    border: 1px solid #c3d9f7;
    border-radius: 8px;
    padding: 5px 10px;
    display: flex;
    align-items: flex-start;
    gap: 6px;
    font-size: 0.75rem;
    color: {TEXT_PRIMARY};
    line-height: 1.4;
  }}
  .time-info .ti-icon {{
    font-size: 0.85rem;
    flex-shrink: 0;
    margin-top: 1px;
  }}
  /* Motivation pills */
  .motiv-pills {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }}
  .motiv-pill {{
    background: #f3f4f6;
    border: 1px solid #e5e7eb;
    border-radius: 20px;
    padding: 6px 14px;
    font-size: 0.78rem;
    color: {TEXT_PRIMARY};
    font-weight: 500;
    cursor: default;
  }}

  /* Azure Portal top navigation bar */
  .az-topbar {{
    background: {BLUE};
    display: flex;
    align-items: center;
    padding: 0 16px;
    height: 40px;
    margin: -1rem -1rem 0 -1rem;
    font-family: 'Segoe UI', sans-serif;
    color: #fff;
    box-shadow: 0 1px 3px rgba(0,0,0,0.15);
    position: relative;
    z-index: 999;
  }}
  .az-topbar-left {{
    display: flex;
    align-items: center;
    gap: 16px;
    white-space: nowrap;
  }}
  .az-waffle {{
    display: inline-grid;
    grid-template-columns: repeat(3, 3.5px);
    gap: 2.5px;
    padding: 8px;
    cursor: pointer;
  }}
  .az-waffle .wdot {{
    width: 3.5px; height: 3.5px;
    background: rgba(255,255,255,0.85);
    border-radius: 50%;
  }}
  .az-hamburger {{
    font-size: 18px;
    cursor: pointer;
    opacity: 0.9;
    line-height: 1;
    padding: 0 4px;
  }}
  .az-brand {{
    font-size: 15px;
    font-weight: 600;
    letter-spacing: -0.3px;
    color: #fff;
  }}
  .az-topbar-center {{
    flex: 1;
    max-width: 560px;
    margin: 0 24px;
  }}
  .az-search {{
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.25);
    border-radius: 4px;
    padding: 5px 14px;
    display: flex;
    align-items: center;
    gap: 8px;
    color: rgba(255,255,255,0.65);
    font-size: 13px;
  }}
  .az-topbar-right {{
    display: flex;
    align-items: center;
    gap: 4px;
    margin-left: auto;
  }}
  .az-copilot-pill {{
    background: #107C10;
    color: #fff;
    border-radius: 14px;
    padding: 3px 14px 3px 10px;
    font-size: 12px;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    margin-right: 6px;
    border: 1px solid rgba(255,255,255,0.2);
  }}
  .az-topbar-icon {{
    width: 32px; height: 32px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 2px;
    cursor: pointer;
    opacity: 0.8;
    color: #fff;
    transition: background 0.15s;
  }}
  .az-topbar-icon:hover {{
    background: rgba(255,255,255,0.1);
    opacity: 1;
  }}
  .az-topbar-icon svg {{
    width: 16px; height: 16px;
    fill: currentColor;
  }}
  .az-topbar-user {{
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    padding-left: 16px;
    margin-left: 4px;
    border-left: 1px solid rgba(255,255,255,0.2);
    cursor: default;
    max-width: 260px;
  }}
  .az-user-name {{
    font-size: 16px;
    font-weight: 600;
    color: #fff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 240px;
  }}
  .az-user-dir {{
    font-size: 10px;
    color: rgba(255,255,255,0.65);
    text-transform: uppercase;
    letter-spacing: 0.3px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 160px;
  }}

  /* Sub-header breadcrumb bar */
  .az-subheader {{
    background: #fff;
    border-bottom: 1px solid {BORDER};
    padding: 8px 24px;
    margin: 0 -1rem;
    font-size: 0.82rem;
    color: {TEXT_MUTED};
    font-family: 'Segoe UI', sans-serif;
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .az-subheader a {{ color: {BLUE}; text-decoration: none; }}
  .az-subheader a:hover {{ text-decoration: underline; }}
  .az-subheader .sep {{ color: #C8C6C4; }}

  /* Section cards – MS Learn white */
  .card {{
    background: {BG_CARD};
    border-radius: 4px;
    padding: 1.2rem 1.5rem;
    border: 1px solid {BORDER};
    margin-bottom: 1rem;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    color: {TEXT_PRIMARY};
  }}
  .card-purple {{ border-left: 4px solid {PURPLE}; }}
  .card-green  {{ border-left: 4px solid {GREEN}; }}
  .card-gold   {{ border-left: 4px solid {GOLD}; }}
  .card-pink   {{ border-left: 4px solid {ORANGE}; }}
  .card-blue   {{ border-left: 4px solid {BLUE}; }}

  /* MS Learn callout styles */
  .callout-note {{
    background: #EFF6FF; border-left: 4px solid #0078D4;
    border-radius: 4px; padding: 12px 16px; margin-bottom: 12px; color: #1B1B1B;
  }}
  .callout-tip {{
    background: #F0FFF4; border-left: 4px solid #107C10;
    border-radius: 4px; padding: 12px 16px; margin-bottom: 12px; color: #1B1B1B;
  }}
  .callout-warning {{
    background: #FFF8F0; border-left: 4px solid #CA5010;
    border-radius: 4px; padding: 12px 16px; margin-bottom: 12px; color: #1B1B1B;
  }}
  .callout-important {{
    background: #F5F0FF; border-left: 4px solid #5C2D91;
    border-radius: 4px; padding: 12px 16px; margin-bottom: 12px; color: #1B1B1B;
  }}

  /* Domain badge pills */
  .badge-unknown  {{ background:{LEVEL_COLOUR["unknown"]};  color:white; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }}
  .badge-weak     {{ background:{LEVEL_COLOUR["weak"]};     color:white; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }}
  .badge-moderate {{ background:{LEVEL_COLOUR["moderate"]}; color:white; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }}
  .badge-strong   {{ background:{LEVEL_COLOUR["strong"]};   color:white; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }}

  /* Ready / not-ready */
  .decision-ready     {{ background:{GREEN_LITE}; border:2px solid {GREEN}; border-radius:4px; padding:1rem 1.5rem; color:{TEXT_PRIMARY}; }}
  .decision-not-ready {{ background:{RED_LITE};   border:2px solid {RED};   border-radius:4px; padding:1rem 1.5rem; color:{TEXT_PRIMARY}; }}

  /* Progress bar */
  div[data-testid="stProgress"] > div {{ background-color: {BLUE}; }}

  /* Tab styling – MS Learn blue */
  .stTabs [data-baseweb="tab-highlight"] {{ background-color: {BLUE} !important; }}
  .stTabs [aria-selected="true"] {{ color: {BLUE} !important; font-weight: 600 !important; }}
  .stTabs [data-baseweb="tab"] {{ color: {TEXT_MUTED} !important; }}

  /* Global text */
  h1, h2, h3, h4, h5 {{ color: {TEXT_PRIMARY} !important; font-family: 'Segoe UI', -apple-system, sans-serif; }}
  .stMarkdown p, .stMarkdown li {{ color: #323130; }}
  .stCaption {{ color: {TEXT_MUTED} !important; }}

  /* Form elements */
  .stSelectbox div[data-baseweb="select"] > div {{
    background: #fff !important;
    border: 1px solid {BORDER} !important;
    color: {TEXT_PRIMARY} !important;
    border-radius: 4px !important;
  }}
  .stTextInput input, .stTextArea textarea {{
    background: #fff !important;
    border: 1px solid {BORDER} !important;
    color: {TEXT_PRIMARY} !important;
    border-radius: 4px !important;
  }}
  .stTextInput input:focus, .stTextArea textarea:focus {{
    border-color: {BLUE} !important;
    box-shadow: 0 0 0 1px {BLUE} !important;
  }}
  .stNumberInput input {{
    background: #fff !important;
    border: 1px solid {BORDER} !important;
    color: {TEXT_PRIMARY} !important;
  }}

  /* Radio/checkbox */
  div[data-testid="stRadio"] label *,
  div[data-testid="stRadio"] label span {{
    color: {TEXT_PRIMARY} !important;
  }}
  div[data-testid="stRadio"] label:has(input:checked) * {{
    color: {BLUE} !important;
  }}

  /* Expander */
  .stExpander details {{
    background: {BG_CARD} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 4px;
  }}
  .stExpander summary {{ color: {TEXT_PRIMARY} !important; }}

  /* Metric */
  div[data-testid="stMetricValue"] {{ color: {BLUE} !important; }}
  div[data-testid="stMetricLabel"] {{ color: {TEXT_MUTED} !important; }}

  /* Table */
  div[data-testid="stTable"] {{ background: {BG_CARD}; border-radius: 4px; border: 1px solid {BORDER}; }}

  /* Buttons (post-login, main content only) */
  .main .stButton > button {{
    background: {BLUE} !important;
    border: none !important;
    color: #fff !important;
    border-radius: 4px !important;
    font-weight: 600 !important;
    font-family: 'Segoe UI', sans-serif !important;
  }}
  .main .stButton > button:hover {{
    background: #106EBE !important;
  }}
</style>
""", unsafe_allow_html=True)


# ─── Post-login setup ────────────────────────────────────────────────────────
_login_name = st.session_state.get("login_name", "Learner")
_utype = st.session_state.get("user_type", "learner")
is_returning = "profile" in st.session_state

# ─── Auto-detect live mode from environment variables ───────────────────────
# Live mode activates automatically when both AZURE_OPENAI_ENDPOINT and
# AZURE_OPENAI_API_KEY are set with real (non-placeholder) values in .env.
# Override with FORCE_MOCK_MODE=true to stay in mock mode regardless.
def _is_real_value(v: str) -> bool:
    return bool(v) and "<" not in v and not v.startswith("your-")

_env_endpoint   = os.getenv("AZURE_OPENAI_ENDPOINT",   "").rstrip("/")
_env_api_key    = os.getenv("AZURE_OPENAI_API_KEY",     "")
_env_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT",  "gpt-4o")
_env_version    = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
_force_mock     = os.getenv("FORCE_MOCK_MODE", "false").lower() in ("1", "true", "yes")

_env_live = _is_real_value(_env_endpoint) and _is_real_value(_env_api_key) and not _force_mock

# ── Per-service configuration status (for the notification panel) ────────────
_svc_checks = [
    ("Azure OpenAI",        _is_real_value(_env_endpoint) and _is_real_value(_env_api_key),
     "AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY", True),   # required for live mode
    ("Azure AI Foundry",    _is_real_value(os.getenv("AZURE_AI_PROJECT_CONNECTION_STRING", "")),
     "AZURE_AI_PROJECT_CONNECTION_STRING", False),
    ("Azure Content Safety", _is_real_value(os.getenv("AZURE_CONTENT_SAFETY_ENDPOINT", "")),
     "AZURE_CONTENT_SAFETY_ENDPOINT", False),
    ("Azure AI Language",   _is_real_value(os.getenv("AZURE_LANGUAGE_ENDPOINT", "")),
     "AZURE_LANGUAGE_ENDPOINT + AZURE_LANGUAGE_KEY", False),
    ("Azure Comm Services", _is_real_value(os.getenv("AZURE_COMM_CONNECTION_STRING", "")),
     "AZURE_COMM_CONNECTION_STRING", False),
    ("MS Learn MCP",        _is_real_value(os.getenv("MCP_MSLEARN_URL", "")),
     "MCP_MSLEARN_URL", False),
]
_missing_svcs     = [(n, env) for n, ok, env, _ in _svc_checks if not ok]
_configured_svcs  = [(n, env) for n, ok, env, _ in _svc_checks if ok]

# ── Session-state toggle (user can override auto-detected mode) ───────────────
# _live_mode_pref is a non-widget key that persists across partial reruns.
# Streamlit clears widget keys for widgets that were not rendered in a run
# (e.g. when a sidebar button calls st.rerun() before the main-page toggle renders).
# We keep _live_mode_pref as the source of truth and restore live_mode_toggle from it.
if "_live_mode_pref" not in st.session_state:
    # First visit: default to Live if Azure credentials are configured
    st.session_state["_live_mode_pref"] = _env_live

# Restore widget key if Streamlit cleaned it up during a partial rerun
if "live_mode_toggle" not in st.session_state:
    st.session_state["live_mode_toggle"] = st.session_state["_live_mode_pref"]

# Respect FORCE_MOCK_MODE env var — never allow live if it's set
if _force_mock:
    st.session_state["live_mode_toggle"] = False
    st.session_state["_live_mode_pref"]  = False

use_live     = st.session_state["live_mode_toggle"]
az_endpoint  = _env_endpoint   if use_live and _env_live else ""
az_key       = _env_api_key    if use_live and _env_live else ""
az_deployment= _env_deployment if use_live else ""

# ─── Sidebar navigation (blue panel) ───────────────────────────────────────
with st.sidebar:
    # Brand / Logo area
    st.markdown("""
    <div style="text-align:center;padding:12px 0 12px;">
      <div style="font-size:1.8rem;line-height:1;">🎓</div>
      <div style="color:#fff;font-size:1.1rem;font-weight:700;letter-spacing:-0.02em;margin-top:6px;">Certification Preparation AI</div>
      <div style="color:rgba(255,255,255,0.6);font-size:0.7rem;margin-top:2px;">Agents League</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # User profile card
    _avatar_emoji = "🔧" if _utype == "admin" else "👤"
    st.markdown(f"""
    <div style="background:rgba(255,255,255,0.12);border-radius:10px;padding:14px 16px;margin-bottom:16px;">
      <div style="display:flex;align-items:center;gap:10px;">
        <div style="width:36px;height:36px;background:rgba(255,255,255,0.2);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.1rem;">{_avatar_emoji}</div>
        <div>
          <div style="color:#fff;font-size:0.88rem;font-weight:600;">{_login_name}</div>
          <div style="color:rgba(255,255,255,0.6);font-size:0.7rem;">{"Administrator" if _utype == "admin" else "Learner"}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Navigation section — DEMO SCENARIOS for new users only
    # is_demo_user is set at login time and never changes mid-session.
    # It stays True even after form submission so Reset Scenario always works.
    _is_returning_user = not st.session_state.get("is_demo_user", False)

    if not _is_returning_user:
        st.markdown(
            '<p style="color:rgba(255,255,255,0.5);font-size:0.6rem;font-weight:700;'
            'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:2px;padding-left:4px;">'
            'DEMO SCENARIOS</p>'
            '<p style="color:rgba(255,255,255,0.4);font-size:0.68rem;margin:0 0 6px;padding-left:4px;">'
            '✨ New here? Pick a scenario to get started.</p>',
            unsafe_allow_html=True,
        )
        _active_prefill = st.session_state.get("sidebar_prefill")
        _alex_active    = _active_prefill == "alex"
        _jordan_active  = _active_prefill == "alex_expert"

        # active → bright; other card selected → dim with disabled style
        _alex_cls   = ("sb-sc-card active"   if _alex_active
                       else ("sb-sc-card disabled" if _jordan_active
                             else "sb-sc-card"))
        _jordan_cls = ("sb-sc-card active"   if _jordan_active
                       else ("sb-sc-card disabled" if _alex_active
                             else "sb-sc-card"))

        st.markdown(f'''
        <div class="{_alex_cls}">
          <span class="sbc-icon">🌱</span>
          <div class="sbc-body">
            <span class="sbc-title">Novice</span>
            <span class="sbc-badge">AI-102</span>
          </div>
        </div>''', unsafe_allow_html=True)
        if st.button("\u200b", key="sb_sc_alex", use_container_width=True, disabled=_jordan_active):
            if not _alex_active:
                st.session_state["sidebar_prefill"] = "alex"
                st.rerun()

        st.markdown(f'''
        <div class="{_jordan_cls}">
          <span class="sbc-icon">🏆</span>
          <div class="sbc-body">
            <span class="sbc-title">Expert</span>
            <span class="sbc-badge">AI-102</span>
          </div>
        </div>''', unsafe_allow_html=True)
        if st.button("\u200b", key="sb_sc_jordan", use_container_width=True, disabled=_alex_active):
            if not _jordan_active:
                st.session_state["sidebar_prefill"] = "alex_expert"
                st.rerun()
        if _active_prefill:
            if st.button(
                "↩ Reset scenario",
                key="sb_reset_link",
                use_container_width=True,
                help="Clear the current demo scenario and pick a different one",
            ):
                # Keep only the login-level keys; wipe all profile/plan/form data
                _keep = {"authenticated", "login_name", "user_type", "live_mode_toggle"}
                for _k in list(st.session_state.keys()):
                    if _k not in _keep:
                        del st.session_state[_k]
                st.session_state["is_demo_user"] = True
                st.rerun()
    # Existing user — no demo scenario buttons, no message

    if _utype == "admin":
        st.markdown("---")
        st.markdown('<p style="color:rgba(255,255,255,0.5);font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;padding-left:4px;">ADMIN</p>', unsafe_allow_html=True)
        st.page_link("pages/1_Admin_Dashboard.py", label="🔐 Admin Dashboard", icon=None)

    st.markdown("---")
    st.markdown('<p style="color:rgba(255,255,255,0.5);font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px;padding-left:4px;">SETTINGS</p>', unsafe_allow_html=True)
    if st.button("🚪  Sign Out", key="sidebar_signout", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

    # ── Azure services mode badge ─────────────────────────────────────────
    st.markdown("---")
    if use_live:
        _foundry_live = _is_real_value(os.getenv("AZURE_AI_PROJECT_CONNECTION_STRING", ""))
        _badge_col  = "#22c55e"   # green
        _badge_icon = "☁️"
        _badge_text = "Azure AI Foundry SDK" if _foundry_live else "Live Azure Mode"
        _badge_sub  = "Foundry Agent Service + OpenAI" if _foundry_live else "OpenAI + guardrails active"
    else:
        _badge_col = "#94a3b8"   # grey
        _badge_icon = "🧪"
        _badge_text = "Mock Mode"
        _badge_sub  = "Rule-based agents · no Azure needed" if not _env_live else "Toggle Live Mode ↑ to use Azure"
    st.markdown(f"""
    <div style="background:rgba(255,255,255,0.08);border-radius:8px;padding:10px 12px;margin-top:4px;">
      <div style="display:flex;align-items:center;gap:6px;">
        <span style="font-size:1rem;">{_badge_icon}</span>
        <div>
          <div style="color:#fff;font-size:0.75rem;font-weight:600;">{_badge_text}</div>
          <div style="color:{_badge_col};font-size:0.62rem;">{_badge_sub}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ─── Pre-fill values per scenario ────────────────────────────────────────────
_PREFILL_SCENARIOS = {
    "Blank — start from scratch": {},
    "Alex Chen — complete beginner, AI-102": {
        "exam": "AI-102 – Azure AI Engineer Associate",
        "name": "Alex Chen", "email": "alex.chen@demo.com",
        "background": "Recent computer science graduate, basic Python skills, no cloud or Azure experience at all.",
        "certs": "", "style": "Hands-on labs and step-by-step tutorials",
        "hpw": 12.0, "weeks": 10, "concerns": "Azure Cognitive Services, Azure OpenAI, Bot Service",
        "goal": "Break into AI engineering as a first job after graduation",
        "role": "Student / Fresh Graduate",
        "motivation": ["Career growth"],
        "style_tags": ["Hands-on labs", "Practice tests"],
    },
    "Alex Chen — expert, AI-102": {
      "exam": "AI-102 – Azure AI Engineer Associate",
      "name": "Alex Chen", "email": "alex.chen@demo.com",
      "background": "5 years as an Azure cloud developer. Built production NLP pipelines and Computer Vision solutions using Azure Cognitive Services. Strong on plan/manage and classic AI services; needs to close gaps on Generative AI and Document Intelligence before the exam.",
      "certs": "AZ-204, AZ-900", "style": "Reference docs and hands-on labs",
      "hpw": 8.0, "weeks": 6, "concerns": "Azure OpenAI, prompt engineering, Document Intelligence, Azure AI Search",
      "goal": "Pass AI-102 to formalise 5 years of applied Azure AI work into an official certification",
      "role": "Data Analyst / Scientist",
      "motivation": ["Career growth", "Role switch"],
      "style_tags": ["Reference docs", "Hands-on labs"],
    },
}
prefill = {}

# ─── Live / Mock mode toggle (main page) ─────────────────────────────────────
_tgl_c1, _tgl_c2, _tgl_c3 = st.columns([2.2, 4.0, 5.8])
with _tgl_c1:
    _tog_val = st.toggle(
        "Live Mode",
        key="live_mode_toggle",
        help="Switch between Live Azure (real OpenAI) and Mock mode (no credentials needed)",
    )
    # Sync user's choice back to the persistent key so it survives the next partial rerun
    st.session_state["_live_mode_pref"] = _tog_val
with _tgl_c2:
    if use_live:
        _foundry_pill = _is_real_value(os.getenv("AZURE_AI_PROJECT_CONNECTION_STRING", ""))
        _pill_label   = "Azure AI Foundry SDK" if _foundry_pill else "Live Azure Mode"
        _pill_sub     = "Foundry Agent Service" if _foundry_pill else "Real OpenAI calls"
        st.markdown(
            f'''<div style="display:inline-flex;align-items:center;gap:8px;
                  background:linear-gradient(135deg,#e8f5e9 0%,#f0fff4 100%);
                  border:1px solid #a5d6a7;border-radius:20px;
                  padding:5px 14px;margin-top:6px;line-height:1.4;">
              <span style="width:8px;height:8px;border-radius:50%;flex-shrink:0;
                    background:{GREEN};display:inline-block;vertical-align:middle;
                    box-shadow:0 0 0 2px #a5d6a7;"></span>
              <span style="font-size:0.8rem;font-weight:700;color:{GREEN};letter-spacing:0.01em;line-height:1;">{_pill_label}</span>
              <span style="font-size:0.72rem;color:{TEXT_MUTED};line-height:1;">{_pill_sub}</span>
            </div>''',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'''<div style="display:inline-flex;align-items:center;gap:8px;
                  background:linear-gradient(135deg,#FFF8E1 0%,#FFFDE7 100%);
                  border:1px solid #FFD54F;border-radius:20px;
                  padding:5px 14px;margin-top:6px;line-height:1.4;">
              <span style="width:8px;height:8px;border-radius:50%;flex-shrink:0;
                    background:#FB8C00;display:inline-block;vertical-align:middle;
                    box-shadow:0 0 0 2px #FFD54F;"></span>
              <span style="font-size:0.8rem;font-weight:700;color:#E65100;letter-spacing:0.01em;line-height:1;">Mock Mode</span>
              <span style="font-size:0.72rem;color:#BF360C;line-height:1;">No credentials needed</span>
            </div>''',
            unsafe_allow_html=True,
        )

# ── Azure Services Status panel ───────────────────────────────────────────────
if use_live:
    _has_required_missing = any(n == "Azure OpenAI" for n, _ in _missing_svcs)
    _all_ok               = len(_missing_svcs) == 0

    if _has_required_missing:
        _panel_border = "#D32F2F"; _panel_bg = "#FFF5F5"; _header_col = "#D32F2F"
        _header_badge_bg = "#FFEBEE"
        _status_icon = "⚠️"
        _status_text = "Required credentials missing — Live mode unavailable"
        _status_sub  = "Set AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY in .env and restart."
    elif _all_ok:
        _panel_border = "#2E7D32"; _panel_bg = "#F1F8E9"; _header_col = "#2E7D32"
        _header_badge_bg = "#E8F5E9"
        _status_icon = "✅"
        _status_text = "All services configured — Full live mode active"
        _status_sub  = "Every Azure service is connected and ready."
    else:
        _panel_border = "#F57C00"; _panel_bg = "#FFFDE7"; _header_col = "#E65100"
        _header_badge_bg = "#FFF8E1"
        _status_icon = "🟡"
        _status_text = "Live mode active — some optional services not configured"
        _status_sub  = "Missing optional services degrade gracefully."

    _checklist = [
        ("Azure OpenAI",         _is_real_value(_env_endpoint) and _is_real_value(_env_api_key),
         True,  "LLM backbone — all agents",
         "AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY"),
        ("Azure AI Foundry",     _is_real_value(os.getenv("AZURE_AI_PROJECT_CONNECTION_STRING", "")),
         False, "Managed agent + thread (Tier 1)",
         "AZURE_AI_PROJECT_CONNECTION_STRING"),
        ("Azure Content Safety", _is_real_value(os.getenv("AZURE_CONTENT_SAFETY_ENDPOINT", "")),
         False, "G-16 harmful content BLOCK (Hate/Violence/SelfHarm/Sexual)",
         "AZURE_CONTENT_SAFETY_ENDPOINT + AZURE_CONTENT_SAFETY_KEY"),
        ("Azure AI Language",    _is_real_value(os.getenv("AZURE_LANGUAGE_ENDPOINT", "")),
         False, "G-16 PII entity recognition (SSN / CC / passport — live ML scan)",
         "AZURE_LANGUAGE_ENDPOINT + AZURE_LANGUAGE_KEY"),
        ("SMTP Email",
         _is_real_value(os.getenv("SMTP_USER", "")) and _is_real_value(os.getenv("SMTP_PASS", "")),
         False, "PDF reports via smtplib — any SMTP provider",
         "SMTP_USER + SMTP_PASS (+ SMTP_HOST, SMTP_PORT, SMTP_FROM)"),
        ("MS Learn MCP",         _is_real_value(os.getenv("MCP_MSLEARN_URL", "")),
         False, "Live module catalogue",
         "MCP_MSLEARN_URL"),
    ]

    # ── Build entire table as one flat string (no nested f-string interpolation) ──
    _tbl = (
        "<div style='border:1px solid " + _panel_border + "33;"
        "border-radius:10px;overflow:hidden;margin:8px 0 16px;"
        "font-family:Segoe UI,Arial,sans-serif;"
        "box-shadow:0 2px 8px rgba(0,0,0,0.07);'>"

        # ── Banner header
        "<div style='background:" + _panel_bg + ";"
        "border-bottom:2px solid " + _panel_border + "55;"
        "padding:11px 16px;display:flex;align-items:center;justify-content:space-between;'>"
        "<div style='display:flex;align-items:center;gap:8px;'>"
        "<span style='font-size:1rem;'>" + _status_icon + "</span>"
        "<div>"
        "<span style='font-size:0.83rem;font-weight:700;color:" + _header_col + ";'>" + _status_text + "</span>"
        "<br><span style='font-size:0.71rem;color:#607D8B;'>" + _status_sub + "</span>"
        "</div></div>"
        "<span style='font-size:0.6rem;font-weight:700;letter-spacing:0.07em;"
        "text-transform:uppercase;color:" + _panel_border + ";"
        "background:" + _header_badge_bg + ";"
        "border:1px solid " + _panel_border + "55;"
        "border-radius:20px;padding:4px 12px;white-space:nowrap;line-height:1;display:inline-flex;align-items:center;'>☁️ Azure Services</span>"
        "</div>"

        # ── Table column headers
        "<table style='width:100%;border-collapse:collapse;'>"
        "<thead><tr style='background:rgba(0,0,0,0.035);'>"
        "<th style='padding:6px 14px;font-size:0.66rem;font-weight:600;color:#90A4AE;"
        "text-transform:uppercase;letter-spacing:0.05em;text-align:center;width:36px;'></th>"
        "<th style='padding:6px 14px;font-size:0.66rem;font-weight:600;color:#90A4AE;"
        "text-transform:uppercase;letter-spacing:0.05em;text-align:left;'>Service</th>"
        "<th style='padding:6px 14px;font-size:0.66rem;font-weight:600;color:#90A4AE;"
        "text-transform:uppercase;letter-spacing:0.05em;text-align:left;'>Description</th>"
        "<th style='padding:6px 14px;font-size:0.66rem;font-weight:600;color:#90A4AE;"
        "text-transform:uppercase;letter-spacing:0.05em;text-align:left;'>Env Variables</th>"
        "<th style='padding:6px 14px;font-size:0.66rem;font-weight:600;color:#90A4AE;"
        "text-transform:uppercase;letter-spacing:0.05em;text-align:center;'>Status</th>"
        "</tr></thead><tbody>"
    )

    for _i, (_svc_name, _svc_ok, _svc_req, _svc_desc, _svc_env) in enumerate(_checklist):
        _row_bg = "rgba(46,125,50,0.03)" if _svc_ok else ("rgba(211,47,47,0.03)" if _svc_req else "transparent")
        _row_sep = "border-top:1px solid rgba(0,0,0,0.06);" if _i > 0 else ""

        if _svc_ok:
            _dot   = "<span style='display:inline-block;width:10px;height:10px;border-radius:50%;background:#43A047;box-shadow:0 0 4px #43A04766;'></span>"
            _nc    = "#2E7D32"
            _ev    = "<span style='color:#B0BEC5;font-size:0.72rem;'>—</span>"
            _badge = ("<span style='font-size:0.65rem;font-weight:600;color:#2E7D32;"
                      "background:#E8F5E9;border:1px solid #A5D6A7;"
                      "border-radius:20px;padding:4px 12px;line-height:1;"
                      "display:inline-flex;align-items:center;white-space:nowrap;'>● connected</span>")
        else:
            _dot   = "<span style='display:inline-block;width:10px;height:10px;border-radius:50%;background:#BDBDBD;'></span>"
            _nc    = "#C62828" if _svc_req else "#5D4037"
            _ev    = ("<code style='font-size:0.67rem;font-family:Consolas,monospace;"
                      "background:rgba(0,0,0,0.06);border-radius:4px;padding:1px 5px;"
                      "color:#546E7A;'>" + _svc_env + "</code>")
            if _svc_req:
                _badge = ("<span style='font-size:0.65rem;font-weight:600;color:#C62828;"
                          "background:#FFEBEE;border:1px solid #EF9A9A;"
                          "border-radius:20px;padding:4px 12px;line-height:1;"
                          "display:inline-flex;align-items:center;white-space:nowrap;'>✕ required</span>")
            else:
                _badge = ("<span style='font-size:0.65rem;font-weight:600;color:#9E9E9E;"
                          "background:#F5F5F5;border:1px solid #BDBDBD;"
                          "border-radius:20px;padding:4px 12px;line-height:1;"
                          "display:inline-flex;align-items:center;white-space:nowrap;'>○ optional</span>")

        _tbl += (
            "<tr style='background:" + _row_bg + ";" + _row_sep + "'>"
            "<td style='padding:9px 14px;text-align:center;'>" + _dot + "</td>"
            "<td style='padding:9px 14px;'>"
            "<span style='font-size:0.8rem;font-weight:600;color:" + _nc + ";'>" + _svc_name + "</span>"
            "</td>"
            "<td style='padding:9px 14px;font-size:0.76rem;color:#607D8B;'>" + _svc_desc + "</td>"
            "<td style='padding:9px 14px;'>" + _ev + "</td>"
            "<td style='padding:9px 16px;text-align:center;'>" + _badge + "</td>"
            "</tr>"
        )

    _tbl += "</tbody></table></div>"
    st.markdown(_tbl, unsafe_allow_html=True)

# ─── Gate: Live mode ON but required credentials missing ─────────────────────
# Hide all content sections (intake form, domain map, study plan, etc.) until
# the user either adds credentials or switches back to Mock mode.
if use_live and not _env_live:
    st.markdown(
        """
        <div style="
          display:flex; flex-direction:column; align-items:center; justify-content:center;
          padding:48px 24px; text-align:center; margin:24px 0;
          background:linear-gradient(135deg,#FFF5F5 0%,#FFF0F0 100%);
          border:1.5px solid #FFCDD2; border-radius:14px;
          box-shadow:0 4px 16px rgba(211,47,47,0.08);
        ">
          <div style="font-size:2.4rem;margin-bottom:12px;line-height:1;">🔐</div>
          <div style="font-size:1.15rem;font-weight:700;color:#C62828;margin-bottom:8px;">
            Azure credentials required for Live Mode
          </div>
          <div style="font-size:0.85rem;color:#B71C1C;max-width:480px;margin-bottom:20px;line-height:1.6;">
            <strong>AZURE_OPENAI_ENDPOINT</strong> and <strong>AZURE_OPENAI_API_KEY</strong>
            must be set in your <code>.env</code> file before Live Mode can run.<br>
            All content sections are hidden until the services are reachable.
          </div>
          <div style="display:flex;gap:10px;flex-wrap:wrap;justify-content:center;">
            <div style="background:#FFEBEE;border:1px solid #FFCDD2;border-radius:8px;
                        padding:8px 16px;font-size:0.78rem;color:#C62828;font-weight:600;">
              1 &nbsp;·&nbsp; Add credentials to <code>.env</code>
            </div>
            <div style="background:#FFEBEE;border:1px solid #FFCDD2;border-radius:8px;
                        padding:8px 16px;font-size:0.78rem;color:#C62828;font-weight:600;">
              2 &nbsp;·&nbsp; Restart the Streamlit server
            </div>
            <div style="background:#FFEBEE;border:1px solid #FFCDD2;border-radius:8px;
                        padding:8px 16px;font-size:0.78rem;color:#C62828;font-weight:600;">
              3 &nbsp;·&nbsp; Or toggle back to <strong>Mock Mode</strong> ↑
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# ─── Dashboard welcome / Hero header ──────────────────────────────────────────
if is_returning:
    _rp_name = st.session_state["profile"].student_name
    _welcome_msg = f"Welcome back, {_rp_name}"
else:
    _welcome_msg = f"Welcome, {_login_name}"

if is_returning:
    st.markdown(f"""
    <div style="margin-bottom:4px;">
      <h1 style="margin:0;font-size:1.1rem;font-weight:700;color:{TEXT_PRIMARY} !important;">{_welcome_msg} 👋</h1>
      <p style="color:{TEXT_MUTED};font-size:0.78rem;margin:1px 0 0;">Your AI-powered certification preparation dashboard</p>
    </div>
    """, unsafe_allow_html=True)
# new-user header is rendered inline below with the Reset button

# ─── Scenario picker (driven from sidebar) ──────────────────────────────────
if not is_returning:
    _sb_choice = st.session_state.get("sidebar_prefill", "")
    if _sb_choice == "alex":
      prefill.update(_PREFILL_SCENARIOS["Alex Chen — complete beginner, AI-102"])
    elif _sb_choice == "alex_expert":
      prefill.update(_PREFILL_SCENARIOS["Alex Chen — expert, AI-102"])

    # Push prefill values into session state so Streamlit widgets pick them up
    if prefill:
        _motivations_list = ["Career growth", "Client requirement", "Role switch", "Just learning"]
        _prefill_motivations = prefill.get("motivation", [])
        for i, m in enumerate(_motivations_list):
            st.session_state[f"motiv_{i}"] = m in _prefill_motivations

        _style_labels = ["Hands-on labs", "Video tutorials", "Reading docs", "Real projects", "Practice tests"]
        _prefill_style_tags = prefill.get("style_tags", [])
        for i, s in enumerate(_style_labels):
            st.session_state[f"style_{i}"] = s in _prefill_style_tags

# ─── Intake form (compact two-column, no scroll) ────────────────────────────

# ── Existing user: frozen read-only view (toggle to edit) ────────────────────
if is_returning and not st.session_state.get("editing_profile", False):
    _raw_r: RawStudentInput = st.session_state["raw"]

    _fv_hdr_l, _fv_hdr_r = st.columns([8, 2])
    with _fv_hdr_l:
        st.markdown(
            f'<h3 style="margin:0 0 12px;font-size:1.05rem;font-weight:700;'
            f'color:{TEXT_PRIMARY};">📋 Your Profile on File</h3>',
            unsafe_allow_html=True,
        )
    with _fv_hdr_r:
        if st.button("✏️ Edit Profile", key="edit_profile_btn", use_container_width=True):
            st.session_state["editing_profile"] = True
            st.rerun()

    _email_disp   = getattr(_raw_r, "email", "") or st.session_state.get("user_email", "")
    _email_row    = f'<div class="pfc-label">📧 Email</div><div class="pfc-val">{_email_disp if _email_disp else "—"}</div>'
    _certs_disp   = ", ".join(_raw_r.existing_certs) if _raw_r.existing_certs else "None yet"
    _concern_disp = ", ".join(_raw_r.concern_topics) if _raw_r.concern_topics else "None specified"
    _bg_short     = (_raw_r.background_text[:300] + "\u2026") if len(_raw_r.background_text) > 300 else _raw_r.background_text
    _style_disp   = _raw_r.preferred_style if _raw_r.preferred_style else "Not specified"
    st.markdown(f"""
    <style>
      .pfc-row {{ display:flex; gap:12px; margin-bottom:6px; }}
      .pfc-card {{ flex:1; background:#fff; border:1px solid #e5e7eb; border-radius:10px;
                  padding:12px 14px; box-shadow:0 1px 3px rgba(0,0,0,0.04);
                  display:flex; flex-direction:column; }}
      .pfc-label {{ color:{TEXT_MUTED}; font-size:0.67rem; font-weight:700;
                   text-transform:uppercase; letter-spacing:.06em; margin-bottom:4px; margin-top:10px; }}
      .pfc-label:first-child {{ margin-top:0; }}
      .pfc-val   {{ font-size:0.87rem; font-weight:600; color:{TEXT_PRIMARY}; margin-bottom:2px; line-height:1.45; }}
      .pfc-val-lg{{ font-size:0.95rem; font-weight:700; color:{TEXT_PRIMARY}; margin-bottom:2px; }}
    </style>
    <div class="pfc-row">
      <div class="pfc-card">
        <div class="pfc-label">🎯 Exam Target</div>
        <div class="pfc-val-lg">{_raw_r.exam_target}</div>
        <div class="pfc-label">🕐 Study Budget</div>
        <div class="pfc-val">{_raw_r.hours_per_week} hr/wk · {_raw_r.weeks_available} weeks</div>
        {_email_row}
      </div>
      <div class="pfc-card">
        <div class="pfc-label">🏅 Existing Certs</div>
        <div class="pfc-val">{_certs_disp}</div>
        <div class="pfc-label">🔍 Focus Areas</div>
        <div class="pfc-val">{_concern_disp}</div>
      </div>
      <div class="pfc-card">
        <div class="pfc-label">👤 Background</div>
        <div class="pfc-val">{_bg_short}</div>
        <div class="pfc-label">📖 Learning Style</div>
        <div class="pfc-val">{_style_disp}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    submitted = False  # no form submission in read-only mode

else:
    # ── Editable form (new user, or returning user clicked Edit) ─────────────
    if is_returning:
        # Pre-populate form fields from the saved raw input
        _raw_r = st.session_state["raw"]
        prefill = {
            "name":       _raw_r.student_name,
            "email":      getattr(_raw_r, "email", st.session_state.get("user_email", "")),
            "exam":       next((c for c in AZURE_CERTS if c.startswith(_raw_r.exam_target)), DEFAULT_CERT),
            "background": _raw_r.background_text,
            "certs":      ", ".join(_raw_r.existing_certs),
            "hpw":        _raw_r.hours_per_week,
            "weeks":      _raw_r.weeks_available,
            "concerns":   ", ".join(_raw_r.concern_topics),
            "goal":       _raw_r.goal_text,
            "style":      _raw_r.preferred_style,
            "motivation": [m.strip() for m in _raw_r.goal_text.split(",") if m.strip()],
            "style_tags": [s.strip() for s in _raw_r.preferred_style.split(",") if s.strip()],
            "role":       "",
        }
        _motivations_list = ["Career growth", "Client requirement", "Role switch", "Just learning"]
        for i, m in enumerate(_motivations_list):
            st.session_state[f"motiv_{i}"] = m in prefill["motivation"]
        _style_labels = ["Hands-on labs", "Video tutorials", "Reading docs", "Real projects", "Practice tests"]
        for i, s in enumerate(_style_labels):
            st.session_state[f"style_{i}"] = s in prefill["style_tags"]

        _hdr_l, _hdr_r = st.columns([8, 1])
        with _hdr_l:
            st.markdown(f'<p style="margin:0 0 4px;font-size:0.72rem;color:{TEXT_MUTED};">Update your details — your study plan will be regenerated on save.</p>', unsafe_allow_html=True)
        with _hdr_r:
            if st.button("✕ Cancel", key="cancel_edit_btn", use_container_width=True):
                st.session_state.pop("editing_profile", None)
                st.rerun()
    else:
        # Inline header + Reset button for new users
        _hdr_l, _hdr_r = st.columns([8, 1])
        with _hdr_l:
            st.markdown(f"""
            <div style="padding:2px 0 4px;">
              <span style="font-size:1.05rem;font-weight:700;color:{TEXT_PRIMARY};">{_welcome_msg} 👋</span>
              <span style="color:{TEXT_MUTED};font-size:0.78rem;margin-left:10px;">Build your personalized AI certification plan — your AI coach does the rest</span>
            </div>
            """, unsafe_allow_html=True)
        with _hdr_r:
            if st.button("🔄 Reset", key="clear_form", use_container_width=True):
                # Clear keyed checkbox state
                for k in list(st.session_state.keys()):
                    if k.startswith(("motiv_", "style_")):
                        del st.session_state[k]
                # Clear prefill + PII counter
                st.session_state.pop("sidebar_prefill", None)
                st.session_state.pop("_pii_seen_count", None)
                # Bump form version → forces all keyless widgets to re-render blank
                st.session_state["_form_version"] = st.session_state.get("_form_version", 0) + 1
                st.rerun()

    _form_version = st.session_state.get("_form_version", 0)
    with st.form(f"intake_form_{_form_version}", clear_on_submit=False):

        _left, _right = st.columns(2, gap="small")

        # ════════════ LEFT COLUMN ════════════
        with _left:
            # ── Your Goal ──
            st.markdown('<div class="intake-card"><h3><span class="card-icon">🎯</span> Your Goal</h3>', unsafe_allow_html=True)
            exam_cert = st.selectbox(
                "Which certification exam are you targeting?",
                options=AZURE_CERTS,
                index=AZURE_CERTS.index(prefill.get("exam", DEFAULT_CERT))
                      if prefill.get("exam") in AZURE_CERTS else AZURE_CERTS.index(DEFAULT_CERT),
            )
            exam_target = exam_cert.split(" – ")[0].strip()

            _motiv_cols = st.columns(2)
            _motivations = [("🚀", "Career growth"), ("🤝", "Client need"), ("🔄", "Role switch"), ("💡", "Learning")]
            _selected_motiv = []
            for i, (icon, m) in enumerate(_motivations):
                with _motiv_cols[i % 2]:
                    if st.checkbox(f"{icon} {m}", key=f"motiv_{i}"):
                        _selected_motiv.append(m)
            st.markdown('</div>', unsafe_allow_html=True)

            # ── Time Commitment ──
            st.markdown('<div class="intake-card"><h3><span class="card-icon">⏱️</span> Time Commitment</h3>', unsafe_allow_html=True)
            _tc1, _tc2 = st.columns(2)
            with _tc1:
                hours_per_week = st.slider("Hours / week", min_value=1, max_value=40, value=int(prefill.get("hpw", 10)))
            with _tc2:
                weeks_available = st.slider("Weeks available", min_value=1, max_value=52, value=int(prefill.get("weeks", 8)))
            total_hours = hours_per_week * weeks_available
            st.markdown(f'<div class="time-info"><span class="ti-icon">📅</span><span>Study plan: <b>{weeks_available} weeks</b> × <b>{hours_per_week} hr/wk</b> = <b>{total_hours} hours</b></span></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # ── How do you learn best? ──
            st.markdown('<div class="intake-card"><h3><span class="card-icon">📖</span> How do you learn best?</h3>', unsafe_allow_html=True)
            _style_cols_r1 = st.columns(3)
            _style_cols_r2 = st.columns(3)
            _style_options = [("🔬", "Hands-on labs"), ("📹", "Videos"), ("📄", "Reading"), ("🏗️", "Projects"), ("📝", "Practice tests")]
            _selected_styles = []
            for i, (icon, label) in enumerate(_style_options):
                _col = _style_cols_r1[i] if i < 3 else _style_cols_r2[i - 3]
                with _col:
                    if st.checkbox(f"{icon} {label}", key=f"style_{i}"):
                        _selected_styles.append(label)
            preferred_style = ", ".join(_selected_styles) if _selected_styles else ""
            st.markdown('</div>', unsafe_allow_html=True)

        # ════════════ RIGHT COLUMN ════════════
        with _right:
            # ── Your Background ──
            st.markdown('<div class="intake-card"><h3><span class="card-icon">👤</span> Your Background</h3>', unsafe_allow_html=True)
            background_text = st.text_area(
                "Tell us about your experience",
                value=prefill.get("background", ""),
                placeholder="e.g. 3 years Python developer, familiar with REST APIs, no Azure experience",
                height=68,
                label_visibility="collapsed",
            )
            st.markdown('</div>', unsafe_allow_html=True)

            # ── About You ──
            st.markdown('<div class="intake-card"><h3><span class="card-icon">🧑‍💼</span> About You</h3>', unsafe_allow_html=True)
            _role_options = [
                "Student / Fresh Graduate", "Software Developer", "Cloud Engineer",
                "Data Analyst / Scientist", "IT Administrator", "Solutions Architect",
                "Manager / Team Lead", "Other",
            ]
            _role_default = 0
            _prefill_role = prefill.get("role", "")
            if _prefill_role in _role_options:
                _role_default = _role_options.index(_prefill_role)
            current_role = st.selectbox("What's your current role?", options=_role_options, index=_role_default)

            email_input = st.text_input(
                "📧 Email address (optional — for weekly digest)",
                value=prefill.get("email", st.session_state.get("user_email", "")),
                placeholder="e.g. you@example.com",
            )

            _common_certs = ["None yet", "AZ-900", "AZ-104", "AZ-204", "AZ-305", "AI-900", "AI-102", "DP-900", "DP-100", "SC-900"]
            _prefill_certs = [c.strip() for c in prefill.get("certs", "").split(",") if c.strip()]
            _cert_defaults = _prefill_certs if _prefill_certs else ["None yet"]
            _cert_defaults = [c for c in _cert_defaults if c in _common_certs]
            existing_certs_list = st.multiselect("Certifications you already have", options=_common_certs, default=_cert_defaults)
            existing_certs_raw = ", ".join([c for c in existing_certs_list if c != "None yet"])
            st.markdown('</div>', unsafe_allow_html=True)

            # ── Areas of concern ──
            st.markdown('<div class="intake-card"><h3><span class="card-icon">🔍</span> Any specific topics you find challenging?</h3>', unsafe_allow_html=True)
            _concern_options = ["Azure OpenAI", "Bot Framework", "Cognitive Services", "Computer Vision", "NLP / Language", "Search (AI Search)", "Document Intelligence", "Responsible AI"]
            _prefill_concerns = [c.strip() for c in prefill.get("concerns", "").split(",") if c.strip()]
            _concern_defaults = [c for c in _prefill_concerns if c in _concern_options]
            concern_topics_list = st.multiselect("Select topics you want to focus on", options=_concern_options, default=_concern_defaults, label_visibility="collapsed")
            concern_topics_raw_ui = ", ".join(concern_topics_list)
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Derived fields (auto-computed) ──
        student_name = prefill.get("name", _login_name)
        concern_topics_raw = concern_topics_raw_ui if concern_topics_list else prefill.get("concerns", "")
        goal_text = ", ".join(_selected_motiv) if _selected_motiv else prefill.get("goal", "")
        # email_input is bound inside the form; provide a fallback for read-only mode
        if "email_input" not in dir():
            email_input = prefill.get("email", st.session_state.get("user_email", ""))

        _has_demo_prefill = bool(st.session_state.get("sidebar_prefill", ""))
        _has_bg_text = bool(background_text.strip())

        _submit_label = "💾 Save & Regenerate Plan" if is_returning else "🎯 Create My AI Study Plan"
        submitted = st.form_submit_button(
            _submit_label,
            type="primary",
            use_container_width=True,
        )
        st.caption("You can adjust your preferences anytime.")


# ─── Handle submit ────────────────────────────────────────────────────────────
if submitted:
    # ── Required-field validation (runs after submit so Streamlit can read form values)
    _val_errors = []
    if not student_name.strip():
        _val_errors.append("**Name** — please enter your name (or use a demo scenario from the sidebar).")
    if not background_text.strip() and not _has_demo_prefill:
        _val_errors.append("**Your AI & Cloud Background** — please describe your experience so the agents can build a personalised plan.")
    if _val_errors:
        st.error(
            "Please fix the following before generating your plan:\n\n"
            + "\n".join(f"• {e}" for e in _val_errors)
        )
        st.stop()

    raw = RawStudentInput(
        student_name    = student_name.strip(),
        exam_target     = exam_target.strip(),
        background_text = background_text.strip(),
        existing_certs  = [c.strip() for c in existing_certs_raw.split(",") if c.strip()],
        hours_per_week  = hours_per_week,
        weeks_available = weeks_available,
        concern_topics  = [t.strip() for t in concern_topics_raw.split(",") if t.strip()],
        preferred_style = preferred_style.strip(),
        goal_text       = goal_text.strip(),
        email           = email_input.strip() if email_input else "",
    )
    st.session_state["user_email"] = raw.email

    # ── Guardrail: validate raw input ────────────────────────────────────────
    # G-16 PII + harmful content:
    #   Mock mode  → regex patterns + keyword-context scan (no credentials needed)
    #   Live mode  → Azure Content Safety API; regex + keyword scan always supplement
    _guardrails = GuardrailsPipeline()
    _input_result = _guardrails.check_input(raw, use_live=use_live)
    if _input_result.blocked:
        for v in _input_result.violations:
            if v.level == GuardrailLevel.BLOCK:
                st.error(f"🚫 **Guardrail [{v.code}]** — {v.message}")
        st.stop()

    # Surface WARNs — PII detections get a dedicated callout box
    _warn_violations = [v for v in _input_result.violations if v.level.value == "WARN"]
    _pii_warns   = [v for v in _warn_violations if v.code == "G-16"]
    _other_warns = [v for v in _warn_violations if v.code != "G-16"]

    # PII gate: first submit → show warning + stop; second submit → proceed with note
    _pii_seen_count = st.session_state.get("_pii_seen_count", 0)
    if _pii_warns:
        if _pii_seen_count == 0:
            # ── First submission with PII: block and explain ──────────────────
            st.session_state["_pii_seen_count"] = 1
            _mode_label = (
                "Azure Content Safety API + regex scan" if use_live
                else "Regex + keyword scan (mock mode)"
            )
            _pii_lines = "\n\n".join(f"- **{v.field or 'field'}**: {v.message}" for v in _pii_warns)
            st.warning(
                f"### ⚠️ Personal data detected [{_mode_label}]\n\n"
                f"{_pii_lines}\n\n"
                "---\n"
                "**Your study plan was not generated.**\n\n"
                "Please remove the flagged data from the form fields listed above, "
                "then click **🎯 Create My AI Study Plan** again.\n\n"
                "*If this is not real personal data and you still want to continue, "
                "click the button once more without making changes.*"
            )
            st.stop()
        else:
            # ── Second submission: user acknowledged, proceed with notice ─────
            st.session_state["_pii_seen_count"] = 0
            _mode_label = (
                "Azure Content Safety API + regex scan" if use_live
                else "Regex + keyword scan (mock mode)"
            )
            _pii_lines = "\n\n".join(f"- {v.message}" for v in _pii_warns)
            st.info(
                f"ℹ️ **Proceeding despite PII warnings [{_mode_label}]** — "
                "data remains in your form. Consider removing it after this session.\n\n"
                + _pii_lines
            )
    else:
        # Clean input — reset counter so next PII detection is fresh
        st.session_state["_pii_seen_count"] = 0

    for v in _other_warns:
        st.warning(f"⚠️ [{v.code}] {v.message}")

    # ── Profile generation ────────────────────────────────────────────────────
    if use_live:
        try:
            os.environ["AZURE_OPENAI_ENDPOINT"]    = az_endpoint
            os.environ["AZURE_OPENAI_API_KEY"]     = az_key
            os.environ["AZURE_OPENAI_DEPLOYMENT"]  = az_deployment
            os.environ["AZURE_OPENAI_API_VERSION"] = _env_version

            from cert_prep.b0_intake_agent import LearnerProfilingAgent
            _profiler = LearnerProfilingAgent()
            _using_foundry = _profiler.using_foundry
            _cache_hit = _profiler.peek_cache(raw)  # internal optimisation only
            _spinner_msg = (
                "☁️ Calling Azure AI Foundry Agent Service SDK — creating managed agent…"
                if _using_foundry
                else "☁️ Calling Azure OpenAI — analysing profile…"
            )
            with st.spinner(_spinner_msg):
                profile: LearnerProfile = _profiler.run(raw)

            if _using_foundry:
                st.success("✅ Profile generated via **Azure AI Foundry Agent Service SDK** (managed agent + thread).")
                mode_badge = "☁️ Azure AI Foundry SDK"
            else:
                st.success("✅ Live Azure OpenAI profile generated.")
                mode_badge = "☁️ Live Azure OpenAI"
        except Exception as e:
            st.error(f"Azure call failed: {e}")
            st.info("Falling back to mock profiler.")
            profile, trace = run_mock_profiling_with_trace(raw)
            st.session_state["trace"] = trace
            mode_badge = "🧪 Mock (fallback)"
    else:
        with st.spinner("🧪 Running rule-based profiler…"):
            profile, trace = run_mock_profiling_with_trace(raw)
        st.session_state["trace"] = trace
        mode_badge = "🧪 Mock mode"

    # ── Guardrail: validate profile output ───────────────────────────────────
    _profile_result = _guardrails.check_profile(profile)
    if _profile_result.blocked:
        for v in _profile_result.violations:
            if v.level == GuardrailLevel.BLOCK:
                st.error(f"🚫 Profile guardrail [{v.code}]: {v.message}")
        st.warning("Profile has critical issues; results may be unreliable.")

    st.session_state["profile"]           = profile
    st.session_state["intake_submitted"]   = True
    st.session_state["raw"]               = raw
    st.session_state["badge"]             = mode_badge
    st.session_state.pop("editing_profile", None)  # exit edit mode after save
    st.session_state["guardrail_input"]   = _input_result
    st.session_state["guardrail_profile"] = _profile_result

    # ── Generate study plan + learning path CONCURRENTLY (asyncio.gather() pattern) ──
    # Both agents depend only on LearnerProfile — no data dependency between them.
    # ThreadPoolExecutor provides true I/O parallelism in live Azure OpenAI mode
    # (~8s instead of ~14s sequential) and works correctly inside Streamlit's
    # synchronous execution model without nest_asyncio hacks.
    _existing_certs_list = [c.strip() for c in existing_certs_raw.split(",") if c.strip()]

    def _run_study_plan():
        return StudyPlanAgent().run_with_raw(profile, existing_certs=_existing_certs_list)

    def _run_learning_path():
        return LearningPathCuratorAgent().curate(profile)

    _t0 = time.perf_counter()
    with st.spinner("⚡ Parallel Agents: Study Plan + Learning Path Curator running concurrently…"):
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as _executor:
            _plan_future = _executor.submit(_run_study_plan)
            _path_future = _executor.submit(_run_learning_path)
            plan: StudyPlan          = _plan_future.result()
            learning_path: LearningPath = _path_future.result()
    _parallel_ms = int((time.perf_counter() - _t0) * 1000)
    st.session_state["parallel_agent_ms"] = _parallel_ms

    # Guardrail checks on both outputs (run after parallel completion)
    _plan_result  = _guardrails.check_study_plan(plan, profile)
    _path_result  = _guardrails.check_learning_path(learning_path)
    st.session_state["plan"]           = plan
    st.session_state["guardrail_plan"] = _plan_result
    st.session_state["learning_path"]  = learning_path
    st.session_state["guardrail_path"] = _path_result
    _student_name = student_name.strip()
    upsert_student(_student_name, APP_PIN, "learner")
    save_profile(
        _student_name,
        profile.model_dump_json(),
        _json_mod.dumps(_dc.asdict(raw)),
        exam_target.strip(),
        badge=mode_badge,
    )
    save_plan(_student_name, _dc_to_json(plan))
    save_learning_path(_student_name, _dc_to_json(learning_path))
    if st.session_state.get("trace"):
        _trace_obj = st.session_state["trace"]
        save_trace(_student_name, _json_mod.dumps(_trace_obj.__dict__, default=str))

    # ── Auto-email: send study plan + PDF on first intake ─────────────────────
    _intake_email = raw.email.strip() if raw.email else ""
    _smtp_ready = _is_real_value(os.getenv("SMTP_USER", "")) and _is_real_value(os.getenv("SMTP_PASS", ""))
    if _intake_email and _smtp_ready:
        try:
            _intake_html = generate_intake_summary_html(profile, plan, learning_path)
            _intake_pdf  = _get_or_generate_pdf(
                st.session_state.get("sidebar_prefill"), "profile",
                generate_profile_pdf, profile, plan, learning_path, raw,
            )
            _pdf_fname   = f"StudyPlan_{_student_name.replace(' ','_')}_{profile.exam_target.split()[0]}.pdf"
            _subj        = f"Your {profile.exam_target} Study Plan is Ready — {_student_name}"
            _ok_i, _msg_i = attempt_send_email(
                _intake_email, _subj, _intake_html,
                pdf_bytes=_intake_pdf, pdf_filename=_pdf_fname,
            )
            if _ok_i:
                st.success(f"📧 Study plan emailed to **{_intake_email}** with PDF attached!")
            else:
                st.info("✉️ Auto-email failed — check SMTP credentials in .env. Use the ⬇️ Download PDF button in the Profile tab.")
        except Exception:
            pass  # silently skip auto-email on unexpected errors


# ─── Results ─────────────────────────────────────────────────────────────────
if "profile" in st.session_state:
    profile: LearnerProfile  = st.session_state["profile"]
    raw:     RawStudentInput = st.session_state["raw"]
    badge = st.session_state.get("badge", "")

    st.markdown("---")
    st.markdown(f"## 📊 Learner Profile  <small style='color:grey;font-size:0.8rem;'>({badge})</small>",
                unsafe_allow_html=True)

    # ── KPI info-bar (HTML cards — never truncates) ───────────────────────────
    risk_count = len(profile.risk_domains)
    skip_count = len(profile.modules_to_skip)
    avg_conf   = sum(dp.confidence_score for dp in profile.domain_profiles) / len(profile.domain_profiles)

    conf_color = "#27ae60" if avg_conf >= 0.65 else ("#e67e22" if avg_conf >= 0.40 else "#e74c3c")
    risk_color = "#e74c3c" if risk_count > 2 else ("#e67e22" if risk_count > 0 else "#27ae60")

    # Risk / confidence backgrounds (light pastel that complements the value colour)
    _rc_bg  = "#fff1f0" if risk_count > 2 else ("#fff8ee" if risk_count > 0 else "#f0fff4")
    _rc_bdr = risk_color
    _cf_bg  = "#f0fff4" if avg_conf >= 0.65 else ("#fff8ee" if avg_conf >= 0.40 else "#fff1f0")
    _learn_icon = {"unknown": "🌱", "weak": "📖", "moderate": "📘", "strong": "🏆"}.get(
        profile.experience_level.value.split("_")[0], "🎓"
    )

    kpi_cards = f"""
    <div style="display:flex;gap:14px;margin-bottom:18px;flex-wrap:wrap;">

      <!-- Student -->
      <div style="flex:1;min-width:150px;
                  background:linear-gradient(135deg,#f5f0ff 0%,#ede9fe 100%);
                  border-left:5px solid #7c3aed;border-radius:10px;padding:14px 18px;
                  box-shadow:0 2px 8px rgba(124,58,237,.12);">
        <div style="color:#7c3aed;font-size:0.68rem;font-weight:700;
                    text-transform:uppercase;letter-spacing:.08em;margin-bottom:5px;">🎓 Student</div>
        <div style="color:#3b0764;font-size:1.1rem;font-weight:800;
                    line-height:1.3;word-break:break-word;">{profile.student_name}</div>
        <div style="color:#8b5cf6;font-size:0.75rem;margin-top:3px;">
          🎯&nbsp;{profile.exam_target}
        </div>
      </div>

      <!-- Experience -->
      <div style="flex:1;min-width:150px;
                  background:linear-gradient(135deg,#eff6ff 0%,#dbeafe 100%);
                  border-left:5px solid #2563eb;border-radius:10px;padding:14px 18px;
                  box-shadow:0 2px 8px rgba(37,99,235,.12);">
        <div style="color:#2563eb;font-size:0.68rem;font-weight:700;
                    text-transform:uppercase;letter-spacing:.08em;margin-bottom:5px;">{_learn_icon} Experience</div>
        <div style="color:#1e3a8a;font-size:1.05rem;font-weight:800;
                    line-height:1.3;word-break:break-word;">
          {profile.experience_level.value.replace("_", " ").title()}
        </div>
        <div style="color:#3b82f6;font-size:0.75rem;margin-top:3px;">
          📚&nbsp;{profile.learning_style.value.replace("_"," ").title()} learner
        </div>
      </div>

      <!-- Study Budget -->
      <div style="flex:1;min-width:140px;
                  background:linear-gradient(135deg,#f0fdf4 0%,#bbf7d0 100%);
                  border-left:5px solid #16a34a;border-radius:10px;padding:14px 18px;
                  box-shadow:0 2px 8px rgba(22,163,74,.12);">
        <div style="color:#16a34a;font-size:0.68rem;font-weight:700;
                    text-transform:uppercase;letter-spacing:.08em;margin-bottom:5px;">⏱ Study Budget</div>
        <div style="color:#14532d;font-size:1.15rem;font-weight:800;line-height:1.3;">
          {profile.total_budget_hours:.0f}&nbsp;h
        </div>
        <div style="color:#22c55e;font-size:0.75rem;margin-top:3px;">
          {profile.hours_per_week}h/wk × {profile.weeks_available} weeks
        </div>
      </div>

      <!-- Risk Domains -->
      <div style="flex:1;min-width:140px;
                  background:linear-gradient(135deg,{_rc_bg} 0%,white 100%);
                  border-left:5px solid {_rc_bdr};border-radius:10px;padding:14px 18px;
                  box-shadow:0 2px 8px rgba(0,0,0,.07);">
        <div style="color:{_rc_bdr};font-size:0.68rem;font-weight:700;
                    text-transform:uppercase;letter-spacing:.08em;margin-bottom:5px;">⚠ Risk Domains</div>
        <div style="color:{_rc_bdr};font-size:1.25rem;font-weight:800;line-height:1.3;">
          {risk_count}
          <span style="font-size:0.8rem;font-weight:500;color:#555;margin-left:4px;">
            {"critical" if risk_count > 2 else ("flagged" if risk_count > 0 else "clear")}
          </span>
        </div>
        <div style="color:#888;font-size:0.75rem;margin-top:3px;">
          {skip_count} domains skippable
        </div>
      </div>

      <!-- Avg Confidence -->
      <div style="flex:1;min-width:140px;
                  background:linear-gradient(135deg,{_cf_bg} 0%,white 100%);
                  border-left:5px solid {conf_color};border-radius:10px;padding:14px 18px;
                  box-shadow:0 2px 8px rgba(0,0,0,.07);">
        <div style="color:{conf_color};font-size:0.68rem;font-weight:700;
                    text-transform:uppercase;letter-spacing:.08em;margin-bottom:5px;">💯 Avg Confidence</div>
        <div style="color:{conf_color};font-size:1.35rem;font-weight:800;line-height:1.3;">
          {avg_conf:.0%}
        </div>
        <div style="color:#888;font-size:0.75rem;margin-top:3px;">
          {"Great start! 🎉" if avg_conf >= 0.65 else ("Needs work 📖" if avg_conf >= 0.40 else "Remediation needed 🔧")}
        </div>
      </div>

    </div>
    """
    st.markdown(kpi_cards, unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    # All learners see all tabs (returning users have their data auto-loaded)
    tab_domains, tab_plan, tab_path, tab_recs, tab_progress, tab_quiz, tab_json = st.tabs([
        "🗺️ Domain Map",
        "📅 Study Setup",
        "📚 Learning Path",
        "💡 Recommendations",
        "📈 My Progress",
        "🧪 Knowledge Check",
        "📄 Raw JSON",
    ])

    # ── Auto-jump back to the correct tab after any form submission ───────────
    # st.form_submit_button always triggers a rerun which resets st.tabs() to
    # index 0 (Domain Map). Any handler that needs to stay on its tab stores
    # the desired tab index in _active_tab_idx before the rerun; the JS snippet
    # below clicks the right tab button once the DOM has rendered.
    _jump_tab = st.session_state.pop("_active_tab_idx", None)
    if _jump_tab is not None:
        _tab_js = f"""
        <script>
        (function() {{
            var targetIdx = {_jump_tab};
            var attempts  = 0;
            var maxTries  = 30;
            function clickTab() {{
                try {{
                    var doc = window.parent.document;
                    // Try multiple selectors for Streamlit 1.31+ through 1.54+
                    var tabs = doc.querySelectorAll('[data-baseweb="tab"]');
                    if (!tabs.length) tabs = doc.querySelectorAll('[role="tab"]');
                    if (!tabs.length) tabs = doc.querySelectorAll('.stTabs button');
                    if (tabs.length > targetIdx) {{
                        tabs[targetIdx].click();
                        return;
                    }}
                }} catch(e) {{}}
                if (attempts++ < maxTries) setTimeout(clickTab, 100);
            }}
            // First attempt after 400ms — enough for Streamlit to paint the tabs
            setTimeout(clickTab, 400);
        }})();
        </script>
        """
        st.components.v1.html(_tab_js, height=1)

    # ── Tab 1: Domain Map ─────────────────────────────────────────────────────
    with tab_domains:
        st.markdown('<a href="#" style="font-size:0.75rem;color:#9CA3AF;text-decoration:none;">↑ Back to top</a>', unsafe_allow_html=True)
        st.markdown("### 🗺️ Domain Knowledge Assessment")
        st.caption(
            "Your personalised exam domain map. Each bar shows your current confidence level "
            "across the key syllabus areas — making it easy to see exactly where to focus "
            "and which topics you can spend less time on."
        )

        # ── Pre-compute insight data ──────────────────────────────────────────
        def _wrap_label(s: str, width: int = 18) -> str:
            """Break long domain labels at word boundaries for x-axis display."""
            words, line, lines = s.split(), "", []
            for w in words:
                if len(line) + len(w) + (1 if line else 0) > width:
                    if line:
                        lines.append(line)
                    line = w
                else:
                    line = (line + " " + w).strip()
            if line:
                lines.append(line)
            return "<br>".join(lines)

        labels    = [_wrap_label(dp.domain_name.replace(" Solutions", "").replace("Implement ", ""))
                     for dp in profile.domain_profiles]
        scores    = [dp.confidence_score for dp in profile.domain_profiles]
        threshold = [0.50] * len(labels)

        _sorted_dp   = sorted(profile.domain_profiles, key=lambda d: d.confidence_score)
        _weakest     = _sorted_dp[0]
        _strongest   = _sorted_dp[-1]
        _above_thresh = [dp for dp in profile.domain_profiles if dp.confidence_score >= 0.50]
        _below_thresh = [dp for dp in profile.domain_profiles if dp.confidence_score < 0.50]
        _score_range  = _strongest.confidence_score - _weakest.confidence_score
        _avg_score    = sum(scores) / len(scores)

        # ── Radar: Knowledge Coverage by Domain ─────────────────────────────
        st.markdown("#### 🕸️ Knowledge Coverage by Domain")
        st.caption(
            "The filled shape represents your current knowledge coverage. "
            "The dashed orange ring marks the 50 % pass-readiness threshold. "
            "Domains where the shape dips inside the ring need focused study."
        )

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=scores + [scores[0]],
            theta=labels + [labels[0]],
            fill="toself",
            name="Student confidence",
            line=dict(color=BLUE, width=2),
            fillcolor="rgba(0,120,212,0.15)",
        ))
        fig.add_trace(go.Scatterpolar(
            r=threshold + [threshold[0]],
            theta=labels + [labels[0]],
            name="Min threshold (50%)",
            line=dict(color="#ca5010", width=1.5, dash="dot"),
            fill="none",
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 1], tickformat=".0%",
                                gridcolor="#e0e0e0", linecolor="#e0e0e0"),
                angularaxis=dict(linecolor="#cccccc"),
                bgcolor="white",
            ),
            legend=dict(orientation="h", yanchor="bottom", y=-0.15),
            margin=dict(t=30, b=60, l=60, r=60),
            height=380,
            paper_bgcolor="white",
            plot_bgcolor="white",
        )

        col_chart, col_detail = st.columns([1, 1])
        with col_chart:
            st.plotly_chart(fig, use_container_width=True)

            # ── Radar insights ────────────────────────────────────────────────
            _shape_pct = int((_avg_score / 0.50) * 100)
            _radar_colour = GREEN if len(_below_thresh) == 0 else (GOLD if len(_below_thresh) <= 2 else "#d13438")
            _coverage_label = (
                "Full coverage above threshold" if not _below_thresh
                else f"{len(_below_thresh)} domain(s) below threshold"
            )
            st.markdown(
                f"""<div style="background:#f8f8ff;border-left:4px solid {PURPLE};
                     border-radius:8px;padding:10px 14px;margin-top:4px;font-size:0.85rem;">
                  <b style="font-size:0.9rem;">📌 Radar Insights</b><br/><br/>
                  <b>Shape coverage:</b> {_avg_score:.0%} avg confidence
                  &nbsp;<span style="color:{_radar_colour};font-weight:600;">({_coverage_label})</span><br/>
                  <b>Strongest axis:</b>
                    <span style="color:{GREEN};font-weight:600;">
                      {_strongest.domain_name.replace("Implement ","").replace(" Solutions","")}
                    </span>
                    &nbsp;at {_strongest.confidence_score:.0%}<br/>
                  <b>Weakest axis:</b>
                    <span style="color:#d13438;font-weight:600;">
                      {_weakest.domain_name.replace("Implement ","").replace(" Solutions","")}
                    </span>
                    &nbsp;at {_weakest.confidence_score:.0%}<br/>
                  <b>Score range:</b> {_score_range:.0%}
                    {"&nbsp;— wide gap, uneven preparation" if _score_range > 0.40
                     else ("&nbsp;— moderate spread" if _score_range > 0.20
                     else "&nbsp;— fairly balanced")}<br/>
                  {"<b style='color:#d13438;'>⚠ " + str(len(_below_thresh)) + " domain(s) need immediate focus:</b> " +
                    ", ".join(dp.domain_name.replace("Implement ","").replace(" Solutions","")
                              for dp in _below_thresh)
                   if _below_thresh else
                   "<b style='color:" + GREEN + ";'>✓ All domains meet the 50 % readiness threshold.</b>"}
                </div>""",
                unsafe_allow_html=True,
            )

        with col_detail:
            st.markdown("**Initial Knowledge Baseline**")
            st.caption("AI-estimated starting point from your background — shows where to focus, not your final level.")
            _BASELINE_LABEL = {
                "unknown":  "Not Assessed",
                "weak":     "Needs Focus",
                "moderate": "Building Up",
                "strong":   "Strong Start",
            }
            for dp in profile.domain_profiles:
                level  = dp.knowledge_level.value
                colour = LEVEL_COLOUR[level]
                icon   = LEVEL_ICON[level]
                pct    = int(dp.confidence_score * 100)
                skip   = "⏭ Fast-track" if dp.skip_recommended else ""
                risk   = "⚠️ Priority" if dp.domain_id in profile.risk_domains else ""
                flags  = f"&nbsp;{skip}&nbsp;{risk}" if (skip or risk) else ""
                blabel = _BASELINE_LABEL.get(level, level.title())

                st.markdown(
                    f"""<div style="margin-bottom:10px;">
                        <span><b>{dp.domain_name}</b></span>
                        <span style="background:{colour};color:white;
                              padding:1px 8px;border-radius:10px;font-size:0.75rem;
                              font-weight:600;margin-left:8px;">{icon} {blabel}</span>
                        <span style="font-size:0.75rem;color:grey;margin-left:8px;">{flags}</span>
                        <div style="background:#e0e0e0;border-radius:4px;height:8px;margin-top:4px;">
                          <div style="background:{colour};width:{pct}%;height:8px;border-radius:4px;"></div>
                        </div>
                        <span style="font-size:0.75rem;color:#555;">{pct}% initial estimate — {dp.notes}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )

        # ── Domain Weight vs Confidence chart ────────────────────────────────
        st.markdown("---")
        st.markdown("#### 📊 Exam Score Contribution Analysis")
        st.caption(
            "Both bars use the same unit: **% of your total exam score**. "
            "'Max possible' = the exam weight for that domain (if you scored 100% in it). "
            "'Expected score' = exam weight × your confidence — the points you are likely to earn. "
            "The gap is the score you are leaving on the table. Prioritise high-weight, low-confidence domains."
        )

        # Fetch official domain weights from the registry
        _exam_domain_list = get_exam_domains(raw.exam_target)
        _weight_by_id     = {d["id"]: d["weight"] for d in _exam_domain_list}

        _weights    = [_weight_by_id.get(dp.domain_id, 1.0 / len(profile.domain_profiles))
                       for dp in profile.domain_profiles]
        _conf_frac  = [dp.confidence_score for dp in profile.domain_profiles]       # 0–1
        _conf_pct   = [c * 100 for c in _conf_frac]                                 # for summary table
        _weight_pct = [w * 100 for w in _weights]                                   # max contribution %

        # Common scale: both expressed as "% of total exam score"
        # Max contribution  = weight × 100   (what you'd earn at 100% confidence)
        # Expected score    = weight × confidence × 100
        _expected_pct = [w * c * 100 for w, c in zip(_weights, _conf_frac)]
        _bar_labels   = labels  # already short-form

        # Colour each expected-score bar by knowledge level
        _exp_colours = [LEVEL_COLOUR[dp.knowledge_level.value] for dp in profile.domain_profiles]

        # Gap = exam points being left on the table (max - expected)
        _pts_gap = [m - e for m, e in zip(_weight_pct, _expected_pct)]
        _gap_texts = [
            f"▼ {g:.1f}pt gap" if g > 0.5 else "✓ on track"
            for g in _pts_gap
        ]
        _gap_colours = [
            "#d13438" if g > 5 else ("#ca5010" if g > 2 else "#27ae60")
            for g in _pts_gap
        ]

        # Predicted total score annotation
        _predicted_total = sum(_expected_pct)
        _pass_mark       = 70.0   # standard MS certification pass mark

        bar_fig = go.Figure()

        # Trace 1 — Max possible contribution (= exam weight)
        bar_fig.add_trace(go.Bar(
            name="Max possible (exam weight)",
            x=_bar_labels,
            y=_weight_pct,
            marker=dict(color="#BFD4EF", line=dict(color="#0078D4", width=1.2)),
            text=[f"{w:.0f}pt" for w in _weight_pct],
            textposition="outside",
            textfont=dict(color="#0078D4", size=11, family="Segoe UI"),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Exam weight: %{y:.1f}% of total score<br>"
                "<i>Points available if you score 100% here</i><extra></extra>"
            ),
        ))

        # Trace 2 — Expected score contribution (weight × confidence)
        bar_fig.add_trace(go.Bar(
            name="Expected score (weight × confidence)",
            x=_bar_labels,
            y=_expected_pct,
            marker=dict(color=_exp_colours, opacity=0.88, line=dict(width=0)),
            text=[f"{e:.1f}pt" for e in _expected_pct],
            textposition="outside",
            textfont=dict(color="#555", size=11, family="Segoe UI"),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Expected score: %{y:.1f}% of total<br>"
                "<i>= exam weight × your confidence</i><extra></extra>"
            ),
        ))

        # Pass-mark reference line
        bar_fig.add_hline(
            y=_pass_mark / len(profile.domain_profiles),  # per-domain average needed to pass
            line_dash="dot", line_color="#ca5010",
            annotation_text=f"Avg needed per domain to pass ({_pass_mark:.0f}%)",
            annotation_font=dict(color="#ca5010", size=10),
            annotation_position="top right",
        )

        _y_max = max(_weight_pct) * 1.30
        _ann_colour = "#27ae60" if _predicted_total >= _pass_mark else "#d13438"
        _ann_suffix = (
            "above pass mark \u2713"
            if _predicted_total >= _pass_mark
            else f"below pass mark \u2014 need {_pass_mark - _predicted_total:.0f}pt more"
        )
        bar_fig.update_layout(
            barmode="group",
            bargroupgap=0.10,
            bargap=0.30,
            height=460,
            margin=dict(l=10, r=20, t=55, b=80),
            xaxis=dict(
                tickfont=dict(size=10, family="Segoe UI"),
                tickangle=0,
                automargin=True,
                showgrid=False,
            ),
            yaxis=dict(
                range=[0, _y_max],
                ticksuffix="pt",
                showgrid=True,
                gridcolor="#eeeeee",
                title=dict(text="Exam score contribution (pts = % of total)", font=dict(size=11, color="#616161")),
            ),
            paper_bgcolor="white",
            plot_bgcolor="white",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02,
                xanchor="left", x=0,
                font=dict(size=11),
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="#e0e0e0", borderwidth=1,
            ),
            annotations=[dict(
                text=f"🎯 Predicted total: <b>{_predicted_total:.0f} / 100</b> — {_ann_suffix}",
                xref="paper", yref="paper", x=0, y=-0.22,
                showarrow=False, align="left",
                font=dict(size=12, family="Segoe UI", color=_ann_colour),
            )],
            uniformtext_minsize=8,
            uniformtext_mode="hide",
        )
        st.plotly_chart(bar_fig, use_container_width=True)

        # Gap summary table (domain · exam weight · confidence · expected score · gap)
        _gap_rows = ""
        for i, dp in enumerate(profile.domain_profiles):
            _lbl  = _bar_labels[i]
            _wt   = _weight_pct[i]
            _cf   = _conf_pct[i]
            _ex   = _expected_pct[i]
            _gc   = _gap_colours[i]
            _gt   = _gap_texts[i]
            _bg   = "#FFF1F0" if _gc == "#d13438" else ("#FFFAF0" if _gc == "#ca5010" else "#F0FFF4")
            _gap_rows += (
                f'<tr style="background:{_bg};">'
                f'<td style="padding:5px 10px;font-size:0.82rem;color:#1B1B1B;font-weight:600;">{_lbl}</td>'
                f'<td style="padding:5px 10px;font-size:0.82rem;text-align:center;color:#0078D4;font-weight:700;">{_wt:.0f}pt</td>'
                f'<td style="padding:5px 10px;font-size:0.82rem;text-align:center;'
                f'color:{LEVEL_COLOUR[dp.knowledge_level.value]};font-weight:700;">{_cf:.0f}%</td>'
                f'<td style="padding:5px 10px;font-size:0.82rem;text-align:center;font-weight:700;">{_ex:.1f}pt</td>'
                f'<td style="padding:5px 10px;font-size:0.82rem;text-align:center;'
                f'color:{_gc};font-weight:700;">{_gt}</td>'
                f'</tr>'
            )
        st.markdown(f"""
        <table style="width:100%;border-collapse:collapse;margin-top:8px;
                      border:1px solid #E1DFDD;border-radius:6px;overflow:hidden;">
          <thead>
            <tr style="background:#EFF6FF;">
              <th style="padding:6px 10px;font-size:0.74rem;color:#0078D4;text-align:left;
                         text-transform:uppercase;letter-spacing:.06em;">Domain</th>
              <th style="padding:6px 10px;font-size:0.74rem;color:#0078D4;text-align:center;
                         text-transform:uppercase;letter-spacing:.06em;">Max (pts)</th>
              <th style="padding:6px 10px;font-size:0.74rem;color:#0078D4;text-align:center;
                         text-transform:uppercase;letter-spacing:.06em;">Confidence</th>
              <th style="padding:6px 10px;font-size:0.74rem;color:#0078D4;text-align:center;
                         text-transform:uppercase;letter-spacing:.06em;">Expected (pts)</th>
              <th style="padding:6px 10px;font-size:0.74rem;color:#0078D4;text-align:center;
                         text-transform:uppercase;letter-spacing:.06em;">Gap</th>
            </tr>
          </thead>
          <tbody>{_gap_rows}</tbody>
        </table>
        """, unsafe_allow_html=True)

        # ── Profile snapshot: 4-bullet summary card ──────────────────────────
        _skip_names = [dp.domain_name.replace("Implement ","").replace(" Solutions","")
                       for dp in profile.domain_profiles if dp.skip_recommended]
        _risk_names = [dp.domain_name.replace("Implement ","").replace(" Solutions","")
                       for dp in profile.domain_profiles if dp.domain_id in profile.risk_domains]

        # Bullet 1 — readiness snapshot
        _b1_colour = GREEN if avg_conf >= 0.65 else (GOLD if avg_conf >= 0.40 else "#d13438")
        _b1_icon   = "✅" if avg_conf >= 0.65 else ("⚡" if avg_conf >= 0.40 else "🔴")
        _b1 = (
            f"{_b1_icon} <b>Overall readiness:</b> "
            f"<span style='color:{_b1_colour};font-weight:700;'>{avg_conf:.0%} avg confidence</span> — "
            f"{profile.experience_level.value.replace('_',' ').title()} level · "
            f"{len(_above_thresh)}/{len(profile.domain_profiles)} domains above the 50% pass threshold."
        )
        # Bullet 2 — top strengths
        _strong_names = [dp.domain_name.replace("Implement ","").replace(" Solutions","")
                         for dp in sorted(profile.domain_profiles,
                                          key=lambda d: d.confidence_score, reverse=True)[:2]]
        _b2 = (
            f"🏆 <b>Strongest areas:</b> "
            + ", ".join(f"<b>{n}</b>" for n in _strong_names)
            + f" — these can be covered faster, freeing up time for weaker domains."
        )
        # Bullet 3 — risk / focus
        if _risk_names:
            _b3 = (
                f"⚠️ <b>Focus areas (below threshold):</b> "
                + ", ".join(f"<span style='color:#d13438;font-weight:600;'>{n}</span>" for n in _risk_names)
                + " — allocate extra study time here before sitting the exam."
            )
        else:
            _b3 = (
                f"✅ <b>No domains below the 50% risk threshold</b> — "
                f"your baseline is solid; shift focus to exam-style practice questions."
            )
        # Bullet 4 — fast-track / next step
        if _skip_names:
            _b4 = (
                f"⏭️ <b>Fast-track candidates:</b> "
                + ", ".join(f"<b>{n}</b>" for n in _skip_names)
                + " — existing knowledge means these modules need brief review only."
            )
        else:
            _b4 = (
                f"📅 <b>Recommended next step:</b> review the Study Setup tab to see your "
                f"week-by-week Gantt plan and confirm your {raw.weeks_available}-week schedule."
            )

        st.markdown(f"""
        <div style="margin-top:16px;background:#F8F9FF;border:1px solid #C7D7F5;
                    border-left:4px solid #0078D4;border-radius:8px;padding:14px 18px;">
          <div style="font-size:0.8rem;font-weight:700;color:#0078D4;text-transform:uppercase;
                      letter-spacing:.07em;margin-bottom:10px;">📋 Profile Snapshot</div>
          <ul style="margin:0;padding-left:0;list-style:none;display:flex;flex-direction:column;gap:7px;">
            <li style="font-size:0.875rem;color:#1B1B1B;line-height:1.55;">{_b1}</li>
            <li style="font-size:0.875rem;color:#1B1B1B;line-height:1.55;">{_b2}</li>
            <li style="font-size:0.875rem;color:#1B1B1B;line-height:1.55;">{_b3}</li>
            <li style="font-size:0.875rem;color:#1B1B1B;line-height:1.55;">{_b4}</li>
          </ul>
        </div>""", unsafe_allow_html=True)

        # ── Download / Email Study Plan PDF ──────────────────────────────────
        st.markdown("---")
        st.markdown("### 📄 Study Plan Report")
        _smtp_cfg = _is_real_value(os.getenv("SMTP_USER", "")) and _is_real_value(os.getenv("SMTP_PASS", ""))
        _pdf_cols = st.columns([1, 1, 2])
        with _pdf_cols[0]:
            try:
                _plan_obj = st.session_state.get("plan")
                _lp_obj   = st.session_state.get("learning_path")
                _pdf_data = _get_or_generate_pdf(
                    st.session_state.get("sidebar_prefill"), "profile",
                    generate_profile_pdf, profile, _plan_obj, _lp_obj,
                    st.session_state.get("raw"),
                )
                _pdf_name = f"StudyPlan_{profile.student_name.replace(' ','_')}_{profile.exam_target.split()[0]}.pdf"
                st.download_button(
                    label="⬇️ Download PDF",
                    data=_pdf_data,
                    file_name=_pdf_name,
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as _pdf_err:
                st.caption(f"PDF unavailable: {_pdf_err}")
        with _pdf_cols[1]:
            _profile_email = getattr(profile, "email", "") or st.session_state.get("user_email", "")
            _email_to_send = st.text_input(
                "Email address",
                value=_profile_email,
                placeholder="you@example.com",
                key="profile_pdf_email",
                label_visibility="collapsed",
                disabled=not _smtp_cfg,
            )
        with _pdf_cols[2]:
            _email_btn_clicked = st.button(
                "📤 Email Study Plan PDF",
                key="profile_send_pdf",
                use_container_width=True,
                disabled=not _smtp_cfg,
                help="Configure SMTP_USER & SMTP_PASS in .env to enable email delivery" if not _smtp_cfg else None,
            )
            if _email_btn_clicked:
                if not _email_to_send:
                    st.error("Enter an email address first.")
                else:
                    try:
                        _plan_obj2 = st.session_state.get("plan")
                        _lp_obj2   = st.session_state.get("learning_path")
                        _pdf_bytes2 = _get_or_generate_pdf(
                            st.session_state.get("sidebar_prefill"), "profile",
                            generate_profile_pdf, profile, _plan_obj2, _lp_obj2,
                            st.session_state.get("raw"),
                        )
                        _html_body2 = generate_intake_summary_html(profile, _plan_obj2, _lp_obj2)
                        _subj2      = f"Your {profile.exam_target} Study Plan — {profile.student_name}"
                        _fname2     = f"StudyPlan_{profile.student_name.replace(' ','_')}_{profile.exam_target.split()[0]}.pdf"
                        with st.spinner("Sending…"):
                            _ok2, _msg2 = attempt_send_email(
                                _email_to_send, _subj2, _html_body2,
                                pdf_bytes=_pdf_bytes2, pdf_filename=_fname2,
                            )
                        if _ok2:
                            st.success(f"✅ {_msg2}")
                        else:
                            st.warning(f"⚠️ Email failed — {_msg2}")
                    except Exception as _e2:
                        st.error(f"Failed: {_e2}")

    # ── Tab 2: Study Setup ────────────────────────────────────────────────────
    with tab_plan:
        st.markdown('<a href="#" style="font-size:0.75rem;color:#9CA3AF;text-decoration:none;">↑ Back to top</a>', unsafe_allow_html=True)
        st.caption(
            "📅 **Study Setup** — your complete preparation blueprint. "
            "Check your prerequisites, see how long yours will take, and review "
            "the weekly phase plan built around your availability and target exam date."
        )
        plan: StudyPlan = st.session_state.get("plan")

        # ── 1. Prerequisites ──────────────────────────────────────────────────
        st.markdown("### 🎓 Study Pre-requisites")

        if plan and plan.prerequisites:
            prereq_held    = [p for p in plan.prerequisites if p.already_held]
            prereq_missing = [p for p in plan.prerequisites if not p.already_held and p.relationship == "strongly_recommended"]
            prereq_helpful = [p for p in plan.prerequisites if not p.already_held and p.relationship == "helpful"]

            # Status banner (one line)
            if plan.prereq_gap:
                _missing_codes = [p.cert_code for p in plan.prerequisites
                                   if not p.already_held and p.relationship == "strongly_recommended"]
                _gap_short = (
                    f"Missing strongly-recommended prerequisite{'s' if len(_missing_codes) > 1 else ''}: "
                    f"**{', '.join(_missing_codes)}**. "
                    f"Complete {'these' if len(_missing_codes) > 1 else 'this'} before sitting {profile.exam_target}."
                )
                st.warning(_gap_short, icon="⚠️")
            else:
                st.success(f"✅ All required prerequisites for **{profile.exam_target}** are already held.", icon="✅")

            # Compact inline rows — one cert per row, styled simply
            def _prereq_row(code, name, status_html):
                return (
                    f'<div style="display:flex;align-items:center;gap:10px;'
                    f'padding:7px 12px;border-radius:7px;margin-bottom:5px;background:#F9FAFB;'
                    f'border:1px solid #E5E7EB;">'
                    f'<span style="font-weight:700;color:#111;font-size:0.88rem;min-width:70px;">{code}</span>'
                    f'<span style="color:#555;font-size:0.83rem;flex:1;">{name}</span>'
                    f'{status_html}</div>'
                )

            rows_html = ""
            for p in prereq_missing:
                rows_html += _prereq_row(
                    p.cert_code, p.cert_name,
                    '<span style="background:#FEE2E2;color:#991B1B;border-radius:4px;'
                    'padding:2px 8px;font-size:0.74rem;white-space:nowrap;">⚠ Required — not held</span>',
                )
            for p in prereq_held:
                rows_html += _prereq_row(
                    p.cert_code, p.cert_name,
                    '<span style="background:#DCFCE7;color:#166534;border-radius:4px;'
                    'padding:2px 8px;font-size:0.74rem;white-space:nowrap;">✓ Held</span>',
                )
            for p in prereq_helpful:
                rows_html += _prereq_row(
                    p.cert_code, p.cert_name,
                    '<span style="background:#DBEAFE;color:#1E40AF;border-radius:4px;'
                    'padding:2px 8px;font-size:0.74rem;white-space:nowrap;">💡 Helpful</span>',
                )

            st.markdown(rows_html, unsafe_allow_html=True)
        else:
            st.info(f"No prerequisite data available for **{profile.exam_target}**. Check Microsoft Learn for the latest guidance.")

        st.markdown("---")

        # ── 2. Gantt Chart ────────────────────────────────────────────────────
        st.markdown("### 📊 Weekly Study Plan")
        st.caption("Domains ordered by priority — final week reserved for practice exams & revision.")

        if plan and plan.tasks:
            _BASE = datetime.date(2026, 1, 5)  # Monday Week 1 (display anchor)

            gantt_rows = []
            for task in plan.tasks:
                start_dt = _BASE + datetime.timedelta(weeks=task.start_week - 1)
                end_dt   = _BASE + datetime.timedelta(weeks=task.end_week)  # exclusive end
                short_name = (task.domain_name
                              .replace("Implement ", "")
                              .replace(" Solutions", "")
                              .replace(" & Knowledge Mining", " & KM"))
                gantt_rows.append({
                    "Domain":         short_name,
                    "Start":          start_dt.isoformat(),
                    "Finish":         end_dt.isoformat(),
                    "Priority":       task.priority.title(),
                    "Level":          task.knowledge_level.title(),
                    "Hours":          f"{task.total_hours:.0f} h",
                    "Confidence":     f"{task.confidence_pct}%",
                    "_color":         PLAN_COLOUR.get(task.priority, "#888"),
                    "WeekRange":      (f"Week {task.start_week}" if task.start_week == task.end_week
                                       else f"Week {task.start_week}–{task.end_week}"),
                    "domain_id":      task.domain_id,
                })

            # Add review week bar — review hours = remaining budget after domain tasks
            _gantt_domain_h  = sum(t.total_hours for t in plan.tasks)
            _gantt_review_h  = max(0.0, profile.total_budget_hours - _gantt_domain_h)
            review_start = _BASE + datetime.timedelta(weeks=plan.review_start_week - 1)
            review_end   = _BASE + datetime.timedelta(weeks=plan.review_start_week)
            gantt_rows.append({
                "Domain":     "🏁 Review & Practice Exam",
                "Start":      review_start.isoformat(),
                "Finish":     review_end.isoformat(),
                "Priority":   "Review",
                "Level":      "-",
                "Hours":      f"{_gantt_review_h:.0f} h",
                "Confidence": "—",
                "_color":     PLAN_COLOUR["review"],
                "WeekRange":  f"Week {plan.review_start_week}",
                "domain_id":  "review",
            })

            import pandas as pd
            gantt_df = pd.DataFrame(gantt_rows)

            # Sort by start date so bars appear in schedule order top-to-bottom
            gantt_df = gantt_df.sort_values("Start", ascending=False)

            _COLOR_MAP = {
                row["Priority"]: row["_color"]
                for _, row in gantt_df.iterrows()
            }

            gantt_fig = px.timeline(
                gantt_df,
                x_start="Start",
                x_end="Finish",
                y="Domain",
                color="Priority",
                color_discrete_map=_COLOR_MAP,
                custom_data=["WeekRange", "Hours", "Level", "Confidence", "Priority"],
                labels={"Domain": ""},
            )

            gantt_fig.update_traces(
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "📅 %{customdata[0]}<br>"
                    "⏱ %{customdata[1]}<br>"
                    "📈 Level: %{customdata[2]}<br>"
                    "💯 Confidence: %{customdata[3]}<br>"
                    "🏷 Priority: %{customdata[4]}<extra></extra>"
                ),
            )

            # Replace date x-axis ticks with "Week N" labels
            week_ticks  = [(_BASE + datetime.timedelta(weeks=i)).isoformat()
                           for i in range(plan.total_weeks + 1)]
            week_labels = [f"Wk {i+1}" for i in range(plan.total_weeks + 1)]

            gantt_fig.update_layout(
                xaxis=dict(
                    tickvals=week_ticks,
                    ticktext=week_labels,
                    title="Study Weeks",
                    showgrid=True,
                    gridcolor="#eeeeee",
                ),
                yaxis=dict(title="", autorange=True),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.35,
                    title="Priority:",
                ),
                height=max(280, 60 + len(gantt_rows) * 42),
                margin=dict(l=10, r=20, t=20, b=10),
                paper_bgcolor="white",
                plot_bgcolor="white",
                bargap=0.25,
            )

            # Add week-boundary vertical lines
            for i in range(1, plan.total_weeks + 1):
                gantt_fig.add_vline(
                    x=(_BASE + datetime.timedelta(weeks=i - 1)).isoformat(),
                    line_width=1,
                    line_dash="dot",
                    line_color="#cccccc",
                )

            st.plotly_chart(gantt_fig, use_container_width=True)

            # Hour breakdown table
            st.markdown("#### ⏱ Study Hours by Domain")
            _PRIORITY_SORT = {"critical": 0, "high": 1, "medium": 2, "low": 3, "skip": 4, "review": 5}
            _BASELINE_LBL = {"unknown": "Not Assessed", "weak": "Needs Focus", "moderate": "Building Up", "strong": "Strong Start"}
            task_table_rows = [
                {
                    "Domain":         (t.domain_name.replace("Implement ", "")
                                      .replace(" Solutions", "")
                                      .replace(" & Knowledge Mining", " & KM")),
                    "Weeks":          f"{t.start_week}–{t.end_week}" if t.start_week != t.end_week else str(t.start_week),
                    "Hours":          f"{t.total_hours:.1f} h",
                    "Priority":       t.priority.title(),
                    "Starting Point": _BASELINE_LBL.get(t.knowledge_level, t.knowledge_level.title()),
                }
                for t in plan.tasks
            ]
            _domain_h = sum(t.total_hours for t in plan.tasks)
            _review_h = max(0.0, profile.total_budget_hours - _domain_h)
            task_table_rows.append({
                "Domain":         "🏁 Review & Practice Exam",
                "Weeks":          str(plan.review_start_week),
                "Hours":          f"{_review_h:.1f} h",
                "Priority":       "Review",
                "Starting Point": "—",
            })
            _total_h = profile.total_budget_hours
            task_table_rows.append({
                "Domain":         "📊 TOTAL",
                "Weeks":          f"1–{plan.total_weeks}",
                "Hours":          f"{_total_h:.1f} h",
                "Priority":       "—",
                "Starting Point": "—",
            })
            st.dataframe(
                pd.DataFrame(task_table_rows),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Run the profiler to generate the study plan.")

        # ── 3. Quick Summary ──────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 📋 Study Setup Summary")

        if plan:
            _total_h_sum  = profile.total_budget_hours
            _critical_dom = [t.domain_name.replace("Implement ", "").replace(" Solutions", "")
                             for t in plan.tasks if t.priority == "critical"]
            _skip_dom     = [t.domain_name.replace("Implement ", "").replace(" Solutions", "")
                             for t in plan.tasks if t.priority == "skip"]
            _avg_conf_sum = sum(dp.confidence_score for dp in profile.domain_profiles) / len(profile.domain_profiles)

            _s1, _s2, _s3, _s4 = st.columns(4)
            with _s1: st.metric("Study Budget", f"{_total_h_sum:.0f} h")
            with _s2: st.metric("Duration", f"{plan.total_weeks} weeks")
            with _s3: st.metric("Hours / Week", f"{profile.hours_per_week:.0f} h")
            with _s4: st.metric("Avg Confidence", f"{_avg_conf_sum*100:.0f}%")
            st.caption(
                f"{profile.hours_per_week:.0f} h/week × {profile.weeks_available} weeks = **{_total_h_sum:.0f} h total budget** "
                f"(covers MS Learn modules + labs + practice exams + review). "
                f"MS Learn curated content alone is shorter — see the Learning Path tab for module-level time."
            )

            _bullets = []
            if _critical_dom:
                _bullets.append(f"🔴 <b>Critical focus:</b> {', '.join(_critical_dom)}")
            if _skip_dom:
                _bullets.append(f"⏩ <b>Fast-track (skip):</b> {', '.join(_skip_dom)}")
            _bullets.append(f"🏁 <b>Review week:</b> Week {plan.review_start_week} — practice exams & revision")
            if plan.prereq_gap:
                _bullets.append(f"⚠️ <b>Prerequisite gap</b> — address before exam booking")
            else:
                _bullets.append("✅ <b>All prerequisites met</b> — ready to start studying")

            st.markdown(
                '<div style="background:#F8FAFF;border:1px solid #DBEAFE;border-left:4px solid #0078D4;'
                'border-radius:8px;padding:12px 16px;margin-top:8px;font-size:0.87rem;color:#374151;">'
                + "<br/>".join(f"&nbsp;&nbsp;{b}" for b in _bullets)
                + "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.info("Complete the intake form to generate your personalised study setup summary.")


    # ── Tab 3: Learning Path ──────────────────────────────────────────────────
    with tab_path:
        st.markdown('<a href="#" style="font-size:0.75rem;color:#9CA3AF;text-decoration:none;">↑ Back to top</a>', unsafe_allow_html=True)
        st.markdown("### 📚 Your Learning Path")
        st.caption(
            "📚 **Learning Path** — a curated list of Microsoft Learn modules tailored to your "
            "skill gaps. Modules are grouped by exam domain and ordered by priority, so you "
            "always know what to study next. Domains you already know well are automatically "
            "skipped to save you time."
        )

        _lp: LearningPath = st.session_state.get("learning_path")
        if not _lp:
            st.info("Generate your learner profile first to see curated learning modules.")
        else:
            # User-friendly summary banner (no agent jargon)
            _pr_result     = st.session_state.get("guardrail_path")
            _total_modules = len(_lp.all_modules)
            _active_doms   = len([dp for dp in profile.domain_profiles if not dp.skip_recommended])
            _skipped_doms  = len([dp for dp in profile.domain_profiles if dp.skip_recommended])
            _total_lp_hrs  = sum(getattr(m, "duration_min", 0) for m in _lp.all_modules) / 60.0
            _skip_note     = (
                f"&nbsp; {_skipped_doms} domain(s) skipped — strong prior knowledge detected there."
                if _skipped_doms else ""
            )
            st.markdown(
                f"""<div style="background:linear-gradient(135deg,#eff6ff,#dbeafe);
                     border-left:5px solid #2563eb;border-radius:10px;padding:12px 18px;
                     margin-bottom:16px;font-size:0.9rem;color:#374151;">
                  ✅ &nbsp;<b>Your personalised learning path is ready!</b><br/>
                  <span>We found <b>{_total_modules} Microsoft Learn modules</b> across
                  <b>{_active_doms} exam domain{"s" if _active_doms != 1 else ""}</b>
                  (~<b>{_total_lp_hrs:.1f} hours</b> of self-paced content).{_skip_note}
                  Modules are ordered by priority — work through them top to bottom.</span>
                </div>""",
                unsafe_allow_html=True,
            )

            # Guardrail notices
            if _pr_result:
                for _gv in _pr_result.violations:
                    if _gv.level.value == "WARN":
                        st.warning(f"⚠️ [{_gv.code}] {_gv.message}")

            # Domain-by-domain module list
            _dom_order = sorted(
                profile.domain_profiles,
                key=lambda dp: (
                    0 if dp.domain_id in profile.risk_domains else
                    2 if dp.skip_recommended else 1
                ),
            )

            _priority_colour = {
                "core":        ("#bbf7d0", "#16a34a", "🔴 Core"),
                "supplemental":(  "#dbeafe", "#2563eb", "🟡 Supplemental"),
                "optional":    ("#f3f4f6", "#6b7280", "⚪ Optional"),
            }

            for _dp in _dom_order:
                _domain_modules = _lp.curated_paths.get(_dp.domain_id, [])
                _skip_flag = "⏩ Skipped" if _dp.domain_id in _lp.skipped_domains else ""

                with st.expander(
                    f"{'⏩ ' if _skip_flag else ''}**{_dp.domain_name}** "
                    f"— {len(_domain_modules)} module(s)"
                    + (f"  _(skipped – strong prior knowledge)_" if _skip_flag else ""),
                    expanded=(not bool(_skip_flag) and _dp.domain_id in profile.risk_domains),
                ):
                    if not _domain_modules:
                        st.info("Domain skipped based on strong prior knowledge.")
                        continue

                    for _mod in _domain_modules:
                        _bg, _bd, _plabel = _priority_colour.get(
                            _mod.priority, ("#f9f9f9", "#888", _mod.priority)
                        )
                        st.markdown(
                            f"""<div style="background:{_bg};border-left:4px solid {_bd};
                                 border-radius:8px;padding:10px 14px;margin-bottom:8px;
                                 display:flex;justify-content:space-between;align-items:center;
                                 flex-wrap:wrap;gap:6px;">
                              <div style="flex:3;min-width:200px;">
                                <a href="{_mod.url}" target="_blank"
                                   style="color:#1e40af;font-weight:600;text-decoration:none;
                                          font-size:0.92rem;">
                                  🔗 {_mod.title}
                                </a><br/>
                                <span style="color:#6b7280;font-size:0.78rem;">
                                  {_mod.module_type.title()} · {_mod.difficulty.title()} · ~{_mod.duration_min} min
                                </span>
                              </div>
                              <div style="font-size:0.78rem;color:{_bd};font-weight:700;">{_plabel}</div>
                            </div>""",
                            unsafe_allow_html=True,
                        )

            # Total hours vs budget
            _ratio = _lp.total_hours_est / max(profile.total_budget_hours, 1)
            st.markdown("---")
            _ce1, _ce2, _ce3, _ce4 = st.columns(4)
            with _ce1:
                st.metric("Modules Curated", len(_lp.all_modules))
            with _ce2:
                st.metric("MS Learn Content", f"{_lp.total_hours_est:.1f} h",
                          help="Official Microsoft Learn estimated reading/video time for selected modules only.")
            with _ce3:
                st.metric("Full Study Budget", f"{profile.total_budget_hours:.0f} h",
                          help=f"{profile.hours_per_week:.0f} h/week × {profile.weeks_available} weeks. Includes labs, practice exams, and review time beyond MS Learn modules.")
            with _ce4:
                st.metric("Content vs Budget", f"{_ratio:.0%}",
                          help="MS Learn module time as a share of your total study budget. Remaining time is for labs, practice exams, and self-review.")
            st.caption(
                f"📌 **MS Learn content ({_lp.total_hours_est:.1f} h)** is the official module reading/video time. "
                f"Your **{profile.total_budget_hours:.0f} h total budget** ({profile.hours_per_week:.0f} h/week × {profile.weeks_available} weeks) "
                f"covers modules + hands-on labs + practice exams + review — consistent with your Study Setup plan."
            )

    # ── Tab 4: Recommendations ────────────────────────────────────────────────
    with tab_recs:
        st.markdown('<a href="#" style="font-size:0.75rem;color:#9CA3AF;text-decoration:none;">↑ Back to top</a>', unsafe_allow_html=True)
        st.caption(
            "💡 **Recommendations** — a plain-English summary of what your results mean and "
            "what to do next. Covers your learning style, risk areas, the exam that best matches "
            "your profile right now, and actionable next steps."
        )
        # ── 1. Personalised Recommendation ───────────────────────────────────
        st.markdown("### 💡 Personalised Recommendation")

        _style_label   = profile.learning_style.value.replace("_", " ").title()
        _exp_label     = profile.experience_level.value.replace("_", " ").title()
        _risk_names    = [EXAM_DOMAIN_NAMES.get(d, d) for d in (profile.risk_domains or [])]
        _skip_names    = [EXAM_DOMAIN_NAMES.get(m, m) for m in (profile.modules_to_skip or [])]

        _rc1, _rc2, _rc3 = st.columns(3)
        with _rc1:
            st.markdown(
                f"""<div style="background:#EFF6FF;border-radius:10px;padding:14px 16px;height:100%;">
                  <div style="font-size:0.72rem;font-weight:700;color:#2563EB;
                       text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px;">
                    Learning Style
                  </div>
                  <div style="font-size:1.1rem;font-weight:700;color:#1e3a8a;">{_style_label}</div>
                  <div style="font-size:0.78rem;color:#555;margin-top:6px;">
                    Experience: <b>{_exp_label}</b><br/>
                    Budget: <b>{profile.hours_per_week:.0f} h/wk × {profile.weeks_available} wks
                    = {profile.total_budget_hours:.0f} h total</b>
                  </div>
                </div>""",
                unsafe_allow_html=True,
            )
        with _rc2:
            _risk_html = "".join(
                f'<span style="display:inline-block;background:#FEE2E2;color:#991B1B;'
                f'border-radius:4px;padding:2px 8px;margin:2px 2px;font-size:0.76rem;">'
                f'⚠ {n}</span>'
                for n in _risk_names
            ) if _risk_names else '<span style="color:#16a34a;font-size:0.82rem;">✓ No critical gaps</span>'
            st.markdown(
                f"""<div style="background:#FFF5F5;border-radius:10px;padding:14px 16px;height:100%;">
                  <div style="font-size:0.72rem;font-weight:700;color:#DC2626;
                       text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;">
                    Focus Domains
                  </div>
                  {_risk_html}
                </div>""",
                unsafe_allow_html=True,
            )
        with _rc3:
            _skip_html = "".join(
                f'<span style="display:inline-block;background:#DCFCE7;color:#166534;'
                f'border-radius:4px;padding:2px 8px;margin:2px 2px;font-size:0.76rem;">'
                f'⏩ {n}</span>'
                for n in _skip_names
            ) if _skip_names else '<span style="color:#6b7280;font-size:0.82rem;">No fast-tracks — full study recommended</span>'
            st.markdown(
                f"""<div style="background:#F0FDF4;border-radius:10px;padding:14px 16px;height:100%;">
                  <div style="font-size:0.72rem;font-weight:700;color:#16A34A;
                       text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;">
                    Fast-Track Candidates
                  </div>
                  {_skip_html}
                </div>""",
                unsafe_allow_html=True,
            )

        st.markdown(
            f"""<div style="background:#F9FAFB;border:1px solid #E5E7EB;border-left:4px solid #0078D4;
                 border-radius:8px;padding:12px 16px;margin-top:10px;font-size:0.88rem;color:#374151;">
              <b style="color:#0078D4;">📌 Agent Recommendation</b><br/>{profile.recommended_approach}
            </div>""",
            unsafe_allow_html=True,
        )

        st.markdown("<br/>", unsafe_allow_html=True)

        # ── 2. Predicted Readiness Outlook ────────────────────────────────────
        st.markdown("### 🏁 Predicted Readiness Outlook")

        ready_domains = sum(1 for dp in profile.domain_profiles if dp.confidence_score >= 0.70)
        total_domains = len(profile.domain_profiles)
        ready_pct     = ready_domains / total_domains
        avg_conf      = sum(dp.confidence_score for dp in profile.domain_profiles) / total_domains

        # Verdict config
        if ready_pct == 1.0:
            _vdict_label = "On Track — First-Attempt Pass Likely"
            _vdict_icon  = "✅"
            _vdict_bg    = "#F0FDF4"
            _vdict_col   = "#16A34A"
        elif ready_pct >= 0.66:
            _vdict_label = "Nearly Ready — 1 Remediation Cycle Needed"
            _vdict_icon  = "⚠️"
            _vdict_bg    = "#FFFBEB"
            _vdict_col   = "#D97706"
        else:
            _vdict_label = "Structured Full Prep Recommended"
            _vdict_icon  = "📖"
            _vdict_bg    = "#FFF1F0"
            _vdict_col   = "#DC2626"

        # Top metric row
        _rm1, _rm2, _rm3, _rm4 = st.columns(4)
        with _rm1:
            st.metric("Avg Confidence", f"{avg_conf*100:.0f}%")
        with _rm2:
            st.metric("Domains Ready (≥70%)", f"{ready_domains}/{total_domains}")
        with _rm3:
            _at_risk = len(profile.risk_domains or [])
            st.metric("At-Risk Domains", _at_risk)
        with _rm4:
            st.metric("Study Budget", f"{profile.total_budget_hours:.0f} h")

        # Verdict banner
        _bar_w = int(ready_pct * 100)
        st.markdown(
            f"""<div style="background:{_vdict_bg};border:1.5px solid {_vdict_col};
                 border-radius:10px;padding:14px 18px;margin:10px 0;">
              <div style="font-size:1.05rem;font-weight:700;color:{_vdict_col};">
                {_vdict_icon} {_vdict_label}
              </div>
              <div style="background:#e5e7eb;border-radius:6px;height:10px;margin:10px 0 4px;">
                <div style="background:{_vdict_col};width:{_bar_w}%;height:10px;
                     border-radius:6px;transition:width .4s;"></div>
              </div>
              <div style="font-size:0.78rem;color:#555;">
                {ready_domains} of {total_domains} domains above 70% confidence threshold
              </div>
            </div>""",
            unsafe_allow_html=True,
        )

        # ── Prioritised Study Action Plan ────────────────────────────────────
        st.markdown("##### 🎯 Prioritised Study Action Plan")
        st.caption(
            "Domains ranked by urgency — what to tackle first, with concrete actions "
            "tailored to your learning style and available budget."
        )
        _STUDY_TIPS = {
            "weak":     ("Start from scratch — use official Microsoft Learn modules and take notes.",
                         "📚 Block daily 45-min focus slots. No skipping."),
            "moderate": ("Bridge gaps — review official docs and try 10-question practice drills.",
                         "🔁 Mix reading with practice questions every other day."),
            "strong":   ("Maintain edge — skim official docs and attempt timed mock questions.",
                         "⏱ One timed mock set per week is enough."),
        }
        _PRIORITY_ORDER = [
            (_dp, _dp.domain_id in (profile.risk_domains or []), _dp.domain_id in (profile.modules_to_skip or []))
            for _dp in sorted(profile.domain_profiles, key=lambda d: (
                0 if d.domain_id in (profile.risk_domains or []) else
                (1 if d.confidence_score < 0.50 else
                 (2 if d.confidence_score < 0.70 else
                  (4 if d.domain_id in (profile.modules_to_skip or []) else 3)))
            ))
        ]
        _n_domains = max(len(profile.domain_profiles), 1)
        for _rank, (_pdp, _is_risk_p, _is_skip_p) in enumerate(_PRIORITY_ORDER, 1):
            _lv      = _pdp.knowledge_level.value
            _tip1, _tip2 = _STUDY_TIPS.get(_lv, _STUDY_TIPS["moderate"])
            _pshort  = (_pdp.domain_name
                        .replace("Implement ", "").replace(" Solutions", "")
                        .replace(" & Knowledge Mining", " & KM"))
            # exam_weight_pct is not on DomainProfile; fall back to equal distribution
            _pw_pct  = getattr(_pdp, 'exam_weight_pct', 0) or round(100.0 / _n_domains, 1)
            if _is_skip_p:
                _p_border, _p_bg = "#2563EB", "#EFF6FF"
                _urgency = "⏩ Fast-track — light review only"
            elif _is_risk_p:
                _p_border, _p_bg = "#DC2626", "#FFF1F0"
                _urgency = "🚨 Critical — highest priority"
            elif _pdp.confidence_score < 0.50:
                _p_border, _p_bg = "#D97706", "#FFFBEB"
                _urgency = "⚠️ Below threshold — needs focused time"
            elif _pdp.confidence_score < 0.70:
                _p_border, _p_bg = "#0078D4", "#EFF6FF"
                _urgency = "📈 Building — consolidate with practice"
            else:
                _p_border, _p_bg = "#16A34A", "#F0FDF4"
                _urgency = "✅ Ready — maintain with light review"
            _hrs_suggested = round((_pw_pct / 100) * profile.total_budget_hours)
            st.markdown(
                f"""<div style="background:{_p_bg};border-left:4px solid {_p_border};
                     border-radius:8px;padding:11px 15px;margin-bottom:8px;">
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="font-weight:700;font-size:0.88rem;color:#111;">
                      #{_rank}&nbsp; {_pshort}
                    </span>
                    <span style="font-size:0.75rem;color:{_p_border};font-weight:600;">{_urgency}</span>
                  </div>
                  <div style="font-size:0.78rem;color:#374151;margin-top:5px;">
                    📌 <b>Action:</b> {_tip1}<br/>
                    {_tip2}<br/>
                    ⏱ <b>Suggested budget:</b> ~{_hrs_suggested} h
                    &nbsp;({_pw_pct:.0f}% of exam weight)
                  </div>
                </div>""",
                unsafe_allow_html=True,
            )

        # ── Certification Recommendation Agent ────────────────────────────────
        st.markdown("### 🏅 Exam Booking Guidance")
        _asmt_res = st.session_state.get("assessment_result")
        _prog_asmt = st.session_state.get("progress_assessment")
        _cert_agent = CertificationRecommendationAgent()

        if _asmt_res:
            _cert_rec: CertRecommendation = _cert_agent.recommend(profile, _asmt_res)
            st.session_state["cert_recommendation"] = _cert_rec
        elif _prog_asmt:
            _cert_rec: CertRecommendation = _cert_agent.recommend_from_readiness(profile, _prog_asmt)
            st.session_state["cert_recommendation"] = _cert_rec
        else:
            _cert_rec = None

        if _cert_rec:
            _go_c = "#16a34a" if _cert_rec.go_for_exam else "#dc2626"
            _go_bg = "#f0fdf4" if _cert_rec.go_for_exam else "#fff1f0"
            st.markdown(
                f"""<div style="background:{_go_bg};border:2px solid {_go_c};border-radius:10px;
                     padding:14px 18px;margin-bottom:14px;">
                  <div style="font-size:1.2rem;font-weight:800;color:{_go_c};">
                    {"✅ Ready to Book the Exam!" if _cert_rec.go_for_exam else "📖 More Preparation Needed"}
                  </div>
                  <div style="color:#374151;margin-top:4px;font-size:0.9rem;">{_cert_rec.summary}</div>
                </div>""",
                unsafe_allow_html=True,
            )

            if _cert_rec.exam_info:
                ei = _cert_rec.exam_info
                _ec1, _ec2, _ec3, _ec4 = st.columns(4)
                with _ec1: st.metric("Exam Code", ei.exam_code)
                with _ec2: st.metric("Passing Score", f"{ei.passing_score}/1000")
                with _ec3: st.metric("Duration", f"{ei.duration_minutes} min")
                with _ec4: st.metric("Cost", f"USD {ei.cost_usd}")
                st.markdown(
                    f"""<div class="card card-blue" style="margin-top:8px;">
                      <b>Exam:</b> {ei.exam_name}<br/>
                      <b>Format:</b> {ei.exam_format}<br/>
                      <b>Online Proctored:</b> {"✅ Yes" if ei.online_proctored else "No"}<br/>
                      <b>Schedule:</b> <a href="{ei.scheduling_url}" target="_blank">Pearson VUE</a> &nbsp;|&nbsp;
                      <b>Free Practice:</b> <a href="{ei.free_practice_url}" target="_blank">Official Practice Assessment</a>
                    </div>""",
                    unsafe_allow_html=True,
                )

            if _cert_rec.booking_checklist:
                st.markdown("#### ✅ Pre-Exam Booking Checklist")
                for _item in _cert_rec.booking_checklist:
                    st.checkbox(_item, key=f"chk_{abs(hash(_item))}")

            if _cert_rec.remediation_plan:
                st.markdown(
                    f'<div class="card card-pink">'
                    f'<b>📋 Remediation Plan</b><br/>{_cert_rec.remediation_plan}</div>',
                    unsafe_allow_html=True,
                )

            if _cert_rec.next_cert_suggestions:
                st.markdown("#### 🚀 Next Certification Recommendations")
                for _nc in _cert_rec.next_cert_suggestions:
                    _diff_c = {"foundational":"#16a34a","intermediate":"#2563eb","advanced":"#7c3aed","expert":"#dc2626"}.get(_nc.difficulty, "#888")
                    st.markdown(
                        f"""<div style="background:white;border:1px solid #e5e7eb;border-left:4px solid {_diff_c};
                             border-radius:8px;padding:12px 16px;margin-bottom:8px;">
                          <div style="font-weight:700;color:#111;font-size:0.96rem;">
                            <a href="{_nc.learn_url}" target="_blank" style="color:{_diff_c};text-decoration:none;">
                              {_nc.exam_code}
                            </a> — {_nc.exam_name}
                            <span style="margin-left:8px;font-size:0.75rem;color:{_diff_c};text-transform:uppercase;">
                              {_nc.difficulty}
                            </span>
                          </div>
                          <div style="color:#555;font-size:0.85rem;margin-top:4px;">{_nc.rationale}</div>
                          {f'<div style="color:#888;font-size:0.78rem;margin-top:3px;">⏱ Est. {_nc.timeline_est}</div>' if _nc.timeline_est else ""}
                        </div>""",
                        unsafe_allow_html=True,
                    )
        else:
            st.info(
                "Complete the **Knowledge Check** quiz or the **My Progress** check-in "
                "to unlock personalised certification booking recommendations.",
                icon="💡",
            )

    # ── Tab 4: My Progress ────────────────────────────────────────────────────
    @st.fragment
    def _render_progress_tab():
        profile = st.session_state.get("profile")
        if profile is None:
            return
        st.markdown('<a href="#" style="font-size:0.75rem;color:#9CA3AF;text-decoration:none;">↑ Back to top</a>', unsafe_allow_html=True)
        st.caption(
            "📈 **My Progress** — track how far you've come. Log the hours you've studied, "
            "modules completed, and practice scores, then get an instant readiness gauge "
            "showing whether you're on track for your exam date."
        )
        st.markdown("### 📈 My Progress Check-In")

        _has_plan = "plan" in st.session_state

        if not _has_plan:
            st.info(
                "Complete the intake form above and generate your learner profile first, "
                "then return here to log your progress and get a readiness assessment.",
                icon="ℹ️",
            )
        else:
            _plan: StudyPlan = st.session_state["plan"]
            _prior_snap = st.session_state.get("progress_snapshot")
            _prior_asmt = st.session_state.get("progress_assessment")

            # Welcome back callout for returning users
            if _prior_asmt:
                _pa: ReadinessAssessment = _prior_asmt
                _c = _pa.verdict_colour
                st.markdown(
                    f"""<div style="background:#f0f0f8;border-left:5px solid {_c};
                         border-radius:8px;padding:10px 16px;margin-bottom:12px;">
                      <b>Last check-in result:</b>
                      <span style="color:{_c};font-size:1.1rem;font-weight:700;margin-left:8px;">
                        {_pa.readiness_pct:.0f}% — {_pa.verdict_label}
                      </span>
                      &nbsp;|&nbsp;
                      <span style="color:{_pa.go_nogo_colour};font-weight:700;">
                        {_pa.exam_go_nogo}
                      </span>
                      <span style="color:#555;font-size:0.85rem;margin-left:8px;">
                        {_pa.hours_remaining:.0f} h remaining · {_pa.weeks_remaining} wk(s) left
                      </span>
                    </div>""",
                    unsafe_allow_html=True,
                )

            # ── Progress Check-In Form ────────────────────────────────────────
            st.markdown("#### ✏️ Log Your Study Session")
            with st.form("progress_form", clear_on_submit=False):
                _pcol1, _pcol2 = st.columns(2)
                with _pcol1:
                    _hours_spent = st.number_input(
                        "Total hours studied so far",
                        min_value=0.0,
                        max_value=float(profile.total_budget_hours * 2),
                        value=float(
                            _prior_snap.total_hours_spent if _prior_snap else 0.0
                        ),
                        step=0.5,
                        help=f"Your full budget is {profile.total_budget_hours:.0f} h",
                    )
                    _weeks_elapsed = st.number_input(
                        "Weeks elapsed since you started",
                        min_value=0,
                        max_value=profile.weeks_available + 4,
                        value=int(
                            _prior_snap.weeks_elapsed if _prior_snap else 0
                        ),
                        step=1,
                    )
                with _pcol2:
                    _prac_opt = st.selectbox(
                        "Have you taken a practice exam?",
                        options=["no", "some", "yes"],
                        index=(
                            ["no","some","yes"].index(_prior_snap.done_practice_exam)
                            if _prior_snap else 0
                        ),
                    )
                    _prac_score = st.number_input(
                        "Practice exam score (%)",
                        min_value=0,
                        max_value=100,
                        value=int(_prior_snap.practice_score_pct or 0)
                              if _prior_snap else 0,
                        step=1,
                        disabled=(_prac_opt == "no"),
                        help="Enter 0 if you haven't done a scored test yet",
                    )

                st.markdown("##### 🎯 Domain Self-Rating")
                st.caption(
                    "Rate your current confidence in each domain: "
                    "1 = barely started, 3 = working knowledge, 5 = very confident."
                )

                _domain_ratings: dict[str, int] = {}
                _prev_ratings = {
                    dp.domain_id: dp.self_rating
                    for dp in _prior_snap.domain_progress
                } if _prior_snap else {}

                _dr_cols = st.columns(2)
                for _di, dp in enumerate(profile.domain_profiles):
                    _short = (dp.domain_name
                              .replace("Implement ", "")
                              .replace(" Solutions", "")
                              .replace(" & Knowledge Mining", " & KM"))
                    with _dr_cols[_di % 2]:
                        _domain_ratings[dp.domain_id] = st.slider(
                            _short,
                            min_value=1,
                            max_value=5,
                            value=_prev_ratings.get(dp.domain_id, max(1, int(dp.confidence_score * 4) + 1)),
                            help=dp.domain_name,
                            key=f"dr_{dp.domain_id}",
                        )

                _notes = st.text_area(
                    "Optional notes / blockers",
                    value=_prior_snap.notes if _prior_snap else "",
                    placeholder="e.g. Struggling with Azure OpenAI RAG patterns, skipped conversational AI docs",
                    height=70,
                )

                _assess_btn = st.form_submit_button(
                    "🔍 Assess My Readiness",
                    type="primary",
                    use_container_width=True,
                )

            # ── Run assessment on submit ──────────────────────────────────────
            if _assess_btn:
                _snap = ProgressSnapshot(
                    total_hours_spent  = _hours_spent,
                    weeks_elapsed      = _weeks_elapsed,
                    domain_progress    = [
                        DomainProgress(
                            domain_id   = dp.domain_id,
                            domain_name = dp.domain_name,
                            self_rating = _domain_ratings[dp.domain_id],
                            hours_spent = 0.0,
                        )
                        for dp in profile.domain_profiles
                    ],
                    done_practice_exam  = _prac_opt,
                    practice_score_pct  = _prac_score if _prac_opt != "no" else None,
                    email               = st.session_state.get("user_email", ""),
                    notes               = _notes,
                )
                with st.spinner("🤖 Progress Agent: computing readiness…"):
                    _asmt = ProgressAgent().assess(profile, _snap)
                st.session_state["progress_snapshot"] = _snap
                st.session_state["progress_assessment"] = _asmt
                # Save progress to DB
                _login_nm = st.session_state.get("login_name", "")
                if _login_nm and _login_nm != "Admin":
                    save_progress(_login_nm, _dc_to_json(_snap), _dc_to_json(_asmt))
                # Update local vars so results render immediately on this pass
                # (avoids st.rerun() which resets the active tab to "Domain Map")
                _prior_snap = _snap
                _prior_asmt = _asmt

            # ── Show assessment results ───────────────────────────────────────
            if _prior_asmt:
                _asmt: ReadinessAssessment = _prior_asmt
                _snap: ProgressSnapshot   = st.session_state["progress_snapshot"]
                st.markdown("---")
                st.markdown("### 🎯 Readiness Assessment")

                # ── GO / NO-GO + gauge side by side ──────────────────────────
                _gc1, _gc2 = st.columns([1, 1])

                with _gc1:
                    # Plotly gauge
                    _gauge = go.Figure(go.Indicator(
                        mode  = "gauge+number+delta",
                        value = _asmt.readiness_pct,
                        delta = {"reference": 75, "valueformat": ".0f",
                                 "increasing": {"color": GREEN},
                                 "decreasing": {"color": "#d13438"}},
                        gauge = {
                            "axis":      {"range": [0, 100], "tickformat": ".0f",
                                          "ticksuffix": "%"},
                            "bar":       {"color": _asmt.verdict_colour, "thickness": 0.25},
                            "steps":     [
                                {"range": [0,  45], "color": "#fde7f3"},
                                {"range": [45, 60], "color": "#fff4ce"},
                                {"range": [60, 75], "color": "#eef6ff"},
                                {"range": [75,100], "color": "#e9f7ee"},
                            ],
                            "threshold": {"line": {"color": "#5c2d91", "width": 3},
                                          "thickness": 0.8, "value": 75},
                        },
                        title = {"text": f"Readiness Score<br><span style='font-size:0.85rem;color:#888;'>"
                                         f"(target ≥ 75%)</span>"},
                        number = {"suffix": "%", "font": {"color": _asmt.verdict_colour, "size": 44}},
                    ))
                    _gauge.update_layout(
                        height=260,
                        margin=dict(t=40, b=10, l=20, r=20),
                        paper_bgcolor="white",
                    )
                    st.plotly_chart(_gauge, use_container_width=True)

                with _gc2:
                    # GO / NO-GO card
                    _gnc = _asmt.go_nogo_colour
                    st.markdown(
                        f"""<div style="border:3px solid {_gnc};border-radius:12px;
                             padding:20px 24px;text-align:center;background:white;
                             box-shadow:0 4px 12px rgba(0,0,0,0.08);margin-top:12px;">
                          <div style="font-size:0.9rem;color:#888;font-weight:600;
                               text-transform:uppercase;letter-spacing:.08em;">Exam Decision</div>
                          <div style="font-size:2.4rem;font-weight:800;color:{_gnc};
                               margin:6px 0;">{_asmt.exam_go_nogo}</div>
                          <div style="font-size:0.88rem;color:#444;line-height:1.5;">
                            {_asmt.go_nogo_reason}
                          </div>
                        </div>""",
                        unsafe_allow_html=True,
                    )

                    # Hours + Weeks KPIs
                    st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
                    _kc1, _kc2 = st.columns(2)
                    with _kc1:
                        st.metric("Hours Spent",
                                  f"{_snap.total_hours_spent:.0f} h",
                                  f"{_asmt.hours_progress_pct:.0f}% of budget")
                    with _kc2:
                        _wrem_delta = f"{_asmt.weeks_remaining} wk(s) left"
                        st.metric("Weeks Elapsed",
                                  f"{_snap.weeks_elapsed} / {profile.weeks_available}",
                                  _wrem_delta)

                # ── Nudge alerts ──────────────────────────────────────────────
                st.markdown("### 🔔 Smart Nudges & Alerts")
                _nudge_style = {
                    NudgeLevel.DANGER:  ("🚨", "#fde7f3", "#d13438"),
                    NudgeLevel.WARNING: ("⚠️", "#fff4ce", "#ca5010"),
                    NudgeLevel.INFO:    ("💡", "#eef6ff", "#0078d4"),
                    NudgeLevel.SUCCESS: ("✅", "#e9f7ee", "#107c10"),
                }
                for _n in _asmt.nudges:
                    _icon, _bg, _border = _nudge_style.get(
                        _n.level, ("ℹ️", "#f5f5f5", "#888")
                    )
                    _msg = (_n.message
                            .replace("**", "<b>", 1).replace("**", "</b>", 1)
                            .replace("**", "<b>", 1).replace("**", "</b>", 1))
                    st.markdown(
                        f"""<div style="background:{_bg};border-left:5px solid {_border};
                             border-radius:8px;padding:12px 16px;margin-bottom:10px;">
                          <b style="color:{_border};">{_icon} {_n.title}</b><br/>
                          <span style="font-size:0.87rem;color:#333;">{_msg}</span>
                        </div>""",
                        unsafe_allow_html=True,
                    )

                # ── Domain status table ───────────────────────────────────────
                st.markdown("### 📊 Domain Progress vs Plan")
                st.caption(
                    "Compares your self-rating today against where you should be "
                    "at this point in your study plan."
                )
                _status_meta = {
                    "ahead":    ("✓ Ahead",    GREEN,    "🟢"),
                    "on_track": ("◑ On Track", BLUE,     "🔵"),
                    "behind":   ("⚠ Behind",   GOLD,     "🟡"),
                    "critical": ("🚨 Critical", "#d13438","🔴"),
                }
                for _ds in _asmt.domain_status:
                    _sl, _sc, _si = _status_meta.get(
                        _ds.status, ("?", "#888", "⚪")
                    )
                    _stars_filled  = "★" * _ds.actual_rating
                    _stars_empty   = "☆" * (5 - _ds.actual_rating)
                    _exp_stars     = "★" * int(round(_ds.expected_rating))
                    _exp_empty     = "☆" * (5 - int(round(_ds.expected_rating)))
                    _short_name    = (_ds.domain_name
                                      .replace("Implement ", "")
                                      .replace(" Solutions", "")
                                      .replace(" & Knowledge Mining", " & KM"))
                    st.markdown(
                        f"""<div style="display:flex;align-items:center;gap:12px;
                             padding:8px 12px;border-radius:8px;margin-bottom:6px;
                             background:white;border:1px solid #eeeeee;
                             border-left:4px solid {_sc};">
                          <span style="font-size:1.1rem;">{_si}</span>
                          <span style="flex:2;font-weight:600;color:#222;">{_short_name}</span>
                          <span style="flex:1;text-align:center;font-size:1rem;color:#f4a523;">
                            {_stars_filled}<span style="color:#ccc;">{_stars_empty}</span>
                            <span style="font-size:0.75rem;color:#888;margin-left:4px;">
                              (you: {_ds.actual_rating})
                            </span>
                          </span>
                          <span style="flex:1;text-align:center;font-size:0.82rem;color:#888;">
                            expected: {_exp_stars}<span style="color:#ccc;">{_exp_empty}</span>
                            ({_ds.expected_rating:.1f})
                          </span>
                          <span style="color:{_sc};font-weight:600;font-size:0.85rem;">{_sl}</span>
                        </div>""",
                        unsafe_allow_html=True,
                    )

                # ── Recommended focus ─────────────────────────────────────────
                if _asmt.recommended_focus:
                    _focus_names = [
                        EXAM_DOMAIN_NAMES.get(did, did)
                        for did in _asmt.recommended_focus
                    ]
                    st.markdown(
                        f"""<div style="background:{PURPLE_LITE};border-left:5px solid {PURPLE};
                             border-radius:8px;padding:10px 16px;margin-top:8px;">
                          <b>🎯 Recommended focus for your next study sessions:</b><br/>
                          {"".join(f"<span style='margin-right:8px;'>&nbsp;• {n}</span>" for n in _focus_names)}
                        </div>""",
                        unsafe_allow_html=True,
                    )

                st.markdown("---")

                # ── Email / Download Weekly Report ───────────────────────────
                st.markdown("### 📧 Weekly Progress Report")
                _email_addr  = st.session_state.get("user_email", "")
                _smtp_cfg_pr = _is_real_value(os.getenv("SMTP_USER", "")) and _is_real_value(os.getenv("SMTP_PASS", ""))

                if _smtp_cfg_pr:
                    _erow1, _erow2, _erow3 = st.columns([2.2, 1.1, 1.1])
                    with _erow1:
                        _send_to = st.text_input(
                            "Send report to",
                            value=_email_addr,
                            placeholder="you@example.com",
                            key="send_email_input",
                            help="Enter your email to receive the weekly progress report with PDF attached.",
                        )
                    with _erow2:
                        st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
                        _do_send = st.button(
                            "📤 Email + PDF",
                            type="primary",
                            use_container_width=True,
                        )
                else:
                    _do_send = False
                    _send_to = ""
                    _erow3, _erow_hint = st.columns([1, 3])
                    with _erow_hint:
                        st.caption("💡 Add SMTP credentials to `.env` to enable email delivery.")
                with _erow3:
                    st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
                    try:
                        _prog_pdf  = _get_or_generate_pdf(
                            st.session_state.get("sidebar_prefill"), "assessment",
                            generate_assessment_pdf, profile, _snap, _asmt,
                        )
                        _prog_fname = f"ProgressReport_{profile.student_name.replace(' ','_')}.pdf"
                        st.download_button(
                            label="⬇️ Download PDF",
                            data=_prog_pdf,
                            file_name=_prog_fname,
                            mime="application/pdf",
                            use_container_width=True,
                        )
                    except Exception as _pe:
                        st.caption(f"PDF error: {_pe}")

                if _do_send:
                    if not _send_to:
                        st.error("Please enter an email address.")
                    else:
                        _html_body = generate_weekly_summary(profile, _snap, _asmt)
                        _subject   = (
                            f"{profile.exam_target} Weekly Study Report — "
                            f"{profile.student_name} — "
                            f"Readiness {_asmt.readiness_pct:.0f}%"
                        )
                        try:
                            _pdf_attach  = _get_or_generate_pdf(
                                st.session_state.get("sidebar_prefill"), "assessment",
                                generate_assessment_pdf, profile, _snap, _asmt,
                            )
                            _pdf_attach_name = f"ProgressReport_{profile.student_name.replace(' ','_')}.pdf"
                        except Exception:
                            _pdf_attach      = None
                            _pdf_attach_name = "ProgressReport.pdf"
                        with st.spinner("Sending email…"):
                            _ok, _msg = attempt_send_email(
                                _send_to, _subject, _html_body,
                                pdf_bytes=_pdf_attach,
                                pdf_filename=_pdf_attach_name,
                            )
                        if _ok:
                            st.success(f"✅ {_msg}")
                        else:
                            st.warning(f"⚠️ Email failed — {_msg}")
                            with st.expander("📄 Preview weekly report email", expanded=True):
                                _html_body = generate_weekly_summary(profile, _snap, _asmt)
                                st.components.v1.html(_html_body, height=520, scrolling=True)

                # Preview (always available)
                with st.expander("👁️ Preview weekly report (no email needed)"):
                    _html_prev = generate_weekly_summary(profile, _snap, _asmt)
                    st.components.v1.html(_html_prev, height=520, scrolling=True)
                    _prev_col1, _prev_col2 = st.columns(2)
                    with _prev_col1:
                        st.download_button(
                            label="⬇️ Download as HTML",
                            data=_html_prev.encode("utf-8"),
                            file_name=f"weekly_report_{profile.student_name.replace(' ','_')}.html",
                            mime="text/html",
                            use_container_width=True,
                        )
                    with _prev_col2:
                        try:
                            _prev_pdf = _get_or_generate_pdf(
                                st.session_state.get("sidebar_prefill"), "assessment",
                                generate_assessment_pdf, profile, _snap, _asmt,
                            )
                            st.download_button(
                                label="⬇️ Download as PDF",
                                data=_prev_pdf,
                                file_name=f"ProgressReport_{profile.student_name.replace(' ','_')}.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                            )
                        except Exception as _prev_pe:
                            st.caption(f"PDF error: {_prev_pe}")

    with tab_progress:
        _render_progress_tab()

    # ── Tab 6: Knowledge Check (Assessment Agent) ────────────────────────────
    @st.fragment
    def _render_quiz_tab():
        profile = st.session_state.get("profile")
        if profile is None:
            st.info(
                "Complete the intake form above and generate your learner profile first, "
                "then return here to test your knowledge.",
                icon="ℹ️",
            )
            return
        st.markdown('<a href="#" style="font-size:0.75rem;color:#9CA3AF;text-decoration:none;">↑ Back to top</a>', unsafe_allow_html=True)
        st.caption(
            "🧪 **Knowledge Check** — test yourself with a short domain-weighted quiz. "
            "Choose how many questions you want, answer them, and get an instant readiness "
            "score. Passing threshold is 60%. Use this to identify any remaining weak spots "
            "before your exam."
        )
        st.markdown("### 🧪 Knowledge Check — Readiness Quiz")

        _q_count = st.slider(
            "Number of questions",
            min_value=5, max_value=30,
            value=st.session_state.get("_quiz_q_count", 10),
            key="_quiz_q_count",
        )

        if st.button("🎲 Generate New Quiz", type="primary"):
            _agent = AssessmentAgent()
            _new_assess = _agent.generate(profile, n_questions=_q_count)
            _gr = GuardrailsPipeline().check_assessment(_new_assess)
            if _gr.blocked:
                for _v in _gr.violations:
                    st.error(f"🚫 Assessment guardrail [{_v.code}]: {_v.message}")
            else:
                st.session_state["assessment"] = _new_assess
                st.session_state.pop("assessment_result", None)  # clear prior result
                st.session_state.pop("assessment_answers", None)
                # fragment reruns automatically — no st.rerun() needed

        _active_assess: Assessment = st.session_state.get("assessment")

        if not _active_assess:
            st.info("Press **Generate New Quiz** to start your knowledge check.", icon="🎲")
        else:
            # If result already exists, show it
            _prior_result: AssessmentResult = st.session_state.get("assessment_result")

            if _prior_result:
                _score  = _prior_result.score_pct
                _passed = _prior_result.passed
                _psc    = "#16a34a" if _passed else "#dc2626"
                st.markdown(
                    f"""<div style="background:{'#f0fdf4' if _passed else '#fff1f0'};border:2px solid {_psc};
                         border-radius:10px;padding:16px 20px;margin-bottom:16px;">
                      <div style="font-size:1.4rem;font-weight:800;color:{_psc};">
                        {'✅ PASSED' if _passed else '❌ NOT PASSED'} — {_score:.0f}%
                        <span style="font-size:0.85rem;color:#888;margin-left:8px;">
                          ({_prior_result.correct_count}/{_prior_result.total_count} correct)
                        </span>
                      </div>
                      <div style="color:#374151;margin-top:6px;font-size:0.9rem;">
                        {_prior_result.verdict}<br/>
                        <b>Next step:</b> {_prior_result.recommendation}
                      </div>
                    </div>""",
                    unsafe_allow_html=True,
                )

                # Domain scores
                st.markdown("#### 📊 Domain Breakdown")
                for _did, _ds in sorted(_prior_result.domain_scores.items(), key=lambda x: x[1]):
                    _dom_col = "#16a34a" if _ds >= 70 else ("#f59e0b" if _ds >= 50 else "#dc2626")
                    _dn = EXAM_DOMAIN_NAMES.get(_did, _did).replace("Implement ", "").replace(" Solutions","")
                    st.markdown(
                        f"""<div style="display:flex;align-items:center;gap:10px;
                             margin-bottom:6px;padding:6px 12px;border-radius:6px;
                             background:white;border:1px solid #e5e7eb;border-left:4px solid {_dom_col};">
                          <span style="flex:2;font-weight:600;color:#111;">{_dn}</span>
                          <span style="flex:1;font-weight:700;color:{_dom_col};">{_ds:.0f}%</span>
                          <span style="color:#888;font-size:0.8rem;">
                            {'✓ Pass' if _ds >= 60 else '✗ Review'}
                          </span>
                        </div>""",
                        unsafe_allow_html=True,
                    )

                # Per-question feedback
                with st.expander("📝 View detailed question feedback"):
                    for _i, (_q, _fb) in enumerate(zip(
                        _active_assess.questions, _prior_result.feedback
                    )):
                        _qc = "#16a34a" if _fb.correct else "#dc2626"
                        _icon = "✅" if _fb.correct else "❌"
                        st.markdown(
                            f"""<div style="border:1px solid {'#bbf7d0' if _fb.correct else '#fca5a5'};
                                 border-radius:8px;padding:12px 16px;margin-bottom:10px;
                                 background:{'#f0fdf4' if _fb.correct else '#fff1f0'};">
                              <b style="color:#111;">{_icon} Q{_i+1}. {_q.question}</b><br/>
                              <span style="color:{_qc};font-size:0.88rem;">
                                You chose: <b>{_q.options[_fb.learner_index]}</b>
                              </span>
                              {'<br/><span style="color:#dc2626;font-size:0.88rem;">Correct: <b>' + _q.options[_q.correct_index] + '</b></span>' if not _fb.correct else ""}
                              <br/><span style="color:#555;font-size:0.83rem;font-style:italic;">
                                {_fb.explanation}
                              </span>
                            </div>""",
                            unsafe_allow_html=True,
                        )

                if st.button("🔄 Retake Quiz", use_container_width=True):
                    st.session_state.pop("assessment_result", None)
                    st.session_state.pop("assessment_answers", None)
                    # fragment reruns automatically — no st.rerun() needed

            else:
                # Show quiz form
                st.markdown(f"#### 📋 Answer the {len(_active_assess.questions)} Questions Below")
                st.markdown(
                    f"""<div class="card card-blue">
                      <b>Exam:</b> {_active_assess.exam_target} &nbsp;|&nbsp;
                      <b>Questions:</b> {_active_assess.total_marks} &nbsp;|&nbsp;
                      <b>Pass mark:</b> {_active_assess.pass_mark_pct:.0f}%
                    </div>""",
                    unsafe_allow_html=True,
                )

                _answers: list[int] = []
                with st.form("quiz_form"):
                    for _qi, _q in enumerate(_active_assess.questions):
                        _opt_letters = ["A", "B", "C", "D"]
                        _domain_short = _q.domain_name.replace("Implement ", "").replace(" Solutions","").replace(" & Knowledge Mining"," & KM")
                        st.markdown(
                            f"""<div style="background:white;border:1px solid #e5e7eb;border-radius:8px;
                                 padding:12px 16px;margin-bottom:4px;">
                              <span style="font-size:0.72rem;color:#6b7280;font-weight:700;text-transform:uppercase;">
                                Q{_qi+1} · {_domain_short} · {_q.difficulty.title()}
                              </span><br/>
                              <b style="color:#111;">{_q.question}</b>
                            </div>""",
                            unsafe_allow_html=True,
                        )
                        _chosen = st.radio(
                            label=f"q{_qi+1}",
                            options=list(range(len(_q.options))),
                            format_func=lambda i, opts=_q.options: opts[i],
                            label_visibility="collapsed",
                            horizontal=False,
                            key=f"q_{_qi}",
                        )
                        _answers.append(_chosen)

                    _submit_quiz = st.form_submit_button(
                        "📤 Submit Answers & Get Score",
                        type="primary",
                        use_container_width=True,
                    )

                if _submit_quiz:
                    _agent2 = AssessmentAgent()
                    _result = _agent2.evaluate(_active_assess, _answers)
                    st.session_state["assessment_result"] = _result
                    st.session_state["assessment_answers"] = _answers
                    # Save to DB
                    _login_nm = st.session_state.get("login_name", "")
                    if _login_nm and _login_nm != "Admin":
                        save_assessment(
                            _login_nm,
                            _dc_to_json(_active_assess),
                            _dc_to_json(_result),
                        )
                    # Clear cert rec so it regenerates
                    st.session_state.pop("cert_recommendation", None)
                    st.rerun()

    with tab_quiz:
        _render_quiz_tab()

    # ── Tab 7: Raw JSON ───────────────────────────────────────────────────────
    with tab_json:
        st.markdown('<a href="#" style="font-size:0.75rem;color:#9CA3AF;text-decoration:none;">↑ Back to top</a>', unsafe_allow_html=True)
        st.caption(
            "📄 **Raw Data** — the full JSON behind your session. Useful for debugging, "
            "sharing your profile with a colleague, or downloading a record of your "
            "assessment for offline review."
        )
        col_j1, col_j2 = st.columns(2)
        with col_j1:
            st.markdown("#### Raw Student Input")
            st.json(_dc.asdict(raw))
        with col_j2:
            st.markdown("#### Generated Learner Profile")
            st.json(profile.model_dump())

        st.download_button(
            label="⬇️ Download profile as JSON",
            data=profile.model_dump_json(indent=2),
            file_name=f"learner_profile_{raw.student_name.replace(' ', '_')}.json",
            mime="application/json",
            width="stretch",
        )
