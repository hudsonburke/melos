"""JSON serialization and deserialization for projects."""

from __future__ import annotations

import json
import types as py_types
from dataclasses import asdict, fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Union, get_args, get_origin, get_type_hints
from melos.core.io.schema import CURRENT_SCHEMA_VERSION

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

    version = str(data.get("schema_version") or CURRENT_SCHEMA_VERSION)

    if version != CURRENT_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported melos schema version {version!r}. "
            f"Supported version: {CURRENT_SCHEMA_VERSION}"
        )

    data["schema_version"] = CURRENT_SCHEMA_VERSION
    data.setdefault("systems", [])
    data.setdefault("assemblies", [])
    data.setdefault("skin_attachments", [])
    return _structure(data, Project)


def project_from_json(payload: str) -> Project:
    """Construct a project from a JSON string."""

    return project_from_dict(json.loads(payload))


def load_project(path: str | Path) -> Project:
    """Load a project from a JSON file on disk."""

    return project_from_json(Path(path).read_text(encoding="utf-8"))


def _structure(value: Any, annotation: Any) -> Any:
    """Recursively structure a JSON value into its annotated Python type."""

    if value is None:
        return None

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin in (py_types.UnionType, Union):
        non_none = [arg for arg in args if arg is not type(None)]
        if non_none:
            return _structure(value, non_none[0])
        return value

    if origin is list:
        item_type = args[0] if args else Any
        return [_structure(item, item_type) for item in value]

    if origin is tuple:
        if not args:
            return tuple(value)

        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(_structure(item, args[0]) for item in value)

        if len(value) != len(args):
            raise ValueError(
                f"Expected tuple of length {len(args)}, received {len(value)}."
            )

        return tuple(
            _structure(item, item_type)
            for item, item_type in zip(value, args, strict=True)
        )

    if origin is dict:
        value_type = args[1] if len(args) > 1 else Any
        return {
            key: _structure(item, value_type) for key, item in value.items()
        }

    if isinstance(annotation, type):
        if issubclass(annotation, Enum):
            return annotation(value)

        if is_dataclass(annotation):
            return _structure_dataclass(value, annotation)

    return value


def _structure_dataclass(data: dict[str, Any], cls: type[Any]) -> Any:
    type_hints = get_type_hints(cls)
    kwargs: dict[str, Any] = {}

    for field_info in fields(cls):
        if field_info.name not in data:
            continue

        annotation = type_hints.get(field_info.name, field_info.type)
        kwargs[field_info.name] = _structure(data[field_info.name], annotation)

    return cls(**kwargs)
