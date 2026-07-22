"""MJCF parser — uses the MuJoCo Python package to load models and produce
Arrow-based SkeletonState.  Much more robust than manual XML parsing since
MuJoCo handles includes, compiler directives, and asset resolution natively.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import mujoco
import numpy as np

from melos.backend.models import (
    JointDef,
    JointLimits,
    LinkDef,
    LinkTransform,
    SkeletonState,
)

# MuJoCo joint type constants
_MJ_HINGE = 0
_MJ_SLIDE = 1


def parse_mjcf(path: str | Path) -> SkeletonState:
    """Parse an MJCF model file using the MuJoCo engine.

    Uses ``mujoco.MjModel.from_xml_path()`` which handles includes,
    compiler directives, and asset resolution automatically.

    Returns a ``SkeletonState`` with links, joints, transforms, and
    parent relationships extracted from the MuJoCo model structure.
    """
    path = Path(path).expanduser().resolve()
    model = mujoco.MjModel.from_xml_path(str(path))

    links: dict[str, LinkDef] = {}
    transforms: dict[str, LinkTransform] = {}
    joints: dict[str, JointDef] = {}
    parent_map: dict[str, str] = {}
    order: list[str] = []
    body_names: list[str] = []

    # Collect body names (id → name mapping)
    for i in range(model.nbody):
        name = model.body(i).name or f"body_{i}"
        body_names.append(name)

    # Add ground body (MuJoCo body id 0 is world)
    transforms["ground"] = LinkTransform(
        translation=(0.0, 0.0, 0.0),
        rotation=(1.0, 0.0, 0.0, 0.0),
    )
    links["ground"] = LinkDef(name="ground", mass=0.0, visible=False)

    # Parse all bodies including world (id=0)
    body_parentid = model.body_parentid
    for i in range(model.nbody):
        name = body_names[i]

        if i == 0:
            # World body — skip; its children become direct children of "ground"
            # Don't add world to parent_map or transforms
            continue

        parent_id = body_parentid[i]
        parent_name = body_names[parent_id] if parent_id >= 0 else "ground"
        if parent_id == 0:
            # Children of MuJoCo's world body attach directly to "ground"
            parent_name = "ground"

        # Position and rotation from body's fixed (i.e., joint-free) offset
        body = model.body(i)
        pos = body.pos.tolist() if hasattr(body.pos, "tolist") else [0, 0, 0]
        quat = body.quat.tolist() if hasattr(body.quat, "tolist") else [1, 0, 0, 0]

        transforms[name] = LinkTransform(
            translation=(float(pos[0]), float(pos[1]), float(pos[2])),
            rotation=(float(quat[0]), float(quat[1]), float(quat[2]), float(quat[3])),
        )

        if parent_name != name:
            parent_map[name] = parent_name

        # Inertial — from body mass, COM, inertia
        mass = float(body.mass[0]) if hasattr(body.mass, "__getitem__") else 0.0
        com = body.ipos.tolist() if hasattr(body.ipos, "tolist") else [0, 0, 0]
        # full inertia from MuJoCo body_inertia (3-element diag, pad to 6)
        inertia = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        if model.body_inertia is not None and i < len(model.body_inertia):
            inert_diag = model.body_inertia[i]
            if hasattr(inert_diag, "tolist"):
                diag = inert_diag.tolist()
                if len(diag) >= 3:
                    inertia = [float(diag[0]), float(diag[1]), float(diag[2]), 0.0, 0.0, 0.0]

        # Mesh geometry
        graphics_file = ""
        for geom_idx in range(model.ngeom):
            geom = model.geom(geom_idx)
            if geom.bodyid == i:
                if geom.type == mujoco.mjtGeom.mjGEOM_MESH:
                    mesh_id = geom.dataid
                    if isinstance(mesh_id, np.ndarray):
                        mesh_id = int(mesh_id.item()) if mesh_id.size > 0 else -1
                    else:
                        mesh_id = int(mesh_id) if mesh_id >= 0 else -1
                    if mesh_id >= 0 and mesh_id < model.nmesh:
                        mesh_name = model.mesh(mesh_id).name
                        if mesh_name:
                            graphics_file = str(mesh_name)

        links[name] = LinkDef(
            name=name,
            mass=float(mass),
            center_of_mass=[float(v) for v in com],
            inertia=[float(v) for v in inertia],
            graphics_file=graphics_file,
        )

    # Joint mapping: MuJoCo joint id → child body id
    for jnt_idx in range(model.njnt):
        jnt = model.joint(jnt_idx)
        jname = jnt.name or f"joint_{jnt_idx}"
        jtype = jnt.type  # mjtJoint enum
        child_body_id = jnt.bodyid[0] if hasattr(jnt.bodyid, "__getitem__") else 0
        child_name = body_names[child_body_id] if child_body_id < len(body_names) else "unknown"

        # Map MuJoCo joint type
        if jtype == _MJ_HINGE:
            melos_type = "PinJoint"
        elif jtype == _MJ_SLIDE:
            melos_type = "PrismaticJoint"
        else:
            melos_type = "CustomJoint"

        axis = jnt.axis.tolist() if hasattr(jnt.axis, "tolist") else [0, 0, 1]
        range_vals = jnt.range.tolist() if hasattr(jnt.range, "tolist") else [0, 0]
        limits = JointLimits(
            lower=float(range_vals[0]) if not math.isinf(range_vals[0]) else -math.inf,
            upper=float(range_vals[1]) if not math.isinf(range_vals[1]) else math.inf,
        )

        parent_name = parent_map.get(child_name, "ground")

        joints[jname] = JointDef(
            joint_type=melos_type,
            axis=[float(v) for v in axis],
            limits=limits,
            parent_link=parent_name,
            child_link=child_name,
        )

    # Build topological order from MuJoCo's body tree
    def _walk_body(body_id: int, out: list[str]) -> None:
        name = body_names[body_id] if body_id < len(body_names) else f"body_{body_id}"
        if name not in out:
            out.append(name)
        for child_id, parent_id in enumerate(model.body_parentid):
            if parent_id == body_id and child_id != body_id:
                _walk_body(child_id, out)

    order = ["ground"]
    _walk_body(0, order)
    # Remove world body (MuJoCo internal, not in links/transforms)
    order = [n for n in order if n in transforms]

    # Ensure all named bodies are in order
    for name in body_names:
        if name not in order:
            order.append(name)

    # Compute descendants
    children_of: dict[str, list[str]] = {}
    for c, p in parent_map.items():
        children_of.setdefault(p, []).append(c)

    descendants: dict[str, list[str]] = {}
    for name in reversed(order):
        desc_set = {name}
        for child in children_of.get(name, []):
            desc_set.update(descendants.get(child, {child}))
        descendants[name] = sorted(desc_set)

    return SkeletonState(
        joints=joints,
        links=links,
        transforms=transforms,
        parent_map=parent_map,
        order=order,
        descendants=descendants,
    )
