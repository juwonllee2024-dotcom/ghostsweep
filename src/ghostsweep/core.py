from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn, cast

MAX_FILE_BYTES = 2_000_000
CONVERSATION_TYPES = {"user", "assistant", "system"}
TITLE_TYPES = {"ai-title", "title"}


class GhostSweepError(Exception):
    """A safe, user-actionable GhostSweep error."""


class _SkipFile(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class GhostSession:
    path: str
    session_id: str | None
    title: str | None
    bytes: int
    sha256: str
    reason: str

    def as_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "sessionId": self.session_id,
            "title": self.title,
            "bytes": self.bytes,
            "sha256": self.sha256,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ScanIssue:
    path: str
    reason: str

    def as_dict(self) -> dict[str, str]:
        return {"path": self.path, "reason": self.reason}


@dataclass(frozen=True)
class ScanReport:
    root: Path
    ghosts: tuple[GhostSession, ...]
    skipped: tuple[ScanIssue, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "version": 1,
            "root": str(self.root),
            "ghosts": [ghost.as_dict() for ghost in self.ghosts],
            "skipped": [issue.as_dict() for issue in self.skipped],
        }


def _fail(message: str) -> NoReturn:
    raise GhostSweepError(message)


def _as_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _has_symlink_ancestor(path: Path, root: Path) -> bool:
    current = path.parent
    while current != root:
        if current.is_symlink():
            return True
        current = current.parent
    return False


def _relative_path(root: Path, raw_path: object) -> Path:
    if not isinstance(raw_path, str) or not raw_path:
        _fail("plan entry has no relative path")
    relative = Path(raw_path)
    if relative.is_absolute() or ".." in relative.parts:
        _fail(f"unsafe relative path in plan: {raw_path}")
    return relative


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 128), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_events(path: Path) -> list[dict[str, object]]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise _SkipFile(f"read failed: {exc}") from exc
    if len(data) > MAX_FILE_BYTES:
        raise _SkipFile(f"larger than safety limit ({MAX_FILE_BYTES} bytes)")

    events: list[dict[str, object]] = []
    for line_number, raw_line in enumerate(data.splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            decoded = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise _SkipFile(f"invalid JSON on line {line_number}") from exc
        if not isinstance(decoded, dict):
            raise _SkipFile(f"line {line_number} is not a JSON object")
        events.append(cast(dict[str, object], decoded))
    return events


def _event_type(event: Mapping[str, object]) -> str | None:
    return _as_string(event.get("type")) or _as_string(event.get("role"))


def _title_event(events: list[dict[str, object]]) -> tuple[str | None, str | None] | None:
    for event in events:
        event_type = _event_type(event)
        if event_type not in TITLE_TYPES:
            continue
        session_id = (
            _as_string(event.get("sessionId"))
            or _as_string(event.get("session_id"))
            or _as_string(event.get("id"))
        )
        title = _as_string(event.get("title")) or _as_string(event.get("name"))
        return session_id, title
    return None


def scan_root(root: Path) -> ScanReport:
    resolved_root = root.expanduser().resolve()
    if not resolved_root.exists() or not resolved_root.is_dir():
        _fail(f"scan root is not a directory: {root}")

    ghosts: list[GhostSession] = []
    skipped: list[ScanIssue] = []
    candidates = sorted(resolved_root.rglob("*.jsonl"), key=lambda item: item.as_posix())
    for path in candidates:
        relative = path.relative_to(resolved_root).as_posix()
        if path.is_symlink() or _has_symlink_ancestor(path, resolved_root) or not path.is_file():
            skipped.append(ScanIssue(relative, "symlink or non-file"))
            continue
        try:
            events = _read_events(path)
        except _SkipFile as exc:
            skipped.append(ScanIssue(relative, exc.reason))
            continue
        if not events:
            continue
        title_info = _title_event(events)
        has_conversation = any(_event_type(event) in CONVERSATION_TYPES for event in events)
        if title_info is None or has_conversation:
            continue
        session_id, title = title_info
        stat = path.stat()
        ghosts.append(
            GhostSession(
                path=relative,
                session_id=session_id,
                title=title,
                bytes=stat.st_size,
                sha256=_sha256(path),
                reason="title-only session: no user/assistant/system events",
            )
        )
    return ScanReport(resolved_root, tuple(ghosts), tuple(skipped))


def make_plan(root: Path) -> dict[str, object]:
    report = scan_root(root)
    return {
        "version": 1,
        "root": str(report.root),
        "entries": [ghost.as_dict() for ghost in report.ghosts],
        "skipped": [issue.as_dict() for issue in report.skipped],
    }


def _load_object(path: Path) -> dict[str, object]:
    try:
        decoded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(f"cannot read JSON file {path}: {exc}")
    if not isinstance(decoded, dict):
        _fail(f"JSON file must contain an object: {path}")
    return cast(dict[str, object], decoded)


def _entries(plan: Mapping[str, object]) -> list[dict[str, object]]:
    raw_entries = plan.get("entries")
    if not isinstance(raw_entries, list):
        _fail("plan has no entries list")
    entries: list[dict[str, object]] = []
    for raw_entry in raw_entries:
        if not isinstance(raw_entry, dict):
            _fail("plan entry must be an object")
        entries.append(cast(dict[str, object], raw_entry))
    return entries


def _checked_source(root: Path, entry: Mapping[str, object]) -> tuple[Path, Path]:
    relative = _relative_path(root, entry.get("path"))
    raw_source = root / relative
    if raw_source.is_symlink() or _has_symlink_ancestor(raw_source, root):
        _fail(f"unsafe symlink path in plan: {relative}")
    source = raw_source.resolve()
    if not _inside(source, root) or source == root:
        _fail(f"unsafe source path in plan: {relative}")
    return source, relative


def _verify_entry_file(path: Path, entry: Mapping[str, object], *, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        _fail(f"{label} is missing or is a symlink: {path}")
    expected_size = entry.get("bytes")
    expected_hash = entry.get("sha256")
    if not isinstance(expected_size, int) or not isinstance(expected_hash, str):
        _fail("plan entry is missing bytes or sha256")
    actual_size = path.stat().st_size
    actual_hash = _sha256(path)
    if actual_size != expected_size or actual_hash != expected_hash:
        _fail(f"candidate changed since plan: {path}")


def _write_object(path: Path, payload: Mapping[str, object], *, overwrite: bool = False) -> None:
    if path.exists() and not overwrite:
        _fail(f"refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def quarantine_from_plan(
    plan_path: Path, destination: Path, receipt_path: Path
) -> dict[str, object]:
    plan = _load_object(plan_path)
    root_value = plan.get("root")
    if not isinstance(root_value, str):
        _fail("plan has no root")
    root = Path(root_value).resolve()
    if not root.is_dir():
        _fail(f"plan root is not a directory: {root}")
    resolved_destination = destination.expanduser().resolve()
    if _inside(resolved_destination, root):
        _fail("quarantine destination must be outside the scan root")
    if receipt_path.exists():
        _fail(f"refusing to overwrite existing file: {receipt_path}")

    entries = _entries(plan)
    checked: list[tuple[Path, Path, dict[str, object]]] = []
    for entry in entries:
        source, relative = _checked_source(root, entry)
        _verify_entry_file(source, entry, label="candidate")
        target = (resolved_destination / relative).resolve()
        if not _inside(target, resolved_destination) or target.exists():
            _fail(f"quarantine target already exists or is unsafe: {target}")
        checked.append((source, target, entry))

    receipt_entries = [
        {
            "path": str(relative).replace("\\", "/"),
            "quarantinedPath": str(target),
            "bytes": entry["bytes"],
            "sha256": entry["sha256"],
        }
        for _, target, entry in checked
        for relative in [_relative_path(root, entry.get("path"))]
    ]
    receipt: dict[str, object] = {
        "version": 1,
        "status": "planned",
        "root": str(root),
        "destination": str(resolved_destination),
        "entries": receipt_entries,
    }
    _write_object(receipt_path, receipt)

    moved: list[tuple[Path, Path]] = []
    try:
        for source, target, _ in checked:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))
            moved.append((source, target))
        receipt["status"] = "quarantined"
        _write_object(receipt_path, receipt, overwrite=True)
        return receipt
    except (OSError, GhostSweepError) as exc:
        for source, target in reversed(moved):
            if target.exists() and not source.exists():
                source.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(target), str(source))
        receipt["status"] = "rolled_back"
        _write_object(receipt_path, receipt, overwrite=True)
        raise GhostSweepError(f"quarantine failed and was rolled back: {exc}") from exc


