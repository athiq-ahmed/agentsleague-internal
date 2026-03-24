"""
Smoke tests for guardrails pipeline.
Run: python -m pytest tests/ -v
"""
import io
import json
import sys
import os
import unittest.mock as mock

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cert_prep.guardrails import (
    OutputContentGuardrails,
    InputGuardrails,
    GuardrailLevel,
)
from cert_prep.models import RawStudentInput


class TestG16PiiPatterns:
    """G-16: PII detection should WARN (not block)."""

    def setup_method(self):
        self.guard = OutputContentGuardrails()

    def test_ssn_detected(self):
        result = self.guard.check_text(
            "My SSN is 123-45-6789 and I have 5 years exp.", "background_text"
        )
        pii_violations = [v for v in result.violations if v.code == "G-16"]
        assert pii_violations, "SSN should trigger G-16 PII violation"
        assert pii_violations[0].level == GuardrailLevel.WARN

    def test_credit_card_detected(self):
        result = self.guard.check_text(
            "Card: 4111 1111 1111 1111 — please ignore.", "background_text"
        )
        pii_violations = [v for v in result.violations if v.code == "G-16"]
        assert pii_violations, "Credit card should trigger G-16 PII violation"

    def test_email_detected(self):
        result = self.guard.check_text(
            "I'm jane.doe@company.com, senior engineer.", "background_text"
        )
        pii_violations = [v for v in result.violations if v.code == "G-16"]
        assert pii_violations, "Email address should trigger G-16 PII violation"

    def test_phone_detected(self):
        result = self.guard.check_text(
            "Call me at (555) 867-5309 anytime.", "background_text"
        )
        pii_violations = [v for v in result.violations if v.code == "G-16"]
        assert pii_violations, "Phone number should trigger G-16 PII violation"

    def test_ip_detected(self):
        result = self.guard.check_text(
            "My dev machine is at 192.168.1.42.", "background_text"
        )
        pii_violations = [v for v in result.violations if v.code == "G-16"]
        assert pii_violations, "IP address should trigger G-16 PII violation"

    def test_clean_text_no_pii(self):
        result = self.guard.check_text(
            "I am a software engineer with 8 years of Python and Azure experience.",
            "background_text",
        )
        pii_violations = [v for v in result.violations if v.code == "G-16"]
        assert not pii_violations, "Clean professional bio should not trigger PII"

    def test_pii_does_not_block(self):
        """PII should warn but not halt the pipeline."""
        result = self.guard.check_text("SSN: 987-65-4321", "background_text")
        assert not result.blocked, "PII alone should NOT set blocked=True"


class TestG16HarmfulPatterns:
    """G-16: Harmful content should BLOCK the pipeline."""

    def setup_method(self):
        self.guard = OutputContentGuardrails()

    def test_harmful_content_blocks(self):
        result = self.guard.check_text(
            "I want to hack the exam system.", "background_text"
        )
        harmful = [
            v
            for v in result.violations
            if v.code == "G-16" and v.level == GuardrailLevel.BLOCK
        ]
        assert harmful or result.blocked, "Harmful keyword should trigger BLOCK"

    def test_clean_exam_language_not_blocked(self):
        """Common exam idioms must not be false-positives."""
        result = self.guard.check_text(
            "I want to ace the AI-102 exam and crush my certification goals.",
            "background_text",
        )
        assert not result.blocked, "Positive exam language should not be blocked"


class TestInputGuardrailsPiiScan:
    """G-16 PII scan at InputGuardrails.check() level."""

    def test_pii_in_background_text_warns(self):
        raw = RawStudentInput(
            student_name="Test User",
            exam_target="AI-102",
            background_text="Hello, my SSN is 123-45-6789.",
            existing_certs=[],
            hours_per_week=10.0,
            weeks_available=8,
            concern_topics=[],
            preferred_style="videos",
            goal_text="I want to pass AI-102.",
        )
        ig = InputGuardrails()
        result = ig.check(raw)
        pii_v = [v for v in result.violations if v.code == "G-16"]
        assert pii_v, "G-16 should surface PII violation from background_text"

    def test_clean_input_passes(self):
        raw = RawStudentInput(
            student_name="Test User",
            exam_target="AI-102",
            background_text="I am a cloud engineer with Azure experience.",
            existing_certs=[],
            hours_per_week=10.0,
            weeks_available=8,
            concern_topics=[],
            preferred_style="videos",
            goal_text="I want to pass AI-102.",
        )
        ig = InputGuardrails()
        result = ig.check(raw)
        pii_v = [v for v in result.violations if v.code == "G-16"]
        assert not pii_v, "Clean background text should produce no G-16 violations"


