"""Focused tests for the shared-system MJCF importer."""

from __future__ import annotations

from pathlib import Path

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


def test_import_mjcf_normalizes_nested_default_muscle_blocks(tmp_path: Path) -> None:
    from melos.sim.mujoco.importers import import_mjcf

    fixture = tmp_path / "nested-default-muscle.xml"
    fixture.write_text(
        """
        <mujoco model="demo">
          <default>
            <default class="forearm_muscle">
              <muscle ctrllimited="true" ctrlrange="-1 1"/>
              <tendon width="0.002"/>
            </default>
          </default>
          <worldbody>
            <body name="pelvis">
              <site name="origin_site"/>
              <site name="distal_site"/>
            </body>
          </worldbody>
          <tendon>
            <spatial name="test_tendon" class="forearm_muscle">
              <site site="origin_site"/>
              <site site="distal_site"/>
            </spatial>
          </tendon>
          <actuator>
            <muscle name="test" class="forearm_muscle" tendon="test_tendon" force="10" lengthrange="1 2"/>
          </actuator>
        </mujoco>
        """.strip()
    )

    result = import_mjcf(fixture)

    assert any(w.code == "MJCF_NORMALIZED_DEFAULT_MUSCLE" for w in result.report.warnings)
    assert result.project.systems[0].actuators[0].parameters["physiology"]["max_isometric_force"] == 10.0
