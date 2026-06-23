from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

import pytest

import melos.blender.addon.operators.project as project_ops
from melos.blender.addon.operators.project import (
    MELOS_OT_create_example_model_project,
    MELOS_OT_create_example_project,
    MELOS_OT_toggle_example_body_mesh_references,
    _compute_example_segment_scale_factors,
    _example_body_mesh_reference_objects,
    _example_body_mesh_references_visible,
    _run_create_example_project,
)
from melos.blender.services.example_workflow import (
    _compute_example_body_mesh_display_scale,
    _compute_example_body_mesh_display_scale_factors,
    _compute_example_body_mesh_source_tail_points,
    _compute_example_display_upright_rotation,
)
from melos.sim.mujoco.adapters import build_example_human_mesh_rigging_plan
from melos.blender.bpy_io.skin_bundle import SKIN_REFERENCE_COLLECTION, SKIN_REFERENCE_PROP
from melos.blender.bpy_io.skinned_import import compute_system_link_world_transforms
from melos.blender.constants import ENTITY_ID_KEY, ENTITY_KIND_KEY, ANATOMICAL_LINK_KIND
from melos.core.common.assets import AssetRecord
from melos.core.common.types import AssetRole, Transform
from melos.core.common.enums import JointKind
from melos.core.common.enums import SystemRole
from melos.core.system.model import Joint, Link, SystemModel
from melos.skin.adapters import build_example_mhr_skin_bundle
from melos.skin.mappings.myofullbody_to_human_v1 import build_myofullbody_translation_map


class FakeObject(dict):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.type = "EMPTY"
        self.parent = None
        self.children: list = []
        self.empty_display_type = ""
        self.display_type = ""
        self.show_in_front = False
        self.hide_viewport = False
        self.hide_render = False
        self.show_transparent = False
        self.color = (1.0, 1.0, 1.0, 1.0)

    def get(self, key, default=None):
        return super().get(key, default)


class FakeCollection:
    def __init__(self, name: str = "") -> None:
        self.name = name
        self.linked: list[FakeObject] = []
        self.objects: list[FakeObject] = []

    def link(self, obj: FakeObject) -> None:
        self.linked.append(obj)
        self.objects.append(obj)


class FakeSettings:
    project_id = ""
    project_name = ""
    anatomical_system_id = ""
    anatomical_system_name = ""
    anatomical_system_root_link_id = ""


class FakeScene:
    def __init__(self):
        self.objects: list[FakeObject] = []
        self.melos_blender = FakeSettings()
        self.collection = FakeCollection("Scene Collection")
        self.collections: list[FakeCollection] = []


class FakeContext:
    def __init__(self, scene: FakeScene) -> None:
        self.scene = scene


@lru_cache(maxsize=1)
def _mhr_runtime_available() -> bool:
    return (
        build_example_mhr_skin_bundle(
            Path(__file__).resolve().parents[3]
            / "resources"
            / "third_party"
            / "skin"
        )
        is not None
    )



def fake_create_object(name: str, collection: FakeCollection) -> FakeObject:
    obj = FakeObject(name)
    collection.link(obj)
    return obj



def _make_arm_factory(scene):
    def _create_armature(name, data, col):
        obj = fake_create_object(name, scene.collection)
        obj["armature_data"] = data
        return obj
    return _create_armature



def _make_mesh_factory(scene):
    def _create_mesh(name, data, col):
        obj = fake_create_object(name, scene.collection)
        obj["mesh_data"] = data
        obj.modifiers = []
        return obj
    return _create_mesh



def _run(scene=None, include_skin=True):
    if not _mhr_runtime_available() and include_skin:
        pytest.skip("MHR runtime not available")
    if scene is None:
        scene = FakeScene()
    ctx = FakeContext(scene)
    project = _run_create_example_project(
        ctx,
        create_object=fake_create_object,
        create_armature_object=_make_arm_factory(scene),
        create_mesh_object=_make_mesh_factory(scene),
        include_skin=include_skin,
    )
    return scene, project



