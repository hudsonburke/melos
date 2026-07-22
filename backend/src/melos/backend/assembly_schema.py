"""JSON Schema contract between Melos and Proteus for exoskeleton part assembly.

This schema defines the resolved output that Melos produces from an assembly
descriptor YAML — it is the zero-coupling protocol between the two packages.
Proteus parsers consume this dict; Melos producers emit it.

Neither package imports the other.  The schema IS the API.

Fields:
  part_type    — Proteus BaseGeometry subclass name (e.g. "Cuff", "ArmBrace")
  id          — unique instance name within the assembly
  parameters  — keyword arguments for the Proteus constructor (in CAD-native
                mm/deg units, converted by Proteus's own unit helpers)
  attachments — mapping from role name (e.g. "proximal", "distal") to the
                resolved landmark position in metres and the link/landmark
                references.  The consuming side uses the world position
                (x, y, z) to place the part.
  measurements — derived subject metrics computed from landmark pairs,
                 in metres.  The consuming side uses these for parameter
                 overrides.
"""

ASSEMBLY_PART_SPEC = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "part_type": {"type": "string"},
        "description": {"type": "string"},
        "parameters": {"type": "object"},
        "attachments": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                    "z": {"type": "number"},
                    "link": {"type": "string"},
                    "offset": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                    },
                    "landmark_name": {"type": "string"},
                },
            },
        },
        "measurements": {
            "type": "object",
            "additionalProperties": {"type": "number"},
        },
    },
    "required": ["id", "part_type", "parameters"],
}

ASSEMBLY_RESOLVED = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "version": {"type": "string"},
        "parts": {
            "type": "array",
            "items": ASSEMBLY_PART_SPEC,
        },
    },
    "required": ["name", "parts"],
}
