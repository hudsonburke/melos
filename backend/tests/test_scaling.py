"""Tests for backend scaling utility with real model data."""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / ".venv/lib/python3.14/site-packages"))

from melos.backend.app import load_model_from_osim
from melos.backend.scaling import by_segment_lengths, by_bone_vectors


OSIM_PATH = "/var/lib/hermes/rerun-importer-osim/test_data/RajagopalData/Rajagopal2015.osim"

# Load model
m = load_model_from_osim(OSIM_PATH)
print(f"Model: {m.name}")
print(f"Skeleton: {len(m.skeleton.joints)} joints, {len(m.skeleton.links)} links")

# ── Test 1: Segment-length scaling ────────────────────────────────────────

# Simulate subject measurements: 10% larger femur, 5% larger tibia
# Current lengths (from transform translations):
s = m.skeleton
femur_len = math.sqrt(s.transforms["femur_r"].translation[0]**2 + 
                       s.transforms["femur_r"].translation[1]**2 +
                       s.transforms["femur_r"].translation[2]**2)
tibia_len = math.sqrt(s.transforms["tibia_r"].translation[0]**2 +
                       s.transforms["tibia_r"].translation[1]**2 +
                       s.transforms["tibia_r"].translation[2]**2)
pelvis_len = math.sqrt(s.transforms["pelvis"].translation[0]**2 +
                        s.transforms["pelvis"].translation[1]**2 +
                        s.transforms["pelvis"].translation[2]**2)

print(f"\nBaseline lengths: pelvis={pelvis_len:.4f}, femur={femur_len:.4f}, tibia={tibia_len:.4f}")

result = by_segment_lengths(
    m.skeleton,
    target_lengths={
        "thigh": femur_len * 1.10,
        "shank": tibia_len * 1.05,
        "torso_height": pelvis_len * 1.08,
    },
    segment_to_link={
        "thigh": "femur_r",
        "shank": "tibia_r",
        "torso_height": "pelvis",
    },
    target_mass=85.0,
)

print(f"\nTest 1 — Segment-length scaling:")
print(f"  Matched: {result.matched_segments[:5]}...")
print(f"  Scale factors (first 5): {dict(list(result.link_scale_factors.items())[:5])}")
print(f"  Total mass: {result.total_mass_before:.2f} → {result.total_mass_after:.2f} kg")
print(f"  Warnings: {result.warnings}")

# Verify femur_r was scaled by ~1.10
femur_sf = result.link_scale_factors.get("femur_r", 0)
assert abs(femur_sf - 1.10) < 0.01, f"Femur scale factor {femur_sf} != 1.10"
print("  ✓ Femur scaled correctly (×1.10)")

# Verify tibia_r was scaled by ~1.05
tibia_sf = result.link_scale_factors.get("tibia_r", 0)
assert abs(tibia_sf - 1.05) < 0.01, f"Tibia scale factor {tibia_sf} != 1.05"
print("  ✓ Tibia scaled correctly (×1.05)")

# Verify mass was normalised to 85 kg
assert abs(result.total_mass_after - 85.0) < 0.1
print("  ✓ Mass normalised to 85.0 kg")

# ── Test 2: Bone-vector scaling ──────────────────────────────────────────

result2 = by_bone_vectors(
    m.skeleton,
    target_vectors={
        "hip_r": (0.0, 0.0, -0.50),
        "knee_r": (0.0, 0.0, -0.45),
    },
    joint_to_link={
        "hip_r": "femur_r",
        "knee_r": "tibia_r",
    },
    target_mass=75.0,
)

print(f"\nTest 2 — Bone-vector scaling:")
for m in result2.matched_segments[:4]:
    print(f"  {m}")
print(f"  Total mass: {result2.total_mass_before:.2f} → {result2.total_mass_after:.2f} kg")

# ── Test 3: Verify scaled skeleton produces valid JSON ───────────────────

import json
data = result.scaled_skeleton.model_dump_json()
parsed = json.loads(data)
assert "transforms" in parsed
assert "links" in parsed
assert len(parsed["links"]) == 22  # same number as original
print(f"\nTest 3 — Serialization: ✓ {len(parsed['links'])} links serialized to JSON")

print("\n✓ All tests passed")
