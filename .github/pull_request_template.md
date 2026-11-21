## What this changes

<!-- What does the pull request do, and why? Link the issue it fixes, e.g. "Fixes #12".
     If the change also applies to the official Tissue, consider sending it upstream too:
     https://github.com/alessandro-zomparelli/tissue -->

## How it was tested

- [ ] `tests/run_tests.py` passes on Blender 5.3 (see CONTRIBUTING.md)
- [ ] For changes to Tessellate or shared code: also passes with `TISSUE_TEST_NO_NUMBA=1`
- [ ] For a bug fix: a new `@test` that fails without the fix
- [ ] Tried by hand in Blender if it touches a panel or a dialog

## Checklist

- [ ] No docstrings on Operator or Panel classes (they become tooltips): `#` comments instead
- [ ] README updated if users will notice the change (the list of fixes, the test count)
