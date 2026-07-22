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
}

export default function ControlPanel({ model, selectedPath, apiBase, transformMode, onModeChange, showLandmarks, onLandmarkToggle, showSkin, onSkinToggle }: Props) {
  if (!model) {
    return (
      <aside className="sidebar">
        <h2>Melos Editor</h2>
        <p>No model loaded.</p>
        <p style={{ fontSize: 11, color: "#666", marginTop: 8 }}>
          Start the backend:{" "}
          <code style={{ color: "#888" }}>uvicorn melos.backend.app:app</code>
        </p>
      </aside>
    );
  }

  const skeleton = model.skeleton;

  return (
    <aside className="sidebar">
      <h2>Melos Editor</h2>
      <p style={{ marginBottom: 12, color: "#fff" }}>{model.name}</p>

      {/* Stats */}
      <h3>Model</h3>
      <div className="property">
        <span className="label">Joints</span>
        <span className="value">{Object.keys(skeleton.joints).length}</span>
      </div>
      <div className="property">
        <span className="label">Links</span>
        <span className="value">{Object.keys(skeleton.links).length}</span>
      </div>

      {/* Transform mode toggle */}
      <h3>Transform</h3>
      <div style={{ display: "flex", gap: 4, marginBottom: 8 }}>
        {(["translate", "rotate"] as const).map((mode) => (
          <button
            key={mode}
            onClick={() => onModeChange(mode)}
            style={{
              flex: 1,
              padding: "4px 8px",
              background: transformMode === mode ? "#ff6600" : "#333",
              color: "#fff",
              border: "1px solid #555",
              borderRadius: 4,
              cursor: "pointer",
              fontSize: 12,
              textTransform: "capitalize",
            }}
          >
            {mode === "translate" ? "↕ Move" : "↻ Rotate"}
          </button>
        ))}
      </div>

      {/* Landmark toggle */}
      <h3>Overlays</h3>
      <button
        onClick={onLandmarkToggle}
        style={{
          width: "100%",
          padding: "4px 8px",
          marginBottom: 8,
          background: showLandmarks ? "#44aaff" : "#333",
          color: "#fff",
          border: "1px solid #555",
          borderRadius: 4,
          cursor: "pointer",
          fontSize: 12,
          textAlign: "left",
        }}
      >
        {showLandmarks ? "◉" : "○"} Landmarks
      </button>
      <button
        onClick={onSkinToggle}
        style={{
          width: "100%",
          padding: "4px 8px",
          marginBottom: 8,
          background: showSkin ? "#ff6644" : "#333",
          color: "#fff",
          border: "1px solid #555",
          borderRadius: 4,
          cursor: "pointer",
          fontSize: 12,
          textAlign: "left",
        }}
      >
        {showSkin ? "◉" : "○"} Skin (18K verts)
      </button>

      {/* Selected entity details */}
      {selectedPath && (
        <SelectedInfo path={selectedPath} skeleton={skeleton} apiBase={apiBase} />
      )}

      {/* Joint list */}
      <h3>Joints</h3>
      {Object.entries(skeleton.joints).slice(0, 20).map(([name, joint]) => (
        <div key={name} className="property">
          <span className="label">{name}</span>
          <span className="value">{joint.joint_type}</span>
        </div>
      ))}
      {Object.keys(skeleton.joints).length > 20 && (
        <div className="property">
          <span className="label">...</span>
          <span className="value">+{Object.keys(skeleton.joints).length - 20} more</span>
        </div>
      )}

      {/* Link list */}
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

function SelectedInfo({
  path,
  skeleton,
  apiBase,
}: {
  path: string;
  skeleton: ModelState["skeleton"];
  apiBase: string;
}) {
  // Path is a link name (set by onClick in Scene)
  const name = path;
  const link = skeleton.links[name];
  const joint = skeleton.joints[name];

  // Check if it's a link
  if (link) {
    const wt = skeleton.transforms[name];
    return (
      <>
        <h3 style={{ color: "#ff6600" }}>🔗 {name}</h3>
        <div className="property">
          <span className="label">Mass</span>
          <span className="value">{link.mass.toFixed(3)} kg</span>
        </div>
        <div className="property">
          <span className="label">Mesh</span>
          <span className="value">{link.graphics_file || "—"}</span>
        </div>
        {wt && (
          <>
            <div className="property">
              <span className="label">Position</span>
              <span className="value">
                ({wt.translation[0].toFixed(3)}, {wt.translation[1].toFixed(3)}, {wt.translation[2].toFixed(3)})
              </span>
            </div>
            {/* Inline transform editor placeholder */}
            <button
              style={{
                marginTop: 8,
                padding: "4px 12px",
                background: "#333",
                color: "#ccc",
                border: "1px solid #555",
                borderRadius: 4,
                cursor: "pointer",
                fontSize: 12,
              }}
              onClick={() => {
                // TODO: open transform controls / gizmo mode
                console.log("Edit transform for", name, apiBase);
              }}
            >
              ✏️ Edit Transform
            </button>
          </>
        )}
      </>
    );
  }

  // Check if it's a joint
  if (joint) {
    return (
      <>
        <h3 style={{ color: "#44aaff" }}>⚙️ {name}</h3>
        <div className="property">
          <span className="label">Type</span>
          <span className="value">{joint.joint_type}</span>
        </div>
        <div className="property">
          <span className="label">Parent</span>
          <span className="value">{joint.parent_link}</span>
        </div>
        <div className="property">
          <span className="label">Child</span>
          <span className="value">{joint.child_link}</span>
        </div>
        <div className="property">
          <span className="label">Limits</span>
          <span className="value">
            [{joint.limits.lower.toFixed(2)}, {joint.limits.upper.toFixed(2)}]
          </span>
        </div>
      </>
    );
  }

  return (
    <>
      <h3>Selected: {name}</h3>
      <p style={{ color: "#666" }}>No details available</p>
    </>
  );
}
