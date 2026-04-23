from __future__ import annotations

import re


REDACT = "[REDACTED]"

_CREDENTIAL_PATTERNS = [
    re.compile(r"(password\s*[:=]\s*)([^\s,;]+)", re.IGNORECASE),
    re.compile(r"(api[_-]?key\s*[:=]\s*[\"']?)([^\s\"',;]+)", re.IGNORECASE),
    re.compile(r"(-----BEGIN\s+(?:RSA|EC|)\s*PRIVATE\s+KEY-----)([\s\S]*?)(-----END[\s\S]*?-----)?", re.IGNORECASE),
    re.compile(r"(bearer\s+)([A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+)", re.IGNORECASE),
]


def check_policy_violations(text: str) -> list[str]:
    for pattern in _CREDENTIAL_PATTERNS:
        if pattern.search(text):
            return ["credential_detected"]
    return []


def validate_output(text: str) -> str:
    result = text
    for pattern in _CREDENTIAL_PATTERNS:
        if pattern.pattern.startswith("(-----BEGIN"):
            result = pattern.sub(REDACT, result)
        else:
            result = pattern.sub(lambda m: f"{m.group(1)}{REDACT}", result)
    return result
