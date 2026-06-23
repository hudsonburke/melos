"""Paste this into Blender's Python console after importing a model."""
import bpy
import json

print("\n" + "="*60)
print("ARMATURE ALIGNMENT DIAGNOSTIC")
print("="*60)

# Find the armature
armature = None
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE' and 'myofullbody' in obj.name:
        armature = obj
        break

if armature is None:
    print("ERROR: No myofullbody armature found")
else:
    print(f"\nArmature: {armature.name}")
    print(f"  Object location (world): {tuple(round(v, 4) for v in armature.location)}")
    print(f"  matrix_world translation: {tuple(round(v, 4) for v in armature.matrix_world.translation)}")
    print(f"  Parent: {armature.parent.name if armature.parent else 'None'}")
    if armature.parent:
        print(f"  Parent location: {tuple(round(v, 4) for v in armature.parent.location)}")
        print(f"  matrix_parent_inverse:\n{armature.matrix_parent_inverse}")
    
    # Check bone positions
    print(f"\n  Bones ({len(armature.data.bones)}):")
    for bone in list(armature.data.bones)[:5]:
        head_world = armature.matrix_world @ bone.head_local
        print(f"    {bone.name}: head_local={tuple(round(v,4) for v in bone.head_local)} head_world={tuple(round(v,4) for v in head_world)}")
    
    # Check the root bone specifically
    root_bone = armature.data.bones.get("Full Body")
    if root_bone:
        head_world = armature.matrix_world @ root_bone.head_local
        print(f"\n  ROOT bone 'Full Body':")
        print(f"    head_local: {tuple(round(v,4) for v in root_bone.head_local)}")
        print(f"    head_world: {tuple(round(v,4) for v in head_world)}")
    else:
        print("\n  ROOT bone 'Full Body': NOT FOUND")

# Find skin mesh
skin_mesh = None
for obj in bpy.data.objects:
    if obj.type == 'MESH' and 'myofullbody_skin' in obj.name:
        skin_mesh = obj
        break

if skin_mesh is None:
    print("\nSkin mesh: NOT FOUND")
else:
    print(f"\nSkin mesh: {skin_mesh.name}")
    print(f"  Object location (world): {tuple(round(v, 4) for v in skin_mesh.location)}")
    print(f"  matrix_world translation: {tuple(round(v, 4) for v in skin_mesh.matrix_world.translation)}")
    print(f"  Parent: {skin_mesh.parent.name if skin_mesh.parent else 'None'}")
    
    # Vertex bounding box
    verts = skin_mesh.data.vertices
    if verts:
        xs = [v.co.x for v in verts]
        ys = [v.co.y for v in verts]
        zs = [v.co.z for v in verts]
        print(f"  Vertex bounds (local): X=[{min(xs):.3f}, {max(xs):.3f}] Y=[{min(ys):.3f}, {max(ys):.3f}] Z=[{min(zs):.3f}, {max(zs):.3f}]")
        # World-space bounds
        mat = skin_mesh.matrix_world
        world_zs = [(mat @ v.co).z for v in verts]
        print(f"  Vertex Z (world): [{min(world_zs):.3f}, {max(world_zs):.3f}]")

# Find display root
for obj in bpy.data.objects:
    if 'display_root' in obj.name:
        print(f"\nDisplay root: {obj.name}")
        print(f"  Location: {tuple(round(v, 4) for v in obj.location)}")
        print(f"  Rotation (quat): {tuple(round(v, 4) for v in obj.rotation_quaternion)}")
        print(f"  matrix_world translation: {tuple(round(v, 4) for v in obj.matrix_world.translation)}")
        break

print("\n" + "="*60)
