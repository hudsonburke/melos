from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
REPO_ROOT = ROOT.parents[1]
SIM_SRC = REPO_ROOT / "packages" / "melos-sim" / "src"
BLENDER_SRC = REPO_ROOT / "packages" / "melos-blender" / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

if SIM_SRC.exists() and str(SIM_SRC) not in sys.path:
    sys.path.insert(0, str(SIM_SRC))

if BLENDER_SRC.exists() and str(BLENDER_SRC) not in sys.path:
    sys.path.insert(0, str(BLENDER_SRC))

FIXTURES_DIR = ROOT / "tests" / "fixtures"
MYOELBOW_DIR = FIXTURES_DIR / "myoelbow"
