"""Tests for thread and export CLI commands."""

import json

from click.testing import CliRunner

from clawmail.cli import cli


def test_thread_json(mail_db):
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "--db", mail_db, "thread", "1"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "ok"
    assert data["data"]["conversation_id"] == 100
    assert data["data"]["message_count"] == 2


def test_thread_human(mail_db):
    runner = CliRunner()
    result = runner.invoke(cli, ["--db", mail_db, "thread", "1"])
    assert result.exit_code == 0
    assert "Thread:" in result.output
    assert "Messages: 2" in result.output


def test_thread_not_found(mail_db):
    runner = CliRunner()
    result = runner.invoke(cli, ["--db", mail_db, "thread", "999"])
    assert result.exit_code != 0
