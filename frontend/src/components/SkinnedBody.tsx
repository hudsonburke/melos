import { useRef, useMemo, useEffect, useState } from "react";
import * as THREE from "three";

// ── Types ────────────────────────────────────────────────────────────────

export interface SkinBundle {
  vertices: [number, number, number][];
  faces: [number, number, number][];
  joint_names: string[];
  joint_parent_ids: number[];
  joints: Record<string, [number, number, number]>;
  bind_pose_world: number[][][];  // (J, 4, 4)
  weight_data: number[];
  weight_indices: number[];
  weight_indptr: number[];
}

// ── SkinnedMesh component ────────────────────────────────────────────────

interface Props {
  bundle: SkinBundle;
  /** Map of bone name → (position, quaternion) from the animated skeleton */
  boneOffsets?: Record<string, { pos: THREE.Vector3; quat: THREE.Quaternion }>;
}

export default function SkinnedBody({ bundle, boneOffsets }: Props) {
  const meshRef = useRef<THREE.SkinnedMesh>(null);
  const skeletonRef = useRef<THREE.Skeleton | null>(null);
  const [ready, setReady] = useState(false);

  // Convert CSR weights to per-vertex arrays
  const { skinIndices, skinWeights } = useMemo(() => {
    const indices: number[] = [];
    const weights: number[] = [];
    const MAX_WEIGHTS = 4;

    for (let vi = 0; vi < bundle.weight_indptr.length - 1; vi++) {
      const start = bundle.weight_indptr[vi];
      const end = bundle.weight_indptr[vi + 1];

      // Pad or truncate to MAX_WEIGHTS
      const vi_arr: number[] = [];
      const vw_arr: number[] = [];
      for (let wi = start; wi < end && vi_arr.length < MAX_WEIGHTS; wi++) {
        vi_arr.push(bundle.weight_indices[wi]);
        vw_arr.push(bundle.weight_data[wi]);
      }
      // Pad with zeros
      while (vi_arr.length < MAX_WEIGHTS) {
        vi_arr.push(0);
        vw_arr.push(0);
      }
      // Normalize weights
      const sum = vw_arr.reduce((a, b) => a + b, 0);
      if (sum > 0) {
        for (let i = 0; i < MAX_WEIGHTS; i++) vw_arr[i] /= sum;
      }
      indices.push(...vi_arr);
      weights.push(...vw_arr);
    }
    return {
      skinIndices: new Uint16Array(indices),
      skinWeights: new Float32Array(weights),
    };
  }, [bundle]);

  // Build geometry
  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry();

    // Vertex positions
    const positions = new Float32Array(bundle.vertices.length * 3);
    for (let i = 0; i < bundle.vertices.length; i++) {
      positions[i * 3] = bundle.vertices[i][0];
      positions[i * 3 + 1] = bundle.vertices[i][1];
      positions[i * 3 + 2] = bundle.vertices[i][2];
    }
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));

    // Faces
    const triangles = new Uint32Array(bundle.faces.length * 3);
    for (let i = 0; i < bundle.faces.length; i++) {
      triangles[i * 3] = bundle.faces[i][0];
      triangles[i * 3 + 1] = bundle.faces[i][1];
      triangles[i * 3 + 2] = bundle.faces[i][2];
    }
    geo.setIndex(new THREE.BufferAttribute(triangles, 1));

    // Skin attributes
    geo.setAttribute("skinIndex", new THREE.BufferAttribute(skinIndices, 4));
    geo.setAttribute("skinWeight", new THREE.BufferAttribute(skinWeights, 4));

    // Compute normals for lighting
    geo.computeVertexNormals();

    return geo;
  }, [bundle, skinIndices, skinWeights]);

  // Build skeleton from bind pose
  const skeleton = useMemo(() => {
    const jn = bundle.joint_names.length;
    const bones: THREE.Bone[] = [];
    const boneMap = new Map<string, THREE.Bone>();

    // Create bones
    for (let i = 0; i < jn; i++) {
      const bone = new THREE.Bone();
      bone.name = bundle.joint_names[i];
      bones.push(bone);
      boneMap.set(bone.name, bone);
    }

    // Set parent-child relationships
    for (let i = 0; i < jn; i++) {
      const parentIdx = bundle.joint_parent_ids[i];
      if (parentIdx >= 0 && parentIdx < jn) {
        bones[parentIdx].add(bones[i]);
      }
    }

    // Set bind pose positions from bind_pose_world
    // We use the local transforms because Three.js skeleton uses parent-relative
    for (let i = 0; i < jn; i++) {
      const mat = bundle.bind_pose_world[i];
      // Extract translation from the 4x4 matrix
      bones[i].position.set(mat[0][3] / 100, mat[1][3] / 100, mat[2][3] / 100);
    }

    const skel = new THREE.Skeleton(bones);
    // Compute inverse bind matrices from bind_pose_world
    const invBind = new Float32Array(jn * 16);
    for (let i = 0; i < jn; i++) {
      const mat = new THREE.Matrix4().fromArray(
        (bundle.bind_pose_world[i] as number[][]).flat()
      );
      // Convert from mm/cm to meters? Actually this is in SOMA coords.
      // Scale translation to match our scene units
      const inv = mat.clone().invert();
      inv.toArray(invBind, i * 16);
    }
    skel.boneInverses = invBind as unknown as THREE.Matrix4[];

    skeletonRef.current = skel;
    return skel;
  }, [bundle]);

  // Update bone transforms when the skeleton moves
  useEffect(() => {
    if (!boneOffsets || !skeletonRef.current) return;
    const skel = skeletonRef.current;
    for (const bone of skel.bones) {
      const offset = boneOffsets[bone.name];
      if (offset) {
        bone.position.copy(offset.pos);
        bone.quaternion.copy(offset.quat);
      }
    }
    skel.update();
  }, [boneOffsets]);

  if (!ready && skeleton) {
    // Wait for the mesh to render once before marking as ready
    // (deferred to allow refs to attach)
    setTimeout(() => setReady(true), 0);
  }

  return (
    <group>
      {ready && (
        <skinnedMesh ref={meshRef} geometry={geometry} skeleton={skeleton}>
          <meshStandardMaterial
            color="#d4a574"
            roughness={0.6}
            metalness={0.0}
            transparent
            opacity={0.85}
            side={THREE.DoubleSide}
          />
        </skinnedMesh>
      )}
    </group>
  );
}
