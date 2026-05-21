"""Compiler entry points for ``melos.sim.mujoco``."""

from .mjcf import compile_project, compile_project_file

__all__ = ["compile_project", "compile_project_file"]
