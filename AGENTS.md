# AGENTS.md

Instructions for AI coding agents working on this repository. For people, the same ground is covered in [HANDOVER.md](HANDOVER.md).

## Project

Blender add-on **Tissue** (computational design tools), forked from https://github.com/alessandro-zomparelli/tissue at 0.3.76, with fixes for Blender 5. Owner of the fork: https://github.com/mttfntn/tissue-blender-5. Current version: see `version` in `blender_manifest.toml`.

- Pure Python, run by Blender's bundled Python (3.13 on Blender 5.3). Depends only on `bpy`, `bmesh`, `mathutils` and NumPy, all bundled with Blender. Numba is optional.
- The add-on is the `tissue/` folder; everything else (tests, docs, CI) is outside it. Distributed as a Blender extension zip built from `tissue/`. `tissue/blender_manifest.toml` is the source of truth for metadata; `_bl_info_fallback` in `tissue/__init__.py` must carry the same version.
- Supports **Blender 5.3 only** (`blender_version_min = "5.3.0"`, no maximum). CI tests 5.3 only.
- License GPL-3.0-or-later. Keep the SPDX headers and the credit to Alessandro Zomparelli.

## Commands

Run from the repository root. `blender` is the Blender executable; on the original machine it is `C:\Program Files\Blender Foundation\Blender 5.3\blender.exe`.

```
# test suite (exit code 1 on failure)
blender --background --factory-startup --python-exit-code 1 --python tests/run_tests.py
# NumPy code paths only: Numba blocked
TISSUE_TEST_NO_NUMBA=1 blender --background --factory-startup --python-exit-code 1 --python tests/run_tests.py
# a specific Numba: folder made with `<blender python> -m pip install --target <folder> numba llvmlite`
TISSUE_TEST_SITE=<folder> blender --background --factory-startup --python-exit-code 1 --python tests/run_tests.py
# build the extension zip
blender --command extension build --source-dir tissue --output-dir .
blender --command extension validate <zip>
```

The suite takes about a minute and has 52 tests. All of them must pass before a commit, both with Numba and with `TISSUE_TEST_NO_NUMBA=1`.

- **Numba is found anyway:** `numba_functions.py` adds the user's Python site folder to `sys.path`. A plain run uses whatever Numba the user installed, so it is not a no-Numba run.
- **Isolate the user's Blender:** for anything that installs extensions, draws the preferences or opens a window, set `BLENDER_USER_RESOURCES` to a scratch folder so the user's real Blender profile is untouched.
- **Never test in the user's open Blender** unless asked: start separate `--background` instances.

## Architecture

All paths below are in `tissue/`.

| File | Role |
|---|---|
| `__init__.py` | `classes` tuple (everything registered), `register` adds PointerProperties on `bpy.types.Object`; `unregister` also removes every handler whose function belongs to the package (`is_tissue_function`) |
| `tessellate_numpy.py` | Tessellate: `tessellate_patch` (algorithm, one iteration), operators `tissue_tessellate` (create) and `tissue_update_tessellate` (rebuild from stored settings), `merge_components`, fill-mode converters, face rotation, `tissue_render_animation`, all Tessellate panels |
| `tissue_properties.py` | `tissue_prop` (`object.tissue`: type, Animatable, Lock), `tissue_tessellate_prop` (`object.tissue_tessellate`), `anim_tissue` frame handler, `store_parameters` (operator → object), `props_to_dict` (object → dict for `tessellate_patch`) |
| `utils.py` | Shared helpers, re-exported everywhere through `from .utils import *`: `convert_object_to_mesh`, `get_patches`, `get_quads`, `np_lerp2`, `calc_thickness`, curves, vertex group I/O, `tissue_time` |
| `numba_functions.py` | `@njit` versions of hot loops, defined only when `bool_numba`. Callers check `'numba' in sys.modules` / `use_numba_tess()`, or whether the name exists, and fall back to NumPy |
| `weight_tools.py`, `weight_reaction_diffusion.py`, `texture_reaction_diffusion.py`, `contour_curves.py`, `curves_tools.py`, `polyhedra.py`, `dual_mesh.py`, `lattice.py`, `material_tools.py`, `uv_to_mesh.py` | One family of tools each |
| `config.py`, `utils_pip.py` | AddonPreferences (`bl_idname = __package__`), Install Numba |

### Tessellate data flow

