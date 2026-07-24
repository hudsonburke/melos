/**
 * Canonical Melos types — mirrors melos.core.model exactly.
 *
 * Field names, nesting, and types MUST match the Pydantic schema.
 * This is the single source of truth for the frontend.
 */

export interface JointLimits {
  lower: number;
  upper: number;
}

export interface JointDef {
  joint_type: string;
  axis: number[];
  limits: JointLimits;
  parent_link: string;
  child_link: string;
  default_qpos: number;
}

export interface LinkDef {
  name: string;
  mass: number;
  center_of_mass: number[];
  inertia: number[];
  graphics_file: string;
  visible: boolean;
}

export interface LinkTransform {
  translation: [number, number, number];
  rotation: [number, number, number, number]; // (w, x, y, z)
}

export interface SkeletonState {
  joints: Record<string, JointDef>;
  links: Record<string, LinkDef>;
  transforms: Record<string, LinkTransform>;
  parent_map: Record<string, string>;
  order: string[];
  descendants: Record<string, string[]>;
}

export interface ModelState {
  name: string;
  skeleton: SkeletonState;
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
