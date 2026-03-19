"""Tests for apple_mail data models."""

from dataclasses import asdict

from apple_mail.models import Mailbox, Message, MessageBody, Stats


def test_message_defaults():
    msg = Message(
        id=1, subject="Hello", sender="a@b.com", sender_name="A",
        date="2026-01-01T00:00:00", mailbox="Inbox", read=False,
        flagged=False, has_attachments=False,
    )
    assert msg.recipients == []
    d = asdict(msg)
    assert d["id"] == 1
    assert d["recipients"] == []


def test_mailbox():
    mb = Mailbox(id=1, name="Inbox", path="/path", account="iCloud")
    assert mb.name == "Inbox"


def test_stats():
    s = Stats(total=100, unread=5, deleted=2, with_attachments=10)
    assert s.total == 100


def test_message_body():
    body = MessageBody(id=1, subject="Hello", sender="a@b.com", body="Content here")
    assert body.body == "Content here"
