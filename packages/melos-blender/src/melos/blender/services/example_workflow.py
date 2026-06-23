"""Example-project orchestration for Blender-facing workflows."""

from __future__ import annotations

import importlib
from typing import Any, Callable

from melos.blender.bpy_io.importer import import_project_to_scene
from melos.blender.bpy_io.skinned_import import (
    build_armature_object,
    build_weighted_mesh_object,
    compute_project_link_world_transforms,
    compute_system_link_world_transforms,
)
from melos.blender.bpy_io.rigging import setup_native_fk_rig, create_rigid_body_meshes
from melos.blender.bpy_io.skin_bundle import (
    SKIN_REFERENCE_COLLECTION,
    SKIN_REFERENCE_KIND_BODY_MESH,
    SKIN_REFERENCE_KIND_PROP,
    SKIN_REFERENCE_PROP,
)
from melos.blender.constants import (
    ENTITY_ID_KEY,
    ENTITY_KIND_KEY,
    SCENE_SETTINGS_ATTRIBUTE,
    ANATOMICAL_LINK_KIND,
)
from melos.blender.services.example_alignment import reference_body_tail_dirs
from melos.core.common.assets import AssetRecord
from melos.core.common.types import AssetRole, Transform
from melos.core.project.skin import SkinAttachment, SkinAttachmentFit
from melos.core.project.skin_binding import collapse_joint_weights_to_binding_spec
from melos.core.system import (
    Actuator,
    ActuatorKind,
    CableParameters,
    Link,
    RouteNode,
    RouteNodeKind,
    Site,
    SystemModel,
    SystemRole,
)
from melos.core.retarget.alignment import apply_similarity, apply_similarity_to_vertices, frame_basis, matmul, transpose
from melos.core.scaling import (
    fit_project_system_to_measurements,
    link_scale_factors_from_segment_scale_factors,
)
from melos.sim.mujoco.adapters import (
    build_example_human_mesh_rigging_plan,
    build_example_scale_link_map,
    build_example_visual_scale_link_map,
    measure_example_source_segments,
)
from melos.sim.mujoco.importers import import_mjcf
from melos.skin.adapters import (
    build_example_mhr_skin_bundle,
    measure_example_skin_segments,
)
from melos.skin.mappings.myofullbody_to_human_v1 import (
    build_myofullbody_translation_map,
)





