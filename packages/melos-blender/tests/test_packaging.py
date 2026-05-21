from __future__ import annotations

import importlib.util
import subprocess
import sys
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "packages" / "melos-blender" / "scripts" / "build_blender_addon.py"


def test_build_blender_addon_creates_installable_zip(tmp_path) -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--output-dir", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )

    archive_path = Path(result.stdout.strip())
    assert archive_path.exists()

    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())

    assert "melos/__init__.py" in names
    assert "melos/blender/addon/__init__.py" in names
    assert "melos/core/__init__.py" in names
    assert "melos/sim/__init__.py" in names
    assert "melos/sim/mujoco/importers/__init__.py" in names
    assert "melos/resources/myofullbody/body/myofullbody.xml" in names
    assert "melos/resources/skin/SOMA_neutral.npz" in names
    assert "melos/resources/skin/MHR/mhr_model_lod1.pt" in names
    assert "melos/resources/skin/MHR/base_body_lod1.obj" in names
    assert "melos/resources/skin/MHR/SOMA_wrap_lod1.obj" in names
    assert "melos/skin/adapters/__init__.py" in names
    assert "melos/skin/adapters/mhr_skin.py" in names
    assert "melos/skin/adapters/skin_bundle.py" in names
    assert "melos/skin/mappings/__init__.py" in names
    assert "melos/skin/mappings/myofullbody_to_human_v1.py" in names


def test_packaged_addon_bootstrap_imports(tmp_path, monkeypatch) -> None:
    subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--output-dir", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    archive_path = next(tmp_path.glob("melos-addon-*.zip"))
    extract_dir = tmp_path / "extracted"

    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(extract_dir)

    bootstrap_path = extract_dir / "melos" / "__init__.py"
    monkeypatch.syspath_prepend(str(extract_dir))
    spec = importlib.util.spec_from_file_location("melos", bootstrap_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules.pop("melos", None)
    sys.modules.pop("melos.blender", None)
    sys.modules.pop("melos.core", None)
    sys.modules.pop("melos.skin", None)
    spec.loader.exec_module(module)

    assert module.bl_info["name"] == "melos"
    assert callable(module.register)
    assert callable(module.unregister)
