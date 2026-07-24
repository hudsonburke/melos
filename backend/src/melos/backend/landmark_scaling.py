"""Landmark-based measurement rules for subject-specific scaling.

Each rule defines how to derive a segment length from anatomical landmark
positions.  The measured distance between two landmarks (or a chain of
landmarks) forms the *source* length for the scaling pipeline, and the
user provides the corresponding *target* length from the subject.

This connects the landmark registry to the by_segment_lengths() scaler.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from melos.core.model import SkeletonState
from melos.backend.scaling import by_segment_lengths


# ── Measurement rules ─────────────────────────────────────────────────────


@dataclass
class MeasurementRule:
    """A rule that derives a segment length from one or more landmarks.

    ``segment`` is the logical segment name (e.g. ``"thigh"``) used in the
    scaling pipeline.

    ``mode`` determines how the length is computed:
    - ``"lm_pair_distance"``: Euclidean distance between two landmarks.
    - ``"lm_chain_length"``: sum of distances along a chain of landmarks.
    - ``"lm_axis_distance"``: distance along a single axis (e.g. X for width).

    ``landmark_names`` are the landmark keys in the registry (e.g. ``"RASI"``).

    ``link_ids`` are the Melos link(s) this segment maps to (for scaling).
    """
    segment: str
    mode: str  # "lm_pair_distance" | "lm_chain_length" | "lm_axis_distance"
    landmark_names: list[str]
    link_ids: list[str]
    axis: str | None = None  # "x", "y", or "z" for lm_axis_distance


# ── Rajagopal model measurement rules ─────────────────────────────────────
# These are derived from the 57 landmarks in the registry and the standard
# marker set used in gait biomechanics (similar to OpenSim's Scale Tool).

RAJAGOPAL_MEASUREMENT_RULES = [
    # Pelvis
    MeasurementRule(
        segment="pelvis_width",
        mode="lm_pair_distance",
        landmark_names=["RASI", "LASI"],
        link_ids=["pelvis"],
    ),
    MeasurementRule(
        segment="pelvis_depth",
        mode="lm_pair_distance",
        landmark_names=["RASI", "RPSI"],
        link_ids=["pelvis"],
    ),

    # Right leg
    MeasurementRule(
        segment="thigh_r",
        mode="lm_chain_length",
        landmark_names=["RASI", "RLEpicondyle"],
        link_ids=["femur_r"],
    ),
    MeasurementRule(
        segment="shank_r",
        mode="lm_chain_length",
        landmark_names=["RLEpicondyle", "RMalleolusLat"],
        link_ids=["tibia_r"],
    ),

    # Left leg
    MeasurementRule(
        segment="thigh_l",
        mode="lm_chain_length",
        landmark_names=["LASI", "LLEpicondyle"],
        link_ids=["femur_l"],
    ),
    MeasurementRule(
        segment="shank_l",
        mode="lm_chain_length",
        landmark_names=["LLEpicondyle", "LMalleolusLat"],
        link_ids=["tibia_l"],
    ),

    # Torso
    MeasurementRule(
        segment="torso_height",
        mode="lm_chain_length",
        landmark_names=["C7", "Sacral"],
        link_ids=["torso", "pelvis"],
    ),
    MeasurementRule(
        segment="shoulder_width",
        mode="lm_pair_distance",
        landmark_names=["RACR", "LACR"],
        link_ids=["torso"],
    ),

    # Right arm
    MeasurementRule(
        segment="upper_arm_r",
        mode="lm_chain_length",
        landmark_names=["RSJC", "RLElbow"],
        link_ids=["humerus_r"],
    ),
    MeasurementRule(
        segment="forearm_r",
        mode="lm_chain_length",
        landmark_names=["RLElbow", "RStyloid"],
        link_ids=["ulna_r", "radius_r"],
    ),

    # Left arm
    MeasurementRule(
        segment="upper_arm_l",
        mode="lm_chain_length",
        landmark_names=["LSJC", "LLElbow"],
        link_ids=["humerus_l"],
    ),
    MeasurementRule(
        segment="forearm_l",
        mode="lm_chain_length",
        landmark_names=["LLElbow", "LStyloid"],
        link_ids=["ulna_l", "radius_l"],
    ),
]


def measure_segment(
    rule: MeasurementRule,
    lm_positions: dict[str, tuple[float, float, float]],
) -> float:
    """Compute the current segment length from landmark positions using a rule.

    Returns the measured length in meters (same units as the landmark positions).
    """
    pts = []
    for name in rule.landmark_names:
        pos = lm_positions.get(name)
        if pos is None:
            raise ValueError(f"Landmark '{name}' not found in registry positions")
        pts.append(pos)

    if rule.mode == "lm_pair_distance":
        if len(pts) < 2:
            raise ValueError("lm_pair_distance requires at least 2 landmarks")
        dx = pts[0][0] - pts[1][0]
        dy = pts[0][1] - pts[1][1]
        dz = pts[0][2] - pts[1][2]
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    elif rule.mode == "lm_chain_length":
        total = 0.0
        for i in range(len(pts) - 1):
            dx = pts[i][0] - pts[i + 1][0]
            dy = pts[i][1] - pts[i + 1][1]
            dz = pts[i][2] - pts[i + 1][2]
            total += math.sqrt(dx * dx + dy * dy + dz * dz)
        return total

    elif rule.mode == "lm_axis_distance":
        if len(pts) < 2:
            raise ValueError("lm_axis_distance requires at least 2 landmarks")
        axis_idx = {"x": 0, "y": 1, "z": 2}.get(rule.axis or "y")
        if axis_idx is None:
            raise ValueError(f"Invalid axis: {rule.axis}")
        return abs(pts[0][axis_idx] - pts[1][axis_idx])

    else:
        raise ValueError(f"Unknown mode: {rule.mode}")


def scale_by_landmarks(
    skeleton: SkeletonState,
    landmark_positions: dict[str, tuple[float, float, float]],
    subject_measurements: dict[str, float],
    *,
    rules: list[MeasurementRule] | None = None,
    target_mass: float | None = None,
) -> Any:
    """Scale the skeleton using landmark-derived segment measurements.

    ``landmark_positions`` are world-space positions from the landmark registry.
    ``subject_measurements`` map segment names (e.g. ``"thigh_r"``) to subject
    lengths in meters.

    Returns the same ScaleReport as ``by_segment_lengths()``.
    """
    if rules is None:
        rules = RAJAGOPAL_MEASUREMENT_RULES

    # Compute current (source) lengths from landmark positions
    source_lengths: dict[str, float] = {}
    for rule in rules:
        try:
            source_lengths[rule.segment] = measure_segment(rule, landmark_positions)
        except (ValueError, KeyError) as e:
            # Skip rules with missing landmarks
            import logging
            logging.getLogger(__name__).warning(
                "Skipping segment '%s': %s", rule.segment, e
            )
            continue

    # Filter to segments present in both source and subject data
    target: dict[str, float] = {}
    segment_to_link: dict[str, str | list[str]] = {}
    for rule in rules:
        if rule.segment in source_lengths and rule.segment in subject_measurements:
            target[rule.segment] = subject_measurements[rule.segment]
            segment_to_link[rule.segment] = (
                rule.link_ids[0] if len(rule.link_ids) == 1 else rule.link_ids
            )

    return by_segment_lengths(
        skeleton,
        target_lengths=target,
        segment_to_link=segment_to_link,
        source_lengths=source_lengths,
        target_mass=target_mass,
    )
