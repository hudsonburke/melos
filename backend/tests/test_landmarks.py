"""Export landmark registry to YAML and test world-space positions."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from melos.backend.landmarks import LANDMARK_REGISTRY, landmark_world_positions, write_landmark_registry
from melos.backend.app import load_model_from_osim

# Export to YAML
yaml_path = Path(__file__).resolve().parent / "rajagopal_landmarks.yaml"
write_landmark_registry(yaml_path)
print(f"Wrote {len(LANDMARK_REGISTRY['landmarks'])} landmarks to {yaml_path}")

# Load model and compute landmark world positions
m = load_model_from_osim("/var/lib/hermes/rerun-importer-osim/test_data/RajagopalData/Rajagopal2015.osim")

world_pos = landmark_world_positions(m.skeleton)
print(f"\nComputed world positions for {len(world_pos)} landmarks:\n")

# Print some key landmarks
key_landmarks = ["RASI", "LASI", "RPSI", "LPSI", "Sacral",
                 "RACR", "LACR", "C7",
                 "RSJC", "RLElbow", "RStyloid",
                 "RLEpicondyle", "RMalleolusLat", "RHeel", "RToe",
                 "LLEpicondyle", "LMalleolusLat", "LHeel", "LToe"]

print(f"{'Name':<20} {'X':>8} {'Y':>8} {'Z':>8} {'Link'}")
print("-" * 60)
for name in key_landmarks:
    entry = LANDMARK_REGISTRY["landmarks"].get(name)
    link = entry["melos"]["link"] if entry and "melos" in entry else ""
    pos = world_pos.get(name)
    if pos:
        print(f"{name:<20} {pos[0]:>8.4f} {pos[1]:>8.4f} {pos[2]:>8.4f}  {link}")
    else:
        print(f"{name:<20} {'?':>8} {'?':>8} {'?':>8}  {link}")

print(f"\nTotal landmarks: {len(LANDMARK_REGISTRY['landmarks'])}")
print(f"Total world positions computed: {len(world_pos)}")
print("OK")
