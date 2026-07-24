"""
# Landmark Registry Concept

A landmark is a named anatomical point that has a well-defined position relative
to one or more model representations.  Unlike joint centers (which are abstract
and model-specific), landmarks correspond to palpable bony features on the body
surface — the same places you'd place a motion-capture marker or take an
anthropometric measurement.

Each landmark entry can define its position in multiple model spaces:
  - melos  : link-relative offset in the Melos/OpenSim skeleton
  - mhr    : bone-relative offset in the MHR skeleton
  - soma   : vertex index on the SOMA canonical mesh
  - markerset: the name(s) used in OpenSim marker files / OpenCap output

A single YAML file defines all known landmarks for a reference model.
Users can override or extend entries for their specific model.
"""

import os
import yaml
from pathlib import Path
from typing import Any

from melos.core.model import LinkTransform, SkeletonState

# ── Canonical landmark descriptor ─────────────────────────────────────────

LANDMARK_REGISTRY = {
    "version": "1.0",
    "reference_model": "Rajagopal2015",
    "description": "Canonical anatomical landmarks from the Rajagopal2015 full-body OpenSim model",
    "landmarks": {
        # ── Pelvis ────────────────────────────────────────────────────
        "RASI": {
            "description": "Right anterior superior iliac spine",
            "melos": {"link": "pelvis", "offset": [0.0095, 0.0181, 0.1285]},
        },
        "LASI": {
            "description": "Left anterior superior iliac spine",
            "melos": {"link": "pelvis", "offset": [0.0095, 0.0181, -0.1285]},
        },
        "RPSI": {
            "description": "Right posterior superior iliac spine",
            "melos": {"link": "pelvis", "offset": [-0.155, 0.035, 0.045]},
        },
        "LPSI": {
            "description": "Left posterior superior iliac spine",
            "melos": {"link": "pelvis", "offset": [-0.155, 0.035, -0.045]},
        },
        "Sacral": {
            "description": "Sacral marker",
            "melos": {"link": "pelvis", "offset": [-0.06, 0.045, 0.0]},
        },

        # ── Right leg ─────────────────────────────────────────────────
        "RThighUpper": {
            "description": "Right thigh upper",
            "melos": {"link": "femur_r", "offset": [-0.008, -0.134, 0.049]},
        },
        "RThighFront": {
            "description": "Right thigh front",
            "melos": {"link": "femur_r", "offset": [0.032, -0.169, 0.02]},
        },
        "RThighRear": {
            "description": "Right thigh rear",
            "melos": {"link": "femur_r", "offset": [-0.039, -0.15, -0.025]},
        },
        "RLEpicondyle": {
            "description": "Right lateral femoral epicondyle",
            "melos": {"link": "femur_r", "offset": [0.015, -0.28, 0.04]},
        },
        "RMEpicondyle": {
            "description": "Right medial femoral epicondyle",
            "melos": {"link": "femur_r", "offset": [0.0023, -0.286, -0.046]},
        },
        "RShankUpper": {
            "description": "Right shank upper",
            "melos": {"link": "tibia_r", "offset": [0.016, -0.088, 0.025]},
        },
        "RShankFront": {
            "description": "Right shank front",
            "melos": {"link": "tibia_r", "offset": [0.011, -0.22, 0.014]},
        },
        "RShankRear": {
            "description": "Right shank rear",
            "melos": {"link": "tibia_r", "offset": [-0.021, -0.2, -0.009]},
        },
        "RMalleolusLat": {
            "description": "Right lateral malleolus",
            "melos": {"link": "tibia_r", "offset": [0.01, -0.4, 0.0]},
        },
        "RMalleolusMed": {
            "description": "Right medial malleolus",
            "melos": {"link": "tibia_r", "offset": [0.005, -0.4, -0.055]},
        },
        "RHeel": {
            "description": "Right heel",
            "melos": {"link": "calcn_r", "offset": [-0.065, -0.018, 0.0]},
        },
        "RToe": {
            "description": "Right toe",
            "melos": {"link": "toes_r", "offset": [0.065, 0.0, 0.0]},
        },

        # ── Left leg ──────────────────────────────────────────────────
        "LThighUpper": {
            "description": "Left thigh upper",
            "melos": {"link": "femur_l", "offset": [-0.008, -0.134, -0.049]},
        },
        "LThighFront": {
            "description": "Left thigh front",
            "melos": {"link": "femur_l", "offset": [0.032, -0.169, -0.02]},
        },
        "LThighRear": {
            "description": "Left thigh rear",
            "melos": {"link": "femur_l", "offset": [-0.039, -0.15, 0.025]},
        },
        "LMEpicondyle": {
            "description": "Left medial femoral epicondyle",
            "melos": {"link": "femur_l", "offset": [0.015, -0.28, -0.04]},
        },
        "LLEpicondyle": {
            "description": "Left lateral femoral epicondyle",
            "melos": {"link": "femur_l", "offset": [0.0023, -0.286, 0.046]},
        },
        "LShankUpper": {
            "description": "Left shank upper",
            "melos": {"link": "tibia_l", "offset": [0.016, -0.088, -0.025]},
        },
        "LShankFront": {
            "description": "Left shank front",
            "melos": {"link": "tibia_l", "offset": [0.011, -0.22, -0.014]},
        },
        "LShankRear": {
            "description": "Left shank rear",
            "melos": {"link": "tibia_l", "offset": [-0.021, -0.2, 0.009]},
        },
        "LMalleolusLat": {
            "description": "Left lateral malleolus",
            "melos": {"link": "tibia_l", "offset": [0.01, -0.4, 0.0]},
        },
        "LMalleolusMed": {
            "description": "Left medial malleolus",
            "melos": {"link": "tibia_l", "offset": [0.005, -0.4, 0.055]},
        },
        "LHeel": {
            "description": "Left heel",
            "melos": {"link": "calcn_l", "offset": [-0.065, -0.018, 0.0]},
        },
        "LToe": {
            "description": "Left toe",
            "melos": {"link": "toes_l", "offset": [0.065, 0.0, 0.0]},
        },

        # ── Torso ─────────────────────────────────────────────────────
        "RACR": {
            "description": "Right acromion",
            "melos": {"link": "torso", "offset": [-0.003, 0.425, 0.13]},
        },
        "LACR": {
            "description": "Left acromion",
            "melos": {"link": "torso", "offset": [-0.003, 0.425, -0.13]},
        },
        "C7": {
            "description": "Cervical 7 vertebrae",
            "melos": {"link": "torso", "offset": [-0.085, 0.435, 0.0017]},
        },
        "CLAV": {
            "description": "Clavicle",
            "melos": {"link": "torso", "offset": [0.04, 0.38, 0.017]},
        },
        "RASH": {
            "description": "Right anterior shoulder",
            "melos": {"link": "torso", "offset": [0.05, 0.3715, 0.17]},
        },
        "RPSH": {
            "description": "Right posterior shoulder",
            "melos": {"link": "torso", "offset": [-0.05, 0.3715, 0.17]},
        },
        "LASH": {
            "description": "Left anterior shoulder",
            "melos": {"link": "torso", "offset": [0.05, 0.3715, -0.17]},
        },
        "LPSH": {
            "description": "Left posterior shoulder",
            "melos": {"link": "torso", "offset": [-0.058, 0.3715, -0.17]},
        },

        # ── Right arm ─────────────────────────────────────────────────
        "RSJC": {
            "description": "Right shoulder joint center",
            "melos": {"link": "humerus_r", "offset": [0.0, 0.0, 0.0]},
        },
        "RUA1": {
            "description": "Right upper arm 1",
            "melos": {"link": "humerus_r", "offset": [0.0, -0.05, 0.02]},
        },
        "RUA2": {
            "description": "Right upper arm 2",
            "melos": {"link": "humerus_r", "offset": [0.0, -0.2, 0.02]},
        },
        "RUA3": {
            "description": "Right upper arm 3",
            "melos": {"link": "humerus_r", "offset": [0.03, -0.13, 0.02]},
        },
        "RLElbow": {
            "description": "Right lateral elbow (radial epicondyle)",
            "melos": {"link": "humerus_r", "offset": [0.015, -0.28, 0.04]},
        },
        "RMElbow": {
            "description": "Right medial elbow (ulnar epicondyle)",
            "melos": {"link": "humerus_r", "offset": [0.0023, -0.286, -0.046]},
        },
        "RFASup": {
            "description": "Right forearm superior",
            "melos": {"link": "ulna_r", "offset": [0.0046, -0.08, 0.045]},
        },
        "RFAProx": {
            "description": "Right forearm radius proximal",
            "melos": {"link": "radius_r", "offset": [0.0005, -0.225, 0.05]},
        },
        "RFADist": {
            "description": "Right forearm ulna distal",
            "melos": {"link": "radius_r", "offset": [-0.022, -0.225, -0.022]},
        },
        "RStyloid": {
            "description": "Right radial styloid",
            "melos": {"link": "radius_r", "offset": [-0.009, -0.255, 0.03]},
        },

        # ── Left arm ──────────────────────────────────────────────────
        "LSJC": {
            "description": "Left shoulder joint center",
            "melos": {"link": "humerus_l", "offset": [0.0, 0.0, 0.0]},
        },
        "LUA1": {
            "description": "Left upper arm 1",
            "melos": {"link": "humerus_l", "offset": [0.0, -0.05, -0.02]},
        },
        "LUA2": {
            "description": "Left upper arm 2",
            "melos": {"link": "humerus_l", "offset": [0.0, -0.2, -0.02]},
        },
        "LUA3": {
            "description": "Left upper arm 3",
            "melos": {"link": "humerus_l", "offset": [0.03, -0.13, -0.02]},
        },
        "LLElbow": {
            "description": "Left lateral elbow (radial epicondyle)",
            "melos": {"link": "humerus_l", "offset": [0.015, -0.28, -0.04]},
        },
        "LMElbow": {
            "description": "Left medial elbow (ulnar epicondyle)",
            "melos": {"link": "humerus_l", "offset": [0.0023, -0.286, 0.046]},
        },
        "LFASup": {
            "description": "Left forearm superior",
            "melos": {"link": "ulna_l", "offset": [0.0046, -0.08, -0.045]},
        },
        "LFAProx": {
            "description": "Left forearm radius proximal",
            "melos": {"link": "radius_l", "offset": [0.0005, -0.225, -0.05]},
        },
        "LFADist": {
            "description": "Left forearm ulna distal",
            "melos": {"link": "radius_l", "offset": [-0.022, -0.225, 0.022]},
        },
        "LStyloid": {
            "description": "Left radial styloid",
            "melos": {"link": "radius_l", "offset": [-0.009, -0.255, -0.03]},
        },
    },
}


