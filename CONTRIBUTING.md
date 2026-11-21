# Contributing to Tissue for Blender 5.3

Thanks for helping! Bug reports, ideas and pull requests are all welcome.

## This is not the official Tissue

This repository is a fork of [Tissue](https://github.com/alessandro-zomparelli/tissue), created and maintained by Alessandro Zomparelli. The fork adds bug fixes and targets Blender 5.3. Before you open an issue or a pull request, please check where it belongs:

- **Problems that also happen with the official Tissue, and new tools or larger features:** report them to [the official Tissue](https://github.com/alessandro-zomparelli/tissue/issues). That way every Tissue user gets the fix.
- **Problems that happen only with this fork,** for example with one of the fixes listed in the README, on Blender 5.3, or in the packaging: report them [here](https://github.com/mttfntn/tissue-blender-5/issues/new/choose).

Not sure? Open an issue here and say so.

## Reporting a bug or suggesting a feature

Open an [issue](https://github.com/mttfntn/tissue-blender-5/issues/new/choose) and pick a form:

- **Bug report:** say which Blender version and Tissue version you use, whether Numba is installed, and the steps to reproduce. A small `.blend` file helps most.
- **Feature request:** describe what you're trying to do, not only the solution you have in mind.

First, check whether someone has already opened an issue for the same thing, here or [upstream](https://github.com/alessandro-zomparelli/tissue/issues).

## Changing the code

[HANDOVER.md](HANDOVER.md) explains how the add-on is organized, how to test it, and the pitfalls already found. Read it before a larger change.

1. **Fork** the repository and create a branch for your change.
2. You need **Blender 5.3**, the version this fork requires. The add-on is the `tissue/` folder.
3. Run the tests from the repository folder, in a separate background Blender, never in the one you work in:

   ```
   blender --background --factory-startup --python-exit-code 1 --python tests/run_tests.py
   ```

   The last line says how many tests passed; all of them must pass. Tissue uses Numba whenever it can find it, so if you change Tessellate or shared code, also run the tests with `TISSUE_TEST_NO_NUMBA=1` set, which tests the NumPy code.
4. **If you fix a bug,** add a test marked with `@test` to `tests/run_tests.py` that fails without your fix, and add a line to the list of fixes in the README.
5. **Open a pull request.** The template has a short checklist. GitHub runs the tests on Blender 5.3 for every pull request.

If your fix also applies to the official Tissue, please consider sending it [upstream](https://github.com/alessandro-zomparelli/tissue) as well.

### Style

- Each tool is in its own file in `tissue/`, and every file starts with a short description. Keep new code in the matching file.
- Most files use `from .utils import *`, and some `from numpy import *`: before renaming or removing a name, search the whole repository for it, and use `np.` explicitly for `any`, `min`, `max` and similar.
- **Operator and Panel classes:** use `#` comments, not docstrings, because Blender shows a class's docstring as its tooltip.
- **Errors for the user:** `self.report({'ERROR'}, "...")` and return `{'CANCELLED'}`, never an uncaught exception.
- Keep the license headers and the credit to Alessandro Zomparelli.
- Keep commits small, with messages that explain what changed and how you checked it.

## License

Tissue is GPL-3.0-or-later. By contributing, you agree that your contribution is released under the same license.
