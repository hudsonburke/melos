"""MJCF mesh asset materializer and AssetLibrary builder for ``melos.sim.mujoco.importers``."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

from melos.core.assets.model import AssetLibrary, AssetRecord
from melos.core.common.enums import AssetRole

from .bodies import _build_quat_annotation, _commit_defaults_if_supported
from .xml_parser import CompilerDirectives
from .report import ImportReport


def map_assets(
    root: Any,
    directives: CompilerDirectives,
    source_path: Path,
    output_dir: Path | None,
    report: ImportReport,
) -> AssetLibrary:
    """Build an AssetLibrary from ``dm_control`` MJCF mesh assets."""
    library = AssetLibrary()
    collected_annotations = _collect_mesh_annotations(root)

    for mesh in getattr(getattr(root, "asset", None), "mesh", []):
        mesh_name = getattr(mesh, "name", None)
        if not mesh_name:
            continue

        annotations = dict(collected_annotations.get(str(mesh_name), {}))
        if getattr(mesh, "scale", None) is not None:
            annotations["mjcf_mesh_scale"] = _vec_to_string(mesh.scale)

        try:
            uri = _resolve_mesh_uri(mesh, directives, source_path, output_dir)
        except FileNotFoundError as exc:
            report.add_warning(
                code="MESH_NOT_FOUND",
                message=str(exc),
                location="asset/mesh",
            )
            continue

        library.items.append(
            AssetRecord(
                id=str(mesh_name),
                name=str(mesh_name),
                role=AssetRole.VISUAL,
                uri=uri,
                annotations=annotations,
            )
        )

    return library


def _collect_mesh_annotations(root: Any) -> dict[str, dict[str, str]]:
    annotations: dict[str, dict[str, str]] = {}
    for geom in root.find_all("geom"):
        _commit_defaults_if_supported(geom)
        if str(getattr(geom, "type", "")) != "mesh":
            continue
        mesh = getattr(geom, "mesh", None)
        mesh_name = getattr(mesh, "name", None)
        if mesh_name is None:
            continue
        mesh_name = str(mesh_name)
        if mesh_name in annotations:
            continue
        geom_annotations: dict[str, str] = {}
        pos_str = _attribute_string(geom, "pos")
        if pos_str is not None:
            geom_annotations["mjcf_geom_pos"] = pos_str
        quat_annotation = _build_quat_annotation(geom)
        if quat_annotation is not None:
            geom_annotations["mjcf_geom_quat"] = quat_annotation
        scale_str = _attribute_string(geom, "scale")
        if scale_str is not None:
            geom_annotations["mjcf_geom_scale"] = scale_str
        annotations[mesh_name] = geom_annotations
    return annotations


def _resolve_mesh_uri(
    mesh: Any,
    directives: CompilerDirectives,
    source_path: Path,
    output_dir: Path | None,
) -> str:
    source_candidate = _resolve_source_mesh_path(mesh, directives, source_path)
    filename = source_candidate.name

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        destination = output_dir / filename
        if source_candidate.exists():
            shutil.copy2(source_candidate, destination)
        else:
            _write_dm_asset_contents(mesh, destination)
        return str(destination)

    if source_candidate.exists():
        return str(source_candidate)

    cache_dir = Path(tempfile.gettempdir()) / "melos-sim-assets"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached_path = cache_dir / filename
    if not cached_path.exists():
        _write_dm_asset_contents(mesh, cached_path)
    return str(cached_path)


def _resolve_source_mesh_path(
    mesh: Any,
    directives: CompilerDirectives,
    source_path: Path,
) -> Path:
    source_dir = source_path.parent
    filename = _mesh_filename(mesh)
    if directives.meshdir:
        return (source_dir / directives.meshdir / filename).resolve()
    return (source_dir / filename).resolve()


def _mesh_filename(mesh: Any) -> str:
    file_asset = getattr(mesh, "file", None)
    prefix = getattr(file_asset, "prefix", None)
    extension = getattr(file_asset, "extension", None)
    if prefix and extension:
        return f"{prefix}{extension}"
    raw_file = _attribute_string(mesh, "file")
    if raw_file is not None:
        return Path(raw_file).name
    raise FileNotFoundError(f"Mesh '{getattr(mesh, 'name', '<unnamed>')}' has no file attribute")


def _write_dm_asset_contents(mesh: Any, destination: Path) -> None:
    file_asset = getattr(mesh, "file", None)
    contents = getattr(file_asset, "contents", None)
    if contents is None:
        raise FileNotFoundError(f"Mesh file not found: {_mesh_filename(mesh)}")
    destination.write_bytes(contents)


def _attribute_string(element: Any, attribute_name: str) -> str | None:
    getter = getattr(element, "get_attribute_xml_string", None)
    if callable(getter):
        try:
            return getter(attribute_name)
        except AttributeError:
            return None
    return None


def _vec_to_string(value: object) -> str:
    return " ".join(format(float(component), ".16g") for component in value)
