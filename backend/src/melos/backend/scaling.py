"""Scaling utilities for subject-specific model adaptation.

Takes any available subject data (segment lengths, 3D bone vectors, marker
distances, MHR bone parameters) and produces per-body scale factors applied
to the Arrow-based SkeletonState.

Three scaling modes:
  - ``by_segment_lengths`` — scalar segment lengths with a segment→link map
  - ``by_bone_vectors`` — 3D vectors for each bone (from MHR/SOMA skeleton fit)
  - ``by_marker_distances`` — OpenSim-style marker pair distances

All modes output a ``ScaleReport`` with per-link factors, the scaled
``SkeletonState``, and any warnings about unmapped segments.
"""

from __future__ import annotations

import copy
import logging
import math
from dataclasses import dataclass, field
from typing import Any

from melos.backend.models import (
    JointDef,
    LinkDef,
    LinkTransform,
    ModelState,
    SkeletonState,
)

logger = logging.getLogger(__name__)

# ── Data structures ───────────────────────────────────────────────────────


@dataclass
class ScaleReport:
    """Result of a scaling operation."""

    link_scale_factors: dict[str, float]
    scaled_skeleton: SkeletonState
    matched_segments: list[str]
    unmatched_segments: list[str]
    total_mass_before: float
    total_mass_after: float
    target_mass: float | None = None
    warnings: list[str] = field(default_factory=list)


# ── Helpers ───────────────────────────────────────────────────────────────


def _link_ids_in_order(skeleton: SkeletonState) -> list[str]:
    """Return link IDs in topological (parent-before-child) order."""
    if skeleton.order:
        return skeleton.order
    all_children = set(skeleton.parent_map.keys())
    return [n for n in skeleton.order if n not in all_children]


def compute_bone_positions(s: SkeletonState) -> dict[str, tuple[float, float, float]]:
    """Return world-space position of each link's origin (parent-relative → world).

    Iterates in parent-before-child order so parent positions are always
    available when computing children.
    """
    result: dict[str, tuple[float, float, float]] = {}
    order = s.order or list(s.parent_map.keys())
    for name in order:
        xf = s.transforms.get(name)
        px, py, pz = (xf.translation[0], xf.translation[1], xf.translation[2]) if xf else (0, 0, 0)
        parent = s.parent_map.get(name)
        if parent and parent in result:
            pp = result[parent]
            px += pp[0]
            py += pp[1]
            pz += pp[2]
        result[name] = (px, py, pz)
    return result


def _compute_child_map(skeleton: SkeletonState) -> dict[str, list[str]]:
    """Build parent → children list from parent_map."""
    children: dict[str, list[str]] = {}
    for child, parent in skeleton.parent_map.items():
        children.setdefault(parent, []).append(child)
    return children


def _compute_current_segment_lengths(
    skeleton: SkeletonState,
) -> dict[str, float]:
    """Compute the current length of each bone from transforms.

    For each link with a parent, the segment length is the Euclidean norm
    of its parent-relative translation vector.
    """
    lengths: dict[str, float] = {}
    for child, parent in skeleton.parent_map.items():
        xf = skeleton.transforms.get(child)
        if xf is None:
            continue
        t = xf.translation
        length = math.sqrt(t[0] ** 2 + t[1] ** 2 + t[2] ** 2)
        if length > 1e-12:
            lengths[child] = length
    return lengths


def _normalize_mass(
    skeleton: SkeletonState,
    target_mass: float,
) -> dict[str, float]:
    """Normalise per-link masses so total equals target_mass.

    Computes the current total mass, then scales each link's mass by
    ``target_mass / current_mass``.
    """
    current_total = 0.0
    for link in skeleton.links.values():
        current_total += link.mass
    if current_total < 1e-12:
        return {name: link.mass for name, link in skeleton.links.items()}

    ratio = target_mass / current_total
    return {name: link.mass * ratio for name, link in skeleton.links.items()}


def _apply_scale_factors(
    skeleton: SkeletonState,
    link_scale_factors: dict[str, float],
    target_mass: float | None = None,
) -> SkeletonState:
    """Return a new SkeletonState with scaled transforms and masses.

    Each link's translation vector is scaled by its per-link factor.
    If ``target_mass`` is given, masses are normalised to that total.
    Note: ``LinkTransform.rotation`` is preserved (unaffected by isotropic scaling).
    """
    new_transforms: dict[str, LinkTransform] = {}
    new_links: dict[str, LinkDef] = {}

    mass_map: dict[str, float] | None = None
    if target_mass is not None:
        mass_map = _normalize_mass(skeleton, target_mass)
        logger.info("Mass normalized: %.2f → %.2f kg",
                     sum(l.mass for l in skeleton.links.values()), target_mass)

    for name, link in skeleton.links.items():
        sf = link_scale_factors.get(name, 1.0)
        mass = mass_map[name] if mass_map is not None else link.mass

        new_links[name] = LinkDef(
            name=link.name,
            mass=mass,
            center_of_mass=[
                link.center_of_mass[0] * sf,
                link.center_of_mass[1] * sf,
                link.center_of_mass[2] * sf,
            ],
            inertia=[v * sf**5 for v in link.inertia],
            graphics_file=link.graphics_file,
            visible=link.visible,
        )

    for name, xf in skeleton.transforms.items():
        sf = link_scale_factors.get(name, 1.0)
        new_transforms[name] = LinkTransform(
            translation=(
                xf.translation[0] * sf,
                xf.translation[1] * sf,
                xf.translation[2] * sf,
            ),
            rotation=xf.rotation,
        )

    return SkeletonState(
        joints=skeleton.joints,
        links=new_links,
        transforms=new_transforms,
        parent_map=skeleton.parent_map,
        order=list(skeleton.order),
        descendants=dict(skeleton.descendants),
    )


