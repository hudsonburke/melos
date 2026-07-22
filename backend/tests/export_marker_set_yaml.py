"""Export the built-in landmark registry to the marker_sets YAML format."""
import sys, yaml, json
sys.path.insert(0, "backend/src")
from melos.backend.landmarks import LANDMARK_REGISTRY

data = {
    "name": "gait_full_body",
    "description": "Standard gait analysis marker set derived from the Rajagopal2015 OpenSim full-body model and OpenCap marker conventions. 57 landmarks covering pelvis, legs, torso, and arms.",
    "reference_model": "Rajagopal2015",
    "landmarks": LANDMARK_REGISTRY["landmarks"],
}
yaml.dump(data, sys.stdout, default_flow_style=False, sort_keys=False, width=120)