def display_project_in_scene(
    project: Any,
    context: Any,
    *,
    create_object: Callable[[str, Any], Any] | None = None,
    create_armature_object: Callable[[str, Any, Any], Any] | None = None,
    create_mesh_object: Callable[[str, Any, Any], Any] | None = None,
    translation_map: Any | None = None,
    body_scale_factors: dict[str, float] | None = None,
    body_display_scale_factors: dict[str, float] | None = None,
    reference_body_anchors: dict[str, tuple[float, float, float]] | None = None,
    reference_body_tail_points: dict[str, tuple[float, float, float]] | None = None,
    source_body_tail_points: dict[str, tuple[float, float, float]] | None = None,
    display_armature_system: Any | None = None,
    armature_name: str = "anatomical_armature",
    load_meshes: bool = False,
) -> tuple[Any, Any | None, list[Any]]:
    """Display a melos project in Blender with armature and body meshes.

    Creates link/joint/site empties via import_project_to_scene, builds an
    armature from the link hierarchy, loads body meshes with world-space
    transforms, creates a display root for upright orientation, and hides
    raw structural empties.

    Returns (project, armature_obj, body_mesh_objects).
    """
    project_ops = importlib.import_module("melos.blender.addon.operators.project")

    anatomical_system = project.get_anatomical_system()
    if anatomical_system is None:
        return project, None, []
    scene = context.scene
    collection = getattr(scene, "collection", scene)
    settings = getattr(scene, SCENE_SETTINGS_ATTRIBUTE)
    _remove_default_startup_objects(scene)

    def _default_create(name: str, collection: Any) -> Any:
        bpy = getattr(project_ops, "bpy", None)
        if bpy is None:
            raise RuntimeError(
                "The melos add-on can only create objects inside Blender."
            )
        obj = bpy.data.objects.new(name, None)
        obj.empty_display_type = "PLAIN_AXES"
        collection.objects.link(obj)
        return obj

    effective_create = create_object if create_object is not None else _default_create
    created = import_project_to_scene(
        project, scene, settings, create_object=effective_create, load_meshes=load_meshes
    )

    body_objects = {
        obj.get(ENTITY_ID_KEY): obj
        for obj in created
        if getattr(obj, "get", lambda *_: None)(ENTITY_KIND_KEY) == ANATOMICAL_LINK_KIND
    }
    world_transforms = compute_project_link_world_transforms(
        project,
        coordinate_values=project.simulation.initial_coordinate_values,
    )

    body_tail_dirs = reference_body_tail_dirs(translation_map)
    effective_display_armature_system = display_armature_system if display_armature_system is not None else anatomical_system

    # Build native FK rig (one bone per link, with drivers and constraints)
    arm_obj = build_armature_object(
        project,
        context,
        create_armature_object=create_armature_object,
        armature_name=armature_name,
        reference_body_tail_dirs=body_tail_dirs,
        target_system=effective_display_armature_system,
    )
    fk_meta = setup_native_fk_rig(arm_obj, anatomical_system)

    body_mesh_objects: list[Any] = []
    arm_obj[SKIN_REFERENCE_PROP] = True
    if hasattr(arm_obj, "display_type"):
        arm_obj.display_type = "WIRE"
    arm_data = getattr(arm_obj, "data", None)
    if arm_data is not None and hasattr(arm_data, "display_type"):
        arm_data.display_type = "STICK"

    # Create body meshes: rigid rigging in Blender, skinned fallback in headless mode
    try:
        bpy_check = importlib.import_module("bpy")
    except ModuleNotFoundError:
        bpy_check = None

    if bpy_check is not None:
        # Blender mode — rigid body meshes parented to bones
        body_mesh_objects = create_rigid_body_meshes(project, anatomical_system, arm_obj, context, collection)
    else:
        # Headless/test mode — use old skinned approach for compatibility
        body_mesh_objects = project_ops._create_body_mesh_objects(
            project,
            context,
            arm_obj=arm_obj,
            world_transforms=world_transforms,
            body_objects=body_objects,
            display_relationship_system=effective_display_armature_system,
            create_mesh_object=create_mesh_object,
            attach_to_armature=True,
            reference_body_tail_dirs=body_tail_dirs,
            display_scale_factor=1.0,
        )

    _configure_example_reference_display(
        arm_obj=arm_obj,
        mesh_obj=None,
        body_mesh_objects=body_mesh_objects,
    )

    ref_collection = project_ops._get_or_create_collection(
        scene, SKIN_REFERENCE_COLLECTION
    )
    for body_mesh_obj in body_mesh_objects:
        body_mesh_obj[SKIN_REFERENCE_PROP] = True
        body_mesh_obj[SKIN_REFERENCE_KIND_PROP] = SKIN_REFERENCE_KIND_BODY_MESH
        project_ops._link_to_collection(ref_collection, body_mesh_obj)
    project_ops._link_to_collection(ref_collection, arm_obj)

    muscle_objs: list[Any] = []
    muscle_objs = project_ops._create_muscle_display_objects(
        project,
        context,
        arm_obj,
        world_transforms,
        create_mesh_object=create_mesh_object,
    )
    for muscle_obj in muscle_objs:
        muscle_obj[SKIN_REFERENCE_PROP] = True
        project_ops._link_to_collection(ref_collection, muscle_obj)

    display_root = _create_example_display_root(
        scene,
        world_transforms,
        [obj for obj in (arm_obj, *muscle_objs) if obj is not None],
        ref_collection=ref_collection,
    )
    if display_root is not None:
        display_root[SKIN_REFERENCE_PROP] = True

    _hide_example_support_objects(
        [*created, *muscle_objs],
        keep_objects=[obj for obj in (arm_obj, *body_mesh_objects) if obj is not None],
    )

    return project, arm_obj, body_mesh_objects
