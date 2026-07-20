"""Quick smoke test for the backend."""
import json, sys
sys.path.insert(0, "backend/src")
sys.path.insert(0, ".venv/lib/python3.14/site-packages")
from melos.backend.app import load_model_from_osim

m = load_model_from_osim("/var/lib/hermes/rerun-importer-osim/test_data/RajagopalData/Rajagopal2015.osim")
print(json.dumps({
    "name": m.name,
    "n_joints": len(m.skeleton.joints),
    "n_links": len(m.skeleton.links),
}, indent=2))
print("OK: model loaded successfully")
