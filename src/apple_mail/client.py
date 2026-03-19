"""Unified client for Apple Mail — the single entry point for all operations.

Reads go through SQLite (db.py), message open/body through AppleScript.
All methods return data classes, never raw dicts.
"""

from __future__ import annotations

from .db import MailDB
from .models import Mailbox, Message, MessageBody, Stats


class MailClient:
    """Apple Mail client.

    Args:
        db_path: Path to Envelope Index. Defaults to auto-detection.
        copy_mode: If True, copy the DB to a temp file before reading.
    """

    def __init__(self, db_path: str | None = None, copy_mode: bool = False):
        self._db = MailDB(db_path, copy_mode=copy_mode)

    # ── Read operations (SQLite) ─────────────────────────────────────

    def search(
        self,
        *,
        subject: str | None = None,
        sender: str | None = None,
        from_name: str | None = None,
        to: str | None = None,
        unread: bool | None = None,
        days: int | None = None,
        has_attachment: bool = False,
        attachment_type: str | None = None,
        limit: int = 20,
    ) -> list[Message]:
        """Search messages with optional filters."""
        rows = self._db.search(
            subject=subject, sender=sender, from_name=from_name, to=to,
            unread=unread, days=days, has_attachment=has_attachment,
            attachment_type=attachment_type, limit=limit,
        )
        return [_row_to_message(r) for r in rows]

    def recent(self, *, days: int = 7, limit: int = 20) -> list[Message]:
        """Get recent messages."""
        return self.search(days=days, limit=limit)

    def unread(self, *, limit: int = 20) -> list[Message]:
        """Get unread messages."""
        return self.search(unread=True, limit=limit)

    def stats(self) -> Stats:
        """Get database statistics."""
        row = self._db.stats()
        return Stats(
            total=row["total"] or 0,
            unread=row["unread"] or 0,
            deleted=row["deleted"] or 0,
            with_attachments=row["with_attachments"] or 0,
        )

    def mailboxes(self) -> list[Mailbox]:
        """List all mailboxes."""
        rows = self._db.mailboxes()
        return [
            Mailbox(
                id=r["id"],
                name=r["name"],
                path=r["path"],
                account=r.get("account", ""),
            )
            for r in rows
        ]

    # ── App interaction (AppleScript) ─────────────────────────────────

    def open_message(self, message_id: int) -> None:
        """Open a message in Mail.app."""
        from .applescript import open_message as as_open

        row = self._db.get_message(message_id)
        as_open(
            message_id=message_id,
            subject=row["subject"] if row else None,
            sender=row["sender"] if row else None,
        )

    def get_body(self, message_id: int) -> MessageBody:
        """Get full message body via AppleScript."""
        from .applescript import get_message_body as as_body

        row = self._db.get_message(message_id)
        subject = row["subject"] if row else ""
        sender = row["sender"] if row else ""

        body = as_body(
            message_id=message_id,
            subject=subject,
            sender=sender,
        )
        return MessageBody(
            id=message_id,
            subject=subject,
            sender=sender,
            body=body,
        )


def _row_to_message(row: dict) -> Message:
    """Convert a raw DB row dict to a Message data class."""
    return Message(
        id=row["id"],
        subject=row.get("subject", "") or "",
        sender=row.get("sender", "") or "",
        sender_name=row.get("sender_name", "") or "",
        date=row.get("date", "") or "",
        mailbox=row.get("mailbox", "") or "",
        read=bool(row.get("read", 0)),
        flagged=bool(row.get("flagged", 0)),
        has_attachments=bool(row.get("has_attachments", 0)),
        recipients=row.get("recipients", []),
    )
