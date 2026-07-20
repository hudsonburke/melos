"""Custom Rerun archetypes for biomechanics.

An *archetype* bundles a set of components that together describe one
semantic concept.  Logging an archetype is short for logging all its
component batches at once at a single entity path.

These supplement Rerun's built-in archetypes (``Transform3D``, ``Mesh3D``,
``Points3D``, ``Scalars``, …).
"""

from __future__ import annotations

from typing import Any

import rerun as rr

from .components import (
    ActuatorDefinitionBatch,
    AssemblyConstraintBatch,
    BodyMeasurementsBatch,
    CableViaPointBatch,
    JointDefinitionBatch,
    LinkDefinitionBatch,
    MuscleDefinitionBatch,
)

# Descriptor namespacing prefix
_NS = "biomech"


def _desc(
    component: str,
    archetype: str | None = None,
    component_type: str | None = None,
) -> rr.ComponentDescriptor:
    return rr.ComponentDescriptor(
        component,
        archetype=archetype,
        component_type=component_type,
    )


class Joint(rr.AsComponents):
    """A single joint, intended to be logged at its own entity path.

    Each joint gets its own path for independent selection in the viewer:
    ``{prefix}/skeleton/joints/{name}``
    """

    def __init__(
        self,
        joint_type: str,
        axis: list[float],
        parent_link: str,
        child_link: str,
        limits: dict[str, float] | None = None,
        default_qpos: float = 0.0,
    ) -> None:
        self._data: list[dict[str, Any]] = [
            {
                "joint_type": joint_type,
                "axis": axis,
                "limits": limits or {"lower": float("-inf"), "upper": float("inf")},
                "parent_link": parent_link,
                "child_link": child_link,
                "default_qpos": default_qpos,
            }
        ]

    def as_component_batches(self) -> list[rr.DescribedComponentBatch]:
        return [
            JointDefinitionBatch(self._data).described(
                _desc(
                    f"{_NS}.JointDefinition",
                    archetype=f"{_NS}.Joint",
                    component_type=f"{_NS}.JointDefinition",
                )
            )
        ]


class Link(rr.AsComponents):
    """A rigid link, logged at ``{prefix}/skeleton/links/{name}``.

    The spatial transform is logged separately as ``rr.Transform3D``.
    This archetype only carries the *semantic* metadata (mass, inertia, mesh).
    """

    def __init__(
        self,
        name: str,
        mass: float = 0.0,
        center_of_mass: list[float] | None = None,
        inertia: list[float] | None = None,
        graphics_file: str = "",
        visible: bool = True,
    ) -> None:
        self._data: list[dict[str, Any]] = [
            {
                "name": name,
                "mass": mass,
                "center_of_mass": center_of_mass or [0.0, 0.0, 0.0],
                "inertia": inertia or [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                "graphics_file": graphics_file,
                "visible": visible,
            }
        ]

    def as_component_batches(self) -> list[rr.DescribedComponentBatch]:
        return [
            LinkDefinitionBatch(self._data).described(
                _desc(
                    f"{_NS}.LinkDefinition",
                    archetype=f"{_NS}.Link",
                    component_type=f"{_NS}.LinkDefinition",
                )
            )
        ]


class Skeleton(rr.AsComponents):
    """A complete articulated skeleton logged at the root skeleton path.

    Convenience archetype that bundles all joints and links at one entity
    path (typically ``{prefix}/skeleton``) so the viewer can display a
    summary of what's available.
    """

    def __init__(
        self,
        joints: list[dict[str, Any]] | None = None,
        links: list[dict[str, Any]] | None = None,
    ) -> None:
        self.joints = joints
        self.links = links

    def as_component_batches(self) -> list[rr.DescribedComponentBatch]:
        batches: list[rr.DescribedComponentBatch] = []
        if self.joints:
            batches.append(
                JointDefinitionBatch(self.joints).described(
                    _desc(
                        f"{_NS}.Skeleton:joints",
                        archetype=f"{_NS}.Skeleton",
                        component_type=f"{_NS}.JointDefinition",
                    )
                )
            )
        if self.links:
            batches.append(
                LinkDefinitionBatch(self.links).described(
                    _desc(
                        f"{_NS}.Skeleton:links",
                        archetype=f"{_NS}.Skeleton",
                        component_type=f"{_NS}.LinkDefinition",
                    )
                )
            )
        return batches


class Subject(rr.AsComponents):
    """Subject anthropometric measurements.

    Logged as static data at ``{prefix}/subject``.
    """

    def __init__(self, measurements: list[dict[str, Any]]) -> None:
        self.measurements = measurements

    def as_component_batches(self) -> list[rr.DescribedComponentBatch]:
        return [
            BodyMeasurementsBatch(self.measurements).described(
                _desc(
                    f"{_NS}.Subject:measurements",
                    archetype=f"{_NS}.Subject",
                    component_type=f"{_NS}.BodyMeasurements",
                )
            )
        ]


class Actuator(rr.AsComponents):
    """An actuator defined on a joint."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = [data]

    def as_component_batches(self) -> list[rr.DescribedComponentBatch]:
        return [
            ActuatorDefinitionBatch(self._data).described(
                _desc(
                    f"{_NS}.ActuatorDefinition",
                    archetype=f"{_NS}.Actuator",
                    component_type=f"{_NS}.ActuatorDefinition",
                )
            )
        ]


class CableViaPoint(rr.AsComponents):
    """A cable-routing via-point."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = [data]

    def as_component_batches(self) -> list[rr.DescribedComponentBatch]:
        return [
            CableViaPointBatch(self._data).described(
                _desc(
                    f"{_NS}.CableViaPoint",
                    archetype=f"{_NS}.Cable",
                    component_type=f"{_NS}.CableViaPoint",
                )
            )
        ]


class Assembly(rr.AsComponents):
    """An assembly constraint between two systems."""

    def __init__(self, constraints: list[dict[str, Any]]) -> None:
        self.constraints = constraints

    def as_component_batches(self) -> list[rr.DescribedComponentBatch]:
        return [
            AssemblyConstraintBatch(self.constraints).described(
                _desc(
                    f"{_NS}.AssemblyConstraint",
                    archetype=f"{_NS}.Assembly",
                    component_type=f"{_NS}.AssemblyConstraint",
                )
            )
        ]
