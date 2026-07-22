"""Arrow-native MJCF compiler — reads component types, outputs MuJoCo XML."""

from __future__ import annotations

import math
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

from melos.backend.models import SkeletonState


def compile_skeleton(
    skeleton: SkeletonState,
    model_name: str = "melos_model",
    *,
    timestep: float = 0.01,
    gravity: list[float] | None = None,
    meshdir: str | None = None,
) -> str:
    """Compile SkeletonState to MJCF XML string."""
    root = Element("mujoco", {"model": model_name})
    g = gravity or [0, 0, -9.81]

    compiler_attrs: dict[str, str] = {
        "angle": "radian",
        "balanceinertia": "true",
    }
    if meshdir:
        compiler_attrs["meshdir"] = meshdir
    SubElement(root, "compiler", compiler_attrs)
    SubElement(root, "option", {
        "timestep": str(timestep),
        "gravity": f"{g[0]} {g[1]} {g[2]}",
        "integrator": "RK4",
    })

    # Asset section — define meshes for MuJoCo to find (only if files exist)
    asset = SubElement(root, "asset")
    seen_meshes: set[str] = set()
    for name, link in skeleton.links.items():
        if link and link.graphics_file and meshdir:
            mesh_name = link.graphics_file.replace(".stl", "").replace(".vtp", "")
            if mesh_name not in seen_meshes:
                # Check mesh file exists before adding
                mesh_path = Path(meshdir) / link.graphics_file
                if not mesh_path.exists():
                    # Try with extensions
                    found = False
                    for ext in [".stl", ".STL", ".obj", ".vtp", ".ply"]:
                        if (mesh_path.parent / (mesh_path.name + ext)).exists():
                            found = True
                            mesh_path = mesh_path.parent / (mesh_path.name + ext)
                            break
                    if not found:
                        continue
                SubElement(asset, "mesh", {
                    "name": mesh_name,
                    "file": str(mesh_path),
                })
                seen_meshes.add(mesh_name)

    worldbody = SubElement(root, "worldbody")

    all_children = set(skeleton.parent_map.keys())
    roots = [n for n in skeleton.order if n not in all_children and n in skeleton.transforms]

    children_of: dict[str, list[str]] = {}
    for c, p in skeleton.parent_map.items():
        children_of.setdefault(p, []).append(c)

    SubElement(worldbody, "geom", {
        "name": "ground", "type": "plane",
        "size": "5 5 0.1", "rgba": "0.8 0.8 0.8 1",
        "conaffinity": "1", "condim": "3",
    })

    for root_name in roots:
        _build_body(worldbody, skeleton, root_name, children_of, meshdir)

    # Actuators (position control on every joint)
    actuator = SubElement(root, "actuator")
    for jname in skeleton.joints:
        SubElement(actuator, "position", {
            "name": f"{jname}_act", "joint": jname, "kp": "100",
        })

    return _pretty_xml(root)


def _build_body(
    parent: Element,
    skeleton: SkeletonState,
    name: str,
    children_of: dict[str, list[str]],
    meshdir: str | None = None,
) -> None:
    """Recursively build body/joint/geom elements."""
    xf = skeleton.transforms.get(name)
    link = skeleton.links.get(name)
    children = children_of.get(name, [])

    pos = xf.translation if xf else (0, 0, 0)
    quat = xf.rotation if xf else (1, 0, 0, 0)

    attrs: dict[str, str] = {"name": name, "pos": f"{pos[0]:.6f} {pos[1]:.6f} {pos[2]:.6f}"}
    if quat != (1, 0, 0, 0):
        attrs["quat"] = f"{quat[0]:.6f} {quat[1]:.6f} {quat[2]:.6f} {quat[3]:.6f}"

    body = SubElement(parent, "body", attrs)

    # Inertial
    if link and link.mass > 0:
        com = link.center_of_mass
        inertia = link.inertia
        SubElement(body, "inertial", {
            "pos": f"{com[0]:.6f} {com[1]:.6f} {com[2]:.6f}",
            "mass": f"{link.mass:.6f}",
            "fullinertia": f"{inertia[0]:.10f} {inertia[1]:.10f} {inertia[2]:.10f} "
                           f"{inertia[3]:.10f} {inertia[4]:.10f} {inertia[5]:.10f}",
        })

    # Joint
    for jname, jdef in skeleton.joints.items():
        if jdef.child_link == name:
            jtype = _mujoco_type(jdef.joint_type)
            ja: dict[str, str] = {"name": jname, "type": jtype}
            if jtype in ("hinge", "slide"):
                ax = jdef.axis
                ja["axis"] = f"{ax[0]:.6f} {ax[1]:.6f} {ax[2]:.6f}"
            lim = jdef.limits
            if math.isfinite(lim.lower) or math.isfinite(lim.upper):
                lower = lim.lower if math.isfinite(lim.lower) else -3.14
                upper = lim.upper if math.isfinite(lim.upper) else 3.14
                ja["range"] = f"{lower:.6f} {upper:.6f}"
            SubElement(body, "joint", ja)
            break

    # Mesh geometry — only if mesh file exists in meshdir
    mesh_geom = None
    if link and link.graphics_file and meshdir:
        mesh_path = Path(meshdir) / link.graphics_file
        # Try common extensions
        for ext in ["", ".stl", ".STL", ".obj", ".OBJ", ".vtp", ".ply"]:
            test_path = mesh_path.parent / (mesh_path.name + ext) if ext else mesh_path
            if test_path.exists():
                mesh_geom = SubElement(body, "geom", {
                    "type": "mesh",
                    "mesh": link.graphics_file.replace(".stl", "").replace(".vtp", ""),
                    "rgba": "0.8 0.8 0.8 1",
                })
                break

    # Children
    for child in children:
        _build_body(body, skeleton, child, children_of, meshdir)


def _mujoco_type(jt: str) -> str:
    return {"PinJoint": "hinge", "CustomJoint": "hinge", "RevoluteJoint": "hinge",
            "PrismaticJoint": "slide", "BallJoint": "ball", "FreeJoint": "free",
            "FixedJoint": "fixed"}.get(jt, "hinge")


def _pretty_xml(root: Element) -> str:
    raw = tostring(root, encoding="unicode")
    import xml.dom.minidom
    dom = xml.dom.minidom.parseString(raw.encode())
    return dom.toprettyxml(indent="  ")
