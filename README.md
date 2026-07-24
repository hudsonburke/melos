# melos — Subject-specific musculoskeletal modeling, exoskeleton design, and simulation

## Overview

melos is a framework for subject-specific musculoskeletal modeling, assistive device design, and physics simulation. It provides a unified data model for describing biological subjects (bones, joints, muscles), wearable devices (exoskeletons, prosthetics), and the assembly between them.

## Architecture

The canonical data model is defined by Pydantic models in **`melos.core.model`**.
All backend modules, the API, the frontend TypeScript types, and the MJCF
compiler/parser derive from this single schema.

### Single source of truth: `melos.core.model`

```
melos.core.model (Pydantic) ──→ JSON API ──→ TypeScript frontend
      │
      ├──→ MJCF parser (MuJoCo → Pydantic)
      ├──→ MJCF compiler (Pydantic → MuJoCo XML)
      ├──→ Rerun adapter (Pydantic → Arrow → Rerun for analysis)
      └──→ Proteus build spec (Pydantic → JSON → CAD parts)
```

### Namespace packages

*   **`melos.core`** — Pydantic models, scaling, landmarks, assembly descriptors
*   **`melos.rerun`** — Thin logging adapter (Pydantic → Rerun for visualization)
*   **`melos.skin`** — SOMA/MHR skin pipeline (optional ML dependencies)
*   **`melos.blender`** — Blender addon for visual authoring
*   **`melos.sim`** — MuJoCo MJCF compilation

## Data Flow

```text
Subject Data                Melos Editor               Simulation
(OpenSim/MJCF/MoCap)        (Python Backend)           (MuJoCo)
─────────────────           ───────────────            ─────────
                            ┌──────────────┐
OpenSim ──→ parse_mjcf ──→ │ SkeletonState│──→ compile_skeleton ──→ MJCF XML
MJCF ─────→ parse_mjcf ──→ │   (Pydantic) │                       │
                            │              │                       │
Mocap ────→ scale_by_  ──→ │              │                       ▼
            landmarks       │              │              MuJoCo simulation
                            └──────────────┘
                                 │   │
                                 ▼   ▼
                            REST API  Frontend
                            (JSON)    (R3F 3D editor)
```

## Key Design Principles

*   **Single source of truth**: `melos.core.model` defines all types. Backend, compiler, parser, and frontend all derive from it.
*   **Pydantic first**: JSON serialization, validation, and schema generation for free. `ModelState.model_json_schema()` produces the contract.
*   **Thin layers**: melos is an authoring and translation tool, not a simulator. It delegates physics to MuJoCo.
*   **Explicit SI units**: All values (meters, kilograms, seconds, radians) in SI. Scaling produces a new model; serialization stays in canonical SI units.
*   **YAML for configuration**: Marker sets, assembly descriptors, and cable routing are defined in human-readable YAML files.
*   **JSON as contract**: The Pydantic JSON API is what Proteus, the frontend, and any other consumer reads.

## Quick Start

### Installation

```bash
uv sync --all-packages
```

### Running Tests

```bash
cd backend && uv run python tests/test_mjcf_roundtrip.py
cd backend && uv run python tests/test_scaling.py
cd frontend && npm run build
```

### Running the Editor

```bash
# Terminal 1: Backend
cd backend && uvicorn melos.backend.app:app --port 8008

# Terminal 2: Frontend
cd frontend && npm run dev
# Open http://localhost:5173
```

## Project Structure

```text
melos/
├── packages/
│   ├── melos-core/
│   │   └── src/melos/core/
│   │       ├── model.py         ← THE SCHEMA (Pydantic, single source of truth)
│   │       ├── scaling/         ← Subject-specific scaling
│   │       └── io/              ← JSON serialization
│   ├── melos-rerun/
│   │   └── src/melos/rerun/
│   │       └── adapter.py       ← Thin Pydantic→Rerun logging adapter
│   └── melos-sim/               ← MuJoCo MJCF compilation
├── backend/
│   └── src/melos/backend/
│       ├── app.py               ← FastAPI (imports from melos.core.model)
│       ├── mjcf_parser.py       ← MuJoCo → SkeletonState
│       ├── mjcf_compiler.py     ← SkeletonState → MJCF XML
│       ├── landmarks.py         ← 57 anatomical landmarks
│       ├── marker_sets/         ← YAML marker set definitions
│       ├── scaling.py           ← Segment-length and landmark scaling
│       ├── assembly.py          ← Exoskeleton assembly descriptors
│       ├── assembly_bridge.py   ← Assembly → SkeletonState + cables
│       └── models.py            ← Re-exports from melos.core.model
├── frontend/
│   └── src/
│       ├── App.tsx              ← Main React app
│       ├── components/
│       │   ├── Scene.tsx        ← R3F 3D viewport
│       │   ├── ControlPanel.tsx ← Pipeline controls sidebar
│       │   └── SkinnedBody.tsx  ← SOMA mesh overlay
│       └── types/
│           └── schema.ts        ← TypeScript types (matches melos.core.model)
├── TESTING.md                   ← Step-by-step test guide
└── pyproject.toml
```

## The Pydantic Schema

All types live in `melos.core.model`. Key types:

| Type | Purpose |
|---|---|
| `ModelState` | Top-level: name + SkeletonState |
| `SkeletonState` | Full skeleton: joints, links, transforms, hierarchy |
| `JointDef` | Single joint: type, axis, limits, parent/child links |
| `LinkDef` | Single body: mass, inertia, mesh file, visibility |
| `LinkTransform` | Parent-relative position + rotation (w,x,y,z) |
| `CableDef` | Tendon/cable with via-points and muscle parameters |
| `CableViaPoint` | Single via-point on a body (cable routing) |
| `LandmarkDef` | Anatomical landmark (link + offset) |
| `ExoPartDef` | Exoskeleton part (cuff, brace, motor mount) |
| `ExoAssemblyDef` | Complete exoskeleton assembly with parts + cables |

Export the JSON schema anytime:
```python
from melos.core.model import ModelState
import json
print(json.dumps(ModelState.model_json_schema(), indent=2))
```

## License

See LICENSE for more information.