def test_compute_example_display_upright_rotation_aligns_example_long_axis_to_z() -> None:
    rotation = _compute_example_display_upright_rotation(
        {
            "pelvis": Transform(translation=(0.0, 0.0, 0.0)),
            "head": Transform(translation=(-2.0, 0.0, 0.0)),
            "femur_l": Transform(translation=(0.0, 1.0, 0.0)),
            "femur_r": Transform(translation=(0.0, -1.0, 0.0)),
        }
    )
    assert rotation is not None
    longitudinal = (
        rotation[0][0] * -2.0,
        rotation[1][0] * -2.0,
        rotation[2][0] * -2.0,
    )
    assert longitudinal[2] == pytest.approx(2.0)
    assert longitudinal[0] == pytest.approx(0.0, abs=1e-6)
    assert longitudinal[1] == pytest.approx(0.0, abs=1e-6)



def test_create_example_project_populates_scene() -> None:
    scene, _ = _run()
    body_objs = [o for o in scene.collection.linked if o.get(ENTITY_KIND_KEY) == ANATOMICAL_LINK_KIND]
    assert len(body_objs) > 50
    body_ids = {o.get(ENTITY_ID_KEY) for o in body_objs}
    assert "sacrum" in body_ids



def test_create_example_project_creates_armature_and_mesh() -> None:
    scene, project = _run()
    names = [o.name for o in scene.collection.linked]
    assert any("myofullbody_armature" in n for n in names)
    assert any("myofullbody_skin" in n for n in names)
    assert len(project.skin_attachments) >= 1
    assert any(s.id == "skin_main" for s in project.skin_attachments)



def test_create_example_project_keeps_body_mesh_visualizations() -> None:
    scene, _ = _run()
    body_meshes = [o for o in scene.collection.linked if o.name.startswith("body_")]
    assert body_meshes
    assert all(getattr(obj, "hide_viewport", False) for obj in body_meshes)
    assert all(getattr(obj, "show_in_front", False) for obj in body_meshes)



def test_example_body_mesh_reference_helpers_find_hidden_default_layer() -> None:
    scene, _ = _run()
    body_meshes = _example_body_mesh_reference_objects(scene)
    assert body_meshes
    assert _example_body_mesh_references_visible(scene) is False



def test_toggle_example_body_mesh_references_operator_shows_and_hides_layer() -> None:
    scene, _ = _run()
    ctx = FakeContext(scene)

    reported = []

    class _Op(MELOS_OT_toggle_example_body_mesh_references):
        def report(self, level, msg):
            reported.append((level, msg))

    op = _Op()
    assert _example_body_mesh_references_visible(scene) is False

    result_show = op.execute(ctx)
    assert result_show == {"FINISHED"}
    assert _example_body_mesh_references_visible(scene) is True

    result_hide = op.execute(ctx)
    assert result_hide == {"FINISHED"}
    assert _example_body_mesh_references_visible(scene) is False
    assert any(level == {"INFO"} for level, _ in reported)



