from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .core import GhostSweepError, make_plan, quarantine_from_plan, restore_from_receipt, scan_root


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ghostsweep",
        description="Find empty AI coding sessions and reversibly quarantine them.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    scan = commands.add_parser("scan", help="read-only scan for title-only sessions")
    scan.add_argument(
        "--root", type=Path, required=True, help="explicit session directory to inspect"
    )
    scan.add_argument("--format", choices=("text", "json"), default="text")

    plan = commands.add_parser("plan", help="write a reviewable, read-only quarantine plan")
    plan.add_argument(
        "--root", type=Path, required=True, help="explicit session directory to inspect"
    )
    plan.add_argument("--output", type=Path, required=True, help="new JSON plan path")

    quarantine = commands.add_parser("quarantine", help="move planned files outside the scan root")
    quarantine.add_argument("--plan", type=Path, required=True)
    quarantine.add_argument("--destination", type=Path, required=True)
    quarantine.add_argument("--receipt", type=Path, required=True)

    restore = commands.add_parser("restore", help="restore files from a quarantine receipt")
    restore.add_argument("--receipt", type=Path, required=True)
    return parser


def _print_scan(root: Path, output_format: str) -> None:
    report = scan_root(root)
    if output_format == "json":
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
        return
    print(f"Root: {report.root}")
    print(f"Ghost sessions: {len(report.ghosts)}")
    for ghost in report.ghosts:
        title = ghost.title or "(untitled)"
        print(f"- {ghost.path} | {title} | {ghost.bytes} bytes | sha256 {ghost.sha256[:12]}...")
    if report.skipped:
        print(f"Skipped: {len(report.skipped)}")
        for issue in report.skipped:
            print(f"- {issue.path}: {issue.reason}")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "scan":
            _print_scan(args.root, args.format)
        elif args.command == "plan":
            payload = make_plan(args.root)
            if args.output.exists():
                raise GhostSweepError(f"refusing to overwrite existing file: {args.output}")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            entries = payload.get("entries")
            count = len(entries) if isinstance(entries, list) else 0
            print(f"Plan written: {args.output} ({count} candidates)")
        elif args.command == "quarantine":
            payload = quarantine_from_plan(args.plan, args.destination, args.receipt)
            entries = payload.get("entries")
            count = len(entries) if isinstance(entries, list) else 0
            print(f"Quarantined {count} session(s); receipt: {args.receipt}")
        elif args.command == "restore":
            payload = restore_from_receipt(args.receipt)
            entries = payload.get("entries")
            count = len(entries) if isinstance(entries, list) else 0
            print(f"Restored {count} session(s); receipt: {args.receipt}")
        else:
            raise GhostSweepError("unknown command")
    except GhostSweepError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
