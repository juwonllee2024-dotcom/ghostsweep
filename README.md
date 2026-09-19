# 👻 GhostSweep

**Find the AI sessions that never actually happened — then move them somewhere safe.**

AI coding tools can leave title-only session files behind after a canceled or interrupted
resume. Those empty entries make history noisy and can make the next resume feel like it
lost context. GhostSweep scans an explicitly chosen JSONL directory, shows a reviewable
plan, and moves only approved matches to an external quarantine folder. Every move has a
hash-checked receipt that can restore the original path.

> **No model. No account. No network. No silent deletion.**

## Why this exists

The [Claude Code phantom-session report](https://github.com/anthropics/claude-code/issues/60390)
describes canceled resumes that create empty session files with only a generated title.
GhostSweep is a narrow safety tool for that failure mode: it is not a session archive,
analytics dashboard, or handoff system.

## Quick start

GhostSweep never guesses a directory. Pass the session directory explicitly.

```bash
python -m pip install .

# 1. Read-only: inspect candidates.
ghostsweep scan --root ./example-sessions

# 2. Read-only: create a manifest you can review or commit.
ghostsweep plan --root ./example-sessions --output ./ghostsweep-plan.json

# 3. After reviewing the plan: move candidates outside the scan root.
ghostsweep quarantine \
  --plan ./ghostsweep-plan.json \
  --destination ./ghostsweep-quarantine \
  --receipt ./ghostsweep-receipt.json

# 4. Undo the move using the receipt.
ghostsweep restore --receipt ./ghostsweep-receipt.json
```

The scanner recognizes a JSONL file as a candidate only when it contains a title event
(`ai-title` or `title`) and no `user`, `assistant`, or `system` event. Invalid, oversized,
or symlinked files are skipped and reported rather than guessed about.

## Safety contract

- **Explicit root:** there is no default home-directory scan.
- **Preview first:** `scan` and `plan` do not mutate files.
- **External destination:** quarantine cannot write inside the scanned root.
- **Hash check:** a file changed after planning is refused.
- **No overwrite:** existing destination, receipt, or restored original files are refused.
- **Reversible:** quarantine is a move, not deletion; restore uses a receipt.
- **Offline:** runtime code uses only the Python standard library.

GhostSweep is intentionally conservative. A skipped file is better than a destructive
guess. The matching rule is a useful MVP, not a claim that every AI tool uses the same
session format.

## Development

```bash
python -m pip install -e .
python -m pip install pytest ruff mypy build pip-audit
python -m pytest -q
ruff check src tests
mypy src
python -m build
```

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and the
[verification record](docs/verification.md).

## License

MIT — see [LICENSE](LICENSE).
