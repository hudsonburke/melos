import { useState, useRef, useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import {
  OrbitControls,
  TransformControls,
  Grid,
  Box,
  Line,
  Sphere,
  Text,
} from "@react-three/drei";
import * as THREE from "three";
import type { ModelState, SkeletonState } from "../types/schema";
import type { SkinBundle } from "./SkinnedBody";
import SkinnedBody from "./SkinnedBody";

type LandmarkData = Record<string, { link: string; offset: [number, number, number] }>;

// ── Scene ────────────────────────────────────────────────────────────────

interface SceneProps {
  model: ModelState | null;
  onSelect: (ep: string | null) => void;
  selected: string | null;
  apiBase: string;
  transformMode: "translate" | "rotate";
  showLandmarks: boolean;
  landmarks: LandmarkData | null;
  showSkin: boolean;
  skinBundle: SkinBundle | null;
}

export default function Scene({ model, onSelect, selected, apiBase, transformMode, showLandmarks, landmarks, showSkin, skinBundle }: SceneProps) {
  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      <Canvas camera={{ position: [2, 2, 3], fov: 50 }} style={{ background: "#1a1a1a" }}>
        <ambientLight intensity={0.4} />
        <directionalLight position={[5, 10, 5]} intensity={0.8} />
        <directionalLight position={[-3, -2, -5]} intensity={0.3} />
        <Grid infiniteGrid />
        <OrbitControls makeDefault />
        {model && (
          <>
            <SkeletonRenderer
              skeleton={model.skeleton} selected={selected} onSelect={onSelect}
              apiBase={apiBase} transformMode={transformMode}
              showLandmarks={showLandmarks} landmarks={landmarks}
            />
            {showSkin && skinBundle && (
              <SkinnedBody bundle={skinBundle} />
            )}
          </>
        )}
      </Canvas>
    </div>
  );
}

// ── Helpers ──────────────────────────────────────────────────────────────

function useChildrenOf(pm: Record<string, string>): Record<string, string[]> {
  return useMemo(() => {
    const m: Record<string, string[]> = {};
    for (const [c, p] of Object.entries(pm)) (m[p] ??= []).push(c);
    return m;
  }, [pm]);
}

// ── Skeleton renderer ────────────────────────────────────────────────────

interface SRProps {
  skeleton: SkeletonState;
  selected: string | null;
  onSelect: (p: string | null) => void;
  apiBase: string;
  transformMode: "translate" | "rotate";
  showLandmarks: boolean;
  landmarks: LandmarkData | null;
}

function SkeletonRenderer({ skeleton, selected, onSelect, apiBase, transformMode, showLandmarks, landmarks }: SRProps) {
  const childrenOf = useChildrenOf(skeleton.parent_map);
  const allChildren = useMemo(() => new Set(Object.keys(skeleton.parent_map)), [skeleton.parent_map]);
  const roots = skeleton.order.filter((n) => !allChildren.has(n));
  const worldPoses = useMemo(() => computeBonePositions(skeleton), [skeleton]);

  // Build per-link landmark list
  const linkLandmarks = useMemo(() => {
    const ll: Record<string, { name: string; offset: [number, number, number] }[]> = {};
    if (!landmarks) return ll;
    for (const [name, def] of Object.entries(landmarks)) {
      if (!def.link) continue;
      (ll[def.link] ??= []).push({ name, offset: def.offset });
    }
    return ll;
  }, [landmarks]);

  return (
    <group>
      {roots.map((name) => (
        <LinkGroup key={name} name={name} skeleton={skeleton} childrenOf={childrenOf}
          selected={selected} onSelect={onSelect} apiBase={apiBase}
          transformMode={transformMode}
          showLandmarks={showLandmarks} linkLandmarks={linkLandmarks[name] || []} />
      ))}
      {Object.entries(skeleton.parent_map).map(([child, parent]) => {
        const c = worldPoses.get(child);
        const p = worldPoses.get(parent);
        if (!c || !p) return null;
        return <Line key={`b:${parent}-${child}`} points={[p, c]} color="#666" lineWidth={1} />;
      })}
    </group>
  );
}

// ── Bone positions ───────────────────────────────────────────────────────

function computeBonePositions(s: SkeletonState): Map<string, THREE.Vector3> {
  const m = new Map<string, THREE.Vector3>();
  const order = s.order.length ? s.order : Object.keys(s.parent_map);
  for (const name of order) {
    const xf = s.transforms[name];
    const pos = xf ? new THREE.Vector3(xf.translation[0], xf.translation[1], xf.translation[2]) : new THREE.Vector3();
    const q = xf ? new THREE.Quaternion(xf.rotation[1], xf.rotation[2], xf.rotation[3], xf.rotation[0]) : new THREE.Quaternion();
    const pn = s.parent_map[name];
    if (pn) { const pp = m.get(pn); if (pp) { pos.applyQuaternion(q); pos.add(pp); } }
    m.set(name, pos);
  }
  return m;
}

