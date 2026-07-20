import { useState } from "react";
import { Canvas } from "@react-three/fiber";
import {
  OrbitControls,
  Grid,
  Box,
  Line,
} from "@react-three/drei";
import * as THREE from "three";
import type { ModelState, SkeletonState, LinkDefinition, LinkTransform } from "../types/schema";

// ── Scene component ──────────────────────────────────────────────────────

interface SceneProps {
  model: ModelState | null;
  onSelect: (entityPath: string) => void;
  selected: string | null;
}

export default function Scene({ model, onSelect, selected }: SceneProps) {
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
          />
        )}
      </Canvas>
    </div>
  );
}

// ── Skeleton renderer ────────────────────────────────────────────────────

interface SkeletonRendererProps {
  skeleton: SkeletonState;
  onSelect: (path: string) => void;
  selected: string | null;
}

function SkeletonRenderer({ skeleton, onSelect, selected }: SkeletonRendererProps) {
  const links = skeleton.links;
  const transforms = skeleton.transforms;
  const parentMap = skeleton.parent_map;

  const worldTransforms = computeWorldTransforms(links, transforms, parentMap);

  return (
    <group>
      {/* Render each link as a box at its world position */}
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
            onClick={() => onSelect(name)}
          />
        );
      })}

      {/* Render bones (lines between parent and child) */}
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

interface BoneProps {
  start: THREE.Vector3;
  end: THREE.Vector3;
}

function Bone({ start, end }: BoneProps) {
  const points = [start, end];
  return (
    <Line
      points={points}
      color="#888"
      lineWidth={1}
    />
  );
}

// ── Link node with click selection ──────────────────────────────────────

interface LinkNodeProps {
  name: string;
  worldTransform: WorldTransform;
  isSelected: boolean;
  onClick: () => void;
}

function LinkNode({ name: _name, worldTransform, isSelected, onClick }: LinkNodeProps) {
  const [hovered, setHovered] = useState(false);

  const color = isSelected ? "#ff6600" : hovered ? "#44aaff" : "#3399ff";
  const scale = isSelected ? 1.4 : hovered ? 1.2 : 1.0;

  return (
    <group
      position={worldTransform.position}
      quaternion={worldTransform.quaternion}
    >
      <Box
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
