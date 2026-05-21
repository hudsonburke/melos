"""Direct Blender scene -> shared anatomical ``SystemModel`` mapping."""

from __future__ import annotations

from collections.abc import Iterable
from typing import cast

from melos.core.common.mechanics import InertialProperties
from melos.core.common.types import Bounds, Transform
from melos.core.kinematics.enums import CoordinateKind, JointKind
from melos.core.kinematics.model import CoordinateDefinition
from melos.core.system.enums import ActuatorKind, GeometryRole, SystemRole
from melos.core.system.model import Actuator, Geometry, Joint, Link, Site, SystemModel

from melos.blender.constants import (
    ASSET_ID_KEY,
    BODY_CENTER_OF_MASS_KEY,
    BODY_INERTIA_KEY,
    BODY_MASS_KEY,
    DISPLAY_NAME_KEY,
    ENTITY_ID_KEY,
    ENTITY_KIND_KEY,
    FRAME_LINK_ID_KEY,
    FRAME_IS_ANATOMICAL_KEY,
    JOINT_CHILD_LINK_ID_KEY,
    JOINT_CHILD_FRAME_ID_KEY,
    JOINT_COORDINATE_AXIS_KEY,
    JOINT_COORDINATE_DEFAULT_VALUE_KEY,
    JOINT_COORDINATE_ID_KEY,
    JOINT_COORDINATE_KIND_KEY,
    JOINT_COORDINATE_NAME_KEY,
    JOINT_KIND_KEY,
    JOINT_PARENT_LINK_ID_KEY,
    JOINT_PARENT_FRAME_ID_KEY,
    ANATOMICAL_LINK_KIND,
    ANATOMICAL_SITE_KIND,
    ANATOMICAL_JOINT_KIND,
)
from melos.blender.services.builders import build_system_model

from .landmark import build_landmarks_from_scene
from .muscle import build_muscles_from_scene, build_wrap_geometries_from_scene
from .transforms import transform_from_object


def build_anatomical_system_from_scene(scene: object, settings: object) -> SystemModel:
    """Build an anatomical ``SystemModel`` from the current Blender scene."""

    body_objects = list(_iter_scene_objects(scene, ANATOMICAL_LINK_KIND))
    frame_objects = list(_iter_scene_objects(scene, ANATOMICAL_SITE_KIND))
    joint_objects = list(_iter_scene_objects(scene, ANATOMICAL_JOINT_KIND))

    links = [build_anatomical_link_from_object(object_) for object_ in body_objects]
    frame_sites = [build_anatomical_site_from_object(object_) for object_ in frame_objects]
    frame_link_ids = {site.id: site.link_id for site in frame_sites}
    joints = [
        build_anatomical_joint_from_object(object_, frame_link_ids=frame_link_ids)
        for object_ in joint_objects
    ]

    landmark_sites = build_landmarks_from_scene(scene)

    muscles = build_muscles_from_scene(scene, settings)
    wraps = build_wrap_geometries_from_scene(scene)
    muscle_sites: list[Site] = []
    geometries: list[Geometry] = []
    actuators: list[Actuator] = []
    for wrap in wraps:
        parameters = {}
        if wrap.parameters is not None:
            if hasattr(wrap.parameters, "radius"):
                parameters["radius"] = float(wrap.parameters.radius)
            if hasattr(wrap.parameters, "height"):
                parameters["height"] = float(wrap.parameters.height)
        geometries.append(
            Geometry(
                id=wrap.id,
                name=wrap.name,
                kind=wrap.kind.value,
                role=GeometryRole.WRAP,
                link_id=wrap.link_id,
                site_id=wrap.site_id,
                transform=wrap.transform,
                parameters=parameters,
            )
        )

    for muscle in muscles:
        site_ids: list[str] = []
        for point in muscle.path.points:
            site_id = f"{muscle.id}_{point.id}"
            muscle_sites.append(
                Site(
                    id=site_id,
                    name=point.name,
                    link_id=point.link_id,
                    parent_site_id=point.site_id,
                    transform=Transform(translation=point.position),
                    tags=["muscle_path_point", point.kind.value, muscle.id],
                )
            )
            site_ids.append(site_id)
        actuators.append(
            Actuator(
                id=muscle.id,
                name=muscle.name,
                kind=ActuatorKind.MUSCLE,
                site_ids=site_ids,
                parameters={"wrap_geometry_ids": list(muscle.path.wrap_geometry_ids)},
            )
        )

    root_link_id = getattr(settings, "anatomical_system_root_link_id", None) or None
    profile: dict[str, object] = {}
    species = getattr(settings, "anatomical_species", None) or None
    if species is not None:
        profile["species"] = species

    return build_system_model(
        system_id=getattr(settings, "anatomical_system_id", "anatomical"),
        name=getattr(settings, "anatomical_system_name", "anatomical"),
        role=SystemRole.ANATOMICAL,
        description=getattr(settings, "anatomical_system_description", ""),
        links=links,
        joints=joints,
        sites=[*frame_sites, *landmark_sites, *muscle_sites],
        geometries=geometries,
        actuators=actuators,
        root_link_id=root_link_id,
        profile=profile,
    )


def build_anatomical_link_from_object(object_: object) -> Link:
    """Build an anatomical link/link directly from a tagged Blender object."""

    inertial = _build_inertial_properties(object_)
    asset_ids = _collect_body_asset_ids(object_)
    return Link(
        id=_required_string(object_, ENTITY_ID_KEY),
        name=_preferred_name(object_),
        transform=transform_from_object(object_, use_local=True),
        inertial=inertial,
        asset_ids=asset_ids,
    )


