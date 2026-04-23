from __future__ import annotations

import os
import re


class InputGuardError(ValueError):
    pass


MAX_INPUT_TOKENS = int(os.getenv("MAX_INPUT_TOKENS", "4096"))
MAX_INPUT_BYTES = MAX_INPUT_TOKENS * 4

INJECTION_PATTERNS = [
    r"ignore\s+all\s+previous\s+instructions",
    r"ignore\s+previous\s+instructions",
    r"you\s+are\s+now\s+a\s+different\s+assistant",
    r"disregard\s+(your\s+)?system\s+prompt",
    r"\bjailbreak\b",
    r"\bdan\s+mode\b",
    r"repeat\s+after\s+me",
    r"\bact\s+as\s+an?\s+unrestricted",
    r"\bact\s+as\s+(a\s+)?different",
    r"without\s+restrictions",
]

SECRET_PATTERNS = [
    r"\bpassword\b\s*[:=]\s*(?:[\"'][^\"']{4,}[\"']|[A-Za-z0-9_\-]*\d[A-Za-z0-9_\-]*)",
    r"\bpwd\b\s*[:=]\s*(?:[\"'][^\"']{4,}[\"']|[A-Za-z0-9_\-]*\d[A-Za-z0-9_\-]*)",
    r"\bapi[_-]?key\s*[:=]\s*(?:[\"'][^\"']{6,}[\"']|[A-Za-z0-9_\-]{8,})",
    r"\bapiKey\s*[:=]\s*(?:[\"'][^\"']{6,}[\"']|[A-Za-z0-9_\-]{8,})",
    r"\bAKIA[0-9A-Z]{16}\b",
    r"\baws_access_key_id\b",
    r"\baws_secret_access_key\b",
    r"-----BEGIN\s+(?:RSA|EC|)\s*PRIVATE\s+KEY-----",
    r"-----BEGIN\s+PRIVATE\s+KEY-----",
    r"\bBearer\s+[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+",
    r"\bAuthorization\s*:\s*Bearer\s+",
    r"\bsk-[A-Za-z0-9]{12,}\b",
]
_INJECTION_REGEXES = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]
_SECRET_REGEXES = [re.compile(p, re.IGNORECASE) for p in SECRET_PATTERNS]
_HTML_RE = re.compile(r"<[^>]+>")
_CTRL_RE = re.compile(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize(text: str | None) -> str:
    if text is None:
        raise InputGuardError("invalid input")

    cleaned = str(text)

    if "\x00" in cleaned:
        raise InputGuardError("secret or binary content detected")

    cleaned = _HTML_RE.sub("", cleaned)
    cleaned = _CTRL_RE.sub("", cleaned)
    cleaned = cleaned.strip()

    if len(cleaned.encode("utf-8")) > MAX_INPUT_BYTES:
        raise InputGuardError("input length exceeds guardrail limit")

    normalized = re.sub(r"[^A-Za-z0-9]+", " ", cleaned).strip()

    for rgx in _INJECTION_REGEXES:
        if rgx.search(cleaned) or rgx.search(normalized):
            raise InputGuardError("injection pattern detected")

    for rgx in _SECRET_REGEXES:
        if rgx.search(cleaned):
            raise InputGuardError("secret pattern detected")

    return cleaned
