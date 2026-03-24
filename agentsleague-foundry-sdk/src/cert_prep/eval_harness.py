"""
eval_harness.py — azure-ai-evaluation SDK integration                   T-09
============================================================================
Uses the ``azure-ai-evaluation`` SDK to run LLM-as-judge quality metrics
against ``LearnerProfilingAgent`` outputs **without** any manual labelling.

Three metrics are measured per run:

  Coherence   — logical flow and readability of the recommendation text
  Relevance   — how well the recommendation addresses the student's background
  Fluency     — grammar, language quality, and natural phrasing

Evaluation strategy
-------------------
  query    = background_text + " Goal: " + goal_text
             (what the student told us about themselves)
  response = recommended_approach + "\\n\\n" + engagement_notes
             (what the profiling agent produced)

The judge model is the same Azure OpenAI deployment used by the main app
(``AZURE_OPENAI_DEPLOYMENT`` env-var, usually ``gpt-4o``), so no extra
Azure resource is required.

Graceful degradation
--------------------
  * Package not installed        → ``EvalResult`` with ``available=False``
  * Credentials not configured   → ``EvalResult`` with ``available=False``
  * Individual evaluator failure → that metric stored as ``None``

Public API
----------
  EvalResult                   dataclass; one instance per profiling run
  evaluate_profile(raw, profile) → EvalResult
  batch_evaluate(pairs)          → list[EvalResult]
  is_eval_available()            → bool  (quick pre-flight check)

Usage (called from streamlit_app.py after LearnerProfilingAgent completes)
--------------------------------------------------------------------------
  from src.cert_prep.eval_harness import evaluate_profile, is_eval_available

  if is_eval_available():
      eval_result = evaluate_profile(raw_input, learner_profile)
      st.session_state["eval_result"] = eval_result
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.cert_prep.models import LearnerProfile, RawStudentInput

logger = logging.getLogger(__name__)

# ─── Try to import azure-ai-evaluation (optional dependency) ─────────────────

_EVAL_SDK_AVAILABLE = False
try:
    from azure.ai.evaluation import (  # type: ignore[import]
        CoherenceEvaluator,
        RelevanceEvaluator,
        FluencyEvaluator,
    )
    _EVAL_SDK_AVAILABLE = True
except ImportError:
    logger.debug(
        "azure-ai-evaluation not installed — eval harness disabled. "
        "Run: pip install azure-ai-evaluation>=1.0.0"
    )


# ─── Result type ─────────────────────────────────────────────────────────────

@dataclass
class EvalResult:
    """
    Quality scores for a single ``LearnerProfilingAgent`` output.

    All metric fields are ``None`` when the evaluator failed or was skipped.
    Check ``available`` first; if ``False``, all scores will be ``None``.
    """
    student_name:  str
    exam_target:   str

    # LLM-as-judge scores (1–5 scale from azure-ai-evaluation)
    coherence:  Optional[float] = None
    relevance:  Optional[float] = None
    fluency:    Optional[float] = None

    # Meta
    available:  bool = True          # False when SDK/creds missing
    error:      Optional[str] = None # human-readable reason if available=False
    raw_scores: dict = field(default_factory=dict)  # full evaluator output

    @property
    def mean_score(self) -> Optional[float]:
        """Average of all non-None scores; None if none available."""
        scores = [s for s in (self.coherence, self.relevance, self.fluency)
                  if s is not None]
        return sum(scores) / len(scores) if scores else None

    def passed_threshold(self, threshold: float = 3.0) -> bool:
        """Return True if mean_score >= threshold (default 3/5 = 60 %)."""
        ms = self.mean_score
        return ms is not None and ms >= threshold


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _build_model_config() -> Optional[dict]:
    """
    Build the model configuration dict that azure-ai-evaluation evaluators
    expect.  Returns ``None`` if required environment variables are missing.
    """
    endpoint    = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    api_key     = os.getenv("AZURE_OPENAI_API_KEY", "")
    deployment  = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

    if not endpoint or not api_key:
        return None

    return {
        "azure_endpoint":    endpoint,
        "api_key":           api_key,
        "azure_deployment":  deployment,
        "api_version":       api_version,
    }


def _build_query_response(raw, profile) -> tuple[str, str]:
    """
    Construct (query, response) strings for the evaluators.

    query    = student's self-description + goal  (the "question" we asked)
    response = agent's recommendation text         (the "answer" we're judging)
    """
    query = (
        f"Student background: {raw.background_text.strip()} "
        f"Goal: {raw.goal_text.strip()} "
        f"Exam target: {raw.exam_target}."
    )
    response = (
        f"{profile.recommended_approach.strip()}\n\n"
        f"{profile.engagement_notes.strip()}"
    )
    return query, response


def _unavailable(student_name: str, exam_target: str, reason: str) -> EvalResult:
    """Return a stub EvalResult indicating eval was skipped."""
    logger.info("Eval harness skipped: %s", reason)
    return EvalResult(
        student_name=student_name,
        exam_target=exam_target,
        available=False,
        error=reason,
    )


# ─── Public API ───────────────────────────────────────────────────────────────

def is_eval_available() -> bool:
    """
    Quick pre-flight check.  Returns ``True`` only when:
      1. ``azure-ai-evaluation`` package is installed, AND
      2. ``AZURE_OPENAI_ENDPOINT`` + ``AZURE_OPENAI_API_KEY`` env-vars are set.
    """
    if not _EVAL_SDK_AVAILABLE:
        return False
    return _build_model_config() is not None


def evaluate_profile(raw, profile) -> EvalResult:
    """
    Run Coherence, Relevance, and Fluency evaluators against a
    ``LearnerProfilingAgent`` output.

    Parameters
    ----------
    raw : RawStudentInput
        The original intake form data.
    profile : LearnerProfile
        The profiling agent's output to evaluate.

    Returns
    -------
    EvalResult
        Populated with per-metric scores.  ``available=False`` if the SDK or
        credentials are not configured.
    """
    if not _EVAL_SDK_AVAILABLE:
        return _unavailable(
            raw.student_name, raw.exam_target,
            "azure-ai-evaluation package not installed"
        )

    model_config = _build_model_config()
    if model_config is None:
        return _unavailable(
            raw.student_name, raw.exam_target,
            "AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY not configured"
        )

    query, response = _build_query_response(raw, profile)
    result = EvalResult(student_name=raw.student_name, exam_target=raw.exam_target)
    raw_scores: dict = {}

    # ── Coherence ────────────────────────────────────────────────────────────
    try:
        evaluator = CoherenceEvaluator(model_config)
        out = evaluator(query=query, response=response)
        raw_scores["coherence"] = out
        result.coherence = float(out.get("coherence", out.get("score", 0)))
        logger.debug("Coherence score for %s: %.2f", raw.student_name, result.coherence)
    except Exception as exc:  # noqa: BLE001
        logger.warning("CoherenceEvaluator failed: %s", exc)

    # ── Relevance ────────────────────────────────────────────────────────────
    try:
        evaluator = RelevanceEvaluator(model_config)
        out = evaluator(query=query, response=response)
        raw_scores["relevance"] = out
        result.relevance = float(out.get("relevance", out.get("score", 0)))
        logger.debug("Relevance score for %s: %.2f", raw.student_name, result.relevance)
    except Exception as exc:  # noqa: BLE001
        logger.warning("RelevanceEvaluator failed: %s", exc)

    # ── Fluency ──────────────────────────────────────────────────────────────
    try:
        evaluator = FluencyEvaluator(model_config)
        out = evaluator(query=query, response=response)
        raw_scores["fluency"] = out
        result.fluency = float(out.get("fluency", out.get("score", 0)))
        logger.debug("Fluency score for %s: %.2f", raw.student_name, result.fluency)
    except Exception as exc:  # noqa: BLE001
        logger.warning("FluencyEvaluator failed: %s", exc)

    result.raw_scores = raw_scores
    logger.info(
        "Eval complete for %s (%s): coherence=%.2f relevance=%.2f fluency=%.2f mean=%.2f",
        raw.student_name, raw.exam_target,
        result.coherence or 0,
        result.relevance or 0,
        result.fluency or 0,
        result.mean_score or 0,
    )
    return result


def batch_evaluate(pairs: list[tuple]) -> list[EvalResult]:
    """
    Evaluate a list of (RawStudentInput, LearnerProfile) pairs.

    This is useful for bulk regression testing — e.g. run all demo personas
    through the profiling agent and check that mean scores stay above a
    threshold after each code change.

    Parameters
    ----------
    pairs : list[tuple[RawStudentInput, LearnerProfile]]

    Returns
    -------
    list[EvalResult]
        One ``EvalResult`` per input pair, in the same order.
    """
    return [evaluate_profile(raw, profile) for raw, profile in pairs]