def test_create_example_project_uses_mhr_mesh_on_mujoco_armature() -> None:
    scene, project = _run()
    arm_obj = next(o for o in scene.collection.linked if o.name == "myofullbody_armature")
    mesh_obj = next(o for o in scene.collection.linked if o.name == "myofullbody_skin")

    assert getattr(arm_obj, "show_in_front", False) is True
    assert getattr(mesh_obj, "show_transparent", False) is True
    assert getattr(mesh_obj, "color", (1.0, 1.0, 1.0, 1.0))[3] == pytest.approx(0.28)

    modifiers = getattr(mesh_obj, "modifiers", [])
    armature_modifiers = [modifier for modifier in modifiers if modifier.type == "ARMATURE"]
    assert len(armature_modifiers) == 1
    assert armature_modifiers[0].object is arm_obj

    bone_names = {bone.name for bone in arm_obj["armature_data"].bones}
    assert bone_names == {
        "pelvis",
        "torso",
        "thorax",
        "neck",
        "head",
        "clavicle_l",
        "humerus_l",
        "ulna_l",
        "radius_l",
        "clavicle_r",
        "humerus_r",
        "ulna_r",
        "radius_r",
        "femur_l",
        "tibia_l",
        "calcn_l",
        "femur_r",
        "tibia_r",
        "calcn_r",
    }

    mesh_data = mesh_obj["mesh_data"]
    assert set(mesh_data.vertex_groups) == {
        "pelvis",
        "torso",
        "thorax",
        "neck",
        "head",
        "clavicle_l",
        "humerus_l",
        "ulna_l",
        "radius_l",
        "clavicle_r",
        "humerus_r",
        "ulna_r",
        "radius_r",
        "femur_l",
        "tibia_l",
        "calcn_l",
        "femur_r",
        "tibia_r",
        "calcn_r",
    }

    skin_attachment = next(attachment for attachment in project.skin_attachments if attachment.id == "skin_main")
    anatomical_system = project.get_anatomical_system()
    assert anatomical_system is not None
    assert skin_attachment.target_system_id == anatomical_system.id
    assert skin_attachment.fit.fit_method == "mhr_rest_mesh_bound_to_mujoco_links_v1"
    assert skin_attachment.fit.annotations["skin_source_model"] == "mhr"
    assert skin_attachment.fit.annotations["shape_source"] == "mhr_input_model"
    assert skin_attachment.fit.annotations["kinematics_source"] == "mujoco_system_rest_armature"
    assert skin_attachment.fit.annotations["display_rig"] == "mujoco_link_rig"
    assert skin_attachment.fit.annotations["binding_mode"] == "mhr_joint_weights_collapsed_to_mujoco_links"
    assert skin_attachment.fit.annotations["mesh_pose_source"] == "aligned_mhr_rest_mesh"
    assert skin_attachment.fit.annotations["retarget_link_layer"] == "translation_map_source_links_v1"
    assert skin_attachment.fit.annotations["retarget_link_count"] == 19
    assert skin_attachment.fit.annotations["mesh_deformation_in_blender"] == "armature_modifier"



def test_create_example_project_armature_uses_skin_aligned_display_anchors() -> None:
    scene, project = _run()
    arm_obj = next(o for o in scene.collection.linked if o.name == "myofullbody_armature")
    bones = {bone.name: bone for bone in arm_obj["armature_data"].bones}

    anatomical_system = project.get_anatomical_system()
    assert anatomical_system is not None
    world_transforms = compute_system_link_world_transforms(
        anatomical_system,
        coordinate_values=project.simulation.initial_coordinate_values,
    )
    skin_bundle = build_example_mhr_skin_bundle(
        Path(__file__).resolve().parents[3]
        / "resources"
        / "third_party"
        / "skin"
    )
    assert skin_bundle is not None
    translation_map = build_myofullbody_translation_map()
    rigging_plan = build_example_human_mesh_rigging_plan(
        anatomical_system,
        world_transforms,
        skin_bundle["joints"],
        translation_map,
    )

    assert bones["thorax"].head == pytest.approx(rigging_plan.reference_body_anchors["thorax"], abs=3e-2)
    assert bones["humerus_l"].head == pytest.approx(rigging_plan.reference_body_anchors["humerus_l"], abs=3e-2)
    assert bones["ulna_l"].head == pytest.approx(rigging_plan.reference_body_anchors["ulna_l"], abs=3e-2)
    assert bones["humerus_l"].tail == pytest.approx(rigging_plan.reference_body_tail_points["humerus_l"], abs=3e-2)
    assert bones["ulna_l"].tail == pytest.approx(rigging_plan.reference_body_tail_points["ulna_l"], abs=3e-2)



def test_compute_example_body_mesh_display_scale_uses_display_to_source_segment_ratio() -> None:
    translation_map = build_myofullbody_translation_map()
    scale = _compute_example_body_mesh_display_scale(
        {
            "femur_l": Transform(translation=(0.0, 0.0, 0.0)),
            "tibia_l": Transform(translation=(2.0, 0.0, 0.0)),
            "tibia_r": Transform(translation=(0.0, 0.0, 0.0)),
            "talus_r": Transform(translation=(4.0, 0.0, 0.0)),
        },
        translation_map,
        {
            "femur_l": (10.0, 0.0, 0.0),
            "tibia_r": (20.0, 0.0, 0.0),
        },
        {
            "femur_l": (11.0, 0.0, 0.0),
            "tibia_r": (22.0, 0.0, 0.0),
        },
    )

    assert scale == pytest.approx(0.5)



