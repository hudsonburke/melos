"""MHR-to-Melos scaling adapter.

Takes MHR identity parameters (from monocular video via SAM 3D Body or
similar) and produces a subject-specific scaled skeleton + skinned mesh
for the editor.

Flow:
  MHR identity coefficients + scale params
    → SOMA layer → skin bundle (joints, mesh, skin weights)
    → compute segment lengths from MHR joint pairs
    → map to Melos segment names (myofullbody_to_human_v1)
    → scale the Arrow skeleton via landmark-based scaling
    → return scaled skeleton + MHR mesh for visualization

If SOMA is not available, the adapter degrades to using the generic
baseline skin bundle for visualization without subject-specific scaling.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from melos.core.model import SkeletonState
from melos.backend.scaling import by_segment_lengths, compute_bone_positions

logger = logging.getLogger(__name__)

# ── Detect SOMA availability ──────────────────────────────────────────────

def soma_available() -> bool:
    """Check whether the SOMA-X package and assets are installed."""
    import importlib.util
    return (
        importlib.util.find_spec("soma") is not None
    )


def default_mhr_bundle() -> dict[str, Any] | None:
    """Try to load a default MHR skin bundle from melos-skin assets.

    Returns None if assets aren't available.
    """
    try:
        from melos.skin.adapters import build_example_mhr_skin_bundle
        return build_example_mhr_skin_bundle(
            Path(__file__).resolve().parent / "marker_sets",
            global_scale=1.0,
        )
    except (ImportError, FileNotFoundError, OSError):
        logger.info("MHR skin assets not available — skeleton-only mode")
        return None


def load_mhr_bundle(
    identity_coeffs: list[float] | None = None,
    scale_params: list[float] | None = None,
    data_root: str | Path | None = None,
    global_scale: float = 1.0,
) -> dict[str, Any] | None:
    """Build an MHR skin bundle from identity parameters.

    Args:
        identity_coeffs: MHR shape coefficients (from SAM 3D Body or SOMA).
            If None, uses default (neutral) coefficients.
        scale_params: MHR scale parameters. If None, uses defaults.
        data_root: Path to SOMA assets. If None, uses built-in location.
        global_scale: Additional size multiplier.

    Returns:
        Skin bundle dict with keys: vertices, faces, joints, joint_names,
        joint_parent_ids, bind_pose_world, bind_pose_local, weight_*.
        None if SOMA is not available or loading fails.
    """
    if not soma_available():
        logger.warning("SOMA-X not installed — cannot generate MHR skin bundle")
        return default_mhr_bundle()

    from melos.skin.adapters.mhr_skin import build_example_mhr_skin_bundle

    data_root_path = Path(data_root) if data_root else (
        Path(__file__).resolve().parent / "marker_sets"
    )
    if not data_root_path.exists():
        logger.warning("SOMA data root %s not found", data_root_path)
        return default_mhr_bundle()

    try:
        bundle = build_example_mhr_skin_bundle(
            data_root_path,
            identity_coeffs=identity_coeffs,
            scale_params=scale_params,
            global_scale=global_scale,
        )
        return bundle
    except Exception as e:
        logger.error("Failed to build MHR skin bundle: %s", e)
        return None


# ── Segment measurements from MHR bundle ──────────────────────────────────


def segment_lengths_from_mhr(
    bundle: dict[str, Any],
) -> dict[str, float]:
    """Extract segment lengths from an MHR skin bundle.

    Uses the myofullbody_to_human_v1 translation map rules to derive
    per-segment lengths from MHR joint world positions.

    Returns a dict mapping segment names (e.g. ``"right_thigh"``,
    ``"right_shank"``) to lengths in meters.
    """
    from melos.core.retarget.model import JointPositionSet
    from melos.skin.adapters.skin_bundle import build_example_skin_joint_set
    from melos.skin.mappings.myofullbody_to_human_v1 import MYOFULLBODY_TO_HUMAN_V1

    # Joint positions are in cm from MHR; convert to meters
    joint_set = build_example_skin_joint_set(bundle)
    # MHR uses cm internally
    joint_set.units = "cm"

    from melos.core.retarget.measurements import compute_segment_measurements_from_rules
    measurements = compute_segment_measurements_from_rules(
        joint_set,
        MYOFULLBODY_TO_HUMAN_V1.rules,
        units="cm",
    )

    result: dict[str, float] = {}
    for item in measurements.items:
        # Convert cm → m
        result[item.segment_id] = item.length / 100.0
    return result


# ── Main scaling entry point ──────────────────────────────────────────────


def scale_skeleton_from_mhr(
    skeleton: SkeletonState,
    bundle: dict[str, Any],
    target_mass: float | None = None,
) -> dict[str, Any]:
    """Scale the Melos skeleton to match the body shape from an MHR skin bundle.

    Extracts segment lengths from the MHR joint positions, maps them to Melos
    segment names, and runs the landmark-based scaling pipeline.

    Returns:
        dict with keys:
        - scale_report: the ScaleReport from the scaling pipeline
        - skin_bundle: the MHR mesh data (for frontend skin rendering)
        - segment_lengths: dict of segment name → length in meters
    """
    from melos.backend.landmarks import landmark_world_positions

    segment_lengths = segment_lengths_from_mhr(bundle)
    lm_pos = landmark_world_positions(skeleton)
    # Build landmark distances as subject measurements
    from melos.backend.landmark_scaling import RAJAGOPAL_MEASUREMENT_RULES, measure_segment

    subject_measurements: dict[str, float] = {}
    for rule in RAJAGOPAL_MEASUREMENT_RULES:
        try:
            baseline = measure_segment(rule, lm_pos)
            # The subject measurement is the MHR-derived segment length
            # mapped to this rule's segment.  We don't have a direct mapping
            # from MHR segment names to our rule segment names, so we use
            # the landmark distance as-is for now.
            # TODO: Build explicit MHR→Melos segment mapping
            pass
        except (ValueError, KeyError):
            pass

    # For now, use a simpler approach: by_bone_vectors from joint positions
    from melos.backend.scaling import by_bone_vectors

    # Build joint name → link ID mapping from the translation rules
    joint_to_link = {
        "hip_r": "femur_r",
        "knee_r": "tibia_r",
        "ankle_r": "talus_r",
        "hip_l": "femur_l",
        "knee_l": "tibia_l",
        "ankle_l": "talus_l",
    }

    # Extract target bone vectors from MHR joints
    mhr_joints = bundle.get("joints", {})
    # MHR joint names in the bundle follow myofullbody convention
    mhr_joint_names = bundle.get("joint_names", [])

    # Compute bone vectors using MHR world joint positions
    # (in cm, convert to m)
    target_vectors: dict[str, tuple[float, float, float]] = {}

    hip_r = mhr_joints.get("RightLeg") or mhr_joints.get("r_leg") or (0, 0, 0)
    knee_r = mhr_joints.get("RightShin") or mhr_joints.get("r_shin") or (0, 0, 0)
    ankle_r = mhr_joints.get("RightFoot") or mhr_joints.get("r_foot") or (0, 0, 0)

    if hip_r and knee_r:
        target_vectors["hip_r"] = (
            (knee_r[0] - hip_r[0]) / 100.0,
            (knee_r[1] - hip_r[1]) / 100.0,
            (knee_r[2] - hip_r[2]) / 100.0,
        )
    if knee_r and ankle_r:
        target_vectors["knee_r"] = (
            (ankle_r[0] - knee_r[0]) / 100.0,
            (ankle_r[1] - knee_r[1]) / 100.0,
            (ankle_r[2] - knee_r[2]) / 100.0,
        )

    if not target_vectors:
        # Fallback to no scaling
        logger.warning("No MHR joint positions available — skipping scaling")
        from melos.backend.scaling import ScaleReport
        return {
            "scale_report": None,
            "skin_bundle": bundle,
            "segment_lengths": segment_lengths,
        }

    report = by_bone_vectors(
        skeleton,
        target_vectors,
        joint_to_link,
        target_mass=target_mass,
    )

    return {
        "scale_report": {
            "link_scale_factors": report.link_scale_factors,
            "matched_segments": report.matched_segments,
            "total_mass_before": report.total_mass_before,
            "total_mass_after": report.total_mass_after,
        },
        "skin_bundle": {
            "vertices": bundle.get("vertices", []),
            "faces": bundle.get("faces", []),
            "joint_names": bundle.get("joint_names", []),
            "joint_parent_ids": bundle.get("joint_parent_ids", []),
            "joints": mhr_joints,
            "bind_pose_world": bundle.get("bind_pose_world", []),
            "bind_pose_local": bundle.get("bind_pose_local", []),
            "weight_data": bundle.get("weight_data", []),
            "weight_indices": bundle.get("weight_indices", []),
            "weight_indptr": bundle.get("weight_indptr", []),
        },
        "segment_lengths": segment_lengths,
    }
