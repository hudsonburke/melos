"""Simulation backends for the melos ecosystem.

The current default backend is MuJoCo, re-exported here for convenience,
while backend-specific modules live under ``melos.sim.<backend>``.
"""

from .mujoco import compile_project, compile_project_file, import_mjcf
from .mujoco import (
    AssetBinding,
    CompileReport,
    CompileWarning,
    MujocoCompileResult,
    SignalBinding,
    SignalMap,
)

__version__ = "0.1.0"

__all__ = [
    "AssetBinding",
    "CompileReport",
    "CompileWarning",
    "MujocoCompileResult",
    "SignalBinding",
    "SignalMap",
    "compile_project",
    "compile_project_file",
    "import_mjcf",
]
