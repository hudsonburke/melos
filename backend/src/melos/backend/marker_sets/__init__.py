"""Landmark / marker-set registry — separate YAML files defining anatomical
landmarks as link-relative offsets on a skeleton.

Each YAML file is a self-contained marker set that can be loaded/unloaded
as an overlay on any compatible skeleton model.  This decouples the marker
definition from the skeleton implementation.

A marker set file looks like:

```yaml
name: "gait_full_body"
description: "Standard gait analysis marker set (Rajagopal model)"
landmarks:
  RASI:
    description: "Right anterior superior iliac spine"
    melos: { link: "pelvis", offset: [0.0095, 0.0181, 0.1285] }
    # Future: mhr: { bone: "Hips", offset: [0.06, 0.02, 0.12] }
    # Future: soma: { vertex_index: 1876 }
```

Users can swap marker sets by loading a different YAML file, enabling
different mocap protocols, exo attachment points, or joint centre estimators.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_marker_set(path: str | Path) -> dict[str, Any]:
    """Load a marker-set YAML file and return the landmark definitions.

    Returns a dict with keys: ``name``, ``description``, ``landmarks``.
    """
    path = Path(path)
    with open(path) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "landmarks" not in data:
        raise ValueError(
            f"Marker set {path} missing 'landmarks' key. "
            f"Top-level keys: {list(data.keys()) if isinstance(data, dict) else type(data).__name__}"
        )
    return data


def builtin_marker_sets_dir() -> Path:
    """Return the path to the built-in marker set YAML files."""
    return Path(__file__).resolve().parent


def list_builtin_marker_sets() -> list[dict[str, str]]:
    """List available marker sets bundled with Melos."""
    sets_dir = builtin_marker_sets_dir()
    if not sets_dir.exists():
        return []
    result: list[dict[str, str]] = []
    for f in sorted(sets_dir.glob("*.yaml")):
        try:
            data = load_marker_set(f)
            result.append({
                "name": data.get("name", f.stem),
                "description": data.get("description", ""),
                "file": f.name,
                "count": str(len(data.get("landmarks", {}))),
            })
        except Exception:
            pass
    return result


def available_marker_sets() -> dict[str, list[dict[str, str]]]:
    """Return a dict with built-in and user marker sets."""
    return {
        "builtin": list_builtin_marker_sets(),
    }
