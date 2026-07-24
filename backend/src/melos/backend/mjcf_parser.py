"""MJCF parser — reads MuJoCo models into Arrow SkeletonState + cable defs.

Uses the MuJoCo Python package for structural parsing (bodies, joints, meshes)
and accesses tendon/wrap/actuator arrays directly from the MjModel for
full tendon and muscle extraction.

Returns ``(SkeletonState, cable_defs)`` for round-trip compatibility with
the MJCF compiler.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import mujoco
import numpy as np

from melos.core.model import (
    JointDef,
    JointLimits,
    LinkDef,
    LinkTransform,
    SkeletonState,
)

_MJ_HINGE = 0
_MJ_SLIDE = 1


def parse_mjcf(path: str | Path) -> tuple[SkeletonState, list[dict[str, Any]]]:
    """Parse an MJCF model file into a SkeletonState + cable definitions.

    Returns:
        Tuple of (SkeletonState, cable_defs) where cable_defs is a list
        of dicts ready for ``compile_skeleton(cables=...)``.
    """
    path = Path(path).expanduser().resolve()
    model = mujoco.MjModel.from_xml_path(str(path))

    links: dict[str, LinkDef] = {}
    transforms: dict[str, LinkTransform] = {}
    joints: dict[str, JointDef] = {}
    parent_map: dict[str, str] = {}
    order: list[str] = []
    body_names: list[str] = []

    for i in range(model.nbody):
        name = model.body(i).name or f"body_{i}"
        body_names.append(name)

    # Add ground
    transforms["ground"] = LinkTransform(
        translation=(0.0, 0.0, 0.0), rotation=(1.0, 0.0, 0.0, 0.0),
    )
    links["ground"] = LinkDef(name="ground", mass=0.0, visible=False)

    # Build name → body_id map for site resolution
    body_name_to_id: dict[str, int] = {name: i for i, name in enumerate(body_names)}

    # Parse bodies
    body_parentid = model.body_parentid
    for i in range(model.nbody):
        name = body_names[i]
        if i == 0:
            continue
        parent_id = body_parentid[i]
        parent_name = body_names[parent_id] if parent_id >= 0 else "ground"
        if parent_id == 0:
            parent_name = "ground"

        body = model.body(i)
        pos = body.pos.tolist() if hasattr(body.pos, "tolist") else [0, 0, 0]
        quat = body.quat.tolist() if hasattr(body.quat, "tolist") else [1, 0, 0, 0]

        transforms[name] = LinkTransform(
            translation=(float(pos[0]), float(pos[1]), float(pos[2])),
            rotation=(float(quat[0]), float(quat[1]), float(quat[2]), float(quat[3])),
        )
        if parent_name != name:
            parent_map[name] = parent_name

        mass = float(body.mass[0]) if hasattr(body.mass, "__getitem__") else 0.0
        com = body.ipos.tolist() if hasattr(body.ipos, "tolist") else [0, 0, 0]
        inertia = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        if model.body_inertia is not None and i < len(model.body_inertia):
            diag = model.body_inertia[i]
            if hasattr(diag, "tolist"):
                d = diag.tolist()
                if len(d) >= 3:
                    inertia = [float(d[0]), float(d[1]), float(d[2]), 0.0, 0.0, 0.0]

        # Mesh geometry
        graphics_file = ""
        for geom_idx in range(model.ngeom):
            geom = model.geom(geom_idx)
            if geom.bodyid == i and geom.type == mujoco.mjtGeom.mjGEOM_MESH:
                mid = geom.dataid
                if isinstance(mid, np.ndarray):
                    mid = int(mid.item()) if mid.size > 0 else -1
                else:
                    mid = int(mid) if mid >= 0 else -1
                if mid >= 0 and mid < model.nmesh and model.mesh(mid).name:
                    graphics_file = str(model.mesh(mid).name)

        links[name] = LinkDef(
            name=name, mass=float(mass),
            center_of_mass=[float(v) for v in com],
            inertia=[float(v) for v in inertia],
            graphics_file=graphics_file,
        )

    # Joints
    for jnt_idx in range(model.njnt):
        jnt = model.joint(jnt_idx)
        jname = jnt.name or f"joint_{jnt_idx}"
        jtype = jnt.type
        cid = jnt.bodyid[0] if hasattr(jnt.bodyid, "__getitem__") else 0
        cname = body_names[cid] if cid < len(body_names) else "unknown"
        melos_type = "PinJoint" if jtype == _MJ_HINGE else "PrismaticJoint" if jtype == _MJ_SLIDE else "CustomJoint"
        axis = jnt.axis.tolist() if hasattr(jnt.axis, "tolist") else [0, 0, 1]
        rv = jnt.range.tolist() if hasattr(jnt.range, "tolist") else [0, 0]
        limits = JointLimits(
            lower=float(rv[0]) if not math.isinf(rv[0]) else -math.inf,
            upper=float(rv[1]) if not math.isinf(rv[1]) else math.inf,
        )
        joints[jname] = JointDef(
            joint_type=melos_type, axis=[float(v) for v in axis],
            limits=limits,
            parent_link=parent_map.get(cname, "ground"),
            child_link=cname,
        )

    # Topological order
    def _walk(bid: int, out: list[str]) -> None:
        nb = body_names[bid] if bid < len(body_names) else f"body_{bid}"
        if nb not in out:
            out.append(nb)
        for ci, pi in enumerate(model.body_parentid):
            if pi == bid and ci != bid:
                _walk(ci, out)

    order = ["ground"]
    _walk(0, order)
    order = [n for n in order if n in transforms]
    for nb in body_names:
        if nb not in order:
            order.append(nb)

    children_of: dict[str, list[str]] = {}
    for c, p in parent_map.items():
        children_of.setdefault(p, []).append(c)
    descendants: dict[str, list[str]] = {}
    for n in reversed(order):
        ds = {n}
        for ch in children_of.get(n, []):
            ds.update(descendants.get(ch, {ch}))
        descendants[n] = sorted(ds)

    skeleton = SkeletonState(
        joints=joints, links=links, transforms=transforms,
        parent_map=parent_map, order=order, descendants=descendants,
    )

    # ── Extract cable definitions from tendons ────────────────────────
    cables: list[dict[str, Any]] = []
    site_body_map: dict[int, str] = {}
    for si in range(model.nsite):
        bid = model.site_bodyid[si] if hasattr(model, "site_bodyid") else model.site(si).bodyid[0]
        nb = body_names[bid] if bid < len(body_names) else "ground"
        site_body_map[si] = nb

    for ti in range(model.ntendon):
        tname = model.tendon(ti).name or f"tendon_{ti}"
        adr = int(model.tendon_adr[ti])
        num = int(model.tendon_num[ti])
        width = float(model.tendon_width[ti]) if ti < len(model.tendon_width) else 0.005
        lengthspring = model.tendon_lengthspring[ti] if hasattr(model, 'tendon_lengthspring') and len(model.tendon_lengthspring) > ti else [0, 0]

        via_points: list[dict[str, Any]] = []
        for w in range(num):
            idx = adr + w
            wtype = int(model.wrap_type[idx])
            wid = int(model.wrap_objid[idx])
            prm = float(model.wrap_prm[idx])

            if wtype == 3:  # site wrap
                sname = model.site(wid).name if wid < model.nsite else f"wp_{idx}"
                bid = model.site_bodyid[wid] if hasattr(model, 'site_bodyid') and wid < len(model.site_bodyid) else 0
                bname = site_body_map.get(wid, body_names[bid] if bid < len(body_names) else "ground")
                spos = model.site_pos[wid] if hasattr(model, 'site_pos') and wid < len(model.site_pos) else [0, 0, 0]
                via_points.append({
                    "body": bname,
                    "pos": (float(spos[0]), float(spos[1]), float(spos[2])),
                    "wrap_radius": 0,
                })
            elif wtype == 4:  # wrap geom (cylinder/sphere)
                gname = model.geom(wid).name if wid < model.ngeom else f"wg_{idx}"
                # Find which body this geom is on
                gbody_id = model.geom(wid).bodyid if wid < model.ngeom else 0
                if hasattr(gbody_id, '__getitem__'):
                    gbody_id = gbody_id[0]
                gbody_id = int(gbody_id)
                bname = body_names[gbody_id] if gbody_id < len(body_names) else "ground"
                # Find geom size (MuJoCo stores geom sizes)
                gsize = model.geom_size[wid] if hasattr(model, 'geom_size') and wid < len(model.geom_size) else [0.01, 0.01, 0.01]
                radius = float(gsize[0]) if len(gsize) > 0 else 0.01
                # Geom position (relative to body)
                gpos = model.geom_pos[wid] if hasattr(model, 'geom_pos') and wid < len(model.geom_pos) else [0, 0, 0]
                via_points.append({
                    "body": bname,
                    "pos": (float(gpos[0]), float(gpos[1]), float(gpos[2])),
                    "wrap_radius": radius,
                })
            elif wtype == 5:  # pulley — skip for now
                pass

        if via_points:
            cable_def: dict[str, Any] = {
                "id": tname,
                "spring_length": float(lengthspring[0]) if lengthspring[0] > 0 else 0.3,
                "diameter": width,
                "max_force": 500.0,
                "via_points": via_points,
                "actuator_type": "motor",
            }

            # Find ALL actuators for this tendon, pick the best match
            matching_acts: list[dict[str, Any]] = []
            for act_i in range(model.nu):
                trntype = int(model.actuator_trntype[act_i]) if hasattr(model, 'actuator_trntype') and act_i < len(model.actuator_trntype) else 0
                trnid = model.actuator_trnid[act_i] if hasattr(model, 'actuator_trnid') and act_i < len(model.actuator_trnid) else [-1, -1]
                tid = int(trnid[0]) if len(trnid) > 0 else -1
                if tid == ti:
                    matching_acts.append({"idx": act_i, "trntype": trntype})

            # Pick the best actuator: muscle > motor
            best_act = None
            for ma in matching_acts:
                if ma["trntype"] == 3:  # muscle
                    best_act = ma
                    break
            if best_act is None and matching_acts:
                # Fall back to first actuator (likely motor)
                best_act = matching_acts[0]

            if best_act:
                act_i = best_act["idx"]
                trntype = best_act["trntype"]
                if trntype == 3:  # mjTRN_MUSCLE
                    cable_def["actuator_type"] = "muscle_hill"
                    # MuJoCo stores muscle params in gainprm and biasprm:
                    # gainprm[0] = range[0], gainprm[1] = range[1]
                    # gainprm[2] = max_force, gainprm[4] = lmin, gainprm[5] = lmax
                    # gainprm[7] = fpmax
                    if hasattr(model, 'actuator_gainprm') and act_i < len(model.actuator_gainprm):
                        gp = model.actuator_gainprm[act_i]
                        if len(gp) >= 3:
                            cable_def["muscle_force"] = float(gp[2])
                            cable_def["muscle_range"] = [float(gp[0]), float(gp[1])]
                        if len(gp) >= 6:
                            cable_def["muscle_lmin"] = float(gp[4])
                            cable_def["muscle_lmax"] = float(gp[5])
                        if len(gp) >= 8:
                            cable_def["muscle_fpmax"] = float(gp[7])
                    # Length range from actuator_lengthrange
                    if hasattr(model, 'actuator_lengthrange') and act_i < len(model.actuator_lengthrange):
                        lr = model.actuator_lengthrange[act_i]
                        cable_def["muscle_lengthrange"] = [float(lr[0]), float(lr[1])]

            cables.append(cable_def)

    return skeleton, cables
