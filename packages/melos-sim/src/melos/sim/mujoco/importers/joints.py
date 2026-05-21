"""MJCF joint and coordinate mapper for ``melos.sim.mujoco.importers``."""

from __future__ import annotations

import math
from typing import Any

from melos.core.common.types import Bounds, Vec3
from melos.core.kinematics.enums import CoordinateKind, JointKind
from melos.core.kinematics.model import CoordinateDefinition
from melos.core.system.model import Joint

from .bodies import BodyTree, _commit_defaults_if_supported
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


def _parse_axis(value: object | None) -> Vec3:
    if value is None:
        return _DEFAULT_AXIS
    parts = tuple(float(component) for component in value)
    if len(parts) != 3:
        return _DEFAULT_AXIS
    return parts  # type: ignore[return-value]


def map_joints(
    body_tree: BodyTree,
    directives: CompilerDirectives,
    report: ImportReport,
) -> list[Joint]:
    angle_scale = math.pi / 180.0 if directives.angle == "degree" else 1.0
    joints: list[Joint] = []

    for body_name, body_info in body_tree.items():
        explicit_joint_elements = list(getattr(body_info.element, "joint", []))
        explicit_joint_count = 0
        for joint_el in explicit_joint_elements:
            explicit_joint_count += 1
            _commit_defaults_if_supported(joint_el)

            type_str = str(getattr(joint_el, "type", None) or "hinge")
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

            name = getattr(joint_el, "name", None)
            if name is None:
                report.add_warning(
                    code="MISSING_JOINT_NAME",
                    message="<joint> element has no name attribute",
                    location=f"body:{body_name}",
                )
                continue

            axis = _parse_axis(getattr(joint_el, "axis", None))

            limits: Bounds | None = None
            limited = getattr(joint_el, "limited", None)
            if _is_truthy(limited):
                range_values = getattr(joint_el, "range", None)
                if range_values is not None:
                    lo, hi = (float(v) * angle_scale for v in range_values)
                    limits = Bounds(lower=lo, upper=hi)

            ref_value = getattr(joint_el, "ref", None)
            default_value = float(ref_value) * angle_scale if ref_value is not None else 0.0

            coord = CoordinateDefinition(
                id=str(name),
                name=str(name),
                kind=_JOINT_KIND_TO_COORD_KIND[joint_kind],
                axis=axis,
                default_value=default_value,
                limits=limits,
            )

            joints.append(Joint(
                id=str(name),
                name=str(name),
                kind=joint_kind,
                parent_link_id=body_info.parent_name,
                child_link_id=body_name,
                coordinates=[coord],
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


def _is_truthy(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"true", "1", "yes"}
