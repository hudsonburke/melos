"""Adaptix-based import adapter for melos.core projects.

This module provides a lightweight Retort configuration that knows how to
convert common low-level melos types (Transform, Bounds, enums) from
JSON-like dictionaries into the canonical dataclass Project model.

The adapter is optional: importing or calling project_from_dict_adaptix will
raise an informative ImportError when `adaptix` is not installed.

ponytail: minimal POC. Add more field/path-level loaders as needed; keep core
dataclasses as the single source-of-truth.
"""

from __future__ import annotations

from typing import Any, Tuple

try:
    from adaptix import Retort, loader, validator, enum_by_name, P, Chain
except Exception:  # pragma: no cover - adaptix optional in CI
    Retort = None  # type: ignore

try:
    from pint import UnitRegistry
except Exception:  # pragma: no cover - pint optional
    UnitRegistry = None  # type: ignore

from melos.core.common.types import Bounds, Inertia6, Quat, Transform, Vec3
from melos.core.project.model import Project
from melos.core.system.enums import SystemRole

__all__ = ["build_retort", "project_from_dict_adaptix"]


def _ensure_adaptix_available() -> None:
    if Retort is None:
        raise ImportError(
            "adaptix is required for adaptix_adapter but is not installed. "
            "Install with `pip install adaptix` or use the existing JSON structurer."
        )


def _ensure_pint() -> "UnitRegistry | None":
    if UnitRegistry is None:
        return None
    return UnitRegistry()


def _parse_vec3(value: Any) -> Vec3:
    if isinstance(value, tuple) and len(value) == 3:
        return tuple(float(x) for x in value)
    if isinstance(value, list) and len(value) == 3:
        return tuple(float(x) for x in value)
    if isinstance(value, str):
        # accept comma or whitespace separated
        parts = [p for p in (value.replace(",", " ").split()) if p]
        if len(parts) != 3:
            raise TypeError("Vec3 string must contain three components")
        return tuple(float(x) for x in parts)
    raise TypeError("Expected Vec3 as list/tuple of 3 numbers or a string")


def _parse_quat(value: Any) -> Quat:
    if isinstance(value, tuple) and len(value) == 4:
        return tuple(float(x) for x in value)
    if isinstance(value, list) and len(value) == 4:
        return tuple(float(x) for x in value)
    if isinstance(value, str):
        parts = [p for p in (value.replace(",", " ").split()) if p]
        if len(parts) != 4:
            raise TypeError("Quat string must contain four components")
        return tuple(float(x) for x in parts)
    raise TypeError("Expected Quat as list/tuple of 4 numbers or a string")


def _parse_inertia6(value: Any) -> Inertia6:
    if isinstance(value, (list, tuple)) and len(value) == 6:
        return tuple(float(x) for x in value)
    raise TypeError("Expected Inertia6 as list/tuple of 6 numbers")


def _parse_bounds(value: Any) -> Bounds:
    if value is None:
        return Bounds()
    if isinstance(value, Bounds):
        return value
    if isinstance(value, dict):
        return Bounds(lower=value.get("lower"), upper=value.get("upper"))
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return Bounds(lower=value[0], upper=value[1])
    raise TypeError("Expected Bounds as dict with lower/upper or 2-tuple/list")


def _build_transform(value: Any) -> Transform:
    if isinstance(value, Transform):
        return value
    # Accept dict with 'translation' and optional 'rotation'
    if isinstance(value, dict):
        translation = value.get("translation", (0.0, 0.0, 0.0))
        rotation = value.get("rotation", (1.0, 0.0, 0.0, 0.0))
        return Transform(translation=_parse_vec3(translation), rotation=_parse_quat(rotation))

    # Accept flat list/tuple: [tx,ty,tz,qw,qx,qy,qz] or [tx,ty,tz]
    if isinstance(value, (list, tuple)):
        if len(value) == 3:
            return Transform(translation=_parse_vec3(value))
        if len(value) == 7:
            t = tuple(float(x) for x in value[:3])
            q = tuple(float(x) for x in value[3:7])
            return Transform(translation=t, rotation=q)
    raise TypeError("Unsupported Transform representation")


def _parse_length_to_meters(value: Any, *, ureg: "UnitRegistry | None") -> float:
    # If pint present, use it for robust unit parsing. Otherwise accept numeric only.
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        if ureg is not None:
            try:
                return float(ureg(value).to("meter").magnitude)
            except Exception as exc:  # pragma: no cover - pint runtime
                raise ValueError(f"Could not parse unitful length: {value!r}: {exc}")
        # fallback: try simple suffixes (cm, mm)
        s = value.strip()
        try:
            # plain number in string
            return float(s)
        except Exception:
            if s.endswith("cm"):
                return float(s[:-2]) / 100.0
            if s.endswith("mm"):
                return float(s[:-2]) / 1000.0
            if s.endswith("m"):
                return float(s[:-1])
            raise ValueError("Unit parsing requires pint; install pint or provide numeric values")

    raise TypeError("Expected numeric or unit string for length")


_retort_cache: "Retort | None" = None


def build_retort() -> "Retort":
    """Return a configured Retort for loading Project dataclasses.

    The function caches a single Retort instance.
    """

    _ensure_adaptix_available()
    global _retort_cache
    if _retort_cache is not None:
        return _retort_cache

    ureg = _ensure_pint()

    # small recipe: map low-level types and a few key simulation fields
    recipe = [
        loader(Transform, _build_transform),
        loader(Bounds, _parse_bounds),
        loader(Inertia6, _parse_inertia6),
        # parse a common simulation scalar field if present; path-based loading:
        loader(P[Project].simulation.time_step, lambda v: _parse_length_to_meters(v, ureg), Chain.FIRST),
        validator(P[Project].simulation.time_step, lambda x: x > 0.0, "simulation.time_step must be > 0"),
        enum_by_name(SystemRole),
    ]

    _retort_cache = Retort(recipe=recipe)
    return _retort_cache


def project_from_dict_adaptix(data: dict[str, Any]) -> Project:
    """Load a Project from a dict using adaptix-based conversion.

    Raises ImportError if adaptix is not available, or adaptix.load errors on invalid input.
    """

    _ensure_adaptix_available()
    ret = build_retort()
    return ret.load(data, Project)
