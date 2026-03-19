"""Tests for EMLX parsing and full-text search index."""

import json
from pathlib import Path

from apple_mail.cli import cli
from apple_mail.emlx import parse_emlx
from apple_mail.search_index import SearchIndex
from click.testing import CliRunner


def _create_emlx(path: Path, subject: str, sender: str, body: str) -> None:
    """Create a minimal .emlx file for testing."""
    msg = (
        f"From: {sender}\r\n"
        f"Subject: {subject}\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n"
        f"\r\n"
        f"{body}"
    ).encode("utf-8")
    # EMLX format: byte count on first line, then the RFC 2822 message
    content = f"{len(msg)}\n".encode("ascii") + msg
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def test_parse_emlx(tmp_path):
    emlx = tmp_path / "Messages" / "42.emlx"
    _create_emlx(
        emlx, "Test Subject", "alice@example.com", "Hello world this is a test."
    )
    result = parse_emlx(emlx)
    assert result is not None
    assert result["message_id"] == 42
    assert result["subject"] == "Test Subject"
    assert "Hello world" in result["body"]


def test_parse_emlx_partial(tmp_path):
    emlx = tmp_path / "Messages" / "99.partial.emlx"
    _create_emlx(emlx, "Partial", "bob@example.com", "Partial body content.")
    result = parse_emlx(emlx)
    assert result is not None
    assert result["message_id"] == 99


def test_parse_emlx_invalid(tmp_path):
    bad = tmp_path / "bad.emlx"
    bad.write_text("not a valid emlx file")
    result = parse_emlx(bad)
    assert result is None


def test_search_index_build_and_search(tmp_path):
    """Build an index from test EMLX files and search it."""
    mail_dir = tmp_path / "Mail"
    msgs_dir = mail_dir / "account" / "INBOX.mbox" / "uuid" / "Data" / "Messages"

    _create_emlx(
        msgs_dir / "1.emlx",
        "Deposition Notice",
        "lawyer@firm.com",
        "Your deposition is scheduled for April 15 at 2pm.",
    )
    _create_emlx(
        msgs_dir / "2.emlx",
        "Meeting Tomorrow",
        "boss@work.com",
        "Please attend the team meeting at 10am.",
    )
    _create_emlx(
        msgs_dir / "3.emlx",
        "Invoice #4567",
        "billing@vendor.com",
        "Please find attached invoice for March services.",
    )

    idx = SearchIndex(index_dir=str(tmp_path / "index"), mail_dir=str(mail_dir))
    result = idx.build()
    assert result["indexed"] == 3
    assert result["errors"] == 0

    # Search for deposition
    hits = idx.search("deposition")
    assert len(hits) == 1
    assert hits[0]["message_id"] == 1
    assert "April 15" in hits[0]["snippet"]

    # Search for meeting
    hits = idx.search("meeting")
    assert len(hits) == 1
    assert hits[0]["message_id"] == 2

    # Phrase search
    hits = idx.search('"team meeting"')
    assert len(hits) == 1


def test_search_index_incremental(tmp_path):
    """Incremental build should skip unchanged files."""
    mail_dir = tmp_path / "Mail"
    msgs_dir = mail_dir / "Messages"
    _create_emlx(msgs_dir / "1.emlx", "Test", "a@b.com", "Hello")

    idx = SearchIndex(index_dir=str(tmp_path / "index"), mail_dir=str(mail_dir))
    r1 = idx.build()
    assert r1["indexed"] == 1

    r2 = idx.build()
    assert r2["indexed"] == 0
    assert r2["skipped"] == 1


def test_search_index_force_rebuild(tmp_path):
    """Force rebuild should reindex everything."""
    mail_dir = tmp_path / "Mail"
    msgs_dir = mail_dir / "Messages"
    _create_emlx(msgs_dir / "1.emlx", "Test", "a@b.com", "Hello")

    idx = SearchIndex(index_dir=str(tmp_path / "index"), mail_dir=str(mail_dir))
    idx.build()
    r2 = idx.build(force=True)
    assert r2["indexed"] == 1
    assert r2["skipped"] == 0


def test_search_index_status(tmp_path):
    mail_dir = tmp_path / "Mail"
    msgs_dir = mail_dir / "Messages"
    _create_emlx(msgs_dir / "1.emlx", "Test", "a@b.com", "Hello")

    idx = SearchIndex(index_dir=str(tmp_path / "index"), mail_dir=str(mail_dir))
    idx.build()
    status = idx.status()
    assert status["indexed_messages"] == 1
    assert status["index_size_mb"] >= 0


def test_cli_index_status(tmp_path, mail_db):
    """CLI index --status should work."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "--db", mail_db, "index", "--status"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "ok"


def test_cli_search_body(tmp_path, mail_db):
    """CLI search-body should return results."""
    # Build a test index first
    mail_dir = tmp_path / "Mail"
    msgs_dir = mail_dir / "Messages"
    _create_emlx(
        msgs_dir / "1.emlx",
        "Depo Notice",
        "law@firm.com",
        "Your deposition is scheduled.",
    )

    idx = SearchIndex(index_dir=str(tmp_path / "index"), mail_dir=str(mail_dir))
    idx.build()

    # The CLI uses the default index path, so this test just verifies the command works
    runner = CliRunner()
    result = runner.invoke(
        cli, ["--json", "--db", mail_db, "search-body", "nonexistent"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "ok"
