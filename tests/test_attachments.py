"""Tests for attachment operations."""

import json
import subprocess

from click.testing import CliRunner

from apple_mail.cli import cli
from apple_mail.client import MailClient


def test_get_attachments(mail_db):
    client = MailClient(db_path=mail_db)
    atts = client.get_attachments(3)
    assert len(atts) == 2
    assert atts[0].name == "report.pdf"
    assert atts[1].name == "notes.docx"


def test_get_attachments_none(mail_db):
    client = MailClient(db_path=mail_db)
    atts = client.get_attachments(1)
    assert len(atts) == 0


def test_save_attachments(mail_db, monkeypatch):
    """save_attachments should call AppleScript and return filenames."""

    def mock_run(cmd, **kwargs):
        return subprocess.CompletedProcess(
            cmd, 0, stdout="report.pdf||notes.docx", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", mock_run)

    client = MailClient(db_path=mail_db)
    saved = client.save_attachments(3, "/tmp/test")
    assert saved == ["report.pdf", "notes.docx"]


def test_save_attachments_empty(mail_db, monkeypatch):
    """Message with no attachments should return empty list."""

    def mock_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    client = MailClient(db_path=mail_db)
    saved = client.save_attachments(1, "/tmp/test")
    assert saved == []


def test_cli_attachments_json(mail_db):
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "--db", mail_db, "attachments", "3"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "ok"
    assert len(data["data"]) == 2
    assert data["data"][0]["name"] == "report.pdf"


def test_cli_attachments_none(mail_db):
    runner = CliRunner()
    result = runner.invoke(cli, ["--db", mail_db, "attachments", "1"])
    assert result.exit_code == 0
    assert "No attachments" in result.output


def test_cli_save_attachments_dry_run(mail_db):
    runner = CliRunner()
    result = runner.invoke(
        cli, ["--json", "--db", mail_db, "save-attachments", "3", "--dry-run"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["dry_run"] is True
    assert "report.pdf" in data["data"]["files"]