class TestLanguagePiiApi:
    """G-16 Layer 3: Azure AI Language PII Entity Recognition (live mode)."""

    def setup_method(self):
        self.guard = OutputContentGuardrails()

    def _fake_response(self, entities: list) -> mock.MagicMock:
        """Return a mock urlopen context manager with given entity list."""
        body = json.dumps({
            "results": {
                "documents": [{"id": "1", "entities": entities, "redactedText": ""}],
                "errors": [],
            }
        }).encode()
        ctx = mock.MagicMock()
        ctx.__enter__ = mock.Mock(return_value=ctx)
        ctx.__exit__  = mock.Mock(return_value=False)
        ctx.read     = mock.Mock(return_value=body)
        return ctx

    def test_no_violations_when_env_vars_missing(self):
        """Without AZURE_LANGUAGE_ENDPOINT/KEY the method returns empty."""
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("AZURE_LANGUAGE_ENDPOINT", None)
            os.environ.pop("AZURE_LANGUAGE_KEY", None)
            viols = self.guard._check_language_pii_api(
                "My SSN is 123-45-6789", "background_text", "Your Background"
            )
        assert viols == [], "No violations expected when env vars absent"

    def test_ssn_entity_produces_warn(self):
        """A high-confidence SSN entity returned by the API → G-16 WARN."""
        entities = [{"text": "123-45-6789", "category": "USSocialSecurityNumber",
                     "confidenceScore": 0.92}]
        env = {"AZURE_LANGUAGE_ENDPOINT": "https://fake.cognitiveservices.azure.com",
               "AZURE_LANGUAGE_KEY": "fakekey123"}
        with mock.patch.dict(os.environ, env):
            with mock.patch("urllib.request.urlopen", return_value=self._fake_response(entities)):
                viols = self.guard._check_language_pii_api(
                    "My SSN is 123-45-6789", "background_text", "Your Background"
                )
        assert len(viols) == 1
        assert viols[0].level.value == "WARN"
        assert viols[0].code == "G-16"
        assert "Social Security Number" in viols[0].message
        assert "92%" in viols[0].message

    def test_low_confidence_entity_skipped(self):
        """Entities with confidence < 0.5 should not generate violations."""
        entities = [{"text": "123-45-6789", "category": "USSocialSecurityNumber",
                     "confidenceScore": 0.30}]
        env = {"AZURE_LANGUAGE_ENDPOINT": "https://fake.cognitiveservices.azure.com",
               "AZURE_LANGUAGE_KEY": "fakekey123"}
        with mock.patch.dict(os.environ, env):
            with mock.patch("urllib.request.urlopen", return_value=self._fake_response(entities)):
                viols = self.guard._check_language_pii_api(
                    "Some text", "background_text", "Background"
                )
        assert viols == [], "Low-confidence entity should be silently skipped"

    def test_api_error_returns_empty(self):
        """Network / API failure should return [] without raising."""
        env = {"AZURE_LANGUAGE_ENDPOINT": "https://fake.cognitiveservices.azure.com",
               "AZURE_LANGUAGE_KEY": "fakekey123"}
        with mock.patch.dict(os.environ, env):
            with mock.patch("urllib.request.urlopen", side_effect=OSError("timeout")):
                viols = self.guard._check_language_pii_api(
                    "My SSN is 123-45-6789", "background_text", "Background"
                )
        assert viols == [], "API error should be swallowed, not raised"

    def test_multiple_categories_deduplicated(self):
        """Two entities with the same category → only one violation."""
        entities = [
            {"text": "123-45-6789", "category": "USSocialSecurityNumber", "confidenceScore": 0.90},
            {"text": "987-65-4321", "category": "USSocialSecurityNumber", "confidenceScore": 0.85},
            {"text": "4111111111111111", "category": "CreditCardNumber", "confidenceScore": 0.95},
        ]
        env = {"AZURE_LANGUAGE_ENDPOINT": "https://fake.cognitiveservices.azure.com",
               "AZURE_LANGUAGE_KEY": "fakekey123"}
        with mock.patch.dict(os.environ, env):
            with mock.patch("urllib.request.urlopen", return_value=self._fake_response(entities)):
                viols = self.guard._check_language_pii_api(
                    "text", "background_text", "Background"
                )
        cats = [v.message for v in viols]
        # SSN deduplicated → 1 SSN + 1 CC = 2 violations only
        assert len(viols) == 2

    def test_check_text_live_mode_includes_language_api_warns(self):
        """check_text(use_live=True) with Language API wired returns G-16 WARNs."""
        entities = [{"text": "jane@example.com", "category": "Email",
                     "confidenceScore": 0.99}]
        env = {
            "AZURE_LANGUAGE_ENDPOINT": "https://fake.cognitiveservices.azure.com",
            "AZURE_LANGUAGE_KEY": "fakekey123",
            "AZURE_CONTENT_SAFETY_ENDPOINT": "",
            "AZURE_CONTENT_SAFETY_KEY": "",
        }
        with mock.patch.dict(os.environ, env):
            # Content Safety endpoint empty → falls back to regex harmful check only
            # Language API → returns email entity
            with mock.patch("urllib.request.urlopen", return_value=self._fake_response(entities)):
                result = self.guard.check_text(
                    "Contact me at jane@example.com", "background_text",
                    use_live=True
                )
        lang_warns = [v for v in result.violations
                      if "Azure AI Language" in v.message and v.code == "G-16"]
        assert lang_warns, "check_text in live mode should surface Language API PII warns"
