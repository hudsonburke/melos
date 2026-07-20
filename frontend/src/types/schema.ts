/**
 * TypeScript types mirroring the melos.rerun Arrow component schemas.
 *
 * These are the canonical data types that both the Python backend
 * and React frontend share. The Python backend serializes Arrow structs
 * to JSON, and this frontend deserializes them to these types.
 */

/** Canonical joint definition (mirrors JOINT_DEFINITION Arrow struct) */
export interface JointDefinition {
  joint_type: string;
  axis: [number, number, number];
  limits: { lower: number; upper: number };
  parent_link: string;
  child_link: string;
  default_qpos: number;
}

/** Canonical link/body definition (mirrors LINK_DEFINITION Arrow struct) */
export interface LinkDefinition {
  name: string;
  mass: number;
  center_of_mass: [number, number, number];
  inertia: [number, number, number, number, number, number];
  graphics_file: string;
  visible: boolean;
}

/** Spatial transform for a link */
export interface LinkTransform {
  translation: [number, number, number];
  rotation: [number, number, number, number]; // (w, x, y, z)
}

/** Full skeleton state from the backend */
export interface SkeletonState {
  joints: Record<string, JointDefinition>;
  links: Record<string, LinkDefinition>;
  transforms: Record<string, LinkTransform>;
  parent_map: Record<string, string>; // child_name -> parent_name
}

/** Subject measurements */
export interface BodyMeasurement {
  body_mass: number;
  body_height: number;
  segment: string;
  length: number;
  circumference: number;
  width: number;
  depth: number;
}

/** Complete model state returned by the backend */
export interface ModelState {
  name: string;
  skeleton: SkeletonState;
  subject?: BodyMeasurement[];
}
