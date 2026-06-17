"""Focused tests for the shared-system MJCF importer."""

from __future__ import annotations

from pathlib import Path
import pytest


from melos.core.common.types import AssetRole
from melos.core.system.enums import ActuatorKind, GeometryRole, SystemRole
from melos.sim.mujoco.importers.report import ImportReport, ImportWarning


def test_import_report_add_warning() -> None:
    report = ImportReport()
    report.add_warning(code="TEST001", message="test message", location="test:1")
    assert len(report.warnings) == 1
    warning = report.warnings[0]
    assert warning.code == "TEST001"
    assert warning.message == "test message"
    assert warning.location == "test:1"


def test_import_warning_fields() -> None:
    warning = ImportWarning(code="X", message="msg", location="loc")
    assert warning.code == "X"
    assert warning.message == "msg"
    assert warning.location == "loc"


def _write_simple_fixture(tmp_path: Path) -> Path:
    fixture = tmp_path / "simple.xml"
    fixture.write_text(
        """
        <mujoco model="demo">
          <worldbody>
            <body name="pelvis" pos="0 0 1">
              <geom type="mesh" mesh="pelvis_mesh"/>
              <site name="hip_site" pos="0 0 0"/>
              <joint name="hip_flexion" type="hinge" axis="1 0 0"/>
              <geom name="patella_wrap" type="sphere" size="0.03" contype="0" conaffinity="0"/>
              <body name="femur" pos="0 0 -0.4">
                <site name="knee_site" pos="0 0 0"/>
              </body>
            </body>
          </worldbody>
          <tendon>
            <spatial name="rectus_femoris_tendon">
              <site site="hip_site"/>
              <geom geom="patella_wrap"/>
              <site site="knee_site"/>
            </spatial>
          </tendon>
          <actuator>
            <muscle name="rectus_femoris" force="1200"/>
          </actuator>
        </mujoco>
        """.strip()
    )
    return fixture


def test_import_mjcf_builds_anatomical_system(tmp_path: Path) -> None:
    from melos.sim.mujoco.importers import import_mjcf

    fixture = _write_simple_fixture(tmp_path)

    result = import_mjcf(fixture)
    project = result.project

    assert len(project.systems) == 1
    system = project.systems[0]
    assert system.role is SystemRole.ANATOMICAL
    assert system.root_link_id == "pelvis"
    assert [link.id for link in system.links] == ["pelvis", "femur"]
    assert {site.id for site in system.sites} == {"hip_site", "knee_site"}
    assert system.joints[0].child_link_id == "pelvis"
    assert system.actuators[0].kind is ActuatorKind.MUSCLE
    assert system.actuators[0].site_ids == ["hip_site", "knee_site"]
    assert system.actuators[0].parameters["wrap_geometry_ids"] == ["patella_wrap"]
    assert system.actuators[0].parameters["physiology"]["max_isometric_force"] == 1200.0
    assert system.geometries[0].role is GeometryRole.WRAP
    assert any(link.asset_ids for link in system.links)


def test_import_mjcf_groups_multiple_body_joints_into_one_core_joint(tmp_path: Path) -> None:
    from melos.sim.mujoco.importers import import_mjcf

    fixture = tmp_path / "multi-joint-body.xml"
    fixture.write_text(
        """
        <mujoco model="demo">
          <worldbody>
            <body name="parent">
              <body name="child" pos="0 0 1">
                <joint name="child_rx" type="hinge" axis="1 0 0"/>
                <joint name="child_ry" type="hinge" axis="0 1 0"/>
              </body>
            </body>
          </worldbody>
        </mujoco>
        """.strip()
    )

    result = import_mjcf(fixture)
    system = result.project.systems[0]
    child_joint = next(joint for joint in system.joints if joint.child_link_id == "child")

    assert child_joint.id == "child_joint"
    assert child_joint.parent_link_id == "parent"
    assert [coordinate.id for coordinate in child_joint.coordinates] == ["child_rx", "child_ry"]
    assert [coordinate.axis for coordinate in child_joint.coordinates] == [
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
    ]



def test_import_mjcf_collects_mesh_assets_from_default_class_mesh_geoms(tmp_path: Path) -> None:
    from melos.sim.mujoco.importers import import_mjcf

    mesh_path = tmp_path / "humerus.stl"
    mesh_path.write_bytes(b"0" * 84)

    fixture = tmp_path / "default-class-mesh.xml"
    fixture.write_text(
        """
        <mujoco model="demo">
          <default>
            <default class="bone">
              <geom type="mesh"/>
            </default>
          </default>
          <asset>
            <mesh name="humerus_mesh" file="humerus.stl"/>
          </asset>
          <worldbody>
            <body name="humerus" pos="0 0 1">
              <geom class="bone" mesh="humerus_mesh" pos="0 0 0.1"/>
            </body>
          </worldbody>
        </mujoco>
        """.strip()
    )

    result = import_mjcf(fixture)
    system = result.project.systems[0]
    humerus = next(link for link in system.links if link.id == "humerus")
    mesh_asset = next(asset for asset in result.project.assets.items if asset.id == "humerus_mesh")

    assert humerus.asset_ids == ["humerus_mesh"]
    assert mesh_asset.role is AssetRole.VISUAL
    assert mesh_asset.annotations["mjcf_geom_pos"] == "0 0 0.1"




class TestEulerToQuat:
    """Verify euler_to_quat matches MuJoCo's internal ZYX-intrinsic conversion."""

    @staticmethod
    def _euler_to_quat(euler_str: str) -> tuple[float, float, float, float]:
        from melos.sim.mujoco.importers.quat_utils import euler_to_quat
        return euler_to_quat(euler_str)

    @staticmethod
    def _mj_euler_to_quat(ex: float, ey: float, ez: float) -> tuple[float, float, float, float]:
        """Get MuJoCo's own conversion via XML round-trip (with compiler angle='radian')."""
        import mujoco
        xml = (
            '<mujoco>'
            '<compiler angle="radian"/>'
            '<worldbody>'
            f'<body name="t" euler="{ex} {ey} {ez}"/>'
            '</worldbody>'
            '</mujoco>'
        )
        spec = mujoco.MjSpec.from_string(xml)
        model = spec.compile()
        q = model.body_quat[1]
        return (float(q[0]), float(q[1]), float(q[2]), float(q[3]))

    @pytest.mark.parametrize(
        "ex,ey,ez",
        [
            (1.57, -1.57, 0),
            (0, 0, 0),
            (1.57, 0, 0),
            (0, 1.57, 0),
            (0, 0, 1.57),
            (0.5, -0.3, 0.8),
            (-0.785, 0.523, -0.262),
            (3.0, -0.5, 1.2),
        ],
    )
    def test_matches_mujoco(self, ex: float, ey: float, ez: float) -> None:
        """euler_to_quat must match MuJoCo exactly for radian-valued euler strings."""
        euler_str = f"{ex} {ey} {ez}"
        our_quat = self._euler_to_quat(euler_str)
        mj_quat = self._mj_euler_to_quat(ex, ey, ez)
        for a, b in zip(our_quat, mj_quat):
            assert abs(a - b) < 1e-12, f"Mismatch for ({ex}, {ey}, {ez}): ours={our_quat}, mj={mj_quat}"
