"""Find bones that are far from the skin mesh."""
import bpy
from mathutils import Vector

print("\n" + "="*60)
print("BONE POSITION DIAGNOSTIC")
print("="*60)

armature = None
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE' and 'myofullbody' in obj.name:
        armature = obj
        break

if armature is None:
    print("ERROR: No armature found")
    raise SystemExit

skin_mesh = None
for obj in bpy.data.objects:
    if obj.type == 'MESH' and 'myofullbody_skin' in obj.name:
        skin_mesh = obj
        break

skin_center_z = 1.5
if skin_mesh and skin_mesh.data.vertices:
    mat = skin_mesh.matrix_world
    zs = [(mat @ v.co).z for v in skin_mesh.data.vertices]
    skin_center_z = (min(zs) + max(zs)) / 2
    print(f"Skin Z: [{min(zs):.3f}, {max(zs):.3f}], center: {skin_center_z:.3f}")

print(f"\nMisplaced bones (>0.3m from skin center):")
print(f"{'Name':<30} {'local_Z':>10} {'world_Z':>10} {'delta':>10}")
print("-" * 65)

for bone in armature.data.bones:
    head_world = armature.matrix_world @ bone.head_local
    delta = abs(head_world.z - skin_center_z)
    if delta > 0.3:
        print(f"{bone.name:<30} {bone.head_local.z:>10.3f} {head_world.z:>10.3f} {delta:>10.3f}")
