"""Test MJCF round-trip: parse MyoSuite model → Arrow → compile back to MJCF."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from melos.backend.mjcf_parser import parse_mjcf
from melos.backend.mjcf_compiler import compile_skeleton

# MyoSuite elbow model with exo
mjcf_path = Path("/var/lib/hermes/myosuite/myosuite/simhive/myo_sim/elbow/myoelbow_1dof6muscles_1dofexo.xml")

if not mjcf_path.exists():
    print(f"Model not found: {mjcf_path}")
    sys.exit(1)

print(f"Parsing: {mjcf_path}")
try:
    skeleton = parse_mjcf(mjcf_path)
except Exception as e:
    print(f"PARSE ERROR: {e}")
    sys.exit(1)

print(f"\nParsed successfully:")
print(f"  Links: {len(skeleton.links)}")
print(f"  Joints: {len(skeleton.joints)}")
print(f"  Order: {skeleton.order}")

print(f"\nLinks:")
for name, link in skeleton.links.items():
    mass = link.mass
    mesh = link.graphics_file or "—"
    print(f"  {name}: mass={mass:.4f}kg, mesh={mesh}")

print(f"\nJoints:")
for jname, jdef in skeleton.joints.items():
    print(f"  {jname}: type={jdef.joint_type}, child={jdef.child_link}, "
          f"limits=[{jdef.limits.lower:.3f}, {jdef.limits.upper:.3f}]")

print(f"\nParent map:")
for child, parent in skeleton.parent_map.items():
    print(f"  {child} → {parent}")

print(f"\n=== Round-trip compile ===")
try:
    xml = compile_skeleton(skeleton, "myoelbow_roundtrip")
    lines = xml.split("\n")
    print(f"Compiled: {len(lines)} lines")
    for line in lines[:20]:
        print(line)
    print("...")
    print("✓ Round-trip successful")
except Exception as e:
    print(f"COMPILE ERROR: {e}")
    import traceback
    traceback.print_exc()
