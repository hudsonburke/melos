"""MJCF parser wrapper for ``melos.sim.mujoco.importers`` using ``dm_control``."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element

from dm_control import mjcf

from melos.sim.mujoco.importers.defaults import apply_defaults, get_active_class, resolve_defaults
from melos.sim.mujoco.importers.report import ImportReport


_MERGEABLE_SECTION_TAGS = {
    "asset",
    "actuator",
    "contact",
    "default",
    "equality",
    "sensor",
    "tendon",
    "worldbody",
}


@dataclass(slots=True, kw_only=True)
class CompilerDirectives:
    meshdir: str | None = None
    texturedir: str | None = None
    angle: str = "radian"
    inertiafromgeom: str | None = None
    balanceinertia: bool = False
    boundmass: float | None = None
    boundinertia: float | None = None


MjcfRoot = Any


def parse_mjcf_file(
    path: str | Path,
    report: ImportReport | None = None,
) -> tuple[MjcfRoot, CompilerDirectives, ImportReport]:
    if report is None:
        report = ImportReport()

    path = Path(path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"MJCF file not found: {path}")

    xml_root = ET.parse(path).getroot()
    _resolve_includes(xml_root, path.parent, report, _visited=set())
    _materialize_defaults(xml_root)
    normalization_count = _normalize_default_muscle_blocks(xml_root)
    if normalization_count:
        report.add_warning(
            code="MJCF_NORMALIZED_DEFAULT_MUSCLE",
            message=(
                f"Normalized {normalization_count} nested <default><muscle .../></default> "
                "block(s) for dm_control compatibility"
            ),
            location=str(path),
        )

    xml_text = ET.tostring(xml_root, encoding="unicode")
    root = mjcf.from_xml_string(xml_text, model_dir=str(path.parent), assets=_preload_binary_assets(path))
    directives = _extract_compiler_directives(root)
    return root, directives, report


def _resolve_includes(
    root: Element,
    base_dir: Path,
    report: ImportReport,
    *,
    _visited: set[Path],
) -> None:
    i = 0
    while i < len(list(root)):
        child = list(root)[i]
        if child.tag != "include":
            _resolve_includes(child, base_dir, report, _visited=_visited)
            i += 1
            continue

        include_file = child.get("file")
        if not include_file:
            report.add_warning(
                code="INCLUDE_NO_FILE",
                message="<include> element has no file attribute",
                location=str(base_dir),
            )
            root.remove(child)
            continue

        include_path = (base_dir / include_file).resolve()
        if include_path in _visited:
            report.add_warning(
                code="INCLUDE_CIRCULAR",
                message=f"Circular include detected: {include_path}",
                location=str(base_dir / include_file),
            )
            root.remove(child)
            continue
        if not include_path.exists():
            report.add_warning(
                code="INCLUDE_MISSING",
                message=f"Include file not found: {include_path.name} (resolved from '{include_file}')",
                location=str(base_dir / include_file),
            )
            root.remove(child)
            continue

        _visited.add(include_path)
        included_root = ET.parse(include_path).getroot()
        include_base_dir = include_path.parent
        children_to_insert = list(included_root)
        for inc_child in children_to_insert:
            _resolve_includes(inc_child, include_base_dir, report, _visited=_visited)

        pos = list(root).index(child)
        root.remove(child)
        for j, new_child in enumerate(children_to_insert):
            if not _merge_child_into_root(root, new_child):
                root.insert(pos + j, new_child)
        _visited.discard(include_path)


def _merge_child_into_root(root: Element, new_child: Element) -> bool:
    if new_child.tag not in _MERGEABLE_SECTION_TAGS:
        return False
    existing = root.find(new_child.tag)
    if existing is None:
        return False
    for grandchild in list(new_child):
        existing.append(grandchild)
    return True


def _materialize_defaults(root: Element) -> None:
    defaults = resolve_defaults(root)
    if not defaults:
        return

    def _walk(element: Element, inherited_class: str | None) -> None:
        if element.tag == "default":
            return
        active_class = get_active_class(element, inherited_class)
        apply_defaults(element, active_class, defaults)
        next_inherited = inherited_class
        if element.tag == "body":
            next_inherited = element.get("childclass", active_class)
        for child in element:
            _walk(child, next_inherited)

    for child in root:
        _walk(child, None)


def _normalize_default_muscle_blocks(root: Element) -> int:
    replacements = 0
    for default_el in root.iter("default"):
        for child in list(default_el):
            if child.tag != "muscle":
                continue
            child.tag = "general"
            replacements += 1
    return replacements


def _extract_compiler_directives(root: MjcfRoot) -> CompilerDirectives:
    compiler = getattr(root, "compiler", None)
    if compiler is None:
        return CompilerDirectives()
    return CompilerDirectives(
        meshdir=_optional_str(getattr(compiler, "meshdir", None)),
        texturedir=_optional_str(getattr(compiler, "texturedir", None)),
        angle=_optional_str(getattr(compiler, "angle", None)) or "radian",
        inertiafromgeom=_optional_str(getattr(compiler, "inertiafromgeom", None)),
        balanceinertia=_bool_value(getattr(compiler, "balanceinertia", None)),
        boundmass=_optional_float(getattr(compiler, "boundmass", None)),
        boundinertia=_optional_float(getattr(compiler, "boundinertia", None)),
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    if text == "":
        return None
    return text


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def _bool_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"true", "1", "yes"}


def _preload_binary_assets(path: Path) -> dict[str, bytes]:
    assets: dict[str, bytes] = {}
    for root in _candidate_asset_roots(path):
        if not root.exists() or not root.is_dir():
            continue
        for file_path in root.rglob("*"):
            if not file_path.is_file() or file_path.suffix.lower() == ".xml":
                continue
            try:
                contents = file_path.read_bytes()
            except OSError:
                continue
            assets.setdefault(str(file_path.resolve()), contents)
            assets.setdefault(file_path.name, contents)
            relative_from_root = Path(os.path.relpath(file_path, root)).as_posix()
            assets.setdefault(relative_from_root, contents)
            relative_from_model = Path(os.path.relpath(file_path, path.parent)).as_posix()
            assets.setdefault(relative_from_model, contents)
    return assets


def _candidate_asset_roots(path: Path) -> list[Path]:
    roots: list[Path] = []
    current = path.parent.resolve()
    for _ in range(4):
        if current in roots:
            break
        roots.append(current)
        if current.parent == current:
            break
        current = current.parent
    return roots
