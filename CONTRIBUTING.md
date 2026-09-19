# Contributing to GhostSweep

Thanks for helping make local AI tooling safer.

1. Open an issue describing the user pain and the smallest reproducible case.
2. Keep the tool offline and standard-library-only at runtime unless the change has a
   clear security and maintenance reason.
3. Add a failing test before implementation for behavior changes.
4. Run the full local checks before opening a pull request:

   ```bash
   python -m pytest -q
   ruff check src tests
   mypy src
   python -m build
   pip-audit --path dist
   git diff --check
   ```

5. Never include real AI session contents, credentials, or personal paths in fixtures.

Behavior that changes file selection or file movement needs a security review and a
recovery test.
