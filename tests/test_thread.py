"""Tests for thread and export functionality."""

import subprocess

from apple_mail.client import MailClient


def test_get_thread(mail_db):
    client = MailClient(db_path=mail_db)
    thread = client.get_thread(1)
    # Messages 1 and 2 share conversation_id=100 (message 4 is deleted)
    assert thread.conversation_id == 100
    assert thread.message_count == 2
    assert len(thread.messages) == 2
    # Chronological order (oldest first)
    assert thread.messages[0].date <= thread.messages[1].date


def test_get_thread_participants(mail_db):
    client = MailClient(db_path=mail_db)
    thread = client.get_thread(1)
    assert "alice@example.com" in thread.participants
    assert "bob@example.com" in thread.participants


def test_get_thread_single_message(mail_db):
    client = MailClient(db_path=mail_db)
    thread = client.get_thread(3)
    assert thread.conversation_id == 200
    assert thread.message_count == 1


def test_get_thread_not_found(mail_db):
    client = MailClient(db_path=mail_db)
    try:
        client.get_thread(999)
        assert False, "Should have raised"
    except ValueError:
        pass


def test_conversation_id_on_message(mail_db):
    client = MailClient(db_path=mail_db)
    messages = client.search(subject="Test", limit=10)
    assert messages[0].conversation_id == 100


def test_export_message(mail_db, monkeypatch):
    """Export should produce markdown with YAML frontmatter."""

    def mock_run(cmd, **kwargs):
        return subprocess.CompletedProcess(
            cmd, 0, stdout="Hello, this is the body.\n", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", mock_run)

    client = MailClient(db_path=mail_db)
    md = client.export_message(1)
    assert md.startswith("---")
    assert 'subject: "Test Subject"' in md
    assert 'from: "alice@example.com"' in md
    assert "Hello, this is the body." in md


def test_export_message_not_found(mail_db):
    client = MailClient(db_path=mail_db)
    try:
        client.export_message(999)
        assert False, "Should have raised"
    except ValueError:
        pass


def test_export_thread(mail_db, monkeypatch):
    """Thread export should produce a single doc with all messages."""
    call_count = {"n": 0}

    def mock_run(cmd, **kwargs):
        call_count["n"] += 1
        return subprocess.CompletedProcess(
            cmd, 0, stdout=f"Body of message {call_count['n']}\n", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", mock_run)

    client = MailClient(db_path=mail_db)
    md = client.export_thread(1)
    assert md.startswith("---")
    assert "thread_id: 100" in md
    assert "message_count: 2" in md
    assert "Body of message 1" in md
    assert "Body of message 2" in md
    # Should have section headers
    assert "## " in md