1. `tissue_tessellate.execute` creates or reuses the output object and calls `store_parameters`, then runs `bpy.ops.object.tissue_update_tessellate()`.
2. `tissue_update_tessellate.execute` reads `ob.tissue_tessellate`, validates Base and Component, then calls `tessellate_patch(props_to_dict(ob))` once per iteration.
3. `tessellate_patch` returns either a list of temporary objects (named `_tissue_tmp_*`) or an error code string. Error codes are mapped to messages in the `errors` dict in `tissue_update_tessellate.execute`. To add a failure mode, return a new code and add it to that dict.
4. The results are joined, merged (`merge_components`), and the new mesh replaces `ob.data`, keeping its name.
- Except in Patch mode, `ob.data.clear_geometry()` runs before tessellating, for speed. In Patch mode `tessellate_patch` clears it only after its checks pass, so a refused Patch update keeps the old mesh.
- Settings have `update=anim_tessellate_active`, which refreshes the tessellation on every change. Set `bool_hold = True` while changing several settings, then set it back to `False`.

## Rules and pitfalls

- **Star imports:** most modules do `from .utils import *`, and some do `from numpy import *` or `from math import *`. Builtins such as `any`, `min`, `max`, `sum` and `round` can be NumPy's versions: `any(generator)` is always true there. Use lists, `builtins` or `np.` explicitly.
- **Before removing or renaming any name,** grep the whole repository: names travel through the star imports. Many "unused" imports are left in place on purpose for that reason.
- **No docstrings on Operator or Panel classes:** Blender uses an operator class's docstring as its tooltip. Use `#` comments there. Functions and modules have docstrings.
- **Blender 5 API:** `bpy_struct.keys()` and dict-style access to RNA properties are gone ("this type doesn't support IDProperties"). Use the `.attributes` API for mesh data. `corner_normals` replaces `calc_normals_split`, and `me.update()` recalculates normals. Look up enum values from `bl_rna` rather than hard-coding new ones.
- **Errors for the user:** `self.report({'ERROR'}, ...)` and `return {'CANCELLED'}`, never an uncaught exception. Tests use `check_reports_error` to make sure a message is shown instead of a traceback.
- **Restore on error:** after a failed operation, restore the visibility of Base and Component, the active object, shape key values and modifier visibility, and remove `_tissue_tmp_*` objects (`remove_temp_objects`).
- **Handlers:** tools add `frame_change_post` / `render_init` handlers only while in use (`anim_tissue`, `reaction_diffusion_scene`, `tex_rd_scene`, `turn_off_animatable`). `register` adds none. Handlers are found and removed by function name or module; keep handler functions at module level in this package.
- **Tests:** add a test for every fix in `tests/run_tests.py`, marked with `@test`. Keep `disable_and_enable` as the last test, because it disables the add-on. Prefer checks on results (face counts, attribute values, weights) over checking only that an operator returns `{'FINISHED'}`.

## Verification beyond the suite

The fixes in this fork were also checked with scripts that are not in the repository:

- a sweep that sets every option of every tool to each of its values, about 1,800 cases, comparing results before and after a change. No case may raise a traceback, and every result must match unless the change was meant to alter it
- a real window started with `--enable-event-simulate`, which draws every panel, opens every operator dialog and runs Render Animation

For larger changes, write the equivalent: a static unit test is not enough to show that behaviour did not change.

## Repository and git

- `main` is the fork's branch, published to https://github.com/mttfntn/tissue-blender-5. In a fresh clone that remote is `origin`. Upstream is https://github.com/alessandro-zomparelli/tissue (`master`, and fixes that sometimes wait on `b5-dev`).
- `.github/workflows/tests.yml` runs one job on Linux: tests on Blender 5.3, builds and validates the zip, uploads it as an artifact kept 3 days (`continue-on-error`, the account's artifact storage can be full), and on a `v*` tag publishes a GitHub release with `gh release create --notes-from-tag`. The tag must equal `v` + the manifest version.
- `.github/find-blender.sh <version>` prints the Blender download URL. download.blender.org answers 403 to some GitHub runners, so it falls back to official mirrors; don't replace it with a single direct URL.
- The zip contains only `tissue/` (`paths_exclude_pattern` drops `__pycache__` and zips). `tissue/LICENSE` is a copy of the root `LICENSE`, so the zip carries the license; keep them identical.

## Release checklist

1. Bump the version in `tissue/blender_manifest.toml` and `tissue/__init__.py` (`_bl_info_fallback`).
2. Update the README: the fix list, the test count.
3. Run the suite with and without Numba.
4. Build, `validate`, and install the zip in an isolated profile (`BLENDER_USER_RESOURCES`), then tessellate once.
5. Commit and push `main`, wait for the run to pass.
6. `git tag -a v<version> -m "<release notes>"` and push the tag: the workflow publishes the release.

## Original workspace (optional)

The fork was developed in a folder that also held `.mcp.json`, which configures the Blender MCP server (`uvx blender-mcp`). It lets an assistant drive a running Blender. The matching Blender add-on is installed with `uvx mcp-for-blender install-addon`. None of this is needed to work on the add-on.
