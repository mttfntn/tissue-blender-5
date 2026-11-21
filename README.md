# Tissue for Blender 5.3

A fork of [Tissue](https://github.com/alessandro-zomparelli/tissue), the Blender add-on for computational design by Alessandro Zomparelli (Co-de-iT), with extra bug fixes, made for Blender 5.3.

Older Tissue releases don't work properly on Blender 5: on 0.3.71, Tessellate and many other tools fail with `this type doesn't support IDProperties`. Upstream 0.3.76 fixes that error. This fork starts from 0.3.76 and fixes the bugs listed below.

## Compatibility

This version needs **Blender 5.3 or later**: older Blender versions refuse to install it. It was tested on Blender 5.3.0 with the test suite, a sweep of every option and checks in the real interface. Later versions are allowed, but haven't been tested.

## Installation

1. Download the zip from the [latest release](https://github.com/mttfntn/tissue-blender-5/releases/latest).
2. If you already have Tissue, open **Edit > Preferences > Add-ons**, find it and uninstall it. This fork uses the same add-on ID, so the two can't be active together.
3. In the dropdown at the top right of the Add-ons preferences, choose **Install from Disk** and pick the zip.
4. Restart Blender.

To build the zip yourself instead, use Blender's build command on the `tissue` folder:

```
git clone https://github.com/mttfntn/tissue-blender-5.git
blender --command extension build --source-dir tissue-blender-5/tissue --output-dir .
```

## What's in this repository

| Folder or file | Contents |
|---|---|
| [tissue/](tissue) | The add-on itself: everything that goes into the zip |
| [tests/](tests) | The test suite |
| [docs/](docs/README.md) | The user documentation |
| [.github/](.github) | The automatic tests and releases on GitHub |
| [HANDOVER.md](HANDOVER.md), [AGENTS.md](AGENTS.md) | How to work on the code, for people and for AI assistants |

Tissue works without [Numba](https://numba.pydata.org/), but it is faster with it. You can install it from the add-on's preferences.

## What this fork fixes

**Tessellate**
- Component shape keys crashed with Face normals, with Fan fill and Shape Key normals, and with a thickness vertex group
- Patch fill crashed with UV rotation
- Frame fill crashed with 2 or more iterations
- Collection mode gave a traceback when no collection was selected. It now shows a message
- Creases on merged boundaries were written to `crease_edge.001`, which Blender ignores, so they had no effect
- Patch fill crashed on a Base without 4-sided faces, such as a Dual Mesh of hexagons. It now shows a message that suggests Fan, and an existing tessellation stays as it is
- Patch fill crashed on selected faces with more than 4 sides, when using On selected Faces
- The message about modifiers after the last Subdivision was never shown, because Tissue crashed first

**Render Animation**
- The operator always crashed with a `NameError`
- A scene without a camera left the animation handlers removed. It now shows a message before changing anything

**Curves**
- Convert to Curve in Particles mode crashed on an out of range system index, or when the object had no particle systems

**Weight tools**
- Streamlines crashed when run from a script instead of the dialog
- Area, Random, Harmonic and Laplacian crashed in Edit Mode

**Reaction-Diffusion**
- Baking skipped the last frame, and Free Data left it on disk
- Baking an unsaved file from a script could write the cache to the current folder
- Texture Reaction-Diffusion silently did nothing without Numba. It now has a NumPy version, which gives the same result as the Numba one

**Add-on**
- Disabling Tissue left the frame handlers of animated objects and Reaction-Diffusion running (fix from upstream's `b5-dev` branch)

**Cleanup**
- About 1,400 lines of code that was never called were removed: unused functions, two operators that were never registered, branches that could never run and commented-out code
- Small speed-ups: two handlers that did nothing on every frame change, a full copy of the mesh made on every Merge, and exceptions raised on every update are gone
- Every module and the main Tessellate functions now have comments describing them
- The add-on moved into the `tissue` folder, and it now requires Blender 5.3

## Working on the code

[HANDOVER.md](HANDOVER.md) explains how the add-on is organized and how to change, test and release it. [AGENTS.md](AGENTS.md) has the same information for AI coding assistants.

## Tests

[tests/run_tests.py](tests/run_tests.py) runs each Tissue tool on a small scene and checks the result. Run it from the repository folder:

```
blender --background --factory-startup --python-exit-code 1 --python tests/run_tests.py
```

Tissue uses Numba whenever it can find it. To choose which code is tested:

- `TISSUE_TEST_NO_NUMBA=1` blocks Numba, to test the NumPy code
- `TISSUE_TEST_SITE=<folder>` uses the Numba installed in that folder

The suite has 52 tests, on small meshes. They don't cover the Install Numba button or the help links.

## Documentation

The documentation, with video tutorials, is in the [docs](docs/README.md) folder.

## Credits and license

Tissue is created and maintained by [Alessandro Zomparelli](https://github.com/alessandro-zomparelli). All the credit for the add-on goes to him and its contributors. This fork only adds the fixes above.

If you like Tissue, consider supporting Alessandro's work on [Patreon](https://www.patreon.com/alessandrozomparelli).

Tissue is free software, released under the GNU General Public License v3.0 or later. This fork uses the same license: see [LICENSE](LICENSE).
