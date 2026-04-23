import re
from typing import Tuple

_PATTERNS = [
    ("AFM", re.compile(r"\b\d{9}\b")),
    ("AMKA", re.compile(r"\b\d{11}\b")),
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
    ("PHONE_GR", re.compile(r"\b(?:\+30|0030)?[ \-]?(?:2\d{9}|69\d{8}|6[0-9]\d{8})\b")),
]

_PLACEHOLDER = {
    "AFM": "[AFM_REDACTED]",
    "AMKA": "[AMKA_REDACTED]",
    "EMAIL": "[EMAIL_REDACTED]",
    "PHONE_GR": "[PHONE_REDACTED]",
}


def redact_pii(text: str) -> Tuple[str, int]:
    """Return (redacted_text, count_of_redactions)."""
    count = 0
    for label, pattern in _PATTERNS:
        matches = pattern.findall(text)
        count += len(matches)
        text = pattern.sub(_PLACEHOLDER[label], text)
    return text, count
