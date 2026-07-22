"""Bridge between resolved assembly specs and the Arrow-based SkeletonState.

Takes the resolved output of ``resolve_assembly()`` and applies it to a
``SkeletonState`` — adding exoskeleton part bodies, cable via-points,
actuator definitions, and tendon paths.

The modified skeleton can then be compiled to MJCF for MuJoCo simulation,
combining the original model with all exoskeleton components.
"""

from __future__ import annotations

import copy
import logging
import math
from typing import Any

from melos.backend.models import (
    JointDef,
    JointLimits,
    LinkDef,
    LinkTransform,
    SkeletonState,
)

logger = logging.getLogger(__name__)


def apply_assembly_to_skeleton(
    skeleton: SkeletonState,
    resolved: dict[str, Any],
    *,
    exo_parent: str = "ground",
    landmark_positions: dict[str, tuple[float, float, float]] | None = None,
) -> tuple[SkeletonState, list[dict[str, Any]]]:
    """Add exoskeleton parts from a resolved assembly spec to a skeleton.

    Returns ``(modified_skeleton, cable_definitions)`` where
    ``cable_definitions`` is a list of dicts ready for the MJCF compiler.

    Args:
        skeleton: The base skeleton to extend.
        resolved: Output from ``resolve_assembly()`` with ``parts`` list
            and optional ``cables`` list.
        exo_parent: Which body to parent all exoskeleton parts under.
        landmark_positions: World-space landmark positions, needed to
            resolve cable via-points that reference landmarks.

    Returns:
        Tuple of (modified SkeletonState, cable list for compiler).
    """
    # Deep copy so we don't mutate the original
    sk = copy.deepcopy(skeleton)

    order = list(sk.order)
    seen_ids: set[str] = set()

    for part in resolved.get("parts", []):
        part_id = part.get("id", f"exo_{len(order)}")
        if part_id in seen_ids:
            # Avoid duplicate IDs — append a suffix
            base_id = part_id
            suffix = 1
            while part_id in seen_ids:
                part_id = f"{base_id}_{suffix}"
                suffix += 1
        seen_ids.add(part_id)

        attachments = part.get("attachments", {})
        parameters = part.get("parameters", {})
        part_type = part.get("part_type", "Unknown")

        # Determine parent and local position from the first attachment
        parent_name = exo_parent
        local_pos = [0.0, 0.0, 0.0]

        # Try to find a sensible attachment to use as the parent
        for role, att in attachments.items():
            link = att.get("link", "")
            offset = att.get("offset", [0, 0, 0])
            if link and link in sk.links:
                parent_name = link
                local_pos = offset
                break
            elif link:
                # Link exists in the resolved data but not in the skeleton
                # (e.g., the landmark references a different model)
                # Use world position relative to ground
                local_pos = [att.get("x", 0), att.get("y", 0), att.get("z", 0)]
                break

        # Add the exo part as a body
        if part_id not in sk.transforms:
            sk.transforms[part_id] = LinkTransform(
                translation=(local_pos[0], local_pos[1], local_pos[2]),
                rotation=(1.0, 0.0, 0.0, 0.0),
            )

        if part_id not in sk.links:
            # Estimate mass from parameters or use default
            mass = 0.1
            for param_key in ("mass", "mass_kg", "weight_kg"):
                if param_key in parameters:
                    mass = float(parameters[param_key])
                    break
            sk.links[part_id] = LinkDef(
                name=part_id,
                mass=mass,
                center_of_mass=[0.0, 0.0, 0.0],
                inertia=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                graphics_file="",
            )

        # Set parent relationship
        if part_id not in sk.parent_map:
            sk.parent_map[part_id] = parent_name

        # Add a fixed joint for the exo part (attaches rigidly)
        joint_name = f"{part_id}_joint"
        if joint_name not in sk.joints:
            sk.joints[joint_name] = JointDef(
                joint_type="FixedJoint",
                axis=[0.0, 0.0, 1.0],
                limits=JointLimits(lower=-math.inf, upper=math.inf),
                parent_link=parent_name,
                child_link=part_id,
            )

        # Add to topological order
        if part_id not in order:
            # Insert after parent
            if parent_name in order:
                pidx = order.index(parent_name)
                order.insert(pidx + 1, part_id)
            else:
                order.append(part_id)

        # ── Resolve cable definitions ────────────────────────────────────
    cable_defs: list[dict[str, Any]] = []
    for cable in resolved.get("cables", []):
        via_points: list[dict[str, Any]] = []
        for step in cable.get("path", []):
            port_ref = step.get("port", "")
            landmark_name = step.get("landmark", "")

            if port_ref:
                # Format: "part_id/port_id"
                parts = port_ref.split("/", 1)
                part_id = parts[0]
                port_id = parts[1] if len(parts) > 1 else ""
                # Find the port on the resolved part and get its body name
                for rp in resolved.get("parts", []):
                    if rp["id"] == part_id:
                        # Get the part's body name (from applied skeleton)
                        body = part_id  # same as body id
                        for cp in rp.get("cable_ports", []):
                            if cp["id"] == port_id:
                                pos = cp["position"]
                                via_points.append({
                                    "body": body,
                                    "pos": tuple(pos),
                                    "type": cp.get("type", "via"),
                                })
                                break
                        break

            elif landmark_name and landmark_positions:
                # Via at a landmark — attach to the landmark's link
                lpos = landmark_positions.get(landmark_name)
                if lpos:
                    # Find which link this landmark is on
                    from melos.backend.marker_sets import builtin_marker_sets_dir, load_marker_set
                    ms_path = builtin_marker_sets_dir() / "gait_full_body.yaml"
                    link_name = "ground"
                    offset = [0, 0, 0]
                    if ms_path.exists():
                        ms = load_marker_set(ms_path)
                        lm_entry = ms.get("landmarks", {}).get(landmark_name, {})
                        melos_info = lm_entry.get("melos", {})
                        link_name = melos_info.get("link", "ground")
                        offset = melos_info.get("offset", [0, 0, 0])
                    via_points.append({
                        "body": link_name,
                        "pos": tuple(offset),
                        "type": "via",
                        "wrap_radius": step.get("wrap_radius", 0),
                    })

        if via_points:
            cable_def = {
                "id": cable.get("id", f"cable_{len(cable_defs)}"),
                "spring_length": cable.get("spring_length", 0.3),
                "diameter": cable.get("diameter", 0.002),
                "max_force": cable.get("max_force", 500.0),
                "via_points": via_points,
            }
            # Pass through actuator type
            atype = cable.get("actuator_type", "motor")
            cable_def["actuator_type"] = atype
            if atype == "muscle_hill":
                for k in ("force", "range", "lmin", "lmax", "fpmax", "lengthrange"):
                    v = cable.get(f"muscle_{k}")
                    if v is not None:
                        cable_def[f"muscle_{k}"] = v
            cable_defs.append(cable_def)

    # Recompute descendants
    children_of: dict[str, list[str]] = {}
    for c, p in sk.parent_map.items():
        children_of.setdefault(p, []).append(c)

    descendants: dict[str, list[str]] = {}
    for name in reversed(order):
        desc_set = {name}
        for child in children_of.get(name, []):
            desc_set.update(descendants.get(child, {child}))
        descendants[name] = sorted(desc_set)

    sk.order = order
    sk.descendants = descendants
    return sk, cable_defs


def resolve_and_apply(
    skeleton: SkeletonState,
    descriptor_path: str,
    landmark_positions: dict[str, tuple[float, float, float]],
    landmark_definitions: dict[str, dict[str, Any]],
    *,
    exo_parent: str = "ground",
    subject_overrides: dict[str, float] | None = None,
) -> SkeletonState:
    """Load an assembly descriptor, resolve it, and apply it to the skeleton.

    One-shot convenience combining ``load_assembly_descriptor``,
    ``resolve_assembly``, and ``apply_assembly_to_skeleton``.
    """
    from melos.backend.assembly import load_assembly_descriptor, resolve_assembly

    descriptor = load_assembly_descriptor(descriptor_path)
    resolved = resolve_assembly(
        descriptor,
        landmark_positions,
        landmark_definitions,
        subject_measurements=subject_overrides,
    )
    return apply_assembly_to_skeleton(skeleton, resolved, exo_parent=exo_parent)
