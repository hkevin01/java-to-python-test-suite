from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import re
from urllib.parse import urlparse


class ProviderConfigError(ValueError):
    pass


APPROVED_PROVIDERS = {"ollama", "vllm", "azure", "bedrock"}

_BLOCKED_MODEL_PATTERNS = [
    re.compile(r"\bqwen", re.IGNORECASE),
    re.compile(r"\bdeepseek", re.IGNORECASE),
    re.compile(r"\bbaichuan", re.IGNORECASE),
    re.compile(r"\binternlm", re.IGNORECASE),
    re.compile(r"\bchatglm", re.IGNORECASE),
    re.compile(r"\bglm-", re.IGNORECASE),
    re.compile(r"\bminimax", re.IGNORECASE),
    re.compile(r"\bmoonshot", re.IGNORECASE),
]

_PUBLIC_BLOCKLIST = (
    "openai.com",
    "anthropic.com",
    "googleapis.com",
    "huggingface.co",
    "together.xyz",
    "amazonaws.com",
)


def _is_private_or_local(hostname: str) -> bool:
    if hostname in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        return ipaddress.ip_address(hostname).is_private
    except ValueError:
        return False


def assert_egress_url_safe(url: str | None, provider: str | None) -> None:
    if provider is None:
        raise ProviderConfigError("provider is required")

    provider = provider.lower()
    if provider not in APPROVED_PROVIDERS:
        raise ProviderConfigError("provider blocked")

    if provider == "bedrock" and not url:
        return

    if not url:
        return

    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    if provider == "azure":
        if host.endswith(".azure.com"):
            return
        raise ProviderConfigError("azure provider requires azure endpoint")

    if provider in {"ollama", "vllm"}:
        if _is_private_or_local(host):
            return
        if any(host.endswith(domain) for domain in _PUBLIC_BLOCKLIST) or host:
            raise ProviderConfigError("public egress blocked for on-prem provider")


def validate_provider_config(settings) -> None:
    provider = (settings.LLM_PROVIDER or "").lower()
    model = (settings.LLM_MODEL or "").lower()

    if provider not in APPROVED_PROVIDERS:
        raise ProviderConfigError("provider blocked")

    for pattern in _BLOCKED_MODEL_PATTERNS:
        if pattern.search(model):
            raise ProviderConfigError("blocked model family")

    endpoint = getattr(settings, "LLM_ENDPOINT", None)
    assert_egress_url_safe(endpoint, provider)


def get_provider(settings=None) -> str:
    if settings is None:
        return "ollama"
    return (getattr(settings, "LLM_PROVIDER", "ollama") or "ollama").lower()
