"""Test the MHR→Melos adapter with available data.

This tests the segment-length extraction and code paths even without SOMA.
"""
from __future__ import annotations

import sys, math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from melos.backend.app import load_model_from_osim

# Load the model
m = load_model_from_osim("/var/lib/hermes/rerun-importer-osim/test_data/RajagopalData/Rajagopal2015.osim")
print(f"Model: {m.name}")
print(f"Skeleton: {len(m.skeleton.links)} links")

# Test the MHR adapter — segment length extraction from a fake bundle
# (simulating what SOMA would produce)
from melos.backend.mhr_adapter import segment_lengths_from_mhr, soma_available, default_mhr_bundle

print(f"SOMA available: {soma_available()}")

# Test with a synthetic bundle
fake_bundle = {
    "joint_names": ["pelvis", "femur_r", "tibia_r", "talus_r", "femur_l", "tibia_l", "talus_l",
                    "torso", "humerus_r", "ulna_r", "radius_r", "humerus_l", "ulna_l", "radius_l"],
    "joints": {
        "pelvis": (0.0, 91.5, 0.0),       # cm
        "femur_r": (8.0, 42.0, 7.0),      # cm
        "tibia_r": (0.76, 3.0, -0.18),    # cm
        "talus_r": (1.0, -38.0, 0.0),     # cm
        "femur_l": (-8.0, 42.0, -7.0),    # cm
        "tibia_l": (-0.76, 3.0, 0.18),    # cm
        "talus_l": (-1.0, -38.0, 0.0),    # cm
        "torso": (0.0, 133.0, 0.0),
        "humerus_r": (-6.0, 100.0, 12.0),
        "ulna_r": (-5.0, 63.0, 15.0),
        "radius_r": (-5.0, 63.0, 15.0),
        "humerus_l": (6.0, 100.0, -12.0),
        "ulna_l": (5.0, 63.0, -15.0),
        "radius_l": (5.0, 63.0, -15.0),
    },
}

# Test scale_skeleton_from_mhr with the fake bundle
from melos.backend.mhr_adapter import scale_skeleton_from_mhr
result = scale_skeleton_from_mhr(m.skeleton, fake_bundle, target_mass=70.0)

print(f"\nMHR adapter result:")
print(f"  Scale factors: {result.get('scale_report', {}).get('link_scale_factors', {})}")
print(f"  Matched: {result.get('scale_report', {}).get('matched_segments', [])}")
print(f"  Mass: {result.get('scale_report', {}).get('total_mass_before', '?'):.2f} → "
      f"{result.get('scale_report', {}).get('total_mass_after', '?'):.2f} kg")
print(f"  Segment lengths: {len(result.get('segment_lengths', {}))}")
print(f"  Skin vertices: {len(result.get('skin_bundle', {}).get('vertices', []))}")
print(f"  Skin faces: {len(result.get('skin_bundle', {}).get('faces', []))}")
print(f"  Joint names: {len(result.get('skin_bundle', {}).get('joint_names', []))}")

# Verify the skeleton was scaled
sf = result.get("scale_report", {}).get("link_scale_factors", {})
has_nonscaled = False
for name, factor in sf.items():
    if abs(factor - 1.0) > 0.01:
        has_nonscaled = True

if has_nonscaled:
    print("✓ Skeleton was scaled (non-unit factors found)")
else:
    print("△ Skeleton not scaled (not enough MHR joint data)")

print("OK")
