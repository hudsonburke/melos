"""MuJoCo compiler package for the melos ecosystem."""

from .compiler import compile_project, compile_project_file
from .importers import import_mjcf
from .reports import (
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
