"""Test landmark-based scaling with the Rajagopal model."""
from __future__ import annotations

import sys, math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from melos.backend.app import load_model_from_osim
from melos.backend.landmarks import landmark_world_positions, LANDMARK_REGISTRY
from melos.backend.landmark_scaling import (
    RAJAGOPAL_MEASUREMENT_RULES,
    measure_segment,
    scale_by_landmarks,
)

m = load_model_from_osim("/var/lib/hermes/rerun-importer-osim/test_data/RajagopalData/Rajagopal2015.osim")
lm_pos = landmark_world_positions(m.skeleton)

# Print current segment lengths from landmarks
print("=" * 60)
print("Baseline segment lengths from landmarks:")
print("=" * 60)
baseline: dict[str, float] = {}
for rule in RAJAGOPAL_MEASUREMENT_RULES:
    try:
        length = measure_segment(rule, lm_pos)
        baseline[rule.segment] = length
        desc = " x ".join(rule.landmark_names)
        links = ", ".join(rule.link_ids)
        print(f"  {rule.segment:<20} {length:.4f} m  ({desc}) → [{links}]")
    except (ValueError, KeyError) as e:
        print(f"  {rule.segment:<20} SKIP ({e})")

# Apply scaling: increase femur lengths by 10%
print("\n" + "=" * 60)
print("Scaling: femur_r +10%, shank_r +5%, max 75 kg")
print("=" * 60)
subject_measurements = {
    "thigh_r": baseline["thigh_r"] * 1.10,
    "shank_r": baseline["shank_r"] * 1.05,
}

result = scale_by_landmarks(
    m.skeleton,
    lm_pos,
    subject_measurements,
    target_mass=75.0,
)

print(f"Scale factors:")
for name, sf in sorted(result.link_scale_factors.items()):
    if abs(sf - 1.0) > 0.01:
        print(f"  {name}: x{sf:.4f}")
print(f"Mass: {result.total_mass_before:.2f} → {result.total_mass_after:.2f} kg")
print(f"Matched: {result.matched_segments}")
print(f"Unmatched: {result.unmatched_segments}")
print(f"Warnings: {result.warnings}")

# Verify
assert abs(result.link_scale_factors.get("femur_r", 0) - 1.10) < 0.02
assert abs(result.link_scale_factors.get("tibia_r", 0) - 1.05) < 0.02
assert abs(result.total_mass_after - 75.0) < 0.1
print("\n✓ Landmark-based scaling verified")
