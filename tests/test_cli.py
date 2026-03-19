"""Tests for the apple-mail CLI."""

import json

from click.testing import CliRunner

from apple_mail.cli import cli


def test_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "search" in result.output


def test_stats_json(mail_db):
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "--db", mail_db, "stats"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "ok"
    assert data["data"]["total"] == 3


def test_search_json(mail_db):
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "--db", mail_db, "search"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "ok"
    assert len(data["data"]) == 3


def test_search_subject_json(mail_db):
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "--db", mail_db, "subject", "Test"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data["data"]) == 1


def test_search_sender_json(mail_db):
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "--db", mail_db, "sender", "alice"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data["data"]) == 1


def test_unread_json(mail_db):
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "--db", mail_db, "unread"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert all(not m["read"] for m in data["data"])


def test_mailboxes_json(mail_db):
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "--db", mail_db, "mailboxes"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "ok"


def test_stats_human(mail_db):
    runner = CliRunner()
    result = runner.invoke(cli, ["--db", mail_db, "stats"])
    assert result.exit_code == 0
    assert "Total" in result.output


def test_search_csv(mail_db):
    runner = CliRunner()
    result = runner.invoke(cli, ["--csv", "--db", mail_db, "search"])
    assert result.exit_code == 0
    lines = result.output.strip().split("\n")
    assert len(lines) >= 2


def test_recent_json(mail_db):
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "--db", mail_db, "recent"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "ok"
