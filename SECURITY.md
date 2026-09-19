# Security policy

## Scope

GhostSweep is a local, offline file-management CLI. It reads JSONL files below the
explicit root supplied by the user and can move matching files to an explicit external
directory. It does not send files, call a model, or execute commands from session data.

## Safe use

- Review the `plan` JSON before running `quarantine`.
- Use a destination on a volume you control and keep the receipt.
- Do not point `--root` at an entire drive or an untrusted mounted directory.
- Treat session files and receipts as potentially sensitive; they can contain prompts,
  titles, paths, or identifiers.

## Reporting a vulnerability

Please do not disclose a path traversal, unintended overwrite, data-exfiltration, or
command-execution issue in a public issue first. Use GitHub's private vulnerability
reporting for this repository if enabled, or contact the repository owner through the
profile email. Include a minimal reproduction, the operating system, Python version,
and the exact command. Do not include private session contents.
