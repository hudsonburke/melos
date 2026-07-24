"""Arrow-native MJCF compiler with wrap surfaces and Hill-type muscles."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import Element, SubElement, tostring

from melos.core.model import SkeletonState


def compile_skeleton(
    skeleton: SkeletonState,
    model_name: str = "melos_model",
    *,
    timestep: float = 0.01,
    gravity: list[float] | None = None,
    meshdir: str | None = None,
    cables: list[dict[str, Any]] | None = None,
) -> str:
    """Compile SkeletonState to MJCF XML string.

    Args:
        skeleton: The skeleton to compile.
        cables: Cable/tendon definitions. Each entry::
            {"id": "cable_1",
             "actuator_type": "motor" | "muscle_hill",
             "muscle_force": 769.595,  # Hill-type only
             "muscle_range": [0.828, 1.588],
             "muscle_lmin": 0.421, "muscle_lmax": 1.903,
             "muscle_fpmax": 1.379,
             "muscle_lengthrange": [0.254, 0.356],
             "spring_length": 0.35, "diameter": 0.002, "max_force": 500.0,
             "via_points": [
                 {"body": "body_name", "pos": (x,y,z), "wrap_radius": 0.008},
                 ...
             ]}
    """
    root = Element("mujoco", {"model": model_name})
    g = gravity or [0, 0, -9.81]

    SubElement(root, "compiler", {
        "angle": "radian", "balanceinertia": "true",
        **({"meshdir": meshdir} if meshdir else {}),
    })
    SubElement(root, "option", {
        "timestep": str(timestep),
        "gravity": f"{g[0]} {g[1]} {g[2]}",
        "integrator": "RK4",
    })

    # ── Asset section ─────────────────────────────────────────────────
    asset = SubElement(root, "asset")
    seen_meshes: set[str] = set()
    for _, link in skeleton.links.items():
        gf = link.graphics_file
        if gf and meshdir and _mesh_name(gf) not in seen_meshes:
            p = Path(meshdir) / gf
            if not p.exists():
                for ext in (".stl", ".STL", ".obj", ".vtp", ".ply"):
                    c = p.parent / (p.name + ext)
                    if c.exists():
                        p = c
                        break
                else:
                    continue
            SubElement(asset, "mesh", {"name": _mesh_name(gf), "file": str(p)})
            seen_meshes.add(_mesh_name(gf))

    # ── Preprocess cable data ─────────────────────────────────────────
    site_id_counter = [0]

    def _site_name() -> str:
        site_id_counter[0] += 1
        return f"vp_{site_id_counter[0]}"

    def _wrap_name(cid: str, idx: int) -> str:
        return f"{cid}_wrap_{idx}"

    # Build mapping: body → list of (site_name, pos) and (geom_name, pos, radius)
    body_sites: dict[str, list[tuple[str, str, tuple[float, ...]]]] = {}
    body_wrap_geoms: dict[str, list[tuple[str, str, tuple[float, ...], float]]] = {}
    body_sidesites: dict[str, list[tuple[str, str, tuple[float, ...]]]] = {}
    tendon_entries: list[tuple[str, list[tuple[str, str, float]]]] = []
    # tendon_entries: [(cable_id, [(entry_type, name, wrap_radius), ...])]
    # entry_type: "site" | "wrap"

    if cables:
        for cable in cables:
            cid = cable["id"]
            entries: list[tuple[str, str, float]] = []
            for idx, vp in enumerate(cable.get("via_points", [])):
                body = vp.get("body", "ground")
                pos = vp.get("pos", (0, 0, 0))
                wr = float(vp.get("wrap_radius", 0))

                if wr > 0:
                    # Wrap surface — cylinder/sphere geom
                    gname = _wrap_name(cid, idx)
                    body_wrap_geoms.setdefault(body, []).append(
                        (gname, cid, tuple(pos), wr)
                    )
                    # Sidesite on the "back" of the wrap
                    sn = f"{gname}_side"
                    body_sites.setdefault(body, []).append((sn, cid, tuple(pos)))
                    entries.append(("wrap", gname, wr))
                else:
                    # Regular via-point site
                    sn = _site_name()
                    body_sites.setdefault(body, []).append((sn, cid, tuple(pos)))
                    entries.append(("site", sn, 0))

            tendon_entries.append((cid, entries))

    # ── World body ────────────────────────────────────────────────────
    worldbody = SubElement(root, "worldbody")

    all_children = set(skeleton.parent_map.keys())
    roots = [n for n in skeleton.order
             if n not in all_children and n in skeleton.transforms]
    children_of: dict[str, list[str]] = {}
    for c, p in skeleton.parent_map.items():
        children_of.setdefault(p, []).append(c)

    SubElement(worldbody, "geom", {
        "name": "ground", "type": "plane",
        "size": "5 5 0.1", "rgba": "0.8 0.8 0.8 1",
        "conaffinity": "1", "condim": "3",
    })

    for root_name in roots:
        _build_body(worldbody, skeleton, root_name, children_of, meshdir,
                    body_sites, body_wrap_geoms, body_sidesites)

    # ── Tendon section ────────────────────────────────────────────────
    if tendon_entries:
        tendon = SubElement(root, "tendon")
        for cable in (cables or []):
            cid = cable["id"]
            matched_entries = [e for e in tendon_entries if e[0] == cid]
            if not matched_entries:
                continue
            _, entries = matched_entries[0]
            spat_attrs: dict[str, str] = {"name": cid}
            sl = cable.get("spring_length")
            if sl is not None:
                spat_attrs["springlength"] = f"{sl:.6f}"
            d = cable.get("diameter")
            if d is not None:
                spat_attrs["width"] = f"{d:.6f}"
            spatial = SubElement(tendon, "spatial", spat_attrs)
            for etype, name, _ in entries:
                if etype == "site":
                    SubElement(spatial, "site", {"site": name})
                elif etype == "wrap":
                    SubElement(spatial, "geom", {
                        "geom": name, "sidesite": f"{name}_side",
                    })

    # ── Actuator section ──────────────────────────────────────────────
    non_fixed = [(jn, jd) for jn, jd in skeleton.joints.items()
                 if jd.joint_type != "FixedJoint"]
    has_cables = cables is not None
    if non_fixed or has_cables:
        act = SubElement(root, "actuator")
        for jname, _ in non_fixed:
            SubElement(act, "position", {
                "name": f"{jname}_act", "joint": jname, "kp": "100",
            })
        for cable in (cables or []):
            cid = cable["id"]
            atype = cable.get("actuator_type", "motor")
            if atype == "muscle_hill":
                m_attrs: dict[str, str] = {
                    "name": f"{cid}_act", "tendon": cid,
                    "force": f"{cable.get('muscle_force', 500):.3f}",
                }
                mr = cable.get("muscle_range")
                if mr:
                    m_attrs["range"] = f"{mr[0]:.6f} {mr[1]:.6f}"
                for k in ("lmin", "lmax", "fpmax"):
                    v = cable.get(f"muscle_{k}")
                    if v is not None:
                        m_attrs[k] = f"{v:.6f}"
                lr = cable.get("muscle_lengthrange")
                if lr:
                    m_attrs["lengthrange"] = f"{lr[0]:.6f} {lr[1]:.6f}"
                SubElement(act, "muscle", m_attrs)
            else:
                mf = cable.get("max_force", 100.0)
                SubElement(act, "motor", {
                    "name": f"{cid}_act", "tendon": cid, "gear": f"{mf:.1f}",
                })

    return _pretty_xml(root)


def _mesh_name(gf: str) -> str:
    for suf in (".stl", ".vtp", ".obj", ".ply", ".STL", ".OBJ"):
        gf = gf.replace(suf, "")
    return gf


def _build_body(
    parent: Element,
    skeleton: SkeletonState,
    name: str,
    children_of: dict[str, list[str]],
    meshdir: str | None = None,
    body_sites: dict[str, list[tuple[str, str, tuple[float, ...]]]] | None = None,
    body_wrap_geoms: dict[str, list[tuple[str, str, tuple[float, ...], float]]] | None = None,
    body_sidesites: dict[str, list[tuple[str, str, tuple[float, ...]]]] | None = None,
) -> None:
    xf = skeleton.transforms.get(name)
    link = skeleton.links.get(name)
    children = children_of.get(name, [])

    pos = xf.translation if xf else (0, 0, 0)
    quat = xf.rotation if xf else (1, 0, 0, 0)

    attrs: dict[str, str] = {
        "name": name,
        "pos": f"{pos[0]:.6f} {pos[1]:.6f} {pos[2]:.6f}",
    }
    if quat != (1, 0, 0, 0):
        attrs["quat"] = f"{quat[0]:.6f} {quat[1]:.6f} {quat[2]:.6f} {quat[3]:.6f}"

    body = SubElement(parent, "body", attrs)

    # Inertial
    if link and link.mass > 1e-8:
        com = link.center_of_mass
        inertia = list(link.inertia)
        for idx in range(3):
            if inertia[idx] < 1e-10:
                inertia[idx] = link.mass * 0.001
        SubElement(body, "inertial", {
            "pos": f"{com[0]:.6f} {com[1]:.6f} {com[2]:.6f}",
            "mass": f"{link.mass:.6f}",
            "fullinertia": f"{inertia[0]:.10f} {inertia[1]:.10f} {inertia[2]:.10f} "
                           f"{inertia[3]:.10f} {inertia[4]:.10f} {inertia[5]:.10f}",
        })

    # Joint
    for jname, jdef in skeleton.joints.items():
        if jdef.child_link == name:
            if jdef.joint_type == "FixedJoint":
                break
            jtype = _mujoco_type(jdef.joint_type)
            ja: dict[str, str] = {"name": jname, "type": jtype}
            if jtype in ("hinge", "slide"):
                ax = list(jdef.axis)
                if all(abs(v) < 1e-10 for v in ax):
                    ax = [0.0, 0.0, 1.0]
                ja["axis"] = f"{ax[0]:.6f} {ax[1]:.6f} {ax[2]:.6f}"
            lim = jdef.limits
            if math.isfinite(lim.lower) or math.isfinite(lim.upper):
                lower = lim.lower if math.isfinite(lim.lower) else -3.14
                upper = lim.upper if math.isfinite(lim.upper) else 3.14
                lower = max(lower, -10000.0)
                upper = min(upper, 10000.0)
                if lower < upper - 1e-10:
                    ja["range"] = f"{lower:.6f} {upper:.6f}"
            SubElement(body, "joint", ja)
            break

    # Cable via-point sites on this body
    if body_sites:
        for s_name, s_cid, s_pos in body_sites.get(name, []):
            SubElement(body, "site", {
                "name": s_name,
                "pos": f"{s_pos[0]:.6f} {s_pos[1]:.6f} {s_pos[2]:.6f}",
            })
        for s_name, s_cid, s_pos in body_sidesites.get(name, []):
            SubElement(body, "site", {
                "name": s_name,
                "pos": f"{s_pos[0]:.6f} {s_pos[1]:.6f} {s_pos[2]:.6f}",
            })

    # Wrap surface geometries (group="2" for MuJoCo wrap)
    if body_wrap_geoms:
        for g_name, g_cid, g_pos, g_radius in body_wrap_geoms.get(name, []):
            SubElement(body, "geom", {
                "name": g_name,
                "type": "cylinder",
                "size": f"{g_radius:.6f} {g_radius * 2:.6f}",
                "pos": f"{g_pos[0]:.6f} {g_pos[1]:.6f} {g_pos[2]:.6f}",
                "group": "2",
                "rgba": "0.5 0.5 0.9 0.4",
            })

    # Mesh geometry
    if link and link.graphics_file and meshdir and "." in link.graphics_file:
        mp = Path(meshdir) / link.graphics_file
        for ext in ("", ".stl", ".STL", ".obj", ".vtp", ".ply"):
            tp = mp.parent / (mp.name + ext) if ext else mp
            if tp.exists():
                SubElement(body, "geom", {
                    "type": "mesh",
                    "mesh": _mesh_name(link.graphics_file),
                    "rgba": "0.8 0.8 0.8 1",
                })
                break

    for child in children:
        _build_body(body, skeleton, child, children_of, meshdir,
                    body_sites, body_wrap_geoms, body_sidesites)


def _mujoco_type(jt: str) -> str:
    return {"PinJoint": "hinge", "CustomJoint": "hinge", "RevoluteJoint": "hinge",
            "PrismaticJoint": "slide", "BallJoint": "ball", "FreeJoint": "free",
            "FixedJoint": "fixed"}.get(jt, "hinge")


def _pretty_xml(root: Element) -> str:
    import xml.dom.minidom
    dom = xml.dom.minidom.parseString(tostring(root, encoding="unicode").encode())
    return dom.toprettyxml(indent="  ")
