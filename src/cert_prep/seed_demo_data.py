"""
seed_demo_data.py
─────────────────
Populate the SQLite database with realistic demo student profiles so the
Admin Dashboard shows a varied, convincing cohort beyond the two built-in
scenario personas (Alex Chen + Priyanka Sharma).

Run once (safe to re-run — uses upsert, so existing records are refreshed):
    python -m src.cert_prep.seed_demo_data
or:
    python src/cert_prep/seed_demo_data.py
"""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

# ── Allow running from repo root ──────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.cert_prep.database import (
    upsert_student,
    save_profile,
    save_plan,
    save_progress,
    save_assessment,
)

# ─────────────────────────────────────────────────────────────────────────────
# Helper: tiny builder helpers so the JSON stays readable
# ─────────────────────────────────────────────────────────────────────────────

def _domain(
    domain_id: str,
    domain_name: str,
    knowledge_level: str,
    confidence_score: float,
    skip_recommended: bool,
    notes: str,
) -> dict:
    return {
        "domain_id": domain_id,
        "domain_name": domain_name,
        "knowledge_level": knowledge_level,
        "confidence_score": confidence_score,
        "skip_recommended": skip_recommended,
        "notes": notes,
    }


def _task(
    domain_id: str,
    domain_name: str,
    start_week: int,
    end_week: int,
    total_hours: float,
    priority: str,
    knowledge_level: str,
    confidence_pct: int,
) -> dict:
    return {
        "domain_id": domain_id,
        "domain_name": domain_name,
        "start_week": start_week,
        "end_week": end_week,
        "total_hours": total_hours,
        "priority": priority,
        "knowledge_level": knowledge_level,
        "confidence_pct": confidence_pct,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Student 1 — Marcus Johnson  (AZ-204 · Developer · mid-progress)
# ─────────────────────────────────────────────────────────────────────────────
def seed_marcus():
    name = "Marcus Johnson"
    exam = "AZ-204"
    upsert_student(name)

    profile = {
        "student_name": name,
        "exam_target": exam,
        "experience_level": "intermediate",
        "learning_style": "lab_first",
        "hours_per_week": 9.0,
        "weeks_available": 10,
        "total_budget_hours": 90.0,
        "domain_profiles": [
            _domain("compute_solutions",        "Develop Azure Compute Solutions",   "moderate", 0.62, False,
                    "Has deployed App Service apps; limited AKS/containers experience."),
            _domain("azure_storage",            "Develop for Azure Storage",         "strong",   0.78, True,
                    "Works with Blob + Cosmos DB daily — can move through quickly."),
            _domain("azure_security",           "Implement Azure Security",          "weak",     0.35, False,
                    "Managed Identity and Key Vault are listed as concern topics."),
            _domain("monitoring_optimize",      "Monitor, Troubleshoot & Optimize",  "moderate", 0.55, False,
                    "Uses App Insights but unfamiliar with advanced alerting and Redis."),
            _domain("azure_services_integration","Connect & Consume Azure Services",  "weak",     0.40, False,
                    "Event Grid and Service Bus are new territory."),
        ],
        "modules_to_skip": ["Blob storage basics", "Cosmos DB introduction"],
        "risk_domains": ["azure_security", "azure_services_integration"],
        "analogy_map": {
            "AWS Lambda": "Azure Functions",
            "AWS IAM": "Microsoft Entra ID + RBAC",
            "AWS SQS/SNS": "Azure Service Bus / Event Grid",
        },
        "recommended_approach": textwrap.dedent("""\
            Marcus is a mid-level developer comfortable with Azure basics but needing
            focused depth on security and messaging. Prioritise hands-on labs for
            Key Vault, Managed Identity and Service Bus before moving to integration patterns.
            Storage domains can be covered at light review pace."""),
        "engagement_notes": "Developer mindset — prefer code-first tasks. Weekly lab challenges keep momentum.",
    }

    plan = {
        "student_name": name,
        "exam_target": exam,
        "total_weeks": 10,
        "total_hours": 90.0,
        "tasks": [
            _task("compute_solutions",         "Develop Azure Compute Solutions",    1, 3, 25.0, "critical",  "moderate", 62),
            _task("azure_storage",             "Develop for Azure Storage",          2, 3, 10.0, "low",       "strong",   78),
            _task("azure_security",            "Implement Azure Security",           3, 6, 24.0, "critical",  "weak",     35),
            _task("monitoring_optimize",       "Monitor, Troubleshoot & Optimize",   6, 8, 16.0, "high",      "moderate", 55),
            _task("azure_services_integration","Connect & Consume Azure Services",   7, 9, 15.0, "high",      "weak",     40),
        ],
        "review_start_week": 9,
        "prerequisites": [
            {"cert_code": "AZ-900", "cert_name": "Azure Fundamentals", "relationship": "helpful", "already_held": True}
        ],
        "prereq_gap": False,
        "prereq_message": "AZ-900 is held. No major prerequisite gaps.",
        "plan_summary": textwrap.dedent("""\
            10-week plan front-loading compute and security depth.
            Storage domains leverage existing strength and are time-boxed.
            Final 2 weeks reserved for integration patterns and full practice tests."""),
    }

    snapshot = {
        "student_name": name,
        "exam_target": exam,
        "week_number": 6,
        "domain_scores": {
            "compute_solutions":         0.71,
            "azure_storage":             0.82,
            "azure_security":            0.54,
            "monitoring_optimize":       0.61,
            "azure_services_integration": 0.46,
        },
        "readiness_pct": 65,
        "hours_logged": 52,
        "hours_remaining": 38,
    }

    assessment = {
        "student_name": name,
        "exam_target": exam,
        "readiness_pct": 65,
        "exam_go_nogo": "CONDITIONAL GO",
        "weak_area_flags": ["azure_security", "azure_services_integration"],
        "recommendation": textwrap.dedent("""\
            On track overall but security and integration domains need 2 more focused weeks.
            Schedule 2 practice exams before the final week."""),
    }

    quiz_result = {
        "student_name": name,
        "exam_target": exam,
        "score_pct": 63,
        "pass_threshold": 70,
        "passed": False,
        "weak_areas": ["azure_security", "azure_services_integration"],
        "strong_areas": ["azure_storage"],
    }

    save_profile(name, json.dumps(profile), json.dumps({"student_name": name, "exam": exam}), exam)
    save_plan(name, json.dumps(plan))
    save_progress(name, json.dumps(snapshot), json.dumps(assessment))
    save_assessment(name, json.dumps({"questions_attempted": 30}), json.dumps(quiz_result))
    print(f"  ✅ {name} ({exam}) — seeded")


# ─────────────────────────────────────────────────────────────────────────────
# Student 2 — Sarah Williams  (AI-900 · Fundamentals · nearly done · GO)
# ─────────────────────────────────────────────────────────────────────────────
def seed_sarah():
    name = "Sarah Williams"
    exam = "AI-900"
    upsert_student(name)

    profile = {
        "student_name": name,
        "exam_target": exam,
        "experience_level": "beginner",
        "learning_style": "linear",
        "hours_per_week": 5.0,
        "weeks_available": 6,
        "total_budget_hours": 30.0,
        "domain_profiles": [
            _domain("ai_workloads",      "AI Workloads & Considerations",           "moderate", 0.70, False,
                    "Business analyst background gives good conceptual grounding for AI workloads."),
            _domain("ml_fundamentals",   "Machine Learning Fundamentals on Azure",  "weak",     0.45, False,
                    "No ML hands-on yet; needs conceptual walkthroughs on Azure ML Studio."),
            _domain("cv_fundamentals",   "Computer Vision Workloads",               "moderate", 0.66, False,
                    "Familiar with image classification concepts from a coursework project."),
            _domain("nlp_fundamentals",  "Natural Language Processing Workloads",   "moderate", 0.72, True,
                    "Daily NLP tool usage at work — solid intuition for sentiment and NER."),
            _domain("genai_fundamentals","Generative AI Workloads",                 "moderate", 0.68, False,
                    "Active Copilot user; understands prompting at surface level."),
        ],
        "modules_to_skip": ["Azure Language Service overview (covered by NLP strength)"],
        "risk_domains": ["ml_fundamentals"],
        "analogy_map": {
            "Business Intelligence reports": "Azure AI insights + AutoML",
        },
        "recommended_approach": textwrap.dedent("""\
            Sarah is a business analyst pivoting towards AI awareness.
            Linear study path through official learn modules works well.
            ML fundamentals are the only notable gap — one focused deep-dive week should close it."""),
        "engagement_notes": "Short, structured daily sessions fit her schedule. Mobile-friendly content preferred.",
    }

    plan = {
        "student_name": name,
        "exam_target": exam,
        "total_weeks": 6,
        "total_hours": 30.0,
        "tasks": [
            _task("ai_workloads",      "AI Workloads & Considerations",           1, 1, 5.0, "medium",  "moderate", 70),
            _task("ml_fundamentals",   "Machine Learning Fundamentals on Azure",  2, 3, 8.0, "critical","weak",     45),
            _task("cv_fundamentals",   "Computer Vision Workloads",               3, 4, 5.0, "medium",  "moderate", 66),
            _task("nlp_fundamentals",  "Natural Language Processing Workloads",   4, 4, 3.0, "low",     "moderate", 72),
            _task("genai_fundamentals","Generative AI Workloads",                 4, 5, 7.0, "high",    "moderate", 68),
        ],
        "review_start_week": 6,
        "prerequisites": [],
        "prereq_gap": False,
        "prereq_message": "AI-900 has no formal prerequisites. No gap identified.",
        "plan_summary": textwrap.dedent("""\
            Compact 6-week plan suited for a busy professional.
            ML fundamentals front-loaded in weeks 2–3 to eliminate the main risk domain early.
            Week 6 reserved for two timed practice tests and light review."""),
    }

    snapshot = {
        "student_name": name,
        "exam_target": exam,
        "week_number": 5,
        "domain_scores": {
            "ai_workloads":      0.82,
            "ml_fundamentals":   0.71,
            "cv_fundamentals":   0.77,
            "nlp_fundamentals":  0.85,
            "genai_fundamentals":0.79,
        },
        "readiness_pct": 82,
        "hours_logged": 26,
        "hours_remaining": 4,
    }

    assessment = {
        "student_name": name,
        "exam_target": exam,
        "readiness_pct": 82,
        "exam_go_nogo": "GO",
        "weak_area_flags": [],
        "recommendation": "Strong readiness across all domains. One final practice test recommended before exam day.",
    }

    quiz_result = {
        "student_name": name,
        "exam_target": exam,
        "score_pct": 84,
        "pass_threshold": 70,
        "passed": True,
        "weak_areas": [],
        "strong_areas": ["nlp_fundamentals", "ai_workloads"],
    }

    save_profile(name, json.dumps(profile), json.dumps({"student_name": name, "exam": exam}), exam)
    save_plan(name, json.dumps(plan))
    save_progress(name, json.dumps(snapshot), json.dumps(assessment))
    save_assessment(name, json.dumps({"questions_attempted": 40}), json.dumps(quiz_result))
    print(f"  ✅ {name} ({exam}) — seeded")


# ─────────────────────────────────────────────────────────────────────────────
# Student 3 — David Kim  (AZ-305 · Architect · early stage · NOT YET)
# ─────────────────────────────────────────────────────────────────────────────
def seed_david():
    name = "David Kim"
    exam = "AZ-305"
    upsert_student(name)

    profile = {
        "student_name": name,
        "exam_target": exam,
        "experience_level": "advanced_azure",
        "learning_style": "reference",
        "hours_per_week": 7.0,
        "weeks_available": 14,
        "total_budget_hours": 98.0,
        "domain_profiles": [
            _domain("identity_governance",    "Design Identity, Governance & Monitoring", "strong",   0.80, True,
                    "10+ years Azure admin; strong Entra ID, Policy and RBAC background."),
            _domain("data_storage_solutions", "Design Data Storage Solutions",            "moderate", 0.58, False,
                    "Comfortable with SQL and Blob; Cosmos DB consistency models are a gap."),
            _domain("business_continuity",    "Design Business Continuity Solutions",     "weak",     0.38, False,
                    "Has not designed formal DR strategies — Site Recovery is new."),
            _domain("infrastructure_solutions","Design Infrastructure Solutions",          "moderate", 0.55, False,
                    "Strong on compute/networking; microservices and API Management need depth."),
        ],
        "modules_to_skip": [
            "Entra ID fundamentals",
            "Azure Policy basics",
            "RBAC introduction",
        ],
        "risk_domains": ["business_continuity", "data_storage_solutions"],
        "analogy_map": {
            "On-prem DR with Veeam": "Azure Site Recovery + Backup",
            "RabbitMQ": "Azure Service Bus",
        },
        "recommended_approach": textwrap.dedent("""\
            David is a seasoned Azure admin transitioning to architecture-level thinking.
            Identity and governance domains can be reviewed quickly to bank easy marks.
            Main investment should go into business continuity, Cosmos DB design, and
            microservices / API Management patterns."""),
        "engagement_notes": "Reference learner — concise architecture decision guides and Well-Architected Framework tabs work best.",
    }

    plan = {
        "student_name": name,
        "exam_target": exam,
        "total_weeks": 14,
        "total_hours": 98.0,
        "tasks": [
            _task("identity_governance",    "Design Identity, Governance & Monitoring", 1,  2, 10.0, "low",      "strong",   80),
            _task("data_storage_solutions", "Design Data Storage Solutions",            2,  7, 30.0, "critical", "moderate", 58),
            _task("business_continuity",    "Design Business Continuity Solutions",     5,  9, 24.0, "critical", "weak",     38),
            _task("infrastructure_solutions","Design Infrastructure Solutions",          8, 12, 28.0, "high",     "moderate", 55),
        ],
        "review_start_week": 12,
        "prerequisites": [
            {"cert_code": "AZ-104", "cert_name": "Azure Administrator Associate",
             "relationship": "strongly_recommended", "already_held": True},
        ],
        "prereq_gap": False,
        "prereq_message": "AZ-104 already held. Strongly recommended prereq satisfied.",
        "plan_summary": textwrap.dedent("""\
            14-week plan for an experienced Azure admin targeting the architect exam.
            Identity governance is a quick sweep in week 1.
            Weeks 2–12 focus on data design, DR strategies and infrastructure architecture.
            Open-book architecture reviews and Well-Architected Framework deep-dives throughout."""),
    }

    snapshot = {
        "student_name": name,
        "exam_target": exam,
        "week_number": 3,
        "domain_scores": {
            "identity_governance":    0.85,
            "data_storage_solutions": 0.44,
            "business_continuity":    0.28,
            "infrastructure_solutions": 0.42,
        },
        "readiness_pct": 49,
        "hours_logged": 21,
        "hours_remaining": 77,
    }

    assessment = {
        "student_name": name,
        "exam_target": exam,
        "readiness_pct": 49,
        "exam_go_nogo": "NOT YET",
        "weak_area_flags": ["business_continuity", "data_storage_solutions", "infrastructure_solutions"],
        "recommendation": textwrap.dedent("""\
            Too early to schedule the exam. Business continuity and data storage require
            significant additional study. Re-assess at week 9 for a GO/CONDITIONAL GO decision."""),
    }

    save_profile(name, json.dumps(profile), json.dumps({"student_name": name, "exam": exam}), exam)
    save_plan(name, json.dumps(plan))
    save_progress(name, json.dumps(snapshot), json.dumps(assessment))
    print(f"  ✅ {name} ({exam}) — seeded (no quiz yet, early stage)")


# ─────────────────────────────────────────────────────────────────────────────
# Student 4 — Fatima Al-Rashid  (AI-102 · Expert ML background · GO)
# ─────────────────────────────────────────────────────────────────────────────
def seed_fatima():
    name = "Fatima Al-Rashid"
    exam = "AI-102"
    upsert_student(name)

    profile = {
        "student_name": name,
        "exam_target": exam,
        "experience_level": "expert_ml",
        "learning_style": "adaptive",
        "hours_per_week": 12.0,
        "weeks_available": 7,
        "total_budget_hours": 84.0,
        "domain_profiles": [
            _domain("plan_manage",         "Plan & Manage Azure AI Solutions",               "strong",   0.82, True,
                    "MLOps background gives excellent grounding in responsible AI and monitoring."),
            _domain("computer_vision",     "Implement Computer Vision Solutions",            "strong",   0.88, True,
                    "Published CV research; highly familiar with classification, OCR, detection."),
            _domain("nlp",                 "Implement NLP Solutions",                        "strong",   0.85, True,
                    "NLP is her primary domain — transformer models, CLU, summarisation."),
            _domain("document_intelligence","Implement Document Intelligence & Knowledge Mining","moderate",0.60, False,
                    "Document Intelligence forms and Cognitive Search indexers are less familiar."),
            _domain("conversational_ai",   "Implement Conversational AI Solutions",          "weak",     0.42, False,
                    "Bot Service and Adaptive Dialogs are new; Power Virtual Agents is a gap."),
            _domain("generative_ai",       "Implement Generative AI Solutions",              "strong",   0.91, True,
                    "Prompt engineering and RAG patterns are central to her current role."),
        ],
        "modules_to_skip": [
            "Azure AI Vision overview",
            "NLP fundamentals",
            "Responsible AI principles overview",
            "Azure OpenAI introduction",
        ],
        "risk_domains": ["conversational_ai"],
        "analogy_map": {
            "Hugging Face pipelines": "Azure AI Language service",
            "LangChain RAG": "Azure AI Search + Azure OpenAI RAG pattern",
            "AWS Lex": "Azure Bot Service + CLU",
        },
        "recommended_approach": textwrap.dedent("""\
            Fatima is an expert ML engineer with primarily Python and open-source tooling.
            Most Azure AI service domains can be self-assessed quickly via practise questions.
            Focus study time on Conversational AI and Document Intelligence —
            the only two domains below 70% confidence. 4 weeks should suffice."""),
        "engagement_notes": "Fast learner — allow self-pacing with challenge-based labs. Daily quick quizzes to identify remaining gaps.",
    }

    plan = {
        "student_name": name,
        "exam_target": exam,
        "total_weeks": 7,
        "total_hours": 84.0,
        "tasks": [
            _task("plan_manage",          "Plan & Manage Azure AI Solutions",                1, 1,  8.0, "low",      "strong",   82),
            _task("computer_vision",      "Implement Computer Vision Solutions",             1, 2,  9.0, "low",      "strong",   88),
            _task("nlp",                  "Implement NLP Solutions",                         2, 2,  7.0, "low",      "strong",   85),
            _task("document_intelligence","Implement Document Intelligence & Knowledge Mining",2, 4, 20.0, "high",     "moderate", 60),
            _task("conversational_ai",    "Implement Conversational AI Solutions",           3, 6, 28.0, "critical", "weak",     42),
            _task("generative_ai",        "Implement Generative AI Solutions",               5, 6,  8.0, "low",      "strong",   91),
        ],
        "review_start_week": 7,
        "prerequisites": [
            {"cert_code": "AI-900", "cert_name": "Azure AI Fundamentals",
             "relationship": "helpful", "already_held": True},
        ],
        "prereq_gap": False,
        "prereq_message": "AI-900 held. Expert ML background satisfies all implicit prerequisites.",
        "plan_summary": textwrap.dedent("""\
            Expert-accelerated 7-week plan. Strong domains are covered in rapid review sprints.
            Conversational AI gets the lion's share of focused time (weeks 3–6).
            Document Intelligence follows a structured lab sequence.
            Week 7 reserved for two timed mock exams."""),
    }

    snapshot = {
        "student_name": name,
        "exam_target": exam,
        "week_number": 6,
        "domain_scores": {
            "plan_manage":         0.88,
            "computer_vision":     0.92,
            "nlp":                 0.89,
            "document_intelligence": 0.73,
            "conversational_ai":   0.71,
            "generative_ai":       0.94,
        },
        "readiness_pct": 86,
        "hours_logged": 74,
        "hours_remaining": 10,
    }

    assessment = {
        "student_name": name,
        "exam_target": exam,
        "readiness_pct": 86,
        "exam_go_nogo": "GO",
        "weak_area_flags": [],
        "recommendation": "Excellent readiness. All domains above 70%. One final timed mock exam recommended.",
    }

    quiz_result = {
        "student_name": name,
        "exam_target": exam,
        "score_pct": 88,
        "pass_threshold": 70,
        "passed": True,
        "weak_areas": [],
        "strong_areas": ["generative_ai", "computer_vision", "nlp"],
    }

    save_profile(name, json.dumps(profile), json.dumps({"student_name": name, "exam": exam}), exam)
    save_plan(name, json.dumps(plan))
    save_progress(name, json.dumps(snapshot), json.dumps(assessment))
    save_assessment(name, json.dumps({"questions_attempted": 45}), json.dumps(quiz_result))
    print(f"  ✅ {name} ({exam}) — seeded")


# ─────────────────────────────────────────────────────────────────────────────
# Student 5 — Jordan Baptiste  (DP-100 · Intermediate · mid-progress)
# ─────────────────────────────────────────────────────────────────────────────
def seed_jordan():
    name = "Jordan Baptiste"
    exam = "DP-100"
    upsert_student(name)

    profile = {
        "student_name": name,
        "exam_target": exam,
        "experience_level": "intermediate",
        "learning_style": "lab_first",
        "hours_per_week": 8.0,
        "weeks_available": 10,
        "total_budget_hours": 80.0,
        "domain_profiles": [
            _domain("ml_solution_design",  "Design & Prepare an ML Solution",    "moderate", 0.60, False,
                    "Has used Azure ML workspace but never set up compute clusters or datastores from scratch."),
            _domain("explore_train_models","Explore Data & Train Models",         "strong",   0.79, False,
                    "Experienced pandas/sklearn user; AutoML is new but understandable."),
            _domain("prepare_deployment",  "Prepare a Model for Deployment",      "weak",     0.40, False,
                    "MLflow logging is new; deployment packaging scripts not practiced."),
            _domain("deploy_retrain",      "Deploy & Retrain a Model",            "weak",     0.35, False,
                    "Online/batch endpoints, monitoring and drift detection are completely new."),
        ],
        "modules_to_skip": [],
        "risk_domains": ["deploy_retrain", "prepare_deployment"],
        "analogy_map": {
            "scikit-learn Pipeline": "Azure ML Pipeline + Environment",
            "MLflow local tracking": "Azure ML MLflow remote tracking",
        },
        "recommended_approach": textwrap.dedent("""\
            Jordan is a strong data scientist who needs to shift from local experimentation
            to full cloud MLOps. Weeks 1–4 consolidate Azure ML workspace fundamentals.
            Weeks 5–9 prioritise deployment and retraining pipelines — the main exam differentiators."""),
        "engagement_notes": "Lab-first approach: each concept should be followed immediately by an Azure ML notebook walkthrough.",
    }

    plan = {
        "student_name": name,
        "exam_target": exam,
        "total_weeks": 10,
        "total_hours": 80.0,
        "tasks": [
            _task("ml_solution_design",  "Design & Prepare an ML Solution",    1, 3, 18.0, "high",     "moderate", 60),
            _task("explore_train_models","Explore Data & Train Models",         2, 5, 22.0, "medium",   "strong",   79),
            _task("prepare_deployment",  "Prepare a Model for Deployment",      5, 7, 18.0, "critical", "weak",     40),
            _task("deploy_retrain",      "Deploy & Retrain a Model",            7, 9, 18.0, "critical", "weak",     35),
        ],
        "review_start_week": 10,
        "prerequisites": [
            {"cert_code": "DP-900", "cert_name": "Azure Data Fundamentals",
             "relationship": "helpful", "already_held": False},
        ],
        "prereq_gap": True,
        "prereq_message": "DP-900 is helpful but not required. Consider 3h self-study on Azure data services basics.",
        "plan_summary": textwrap.dedent("""\
            10-week plan for a data scientist pivoting to Azure ML at scale.
            First half builds workspace and experimentation fluency.
            Second half focuses entirely on MLOps: model packaging, deployment, monitoring and retraining."""),
    }

    snapshot = {
        "student_name": name,
        "exam_target": exam,
        "week_number": 5,
        "domain_scores": {
            "ml_solution_design":   0.69,
            "explore_train_models": 0.80,
            "prepare_deployment":   0.44,
            "deploy_retrain":       0.31,
        },
        "readiness_pct": 58,
        "hours_logged": 38,
        "hours_remaining": 42,
    }

    assessment = {
        "student_name": name,
        "exam_target": exam,
        "readiness_pct": 58,
        "exam_go_nogo": "NOT YET",
        "weak_area_flags": ["prepare_deployment", "deploy_retrain"],
        "recommendation": textwrap.dedent("""\
            On pace for training-side topics but deployment pipeline work must be completed.
            Re-assess at week 8 — expect CONDITIONAL GO if labs are completed."""),
    }

    save_profile(name, json.dumps(profile), json.dumps({"student_name": name, "exam": exam}), exam)
    save_plan(name, json.dumps(plan))
    save_progress(name, json.dumps(snapshot), json.dumps(assessment))
    print(f"  ✅ {name} ({exam}) — seeded (no quiz yet)")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🌱 Seeding demo students…")
    seed_marcus()
    seed_sarah()
    seed_david()
    seed_fatima()
    seed_jordan()
    print("\n✅ All demo students seeded successfully.")
    print("   Open the Admin Dashboard to verify the cohort table.")
