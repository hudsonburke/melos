# Third-party runtime assets used by Melos

This directory contains the minimal pinned asset snapshot required by the active Melos example workflow and Blender add-on packaging.

Included subsets:
- `skin/`
  - `SOMA_neutral.npz`
  - `MHR/mhr_model_lod1.pt`
  - `MHR/base_body_lod1.obj`
  - `MHR/SOMA_wrap_lod1.obj`
  - upstream license / attribution files from SOMA-X
- `myofullbody/`
  - the minimal MuscleMimic model subtree required by the example MuJoCo import workflow
  - upstream license / notice files

These files are vendored snapshots, not submodules.
The upstream codebases themselves are not required inside this repository for the active runtime path.