def test_compute_example_body_mesh_source_tail_points_uses_translation_rule_tail_links() -> None:
    translation_map = build_myofullbody_translation_map()
    source_tail_points = _compute_example_body_mesh_source_tail_points(
        {
            "ulna_l": Transform(translation=(1.0, 0.0, 0.0)),
            "lunate_l": Transform(translation=(2.0, 3.0, 4.0)),
            "ulna_r": Transform(translation=(5.0, 0.0, 0.0)),
            "lunate_r": Transform(translation=(6.0, 7.0, 8.0)),
        },
        translation_map,
    )

    assert source_tail_points["ulna_l"] == (2.0, 3.0, 4.0)
    assert source_tail_points["ulna_r"] == (6.0, 7.0, 8.0)



def test_compute_example_body_mesh_display_scale_factors_keeps_per_link_overrides() -> None:
    translation_map = build_myofullbody_translation_map()
    scale_factors = _compute_example_body_mesh_display_scale_factors(
        {
            "humerus_l": Transform(translation=(0.0, 0.0, 0.0)),
            "ulna_l": Transform(translation=(2.0, 0.0, 0.0)),
            "femur_l": Transform(translation=(0.0, 0.0, 0.0)),
            "tibia_l": Transform(translation=(2.0, 0.0, 0.0)),
        },
        translation_map,
        {
            "humerus_l": (10.0, 0.0, 0.0),
            "femur_l": (20.0, 0.0, 0.0),
        },
        {
            "humerus_l": (14.0, 0.0, 0.0),
            "femur_l": (21.0, 0.0, 0.0),
        },
    )

    assert scale_factors["humerus_l"] == pytest.approx(2.0)
    assert scale_factors["femur_l"] == pytest.approx(0.5)



def test_create_body_mesh_objects_propagates_display_transform_to_child_links(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    dummy_asset = tmp_path / "body_child.stl"
    dummy_asset.write_bytes(b"stub")

    system = SystemModel(
        id="anatomical",
        name="Anatomical System",
        role=SystemRole.ANATOMICAL,
        root_link_id="root",
        links=[
            Link(id="root", name="Root"),
            Link(
                id="child",
                name="Child",
                transform=Transform(translation=(2.0, 0.0, 0.0)),
                asset_ids=["child_asset"],
            ),
        ],
        joints=[
            Joint(
                id="root_child",
                name="root_child",
                kind=JointKind.FIXED,
                parent_link_id="root",
                child_link_id="child",
            )
        ],
    )
    world_transforms = compute_system_link_world_transforms(system)
    project = SimpleNamespace(
        assets=SimpleNamespace(
            items=[
                AssetRecord(
                    id="child_asset",
                    name="Child Asset",
                    role=AssetRole.VISUAL,
                    uri=str(dummy_asset),
                    media_type="model/stl",
                )
            ]
        ),
        get_anatomical_system=lambda: system,
    )

    monkeypatch.setattr(
        project_ops,
        "_load_binary_stl_mesh",
        lambda _path: (
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]],
            [[0, 1, 2]],
        ),
    )

    scene = FakeScene()
    ctx = FakeContext(scene)
    body_meshes = project_ops._create_body_mesh_objects(
        project,
        ctx,
        arm_obj=None,
        world_transforms=world_transforms,
        body_objects={},
        create_mesh_object=_make_mesh_factory(scene),
        attach_to_armature=False,
        reference_body_anchors={"root": (10.0, 0.0, 0.0)},
        reference_body_tail_points={"root": (10.0, 1.0, 0.0)},
        display_scale_factor=0.5,
    )

    assert len(body_meshes) == 1
    vertices = body_meshes[0]["mesh_data"].vertices
    assert vertices[0] == pytest.approx([10.0, 1.0, 0.0])
    assert vertices[1] == pytest.approx([10.0, 1.5, 0.0])
    assert vertices[2] == pytest.approx([10.0, 1.0, 0.5])



