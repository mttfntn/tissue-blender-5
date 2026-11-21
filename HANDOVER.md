# Handover

This guide is for anyone who wants to change this fork of Tissue. It explains how the add-on is organized, how to test a change and how to make a new release. To install the add-on and see what this fork fixes, read the [README](README.md).

## In short

- Tissue is a Blender add-on written in Python. There's nothing to compile: Blender runs the `.py` files directly.
- This repository is a fork of [Alessandro Zomparelli's Tissue](https://github.com/alessandro-zomparelli/tissue), version 0.3.76, with bug fixes for Blender 5.
- Every change is checked with [tests/run_tests.py](tests/run_tests.py), which runs inside Blender. Run it before every commit.
- The add-on is in the `tissue/` folder. It's distributed as a zip file built from that folder with Blender's own `extension build` command, and GitHub publishes it as a release.

## What you need

- **Blender 5.3**, which this version requires.
- **Git**, to get the code and publish changes.
- A text editor. [VS Code](https://code.visualstudio.com/) with the Python extension works well.
- Optional: **[Numba](https://numba.pydata.org/)**, a Python package that makes Tissue faster. Tissue can install it from its preferences. Without it, Tissue uses slower NumPy code that gives the same results.

## How the code is organized

The add-on is in the `tissue/` folder, with each tool in its own file. Every file starts with a short description of what it contains.

| File | What it contains |
|---|---|
| `__init__.py` | Entry point: the list of every class Blender registers, and the settings Tissue adds to every object |
| `tessellate_numpy.py` | Tessellate, the main tool, with its operators and panels |
| `tissue_properties.py` | Settings stored on objects, and the handler that updates animated Tissue objects |
| `utils.py` | Helpers shared by all tools: mesh conversion, NumPy access to mesh data, math |
| `numba_functions.py` | Faster versions of the heaviest loops, used only when Numba is installed |
| `weight_tools.py` | Vertex group tools: Formula, Curvature, Laplacian, Streamlines, conversions... |
| `weight_reaction_diffusion.py` | Reaction-Diffusion on vertex groups |
| `texture_reaction_diffusion.py` | Reaction-Diffusion on images |
| `contour_curves.py` | Contour Curves |
| `curves_tools.py` | Convert to Curve |
| `polyhedra.py` | Polyhedral Wireframe |
| `dual_mesh.py`, `lattice.py`, `material_tools.py`, `uv_to_mesh.py` | The smaller tools |
| `config.py`, `utils_pip.py` | Add-on preferences and the Install Numba button |
| `blender_manifest.toml` | Name, version, minimum Blender version and build settings of the extension |

Outside that folder:

| File | What it contains |
|---|---|
| `tests/run_tests.py` | The tests |
| `docs/` | The user documentation, with images |
| `.github/workflows/tests.yml` | The tests, build and releases that GitHub runs |
| `.github/find-blender.sh` | Finds the Blender download for GitHub, falling back to mirrors |
| `.github/ISSUE_TEMPLATE/`, `.github/pull_request_template.md` | The forms for new issues and the checklist for pull requests |
| `CONTRIBUTING.md`, `SECURITY.md` | How to report problems, contribute, and report security problems privately |

### How Tessellate works

Tessellate copies a **Component** onto every face of a **Base** mesh (called the generator in the code).

1. The **Tessellate** button runs `tissue_tessellate`. It creates the new object and stores every setting on it, in `object.tissue_tessellate`.
2. It then calls `tissue_update_tessellate`, the **Refresh** operator. Refresh reads the settings back from the object, so a tessellation can be rebuilt at any time.
3. Refresh runs `tessellate_patch` once per iteration. That function prepares the Base for the chosen Fill Mode, maps the Component onto every face and returns the new geometry.
4. Refresh then merges the result if Merge is on and puts the new mesh into the object.

Changing a setting in the panel runs Refresh automatically, through the `update=` functions of the settings in `tissue_properties.py`.

## Making a change

1. Edit the `.py` files in `tissue/`.
2. To try the change in Blender, either:
   - build and install the zip, as described in [Making a release](#making-a-release), or
   - copy or link the `tissue/` folder into Blender's add-ons folder, then restart Blender.
3. Run the tests and check they all pass.
4. Add a test for the bug you fixed or the feature you added. Each test is a function marked with `@test`. It builds a small scene, runs one tool and checks the result.
5. Add a line to the list of fixes in the README.

### Running the tests

From the repository folder:

```
blender --background --factory-startup --python-exit-code 1 --python tests/run_tests.py
```

On Windows, write Blender's full path, for example `"C:\Program Files\Blender Foundation\Blender 5.3\blender.exe"`.

The last line says how many tests passed. Tissue uses Numba whenever it can find it, so Numba and NumPy are tested separately:

- with `TISSUE_TEST_NO_NUMBA=1` set, Numba is blocked and the NumPy code is tested
- with `TISSUE_TEST_SITE` set to a folder containing Numba, that Numba is used

When you change Tessellate or anything that both versions use, run the tests both ways.

GitHub also runs the tests on Blender 5.3 and builds the zip whenever you push. The results are in the **Actions** tab of the repository.

## Making a release

GitHub builds and publishes a release by itself when you push a version tag.

1. Raise the version in two places in `tissue/`: `version` in `blender_manifest.toml`, and `"version"` in `_bl_info_fallback` in `__init__.py`.
2. Update the README: the list of fixes and the number of tests. The badges at the top update by themselves, so don't write a version in them.
3. Run the tests, then commit and push.
4. Make a tag named after the new version, with the release notes as its message, and push it:

```
git tag -a v0.3.81 -m "What changed in this version"
git push origin v0.3.81
```

GitHub then runs the tests, builds the zip and publishes it as a release, with the tag's message as the notes. The release stops with an error if the tag doesn't match the version in the manifest. The release appears in the **Releases** section of the repository.

The workflow also updates the **download size** badge in the README. shields.io can't read the size of a release file directly, so the workflow writes it into a small file, `release-size.json`, and puts it alone on a separate branch called `badges`, replacing what was there. The badge reads that file. Don't delete the `badges` branch, and don't work on it: the tests don't run there.

GitHub doesn't keep the zip of ordinary pushes (no "artifacts"): the storage for them is shared by every repository of the account and can fill up. Releases carry the zip; to try a commit, build it yourself as shown below.

To build the zip on your computer instead, run this from the repository folder:

```
blender --command extension build --source-dir tissue --output-dir .
```

The zip contains only the `tissue/` folder.

## Getting updates from the original Tissue

Alessandro Zomparelli keeps developing Tissue. To bring his changes into this fork:

```
git remote add upstream https://github.com/alessandro-zomparelli/tissue.git
git fetch upstream
git merge upstream/master
```

His files are at the top level of his repository, while here they are in `tissue/`. Git usually follows the move by itself when merging; if it doesn't, merge with `git merge -X find-renames=40% upstream/master`. Expect conflicts in the files this fork changed, mostly `tessellate_numpy.py`, `utils.py` and `weight_tools.py`, and run the tests after merging. Some of his work happens on other branches first, such as `b5-dev`.

## Things to know

- **Shared names:** most files start with `from .utils import *`, so a name defined in one file can be visible in many others. Before removing or renaming anything, search the whole repository for it.
- **`any`, `min`, `max` and similar:** some files import all of NumPy with `from numpy import *`, so these names may be NumPy's versions, which behave differently. For example, `any()` on a generator is always true. Use lists or `np.` explicitly.
- **Operator tooltips:** in Blender, an operator class's docstring becomes its tooltip, so describe operator classes with `#` comments, not docstrings.
- **Errors:** report problems with `self.report({'ERROR'}, "...")` and return `{'CANCELLED'}`. Inside `tessellate_patch`, return an error code string instead, which Refresh turns into the message shown in the panel.
- **Blender versions:** this version requires Blender 5.3 (`blender_version_min` in the manifest). Check changes against the [Blender Python API documentation](https://docs.blender.org/api/current/) for that version. Older Tissue releases broke on Blender 5 because the API changed.

## Known limits

- Patch fill only works on 4-sided faces. For hexagons, such as a Dual Mesh, use Fan fill with a 60° slice of the shape as the Component.
- If Patch fill runs several iterations and an error only appears after the first one, the existing tessellation is emptied. Refresh with valid settings rebuilds it.
- Some code is always used because of a hard-coded `or True`, in `lattice.py` and in `convert_to_frame`. It works, but the conditions could be simplified.
