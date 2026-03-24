"""
Smoke tests for config / settings loading.
Run: python -m pytest tests/ -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cert_prep.config import get_settings, _is_placeholder


class TestIsPlaceholder:
    def test_empty_string_is_placeholder(self):
        assert _is_placeholder("")

    def test_angle_bracket_is_placeholder(self):
        assert _is_placeholder("<your-key-here>")

    def test_your_prefix_is_placeholder(self):
        assert _is_placeholder("your-endpoint")

    def test_literal_PLACEHOLDER_is_placeholder(self):
        assert _is_placeholder("PLACEHOLDER")

    def test_real_value_not_placeholder(self):
        assert not _is_placeholder("https://my-resource.openai.azure.com")

    def test_real_key_not_placeholder(self):
        assert not _is_placeholder("abc123defgh456ijkl789mnop")


class TestSettingsLoading:
    def test_get_settings_returns_object(self):
        s = get_settings()
        assert s is not None
        assert hasattr(s, "openai")
        assert hasattr(s, "app")

    def test_force_mock_defaults_false(self):
        """FORCE_MOCK_MODE should default to False when env var is absent."""
        os.environ.pop("FORCE_MOCK_MODE", None)
        s = get_settings()
        assert not s.app.force_mock_mode

    def test_live_mode_false_without_credentials(self):
        """live_mode should be False when OpenAI creds are placeholders."""
        os.environ.pop("AZURE_OPENAI_ENDPOINT", None)
        os.environ.pop("AZURE_OPENAI_API_KEY", None)
        s = get_settings()
        assert not s.live_mode

    def test_status_summary_keys(self):
        s = get_settings()
        summary = s.status_summary()
        assert any("openai" in k.lower() or "OpenAI" in k for k in summary)
        assert any("safety" in k.lower() or "Safety" in k for k in summary)
        assert any("comm" in k.lower() or "Comm" in k for k in summary)
        assert any("mcp" in k.lower() or "Learn" in k for k in summary)
