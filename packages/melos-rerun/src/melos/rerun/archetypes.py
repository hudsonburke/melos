"""Custom Rerun archetypes for musculoskeletal models.

An *archetype* bundles a set of components that together describe one semantic
concept (e.g. a single joint).  Logging an archetype is a shorthand for logging
all of its component batches at once.

These archetypes supplement Rerun's built-in archetypes (``Transform3D``,
``Mesh3D``, ``Points3D``, ``Scalars``, …) with musculoskeletal-specific
primitives.
"""

from __future__ import annotations

from typing import Any

import rerun as rr

from .components import JointDefinitionBatch, LinkDefinitionBatch


class Skeleton(rr.AsComponents):
    """A complete articulated skeleton logged at a single entity path.

    Logging a ``Skeleton`` attaches all joints and links at the given path.
    Typically you'd log it once (static data) at the root of your model::

        rr.set_time_seconds("sim_time", 0.0)
        rr.log("subject/skeleton", Skeleton(
            joints=[
                {
                    "joint_type": "pin",
                    "axis": [0, 0, 1],
                    "limits": {"lower": -2.27, "upper": 0.0},
                    "parent_link": "humerus",
                    "child_link": "radius_ulna",
                    "default_qpos": 0.0,
                },
                # …
            ],
            links=[
                {"name": "humerus", "mass": 1.8, "com": [0.0, 0.0, 0.15]},
                # …
            ],
        ))

    The individual links are logged separately with ``rr.Transform3D`` for
    their spatial hierarchy, and ``rr.Mesh3D`` for visual geometry.  This
    archetype only carries the *semantic* definitions (joint type, axis,
    limits) that Rerun's built-in types don't cover.
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
            descriptor = rr.ComponentDescriptor(
                "melos.Skeleton:joints",
                archetype="melos.Skeleton",
                component_type="melos.JointDefinition",
            )
            batch = JointDefinitionBatch(self.joints).described(descriptor)
            batches.append(batch)

        if self.links:
            descriptor = rr.ComponentDescriptor(
                "melos.Skeleton:links",
                archetype="melos.Skeleton",
                component_type="melos.LinkDefinition",
            )
            batch = LinkDefinitionBatch(self.links).described(descriptor)
            batches.append(batch)

        return batches


class Joint(rr.AsComponents):
    """A single joint, intended to be logged at its own entity path.

    This lets each joint be independently selectable in the Rerun viewer::

        rr.log("model/skeleton/joints/r_elbow", Joint(
            joint_type="pin",
            axis=[0, 0, 1],
            limits={"lower": -2.27, "upper": 0.0},
            parent_link="humerus",
            child_link="radius_ulna",
        ))
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
                "limits": limits
                or {"lower": float("-inf"), "upper": float("inf")},
                "parent_link": parent_link,
                "child_link": child_link,
                "default_qpos": default_qpos,
            }
        ]

    def as_component_batches(self) -> list[rr.DescribedComponentBatch]:
        descriptor = rr.ComponentDescriptor(
            "melos.JointDefinition",
            archetype="melos.Joint",
            component_type="melos.JointDefinition",
        )
        batch = JointDefinitionBatch(self._data).described(descriptor)
        return [batch]
