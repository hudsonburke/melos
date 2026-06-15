"""Identifier conventions for melos core models."""

from __future__ import annotations

import re
from typing import TypeAlias

Identifier: TypeAlias = str

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")


def is_valid_identifier(value: str) -> bool:
    """Return ``True`` if ``value`` matches the project identifier pattern."""

    return bool(IDENTIFIER_PATTERN.fullmatch(value))
