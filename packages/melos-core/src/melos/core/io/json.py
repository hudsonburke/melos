"""JSON serialization and deserialization for projects."""

from __future__ import annotations

import json
import typing
import types as py_types
from dataclasses import asdict, fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints

from .migrations import upgrade_project_dict
from melos.core.project.model import Project


def project_to_dict(project: Project) -> dict[str, Any]:
    """Convert a project into a JSON-friendly dictionary."""

    return asdict(project)


def project_to_json(project: Project, *, indent: int = 2) -> str:
    """Serialize a project to a JSON string."""

    return json.dumps(project_to_dict(project), indent=indent, sort_keys=True)


def save_project(project: Project, path: str | Path, *, indent: int = 2) -> None:
    """Write a project to disk as JSON."""

    Path(path).write_text(project_to_json(project, indent=indent), encoding="utf-8")


def project_from_dict(data: dict[str, Any]) -> Project:
    """Construct a ``Project`` from a nested dictionary."""

    upgraded = upgrade_project_dict(data)
    return _structure_dataclass(upgraded, Project)


def project_from_json(payload: str) -> Project:
    """Construct a project from a JSON string."""

    return project_from_dict(json.loads(payload))


def load_project(path: str | Path) -> Project:
    """Load a project from a JSON file on disk."""

    return project_from_json(Path(path).read_text(encoding="utf-8"))


def _structure_dataclass(data: dict[str, Any], cls: type[Any]) -> Any:
    type_hints = get_type_hints(cls)
    kwargs: dict[str, Any] = {}

    for field_info in fields(cls):
        if field_info.name not in data:
            continue

        annotation = type_hints.get(field_info.name, field_info.type)
        kwargs[field_info.name] = _structure_value(data[field_info.name], annotation)

    return cls(**kwargs)


def _structure_value(value: Any, annotation: Any) -> Any:
    if value is None:
        return None

    type_alias_type = getattr(typing, "TypeAliasType", None)
    if type_alias_type is not None and isinstance(annotation, type_alias_type):
        annotation = annotation.__value__

    origin = get_origin(annotation)
    args = get_args(annotation)

    if annotation is Any:
        return value

    if origin in (list, tuple, dict):
        return _structure_container(value, origin, args)

    if origin in (py_types.UnionType, getattr(__import__("typing"), "Union")):
        return _structure_union(value, args)

    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return annotation(value)

    if isinstance(annotation, type) and is_dataclass(annotation):
        return _structure_dataclass(value, annotation)

    return value


def _structure_container(value: Any, origin: Any, args: tuple[Any, ...]) -> Any:
    if origin is list:
        item_type = args[0] if args else Any
        return [_structure_value(item, item_type) for item in value]

    if origin is tuple:
        if not args:
            return tuple(value)

        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(_structure_value(item, args[0]) for item in value)

        if len(value) != len(args):
            raise ValueError(
                f"Expected tuple of length {len(args)}, received {len(value)}."
            )

        return tuple(
            _structure_value(item, item_type)
            for item, item_type in zip(value, args, strict=True)
        )

    if origin is dict:
        key_type = args[0] if args else Any
        value_type = args[1] if len(args) > 1 else Any
        return {
            _structure_value(key, key_type): _structure_value(item, value_type)
            for key, item in value.items()
        }

    return value


def _structure_union(value: Any, args: tuple[Any, ...]) -> Any:
    non_none_args = [arg for arg in args if arg is not type(None)]
    last_error: Exception | None = None

    for candidate in non_none_args:
        try:
            return _structure_value(value, candidate)
        except (TypeError, ValueError, KeyError) as exc:
            last_error = exc
            continue

    if last_error is not None:
        raise last_error

    return value
