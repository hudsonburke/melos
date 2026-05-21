# melos-skin

`melos-skin` provides the `melos.skin` package: model-specific skin sources and rig/weight assets for the melos ecosystem.

Current first-party focus:
- MHR as the primary supported skinned human model

Responsibilities:
- load supported skin-source assets
- expose skin joints, mesh topology, and skinning weights
- provide model-specific helpers for binding a skin to a canonical `melos.core` system

Non-goals:
- canonical system semantics (owned by `melos.core`)
- MuJoCo import (owned by `melos.sim.mujoco`)
- Blender scene orchestration (owned by `melos.blender`)
