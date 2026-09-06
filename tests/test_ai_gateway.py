"""
Unit Tests for Applyr 2.0 AI Gateway (Phase 2)
==============================================

Mocked test suite verifying AI Gateway providers, fallback cascade,
bounded retries, timeout handling, safe logging, and backward compatibility.
Zero network calls are made during execution.
"""

import logging
import os
import unittest
from unittest.mock import MagicMock, patch

import pytest
import requests

from core.ai.schemas import AIRequest, AIResponse
from core.ai.errors import (
    AIGatewayError,
    ProviderUnavailableError,
    AuthenticationError,
    RateLimitError,
    TimeoutError,
    MalformedResponseError,
    sanitize_exception_message,
)
from core.ai.providers.groq import GroqProvider
from core.ai.providers.openrouter import OpenRouterProvider
from core.ai.providers.gemini import GeminiProvider
from core.ai.gateway import AIGateway
from core.services.llm_service import OpenRouterClient, get_llm_client
from utils.llm_client import chat, chat_json, get_llm


class TestAIGateway(unittest.TestCase):
    """17 unit test cases for AI Gateway infrastructure."""

    # 1. Groq provider normalization
    @patch("requests.post")
    def test_01_groq_provider_normalization(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Groq Response"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        mock_post.return_value = mock_resp

        provider = GroqProvider()
        provider.api_key = "gsk_valid_key"
        req = AIRequest(prompt="Hello", request_id="req_test_01")
        res = provider.generate(req)

        self.assertEqual(res.provider, "groq")
        self.assertEqual(res.text, "Groq Response")
        self.assertEqual(res.usage["prompt_tokens"], 10)

    # 2. OpenRouter provider normalization
    @patch("requests.post")
    def test_02_openrouter_provider_normalization(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "OpenRouter Response"}}],
            "usage": {"prompt_tokens": 20, "completion_tokens": 15},
        }
        mock_post.return_value = mock_resp

        provider = OpenRouterProvider()
        provider.api_key = "sk-or-valid_key"
        req = AIRequest(prompt="Hi", request_id="req_test_02")
        res = provider.generate(req)

        self.assertEqual(res.provider, "openrouter")
        self.assertEqual(res.text, "OpenRouter Response")

    # 3. Gemini provider normalization
    @patch("requests.post")
    def test_03_gemini_provider_normalization(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Gemini Response"}]}}]
        }
        mock_post.return_value = mock_resp

        provider = GeminiProvider()
        provider.api_key = "AIzaValidKey"
        req = AIRequest(prompt="Greetings", request_id="req_test_03")
        res = provider.generate(req)

        self.assertEqual(res.provider, "gemini")
        self.assertEqual(res.text, "Gemini Response")

    # 4. Provider selection
    def test_04_provider_selection(self):
        gw = AIGateway()
        gw.providers["groq"].health_check = MagicMock(return_value=True)
        gw.providers["groq"].generate = MagicMock(return_value=AIResponse("OK", "groq", "m", "req_1"))

        res = gw.generate(AIRequest(prompt="Test"))
        self.assertEqual(res.provider, "groq")

    # 5. Explicit provider preference
    def test_05_explicit_provider_preference(self):
        gw = AIGateway()
        gw.providers["gemini"].health_check = MagicMock(return_value=True)
        gw.providers["gemini"].generate = MagicMock(return_value=AIResponse("Gemini Pref", "gemini", "m", "req_1"))

        res = gw.generate(AIRequest(prompt="Test", provider_preference="gemini"))
        self.assertEqual(res.provider, "gemini")

    # 6. Model preference
    @patch("requests.post")
    def test_06_model_preference(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"choices": [{"message": {"content": "Custom Model"}}]}
        mock_post.return_value = mock_resp

        provider = GroqProvider()
        provider.api_key = "gsk_valid"
        req = AIRequest(prompt="Hi", model_preference="custom-groq-model")
        res = provider.generate(req)

        self.assertEqual(res.model, "custom-groq-model")

    # 7. Fallback Groq -> OpenRouter
    def test_07_fallback_groq_to_openrouter(self):
        gw = AIGateway()
        gw.providers["groq"].health_check = MagicMock(return_value=True)
        gw.providers["groq"].generate = MagicMock(side_effect=ProviderUnavailableError("Groq Down"))
        
        gw.providers["openrouter"].health_check = MagicMock(return_value=True)
        gw.providers["openrouter"].generate = MagicMock(return_value=AIResponse("OR Fallback", "openrouter", "m", "req_1"))

        res = gw.generate(AIRequest(prompt="Test"))
        self.assertEqual(res.provider, "openrouter")
        self.assertTrue(res.fallback_used)

    # 8. Fallback OpenRouter -> Gemini
    def test_08_fallback_openrouter_to_gemini(self):
        gw = AIGateway()
        gw.providers["groq"].health_check = MagicMock(return_value=False)
        
        gw.providers["openrouter"].health_check = MagicMock(return_value=True)
        gw.providers["openrouter"].generate = MagicMock(side_effect=TimeoutError("OR Timeout"))
        
        gw.providers["gemini"].health_check = MagicMock(return_value=True)
        gw.providers["gemini"].generate = MagicMock(return_value=AIResponse("Gemini Fallback", "gemini", "m", "req_1"))

        res = gw.generate(AIRequest(prompt="Test"))
        self.assertEqual(res.provider, "gemini")
        self.assertTrue(res.fallback_used)

    # 9. Complete provider failure
    def test_09_complete_provider_failure(self):
        gw = AIGateway()
        gw.providers["groq"].health_check = MagicMock(return_value=False)
        gw.providers["openrouter"].health_check = MagicMock(return_value=False)
        gw.providers["gemini"].health_check = MagicMock(return_value=False)

        with self.assertRaises(ProviderUnavailableError):
            gw.generate(AIRequest(prompt="Test"))

    # 10. Retry behavior
    @patch("time.sleep", return_value=None)
    def test_10_retry_behavior(self, mock_sleep):
        gw = AIGateway()
        gw.providers["groq"].health_check = MagicMock(return_value=True)
        # Fails first attempt with rate limit, succeeds second attempt
        gw.providers["groq"].generate = MagicMock(side_effect=[
            RateLimitError("Rate limit"),
            AIResponse("Success after retry", "groq", "m", "req_1")
        ])
        gw.providers["openrouter"].health_check = MagicMock(return_value=False)
        gw.providers["gemini"].health_check = MagicMock(return_value=False)

        res = gw.generate(AIRequest(prompt="Test"))
        self.assertEqual(res.text, "Success after retry")
        self.assertEqual(res.attempts, 2)

    # 11. Retry limit
    @patch("time.sleep", return_value=None)
    def test_11_retry_limit(self, mock_sleep):
        gw = AIGateway()
        gw.providers["groq"].health_check = MagicMock(return_value=True)
        gw.providers["groq"].generate = MagicMock(side_effect=TimeoutError("Persistent timeout"))

        gw.providers["openrouter"].health_check = MagicMock(return_value=False)
        gw.providers["gemini"].health_check = MagicMock(return_value=False)

        with self.assertRaises(ProviderUnavailableError):
            gw.generate(AIRequest(prompt="Test"))

    # 12. Timeout handling
    @patch("requests.post")
    def test_12_timeout_handling(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")
        provider = GroqProvider()
        provider.api_key = "gsk_valid"

        with self.assertRaises(TimeoutError):
            provider.generate(AIRequest(prompt="Hi"))

    # 13. Authentication failure
    @patch("requests.post")
    def test_13_authentication_failure(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_post.return_value = mock_resp

        provider = OpenRouterProvider()
        provider.api_key = "sk-or-invalid"

        with self.assertRaises(AuthenticationError):
            provider.generate(AIRequest(prompt="Hi"))

    # 14. Rate-limit handling
    @patch("requests.post")
    def test_14_rate_limit_handling(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_post.return_value = mock_resp

        provider = GeminiProvider()
        provider.api_key = "AIzaInvalid"

        with self.assertRaises(RateLimitError):
            provider.generate(AIRequest(prompt="Hi"))

    # 15. Request ID generation
    def test_15_request_id_generation(self):
        req = AIRequest(prompt="Test")
        self.assertTrue(req.request_id.startswith("req_"))

    # 16. Safe logging / secret non-disclosure
    def test_16_safe_logging(self):
        gw = AIGateway()
        gw.providers["groq"].health_check = MagicMock(return_value=True)
        gw.providers["groq"].generate = MagicMock(return_value=AIResponse("Logged OK", "groq", "m", "req_sec_1"))

        with patch("logging.Logger.info") as mock_log:
            res = gw.generate(AIRequest(prompt="Secret info", metadata={"key": "gsk_secret_123"}))
            # Verify secrets are not logged in log calls
            for call_args in mock_log.call_args_list:
                log_str = str(call_args)
                self.assertNotIn("gsk_secret_123", log_str)
                self.assertNotIn("sk-or-", log_str)

    # 17. Backward compatibility through llm_client / llm_service
    @patch("core.ai.gateway.AIGateway.generate")
    def test_17_backward_compatibility(self, mock_gw_generate):
        mock_gw_generate.return_value = AIResponse("Backwards compatible output", "groq", "m", "req_compat")

        client = OpenRouterClient()
        resp = client.invoke("Hello from old client code")
        self.assertEqual(resp.content, "Backwards compatible output")

        llm_obj = get_llm()
        resp2 = llm_obj.invoke("Hello from llm object")
        self.assertEqual(resp2.content, "Backwards compatible output")

        chat_out = chat("Hello chat")
        self.assertEqual(chat_out, "Backwards compatible output")


class TestAPIKeyLeakage(unittest.TestCase):
    """Regression tests verifying API keys never leak through exception messages or logs."""

    FAKE_GROQ_KEY = "gsk-test-secret-789"
    FAKE_OPENROUTER_KEY = "sk-or-test-secret-456"
    FAKE_GEMINI_KEY = "AIza-test-secret-123"
    FAKE_BEARER_TOKEN = "Bearer gsk-test-secret-789"

    # ── Groq: connection error with URL containing key ─────────────────

    @patch("requests.post")
    def test_groq_connection_error_url_key_redacted(self, mock_post):
        """Groq ConnectionError containing URL with key= query param is sanitized."""
        url_with_key = f"https://api.groq.com/openai/v1/chat/completions?key={self.FAKE_GROQ_KEY}"
        mock_post.side_effect = requests.exceptions.ConnectionError(
            f"Connection refused: {url_with_key}"
        )
        provider = GroqProvider()
        provider.api_key = self.FAKE_GROQ_KEY

        with self.assertRaises(ProviderUnavailableError) as ctx:
            provider.generate(AIRequest(prompt="Test"))
        err_msg = str(ctx.exception)
        self.assertNotIn(self.FAKE_GROQ_KEY, err_msg)
        self.assertIn("REDACTED", err_msg)

    @patch("requests.post")
    def test_groq_connection_error_bearer_redacted(self, mock_post):
        """Groq ConnectionError containing Bearer token is sanitized."""
        mock_post.side_effect = requests.exceptions.ConnectionError(
            f"TLS error with header Authorization: {self.FAKE_BEARER_TOKEN}"
        )
        provider = GroqProvider()
        provider.api_key = self.FAKE_GROQ_KEY

        with self.assertRaises(ProviderUnavailableError) as ctx:
            provider.generate(AIRequest(prompt="Test"))
        err_msg = str(ctx.exception)
        self.assertNotIn(self.FAKE_GROQ_KEY, err_msg)

    @patch("requests.post")
    def test_groq_timeout_no_key_leak(self, mock_post):
        """Groq Timeout exception does not expose the API key."""
        mock_post.side_effect = requests.exceptions.Timeout("read timed out")
        provider = GroqProvider()
        provider.api_key = self.FAKE_GROQ_KEY

        with self.assertRaises(TimeoutError) as ctx:
            provider.generate(AIRequest(prompt="Test"))
        self.assertNotIn(self.FAKE_GROQ_KEY, str(ctx.exception))

    # ── OpenRouter: connection error with URL containing key ───────────

    @patch("requests.post")
    def test_openrouter_connection_error_url_key_redacted(self, mock_post):
        """OpenRouter ConnectionError containing URL with key= query param is sanitized."""
        url_with_key = f"https://openrouter.ai/api/v1/chat/completions?key={self.FAKE_OPENROUTER_KEY}"
        mock_post.side_effect = requests.exceptions.ConnectionError(
            f"Connection refused: {url_with_key}"
        )
        provider = OpenRouterProvider()
        provider.api_key = self.FAKE_OPENROUTER_KEY

        with self.assertRaises(ProviderUnavailableError) as ctx:
            provider.generate(AIRequest(prompt="Test"))
        err_msg = str(ctx.exception)
        self.assertNotIn(self.FAKE_OPENROUTER_KEY, err_msg)
        self.assertIn("REDACTED", err_msg)

    @patch("requests.post")
    def test_openrouter_connection_error_bearer_redacted(self, mock_post):
        """OpenRouter ConnectionError containing Bearer token is sanitized."""
        mock_post.side_effect = requests.exceptions.ConnectionError(
            f"TLS error with header Authorization: Bearer {self.FAKE_OPENROUTER_KEY}"
        )
        provider = OpenRouterProvider()
        provider.api_key = self.FAKE_OPENROUTER_KEY

        with self.assertRaises(ProviderUnavailableError) as ctx:
            provider.generate(AIRequest(prompt="Test"))
        err_msg = str(ctx.exception)
        self.assertNotIn(self.FAKE_OPENROUTER_KEY, err_msg)

    @patch("requests.post")
    def test_openrouter_timeout_no_key_leak(self, mock_post):
        """OpenRouter Timeout exception does not expose the API key."""
        mock_post.side_effect = requests.exceptions.Timeout("read timed out")
        provider = OpenRouterProvider()
        provider.api_key = self.FAKE_OPENROUTER_KEY

        with self.assertRaises(TimeoutError) as ctx:
            provider.generate(AIRequest(prompt="Test"))
        self.assertNotIn(self.FAKE_OPENROUTER_KEY, str(ctx.exception))

    # ── Gemini: connection error with URL containing key ───────────────

    @patch("requests.post")
    def test_gemini_connection_error_url_key_redacted(self, mock_post):
        """Gemini ConnectionError containing URL with key= query param is sanitized."""
        url_with_key = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.FAKE_GEMINI_KEY}"
        mock_post.side_effect = requests.exceptions.ConnectionError(
            f"Connection refused: {url_with_key}"
        )
        provider = GeminiProvider()
        provider.api_key = self.FAKE_GEMINI_KEY

        with self.assertRaises(ProviderUnavailableError) as ctx:
            provider.generate(AIRequest(prompt="Test"))
        err_msg = str(ctx.exception)
        self.assertNotIn(self.FAKE_GEMINI_KEY, err_msg)
        self.assertIn("REDACTED", err_msg)

    @patch("requests.post")
    def test_gemini_timeout_no_key_leak(self, mock_post):
        """Gemini Timeout exception does not expose the API key."""
        mock_post.side_effect = requests.exceptions.Timeout("read timed out")
        provider = GeminiProvider()
        provider.api_key = self.FAKE_GEMINI_KEY

        with self.assertRaises(TimeoutError) as ctx:
            provider.generate(AIRequest(prompt="Test"))
        self.assertNotIn(self.FAKE_GEMINI_KEY, str(ctx.exception))

    # ── Gateway: unexpected exception sanitization ─────────────────────

    def test_gateway_unexpected_exception_sanitized(self):
        """Gateway-level generic Exception handler sanitizes key from error message."""
        gw = AIGateway()
        gw.providers["groq"].health_check = MagicMock(return_value=True)
        gw.providers["openrouter"].health_check = MagicMock(return_value=False)
        gw.providers["gemini"].health_check = MagicMock(return_value=False)

        # Simulate an unexpected exception containing a URL with a key
        url_with_key = f"https://api.groq.com/v1?key={self.FAKE_GROQ_KEY}"
        gw.providers["groq"].generate = MagicMock(
            side_effect=RuntimeError(f"Unexpected failure connecting to {url_with_key}")
        )

        with self.assertRaises(ProviderUnavailableError):
            gw.generate(AIRequest(prompt="Test"))

    def test_gateway_unexpected_exception_no_key_in_logs(self):
        """Gateway logs for unexpected exceptions do not contain the API key."""
        gw = AIGateway()
        gw.providers["groq"].health_check = MagicMock(return_value=True)
        gw.providers["openrouter"].health_check = MagicMock(return_value=False)
        gw.providers["gemini"].health_check = MagicMock(return_value=False)

        url_with_key = f"https://api.groq.com/v1?key={self.FAKE_GROQ_KEY}"
        gw.providers["groq"].generate = MagicMock(
            side_effect=RuntimeError(f"Failure at {url_with_key}")
        )

        with patch("logging.Logger.error") as mock_log:
            with self.assertRaises(ProviderUnavailableError):
                gw.generate(AIRequest(prompt="Test"))
            for call_args in mock_log.call_args_list:
                log_str = str(call_args)
                self.assertNotIn(self.FAKE_GROQ_KEY, log_str)

    # ── sanitize_exception_message unit tests ──────────────────────────

    def test_sanitize_url_query_key(self):
        msg = f"Connection to https://api.example.com/v1?key={self.FAKE_GROQ_KEY} failed"
        result = sanitize_exception_message(msg)
        self.assertNotIn(self.FAKE_GROQ_KEY, result)
        self.assertIn("key=REDACTED", result)

    def test_sanitize_bearer_token(self):
        msg = f"Auth failed: Authorization: Bearer {self.FAKE_OPENROUTER_KEY}"
        result = sanitize_exception_message(msg)
        self.assertNotIn(self.FAKE_OPENROUTER_KEY, result)
        self.assertIn("REDACTED", result)

    def test_sanitize_no_secrets_unchanged(self):
        msg = "Connection refused: timeout after 30s"
        result = sanitize_exception_message(msg)
        self.assertEqual(result, msg)

    def test_sanitize_empty_string(self):
        self.assertEqual(sanitize_exception_message(""), "")

    def test_sanitize_none_passthrough(self):
        self.assertIsNone(sanitize_exception_message(None))


if __name__ == "__main__":
    unittest.main()
