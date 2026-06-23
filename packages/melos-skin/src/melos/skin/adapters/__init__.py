"""Core-oriented adapter utilities for supported skin models."""

from .mhr_skin import build_example_mhr_skin_bundle
from .skin_bundle import (
    build_example_skin_joint_set,
    load_example_skin_reference_bundle,
    measure_example_skin_segments,
)

__all__ = [
    "build_example_mhr_skin_bundle",
    "build_example_skin_joint_set",
    "load_example_skin_reference_bundle",
    "measure_example_skin_segments",
]
from .skin_binding import collapse_joint_weights_to_binding_spec
