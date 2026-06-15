"""ElementTree MJCF parser with include resolution for fallback import."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from xml.etree.ElementTree import Element

from melos.sim.mujoco.importers.report import ImportReport


from .quat_utils import _MERGEABLE_SECTION_TAGS


@dataclass(slots=True, kw_only=True)
class CompilerDirectives:
    meshdir: str | None = None
    texturedir: str | None = None
    angle: str = "radian"
    inertiafromgeom: str | None = None
    balanceinertia: bool = False
    boundmass: float | None = None
    boundinertia: float | None = None


def parse_mjcf_file(
    path: str | Path,
    report: ImportReport | None = None,
) -> tuple[Element, CompilerDirectives, ImportReport]:
    if report is None:
        report = ImportReport()

    path = Path(path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"MJCF file not found: {path}")

    root = ET.parse(path).getroot()
    base_dir = path.parent

    _resolve_includes(root, base_dir, report, _visited=set())
    directives = _merge_compiler_directives(root)

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


def _merge_compiler_directives(root: Element) -> CompilerDirectives:
    directives = CompilerDirectives()

    for compiler in root.iter("compiler"):
        if compiler.get("meshdir") is not None:
            directives.meshdir = compiler.get("meshdir")
        if compiler.get("texturedir") is not None:
            directives.texturedir = compiler.get("texturedir")
        if compiler.get("angle") is not None:
            directives.angle = compiler.get("angle")  # type: ignore[assignment]
        if compiler.get("inertiafromgeom") is not None:
            directives.inertiafromgeom = compiler.get("inertiafromgeom")
        if compiler.get("balanceinertia") is not None:
            val = compiler.get("balanceinertia", "").lower()
            directives.balanceinertia = val in ("true", "1", "yes")
        if compiler.get("boundmass") is not None:
            directives.boundmass = float(compiler.get("boundmass"))  # type: ignore[arg-type]
        if compiler.get("boundinertia") is not None:
            directives.boundinertia = float(compiler.get("boundinertia"))  # type: ignore[arg-type]

    return directives