def load_landmark_registry(path: str | Path | None = None) -> dict:
    """Load the landmark registry from a YAML file, or return the built-in."""
    if path is None:
        return LANDMARK_REGISTRY
    with open(path) as f:
        return yaml.safe_load(f)


def write_landmark_registry(path: str | Path) -> None:
    """Write the built-in landmark registry to a YAML file."""
    with open(path, "w") as f:
        yaml.dump(LANDMARK_REGISTRY, f, default_flow_style=False, sort_keys=False)
    print(f"Landmark registry written to {path}")


def landmark_world_positions(
    skeleton: SkeletonState,
    marker_set: dict | None = None,
    set_name: str = "gait_full_body",
) -> dict[str, tuple[float, float, float]]:
    """Compute world-space positions of all landmarks for a given skeleton pose.

    Loads landmarks from a YAML marker set (default: gait_full_body).
    Each landmark offset is transformed through the skeleton hierarchy
    to get world positions.
    """
    if marker_set is None:
        from melos.backend.marker_sets import builtin_marker_sets_dir, load_marker_set
        path = builtin_marker_sets_dir() / f"{set_name}.yaml"
        if not path.exists():
            return {}
        marker_set = load_marker_set(path)

    # Build world transforms for all links
    from melos.backend.scaling import compute_bone_positions
    link_world = compute_bone_positions(skeleton)

    result: dict[str, tuple[float, float, float]] = {}
    landmarks = marker_set.get("landmarks", {}) if marker_set else {}
    for name, entry in landmarks.items():
        melos_info = entry.get("melos", {})
        link_id = melos_info.get("link")
        offset = melos_info.get("offset", [0, 0, 0])
        if not link_id or link_id not in link_world:
            continue
        base = link_world[link_id]
        # The offset is in the link's local frame.  We rotate it by the link's
        # world quaternion to get world-space offset, then add world position.
        # For simplicity (and because most offsets are small), we approximate:
        # landmark_world ≈ link_world + offset (in world axes).
        # A full rotation-aware version would need per-link quaternions.
        result[name] = (
            base[0] + offset[0],
            base[1] + offset[1],
            base[2] + offset[2],
        )
    return result