def run_create_example_project(
    context: Any,
    *,
    create_object: Callable[[str, Any], Any] | None = None,
    create_armature_object: Callable[[str, Any, Any], Any] | None = None,
    create_mesh_object: Callable[[str, Any, Any], Any] | None = None,
    include_skin: bool = True,
) -> Any:
    project_ops = importlib.import_module("melos.blender.addon.operators.project")

    project = import_mjcf(
        project_ops._resolve_resource_path(
            "myofullbody/body/myofullbody.xml",
            "resources/third_party/myofullbody/body/myofullbody.xml",
        )
    ).project
    translation_map = build_myofullbody_translation_map()
    example_mhr_skin_bundle = None
    body_scale_factors: dict[str, float] = {}
    if include_skin:
        skin_asset_path = project_ops._resolve_resource_path(
            "skin/SOMA_neutral.npz",
            "resources/third_party/skin/SOMA_neutral.npz",
        )
        example_mhr_skin_bundle = build_example_mhr_skin_bundle(skin_asset_path.parent)
        if example_mhr_skin_bundle is None:
            raise RuntimeError("MHR skin runtime is not available for the example workflow.")
    project.translation_maps = [translation_map]
    scaling_skin_bundle = example_mhr_skin_bundle
    if scaling_skin_bundle is not None:
        source_world_transforms = compute_project_link_world_transforms(
            project,
            coordinate_values=project.simulation.initial_coordinate_values,
        )
        source_measurements = measure_example_source_segments(source_world_transforms)
        target_measurements = measure_example_skin_segments(
            scaling_skin_bundle,
            translation_map,
        )
        fit_result = fit_project_system_to_measurements(
            project,
            source_measurements,
            target_measurements,
            build_example_scale_link_map(),
        )
        project = fit_result.project
        body_scale_factors = link_scale_factors_from_segment_scale_factors(
            fit_result.segment_scale_factors,
            build_example_visual_scale_link_map(),
        )
    anatomical_system = project.get_anatomical_system()
    # Add cable assist device
    if anatomical_system is not None:
        _add_example_cable_device(project, anatomical_system)
    anatomical_link_ids = (
        [link.id for link in anatomical_system.links] if anatomical_system is not None else []
    )
    anchor_link_id = (
        (anatomical_system.root_link_id or anatomical_link_ids[0])
        if anatomical_link_ids
        else "pelvis"
    )
    if include_skin:
        skin_fit = SkinAttachmentFit(
            anchor_link_id=anchor_link_id,
            rest_transform_in_anchor=Transform.identity(),
            fit_coordinate_values=dict(project.simulation.initial_coordinate_values),
            reference_link_ids=anatomical_link_ids[:4],
            reference_site_ids=[],
            reference_geometry_ids=[],
        )
        project.skin_attachments.append(
            SkinAttachment(
                id="skin_main",
                name="Human Skin (myofullbody)",
                target_system_id=anatomical_system.id
                if anatomical_system is not None
                else "anatomical",
                mesh_asset_id="skin_mesh",
                binding_asset_id="skin_binding",
                fit=skin_fit,
                translation_map_id=translation_map.id if translation_map is not None else None,
            )
        )
        project.assets.items.append(
            AssetRecord(
                id="skin_mesh",
                name="Human skin mesh",
                role=AssetRole.VISUAL,
                uri="",
                media_type="model/obj",
            )
        )
        project.assets.items.append(
            AssetRecord(
                id="skin_binding",
                name="Human skin binding",
                role=AssetRole.FITTING,
                uri="",
                media_type="application/vnd.melos.skin-binding+json",
            )
        )

        scene = context.scene
        settings = getattr(scene, SCENE_SETTINGS_ATTRIBUTE)
        _remove_default_startup_objects(scene)

        def _default_create(name: str, collection: Any) -> Any:
            bpy = getattr(project_ops, "bpy", None)
            if bpy is None:
                raise RuntimeError(
                    "The melos add-on can only create objects inside Blender."
                )
            obj = bpy.data.objects.new(name, None)
            obj.empty_display_type = "PLAIN_AXES"
            collection.objects.link(obj)
            return obj

        effective_create = create_object if create_object is not None else _default_create
        created = import_project_to_scene(
            project, scene, settings, create_object=effective_create, load_meshes=False
        )

        body_objects = {
            obj.get(ENTITY_ID_KEY): obj
            for obj in created
            if getattr(obj, "get", lambda *_: None)(ENTITY_KIND_KEY) == ANATOMICAL_LINK_KIND
        }
        bodies = anatomical_system.links if anatomical_system is not None else []
        world_transforms = compute_project_link_world_transforms(
            project,
            coordinate_values=project.simulation.initial_coordinate_values,
        )

        mesh_obj = None
        display_target_system = anatomical_system
        display_armature_system = anatomical_system
        body_tail_dirs = reference_body_tail_dirs(translation_map)
        reference_body_anchors = None
        reference_body_tail_points = None
        body_mesh_reference_anchors = None
        body_mesh_reference_tail_points = None
        body_mesh_display_scale = 1.0
        body_mesh_display_scale_factors: dict[str, float] = {}
        body_mesh_source_tail_points: dict[str, tuple[float, float, float]] = {}
        if include_skin:
            skin_bundle = example_mhr_skin_bundle
            body_name_map = {i: body.id for i, body in enumerate(bodies)}

            if skin_bundle is not None and display_target_system is not None:
                rigging_plan = build_example_human_mesh_rigging_plan(
                    display_target_system,
                    world_transforms,
                    skin_bundle["joints"],
                    translation_map,
                )
                display_armature_system = rigging_plan.display_system
                binding_spec = rigging_plan.binding_spec
                reference_body_anchors = dict(rigging_plan.reference_body_anchors)
                reference_body_tail_points = dict(rigging_plan.reference_body_tail_points)
                body_mesh_reference_anchors = dict(reference_body_anchors)
                body_mesh_reference_tail_points = dict(reference_body_tail_points)
                _extend_reference_body_points_with_hand_joints(
                    body_mesh_reference_anchors,
                    body_mesh_reference_tail_points,
                    skin_bundle["joints"],
                    rigging_plan.rest_alignment_similarity,
                )
                body_mesh_display_scale = _compute_example_body_mesh_display_scale(
                    world_transforms,
                    translation_map,
                    body_mesh_reference_anchors,
                    body_mesh_reference_tail_points,
                )
                body_mesh_display_scale_factors = _compute_example_body_mesh_display_scale_factors(
                    world_transforms,
                    translation_map,
                    body_mesh_reference_anchors,
                    body_mesh_reference_tail_points,
                )
                body_mesh_source_tail_points = _compute_example_body_mesh_source_tail_points(
                    world_transforms,
                    translation_map,
                )
                vertices = apply_similarity_to_vertices(
                    skin_bundle["vertices"],
                    rigging_plan.rest_alignment_similarity,
                )
                faces = skin_bundle["faces"]
                body_name_map = {
                    link_index: link_id
                    for link_index, link_id in enumerate(binding_spec.deformer_link_ids)
                }
                bone_weights, bone_indices = collapse_joint_weights_to_binding_spec(
                    joint_names=skin_bundle["joint_names"],
                    weight_data=skin_bundle["weight_data"],
                    weight_indices=skin_bundle["weight_indices"],
                    weight_indptr=skin_bundle["weight_indptr"],
                    binding_spec=binding_spec,
                )
                if project.skin_attachments:
                    skin_attachment = project.skin_attachments[0]
                    skin_attachment.target_system_id = anatomical_system.id if anatomical_system is not None else display_target_system.id
                    fit = skin_attachment.fit
                    fit.anchor_link_id = binding_spec.anchor_link_id or anchor_link_id
                    fit.reference_link_ids = list(binding_spec.reference_link_ids)
                    fit.annotations.clear()
                    fit.fit_method = "mhr_rest_mesh_bound_to_mujoco_links_v1"
                    fit.annotations["skin_source_model"] = "mhr"
                    fit.annotations["skin_source_backend"] = "somax_mhr_identity"
                    fit.annotations["shape_source"] = "mhr_input_model"
                    fit.annotations["kinematics_source"] = "mujoco_system_rest_armature"
                    fit.annotations["display_rig"] = "mujoco_link_rig"
                    fit.annotations["binding_mode"] = "mhr_joint_weights_collapsed_to_mujoco_links"
                    fit.annotations["mesh_pose_source"] = "aligned_mhr_rest_mesh"
                    fit.annotations["retarget_link_layer"] = str(
                        binding_spec.annotations.get("retarget_link_layer", "translation_map_source_links_v1")
                    )
                    fit.annotations["retarget_link_count"] = len(binding_spec.deformer_link_ids)
                    fit.annotations["mesh_deformation_in_blender"] = "armature_modifier"
                # Create armature FIRST, then modify it, THEN create skin mesh.
                # This ensures the skin mesh's armature modifier references
                # the modified bone rest poses (aligned to body local frames).
                arm_obj = build_armature_object(
                    project,
                    context,
                    create_armature_object=create_armature_object,
                    armature_name="myofullbody_armature",
                    reference_body_anchors=reference_body_anchors,
                    reference_body_tail_points=reference_body_tail_points,
                    reference_body_tail_dirs=body_tail_dirs,
                    target_system=display_armature_system,
                )
                setup_native_fk_rig(arm_obj, display_armature_system)
                mesh_obj = build_weighted_mesh_object(
                    project,
                    vertices,
                    faces,
                    bone_weights,
                    bone_indices,
                    body_name_map,
                    context,
                    arm_obj=arm_obj,
                    create_mesh_object=create_mesh_object,
                    mesh_name="myofullbody_skin",
                    target_system=display_armature_system,
                )
        else:
            arm_obj = build_armature_object(
                project,
                context,
                create_armature_object=create_armature_object,
                armature_name="myofullbody_armature",
                reference_body_tail_dirs=body_tail_dirs,
            )

        arm_obj[SKIN_REFERENCE_PROP] = True
        if mesh_obj is not None:
            mesh_obj[SKIN_REFERENCE_PROP] = True
        if hasattr(arm_obj, "display_type"):
            arm_obj.display_type = "WIRE"
        arm_data = getattr(arm_obj, "data", None)
        if arm_data is not None and hasattr(arm_data, "display_type"):
            arm_data.display_type = "STICK"
        if mesh_obj is not None:
            _hide_non_deforming_bones(arm_obj, bone_weights, bone_indices, body_name_map)

        body_mesh_objects: list[Any] = []
        if display_target_system is anatomical_system:
            body_mesh_objects = project_ops._create_body_mesh_objects(
                project,
                context,
                arm_obj=arm_obj,
                world_transforms=world_transforms,
                body_objects=body_objects,
                body_scale_factors=body_scale_factors,
                body_display_scale_factors=body_mesh_display_scale_factors,
                # Use the retarget display SystemModel's parent relationships for
                # body-mesh visualization; Blender should not invent a different
                # clavicle/arm hierarchy from the raw MuJoCo body tree.
                display_relationship_system=display_armature_system,
                create_mesh_object=create_mesh_object,
                attach_to_armature=mesh_obj is None,
                reference_body_anchors=body_mesh_reference_anchors or reference_body_anchors,
                reference_body_tail_points=body_mesh_reference_tail_points or reference_body_tail_points,
                reference_body_tail_dirs=body_tail_dirs,
                source_body_tail_points=body_mesh_source_tail_points,
                display_scale_factor=body_mesh_display_scale,
            )

        _configure_example_reference_display(
            arm_obj=arm_obj,
            mesh_obj=mesh_obj,
            body_mesh_objects=body_mesh_objects,
        )

        ref_collection = project_ops._get_or_create_collection(
            scene, SKIN_REFERENCE_COLLECTION
        )
        for body_mesh_obj in body_mesh_objects:
            body_mesh_obj[SKIN_REFERENCE_PROP] = True
            body_mesh_obj[SKIN_REFERENCE_KIND_PROP] = SKIN_REFERENCE_KIND_BODY_MESH
            project_ops._link_to_collection(ref_collection, body_mesh_obj)
        project_ops._link_to_collection(ref_collection, arm_obj)
        if mesh_obj is not None:
            project_ops._link_to_collection(ref_collection, mesh_obj)

        muscle_objs: list[Any] = []
        if display_target_system is anatomical_system and mesh_obj is None:
            muscle_objs = project_ops._create_muscle_display_objects(
                project,
                context,
                arm_obj,
                world_transforms,
                create_mesh_object=create_mesh_object,
            )
        for muscle_obj in muscle_objs:
            muscle_obj[SKIN_REFERENCE_PROP] = True
            project_ops._link_to_collection(ref_collection, muscle_obj)

        display_root = _create_example_display_root(
            scene,
            world_transforms,
            [obj for obj in (arm_obj, mesh_obj, *body_mesh_objects, *muscle_objs) if obj is not None],
            ref_collection=ref_collection,
        )
        if display_root is not None:
            display_root[SKIN_REFERENCE_PROP] = True

        _hide_example_support_objects(
            [*created, *muscle_objs],
            keep_objects=[obj for obj in (arm_obj, mesh_obj, *body_mesh_objects) if obj is not None],
        )

    else:
        project, _, _ = display_project_in_scene(
            project,
            context,
            create_object=create_object,
            create_armature_object=create_armature_object,
            create_mesh_object=create_mesh_object,
            translation_map=translation_map,
            armature_name="myofullbody_armature",
        )

    return project


