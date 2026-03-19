"""Unified client for Apple Mail — the single entry point for all operations.

Reads go through SQLite (db.py), message open/body through AppleScript.
All methods return data classes, never raw dicts.
"""

from __future__ import annotations

from .db import MailDB
from .errors import MailError, MessageNotFoundError
from .models import Attachment, Mailbox, Message, MessageBody, Stats, Thread


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
            subject=subject,
            sender=sender,
            from_name=from_name,
            to=to,
            unread=unread,
            days=days,
            has_attachment=has_attachment,
            attachment_type=attachment_type,
            limit=limit,
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

    # ── Attachment operations ────────────────────────────────────────────

    def get_attachments(self, message_id: int) -> list[Attachment]:
        """List attachments for a message."""
        rows = self._db.get_attachments(message_id)
        return [
            Attachment(id=r["id"], message_id=r["message_id"], name=r["name"])
            for r in rows
        ]

    def save_attachments(self, message_id: int, output_dir: str) -> list[str]:
        """Save all attachments from a message to a directory.

        Returns list of saved filenames.
        """
        from .applescript import save_attachments as as_save

        ctx = self._msg_context(message_id)
        return as_save(
            message_id=message_id,
            output_dir=output_dir,
            subject=ctx["subject"],
            sender=ctx["sender"],
        )

    # ── Thread operations ──────────────────────────────────────────────

    def get_thread(self, message_id: int) -> Thread:
        """Get the full conversation thread containing a message.

        Args:
            message_id: Any message ID in the thread.

        Returns:
            Thread with all messages in chronological order.

        Raises:
            ValueError: If the message is not found.
        """
        conv_id = self._db.get_conversation_id(message_id)
        if conv_id is None:
            raise MessageNotFoundError(message_id)

        rows = self._db.get_thread_messages(conv_id)
        messages = [_row_to_message(r) for r in rows]

        participants = list(dict.fromkeys(m.sender for m in messages if m.sender))
        subject = messages[0].subject if messages else ""

        return Thread(
            conversation_id=conv_id,
            subject=subject,
            participants=participants,
            message_count=len(messages),
            date_start=messages[0].date if messages else "",
            date_end=messages[-1].date if messages else "",
            messages=messages,
        )

    # ── Export ─────────────────────────────────────────────────────────

    def export_message(self, message_id: int) -> str:
        """Export a single message as markdown with YAML frontmatter.

        Fetches body via AppleScript.

        Raises:
            ValueError: If the message is not found.
        """
        from .applescript import get_message_body as as_body

        row = self._db.get_message(message_id)
        if row is None:
            raise MessageNotFoundError(message_id)

        body = as_body(
            message_id=message_id,
            subject=row["subject"],
            sender=row["sender"],
        )

        recipients = row.get("recipients", [])
        to_line = ", ".join(recipients) if recipients else ""

        lines = [
            "---",
            f'subject: "{_escape_yaml(row["subject"])}"',
            f'from: "{_escape_yaml(row["sender"])}"',
            f'from_name: "{_escape_yaml(row["sender_name"])}"',
        ]
        if to_line:
            lines.append(f'to: "{_escape_yaml(to_line)}"')
        lines.extend(
            [
                f'date: "{row["date"]}"',
                f'mailbox: "{row["mailbox"]}"',
                f"id: {message_id}",
                "---",
                "",
                body,
                "",
            ]
        )
        return "\n".join(lines)

    def export_thread(self, message_id: int) -> str:
        """Export a full conversation thread as a single markdown document.

        Fetches body for each message via AppleScript.

        Args:
            message_id: Any message ID in the thread.

        Raises:
            ValueError: If the message is not found.
        """
        from .applescript import get_message_body as as_body

        thread = self.get_thread(message_id)

        # Build frontmatter
        lines = [
            "---",
            f"thread_id: {thread.conversation_id}",
            f'subject: "{_escape_yaml(thread.subject)}"',
            "participants:",
        ]
        for p in thread.participants:
            lines.append(f'  - "{_escape_yaml(p)}"')
        lines.extend(
            [
                f"message_count: {thread.message_count}",
                f'date_range: "{thread.date_start} to {thread.date_end}"',
                "---",
                "",
            ]
        )

        # Each message as a section
        for msg in thread.messages:
            sender_display = msg.sender_name or msg.sender
            lines.append(f"## {sender_display} — {msg.date}")
            lines.append("")

            try:
                body = as_body(
                    message_id=msg.id,
                    subject=msg.subject,
                    sender=msg.sender,
                )
                lines.append(body)
            except MailError:
                lines.append("*(message body unavailable)*")
            lines.append("")

        return "\n".join(lines)

    # ── App interaction (AppleScript) ─────────────────────────────────

    def _msg_context(self, message_id: int) -> dict:
        """Get lookup context for a message (subject, sender for fallback)."""
        row = self._db.get_message(message_id)
        return {
            "message_id": message_id,
            "subject": row["subject"] if row else None,
            "sender": row["sender"] if row else None,
        }

    def open_message(self, message_id: int) -> None:
        """Open a message in Mail.app."""
        from .applescript import open_message as as_open

        as_open(**self._msg_context(message_id))

    def get_body(self, message_id: int) -> MessageBody:
        """Get full message body via AppleScript."""
        from .applescript import get_message_body as as_body

        ctx = self._msg_context(message_id)
        body = as_body(**ctx)
        return MessageBody(
            id=message_id,
            subject=ctx["subject"] or "",
            sender=ctx["sender"] or "",
            body=body,
        )

    # ── Write operations (AppleScript) ────────────────────────────────

    def mark_read(self, message_id: int, *, read: bool = True) -> None:
        """Mark a message as read or unread."""
        from .applescript import mark_read as as_mark

        as_mark(**self._msg_context(message_id), read=read)

    def set_flagged(self, message_id: int, *, flagged: bool = True) -> None:
        """Flag or unflag a message."""
        from .applescript import set_flagged as as_flag

        as_flag(**self._msg_context(message_id), flagged=flagged)

    def archive(self, message_id: int, *, account: str | None = None) -> None:
        """Move a message to Archive."""
        from .applescript import move_message as as_move

        as_move(
            **self._msg_context(message_id),
            target_mailbox="Archive",
            target_account=account,
        )

    def move_to_mailbox(
        self, message_id: int, mailbox: str, *, account: str | None = None
    ) -> None:
        """Move a message to a specific mailbox."""
        from .applescript import move_message as as_move

        as_move(
            **self._msg_context(message_id),
            target_mailbox=mailbox,
            target_account=account,
        )

    def create_draft(
        self,
        *,
        to: list[str],
        subject: str,
        body: str,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
    ) -> None:
        """Create a draft email (saved to Drafts, not sent)."""
        from .applescript import create_draft as as_draft

        as_draft(
            to_addresses=to,
            subject=subject,
            body=body,
            cc_addresses=cc,
            bcc_addresses=bcc,
        )

    # ── Bulk operations ───────────────────────────────────────────────

    def bulk_archive(
        self, message_ids: list[int], *, account: str | None = None
    ) -> int:
        """Archive multiple messages. Returns count of messages archived."""
        from .applescript import move_message as as_move

        count = 0
        for mid in message_ids:
            try:
                as_move(
                    **self._msg_context(mid),
                    target_mailbox="Archive",
                    target_account=account,
                )
                count += 1
            except MailError:
                pass  # skip messages that can't be found
        return count

    def bulk_mark_read(self, message_ids: list[int], *, read: bool = True) -> int:
        """Mark multiple messages as read/unread. Returns count processed."""
        from .applescript import mark_read as as_mark

        count = 0
        for mid in message_ids:
            try:
                as_mark(**self._msg_context(mid), read=read)
                count += 1
            except MailError:
                pass
        return count


def _escape_yaml(s: str) -> str:
    """Escape a string for safe embedding in YAML double-quoted values."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


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
        conversation_id=row.get("conversation_id", 0),
        snippet=row.get("snippet", "") or "",
        recipients=row.get("recipients", []),
    )
