"""Optimize MuJoCo joint angles to match target bone positions.

Given target positions for a subset of links (e.g. from SOMA-X PoseInversion
or similarity-transformed MHR joints), finds coordinate values that minimize
the squared distance between FK bone positions and targets.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from melos.core.kinematics.pose import evaluate_system_world_transforms
from melos.core.system.model import SystemModel


def optimize_joint_angles_to_targets(
    system: SystemModel,
    target_positions: dict[str, tuple[float, float, float]],
    *,
    initial_coordinate_values: dict[str, float] | None = None,
    link_weights: dict[str, float] | None = None,
    max_iterations: int = 200,
    tolerance: float = 1e-6,
) -> dict[str, float]:
    """Find coordinate values that place FK bone positions near *target_positions*.

    Parameters
    ----------
    system :
        The anatomical system model.
    target_positions :
        {link_id: (x, y, z)} desired world positions in metres.
    initial_coordinate_values :
        Starting guess.  Missing keys default to 0.0.
    link_weights :
        Per-link importance weight (default 1.0 for all targeted links).
    max_iterations :
        L-BFGS-B iteration limit.
    tolerance :
        Optimizer convergence tolerance.

    Returns
    -------
    dict
        Optimized ``{coordinate_id: value}`` mapping.
    """
    from scipy.optimize import minimize as scipy_minimize

    if not target_positions:
        return dict(initial_coordinate_values or {})

    # Collect optimizable coordinates (exclude FIXED joints)
    coord_ids: list[str] = []
    coord_axes: list[tuple[float, float, float]] = []
    coord_limits: list[tuple[float | None, float | None]] = []

    for joint in system.joints:
        if joint.child_link_id is None:
            continue
        for coord in getattr(joint, "coordinates", []) or []:
            coord_ids.append(coord.id)
            coord_axes.append(tuple(coord.axis) if coord.axis else (1.0, 0.0, 0.0))
            limit = getattr(coord, "limit", None)
            if limit and len(limit) == 2:
                coord_limits.append((float(limit[0]), float(limit[1])))
            else:
                coord_limits.append((None, None))

    if not coord_ids:
        return {}

    n_coords = len(coord_ids)

    # Build initial guess vector
    x0 = np.zeros(n_coords, dtype=np.float64)
    if initial_coordinate_values:
        for i, cid in enumerate(coord_ids):
            if cid in initial_coordinate_values:
                x0[i] = initial_coordinate_values[cid]

    # Build bounds from joint limits
    bounds = []
    for lo, hi in coord_limits:
        bounds.append((lo, hi))

    # Precompute weight vector
    weights = np.ones(len(target_positions), dtype=np.float64)
    target_link_ids = list(target_positions.keys())
    if link_weights:
        for i, lid in enumerate(target_link_ids):
            if lid in link_weights:
                weights[i] = link_weights[lid]

    target_vec = np.array(
        [target_positions[lid] for lid in target_link_ids], dtype=np.float64
    )  # (N, 3)

    def _objective(x: np.ndarray) -> float:
        coord_values = {coord_ids[i]: float(x[i]) for i in range(n_coords)}
        wt = evaluate_system_world_transforms(system, coord_values)

        total = 0.0
        for i, lid in enumerate(target_link_ids):
            t = wt.get(lid)
            if t is None:
                continue
            pos = np.array(t.translation, dtype=np.float64)
            diff = pos - target_vec[i]
            total += float(weights[i] * (diff[0] ** 2 + diff[1] ** 2 + diff[2] ** 2))
        return total

    def _gradient(x: np.ndarray) -> np.ndarray:
        """Numerical gradient via central differences."""
        grad = np.zeros(n_coords, dtype=np.float64)
        eps = 1e-5
        f0 = _objective(x)
        for i in range(n_coords):
            x_plus = x.copy()
            x_plus[i] += eps
            x_minus = x.copy()
            x_minus[i] -= eps
            grad[i] = (_objective(x_plus) - _objective(x_minus)) / (2.0 * eps)
        return grad

    result = scipy_minimize(
        _objective,
        x0,
        method="L-BFGS-B",
        jac=_gradient,
        bounds=bounds,
        options={"maxiter": max_iterations, "ftol": tolerance, "gtol": tolerance * 10},
    )

    optimized = {coord_ids[i]: float(result.x[i]) for i in range(n_coords)}
    return optimized


def compute_target_positions_from_anchors(
    reference_body_anchors: dict[str, tuple[float, float, float]],
    world_transforms: dict[str, Any],
) -> dict[str, tuple[float, float, float]]:
    """Build target positions from reference body anchors.

    Uses anchors where available, falls back to raw FK positions.
    """
    targets: dict[str, tuple[float, float, float]] = {}
    for link_id, anchor in reference_body_anchors.items():
        targets[link_id] = anchor
    # Add any links in world_transforms that don't have anchors
    # (they'll be at their rest pose, which is the default)
    return targets
