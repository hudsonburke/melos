import sys, math
sys.path.insert(0, "backend/src")
from melos.backend.app import load_model_from_osim
m = load_model_from_osim("/var/lib/hermes/rerun-importer-osim/test_data/RajagopalData/Rajagopal2015.osim")
for name in ["ground", "pelvis", "femur_r", "tibia_r", "talus_r"]:
    xf = m.skeleton.transforms.get(name)
    if xf:
        t = xf.translation
        length = math.sqrt(t[0]*t[0] + t[1]*t[1] + t[2]*t[2])
        print(f"translation=({t[0]:.4f}, {t[1]:.4f}, {t[2]:.4f}), len={length:.6f}")
