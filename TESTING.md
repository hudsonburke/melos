# Melos — Test Guide

The canonical data model lives in **`packages/melos-core/src/melos/core/model.py`**.
All backend modules, the API, the frontend types, and the MJCF compiler/parser
derive from this single Pydantic schema. To verify the contract: `ModelState.model_json_schema()`

## Prerequisites

```bash
cd melos
uv sync --all-packages
cd frontend && npm install && cd ..

# Start the backend (keep running in a terminal):
LD_LIBRARY_PATH=/nix/store/5v131vrpa3wjcq4aqmlg98z6rsxrhl6m-zlib-1.3.2/lib:\
/nix/store/inv916fdyr4z049l8q2v8i5ll3dnmqj6-libglvnd-1.7.0/lib:\
/nix/store/hp54qay7ayl502zksigjr1irfn7h7zrp-gcc-15.2.0-lib/lib \
.venv/bin/uvicorn melos.backend.app:app --host 0.0.0.0 --port 8008

# In another terminal, all curl commands below assume the backend is at localhost:8008.
```

---

## 1. Health check

```bash
curl -s http://localhost:8008/health
# Expected: {"status":"ok"}
```

---

## 2. Load the Rajagopal model (22 joints, 22 links)

```bash
curl -s -X POST "http://localhost:8008/model/load?path=\
/var/lib/hermes/rerun-importer-osim/test_data/RajagopalData/Rajagopal2015.osim"
# Expected: {"name":"FullBodyModel_MuscleActuatedLowerLimb_TorqueActuatedUpperBody",
#            "skeleton":{"joints":{...},"links":{...},"transforms":{...},...}}
```

**Check the model loaded correctly:**

```bash
curl -s http://localhost:8008/model | python3 -c "
import sys, json
d = json.load(sys.stdin)
s = d['skeleton']
print(f'Joints: {len(s[\"joints\"])}')
print(f'Links:  {len(s[\"links\"])}')
print(f'Order:  {len(s[\"order\"])} bodies (topological)')
print(f'First 3 joints: {list(s[\"joints\"].keys())[:3]}')
"
```

---

## 3. View landmarks (57 anatomical landmarks)

```bash
curl -s "http://localhost:8008/model/landmarks?set_name=gait_full_body" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'{d[\"name\"]}: {d[\"count\"]} landmarks')
for k,v in sorted(d['landmarks'].items())[:5]:
    print(f'  {k}: on {v[\"link\"]} at offset {v[\"offset\"]}')
"
```

**Expected output shows landmarks from the Rajagopal model:**
```
gait_full_body: 57 landmarks
  C7: on torso at offset [-0.085, 0.435, 0.0017]
  CLAV: on torso at offset [0.04, 0.38, 0.017]
  ...
```

**List available marker sets:**

```bash
curl -s http://localhost:8008/model/marker-sets
# Expected: {"builtin":[{"name":"gait_full_body","count":"57",...}]}
```

---

## 4. Scale the skeleton (subject-specific)

### 4a. Segment-length scaling

```bash
curl -s -X POST http://localhost:8008/model/scale/lengths \
  -H 'Content-Type: application/json' \
  -d '{"target_lengths": {"thigh": 0.50, "shank": 0.44},
       "segment_to_link": {"thigh": "femur_r", "shank": "tibia_r"},
       "target_mass": 85.0}' | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'Scale factors:')
for k,v in sorted(d['link_scale_factors'].items()):
    if abs(v - 1.0) > 0.01:
        print(f'  {k}: x{v:.3f}')
print(f'Mass: {d[\"total_mass_before\"]:.1f} → {d[\"total_mass_after\"]:.1f} kg')
"
```

**Expected: femur_r scaled x1.099, tibia_r scaled x1.049, mass normalized to 85.0 kg.**

### 4b. Landmark-based scaling

```bash
curl -s -X POST http://localhost:8008/model/scale/landmarks \
  -H 'Content-Type: application/json' \
  -d '{"subject_measurements": {"thigh_r": 0.45, "shank_r": 0.52},
       "target_mass": 80.0}' | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'Matched: {len(d[\"matched_segments\"])} segments')
for m in d['matched_segments'][:4]:
    print(f'  {m}')
print(f'Warnings: {d[\"warnings\"]}')
"
```

---

## 5. Exoskeleton assemblies

### 5a. List available assembly descriptors

