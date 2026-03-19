"""Tests for Apple Mail AppleScript layer."""

import subprocess

from apple_mail.applescript import (
    _build_lookup_script,
    _escape_applescript,
    get_message_body,
    open_message,
)


def test_escape_applescript():
    assert _escape_applescript('say "hello"') == 'say \\"hello\\"'
    assert _escape_applescript("it's") == "it\\'s"
    assert _escape_applescript("back\\slash") == "back\\\\slash"


def test_build_lookup_script_by_id():
    script = _build_lookup_script(message_id=42, mode="content")
    assert "42" in script
    assert "content" in script.lower() or "body" in script.lower()


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
    except RuntimeError as e:
        assert "not found" in str(e).lower()
