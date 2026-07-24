"""Rerun logging adapter for melos.core.model types.

Converts Pydantic model instances into Rerun log calls.
Arrow is a serialization detail here — the Pydantic model
in melos.core.model is the canonical source of truth.

Usage::

    from melos.core.model import ModelState, SkeletonState
    from melos.rerun.adapter import log_skeleton

    log_skeleton("my_model", skeleton_state)
"""

from __future__ import annotations

import rerun as rr

from melos.core.model import SkeletonState, JointDef, LinkDef, LinkTransform


def log_skeleton(prefix: str, skeleton: SkeletonState) -> None:
    """Log a SkeletonState to Rerun at the given entity path prefix."""
    for name, xf in skeleton.transforms.items():
        rr.log(
            f"{prefix}/skeleton/{name}",
            rr.Transform3D(
                translation=list(xf.translation),
                rotation=list(xf.rotation),
            ),
        )
    for name, link in skeleton.links.items():
        if not link.visible:
            continue
        rr.log(
            f"{prefix}/skeleton/{name}",
            rr.TextDocument(f"mass={link.mass:.3f} kg"),
        )


def log_joint(prefix: str, name: str, joint: JointDef) -> None:
    """Log a JointDef to Rerun."""
    rr.log(
        f"{prefix}/skeleton/joints/{name}",
        rr.TextDocument(f"type={joint.joint_type}"),
    )