def test_create_body_mesh_objects_uses_per_body_display_scale_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    dummy_asset = tmp_path / "body_root.stl"
    dummy_asset.write_bytes(b"stub")

    system = SystemModel(
        id="anatomical",
        name="Anatomical System",
        role=SystemRole.ANATOMICAL,
        root_link_id="root",
        links=[
            Link(id="root", name="Root", asset_ids=["body_asset"]),
            Link(
                id="child",
                name="Child",
                transform=Transform(translation=(1.0, 0.0, 0.0)),
            ),
        ],
        joints=[
            Joint(
                id="root_child",
                name="root_child",
                kind=JointKind.FIXED,
                parent_link_id="root",
                child_link_id="child",
            )
        ],
    )
    world_transforms = compute_system_link_world_transforms(system)
    project = SimpleNamespace(
        assets=SimpleNamespace(
            items=[
                AssetRecord(
                    id="body_asset",
                    name="Body Asset",
                    role=AssetRole.VISUAL,
                    uri=str(dummy_asset),
                    media_type="model/stl",
                )
            ]
        ),
        get_anatomical_system=lambda: system,
    )

    monkeypatch.setattr(
        project_ops,
        "_load_binary_stl_mesh",
        lambda _path: (
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]],
            [[0, 1, 2]],
        ),
    )

    scene = FakeScene()
    ctx = FakeContext(scene)
    body_meshes = project_ops._create_body_mesh_objects(
        project,
        ctx,
        arm_obj=None,
        world_transforms=world_transforms,
        body_objects={},
        create_mesh_object=_make_mesh_factory(scene),
        attach_to_armature=False,
        reference_body_anchors={"root": (10.0, 0.0, 0.0)},
        reference_body_tail_points={"root": (10.0, 1.0, 0.0)},
        display_scale_factor=0.5,
        body_display_scale_factors={"root": 0.75},
    )

    assert len(body_meshes) == 1
    vertices = body_meshes[0]["mesh_data"].vertices
    assert len(vertices) == 3
    assert vertices[0] == pytest.approx([10.0, 0.0, 0.0])
    assert vertices[1] == pytest.approx([10.0, 0.75, 0.0])
    assert vertices[2] == pytest.approx([10.0, 0.0, 0.75])



def test_create_example_model_project_creates_armature_but_no_mesh() -> None:
    scene, _ = _run(include_skin=False)
    names = [o.name for o in scene.collection.linked]
    assert any("myofullbody_armature" in n for n in names)
    assert not any("myofullbody_skin" in n for n in names)
    body_meshes = [o for o in scene.collection.linked if o.name.startswith("body_")]
    assert body_meshes
    assert any(not getattr(obj, "hide_viewport", False) for obj in body_meshes)
    body_mesh_names = {obj.name for obj in body_meshes}
    assert "body_humerus_l_humerus_l" in body_mesh_names
    assert "body_ulna_l_ulna_l" in body_mesh_names
    assert "body_radius_l_radius_l" in body_mesh_names



def test_create_example_project_reference_collection_tagged() -> None:
    scene, _ = _run()
    ref_col = next((c for c in scene.collections if c.name == SKIN_REFERENCE_COLLECTION), None)
    assert ref_col is not None
    for obj in ref_col.objects:
        assert obj.get(SKIN_REFERENCE_PROP) is True


class _FakeBpyCollectionObjects:
    def __init__(self) -> None:
        self._items: list[object] = []

    def __iter__(self):
        return iter(self._items)

    def link(self, obj: object) -> None:
        self._items.append(obj)


class _FakeBpyCollectionChildren:
    def __init__(self) -> None:
        self._items: list[object] = []

    def __iter__(self):
        return iter(self._items)

    def link(self, collection: object) -> None:
        self._items.append(collection)


class _FakeBpyCollection:
    def __init__(self, name: str) -> None:
        self.name = name
        self.objects = _FakeBpyCollectionObjects()
        self.children = _FakeBpyCollectionChildren()


