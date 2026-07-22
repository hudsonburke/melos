"""Test MHR adapter with the generated reference bundle."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "packages/melos-core/src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "packages/melos-skin/src"))

# Load the model
from melos.backend.app import load_model_from_osim
m = load_model_from_osim("/var/lib/hermes/rerun-importer-osim/test_data/RajagopalData/Rajagopal2015.osim")
print(f"Model: {m.name}")
print(f"Skeleton: {len(m.skeleton.links)} links, {len(m.skeleton.joints)} joints")

# Load the reference bundle
from melos.skin.adapters.skin_bundle import load_example_skin_reference_bundle
bundle = load_example_skin_reference_bundle(
    Path("resources/third_party/skin/SOMA_neutral_reference.npz")
)
assert bundle is not None, "Failed to load reference bundle"
print(f"\nBundle loaded:")
print(f"  Joints: {len(bundle['joints'])}")
print(f"  Joint names: {sorted(bundle['joint_names'])[:8]}...")
print(f"  Vertices: {len(bundle['vertices'])}")
print(f"  Skin weights: {len(bundle['weight_data'])}")

# Patch the bundle so it looks like an MHR bundle
bundle["joint_names"] = [
    "pelvis", "femur_r", "tibia_r", "talus_r", "calcn_r", "toes_r",
    "femur_l", "tibia_l", "talus_l", "calcn_l", "toes_l",
    "torso",
    "humerus_r", "ulna_r", "radius_r", "hand_r",
    "humerus_l", "ulna_l", "radius_l", "hand_l",
]

# Map SOMA joint names to myofullbody names for the translation rules
bundle["joints"] = {}
jp = bundle["bind_pose_world"]  # (n, 4, 4) transforms
for i, name in enumerate(bundle["joint_names"]):
    bundle["joints"][name] = (float(jp[i][0][3]), float(jp[i][1][3]), float(jp[i][2][3]))

# Print joint positions
import json
print(f"\nJoint positions (cm):")
for name in ["pelvis", "femur_r", "tibia_r", "talus_r", "calcn_r", "toes_r"]:
    p = bundle["joints"].get(name, (0,0,0))
    print(f"  {name}: ({p[0]:.1f}, {p[1]:.1f}, {p[2]:.1f})")

# Run segment measurements from bundle
from melos.core.retarget.model import JointPositionSet
from melos.core.retarget.measurements import compute_segment_measurements_from_rules
from melos.skin.mappings.myofullbody_to_human_v1 import MYOFULLBODY_TO_HUMAN_V1

joint_set = JointPositionSet(
    positions=dict(bundle["joints"]),
    space="bind_pose_world",
    units="cm",
)
measurements = compute_segment_measurements_from_rules(
    joint_set,
    MYOFULLBODY_TO_HUMAN_V1.rules,
    units="cm",
)

print(f"\nSegment measurements from MHR bundle:")
for item in measurements.items:
    print(f"  {item.segment_id:20s} = {item.length/100.0:.3f} m")

# Now test full scaling pipeline
from melos.backend.mhr_adapter import scale_skeleton_from_mhr
result = scale_skeleton_from_mhr(m.skeleton, bundle, target_mass=75.0)

print(f"\nMHR scaling result:")
report = result.get("scale_report", {})
if report and report.get("link_scale_factors"):
    for name, sf in sorted(report["link_scale_factors"].items()):
        if abs(sf - 1.0) > 0.02:
            print(f"  {name}: x{sf:.3f}")
    print(f"  Mass: {report.get('total_mass_before', '?'):.2f} → {report.get('total_mass_after', '?'):.2f} kg")
else:
    print("  No non-unit scale factors (expected — no MHR joint mapping)")
    print(f"  Segment lengths extracted: {len(result.get('segment_lengths', {}))}")

print(f"\nSkin bundle in result:")
skin = result.get("skin_bundle", {})
print(f"  Vertices: {len(skin.get('vertices', []))}")
print(f"  Faces: {len(skin.get('faces', []))}")
print(f"  Joints: {len(skin.get('joints', {}))}")
print(f"  Weights: {len(skin.get('weight_data', []))} entries")
print("OK")
