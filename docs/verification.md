# Verification record

This file records commands and evidence for the published build. It intentionally does
not contain real user session content.

## Test-first record

- RED: before implementation, `python -m pytest -q` failed during collection with
  `ModuleNotFoundError: No module named 'ghostsweep'`.
- GREEN: after the minimum implementation, the same test suite passed locally.

## Required checks — local run 2026-09-19

```text
python -m pytest -q             -> 5 passed
ruff format --check .           -> 11 files already formatted
ruff check src tests             -> All checks passed
mypy src                         -> Success: no issues found in 4 source files
python -m build                  -> built sdist and wheel successfully
pip-audit --path dist            -> No known vulnerabilities found
git diff --check                 -> passed; Git reported only CRLF normalization warnings
```

## Real input to result

The checked-in `examples/phantom-session.jsonl` is a synthetic title-only input. The
wheel smoke test installed the built wheel into an isolated temporary virtual environment
and ran `python -m ghostsweep scan --root examples --format json`, producing one candidate:
`phantom-session.jsonl`, session `demo-ghost-1`, 79 bytes, SHA-256
`385fc986bc9f07ff2fa3c1226e756f29f2506686b29673a73eb1a2d8e49897be`. The test suite also
creates an explicit temporary root, produces a plan, quarantines a candidate outside the
root, and restores it from the receipt. No network or model provider is involved.

## Release evidence

Artifact SHA-256 values from the same build:

- `ghostsweep-0.1.0-py3-none-any.whl` —
  `3f286adc32fccf60ceb0ec6f9231534f2946c0d71591cc559e4ba851cc4b5bdb`
- `ghostsweep-0.1.0.tar.gz` —
  `8e97fd98332991c386f7ad6eb7c917b377e62a61c18da6faa1f036cf0ebac176`

The commit, CI run, and release URL are appended after remote verification completes.

## Security review

- Standard Codex Security scan: complete, 0 reportable findings, 16/16 review rows.
- Scan ID: `bf3d755f-8d57-4c73-9d24-95a6d1307656`.
- The scanner warned that the directory changed while the original snapshot was being
  reviewed. The final local checks above were rerun after the symlink-ancestor hardening;
  treat the security report as covering the earlier snapshot plus this documented manual
  review limitation, not as a guarantee for an unchanged final snapshot.
- Daybreak access was not granted; protected scan output may not be displayable. See
  [security access](https://chatgpt.com/cyber).
