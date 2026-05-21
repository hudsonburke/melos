"""Schema-version helpers for melos project I/O."""

from __future__ import annotations

from typing import Final


CURRENT_SCHEMA_VERSION: Final[str] = "0.1.0"
SUPPORTED_SCHEMA_VERSIONS: Final[tuple[str, ...]] = (CURRENT_SCHEMA_VERSION,)


def is_supported_schema_version(version: str) -> bool:
    """Return ``True`` if ``version`` is understood by this package."""

    return version in SUPPORTED_SCHEMA_VERSIONS
