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
    conversation_id: int = 0
    snippet: str = ""
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


@dataclass
class Attachment:
    """An email attachment."""

    id: int
    message_id: int
    name: str


@dataclass
class Thread:
    """A conversation thread (group of related messages)."""

    conversation_id: int
    subject: str
    participants: list[str] = field(default_factory=list)
    message_count: int = 0
    date_start: str = ""
    date_end: str = ""
    messages: list[Message] = field(default_factory=list)