```bash
curl -s http://localhost:8008/model/assemblies
# Expected: {"assemblies":[{"name":"right_arm_brace_v1","n_parts":"2"},...]}
```

### 5b. Resolve an assembly (get attachment positions and measurements)

```bash
curl -s "http://localhost:8008/model/assembly/right_arm_brace" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'Assembly: {d[\"name\"]}')
for p in d['parts']:
    print(f'  Part: {p[\"id\"]} ({p[\"part_type\"]})')
    for role, att in p.get('attachments', {}).items():
        print(f'    {role}: {att[\"landmark_name\"]} at ({att[\"x\"]:.3f}, {att[\"y\"]:.3f}, {att[\"z\"]:.3f})')
"
```

**Expected:** The arm brace resolves against the Rajagopal skeleton's landmarks — RUA1, RUA3, RFASup, RStyloid with correct world positions.

### 5c. Build assembly spec (with optional subject overrides)

```bash
curl -s -X POST "http://localhost:8008/model/assembly/right_arm_brace/build" \
  -H 'Content-Type: application/json' \
  -d '{"subject_overrides": {"upper_arm_length_r": 0.35, "forearm_length_r": 0.28}}' \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'Assembly: {d[\"name\"]}')
for p in d['parts']:
    print(f'  {p[\"id\"]}: params={json.dumps(p[\"parameters\"])}')
    for m,v in p['measurements'].items():
        print(f'    measured {m}: {v:.3f} m')
"
```

---

## 6. Compile to MuJoCo

### 6a. Compile skeleton only

```bash
curl -s http://localhost:8008/model/compile | python3 -c "
import sys, json
d = json.load(sys.stdin)
mjcf = d['mjcf']
lines = mjcf.split('\n')
print(f'{len(lines)} lines of MJCF')
print('First 5 lines:')
for line in lines[:5]:
    print(f'  {line}')
"
```

**Verify the output loads in MuJoCo:**

```bash
LD_LIBRARY_PATH=/nix/store/5v131vrpa3wjcq4aqmlg98z6rsxrhl6m-zlib-1.3.2/lib:\
/nix/store/inv916fdyr4z049l8q2v8i5ll3dnmqj6-libglvnd-1.7.0/lib:\
/nix/store/hp54qay7ayl502zksigjr1irfn7h7zrp-gcc-15.2.0-lib/lib \
.venv/bin/python -c "
import urllib.request, json, tempfile, os
import mujoco
d = json.loads(urllib.request.urlopen('http://localhost:8008/model/compile').read())
with tempfile.NamedTemporaryFile(suffix='.xml', mode='w', delete=False) as f:
    f.write(d['mjcf']); tmp = f.name
m = mujoco.MjModel.from_xml_path(tmp)
os.unlink(tmp)
print(f'✓ MuJoCo validates: {m.nbody} bodies, {m.njnt} joints, {m.nu} actuators')
"
```

### 6b. Compile with exoskeleton assembly

```bash
curl -s -X POST "http://localhost:8008/model/compile/with-assembly" \
  -H 'Content-Type: application/json' \
  -d '{"assembly_name": "right_arm_brace"}' | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'Bodies: {d[\"n_bodies\"]} (was 22, +2 exo cuffs)')
print(f'Cables: {d[\"n_cables\"]}')
"
```

**Also validate in MuJoCo:**

```bash
LD_LIBRARY_PATH=... .venv/bin/python -c "
import urllib.request, json, tempfile, os, mujoco
req = urllib.request.Request('http://localhost:8008/model/compile/with-assembly',
    data=json.dumps({'assembly_name': 'right_arm_brace'}).encode(),
    headers={'Content-Type': 'application/json'}, method='POST')
d = json.loads(urllib.request.urlopen(req).read())
with tempfile.NamedTemporaryFile(suffix='.xml', mode='w', delete=False) as f:
    f.write(d['mjcf']); tmp = f.name
m = mujoco.MjModel.from_xml_path(tmp)
os.unlink(tmp)
print(f'✓ With exo: {m.nbody}b, {m.njnt}j, {m.nu}act')
"
```

**Expected:** 26 bodies (22 skeleton + 2 cuffs), 22 joints, 22 actuators.

---

## 7. MyoSuite round-trip (MJCF → Melos → MJCF)

### 7a. Import a MyoSuite model

