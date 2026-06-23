from __future__ import annotations

from importlib import import_module

from melos.blender.addon import bl_info
from melos.blender import (
    allocate_identifier,
    assemble_project,
    build_project_meta,
    build_simulation_config,
    build_system_model,
    format_validation_report,
    make_identifier,
)
from melos.blender.bpy_io.assets import build_asset_library_from_scene
from melos.blender.bpy_io.project import build_project_from_scene
from melos.core.system.enums import SystemRole
from melos.core.system.model import Link
from melos.core.validation import validate_project


class FakeMatrix:
    def copy(self):
        return self

    def to_translation(self):
        return (0.0, 0.0, 0.0)

    def to_quaternion(self):
        return (1.0, 0.0, 0.0, 0.0)


class FakeObject(dict):
    def __init__(self, name: str, *, object_type: str = "EMPTY") -> None:
        super().__init__()
        self.name = name
        self.type = object_type
        self.parent: FakeObject | None = None
        self.children: list[FakeObject] = []
        self.matrix_local = FakeMatrix()
        self.matrix_world = FakeMatrix()

    def get(self, key, default=None):
        return super().get(key, default)


class FakeSettings:
    project_id = "project"
    project_name = "Anatomical System Authoring"
    project_description = ""
    created_by = ""
    anatomical_system_id = "anatomical"
    anatomical_system_name = "anatomical"
    anatomical_system_description = ""
    anatomical_species = "human"
    anatomical_system_root_link_id = "pelvis"
    device_id = "device"
    device_name = "device"
    device_root_link_id = ""
    time_step = 0.001
    duration = 0.0
    gravity_x = 0.0
    gravity_y = 0.0
    gravity_z = -9.81


class FakeScene:
    def __init__(self, objects: list[FakeObject]) -> None:
        self.objects = objects
        self.melos_blender = FakeSettings()


def test_blender_namespace_import() -> None:
    module = import_module("melos.blender")
    assert module.__version__ == "0.1.0"


def test_blender_addon_metadata_uses_melos_branding() -> None:
    assert bl_info["name"] == "melos"
    assert bl_info["location"] == "View3D > Sidebar > melos"


def test_identifier_helpers_normalize_and_deduplicate() -> None:
    assert make_identifier("1 Left Thigh", fallback="body") == "body_1_Left_Thigh"
    assert allocate_identifier("Left Thigh", {"Left_Thigh"}, fallback="body") == "Left_Thigh_2"


def test_project_builders_assemble_valid_project() -> None:
    body = Link(id="pelvis", name="Pelvis")
    system = build_system_model(system_id="anatomical", name="anatomical", role=SystemRole.ANATOMICAL, links=[body])
    meta = build_project_meta(project_id="authoring_project", name="Authoring Project")
    simulation = build_simulation_config(time_step=0.002)

    project = assemble_project(meta=meta, systems=[system], simulation=simulation)
    report = validate_project(project)

    assert project.meta.id == "authoring_project"
    assert project.systems[0].root_link_id == "pelvis"
    assert project.simulation.time_step == 0.002
    assert format_validation_report(report) == ["No validation issues found."]


def test_build_asset_library_from_scene_collects_body_mesh_assets() -> None:
    mesh = FakeObject("pelvis_mesh", object_type="MESH")
    mesh["melos_entity_kind"] = "anatomical_link_asset"
    mesh["melos_asset_id"] = "pelvis_visual"
    mesh["melos_asset_name"] = "Pelvis Mesh"
    mesh["melos_asset_role"] = "visual"
    mesh["melos_asset_uri"] = "blender://object/pelvis_mesh"
    scene = FakeScene([mesh])

    assets = build_asset_library_from_scene(scene)

    assert len(assets.items) == 1
    assert assets.items[0].id == "pelvis_visual"
    assert assets.items[0].uri == "blender://object/pelvis_mesh"


def test_build_project_from_scene_includes_body_asset_ids() -> None:
    body = FakeObject("pelvis_body")
    body["melos_entity_kind"] = "anatomical_link"
    body["melos_id"] = "pelvis"
    body["melos_name"] = "Pelvis"

    mesh = FakeObject("pelvis_mesh", object_type="MESH")
    mesh["melos_entity_kind"] = "anatomical_link_asset"
    mesh["melos_id"] = "pelvis"
    mesh["melos_asset_id"] = "pelvis_visual"
    mesh["melos_asset_name"] = "Pelvis Mesh"
    mesh["melos_asset_role"] = "visual"
    mesh["melos_asset_uri"] = "blender://object/pelvis_mesh"
    mesh.parent = body
    body.children.append(mesh)

    scene = FakeScene([body, mesh])
    project = build_project_from_scene(scene)

    assert project.assets.items[0].id == "pelvis_visual"
    assert project.systems[0].links[0].asset_ids == ["pelvis_visual"]
