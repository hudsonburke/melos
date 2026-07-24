import { useState } from "react";
import type { ModelState } from "../types/schema";

interface Props {
  model: ModelState | null;
  selectedPath: string | null;
  apiBase: string;
  transformMode: "translate" | "rotate";
  onModeChange: (m: "translate" | "rotate") => void;
  showLandmarks: boolean;
  onLandmarkToggle: () => void;
  showSkin: boolean;
  onSkinToggle: () => void;
  onModelReload: () => void;
}

// ── Button / section styles ──────────────────────────────────────────────

const btn: any = (active = false) => ({
  width: "100%",
  padding: "4px 8px",
  marginBottom: 4,
  background: active ? "#ff6600" : "#333",
  color: "#fff",
  border: "1px solid #555",
  borderRadius: 4,
  cursor: "pointer",
  fontSize: 11,
  textAlign: "left" as const,
});

const input: any = {
  width: "100%",
  padding: "3px 6px",
  marginBottom: 4,
  background: "#222",
  color: "#ccc",
  border: "1px solid #555",
  borderRadius: 4,
  fontSize: 11,
  outline: "none",
  boxSizing: "border-box" as const,
};

// ── Main component ───────────────────────────────────────────────────────

export default function ControlPanel(props: Props) {
  const { model, selectedPath, apiBase, transformMode, onModeChange,
          showLandmarks, onLandmarkToggle, showSkin, onSkinToggle, onModelReload } = props;

  const [status, setStatus] = useState<string>("");
  const [scaleFemur, setScaleFemur] = useState("0.50");
  const [scaleTibia, setScaleTibia] = useState("0.44");
  const [scaleMass, setScaleMass] = useState("85");
  const [assemblyName, setAssemblyName] = useState("right_arm_brace");
  const [mjcfOutput, setMjcfOutput] = useState<string>("");

  const flash = (msg: string) => { setStatus(msg); setTimeout(() => setStatus(""), 3000); };

  const api = async (method: string, url: string, body?: any) => {
    try {
      const res = await fetch(`${apiBase}${url}`, body ? {
        method, headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      } : { method });
      if (!res.ok) { flash(`HTTP ${res.status}`); return null; }
      return await res.json();
    } catch (e: any) { flash(e.message); return null; }
  };

  const loadModel = () => api("POST", `/model/load?path=/var/lib/hermes/rerun-importer-osim/test_data/RajagopalData/Rajagopal2015.osim`)
    .then(() => { flash("Loaded Rajagopal2015"); onModelReload(); });

  const importMjcf = () => {
    const p = prompt("MJCF path:", "/var/lib/hermes/myosuite/myosuite/simhive/myo_sim/elbow/myoelbow_1dof6muscles_1dofexo.xml");
    if (p) api("POST", `/model/import/mjcf?path=${encodeURIComponent(p)}`)
      .then((d) => { if (d) { flash(`Imported: ${d.n_cables} cables`); onModelReload(); } });
  };

  const scaleByLengths = () => api("POST", "/model/scale/lengths", {
    target_lengths: { thigh: parseFloat(scaleFemur), shank: parseFloat(scaleTibia) },
    segment_to_link: { thigh: "femur_r", shank: "tibia_r" },
    target_mass: parseFloat(scaleMass),
  }).then((d) => { if (d) { flash(`Scaled: mass ${d.total_mass_after}kg`); onModelReload(); } });

  const scaleByLandmarks = () => api("POST", "/model/scale/landmarks", {
    subject_measurements: { thigh_r: parseFloat(scaleFemur), shank_r: parseFloat(scaleTibia) },
    target_mass: parseFloat(scaleMass),
  }).then((d) => { if (d) { flash(`Landmark scaled`); onModelReload(); } });

  const applyAssembly = () => api("POST", "/model/compile/with-assembly", {
    assembly_name: assemblyName,
  }).then((d) => { if (d) { flash(`Assembly applied: ${d.n_bodies} bodies`); onModelReload(); } });

  const compileMjcf = async () => {
    const d = await api("GET", "/model/compile");
    if (d) setMjcfOutput(d.mjcf.slice(0, 3000));
  };

  const downloadMjcf = async () => {
    const d = await api("GET", "/model/compile");
    if (!d) return;
    const blob = new Blob([d.mjcf], { type: "text/xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "melos_model.xml"; a.click();
    URL.revokeObjectURL(url);
    flash("MJCF downloaded");
  };

  if (!model) {
    return (
      <aside className="sidebar">
        <h2>Melos Editor</h2>
        <p>Start the backend, then load a model.</p>
        <p style={{ fontSize: 11, color: "#666", marginTop: 8 }}>
          <code>uvicorn melos.backend.app:app --port 8008</code>
        </p>
        <h3>Load Model</h3>
        <button style={btn()} onClick={loadModel}>📂 Load Rajagopal2015</button>
        <button style={btn()} onClick={importMjcf}>📥 Import MJCF...</button>
        {status && <p style={{ fontSize: 11, color: "#ff0" }}>{status}</p>}
      </aside>
    );
  }

  const skeleton = model.skeleton;

  return (
    <aside className="sidebar" style={{ overflowY: "auto", height: "100vh" }}>
      <h2>Melos Editor</h2>
      <p style={{ marginBottom: 8, color: "#fff", fontSize: 12 }}>{model.name}</p>
      <p style={{ fontSize: 10, color: "#666", marginBottom: 8 }}>
        {Object.keys(skeleton.joints).length}j · {Object.keys(skeleton.links).length}l
      </p>

      {status && <p style={{ fontSize: 11, color: "#0f0", marginBottom: 4 }}>{status}</p>}

      {/* ── Model ───────────────────────────────────────────────────── */}
      <h3>Model</h3>
      <button style={btn()} onClick={loadModel}>📂 OSIM</button>
      <button style={btn()} onClick={importMjcf}>📥 MJCF</button>

      {/* ── Transform ────────────────────────────────────────────────── */}
      <h3>Transform</h3>
      <div style={{ display: "flex", gap: 4, marginBottom: 8 }}>
        {(["translate", "rotate"] as const).map((m) => (
          <button key={m} onClick={() => onModeChange(m)}
            style={{ ...btn(), flex: 1, background: transformMode === m ? "#ff6600" : "#333" }}>
            {m === "translate" ? "↕ Move" : "↻ Rotate"}
          </button>
        ))}
      </div>

      {/* ── Overlays ─────────────────────────────────────────────────── */}
      <h3>Overlays</h3>
      <button style={btn(showLandmarks)} onClick={onLandmarkToggle}>
        {showLandmarks ? "◉" : "○"} Landmarks
      </button>
      <button style={btn(showSkin)} onClick={onSkinToggle}>
        {showSkin ? "◉" : "○"} Skin
      </button>

      {/* ── Scaling ──────────────────────────────────────────────────── */}
      <h3>Scaling</h3>
      <input style={input} placeholder="Femur length (m)" value={scaleFemur}
        onChange={(e) => setScaleFemur(e.target.value)} />
      <input style={input} placeholder="Tibia length (m)" value={scaleTibia}
        onChange={(e) => setScaleTibia(e.target.value)} />
      <input style={input} placeholder="Target mass (kg)" value={scaleMass}
        onChange={(e) => setScaleMass(e.target.value)} />
      <button style={btn()} onClick={scaleByLengths}>📏 Scale by lengths</button>
      <button style={btn()} onClick={scaleByLandmarks}>📍 Scale by landmarks</button>

      {/* ── Assembly ─────────────────────────────────────────────────── */}
      <h3>Assembly</h3>
      <input style={input} placeholder="Assembly name" value={assemblyName}
        onChange={(e) => setAssemblyName(e.target.value)} />
      <button style={btn()} onClick={applyAssembly}>🔧 Apply + compile</button>

      {/* ── MJCF Export ──────────────────────────────────────────────── */}
      <h3>MuJoCo</h3>
      <button style={btn()} onClick={compileMjcf}>🔍 View MJCF</button>
      <button style={btn()} onClick={downloadMjcf}>⬇ Download .xml</button>

      {mjcfOutput && (
        <pre style={{ fontSize: 9, color: "#888", maxHeight: 300, overflowY: "auto",
                      background: "#111", padding: 4, borderRadius: 4, marginTop: 4 }}>
          {mjcfOutput}...
        </pre>
      )}

      {/* ── Selected entity ──────────────────────────────────────────── */}
      {selectedPath && <SelectedInfo path={selectedPath} skeleton={skeleton} />}

      {/* ── Joint list ───────────────────────────────────────────────── */}
      <h3>Joints</h3>
      {Object.entries(skeleton.joints).slice(0, 25).map(([name, joint]) => (
        <div key={name} className="property">
          <span className="label">{name}</span>
          <span className="value">{joint.joint_type}</span>
        </div>
      ))}
      {Object.keys(skeleton.joints).length > 25 && (
        <div className="property"><span className="label">...</span>
          <span className="value">+{Object.keys(skeleton.joints).length - 25} more</span></div>
      )}

      {/* ── Link list ────────────────────────────────────────────────── */}
      <h3>Links</h3>
      {Object.entries(skeleton.links).slice(0, 15).map(([name, link]) => (
        <div key={name} className="property">
          <span className="label">{name}</span>
          <span className="value">{link.mass.toFixed(2)} kg</span>
        </div>
      ))}
    </aside>
  );
}

// ── Selected info ────────────────────────────────────────────────────────

function SelectedInfo({ path, skeleton }: {
  path: string; skeleton: ModelState["skeleton"];
}) {
  const name = path;
  const link = skeleton.links[name];
  const joint = skeleton.joints[name];
  if (link) {
    const wt = skeleton.transforms[name];
    return (<>
      <h3 style={{ color: "#ff6600" }}>🔗 {name}</h3>
      <div className="property"><span className="label">Mass</span><span className="value">{link.mass.toFixed(3)} kg</span></div>
      <div className="property"><span className="label">Mesh</span><span className="value">{link.graphics_file || "—"}</span></div>
      {wt && <div className="property"><span className="label">Pos</span><span className="value">({wt.translation[0].toFixed(3)}, {wt.translation[1].toFixed(3)}, {wt.translation[2].toFixed(3)})</span></div>}
    </>);
  }
  if (joint) {
    return (<>
      <h3 style={{ color: "#44aaff" }}>⚙️ {name}</h3>
      <div className="property"><span className="label">Type</span><span className="value">{joint.joint_type}</span></div>
      <div className="property"><span className="label">Parent</span><span className="value">{joint.parent_link}</span></div>
      <div className="property"><span className="label">Child</span><span className="value">{joint.child_link}</span></div>
      <div className="property"><span className="label">Limits</span><span className="value">[{joint.limits.lower.toFixed(2)}, {joint.limits.upper.toFixed(2)}]</span></div>
    </>);
  }
  return <><h3>Selected: {name}</h3><p style={{ color: "#666" }}>No details</p></>;
}