```bash
curl -s -X POST "http://localhost:8008/model/import/mjcf?path=\
/var/lib/hermes/myosuite/myosuite/simhive/myo_sim/elbow/myoelbow_1dof6muscles_1dofexo.xml" \
| python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'Imported: {d[\"name\"]}')
print(f'Links: {d[\"n_links\"]}, Joints: {d[\"n_joints\"]}, Cables: {d[\"n_cables\"]}')
"
```

### 7b. Compile back and validate

```bash
LD_LIBRARY_PATH=... .venv/bin/python -c "
import urllib.request, json, tempfile, os, mujoco
# Import
req = urllib.request.Request(
    'http://localhost:8008/model/import/mjcf?path=/var/lib/hermes/myosuite/myosuite/simhive/myo_sim/elbow/myoelbow_1dof6muscles_1dofexo.xml')
urllib.request.urlopen(req)
# Compile
d = json.loads(urllib.request.urlopen('http://localhost:8008/model/compile').read())
with tempfile.NamedTemporaryFile(suffix='.xml', mode='w', delete=False) as f:
    f.write(d['mjcf']); tmp = f.name
m = mujoco.MjModel.from_xml_path(tmp)
os.unlink(tmp)
print(f'✓ Round-trip: {m.nbody}b, {m.njnt}j, {m.nu}act, {m.ntendon}tendons')
# Verify muscle types
for i in range(m.nu):
    n = m.actuator(i).name
    print(f'  Act {i}: {n}')
"
```

**Expected:** 7 bodies, 1 joint, 7 actuators (6 muscles + 1 exo motor), 6 tendons.

### 7c. Full exoskeleton + MyoSuite model

```bash
# Import the MyoSuite model first, then apply the cable exo assembly
curl -s -X POST "http://localhost:8008/model/load?path=\
/var/lib/hermes/rerun-importer-osim/test_data/RajagopalData/Rajagopal2015.osim" > /dev/null

curl -s -X POST "http://localhost:8008/model/compile/with-assembly" \
  -H 'Content-Type: application/json' \
  -d '{"assembly_name": "upper_limb_cable_exo"}' | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'Bodies: {d[\"n_bodies\"]}, Cables: {d[\"n_cables\"]}')
# Show actuator types
for line in d['mjcf'].split(chr(10)):
    if '<motor' in line and 'tendon' in line:
        print(f'  Motor: {line.strip()[:100]}')
    if '<muscle' in line:
        print(f'  Muscle: {line.strip()[:100]}')
"
```

**Expected:** 26 bodies, 2 cables with Hill-type muscle on cable 1 and motor on cable 2.

---

## 8. Frontend (R3F editor)

```bash
cd frontend && npm run dev
# Opens at http://localhost:5173
```

With the backend running on port 8008, the frontend:
1. Loads the Rajagopal model automatically
2. Click any link box to select it (orange highlight)
3. Use ↕ Move / ↻ Rotate toggle in sidebar to switch TransformControls mode
4. Toggle Landmarks in sidebar to see the 57 anatomical points
5. Toggle Skin to see the skinned body mesh overlay (18K verts)

---

## 9. Scaling pipeline (standalone test without server)

```bash
LD_LIBRARY_PATH=... .venv/bin/python backend/tests/test_scaling.py
# Expected: 3 tests, all passed
```

```bash
LD_LIBRARY_PATH=... .venv/bin/python backend/tests/test_landmark_scaling.py
# Expected: landmark-based scaling verified
```

---

## 10. Full round-trip tests

```bash
LD_LIBRARY_PATH=... .venv/bin/python backend/tests/test_mjcf_roundtrip.py
# Expected: 2 tests — round-trip and assembly compilation
```

```bash
LD_LIBRARY_PATH=... .venv/bin/python backend/tests/test_mhr_adapter.py
# Expected: MHR adapter path verified (non-unit scale factors found)
```

---

## What each test covers

| # | Test | Covers | Requires backend? |
|---|---|---|---|
| 1 | Health check | Server running | Yes |
| 2 | Load model | OSIM → Arrow components | Yes |
| 3 | View landmarks | Landmark registry | Yes |
| 4 | Scale skeleton | Scaling pipeline | Yes |
| 5 | Assemblies | Assembly descriptors | Yes |
| 6 | MJCF compile | Compiler output + MuJoCo | Yes |
| 7 | MyoSuite round-trip | Parser + compiler | Yes |
| 8 | Frontend | R3F viewer/editor | Yes |
| 9 | Standalone tests | Scaling logic | No |
| 10 | Integration tests | Full pipeline | No (most) |
