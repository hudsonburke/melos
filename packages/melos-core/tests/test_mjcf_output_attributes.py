"""Verify critical MJCF output attributes produced by the compiler."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
import tempfile

import pytest


# ── Fixtures ────────────────────────────────────────────────────────────────

FIXTURE_ANGLE_RADIAN = """\
<mujoco model="test_angle">
  <compiler angle="radian"/>
  <worldbody>
    <body name="parent" pos="0 0 0">
      <body name="root">
        <joint name="hinge_joint" type="hinge" axis="0 0 1" range="-1.57 1.57" limited="true"/>
      </body>
    </body>
  </worldbody>
</mujoco>
"""

FIXTURE_ANGLE_DEGREE = """\
<mujoco model="test_angle">
  <compiler angle="degree"/>
  <worldbody>
    <body name="parent" pos="0 0 0">
      <body name="root">
        <joint name="hinge_joint" type="hinge" axis="0 0 1" range="-90 90" limited="true"/>
      </body>
    </body>
  </worldbody>
</mujoco>
"""
FIXTURE_MIRRORED_MESH = """\
<mujoco model="test_mirror">
  <compiler angle="radian" meshdir="meshes"/>
  <asset>
    <mesh name="bone_r" file="bone.stl" scale="1 1 1"/>
    <mesh name="bone_l" file="bone.stl" scale="1 1 -1"/>
  </asset>
  <worldbody>
    <body name="right_side" pos="0 0 0.1">
      <geom name="bone_r_geom" type="mesh" mesh="bone_r"/>
    </body>
    <body name="left_side" pos="0 0 -0.1">
      <geom name="bone_l_geom" type="mesh" mesh="bone_l"/>
    </body>
  </worldbody>
</mujoco>
"""

FIXTURE_TENDON_LEFT_RIGHT = """\
<mujoco model="test_tendons">
  <compiler angle="radian"/>
  <worldbody>
    <body name="origin" pos="0 0 0">
      <site name="anchor_site" pos="0 0 0"/>
      <body name="target_r" pos="0.05 0 0.05">
        <site name="insertion_r" pos="0 0 0"/>
      </body>
      <body name="target_l" pos="-0.05 0 -0.05">
        <site name="insertion_l" pos="0 0 0"/>
      </body>
    </body>
  </worldbody>
  <tendon>
    <spatial name="biceps_tendon">
      <site site="anchor_site"/>
      <site site="insertion_r"/>
    </spatial>
    <spatial name="biceps_tendon_left">
      <site site="anchor_site"/>
      <site site="insertion_l"/>
    </spatial>
  </tendon>
  <actuator>
    <general name="biceps" tendon="biceps_tendon" gainprm="1 2 3 4 5 6 7 8 9 10" biasprm="1 2 3 4 5 6 7 8 9 10" dynprm="0.01 0.04 0 0 0 0 0 0 0 0" lengthrange="0.1 0.3"/>
    <general name="biceps_left" tendon="biceps_tendon_left" gainprm="5 6 7 8 9 10 11 12 13 14" biasprm="5 6 7 8 9 10 11 12 13 14" dynprm="0.02 0.05 0 0 0 0 0 0 0 0" lengthrange="0.15 0.35" force="550"/>
  </actuator>
</mujoco>
"""

FIXTURE_GEOM_POS_QUAT = """\
<mujoco model="test_geom_attrs">
  <compiler angle="radian"/>
  <asset>
    <mesh name="skull" file="skull.stl"/>
    <mesh name="ribcage" file="ribcage.stl"/>
  </asset>
  <worldbody>
    <body name="torso" pos="0 0 0">
      <geom name="ribcage_geom" type="mesh" mesh="ribcage" pos="0.028 0.365 0"/>
      <body name="head" pos="0 0.5 0">
        <geom name="skull_geom" type="mesh" mesh="skull" pos="0 -0.5 0" euler="0 0 -0.2"/>
      </body>
    </body>
  </worldbody>
</mujoco>
"""


# ── Helper ──────────────────────────────────────────────────────────────────

def _compile_fixture(tmp_path: Path, xml_text: str) -> str:
    """Write fixture XML to a temp file, import, compile, return MJCF text."""
    from melos.sim import compile_project, import_mjcf

    fixture = tmp_path / "model.xml"
    fixture.write_text(xml_text)
    result = import_mjcf(fixture)
    compile_result = compile_project(result.project, validate=False)
    return compile_result.mjcf_text


def _resolve_mesh_paths(tmp_path: Path, xml_text: str) -> str:
    """Create dummy mesh files so map_assets doesn't warn."""
    meshes_dir = tmp_path / "meshes"
    meshes_dir.mkdir(exist_ok=True)
    for mesh_name in ("bone.stl", "skull.stl", "ribcage.stl"):
        (meshes_dir / mesh_name).write_text("dummy")
    return xml_text


# ── Tests ───────────────────────────────────────────────────────────────────

