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
) -> SkeletonState:
    """Add exoskeleton parts from a resolved assembly spec to a skeleton.

    Args:
        skeleton: The base skeleton to extend.
        resolved: Output from ``resolve_assembly()`` with ``parts`` list.
        exo_parent: Which body to parent all exoskeleton parts under.
            Defaults to "ground" so exo parts are at the top level.

    Returns:
        A new ``SkeletonState`` with exoskeleton bodies, joints, and
        cable metadata added.  The original skeleton is not modified.
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

        # Process cable ports as via-point sites (metadata for the compiler)
        cable_ports = part.get("cable_ports", [])
        if cable_ports:
            # Store port info as landmarks-like metadata on the part body
            port_info = []
            for port in cable_ports:
                port_pos = port.get("position", [0, 0, 0])
                port_info.append({
                    "id": port.get("id", ""),
                    "type": port.get("type", "via"),
                    "position": port_pos,
                })
            # Store as a simple string-encoded metadata on the link
            # (the compiler will read this to generate MuJoCo sites/tendons)
            port_str = ";".join(
                f"{p['id']}|{p['type']}|{p['position'][0]},{p['position'][1]},{p['position'][2]}"
                for p in port_info
            )
            if port_str:
                sk.links[part_id].graphics_file = port_str

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
    return sk


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
