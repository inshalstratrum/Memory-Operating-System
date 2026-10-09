from __future__ import annotations

import re

SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"(?i)\b(api[_ -]?key|secret|token|password|passwd)\s*[:=]\s*['\"]?[^'\"\s,;]+"),
    re.compile(r"(?i)\bPIN\s*[:=]?\s*\d{4,8}\b"),
]

CORPORATE_PATTERNS = [
    re.compile(r"(?i)\bconfidential\b"),
    re.compile(r"(?i)\bnda\b"),
    re.compile(r"(?i)\binternal\s+only\b"),
    re.compile(r"(?i)\bdo\s+not\s+distribute\b"),
    re.compile(r"(?i)\bproprietary\b"),
]


def sanitize_text(text: str) -> tuple[str, bool, str]:
    sanitized = text
    applied = False
    sensitivity = "internal"

    if any(pattern.search(text) for pattern in CORPORATE_PATTERNS):
        sensitivity = "sensitive"

    for pattern in SECRET_PATTERNS:
        sanitized_next = pattern.sub("[REDACTED_SECRET]", sanitized)
        if sanitized_next != sanitized:
            applied = True
            sensitivity = "secret"
            sanitized = sanitized_next

    return sanitized, applied, sensitivity
