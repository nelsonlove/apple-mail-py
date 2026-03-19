"""Tests for triage and bulk operations."""

import subprocess

from apple_mail.client import MailClient


def test_snippet_from_summary(mail_db):
    """Message 1 has a summary; it should appear as snippet."""
    client = MailClient(db_path=mail_db)
    messages = client.search(subject="Test", limit=10)
    assert (
        messages[0].snippet == "Hi, just checking in on the test subject we discussed."
    )


def test_snippet_empty_when_no_summary(mail_db):
    """Messages without summaries should have empty snippet."""
    client = MailClient(db_path=mail_db)
    messages = client.search(subject="Another", limit=10)
    assert messages[0].snippet == ""


def test_bulk_mark_read(mail_db, monkeypatch):
    def mock_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout="OK", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    client = MailClient(db_path=mail_db)
    count = client.bulk_mark_read([1, 2, 3])
    assert count == 3


def test_bulk_archive(mail_db, monkeypatch):
    def mock_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout="OK", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    client = MailClient(db_path=mail_db)
    count = client.bulk_archive([1, 2])
    assert count == 2


def test_bulk_archive_skips_missing(mail_db, monkeypatch):
    """Bulk archive should skip messages that can't be found."""
    call_count = {"n": 0}

    def mock_run(cmd, **kwargs):
        call_count["n"] += 1
        # Fail on second call
        if call_count["n"] == 2:
            return subprocess.CompletedProcess(
                cmd, 0, stdout="__NOT_FOUND__", stderr=""
            )
        return subprocess.CompletedProcess(cmd, 0, stdout="OK", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    client = MailClient(db_path=mail_db)
    count = client.bulk_archive([1, 2, 3])
    # One should fail (not found), two should succeed
    assert count == 2
