# Tissue for Blender 5

A fork of [Tissue](https://github.com/alessandro-zomparelli/tissue), the Blender add-on for computational design by Alessandro Zomparelli (Co-de-iT), with extra bug fixes, tested on Blender 5.3 beta.

Older Tissue releases don't work properly on Blender 5: on 0.3.71, Tessellate and many other tools fail with `this type doesn't support IDProperties`. Upstream 0.3.76 fixes that error. This fork starts from 0.3.76 and fixes the bugs listed below.

## Compatibility

| Blender | Status |
|---|---|
| 5.3.0 beta (build `ecaf39c37b28`) | Test suite, full option sweep and real interface checks |
| 5.2.2 LTS | Test suite |
| 4.5 to 5.1 | Should work (the manifest allows 4.5 or later), not tested by hand. GitHub Actions runs the tests on them |

Blender 5.3 is still in beta, so a later build could change its API.

## Installation

The add-on is installed from a zip file, which you can build from this repository with Blender:

```
git clone https://github.com/mttfntn/tissue-blender-5.git
blender --command extension build --source-dir tissue-blender-5 --output-dir .
```

This creates `tissue-0.3.77.zip`. Then in Blender:

1. If you already have Tissue, open **Edit > Preferences > Add-ons**, find it and uninstall it. This fork uses the same add-on ID, so the two can't be active together.
2. In the dropdown at the top right of the Add-ons preferences, choose **Install from Disk** and pick the zip.
3. Restart Blender.

Tissue works without [Numba](https://numba.pydata.org/), but it is faster with it. You can install it from the add-on's preferences.

## What this fork fixes

**Tessellate**
- Component shape keys crashed with Face normals, with Fan fill and Shape Key normals, and with a thickness vertex group
- Patch fill crashed with UV rotation
- Frame fill crashed with 2 or more iterations
- Collection mode gave a traceback when no collection was selected. It now shows a message
- Creases on merged boundaries were written to `crease_edge.001`, which Blender ignores, so they had no effect

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

## Tests

[tests/run_tests.py](tests/run_tests.py) runs each Tissue tool on a small scene and checks the result:

```
blender --background --factory-startup --python-exit-code 1 --python tests/run_tests.py
```

Tissue uses Numba whenever it can find it. To choose which code is tested:

- `TISSUE_TEST_NO_NUMBA=1` blocks Numba, to test the NumPy code
- `TISSUE_TEST_SITE=<folder>` uses the Numba installed in that folder

The suite has 46 tests, on small meshes. They don't cover the Install Numba button or the help links.

## Documentation

The documentation, with video tutorials, is in the [docs](docs/README.md) folder.

## Credits and license

Tissue is created and maintained by [Alessandro Zomparelli](https://github.com/alessandro-zomparelli). All the credit for the add-on goes to him and its contributors. This fork only adds the fixes above.

If you like Tissue, consider supporting Alessandro's work on [Patreon](https://www.patreon.com/alessandrozomparelli).

Tissue is free software, released under the [GNU General Public License v3.0 or later](https://www.gnu.org/licenses/gpl-3.0.html). This fork uses the same license.
