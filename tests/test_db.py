"""Tests for Apple Mail database layer."""

from apple_mail.db import MailDB


def test_search_all(mail_db):
    db = MailDB(mail_db)
    results = db.search(limit=10)
    assert len(results) == 3


def test_search_by_subject(mail_db):
    db = MailDB(mail_db)
    results = db.search(subject="Test", limit=10)
    assert len(results) == 1
    assert results[0]["subject"] == "Test Subject"


def test_search_by_sender(mail_db):
    db = MailDB(mail_db)
    results = db.search(sender="alice", limit=10)
    assert len(results) == 1


def test_search_unread(mail_db):
    db = MailDB(mail_db)
    results = db.search(unread=True, limit=10)
    assert all(r["read"] == 0 for r in results)


def test_search_read(mail_db):
    db = MailDB(mail_db)
    results = db.search(unread=False, limit=10)
    assert all(r["read"] == 1 for r in results)


def test_search_has_attachment(mail_db):
    db = MailDB(mail_db)
    results = db.search(has_attachment=True, limit=10)
    assert len(results) == 1
    assert results[0]["subject"] == "Meeting Notes"


def test_search_by_recipient(mail_db):
    db = MailDB(mail_db)
    results = db.search(to="carol", limit=10)
    assert len(results) == 1
    assert results[0]["subject"] == "Another Email"


def test_stats(mail_db):
    db = MailDB(mail_db)
    s = db.stats()
    assert s["total"] == 3
    assert s["unread"] == 2
    assert s["deleted"] == 1
    assert s["with_attachments"] == 1


def test_mailboxes(mail_db):
    db = MailDB(mail_db)
    mbs = db.mailboxes()
    assert len(mbs) >= 2


def test_get_message(mail_db):
    db = MailDB(mail_db)
    row = db.get_message(1)
    assert row is not None
    assert row["subject"] == "Test Subject"


def test_get_message_missing(mail_db):
    db = MailDB(mail_db)
    row = db.get_message(999)
    assert row is None


def test_friendly_mailbox_name(mail_db):
    db = MailDB(mail_db)
    results = db.search(limit=10)
    mailbox_names = {r["mailbox"] for r in results}
    assert "Inbox" in mailbox_names


def test_copy_mode(mail_db):
    db = MailDB(mail_db, copy_mode=True)
    results = db.search(limit=10)
    assert len(results) == 3
