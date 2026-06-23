from __future__ import annotations

from types import SimpleNamespace

from melos.blender.bpy_io.skinned_import import build_armature_object, compute_system_link_world_transforms
from melos.core.common.types import Transform
from melos.core.project.model import Project
from melos.core.system.enums import SystemRole
from melos.core.system.model import Joint, Link, SystemModel
from melos.core.system.enums import JointKind


def test_compute_system_link_world_transforms_follows_mjcf_parent_annotations() -> None:
    root = Link(
        id="root",
        name="Root",
        transform=Transform(translation=(1.0, 2.0, 3.0)),
    )
    child = Link(
        id="child",
        name="Child",
        transform=Transform(translation=(0.5, -0.5, 1.0)),
        annotations={"mjcf_parent_link": "root"},
    )
    grandchild = Link(
        id="grandchild",
        name="Grandchild",
        transform=Transform(translation=(0.25, 0.0, -1.0)),
        annotations={"mjcf_parent_link": "child"},
    )
    system = SystemModel(
        id="anatomical",
        name="Anatomical System",
        role=SystemRole.ANATOMICAL,
        root_link_id="root",
        links=[root, child, grandchild],
        joints=[],
    )

    world = compute_system_link_world_transforms(system)

    assert world["root"].translation == (1.0, 2.0, 3.0)
    assert world["child"].translation == (1.5, 1.5, 4.0)
    assert world["grandchild"].translation == (1.75, 1.5, 3.0)


def test_compute_system_link_world_transforms_respects_joint_parent_graph() -> None:
    pelvis = Link(id="pelvis", name="Pelvis")
    femur = Link(id="femur", name="Femur", transform=Transform(translation=(0.0, 0.0, -0.4)))
    system = SystemModel(
        id="anatomical",
        name="Anatomical System",
        role=SystemRole.ANATOMICAL,
        root_link_id="pelvis",
        links=[pelvis, femur],
        joints=[
            Joint(
                id="hip_joint",
                name="Hip Joint",
                kind=JointKind.FIXED,
                parent_link_id="pelvis",
                child_link_id="femur",
            )
        ],
    )

    world = compute_system_link_world_transforms(system)

    assert world["femur"].translation == (0.0, 0.0, -0.4)


def test_build_armature_object_uses_reference_tail_points_before_parent_direction() -> None:
    torso = Link(id="torso", name="Torso")
    head = Link(id="head", name="Head")
    system = SystemModel(
        id="anatomical",
        name="Anatomical System",
        role=SystemRole.ANATOMICAL,
        root_link_id="torso",
        links=[torso, head],
        joints=[
            Joint(
                id="neck_joint",
                name="Neck Joint",
                kind=JointKind.FIXED,
                parent_link_id="torso",
                child_link_id="head",
            )
        ],
    )
    project = Project(systems=[system])
    context = SimpleNamespace(scene=SimpleNamespace(collection=object()))

    arm_data = build_armature_object(
        project,
        context,
        create_armature_object=lambda _name, data, _collection: data,
        reference_body_anchors={"torso": (0.0, 0.0, 0.0), "head": (1.0, 0.0, 0.0)},
        reference_body_tail_points={"head": (2.0, 0.0, 0.0)},
    )

    bones = {bone.name: bone for bone in arm_data.bones}
    assert bones["head"].head == (1.0, 0.0, 0.0)
    assert bones["head"].tail == (2.0, 0.0, 0.0)
