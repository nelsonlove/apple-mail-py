"""Tests for MailClient."""

from apple_mail.client import MailClient


def test_search(mail_db):
    client = MailClient(db_path=mail_db)
    messages = client.search(limit=10)
    assert len(messages) == 3
    msg = messages[0]
    assert hasattr(msg, "id")
    assert hasattr(msg, "subject")
    assert hasattr(msg, "sender")


def test_search_by_subject(mail_db):
    client = MailClient(db_path=mail_db)
    messages = client.search(subject="Test", limit=10)
    assert len(messages) == 1
    assert messages[0].subject == "Test Subject"


def test_recent(mail_db):
    client = MailClient(db_path=mail_db)
    messages = client.recent(days=30, limit=10)
    assert isinstance(messages, list)


def test_unread(mail_db):
    client = MailClient(db_path=mail_db)
    messages = client.unread(limit=10)
    assert all(not m.read for m in messages)


def test_stats(mail_db):
    client = MailClient(db_path=mail_db)
    stats = client.stats()
    assert stats.total == 3
    assert stats.unread == 2
    assert stats.deleted == 1


def test_mailboxes(mail_db):
    client = MailClient(db_path=mail_db)
    mbs = client.mailboxes()
    assert len(mbs) >= 2
    mb = mbs[0]
    assert hasattr(mb, "id")
    assert hasattr(mb, "name")


def test_copy_mode(mail_db):
    client = MailClient(db_path=mail_db, copy_mode=True)
    messages = client.search(limit=10)
    assert len(messages) == 3
