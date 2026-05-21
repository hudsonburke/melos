"""Identifier helpers for Blender-authored melos entities."""

from __future__ import annotations

import re
from collections.abc import Collection


_NON_IDENTIFIER_PATTERN = re.compile(r"[^A-Za-z0-9_.-]+")


def make_identifier(label: str, *, fallback: str = "entity") -> str:
    """Convert free-form text into a stable melos identifier."""

    normalized = _NON_IDENTIFIER_PATTERN.sub("_", label.strip())
    normalized = normalized.strip("_.-")

    if not normalized:
        return fallback

    if not normalized[0].isalpha():
        normalized = f"{fallback}_{normalized}"

    return normalized


def allocate_identifier(
    label: str,
    existing: Collection[str],
    *,
    fallback: str = "entity",
) -> str:
    """Return a unique identifier derived from ``label``."""

    base = make_identifier(label, fallback=fallback)
    if base not in existing:
        return base

    index = 2
    candidate = f"{base}_{index}"
    while candidate in existing:
        index += 1
        candidate = f"{base}_{index}"

    return candidate
