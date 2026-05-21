from __future__ import annotations

import argparse
import re
import shutil
import tempfile
import tomllib
import zipfile
from pathlib import Path


_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _read_version(repo_root: Path) -> str:
    pyproject_path = repo_root / "packages" / "melos-blender" / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def _read_supported_blender_version(repo_root: Path) -> tuple[int, int, int]:
    constants_path = repo_root / "packages" / "melos-blender" / "src" / "melos" / "blender" / "constants.py"
    match = re.search(
        r"BLENDER_SUPPORTED_MAJOR_MINOR\s*=\s*\((\d+),\s*(\d+)\)",
        constants_path.read_text(encoding="utf-8"),
    )
    if match is None:
        raise ValueError("Could not determine supported Blender version.")
    return int(match.group(1)), int(match.group(2)), 0


def _write_addon_entrypoint(addon_root: Path, version: str, blender_version: tuple[int, int, int]) -> None:
    entrypoint = addon_root / "__init__.py"
    entrypoint.write_text(
        "from __future__ import annotations\n"
        "\n"
        f"bl_info = {{\n"
        f"    \"name\": \"melos\",\n"
        f"    \"author\": \"OpenCode\",\n"
        f"    \"description\": \"Author canonical melos core models inside Blender.\",\n"
        f"    \"blender\": {blender_version!r},\n"
        f"    \"version\": {tuple(int(part) for part in version.split('.'))!r},\n"
        f"    \"location\": \"View3D > Sidebar > melos\",\n"
        f"    \"category\": \"Animation\",\n"
        f"}}\n"
        "\n"
        "def register() -> None:\n"
        "    from .blender.addon.register import register as _register\n"
        "\n"
        "    _register()\n"
        "\n"
        "def unregister() -> None:\n"
        "    from .blender.addon.register import unregister as _unregister\n"
        "\n"
        "    _unregister()\n"
        "\n"
        "__all__ = [\"bl_info\", \"register\", \"unregister\"]\n",
        encoding="utf-8",
    )


def _copy_tree(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, dirs_exist_ok=True, ignore=_IGNORE)


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)



def _stage_minimal_skin_subset(addon_root: Path, repo_root: Path) -> None:
    skin_root = repo_root / "packages" / "melos-skin" / "src" / "melos" / "skin"

    _copy_file(skin_root / "__init__.py", addon_root / "skin" / "__init__.py")
    _copy_tree(skin_root / "adapters", addon_root / "skin" / "adapters")

    _copy_file(skin_root / "mappings" / "__init__.py", addon_root / "skin" / "mappings" / "__init__.py")
    _copy_file(
        skin_root / "mappings" / "myofullbody_to_human_v1.py",
        addon_root / "skin" / "mappings" / "myofullbody_to_human_v1.py",
    )



def _stage_bundle(stage_root: Path, repo_root: Path) -> Path:
    addon_root = stage_root / "melos"
    addon_root.mkdir(parents=True, exist_ok=True)
    _write_addon_entrypoint(
        addon_root,
        _read_version(repo_root),
        _read_supported_blender_version(repo_root),
    )

    _copy_tree(
        repo_root / "packages" / "melos-core" / "src" / "melos" / "core",
        addon_root / "core",
    )
    _copy_tree(
        repo_root / "packages" / "melos-blender" / "src" / "melos" / "blender",
        addon_root / "blender",
    )
    _copy_file(
        repo_root / "packages" / "melos-sim" / "src" / "melos" / "sim" / "__init__.py",
        addon_root / "sim" / "__init__.py",
    )
    _copy_tree(
        repo_root / "packages" / "melos-sim" / "src" / "melos" / "sim" / "mujoco",
        addon_root / "sim" / "mujoco",
    )
    _copy_tree(
        repo_root / "resources" / "third_party" / "myofullbody",
        addon_root / "resources" / "myofullbody",
    )
    _copy_file(
        repo_root / "resources" / "third_party" / "skin" / "SOMA_neutral.npz",
        addon_root / "resources" / "skin" / "SOMA_neutral.npz",
    )
    _copy_file(
        repo_root / "resources" / "third_party" / "skin" / "LICENSE",
        addon_root / "resources" / "skin" / "LICENSE",
    )
    _copy_file(
        repo_root / "resources" / "third_party" / "skin" / "ATTRIBUTIONS.MD",
        addon_root / "resources" / "skin" / "ATTRIBUTIONS.MD",
    )
    _copy_file(
        repo_root / "resources" / "third_party" / "skin" / "MHR" / "mhr_model_lod1.pt",
        addon_root / "resources" / "skin" / "MHR" / "mhr_model_lod1.pt",
    )
    _copy_file(
        repo_root / "resources" / "third_party" / "skin" / "MHR" / "base_body_lod1.obj",
        addon_root / "resources" / "skin" / "MHR" / "base_body_lod1.obj",
    )
    _copy_file(
        repo_root / "resources" / "third_party" / "skin" / "MHR" / "SOMA_wrap_lod1.obj",
        addon_root / "resources" / "skin" / "MHR" / "SOMA_wrap_lod1.obj",
    )
    _stage_minimal_skin_subset(addon_root, repo_root)
    return addon_root


def build_blender_addon(output_dir: Path | None = None) -> Path:
    repo_root = _repo_root()
    version = _read_version(repo_root)
    destination_dir = output_dir or (repo_root / "dist")
    destination_dir.mkdir(parents=True, exist_ok=True)
    archive_path = destination_dir / f"melos-addon-{version}.zip"

    with tempfile.TemporaryDirectory() as temporary_dir:
        stage_root = Path(temporary_dir)
        addon_root = _stage_bundle(stage_root, repo_root)
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(addon_root.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(stage_root))

    return archive_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    archive_path = build_blender_addon(args.output_dir)
    print(archive_path)


if __name__ == "__main__":
    main()