# ── Scaling modes ─────────────────────────────────────────────────────────


def by_segment_lengths(
    skeleton: SkeletonState,
    target_lengths: dict[str, float],
    segment_to_link: dict[str, str | list[str]],
    *,
    source_lengths: dict[str, float] | None = None,
    target_mass: float | None = None,
) -> ScaleReport:
    """Scale skeleton so measured segment lengths match target values.

    If ``source_lengths`` is omitted, the current lengths are read from the
    skeleton's own transforms (parent-relative translation norms) for each
    link referenced in ``segment_to_link``.

    ``segment_to_link`` maps logical segment names (e.g. ``"thigh"``) to one
    or more link IDs whose translation encodes that segment.
    """
    # Build segment→link ID map
    segment_link_map: dict[str, list[str]] = {}
    for seg, ids in segment_to_link.items():
        segment_link_map[seg] = [ids] if isinstance(ids, str) else list(ids)

    # Auto-compute source lengths from transforms if not provided
    if source_lengths is None:
        raw_lengths = _compute_current_segment_lengths(skeleton)
        # Map segment names to source lengths via segment_to_link
        source_lengths = {}
        for seg, link_ids in segment_link_map.items():
            total_len = 0.0
            for lid in link_ids:
                total_len += raw_lengths.get(lid, 0.0)
            # For single-link segments, total_len is the link length
            # For multi-link segments (e.g., full leg), sum the lengths
            source_lengths[seg] = total_len

    # Compute per-segment scale factors
    link_factors: dict[str, float] = {}
    matched: list[str] = []
    unmatched: list[str] = []
    warnings: list[str] = []

    children_of = _compute_child_map(skeleton)

    for seg, link_ids in segment_link_map.items():
        if seg not in target_lengths:
            unmatched.append(seg)
            continue
        target_len = target_lengths[seg]
        source_len = source_lengths.get(seg, 0.0)
        if source_len < 1e-12:
            warnings.append(
                f"Segment '{seg}' has zero source length; skipping"
            )
            continue
        ratio = target_len / source_len
        for lid in link_ids:
            link_factors[lid] = ratio
            matched.append(f"{seg}→{lid} (×{ratio:.3f})")

    # Inherit parent scale for unmapped links (topological propagation)
    for name in skeleton.order:
        if name not in link_factors:
            parent = skeleton.parent_map.get(name)
            if parent and parent in link_factors:
                link_factors[name] = link_factors[parent]
            else:
                link_factors[name] = 1.0

    total_before = sum(l.mass for l in skeleton.links.values())
    scaled = _apply_scale_factors(skeleton, link_factors, target_mass)
    total_after = sum(l.mass for l in scaled.links.values())

    return ScaleReport(
        link_scale_factors=link_factors,
        scaled_skeleton=scaled,
        matched_segments=matched,
        unmatched_segments=unmatched,
        total_mass_before=total_before,
        total_mass_after=total_after,
        target_mass=target_mass,
        warnings=warnings,
    )


def by_bone_vectors(
    skeleton: SkeletonState,
    target_vectors: dict[str, tuple[float, float, float]],
    joint_to_link: dict[str, str],
    *,
    target_mass: float | None = None,
) -> ScaleReport:
    """Scale skeleton using 3D target bone vectors (from MHR/SOMA skeleton fit).

    Each entry in ``target_vectors`` corresponds to a joint name (e.g.
    ``"hip_r"``) and gives the parent-relative vector from the parent link
    to the child link in the subject's frame.
    ``joint_to_link`` maps joint names to child link IDs.

    The scale factor for a link is:
        |target_vector| / |current_link_translation|
    """
    link_factors: dict[str, float] = {}
    matched: list[str] = []
    unmatched: list[str] = []
    warnings: list[str] = []

    for joint_name, target_vec in target_vectors.items():
        link_id = joint_to_link.get(joint_name)
        if link_id is None:
            unmatched.append(joint_name)
            continue
        xf = skeleton.transforms.get(link_id)
        if xf is None:
            unmatched.append(f"{joint_name}→{link_id} (no transform)")
            continue
        target_len = math.sqrt(
            target_vec[0] ** 2 + target_vec[1] ** 2 + target_vec[2] ** 2
        )
        current_len = math.sqrt(
            xf.translation[0] ** 2
            + xf.translation[1] ** 2
            + xf.translation[2] ** 2
        )
        if current_len < 1e-12:
            warnings.append(
                f"Joint '{joint_name}' at link '{link_id}' has zero length; skipping"
            )
            continue
        ratio = target_len / current_len
        link_factors[link_id] = ratio
        matched.append(f"{joint_name}→{link_id} (×{ratio:.3f})")

    # Inherit parent scale for unmapped links
    for name in skeleton.order:
        if name not in link_factors:
            parent = skeleton.parent_map.get(name)
            if parent and parent in link_factors:
                link_factors[name] = link_factors[parent]
            else:
                link_factors[name] = 1.0

    total_before = sum(l.mass for l in skeleton.links.values())
    scaled = _apply_scale_factors(skeleton, link_factors, target_mass)
    total_after = sum(l.mass for l in scaled.links.values())

    return ScaleReport(
        link_scale_factors=link_factors,
        scaled_skeleton=scaled,
        matched_segments=matched,
        unmatched_segments=unmatched,
        total_mass_before=total_before,
        total_mass_after=total_after,
        target_mass=target_mass,
        warnings=warnings,
    )