def build_anatomical_site_from_object(object_: object) -> Site:
    """Build an anatomical site as a tagged shared site."""

    body_id = _optional_string(object_, FRAME_LINK_ID_KEY)
    if body_id is None:
        body_id = _body_id_from_parent(object_)

    tags = ["frame"]
    if bool(getattr(object_, "get", lambda *_: False)(FRAME_IS_ANATOMICAL_KEY, False)):
        tags.append("anatomical")

    return Site(
        id=_required_string(object_, ENTITY_ID_KEY),
        name=_preferred_name(object_),
        link_id=body_id,
        transform=transform_from_object(object_, use_local=True),
        tags=tags,
    )


def build_anatomical_joint_from_object(
    object_: object,
    *,
    frame_link_ids: dict[str, str | None],
) -> Joint:
    """Build a shared ``Joint`` from a tagged Blender object."""

    parent_frame_id = _optional_string(object_, JOINT_PARENT_FRAME_ID_KEY)
    child_frame_id = _optional_string(object_, JOINT_CHILD_FRAME_ID_KEY)
    parent_link_id = _optional_string(object_, JOINT_PARENT_LINK_ID_KEY)
    child_link_id = _optional_string(object_, JOINT_CHILD_LINK_ID_KEY)

    if parent_link_id is None and parent_frame_id is not None:
        parent_link_id = frame_link_ids.get(parent_frame_id)
    if child_link_id is None and child_frame_id is not None:
        child_link_id = frame_link_ids.get(child_frame_id)
    if child_link_id is None:
        raise ValueError(
            f"Joint {_required_string(object_, ENTITY_ID_KEY)!r} is missing a child link reference."
        )

    return Joint(
        id=_required_string(object_, ENTITY_ID_KEY),
        name=_preferred_name(object_),
        kind=JointKind(getattr(object_, "get", lambda *_: JointKind.REVOLUTE.value)(JOINT_KIND_KEY, JointKind.REVOLUTE.value)),
        parent_link_id=parent_link_id,
        child_link_id=child_link_id,
        parent_site_id=parent_frame_id,
        child_site_id=child_frame_id,
        coordinates=[_build_coordinate_definition(object_)],
    )


def _iter_scene_objects(scene: object, entity_kind: str) -> list[object]:
    objects = getattr(scene, "objects", None)
    if objects is None:
        raise ValueError("Expected a Blender scene with an 'objects' collection.")

    return [
        object_
        for object_ in objects
        if getattr(object_, "get", lambda *_: None)(ENTITY_KIND_KEY) == entity_kind
    ]


def _build_coordinate_definition(object_: object) -> CoordinateDefinition:
    coordinate_id = _required_string(object_, JOINT_COORDINATE_ID_KEY)
    coordinate_name = _optional_string(object_, JOINT_COORDINATE_NAME_KEY) or coordinate_id
    coordinate_kind = CoordinateKind(
        getattr(object_, "get", lambda *_: CoordinateKind.ROTATION.value)(
            JOINT_COORDINATE_KIND_KEY,
            CoordinateKind.ROTATION.value,
        )
    )
    axis = _tuple3(
        getattr(object_, "get", lambda *_: (1.0, 0.0, 0.0))(
            JOINT_COORDINATE_AXIS_KEY,
            (1.0, 0.0, 0.0),
        )
    )
    default_value = float(
        getattr(object_, "get", lambda *_: 0.0)(JOINT_COORDINATE_DEFAULT_VALUE_KEY, 0.0)
    )

    return CoordinateDefinition(
        id=coordinate_id,
        name=coordinate_name,
        kind=coordinate_kind,
        axis=axis,
        default_value=default_value,
        limits=Bounds(),
    )


def _build_inertial_properties(object_: object) -> InertialProperties | None:
    getter = getattr(object_, "get", lambda *_: None)
    mass = getter(BODY_MASS_KEY)
    center_of_mass = getter(BODY_CENTER_OF_MASS_KEY)
    inertia = getter(BODY_INERTIA_KEY)

    if mass is None and center_of_mass is None and inertia is None:
        return None

    return InertialProperties(
        mass=float(mass) if mass is not None else None,
        center_of_mass=_tuple3(center_of_mass) if center_of_mass is not None else None,
        inertia_about_com=_tuple6(inertia) if inertia is not None else None,
    )


def _preferred_name(object_: object) -> str:
    return _optional_string(object_, DISPLAY_NAME_KEY) or getattr(object_, "name", "unnamed")


def _required_string(object_: object, key: str) -> str:
    value = _optional_string(object_, key)
    if value is None:
        raise ValueError(f"Expected Blender object {getattr(object_, 'name', '<unnamed>')!r} to define {key!r}.")
    return value


def _optional_string(object_: object, key: str) -> str | None:
    value = getattr(object_, "get", lambda *_: None)(key)
    if value in (None, ""):
        return None
    return str(value)


def _body_id_from_parent(object_: object) -> str | None:
    parent = getattr(object_, "parent", None)
    if parent is None:
        return None
    return _optional_string(parent, ENTITY_ID_KEY)


def _collect_body_asset_ids(object_: object) -> list[str]:
    children = getattr(object_, "children", ())
    return [
        asset_id
        for child in children
        if (asset_id := _optional_string(child, ASSET_ID_KEY)) is not None
    ]


def _tuple3(value: Iterable[object]) -> tuple[float, float, float]:
    components = tuple(float(cast(float | int | str, component)) for component in value)
    if len(components) != 3:
        raise ValueError(f"Expected 3 components, received {len(components)}.")
    return components  # type: ignore[return-value]


def _tuple6(value: Iterable[object]) -> tuple[float, float, float, float, float, float]:
    components = tuple(float(cast(float | int | str, component)) for component in value)
    if len(components) != 6:
        raise ValueError(f"Expected 6 components, received {len(components)}.")
    return components  # type: ignore[return-value]
