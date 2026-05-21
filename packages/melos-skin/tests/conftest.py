from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
REPO_ROOT = ROOT.parents[1]
CORE_SRC = REPO_ROOT / "packages" / "melos-core" / "src"
BLENDER_SRC = REPO_ROOT / "packages" / "melos-blender" / "src"
MUJOCO_SRC = REPO_ROOT / "packages" / "melos-mujoco" / "src"
SKIN_SRC = REPO_ROOT / "packages" / "melos-skin" / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

if CORE_SRC.exists() and str(CORE_SRC) not in sys.path:
    sys.path.insert(0, str(CORE_SRC))

if BLENDER_SRC.exists() and str(BLENDER_SRC) not in sys.path:
    sys.path.insert(0, str(BLENDER_SRC))

if MUJOCO_SRC.exists() and str(MUJOCO_SRC) not in sys.path:
    sys.path.insert(0, str(MUJOCO_SRC))

if SKIN_SRC.exists() and str(SKIN_SRC) not in sys.path:
    sys.path.insert(0, str(SKIN_SRC))
