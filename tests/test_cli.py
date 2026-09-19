from __future__ import annotations

import json
from pathlib import Path

import pytest

from ghostsweep.cli import main


def _write_jsonl(path: Path, *events: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")


def test_scan_finds_title_only_session_but_not_real_session(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_jsonl(
        tmp_path / "ghost.jsonl",
        {"type": "ai-title", "sessionId": "ghost-1", "title": "Canceled run"},
    )
    _write_jsonl(
        tmp_path / "real.jsonl",
        {"type": "ai-title", "sessionId": "real-1", "title": "Real run"},
        {"type": "user", "message": "Ship it"},
    )

    assert main(["scan", "--root", str(tmp_path), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert [item["path"] for item in payload["ghosts"]] == ["ghost.jsonl"]
    assert payload["ghosts"][0]["sessionId"] == "ghost-1"


def test_plan_is_explicit_and_read_only(tmp_path: Path) -> None:
    source = tmp_path / "ghost.jsonl"
    _write_jsonl(source, {"type": "ai-title", "sessionId": "ghost-1", "title": "Canceled run"})
    plan = tmp_path / "out" / "plan.json"

    before = source.read_bytes()
    assert main(["plan", "--root", str(tmp_path), "--output", str(plan)]) == 0

    assert source.read_bytes() == before
    payload = json.loads(plan.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert payload["entries"][0]["path"] == "ghost.jsonl"


def test_quarantine_then_restore_is_reversible(tmp_path: Path) -> None:
    source = tmp_path / "sessions" / "ghost.jsonl"
    _write_jsonl(source, {"type": "ai-title", "sessionId": "ghost-1", "title": "Canceled run"})
    plan = tmp_path / "plan.json"
    destination = tmp_path.parent / f"{tmp_path.name}-quarantine"
    receipt = tmp_path / "receipt.json"

    assert main(["plan", "--root", str(tmp_path / "sessions"), "--output", str(plan)]) == 0
    assert (
        main(
            [
                "quarantine",
                "--plan",
                str(plan),
                "--destination",
                str(destination),
                "--receipt",
                str(receipt),
            ]
        )
        == 0
    )
    assert not source.exists()
    quarantined = destination / "ghost.jsonl"
    assert quarantined.exists()

    assert main(["restore", "--receipt", str(receipt)]) == 0
    assert source.exists()
    assert not quarantined.exists()
    assert source.read_text(encoding="utf-8").startswith('{"type": "ai-title"')


def test_quarantine_refuses_changed_candidate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "ghost.jsonl"
    _write_jsonl(source, {"type": "ai-title", "sessionId": "ghost-1", "title": "Canceled run"})
    plan = tmp_path / "plan.json"
    destination = tmp_path.parent / f"{tmp_path.name}-quarantine"
    receipt = tmp_path / "receipt.json"
    assert main(["plan", "--root", str(tmp_path), "--output", str(plan)]) == 0
    source.write_text(source.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    assert (
        main(
            [
                "quarantine",
                "--plan",
                str(plan),
                "--destination",
                str(destination),
                "--receipt",
                str(receipt),
            ]
        )
        == 2
    )
    assert "changed" in capsys.readouterr().err
    assert source.exists()
    assert not receipt.exists()


def test_plan_refuses_destination_inside_scan_root(tmp_path: Path) -> None:
    source = tmp_path / "ghost.jsonl"
    _write_jsonl(source, {"type": "ai-title", "sessionId": "ghost-1", "title": "Canceled run"})
    plan = tmp_path / "plan.json"
    assert main(["plan", "--root", str(tmp_path), "--output", str(plan)]) == 0

    assert (
        main(
            [
                "quarantine",
                "--plan",
                str(plan),
                "--destination",
                str(tmp_path / "inside"),
                "--receipt",
                str(tmp_path / "receipt.json"),
            ]
        )
        == 2
    )