// ── Landmark dot ─────────────────────────────────────────────────────────

function LandmarkDot({ name }: { name: string }) {
  const [hovered, setHovered] = useState(false);
  return (
    <group>
      <Sphere args={[0.015, 8, 8]}
        onPointerOver={(e) => { e.stopPropagation(); setHovered(true); }}
        onPointerOut={() => setHovered(false)}>
        <meshStandardMaterial color={hovered ? "#ffff00" : "#ff4444"}
          emissive={hovered ? "#ffff00" : "#ff4444"} emissiveIntensity={0.3} />
      </Sphere>
      {hovered && (
        <Text position={[0, 0.04, 0]} fontSize={0.03} color="white" anchorX="center" anchorY="bottom">{name}</Text>
      )}
    </group>
  );
}

// ── Link group ───────────────────────────────────────────────────────────

function LinkGroup({
  name, skeleton, childrenOf, selected, onSelect, apiBase, transformMode,
  showLandmarks, linkLandmarks,
}: {
  name: string;
  skeleton: SkeletonState;
  childrenOf: Record<string, string[]>;
  selected: string | null;
  onSelect: (p: string | null) => void;
  apiBase: string;
  transformMode: "translate" | "rotate";
  showLandmarks: boolean;
  linkLandmarks: { name: string; offset: [number, number, number] }[];
}) {
  const [hovered, setHovered] = useState(false);
  const [meshReady, setMeshReady] = useState(false);
  const groupRef = useRef<THREE.Group>(null);
  const meshRef = useRef<THREE.Mesh>(null);

  const xf = skeleton.transforms[name];
  const link = skeleton.links[name];
  const children = childrenOf[name] || [];
  const isSelected = selected === name;

  if (!link?.visible) {
    return (
      <group ref={groupRef}>
        {children.map((c) => (
          <LinkGroup key={c} name={c} skeleton={skeleton} childrenOf={childrenOf}
            selected={selected} onSelect={onSelect} apiBase={apiBase} transformMode={transformMode}
            showLandmarks={showLandmarks} linkLandmarks={linkLandmarks} />
        ))}
      </group>
    );
  }

  const color = isSelected ? "#ff6600" : hovered ? "#44aaff" : "#3399ff";
  const s = isSelected ? 1.5 : hovered ? 1.2 : 1.0;

  const handleDragEnd = async () => {
    if (!groupRef.current) return;
    const p = groupRef.current.position;
    const q = groupRef.current.quaternion;
    try {
      await fetch(`${apiBase}/model/skeleton/transforms/${name}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ translation: [p.x, p.y, p.z], rotation: [q.w, q.x, q.y, q.z] }),
      });
    } catch (_) {}
  };

  const refCb = (node: THREE.Mesh | null) => {
    meshRef.current = node;
    if (node) setMeshReady(true);
  };

  const t = xf?.translation ?? [0, 0, 0];
  const r = xf?.rotation ?? [1, 0, 0, 0];

  return (
    <group ref={groupRef} position={new THREE.Vector3(t[0], t[1], t[2])}
      quaternion={new THREE.Quaternion(r[1], r[2], r[3], r[0])}>

      {isSelected && meshReady && (
        <TransformControls object={meshRef.current!} mode={transformMode} onMouseUp={handleDragEnd} />
      )}

      <Box ref={refCb} args={[0.08 * s, 0.08 * s, 0.08 * s]}
        onPointerOver={(e) => { e.stopPropagation(); setHovered(true); }}
        onPointerOut={() => setHovered(false)}
        onClick={(e) => { e.stopPropagation(); onSelect(isSelected ? null : name); }}>
        <meshStandardMaterial color={color} transparent opacity={0.85} />
      </Box>

      {/* Landmarks attached to this link — rendered inside the link's local frame */}
      {showLandmarks && linkLandmarks.map((lm) => (
        <group key={lm.name} position={new THREE.Vector3(lm.offset[0], lm.offset[1], lm.offset[2])}>
          <LandmarkDot name={lm.name} />
        </group>
      ))}

      {children.map((c) => (
        <LinkGroup key={c} name={c} skeleton={skeleton} childrenOf={childrenOf}
          selected={selected} onSelect={onSelect} apiBase={apiBase} transformMode={transformMode}
          showLandmarks={showLandmarks} linkLandmarks={[]} />
      ))}
    </group>
  );
}