def _compute_example_body_mesh_source_tail_points(
    world_transforms: dict[str, Transform],
    translation_map: Any | None,
) -> dict[str, tuple[float, float, float]]:
    if translation_map is None:
        return {}

    source_tail_points: dict[str, tuple[float, float, float]] = {}
    for rule in getattr(translation_map, "rules", ()) or ():
        source_link_id = getattr(rule, "source_link_id", None)
        source_tail_link_id = getattr(rule, "source_tail_link_id", None)
        if source_link_id is None or source_tail_link_id is None:
            continue
        link_id = str(source_link_id)
        tail_link_id = str(source_tail_link_id)
        source_transform = world_transforms.get(link_id)
        tail_transform = world_transforms.get(tail_link_id)
        if source_transform is None or tail_transform is None:
            continue
        if _point_distance(source_transform.translation, tail_transform.translation) <= 1e-8:
            continue
        source_tail_points[link_id] = tuple(float(value) for value in tail_transform.translation)
    return source_tail_points



def _compute_example_body_mesh_display_scale(
    world_transforms: dict[str, Transform],
    translation_map: Any | None,
    reference_body_anchors: dict[str, tuple[float, float, float]] | None,
    reference_body_tail_points: dict[str, tuple[float, float, float]] | None,
) -> float:
    scale_factors = _compute_example_body_mesh_display_scale_factors(
        world_transforms,
        translation_map,
        reference_body_anchors,
        reference_body_tail_points,
    )
    if not scale_factors:
        return 1.0
    ratios = sorted(scale_factors.values())
    return float(ratios[len(ratios) // 2])



def _compute_example_body_mesh_display_scale_factors(
    world_transforms: dict[str, Transform],
    translation_map: Any | None,
    reference_body_anchors: dict[str, tuple[float, float, float]] | None,
    reference_body_tail_points: dict[str, tuple[float, float, float]] | None,
) -> dict[str, float]:
    if (
        translation_map is None
        or not reference_body_anchors
        or not reference_body_tail_points
    ):
        return {}

    from melos.sim.mujoco.adapters.example_source import example_source_segment_length

    scale_factors: dict[str, float] = {}
    for rule in getattr(translation_map, "rules", ()) or ():
        segment_id = getattr(rule, "segment_id", None)
        source_link_id = getattr(rule, "source_link_id", None)
        if segment_id is None or source_link_id is None:
            continue
        link_id = str(source_link_id)
        if link_id not in reference_body_anchors or link_id not in reference_body_tail_points:
            continue
        source_length = example_source_segment_length(str(segment_id), world_transforms)
        if source_length is None or source_length <= 1e-8:
            continue
        head = reference_body_anchors[link_id]
        tail = reference_body_tail_points[link_id]
        display_length = _point_distance(head, tail)
        if display_length <= 1e-8:
            continue
        scale_factors[link_id] = display_length / source_length
    return scale_factors



def _point_distance(
    head: tuple[float, float, float],
    tail: tuple[float, float, float],
) -> float:
    return (
        (tail[0] - head[0]) ** 2
        + (tail[1] - head[1]) ** 2
        + (tail[2] - head[2]) ** 2
    ) ** 0.5


_ARM_REFERENCE_JOINTS: dict[str, tuple[str, str]] = {}


_HAND_REFERENCE_JOINTS: dict[str, tuple[str, str]] = {
    "lunate_l": ("LeftHand", "LeftHandMiddle1"),
    "capitate_l": ("LeftHand", "LeftHandMiddle1"),
    "trapezium_l": ("LeftHand", "LeftHandThumb1"),
    "trapezoid_l": ("LeftHand", "LeftHandIndex1"),
    "hamate_l": ("LeftHand", "LeftHandPinky1"),
    "firstmc_l": ("LeftHandThumb1", "LeftHandThumb2"),
    "proximal_thumb_l": ("LeftHandThumb2", "LeftHandThumb3"),
    "distal_thumb_l": ("LeftHandThumb3", "LeftHandThumbEnd"),
    "secondmc_l": ("LeftHandIndex1", "LeftHandIndex2"),
    "2proxph_l": ("LeftHandIndex2", "LeftHandIndex3"),
    "2midph_l": ("LeftHandIndex3", "LeftHandIndex4"),
    "2distph_l": ("LeftHandIndex4", "LeftHandIndexEnd"),
    "thirdmc_l": ("LeftHandMiddle1", "LeftHandMiddle2"),
    "3proxph_l": ("LeftHandMiddle2", "LeftHandMiddle3"),
    "3midph_l": ("LeftHandMiddle3", "LeftHandMiddle4"),
    "3distph_l": ("LeftHandMiddle4", "LeftHandMiddleEnd"),
    "fourthmc_l": ("LeftHandRing1", "LeftHandRing2"),
    "4proxph_l": ("LeftHandRing2", "LeftHandRing3"),
    "4midph_l": ("LeftHandRing3", "LeftHandRing4"),
    "4distph_l": ("LeftHandRing4", "LeftHandRingEnd"),
    "fifthmc_l": ("LeftHandPinky1", "LeftHandPinky2"),
    "5proxph_l": ("LeftHandPinky2", "LeftHandPinky3"),
    "5midph_l": ("LeftHandPinky3", "LeftHandPinky4"),
    "5distph_l": ("LeftHandPinky4", "LeftHandPinkyEnd"),
    "lunate_r": ("RightHand", "RightHandMiddle1"),
    "capitate_r": ("RightHand", "RightHandMiddle1"),
    "trapezium_r": ("RightHand", "RightHandThumb1"),
    "trapezoid_r": ("RightHand", "RightHandIndex1"),
    "hamate_r": ("RightHand", "RightHandPinky1"),
    "firstmc_r": ("RightHandThumb1", "RightHandThumb2"),
    "proximal_thumb_r": ("RightHandThumb2", "RightHandThumb3"),
    "distal_thumb_r": ("RightHandThumb3", "RightHandThumbEnd"),
    "secondmc_r": ("RightHandIndex1", "RightHandIndex2"),
    "2proxph_r": ("RightHandIndex2", "RightHandIndex3"),
    "2midph_r": ("RightHandIndex3", "RightHandIndex4"),
    "2distph_r": ("RightHandIndex4", "RightHandIndexEnd"),
    "thirdmc_r": ("RightHandMiddle1", "RightHandMiddle2"),
    "3proxph_r": ("RightHandMiddle2", "RightHandMiddle3"),
    "3midph_r": ("RightHandMiddle3", "RightHandMiddle4"),
    "3distph_r": ("RightHandMiddle4", "RightHandMiddleEnd"),
    "fourthmc_r": ("RightHandRing1", "RightHandRing2"),
    "4proxph_r": ("RightHandRing2", "RightHandRing3"),
    "4midph_r": ("RightHandRing3", "RightHandRing4"),
    "4distph_r": ("RightHandRing4", "RightHandRingEnd"),
    "fifthmc_r": ("RightHandPinky1", "RightHandPinky2"),
    "5proxph_r": ("RightHandPinky2", "RightHandPinky3"),
    "5midph_r": ("RightHandPinky3", "RightHandPinky4"),
    "5distph_r": ("RightHandPinky4", "RightHandPinkyEnd"),
}


def _aligned_skin_joint_positions(
    skin_joint_positions: dict[str, tuple[float, float, float]],
    similarity: Any,
) -> dict[str, tuple[float, float, float]]:
    return {
        str(joint_name): apply_similarity(
            (float(position[0]), float(position[1]), float(position[2])),
            similarity,
        )
        for joint_name, position in skin_joint_positions.items()
    }



def _override_example_arm_reference_body_points(
    reference_body_anchors: dict[str, tuple[float, float, float]],
    reference_body_tail_points: dict[str, tuple[float, float, float]],
    skin_joint_positions: dict[str, tuple[float, float, float]],
    similarity: Any,
) -> None:
    aligned_joint_positions = _aligned_skin_joint_positions(skin_joint_positions, similarity)
    for link_id, (anchor_joint_id, tail_joint_id) in _ARM_REFERENCE_JOINTS.items():
        head = aligned_joint_positions.get(anchor_joint_id)
        tail = aligned_joint_positions.get(tail_joint_id)
        if head is None or tail is None:
            continue
        reference_body_anchors[link_id] = head
        delta = (
            float(tail[0] - head[0]),
            float(tail[1] - head[1]),
            float(tail[2] - head[2]),
        )
        if (delta[0] * delta[0] + delta[1] * delta[1] + delta[2] * delta[2]) > 1e-12:
            reference_body_tail_points[link_id] = tail



def _extend_reference_body_points_with_hand_joints(
    reference_body_anchors: dict[str, tuple[float, float, float]],
    reference_body_tail_points: dict[str, tuple[float, float, float]],
    skin_joint_positions: dict[str, tuple[float, float, float]],
    similarity: Any,
) -> None:
    aligned_joint_positions = _aligned_skin_joint_positions(skin_joint_positions, similarity)

    for link_id, (anchor_joint_id, tail_joint_id) in _HAND_REFERENCE_JOINTS.items():
        head = aligned_joint_positions.get(anchor_joint_id)
        tail = aligned_joint_positions.get(tail_joint_id)
        if head is None or tail is None:
            continue
        reference_body_anchors[link_id] = head
        delta = (
            float(tail[0] - head[0]),
            float(tail[1] - head[1]),
            float(tail[2] - head[2]),
        )
        if (delta[0] * delta[0] + delta[1] * delta[1] + delta[2] * delta[2]) > 1e-12:
            reference_body_tail_points[link_id] = tail



def _compute_example_display_upright_rotation(
    world_transforms: dict[str, Transform],
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]] | None:
    required_link_ids = ("pelvis", "head", "femur_l", "femur_r")
    if any(link_id not in world_transforms for link_id in required_link_ids):
        return None

    source_basis = frame_basis(
        {
            "pelvis": world_transforms["pelvis"].translation,
            "head": world_transforms["head"].translation,
            "left_thigh": world_transforms["femur_l"].translation,
            "right_thigh": world_transforms["femur_r"].translation,
        }
    )
    target_basis = (
        (-1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
    )
    return matmul(target_basis, transpose(source_basis))



def _create_example_display_root(
    scene: Any,
    world_transforms: dict[str, Transform],
    objects: list[Any],
    *,
    ref_collection: Any | None = None,
) -> Any | None:
    if not objects:
        return None

    project_ops = importlib.import_module("melos.blender.addon.operators.project")
    bpy = getattr(project_ops, "bpy", None)
    if bpy is None:
        return None

    rotation_matrix = _compute_example_display_upright_rotation(world_transforms)
    pelvis_transform = world_transforms.get("pelvis")
    if rotation_matrix is None or pelvis_transform is None:
        return None

    mathutils = importlib.import_module("mathutils")
    root = bpy.data.objects.new("example_display_root", None)
    root.empty_display_type = "PLAIN_AXES"
    root.empty_display_size = 0.05
    scene.collection.objects.link(root)
    if ref_collection is not None:
        project_ops._link_to_collection(ref_collection, root)

    root.location = tuple(float(value) for value in pelvis_transform.translation)
    root.rotation_mode = "QUATERNION"
    root.rotation_quaternion = mathutils.Matrix(rotation_matrix).to_quaternion()
    view_layer = getattr(bpy.context, "view_layer", None)
    if view_layer is not None and hasattr(view_layer, "update"):
        view_layer.update()

    root_world_matrix = root.matrix_world.copy() if hasattr(root, "matrix_world") else None
    for obj in objects:
        if obj is None:
            continue
        obj.parent = root
        # All example display data (skin vertices, armature edit bones, and body
        # reference mesh vertices) is authored in the same core rest coordinate
        # frame.  Apply the display root uniformly instead of preserving each
        # child's pre-parent world matrix; otherwise toggled body meshes remain
        # in raw MuJoCo coordinates while the skin/armature are shown upright.
        parent_inverse = getattr(obj, "matrix_parent_inverse", None)
        if parent_inverse is not None and hasattr(parent_inverse, "identity"):
            parent_inverse.identity()
        if root_world_matrix is not None and hasattr(obj, "matrix_world"):
            obj.matrix_world = root_world_matrix.copy()

    if hasattr(root, "hide_viewport"):
        root.hide_viewport = True
    if hasattr(root, "hide_render"):
        root.hide_render = True
    return root



def _configure_example_reference_display(
    *,
    arm_obj: Any,
    mesh_obj: Any | None,
    body_mesh_objects: list[Any],
) -> None:
    if hasattr(arm_obj, "show_in_front"):
        arm_obj.show_in_front = True

    if mesh_obj is not None:
        _configure_example_skin_mesh_display(mesh_obj)
        for body_mesh_obj in body_mesh_objects:
            if hasattr(body_mesh_obj, "show_in_front"):
                body_mesh_obj.show_in_front = True
            if hasattr(body_mesh_obj, "hide_viewport"):
                body_mesh_obj.hide_viewport = True
            if hasattr(body_mesh_obj, "hide_render"):
                body_mesh_obj.hide_render = True
    else:
        for body_mesh_obj in body_mesh_objects:
            if hasattr(body_mesh_obj, "hide_viewport"):
                body_mesh_obj.hide_viewport = False



def _configure_example_skin_mesh_display(mesh_obj: Any) -> None:
    if hasattr(mesh_obj, "show_transparent"):
        mesh_obj.show_transparent = True
    if hasattr(mesh_obj, "color"):
        mesh_obj.color = (0.92, 0.92, 0.98, 0.28)

    mesh_data = getattr(mesh_obj, "data", None)
    if mesh_data is None:
        return

    project_ops = importlib.import_module("melos.blender.addon.operators.project")
    bpy = getattr(project_ops, "bpy", None)
    if bpy is None or not hasattr(mesh_data, "materials"):
        return

    material_name = "melos_example_skin_preview"
    material = bpy.data.materials.get(material_name)
    if material is None:
        material = bpy.data.materials.new(material_name)
    material.use_nodes = True
    material.diffuse_color = (0.92, 0.92, 0.98, 0.28)
    if hasattr(material, "blend_method"):
        material.blend_method = "BLEND"
    if hasattr(material, "shadow_method"):
        material.shadow_method = "NONE"
    node_tree = getattr(material, "node_tree", None)
    principled = node_tree.nodes.get("Principled BSDF") if node_tree is not None else None
    if principled is not None:
        base_color = principled.inputs.get("Base Color")
        if base_color is not None:
            base_color.default_value = (0.92, 0.92, 0.98, 1.0)
        alpha = principled.inputs.get("Alpha")
        if alpha is not None:
            alpha.default_value = 0.28
        roughness = principled.inputs.get("Roughness")
        if roughness is not None:
            roughness.default_value = 0.65

    materials = mesh_data.materials
    if len(materials) == 0:
        materials.append(material)
    else:
        materials[0] = material



def _remove_default_startup_objects(scene: Any) -> None:
    project_ops = importlib.import_module("melos.blender.addon.operators.project")
    bpy = getattr(project_ops, "bpy", None)
    if bpy is None:
        return
    existing_names = {obj.name for obj in scene.objects}
    default_names = {"Cube", "Camera", "Light"}
    if not existing_names or not existing_names.issubset(default_names):
        return
    for name in default_names:
        obj = scene.objects.get(name)
        if obj is not None:
            bpy.data.objects.remove(obj, do_unlink=True)



def _hide_example_support_objects(
    objects: list[Any],
    *,
    keep_objects: list[Any] | None = None,
) -> None:
    keep_ids = {id(obj) for obj in (keep_objects or [])}
    for obj in objects:
        if obj is None or id(obj) in keep_ids:
            continue
        if hasattr(obj, "hide_viewport"):
            obj.hide_viewport = True
        if hasattr(obj, "hide_render"):
            obj.hide_render = True



def _hide_non_deforming_bones(
    arm_obj: Any,
    bone_weights: list[list[float]] | None,
    bone_indices: list[list[int]] | None,
    body_name_map: dict[int, str] | None,
) -> None:
    if bone_weights is None or bone_indices is None or body_name_map is None:
        return
    arm_data = getattr(arm_obj, "data", None)
    bones = getattr(arm_data, "bones", None)
    if bones is None:
        return

    used_link_ids: set[str] = set()
    for weight_row, index_row in zip(bone_weights, bone_indices):
        for weight, body_index in zip(weight_row, index_row):
            if weight <= 1e-8:
                continue
            link_id = body_name_map.get(body_index)
            if link_id:
                used_link_ids.add(link_id)

    for bone in bones:
        if getattr(bone, "name", None) in used_link_ids:
            continue
        if hasattr(bone, "hide"):
            bone.hide = True
def _add_example_cable_device(project, anatomical_system):
    """Add a cable assist device to the example project."""
    # Find key anatomical sites for cable attachment
    pelvis_site = None
    tibia_site = None
    for site in anatomical_system.sites:
        if site.id == "pelvis":
            pelvis_site = site
        if site.id == "tibia_r":
            tibia_site = site
    # Create cable device system
    cable_device = SystemModel(
        id="cable_assist",
        name="Cable Assist Device",
        role=SystemRole.DEVICE,
        root_link_id="cable_anchor",
        links=[
            Link(
                id="cable_anchor",
                name="Cable Anchor",
                transform=Transform.identity(),
            )
        ],
        sites=[
            Site(
                id="knee_pulley",
                name="Knee Pulley",
                link_id="cable_anchor",
                transform=Transform.identity(),
            )
        ],
        actuators=[
            Actuator(
                id="knee_cable",
                name="Knee Assist Cable",
                kind=ActuatorKind.CABLE,
                route=[
                    RouteNode(
                        kind=RouteNodeKind.SITE,
                        site_id="pelvis" if pelvis_site else "",
                    ),
                    RouteNode(
                        kind=RouteNodeKind.WRAP,
                        geometry_id="knee_pulley",
                        side_site_id="knee_pulley_side",
                    ),
                    RouteNode(
                        kind=RouteNodeKind.SITE,
                        site_id="tibia_r" if tibia_site else "",
                    ),
                ],
                cable=CableParameters(
                    stiffness=1200.0,
                    damping=2.0,
                    rest_length=0.5,
                ),
            )
        ],
    )
    # Add device to project
    project.systems.append(cable_device)
