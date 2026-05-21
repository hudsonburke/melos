"""Schema migration helpers for melos project files."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .schema import CURRENT_SCHEMA_VERSION, SUPPORTED_SCHEMA_VERSIONS


def upgrade_project_dict(data: Mapping[str, Any]) -> dict[str, Any]:
    """Upgrade a raw project mapping to the current schema version.

    The initial implementation is intentionally minimal: it validates the
    incoming schema version and normalizes missing versions to the current one.
    """

    upgraded = deepcopy(dict(data))
    version = str(upgraded.get("schema_version") or CURRENT_SCHEMA_VERSION)

    if version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ValueError(
            f"Unsupported melos schema version {version!r}. Supported versions: "
            f"{', '.join(SUPPORTED_SCHEMA_VERSIONS)}"
        )

    upgraded["schema_version"] = CURRENT_SCHEMA_VERSION
    upgraded.setdefault("systems", [])
    upgraded.setdefault("assemblies", [])
    upgraded.setdefault("skin_attachments", [])
    return upgraded
