import { useState, useRef } from "react";
import { Canvas } from "@react-three/fiber";
import {
  OrbitControls,
  TransformControls,
  Grid,
  Box,
  Line,
} from "@react-three/drei";
import * as THREE from "three";
import type { ModelState, SkeletonState } from "../types/schema";

// ── Scene component ──────────────────────────────────────────────────────

interface SceneProps {
  model: ModelState | null;
  onSelect: (entityPath: string | null) => void;
  selected: string | null;
  apiBase: string;
}

export default function Scene({ model, onSelect, selected, apiBase }: SceneProps) {
  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      <Canvas
        camera={{ position: [2, 2, 3], fov: 50 }}
        style={{ background: "#1a1a1a" }}
      >
        <ambientLight intensity={0.4} />
        <directionalLight position={[5, 10, 5]} intensity={0.8} />
        <directionalLight position={[-3, -2, -5]} intensity={0.3} />
        <Grid infiniteGrid />
        <OrbitControls makeDefault />
        {model && (
          <SkeletonRenderer
            skeleton={model.skeleton}
            onSelect={onSelect}
            selected={selected}
            apiBase={apiBase}
          />
        )}
      </Canvas>
    </div>
  );
}

// ── World transforms (iterates topological order: parent before child) ────

interface WorldTransform {
  position: THREE.Vector3;
  quaternion: THREE.Quaternion;
}

let _cache: { key: string; map: Map<string, WorldTransform> } | null = null;

function computeWorldTransforms(skeleton: SkeletonState): Map<string, WorldTransform> {
  const key = skeleton.order.join(",");
  if (_cache && _cache.key === key) return _cache.map;

  const result = new Map<string, WorldTransform>();

  for (const body of skeleton.order) {
    const xform = skeleton.transforms[body];
    if (!xform) {
      result.set(body, { position: new THREE.Vector3(), quaternion: new THREE.Quaternion() });
      continue;
    }
    const pos = new THREE.Vector3(xform.translation[0], xform.translation[1], xform.translation[2]);
    const quat = new THREE.Quaternion(xform.rotation[1], xform.rotation[2], xform.rotation[3], xform.rotation[0]);

    const parent = skeleton.parent_map[body];
    if (parent) {
      const p = result.get(parent);
      if (p) {
        pos.applyQuaternion(p.quaternion).add(p.position);
        quat.multiplyQuaternions(p.quaternion, quat);
      }
    }
    result.set(body, { position: pos, quaternion: quat });
  }

  _cache = { key, map: result };
  return result;
}

// ── Skeleton renderer ────────────────────────────────────────────────────

interface SkeletonRendererProps {
  skeleton: SkeletonState;
  onSelect: (path: string | null) => void;
  selected: string | null;
  apiBase: string;
}

function SkeletonRenderer({ skeleton, onSelect, selected, apiBase }: SkeletonRendererProps) {
  const worldTransforms = computeWorldTransforms(skeleton);

  return (
    <group>
      {skeleton.order.map((name) => {
        const link = skeleton.links[name];
        if (!link || !link.visible) return null;
        const wt = worldTransforms.get(name);
        if (!wt) return null;
        const isSelected = selected === name;
        return (
          <LinkNode
            key={name}
            name={name}
            worldTransform={wt}
            isSelected={isSelected}
            onClick={() => onSelect(isSelected ? null : name)}
            apiBase={apiBase}
          />
        );
      })}
      {Object.entries(skeleton.parent_map).map(([child, parent]) => {
        const c = worldTransforms.get(child);
        const p = worldTransforms.get(parent);
        if (!c || !p) return null;
        return <Bone key={`b:${parent}-${child}`} start={p.position} end={c.position} />;
      })}
    </group>
  );
}

// ── Bone ─────────────────────────────────────────────────────────────────

function Bone({ start, end }: { start: THREE.Vector3; end: THREE.Vector3 }) {
  return <Line points={[start, end]} color="#666" lineWidth={1} />;
}

// ── Link node with TransformControls ─────────────────────────────────────

interface LinkNodeProps {
  name: string;
  worldTransform: WorldTransform;
  isSelected: boolean;
  onClick: () => void;
  apiBase: string;
}

function LinkNode({ name, worldTransform, isSelected, onClick, apiBase }: LinkNodeProps) {
  const [hovered, setHovered] = useState(false);
  const [meshReady, setMeshReady] = useState(false);
  const meshRef = useRef<THREE.Mesh>(null);

  const color = isSelected ? "#ff6600" : hovered ? "#44aaff" : "#3399ff";
  const s = isSelected ? 1.5 : hovered ? 1.2 : 1.0;

  const handleDragEnd = async () => {
    if (!meshRef.current) return;
    const p = meshRef.current.position;
    try {
      await fetch(`${apiBase}/model/skeleton/transforms/${name}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ translation: [p.x, p.y, p.z], rotation: [0, 0, 0, 1] }),
      });
    } catch (_) {}
  };

  const refCb = (node: THREE.Mesh | null) => {
    meshRef.current = node;
    if (node) setMeshReady(true);
  };

  return (
    <group position={worldTransform.position} quaternion={worldTransform.quaternion}>
      {isSelected && meshReady && (
        <TransformControls object={meshRef.current!} mode="translate" onMouseUp={handleDragEnd} />
      )}
      <Box
        ref={refCb}
        args={[0.1 * s, 0.1 * s, 0.1 * s]}
        onPointerOver={(e) => { e.stopPropagation(); setHovered(true); }}
        onPointerOut={() => setHovered(false)}
        onClick={(e) => { e.stopPropagation(); onClick(); }}
      >
        <meshStandardMaterial color={color} transparent opacity={0.85} />
      </Box>
    </group>
  );
}
