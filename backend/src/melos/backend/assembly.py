"""Exoskeleton assembly descriptors — YAML files that map Proteus parts to
skeleton landmarks.

An assembly descriptor defines which parametric Proteus parts to build and
where on the skeleton they attach, using the landmark registry as the
common reference frame.

Example YAML:

```yaml
name: "right_arm_brace"
version: "1.0"
parts:
  - type: "Cuff"
    id: "upper_arm_cuff"
    description: "Upper arm cuff for right arm"
    parameters:
      coverage: 0.75
      wall_thickness: 3.0
      padding_thickness: 2.0
      width: 40.0
    attachments:
      - landmark: "RUA1"
        role: "proximal"
      - landmark: "RUA3"
        role: "distal"
    subject_measurements:
      - segment: "upper_arm_r_circumference"
        source: "landmark_circumference"
        landmarks: ["RUA1", "RUA3"]

  - type: "Cuff"
    id: "forearm_cuff"
    parameters:
      coverage: 0.7
      wall_thickness: 3.0
      padding_thickness: 2.0
      width: 35.0
    attachments:
      - landmark: "RStyloid"
        role: "distal"
      - { landmark: "RFASup", role: "proximal" }
```
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_assembly_descriptor(path: str | Path) -> dict[str, Any]:
    """Load an exoskeleton assembly descriptor YAML file."""
    path = Path(path)
    with open(path) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "parts" not in data:
        raise ValueError(f"Assembly descriptor {path} missing 'parts' key")
    return data


def list_assembly_descriptors(descriptors_dir: str | Path) -> list[dict[str, str]]:
    """List available assembly descriptor YAML files."""
    descriptors_dir = Path(descriptors_dir)
    if not descriptors_dir.exists():
        return []
    result: list[dict[str, str]] = []
    for f in sorted(descriptors_dir.glob("*.yaml")):
        try:
            data = load_assembly_descriptor(f)
            result.append({
                "name": data.get("name", f.stem),
                "description": data.get("description", ""),
                "file": f.name,
                "n_parts": str(len(data.get("parts", []))),
            })
        except Exception:
            pass
    return result


def resolve_assembly(
    descriptor: dict[str, Any],
    landmark_positions: dict[str, tuple[float, float, float]],
    landmark_definitions: dict[str, dict[str, Any]],
    subject_measurements: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Resolve an assembly descriptor against real landmark positions.

    For each part in the descriptor:
    1. Look up the attachment landmarks' world positions
    2. Derive part parameters from landmark distances (circumference, length)
    3. Apply any subject-specific overrides
    4. Return a resolved part specification

    Returns a dict with the resolved data — ready for Proteus part construction.
    """
    resolved_parts: list[dict[str, Any]] = []

    for part_spec in descriptor.get("parts", []):
        part_type = part_spec.get("type", "Unknown")
        part_id = part_spec.get("id", f"{part_type}_{len(resolved_parts)}")
        params = dict(part_spec.get("parameters", {}))

        # Resolve attachment landmarks to world positions
        attachments: dict[str, dict[str, float]] = {}
        for att in part_spec.get("attachments", []):
            lm_name = att.get("landmark", "")
            role = att.get("role", "")
            if lm_name in landmark_positions:
                pos = landmark_positions[lm_name]
                lm_def = landmark_definitions.get(lm_name, {})
                attachments[role] = {
                    "x": pos[0],
                    "y": pos[1],
                    "z": pos[2],
                    "link": lm_def.get("link", ""),
                    "offset": lm_def.get("offset", [0, 0, 0]),
                    "landmark_name": lm_name,
                }

        # Compute subject measurements from landmarks
        measurements: dict[str, float] = {}
        for m in part_spec.get("subject_measurements", []):
            seg_name = m.get("segment", "")
            lm_names = m.get("landmarks", [])
            lm_names = lm_names if lm_names else []

            if len(lm_names) >= 2:
                p0 = landmark_positions.get(lm_names[0])
                p1 = landmark_positions.get(lm_names[-1])
                if p0 and p1:
                    import math
                    dx = p0[0] - p1[0]
                    dy = p0[1] - p1[1]
                    dz = p0[2] - p1[2]
                    measurements[seg_name] = math.sqrt(dx*dx + dy*dy + dz*dz)

        # Override with subject-specific measurements if provided
        if subject_measurements:
            for seg_name, val in subject_measurements.items():
                measurements[seg_name] = val

        resolved_parts.append({
            "id": part_id,
            "type": part_type,
            "parameters": params,
            "attachments": attachments,
            "measurements": measurements,
        })

    return {
        "name": descriptor.get("name", "unnamed"),
        "parts": resolved_parts,
    }
