#!/usr/bin/env bash
# Quick self-test script for the Melos pipeline.
# Run from the melos repo root.
# Usage: bash test_quick.sh
set -e

BASE="http://localhost:8008"
PASS=0
FAIL=0

check() {
    local label="$1"
    local cmd="$2"
    if eval "$cmd" 2>/dev/null; then
        echo "  ✓ $label"
        PASS=$((PASS + 1))
    else
        echo "  ✗ $label"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== Melos Quick Test ==="
echo ""

# 1. Health check
echo "--- 1. Health check ---"
check "Health endpoint" "curl -sf $BASE/health | grep -q ok"

# 2. Load model
echo "--- 2. Load Rajagopal model ---"
check "Load OSIM" "curl -sf -X POST '$BASE/model/load?path=/var/lib/hermes/rerun-importer-osim/test_data/RajagopalData/Rajagopal2015.osim' | grep -q 'n_joints'"

check "Get model has 22 joints" "curl -sf $BASE/model | python3 -c 'import sys,json; d=json.load(sys.stdin); assert len(d[\"skeleton\"][\"joints\"]) == 22'"

# 3. Landmarks
echo "--- 3. Landmarks ---"
check "57 landmarks" "curl -sf '$BASE/model/landmarks?set_name=gait_full_body' | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d[\"count\"] == 57'"

# 4. Scale
echo "--- 4. Scaling ---"
check "Segment-length scaling" "curl -sf -X POST $BASE/model/scale/lengths -H 'Content-Type: application/json' -d '{\"target_lengths\":{\"thigh\":0.50,\"shank\":0.44},\"segment_to_link\":{\"thigh\":\"femur_r\",\"shank\":\"tibia_r\"},\"target_mass\":85.0}' | python3 -c 'import sys,json; d=json.load(sys.stdin); assert abs(d[\"link_scale_factors\"][\"femur_r\"] - 1.1) < 0.02'"

# 5. Assembly
echo "--- 5. Assemblies ---"
check "List assemblies" "curl -sf $BASE/model/assemblies | grep -q right_arm_brace"
check "Resolve arm brace" "curl -sf '$BASE/model/assembly/right_arm_brace' | python3 -c 'import sys,json; d=json.load(sys.stdin); assert len(d[\"parts\"]) == 2'"

# 6. Compile
echo "--- 6. MJCF Compile ---"
check "Compile skeleton" "curl -sf $BASE/model/compile | python3 -c 'import sys,json; d=json.load(sys.stdin); mjcf=d[\"mjcf\"]; assert \"mujoco\" in mjcf; assert \"worldbody\" in mjcf'"

check "Compile with assembly" "curl -sf -X POST $BASE/model/compile/with-assembly -H 'Content-Type: application/json' -d '{\"assembly_name\": \"right_arm_brace\"}' | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d[\"n_bodies\"] > 22'"

# 7. MyoSuite round-trip (MuJoCo validation)
echo "--- 7. MyoSuite round-trip ---"
if python3 -c "import mujoco" 2>/dev/null; then
    check "Import + compile + MuJoCo validate" "curl -sf -X POST '$BASE/model/import/mjcf?path=/var/lib/hermes/myosuite/myosuite/simhive/myo_sim/elbow/myoelbow_1dof6muscles_1dofexo.xml' | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d[\"n_cables\"] == 6'"
else
    echo "  - Skip MuJoCo tests (mujoco not importable in this env)"
fi

# 8. Frontend build check
echo "--- 8. Frontend ---"
if [ -d frontend ]; then
    check "Frontend builds" "cd frontend && npm run build 2>/dev/null | tail -1 | grep -q 'built in'"
fi

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ]
