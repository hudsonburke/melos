import { useState, useEffect } from "react";
import Scene from "./components/Scene";
import ControlPanel from "./components/ControlPanel";
import type { ModelState } from "./types/schema";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8008";

export default function App() {
  const [model, setModel] = useState<ModelState | null>(null);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Load model from the Python backend
  useEffect(() => {
    async function loadModel() {
      try {
        // First load the model file on the server
        const loadRes = await fetch(
          `${API_BASE}/model/load?path=/var/lib/hermes/rerun-importer-osim/test_data/RajagopalData/Rajagopal2015.osim`,
          { method: "POST" }
        );
        if (!loadRes.ok) {
          throw new Error(`Load failed: ${loadRes.status}`);
        }

        // Then fetch the model state
        const res = await fetch(`${API_BASE}/model`);
        if (res.ok) {
          const data = await res.json();
          setModel(data);
        } else {
          throw new Error(`Fetch failed: ${res.status}`);
        }
      } catch (e) {
        console.warn("Backend not available, using demo data", e);
        setModel(createDemoModel());
      } finally {
        setLoading(false);
      }
    }
    loadModel();
  }, []);

  return (
    <div className="app-layout">
      <div className="viewport">
        {loading
          ? <div className="loading">Loading model...</div>
          : <Scene model={model} onSelect={setSelectedPath} selected={selectedPath} apiBase={API_BASE} />
        }
      </div>
      <div className="sidebar">
        <ControlPanel
          model={model}
          selectedPath={selectedPath}
          apiBase={API_BASE}
        />
      </div>
    </div>
  );
}

function createDemoModel(): ModelState {
  return {
    name: "Rajagopal2015 (demo)",
    skeleton: {
      joints: {
        ground_pelvis: {
          joint_type: "CustomJoint",
          axis: [0, 0, 1],
          limits: { lower: -1.57, upper: 1.57 },
          parent_link: "ground",
          child_link: "pelvis",
          default_qpos: 0,
        },
        hip_r: {
          joint_type: "CustomJoint",
          axis: [0, 0, 0],
          limits: { lower: -0.52, upper: 2.09 },
          parent_link: "pelvis",
          child_link: "femur_r",
          default_qpos: 0,
        },
        knee_r: {
          joint_type: "CustomJoint",
          axis: [0, 0, 0],
          limits: { lower: 0.0, upper: 2.09 },
          parent_link: "femur_r",
          child_link: "tibia_r",
          default_qpos: 0,
        },
        ankle_r: {
          joint_type: "PinJoint",
          axis: [0, 0, 1],
          limits: { lower: -0.70, upper: 0.52 },
          parent_link: "tibia_r",
          child_link: "talus_r",
          default_qpos: 0,
        },
      },
      links: {
        pelvis: { name: "pelvis", mass: 11.78, center_of_mass: [0, 0, 0], inertia: [0,0,0,0,0,0], graphics_file: "pelvis.vtp", visible: true },
        femur_r: { name: "femur_r", mass: 9.3, center_of_mass: [0, 0, -0.17], inertia: [0,0,0,0,0,0], graphics_file: "femur.vtp", visible: true },
        tibia_r: { name: "tibia_r", mass: 3.71, center_of_mass: [0, 0, -0.18], inertia: [0,0,0,0,0,0], graphics_file: "tibia.vtp", visible: true },
        talus_r: { name: "talus_r", mass: 0.1, center_of_mass: [0, 0, 0], inertia: [0,0,0,0,0,0], graphics_file: "talus.vtp", visible: true },
        ground: { name: "ground", mass: 0, center_of_mass: [0, 0, 0], inertia: [0,0,0,0,0,0], graphics_file: "", visible: false },
      },
      transforms: {
        pelvis: { translation: [0, 0, 0.85], rotation: [1, 0, 0, 0] },
        femur_r: { translation: [0.08, -0.1, -0.07], rotation: [1, 0, 0, 0] },
        tibia_r: { translation: [0, 0, -0.42], rotation: [1, 0, 0, 0] },
        talus_r: { translation: [0.02, 0, -0.4], rotation: [1, 0, 0, 0] },
        ground: { translation: [0, 0, 0], rotation: [1, 0, 0, 0] },
      },
      parent_map: {
        pelvis: "ground",
        femur_r: "pelvis",
        tibia_r: "femur_r",
        talus_r: "tibia_r",
      },
      order: ["ground", "pelvis", "femur_r", "tibia_r", "talus_r"],
      descendants: {
        ground: ["ground", "pelvis", "femur_r", "tibia_r", "talus_r"],
        pelvis: ["pelvis", "femur_r", "tibia_r", "talus_r"],
        femur_r: ["femur_r", "tibia_r", "talus_r"],
        tibia_r: ["tibia_r", "talus_r"],
        talus_r: ["talus_r"],
      },
    },
  };
}
