"""Data classes for Apple Mail objects."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Message:
    """An email message (metadata only, no body)."""

    id: int
    subject: str
    sender: str
    sender_name: str
    date: str
    mailbox: str
    read: bool
    flagged: bool
    has_attachments: bool
    recipients: list[str] = field(default_factory=list)


@dataclass
class Mailbox:
    """A mail folder/mailbox."""

    id: int
    name: str
    path: str
    account: str = ""


@dataclass
class Stats:
    """Database-level statistics."""

    total: int
    unread: int
    deleted: int
    with_attachments: int


@dataclass
class MessageBody:
    """Full message content retrieved via AppleScript."""

    id: int
    subject: str
    sender: str
    body: str
