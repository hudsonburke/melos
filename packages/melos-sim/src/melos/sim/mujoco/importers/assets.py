"""ElementTree MJCF mesh asset copier fallback."""

from __future__ import annotations

import shutil
from pathlib import Path
from xml.etree.ElementTree import Element

from melos.core.common.assets import AssetLibrary, AssetRecord
from melos.core.common.types import AssetRole

from .bodies import _build_quat_annotation
from .xml_parser import CompilerDirectives
from .report import ImportReport


def map_assets(
    root: Element,
    directives: CompilerDirectives,
    source_path: Path,
    output_dir: Path | None,
    report: ImportReport,
) -> AssetLibrary:
    library = AssetLibrary()
    asset_elem = root.find("asset")
    if asset_elem is None:
        return library

    source_dir = Path(source_path).parent
    collected_annotations = _collect_mesh_annotations(root)
    for mesh_elem in asset_elem.findall("mesh"):
        mesh_name = mesh_elem.get("name")
        mesh_file = mesh_elem.get("file")
        if not mesh_name or not mesh_file:
            continue

        annotations = dict(collected_annotations.get(mesh_name, {}))
        mesh_scale = mesh_elem.get("scale")
        if mesh_scale is not None:
            annotations["mjcf_mesh_scale"] = mesh_scale

        mesh_file_path = Path(mesh_file)
        if mesh_file_path.is_absolute():
            mesh_path = mesh_file_path
        elif directives.meshdir:
            mesh_path = source_dir / directives.meshdir / mesh_file
        else:
            mesh_path = source_dir / mesh_file

        uri = str(mesh_path)
        if output_dir:
            dest_path = output_dir / Path(mesh_file).name
            shutil.copy2(mesh_path, dest_path)
            uri = str(dest_path)

        record = AssetRecord(
            id=mesh_name,
            name=mesh_name,
            role=AssetRole.VISUAL,
            uri=uri,
            annotations=annotations,
        )
        library.items.append(record)

    return library


def _collect_mesh_annotations(root: Element) -> dict[str, dict[str, str]]:
    annotations: dict[str, dict[str, str]] = {}
    for geom_elem in root.findall('.//geom'):
        mesh_name = geom_elem.get('mesh')
        if mesh_name is None:
            continue
        if geom_elem.get('type') not in (None, 'mesh'):
            continue
        if mesh_name in annotations:
            continue
        geom_annotations: dict[str, str] = {}
        pos_str = geom_elem.get('pos')
        if pos_str is not None:
            geom_annotations['mjcf_geom_pos'] = pos_str
        quat_annotation = _build_quat_annotation(geom_elem)
        if quat_annotation is not None:
            geom_annotations['mjcf_geom_quat'] = quat_annotation
        scale_str = geom_elem.get('meshscale') or geom_elem.get('scale')
        if scale_str is not None:
            geom_annotations['mjcf_geom_scale'] = scale_str
        annotations[mesh_name] = geom_annotations
    return annotations
