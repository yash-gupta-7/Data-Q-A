"""Lightweight PII detection for common sensitive patterns."""

from __future__ import annotations

import re
from typing import Any

# Patterns for common PII types
_PII_PATTERNS: dict[str, re.Pattern] = {
    "email": re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(
        r"\b(\+?\d[\d\s\-().]{7,}\d)\b"
    ),
    "ssn": re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ \-]?){13,16}\b"),
    "pan_india": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),  # Indian PAN
    "aadhaar": re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"),
}

# Column name hints that likely contain PII
_PII_COLUMN_HINTS: set[str] = {
    "email",
    "phone",
    "mobile",
    "ssn",
    "pan",
    "aadhaar",
    "passport",
    "credit_card",
    "card_number",
    "dob",
    "date_of_birth",
    "address",
    "ip_address",
    "national_id",
    "tax_id",
}


def detect_pii_in_column_name(column_name: str) -> list[str]:
    """Detect PII by column name heuristics."""
    lower = column_name.lower().replace(" ", "_").replace("-", "_")
    detected = []
    for hint in _PII_COLUMN_HINTS:
        if hint in lower:
            detected.append(hint)
    return detected


def detect_pii_in_values(values: list[Any]) -> list[str]:
    """Detect PII patterns in sample values."""
    detected_types: set[str] = set()
    str_values = [str(v) for v in values if v is not None]

    for pii_type, pattern in _PII_PATTERNS.items():
        for val in str_values:
            if pattern.search(val):
                detected_types.add(pii_type)
                break  # one match per type is enough

    return list(detected_types)


def is_pii_column(column_name: str, sample_values: list[Any]) -> list[str]:
    """Combined check: column name + value patterns."""
    detected = set(detect_pii_in_column_name(column_name))
    detected.update(detect_pii_in_values(sample_values))
    return list(detected)


def redact_pii_samples(values: list[Any], pii_types: list[str]) -> list[Any]:
    """Replace sample values with redacted placeholders if PII detected."""
    if not pii_types:
        return values
    label = "/".join(pii_types).upper()
    return [f"[{label} REDACTED]"] * min(len(values), 3)
