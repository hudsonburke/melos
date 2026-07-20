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
import type { ModelState, SkeletonState, LinkDefinition, LinkTransform } from "../types/schema";

// ── Scene component ──────────────────────────────────────────────────────

interface SceneProps {
  model: ModelState | null;
  onSelect: (entityPath: string | null) => void;
  selected: string | null;
  apiBase: string;
}

export default function Scene({ model, onSelect: handleSelect, selected, apiBase }: SceneProps) {
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
            onSelect={handleSelect}
            selected={selected}
            apiBase={apiBase}
          />
        )}
      </Canvas>
    </div>
  );
}

// ── Skeleton renderer ────────────────────────────────────────────────────

interface SkeletonRendererProps {
  skeleton: SkeletonState;
  onSelect: (path: string | null) => void;
  selected: string | null;
  apiBase: string;
}

function SkeletonRenderer({ skeleton, onSelect, selected, apiBase }: SkeletonRendererProps) {
  const links = skeleton.links;
  const transforms = skeleton.transforms;
  const parentMap = skeleton.parent_map;

  const worldTransforms = computeWorldTransforms(links, transforms, parentMap);

  return (
    <group>
      {/* Render each link */}
      {Object.entries(links).map(([name, _link]) => {
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

      {/* Render bones */}
      {Object.entries(parentMap).map(([child, parent]) => {
        const childWt = worldTransforms.get(child);
        const parentWt = worldTransforms.get(parent);
        if (!childWt || !parentWt) return null;
        return (
          <Bone key={`bone-${parent}-${child}`}
            start={parentWt.position}
            end={childWt.position}
          />
        );
      })}
    </group>
  );
}

// ── Bone ────────────────────────────────────────────────────────────────

function Bone({ start, end }: { start: THREE.Vector3; end: THREE.Vector3 }) {
  return (
    <Line points={[start, end]} color="#666" lineWidth={1} />
  );
}

// ── Link node with TransformControls ────────────────────────────────────

interface LinkNodeProps {
  name: string;
  worldTransform: WorldTransform;
  isSelected: boolean;
  onClick: () => void;
  apiBase: string;
}

function LinkNode({ name, worldTransform, isSelected, onClick, apiBase }: LinkNodeProps) {
  const [hovered, setHovered] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [meshReady, setMeshReady] = useState(false);
  const meshRef = useRef<THREE.Mesh>(null);

  const color = dragging ? "#ff9900" : isSelected ? "#ff6600" : hovered ? "#44aaff" : "#3399ff";
  const scale = isSelected ? 1.5 : hovered ? 1.2 : 1.0;

  // On drag end, persist the transform to the backend
  const handleDragEnd = async () => {
    setDragging(false);
    if (!meshRef.current) return;

    const pos = meshRef.current.position;
    const quat = meshRef.current.quaternion;

    try {
      const res = await fetch(`${apiBase}/model/skeleton/transforms/${name}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          translation: [pos.x, pos.y, pos.z],
          rotation: [quat.w, quat.x, quat.y, quat.z],
        }),
      });
      if (!res.ok) {
        console.warn("Failed to save transform:", res.status);
      }
    } catch (e) {
      console.warn("Failed to save transform:", e);
    }
  };

  // Callback ref that triggers re-render once mesh is available
  const setMeshCallback = (node: THREE.Mesh | null) => {
    meshRef.current = node;
    if (node) setMeshReady(true);
  };

  return (
    <group
      position={worldTransform.position}
      quaternion={worldTransform.quaternion}
    >
      {isSelected && meshReady && (
        <TransformControls
          object={meshRef.current!}
          mode="translate"
          onMouseUp={handleDragEnd}
        />
      )}
      <Box
        ref={setMeshCallback}
        args={[0.1 * scale, 0.1 * scale, 0.1 * scale]}
        onPointerOver={(e) => { e.stopPropagation(); setHovered(true); }}
        onPointerOut={() => setHovered(false)}
        onClick={(e) => { e.stopPropagation(); onClick(); }}
      >
        <meshStandardMaterial
          color={color}
          transparent
          opacity={0.85}
        />
      </Box>
    </group>
  );
}

// ── World transform computation ──────────────────────────────────────────

interface WorldTransform {
  position: THREE.Vector3;
  quaternion: THREE.Quaternion;
}

function computeWorldTransforms(
  links: Record<string, LinkDefinition>,
  transforms: Record<string, LinkTransform>,
  parentMap: Record<string, string>,
): Map<string, WorldTransform> {
  const result = new Map<string, WorldTransform>();
  const cache = new Map<string, WorldTransform>();

  function getWorld(name: string): WorldTransform {
    const cached = cache.get(name);
    if (cached) return cached;

    const xform = transforms[name];
    if (!xform) {
      const identity: WorldTransform = {
        position: new THREE.Vector3(0, 0, 0),
        quaternion: new THREE.Quaternion(),
      };
      cache.set(name, identity);
      return identity;
    }

    const localPos = new THREE.Vector3(
      xform.translation[0],
      xform.translation[1],
      xform.translation[2],
    );
    const localQuat = new THREE.Quaternion(
      xform.rotation[1],
      xform.rotation[2],
      xform.rotation[3],
      xform.rotation[0],
    );

    const parent = parentMap[name];
    if (parent) {
      const parentWt = getWorld(parent);
      const worldPos = localPos.clone().applyQuaternion(parentWt.quaternion).add(parentWt.position);
      const worldQuat = parentWt.quaternion.clone().multiply(localQuat);
      const wt: WorldTransform = { position: worldPos, quaternion: worldQuat };
      cache.set(name, wt);
      return wt;
    }

    const wt: WorldTransform = { position: localPos, quaternion: localQuat };
    cache.set(name, wt);
    return wt;
  }

  for (const name of Object.keys(links)) {
    result.set(name, getWorld(name));
  }

  return result;
}
