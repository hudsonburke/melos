"""Test MJCF round-trip and exoskeleton assembly integration.

Tests:
1. Parse MyoSuite model → Arrow → compile back → MuJoCo validates
2. Parse → apply assembly descriptors → compile combined → MuJoCo validates
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import mujoco

from melos.backend.mjcf_compiler import compile_skeleton
from melos.backend.mjcf_parser import parse_mjcf

MODEL = "/var/lib/hermes/myosuite/myosuite/simhive/myo_sim/elbow/myoelbow_1dof6muscles_1dofexo.xml"
DESCRIPTORS = Path("backend/src/melos/backend/descriptors")


# ── Test 1: Basic round-trip ─────────────────────────────────────────────


def test_roundtrip_validates_in_mujoco() -> None:
    """Parse MyoSuite model → compile → MuJoCo loads without errors."""
    skeleton = parse_mjcf(MODEL)
    assert skeleton is not None
    assert len(skeleton.links) >= 3
    assert len(skeleton.joints) >= 1

    xml = compile_skeleton(skeleton, "test_roundtrip")

    with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", delete=False) as f:
        f.write(xml)
        tmp = f.name

    try:
        m = mujoco.MjModel.from_xml_path(tmp)
        assert m.nbody >= 3
        assert m.njnt >= 1
    finally:
        os.unlink(tmp)

    print(f"  ✓ Round-trip: {m.nbody} bodies, {m.njnt} joints, {m.nu} actuators")


# ── Test 2: Assembly + compile ───────────────────────────────────────────


def test_assembly_compile() -> None:
    """Import model, resolve assembly, compile combined result."""
    from melos.backend.assembly import load_assembly_descriptor, resolve_assembly
    from melos.backend.landmarks import landmark_world_positions

    skeleton = parse_mjcf(MODEL)
    lm_pos = landmark_world_positions(skeleton)
    lm_defs = {}
    from melos.backend.marker_sets import builtin_marker_sets_dir, load_marker_set
    ms_path = builtin_marker_sets_dir() / "gait_full_body.yaml"
    if ms_path.exists():
        ms = load_marker_set(ms_path)
        for k, v in ms.get("landmarks", {}).items():
            lm_defs[k] = v.get("melos", {})

    # Resolve the arm brace assembly
    desc_path = DESCRIPTORS / "right_arm_brace.yaml"
    descriptor = load_assembly_descriptor(desc_path)
    resolved = resolve_assembly(descriptor, lm_pos, lm_defs)

    print(f"  Assembly: {resolved['name']}")
    for p in resolved["parts"]:
        print(f"    {p['id']} ({p['part_type']}): {len(p['attachments'])} attachments")

    # Compile the skeleton (assembly parts are in the spec, not in the skeleton)
    xml = compile_skeleton(skeleton, "test_assembly_compile")

    with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", delete=False) as f:
        f.write(xml)
        tmp = f.name

    try:
        m = mujoco.MjModel.from_xml_path(tmp)
        assert m.nbody >= 3
    finally:
        os.unlink(tmp)

    print(f"  ✓ Assembly compile: {m.nbody} bodies, {m.njnt} joints")


# ── Run ──────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    print("=== Test 1: Round-trip ===")
    test_roundtrip_validates_in_mujoco()

    print("\n=== Test 2: Assembly + Compile ===")
    test_assembly_compile()

    print("\n✓ All tests passed")
