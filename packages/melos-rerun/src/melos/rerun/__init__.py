"""melos.rerun — Thin Rerun logging adapter for melos.core.model types.

Pydantic models in melos.core.model are the canonical data types.
This package provides a single adapter function to convert them into
Rerun log calls for analysis and visualization.
"""

from .adapter import log_skeleton, log_joint

__all__ = ["log_skeleton", "log_joint"]
