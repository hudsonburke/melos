"""Integration tests for MJCF import + compile using the shared system model."""

from __future__ import annotations

from pathlib import Path

import pytest


FIXTURE_XML = """
<mujoco model="mini_model">
  <worldbody>
    <body name="pelvis" pos="1 2 3">
      <site name="origin_site" pos="0 0 0"/>
      <body name="femur" pos="0 0 -0.4">
        <joint name="femur_joint" type="hinge" axis="0 1 0"/>
        <site name="distal_site" pos="0 0 0"/>
      </body>
    </body>
  </worldbody>
  <tendon>
    <spatial name="hip_flexor_tendon">
      <site site="origin_site"/>
      <site site="distal_site"/>
    </spatial>
  </tendon>
  <actuator>
    <muscle name="hip_flexor" force="500"/>
  </actuator>
</mujoco>
""".strip()


def test_import_compile_roundtrip(tmp_path: Path) -> None:
    from melos.sim import compile_project, import_mjcf

    fixture = tmp_path / "mini.xml"
    fixture.write_text(FIXTURE_XML)

    result = import_mjcf(fixture)
    compile_result = compile_project(result.project, validate=False)

    assert compile_result.mjcf_text.startswith("<mujoco")
    assert 'body name="anatomical_link_pelvis"' in compile_result.mjcf_text
    assert 'body name="anatomical_link_femur"' in compile_result.mjcf_text
    assert 'spatial name="muscle_hip_flexor"' in compile_result.mjcf_text


def test_import_nonexistent_file() -> None:
    from melos.sim import import_mjcf

    with pytest.raises(FileNotFoundError):
        import_mjcf("nonexistent/path/missing.xml")


def test_import_preserves_root_link_transform_in_compiled_mjcf(tmp_path: Path) -> None:
    from melos.core.common.types import Transform
    from melos.sim import compile_project, import_mjcf

    fixture = tmp_path / "mini.xml"
    fixture.write_text(FIXTURE_XML)

    result = import_mjcf(fixture)
    anatomical = result.project.systems[0]
    root_link = next(link for link in anatomical.links if link.id == anatomical.root_link_id)
    root_link.transform = Transform(translation=(99.0, 99.0, 99.0), rotation=root_link.transform.rotation)

    compile_result = compile_project(result.project, validate=False)

    assert "99 99 99" in compile_result.mjcf_text