class TestCompilerAngleAttribute:
    """The compiled MJCF must include compiler angle='radian' when the source uses radians."""

    def test_radian_source_preserves_angle_radian(self, tmp_path: Path) -> None:
        mjcf = _compile_fixture(tmp_path, FIXTURE_ANGLE_RADIAN)
        assert 'angle="radian"' in mjcf, f"Missing angle=radian in:\n{mjcf[:300]}"

    def test_degree_source_outputs_radian(self, tmp_path: Path) -> None:
        """Even degree sources should output radian (melos normalizes to radians)."""
        mjcf = _compile_fixture(tmp_path, FIXTURE_ANGLE_DEGREE)
        assert 'angle="radian"' in mjcf, f"Missing angle=radian in:\n{mjcf[:300]}"

    def test_joint_range_preserved(self, tmp_path: Path) -> None:
        """Joint ranges written as radian values when angle=radian."""
        mjcf = _compile_fixture(tmp_path, FIXTURE_ANGLE_RADIAN)
        root = ET.fromstring(mjcf)
        joint = root.find(".//joint")
        assert joint is not None
        range_str = joint.get("range", "")
        low, high = (float(v) for v in range_str.split())
        assert abs(low - (-1.57)) < 0.01, f"Expected range start ~-1.57, got {low}"
        assert abs(high - 1.57) < 0.01, f"Expected range end ~1.57, got {high}"


class TestMeshScalePreservation:
    """Mirrored meshes (scale='1 1 -1') must be preserved in compiled output."""

    def test_mirrored_mesh_scale_in_asset_section(self, tmp_path: Path) -> None:
        xml_text = _resolve_mesh_paths(tmp_path, FIXTURE_MIRRORED_MESH)
        mjcf = _compile_fixture(tmp_path, xml_text)
        # Parse and check mesh elements
        root = ET.fromstring(mjcf)
        meshes = {
            m.get("name"): m.get("scale")
            for m in root.findall("asset/mesh")
            if m.get("name") in ("bone_r", "bone_l")
        }
        assert meshes.get("bone_r") == "1 1 1", f"bone_r scale: {meshes.get('bone_r')}"
        assert meshes.get("bone_l") == "1 1 -1", f"bone_l scale: {meshes.get('bone_l')}"


class TestGeomPosAndQuatPreservation:
    """Geom pos and rotation attributes must survive roundtrip."""

    def test_geom_pos_appears_in_output(self, tmp_path: Path) -> None:
        xml_text = _resolve_mesh_paths(tmp_path, FIXTURE_GEOM_POS_QUAT)
        mjcf = _compile_fixture(tmp_path, xml_text)
        root = ET.fromstring(mjcf)
        # Find ribcage geom — should have pos
        ribs = root.find(".//geom[@mesh='ribcage']")
        assert ribs is not None, "ribcage geom not found"
        pos = ribs.get("pos", "")
        assert "0.028" in pos and "0.365" in pos, f"ribcage pos={pos}"

    def test_geom_euler_converted_to_quat(self, tmp_path: Path) -> None:
        xml_text = _resolve_mesh_paths(tmp_path, FIXTURE_GEOM_POS_QUAT)
        mjcf = _compile_fixture(tmp_path, xml_text)
        root = ET.fromstring(mjcf)
        # Find skull geom — should have quat from euler="0 0 -0.2"
        skull = root.find(".//geom[@mesh='skull']")
        assert skull is not None, "skull geom not found"
        # Should have quat (converted from euler)
        quat = skull.get("quat", "")
        assert quat, f"skull geom missing quat attribute"
        # Also check pos
        pos = skull.get("pos", "")
        assert "-0.5" in pos, f"skull pos={pos}"


class TestTendonLeftRightSuffixStripping:
    """Tendon names with _tendon_left/_tendon_right must correctly match muscle physiology."""

    def test_left_muscle_retains_lengthrange(self, tmp_path: Path) -> None:
        mjcf = _compile_fixture(tmp_path, FIXTURE_TENDON_LEFT_RIGHT)
        root = ET.fromstring(mjcf)

        # Both muscles should be <general> with lengthrange
        for expected_name in ("anatomical_muscle_biceps", "anatomical_muscle_biceps_left"):
            muscle = root.find(f"./actuator/general[@name='{expected_name}']")
            assert muscle is not None, f"Missing {expected_name}"

            lr = muscle.get("lengthrange")
            assert lr is not None, f"Missing lengthrange on {expected_name}"

        # Verify tendon names don't have double _tendon
        for spatial in root.findall("tendon/spatial"):
            name = spatial.get("name", "")
            assert "_tendon_tendon" not in name, f"Double tendon suffix: {name}"

    def test_left_muscle_preserves_gainprm(self, tmp_path: Path) -> None:
        mjcf = _compile_fixture(tmp_path, FIXTURE_TENDON_LEFT_RIGHT)
        root = ET.fromstring(mjcf)

        left = root.find("./actuator/general[@name='anatomical_muscle_biceps_left']")
        assert left is not None
        gainprm = left.get("gainprm", "")
        # Should start with the left-specific values (5 6 7...)
        assert gainprm.startswith("5 "), f"gainprm={gainprm}"


class TestCompileProjectDoesNotCrash:
    """The full pipeline must not crash on any fix point."""

    def test_myofullbody_compiles(self) -> None:
        """The full MyoFullBody model must compile without errors."""
        from melos.sim import compile_project, import_mjcf

        original = Path(__file__).parent.parent.parent.parent / (
            "resources/third_party/myofullbody/body/myofullbody.xml"
        )
        if not original.exists():
            pytest.skip("MyoFullBody not available")

        # Import and compile
        result = import_mjcf(str(original))
        compile_result = compile_project(result.project, validate=False)

        # Verify the MJCF loads in MuJoCo
        import mujoco
        with tempfile.TemporaryDirectory() as td:
            mjcf_path = Path(td) / "model.xml"
            mjcf_path.write_text(compile_result.mjcf_text)
            spec = mujoco.MjSpec.from_file(str(mjcf_path))
            model = spec.compile()
            assert model.nbody > 50, f"Expected >50 bodies, got {model.nbody}"
            assert model.ntendon > 100, f"Expected >100 tendons, got {model.ntendon}"