class _FakeBpyCollectionsRegistry:
    def __init__(self) -> None:
        self._items: dict[str, _FakeBpyCollection] = {}

    def get(self, name: str):
        return self._items.get(name)

    def new(self, name: str):
        collection = _FakeBpyCollection(name)
        self._items[name] = collection
        return collection



def test_collection_helpers_support_real_blender_style_link_api(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = _FakeBpyCollectionsRegistry()
    fake_bpy = SimpleNamespace(data=SimpleNamespace(collections=registry))
    monkeypatch.setattr(project_ops, "bpy", fake_bpy)

    scene = SimpleNamespace(collection=_FakeBpyCollection("Scene Collection"))
    collection = project_ops._get_or_create_collection(scene, SKIN_REFERENCE_COLLECTION)

    assert collection.name == SKIN_REFERENCE_COLLECTION
    assert list(scene.collection.children) == [collection]

    obj = FakeObject("skin_ref_obj")
    project_ops._link_to_collection(collection, obj)
    project_ops._link_to_collection(collection, obj)

    assert list(collection.objects) == [obj]



def test_create_example_project_sets_scene_settings() -> None:
    scene, _ = _run()
    settings = scene.melos_blender
    assert settings.project_id != ""
    assert settings.project_name != ""
    assert settings.anatomical_system_id != ""
    assert settings.anatomical_system_root_link_id == "Full Body"



def test_create_example_project_scales_anatomical_to_mhr_bundle_lengths() -> None:
    _, project = _run()
    skin_bundle = build_example_mhr_skin_bundle(
        Path(__file__).resolve().parents[3]
        / "resources"
        / "third_party"
        / "skin"
    )
    assert skin_bundle is not None
    translation_map = build_myofullbody_translation_map()
    anatomical_system = project.get_anatomical_system()
    assert anatomical_system is not None
    world_transforms = compute_system_link_world_transforms(
        anatomical_system,
        coordinate_values=project.simulation.initial_coordinate_values,
    )
    scale_factors = _compute_example_segment_scale_factors(
        skin_bundle["joints"],
        world_transforms,
        translation_map,
    )
    assert scale_factors
    values = sorted(scale_factors.values())
    median = values[len(values) // 2]
    assert median == pytest.approx(0.01, rel=1e-3)



def test_create_example_project_operator_execute() -> None:
    scene = FakeScene()
    ctx = FakeContext(scene)

    if not _mhr_runtime_available():
        pytest.skip("MHR runtime not available")

    reported = []

    class _Op(MELOS_OT_create_example_project):
        def report(self, level, msg):
            reported.append((level, msg))

    op = _Op()

    original_run = _run_create_example_project

    import importlib
    _mod = importlib.import_module("melos.blender.addon.operators.project")

    def _patched_run(context, **kwargs):
        _run_create_example_project(
            context,
            create_object=fake_create_object,
            create_armature_object=_make_arm_factory(scene),
            create_mesh_object=_make_mesh_factory(scene),
            include_skin=True,
        )

    _mod._run_create_example_project = _patched_run
    try:
        result = op.execute(ctx)
    finally:
        _mod._run_create_example_project = original_run

    assert result == {"FINISHED"}
    assert any(level == {"INFO"} for level, _ in reported)



def test_create_example_model_project_operator_execute() -> None:
    scene = FakeScene()
    ctx = FakeContext(scene)

    reported = []

    class _Op(MELOS_OT_create_example_model_project):
        def report(self, level, msg):
            reported.append((level, msg))

    op = _Op()

    original_run = _run_create_example_project

    import importlib
    _mod = importlib.import_module("melos.blender.addon.operators.project")

    def _patched_run(context, **kwargs):
        _run_create_example_project(
            context,
            create_object=fake_create_object,
            create_armature_object=_make_arm_factory(scene),
            create_mesh_object=_make_mesh_factory(scene),
            include_skin=False,
        )

    _mod._run_create_example_project = _patched_run
    try:
        result = op.execute(ctx)
    finally:
        _mod._run_create_example_project = original_run

    assert result == {"FINISHED"}
    assert any(level == {"INFO"} for level, _ in reported)
