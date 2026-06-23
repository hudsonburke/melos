"""ElementTree MJCF joint and coordinate mapper fallback."""

from __future__ import annotations

import math
from xml.etree.ElementTree import Element

from melos.core.system.model import Bounds, Vec3
from melos.core.system.enums import CoordinateKind, JointKind
from melos.core.system.model import CoordinateDefinition
from melos.core.system.model import Joint

from .bodies import BodyTree
from .defaults import DefaultClassMap, apply_defaults, get_active_class
from .report import ImportReport
from .xml_parser import CompilerDirectives

_MJCF_TYPE_TO_JOINT_KIND: dict[str, JointKind] = {
    "hinge": JointKind.REVOLUTE,
    "slide": JointKind.PRISMATIC,
    "ball": JointKind.SPHERICAL,
}

_JOINT_KIND_TO_COORD_KIND: dict[JointKind, CoordinateKind] = {
    JointKind.REVOLUTE: CoordinateKind.ROTATION,
    JointKind.PRISMATIC: CoordinateKind.TRANSLATION,
    JointKind.SPHERICAL: CoordinateKind.ROTATION,
}

_DEFAULT_AXIS: Vec3 = (0.0, 0.0, 1.0)


def _parse_axis(axis_str: str | None) -> Vec3:
    if axis_str is None:
        return _DEFAULT_AXIS
    parts = axis_str.split()
    return (float(parts[0]), float(parts[1]), float(parts[2]))


def map_joints(
    worldbody: Element,
    body_tree: BodyTree,
    defaults: DefaultClassMap,
    directives: CompilerDirectives,
    report: ImportReport,
) -> list[Joint]:
    _ = worldbody
    angle_scale = math.pi / 180.0 if directives.angle == "degree" else 1.0
    joints: list[Joint] = []

    for body_name, body_info in body_tree.items():
        child_class = body_info.child_class
        explicit_joint_elements = list(body_info.element.findall("joint"))
        explicit_joint_count = 0
        coordinate_definitions: list[CoordinateDefinition] = []
        joint_kinds: list[JointKind] = []

        for joint_el in explicit_joint_elements:
            explicit_joint_count += 1
            active_class = get_active_class(joint_el, child_class)
            apply_defaults(joint_el, active_class, defaults)

            type_str = joint_el.get("type", "hinge")
            if type_str == "free":
                report.add_warning(
                    code="FREE_JOINT_SKIPPED",
                    message="<joint type='free'> is not supported and will be skipped",
                    location=f"body:{body_name}",
                )
                continue

            joint_kind = _MJCF_TYPE_TO_JOINT_KIND.get(type_str)
            if joint_kind is None:
                report.add_warning(
                    code="UNKNOWN_JOINT_TYPE",
                    message=f"Unknown joint type '{type_str}', skipping",
                    location=f"body:{body_name}",
                )
                continue

            name = joint_el.get("name")
            if name is None:
                report.add_warning(
                    code="MISSING_JOINT_NAME",
                    message="<joint> element has no name attribute",
                    location=f"body:{body_name}",
                )
                continue

            axis = _parse_axis(joint_el.get("axis"))

            limits: Bounds | None = None
            if joint_el.get("limited", "false").lower() == "true":
                range_str = joint_el.get("range")
                if range_str is not None:
                    lo_str, hi_str = range_str.split()
                    limits = Bounds(lower=float(lo_str) * angle_scale, upper=float(hi_str) * angle_scale)

            ref_str = joint_el.get("ref")
            default_value = float(ref_str) * angle_scale if ref_str is not None else 0.0

            coordinate_definitions.append(CoordinateDefinition(
                id=name,
                name=name,
                kind=_JOINT_KIND_TO_COORD_KIND[joint_kind],
                axis=axis,
                default_value=default_value,
                limits=limits,
            ))
            joint_kinds.append(joint_kind)

        if coordinate_definitions:
            resolved_kind = joint_kinds[0] if all(kind == joint_kinds[0] for kind in joint_kinds) else JointKind.CUSTOM
            joint_id = coordinate_definitions[0].id if len(coordinate_definitions) == 1 else f"{body_name}_joint"
            joints.append(Joint(
                id=joint_id,
                name=joint_id,
                kind=resolved_kind,
                parent_link_id=body_info.parent_name,
                child_link_id=body_name,
                coordinates=coordinate_definitions,
            ))

        if body_info.parent_name is not None and explicit_joint_count == 0:
            joints.append(Joint(
                id=f"{body_name}_fixed",
                name=f"{body_name}_fixed",
                kind=JointKind.FIXED,
                parent_link_id=body_info.parent_name,
                child_link_id=body_name,
                coordinates=[],
            ))

    return joints
