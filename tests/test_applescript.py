"""Tests for Apple Mail AppleScript layer."""

import subprocess

from apple_mail.applescript import (
    _build_action_script,
    _escape_applescript,
    create_draft,
    get_message_body,
    mark_read,
    move_message,
    open_message,
    set_flagged,
)
from apple_mail.errors import MessageNotFoundError


def test_escape_applescript():
    assert _escape_applescript('say "hello"') == 'say \\"hello\\"'
    assert _escape_applescript("it's") == "it\\'s"
    assert _escape_applescript("back\\slash") == "back\\\\slash"


def test_build_action_script_by_id():
    script = _build_action_script(message_id=42, action="return content of foundMsg")
    assert "42" in script
    assert "content" in script


def test_open_message_calls_osascript(monkeypatch):
    called = {}

    def mock_run(cmd, **kwargs):
        called["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="OK", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)
    open_message(message_id=42, subject="Hello", sender="a@b.com")
    assert "osascript" in called["cmd"][0]


def test_get_body_returns_content(monkeypatch):
    def mock_run(cmd, **kwargs):
        return subprocess.CompletedProcess(
            cmd, 0, stdout="Email body text\n", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", mock_run)
    body = get_message_body(message_id=42, subject="Hello", sender="a@b.com")
    assert body == "Email body text"


def test_get_body_not_found(monkeypatch):
    def mock_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout="__NOT_FOUND__\n", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)
    try:
        get_message_body(message_id=42, subject="Hello", sender="a@b.com")
        assert False, "Should have raised"
    except MessageNotFoundError as e:
        assert e.message_id == 42


def test_mark_read(monkeypatch):
    called = {}

    def mock_run(cmd, **kwargs):
        called["script"] = cmd[2] if len(cmd) > 2 else ""
        return subprocess.CompletedProcess(cmd, 0, stdout="OK", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)
    mark_read(message_id=42, subject="Hello", sender="a@b.com")
    assert "read status" in called["script"]
    assert "true" in called["script"]


def test_mark_unread(monkeypatch):
    called = {}

    def mock_run(cmd, **kwargs):
        called["script"] = cmd[2] if len(cmd) > 2 else ""
        return subprocess.CompletedProcess(cmd, 0, stdout="OK", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)
    mark_read(message_id=42, read=False)
    assert "false" in called["script"]


def test_set_flagged(monkeypatch):
    called = {}

    def mock_run(cmd, **kwargs):
        called["script"] = cmd[2] if len(cmd) > 2 else ""
        return subprocess.CompletedProcess(cmd, 0, stdout="OK", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)
    set_flagged(message_id=42, flagged=True)
    assert "flagged status" in called["script"]
    assert "true" in called["script"]


def test_move_message(monkeypatch):
    called = {}

    def mock_run(cmd, **kwargs):
        called["script"] = cmd[2] if len(cmd) > 2 else ""
        return subprocess.CompletedProcess(cmd, 0, stdout="OK", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)
    move_message(
        message_id=42, target_mailbox="Archive", subject="Hello", sender="a@b.com"
    )
    assert "Archive" in called["script"]
    assert "move foundMsg" in called["script"]


def test_move_message_with_account(monkeypatch):
    called = {}

    def mock_run(cmd, **kwargs):
        called["script"] = cmd[2] if len(cmd) > 2 else ""
        return subprocess.CompletedProcess(cmd, 0, stdout="OK", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)
    move_message(
        message_id=42,
        target_mailbox="Archive",
        target_account="iCloud",
        subject="Hello",
        sender="a@b.com",
    )
    assert "iCloud" in called["script"]
    assert "Archive" in called["script"]


def test_create_draft(monkeypatch):
    called = {}

    def mock_run(cmd, **kwargs):
        called["script"] = cmd[2] if len(cmd) > 2 else ""
        return subprocess.CompletedProcess(cmd, 0, stdout="OK", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)
    create_draft(
        to_addresses=["alice@example.com"],
        subject="Re: Hello",
        body="Thanks for your email!",
    )
    assert "alice@example.com" in called["script"]
    assert "Re: Hello" in called["script"]
    assert "visible:false" in called["script"]
    assert "save newMsg" in called["script"]


def test_create_draft_with_cc(monkeypatch):
    called = {}

    def mock_run(cmd, **kwargs):
        called["script"] = cmd[2] if len(cmd) > 2 else ""
        return subprocess.CompletedProcess(cmd, 0, stdout="OK", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)
    create_draft(
        to_addresses=["alice@example.com"],
        subject="Hello",
        body="Body text",
        cc_addresses=["bob@example.com"],
    )
    assert "cc recipient" in called["script"]
    assert "bob@example.com" in called["script"]