def restore_from_receipt(receipt_path: Path) -> dict[str, object]:
    receipt = _load_object(receipt_path)
    if receipt.get("status") != "quarantined":
        _fail("receipt is not an active quarantine receipt")
    root_value = receipt.get("root")
    destination_value = receipt.get("destination")
    if not isinstance(root_value, str) or not isinstance(destination_value, str):
        _fail("receipt has no root or destination")
    root = Path(root_value).resolve()
    destination = Path(destination_value).resolve()
    if not root.is_dir() or not destination.is_dir():
        _fail("receipt root or destination is missing")

    checked: list[tuple[Path, Path, dict[str, object]]] = []
    for entry in _entries(receipt):
        relative = _relative_path(root, entry.get("path"))
        raw_original = root / relative
        if raw_original.is_symlink() or _has_symlink_ancestor(raw_original, root):
            _fail(f"unsafe symlink path in receipt: {relative}")
        original = raw_original.resolve()
        raw_quarantined = entry.get("quarantinedPath")
        if not isinstance(raw_quarantined, str):
            _fail("receipt entry has no quarantined path")
        quarantined = Path(raw_quarantined).resolve()
        if not _inside(original, root) or not _inside(quarantined, destination):
            _fail("receipt contains an unsafe path")
        if original.exists():
            _fail(f"refusing to overwrite existing original: {original}")
        _verify_entry_file(quarantined, entry, label="quarantined file")
        checked.append((quarantined, original, entry))

    moved: list[tuple[Path, Path]] = []
    try:
        for quarantined, original, _ in checked:
            original.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(quarantined), str(original))
            moved.append((quarantined, original))
        receipt["status"] = "restored"
        _write_object(receipt_path, receipt, overwrite=True)
        return receipt
    except (OSError, GhostSweepError) as exc:
        for quarantined, original in reversed(moved):
            if original.exists() and not quarantined.exists():
                quarantined.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(original), str(quarantined))
        raise GhostSweepError(f"restore failed and was rolled back: {exc}") from exc
