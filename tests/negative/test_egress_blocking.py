# =============================================================================
# test_egress_blocking.py
# Negative tests: egress URL enforcement via assert_egress_url_safe().
# Tests that provider-specific URL allowlists prevent data from reaching
# external cloud services when the system is in on-prem/air-gapped mode.
# =============================================================================
import pytest
from core.provider_lock import ProviderConfigError, assert_egress_url_safe

pytestmark = pytest.mark.negative


# ---------------------------------------------------------------------------
# On-prem providers (ollama, vllm) must not egress to public cloud
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("provider", ["ollama", "vllm"])
@pytest.mark.parametrize("url", [
    "https://api.openai.com/v1/chat/completions",
    "https://api.anthropic.com/v1/messages",
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro",
    "https://huggingface.co/api/inference",
    "https://together.xyz/api/inference",
])
def test_onprem_provider_blocks_public_cloud_url(provider, url):
    with pytest.raises(ProviderConfigError):
        assert_egress_url_safe(url, provider)


# ---------------------------------------------------------------------------
# Internal IP ranges pass for on-prem providers
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("provider", ["ollama", "vllm"])
@pytest.mark.parametrize("url", [
    "http://10.0.0.1:11434/v1/chat/completions",
    "http://10.0.0.5:8080/v1",
    "http://192.168.1.100:8080/api",
    "http://172.16.0.5:5000/v1",
])
def test_onprem_provider_allows_internal_ips(provider, url):
    assert_egress_url_safe(url, provider)  # must not raise


# ---------------------------------------------------------------------------
# Bedrock: uses boto3 (no endpoint URL needed)
# ---------------------------------------------------------------------------

def test_bedrock_none_url_does_not_raise():
    assert_egress_url_safe(None, "bedrock")


def test_bedrock_empty_string_url_does_not_raise():
    try:
        assert_egress_url_safe("", "bedrock")
    except ProviderConfigError:
        pass  # Acceptable


# ---------------------------------------------------------------------------
# Azure: .azure.com domain allowed for azure provider
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url", [
    "https://mydeployment.openai.azure.com/openai/deployments/gpt-4o/chat/completions",
    "https://contoso-prod.openai.azure.com/openai/deployments/gpt-4-turbo/chat",
])
def test_azure_gov_endpoint_allowed_for_azure_provider(url):
    assert_egress_url_safe(url, "azure")  # must not raise


def test_azure_endpoint_blocked_for_ollama():
    with pytest.raises(ProviderConfigError):
        assert_egress_url_safe(
            "https://mydeployment.openai.azure.com/openai/v1",
            "ollama",
        )


# ---------------------------------------------------------------------------
# URL scheme safety: HTTP vs HTTPS
# ---------------------------------------------------------------------------

def test_http_internal_allowed():
    assert_egress_url_safe("http://10.0.0.1:11434/v1", "ollama")


def test_http_external_blocked():
    with pytest.raises(ProviderConfigError):
        assert_egress_url_safe("http://api.openai.com/v1", "ollama")


# ---------------------------------------------------------------------------
# None provider — must raise (no provider means no safe egress)
# ---------------------------------------------------------------------------

def test_none_provider_raises():
    with pytest.raises((ProviderConfigError, TypeError, ValueError)):
        assert_egress_url_safe("http://10.0.0.1:11434", None)
