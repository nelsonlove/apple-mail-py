"""SQLite read-only access to the Apple Mail Envelope Index database."""

from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
from contextlib import closing
from typing import Any

from .db_finder import find_mail_db

_MAILBOX_NAMES: dict[str, str] = {
    "INBOX": "Inbox",
    "Sent Messages": "Sent",
    "Sent": "Sent",
    "Drafts": "Drafts",
    "Trash": "Trash",
    "Deleted Messages": "Trash",
    "Junk": "Junk",
    "Archive": "Archive",
    "All Mail": "All Mail",
}


def _friendly_mailbox(url: str | None) -> str:
    if not url:
        return "Unknown"
    name = url.rstrip("/").rsplit("/", 1)[-1].replace("%20", " ")
    return _MAILBOX_NAMES.get(name, name)


class MailDB:
    def __init__(self, db_path: str | None = None, copy_mode: bool = False):
        self._source_path = db_path or find_mail_db()
        self._copy_mode = copy_mode
        self._tmp_path: str | None = None

    @property
    def db_path(self) -> str:
        if self._copy_mode:
            if self._tmp_path is None:
                fd, self._tmp_path = tempfile.mkstemp(suffix=".sqlite")
                os.close(fd)
                shutil.copy2(self._source_path, self._tmp_path)
            return self._tmp_path
        return self._source_path

    def _query(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        uri = f"file:{self.db_path}?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as conn:
            conn.row_factory = sqlite3.Row
            with closing(conn.cursor()) as cur:
                cur.execute(sql, params)
                return [dict(row) for row in cur.fetchall()]

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
    ) -> list[dict[str, Any]]:
        joins = []
        conditions = ["m.deleted = 0"]
        params: list[Any] = []

        if to:
            joins.append(
                "INNER JOIN recipients r ON r.message_id = m.ROWID "
                "INNER JOIN addresses ra ON r.address_id = ra.ROWID"
            )
            conditions.append("(ra.address LIKE ? OR ra.comment LIKE ?)")
            pat = f"%{to}%"
            params.extend([pat, pat])

        if has_attachment or attachment_type:
            joins.append("INNER JOIN attachments att ON att.message_id = m.ROWID")
            if attachment_type:
                conditions.append("att.name LIKE ?")
                params.append(f"%.{attachment_type}")

        if subject:
            conditions.append("s.subject LIKE ?")
            params.append(f"%{subject}%")

        if sender:
            conditions.append("(a.address LIKE ? OR a.comment LIKE ?)")
            pat = f"%{sender}%"
            params.extend([pat, pat])

        if from_name:
            conditions.append("a.comment LIKE ?")
            params.append(f"%{from_name}%")

        if unread is True:
            conditions.append("m.read = 0")
        elif unread is False:
            conditions.append("m.read = 1")

        if days:
            conditions.append("m.date_sent >= strftime('%s', 'now', ?)")
            params.append(f"-{days} days")

        join_clause = "\n".join(joins)
        where_clause = " AND ".join(conditions)

        sql = f"""
        SELECT DISTINCT
            m.ROWID AS id,
            s.subject,
            a.address AS sender,
            COALESCE(a.comment, '') AS sender_name,
            datetime(m.date_sent, 'unixepoch', 'localtime') AS date,
            mb.url AS mailbox_url,
            m.read,
            COALESCE(m.flagged, 0) AS flagged,
            EXISTS(SELECT 1 FROM attachments att2 WHERE att2.message_id = m.ROWID) AS has_attachments
        FROM messages m
        LEFT JOIN subjects s ON m.subject = s.ROWID
        LEFT JOIN addresses a ON m.sender = a.ROWID
        LEFT JOIN mailboxes mb ON m.mailbox = mb.ROWID
        {join_clause}
        WHERE {where_clause}
        ORDER BY m.date_sent DESC
        LIMIT ?
        """
        params.append(limit)

        rows = self._query(sql, tuple(params))
        for row in rows:
            row["mailbox"] = _friendly_mailbox(row.pop("mailbox_url", None))
            row["recipients"] = self._get_recipients(row["id"])
        return rows

    def _get_recipients(self, message_id: int) -> list[str]:
        sql = """
        SELECT a.address
        FROM recipients r
        INNER JOIN addresses a ON r.address_id = a.ROWID
        WHERE r.message_id = ?
        """
        rows = self._query(sql, (message_id,))
        return [r["address"] for r in rows]

    def get_message(self, message_id: int) -> dict[str, Any] | None:
        sql = """
        SELECT
            m.ROWID AS id,
            s.subject,
            a.address AS sender,
            COALESCE(a.comment, '') AS sender_name,
            datetime(m.date_sent, 'unixepoch', 'localtime') AS date,
            mb.url AS mailbox_url,
            m.read,
            COALESCE(m.flagged, 0) AS flagged,
            EXISTS(SELECT 1 FROM attachments att WHERE att.message_id = m.ROWID) AS has_attachments
        FROM messages m
        LEFT JOIN subjects s ON m.subject = s.ROWID
        LEFT JOIN addresses a ON m.sender = a.ROWID
        LEFT JOIN mailboxes mb ON m.mailbox = mb.ROWID
        WHERE m.ROWID = ? AND m.deleted = 0
        LIMIT 1
        """
        rows = self._query(sql, (message_id,))
        if not rows:
            return None
        row = rows[0]
        row["mailbox"] = _friendly_mailbox(row.pop("mailbox_url", None))
        row["recipients"] = self._get_recipients(message_id)
        return row

    def stats(self) -> dict[str, int]:
        sql = """
        SELECT
            SUM(CASE WHEN deleted = 0 THEN 1 ELSE 0 END) AS total,
            SUM(CASE WHEN deleted = 0 AND read = 0 THEN 1 ELSE 0 END) AS unread,
            SUM(CASE WHEN deleted = 1 THEN 1 ELSE 0 END) AS deleted,
            (SELECT COUNT(DISTINCT message_id) FROM attachments) AS with_attachments
        FROM messages
        """
        rows = self._query(sql)
        return rows[0] if rows else {"total": 0, "unread": 0, "deleted": 0, "with_attachments": 0}

    def mailboxes(self) -> list[dict[str, Any]]:
        sql = """
        SELECT mb.ROWID AS id, mb.url AS path
        FROM mailboxes mb
        ORDER BY mb.url
        """
        rows = self._query(sql)
        for row in rows:
            row["name"] = _friendly_mailbox(row["path"])
            row["account"] = _extract_account(row["path"])
        return rows


def _extract_account(url: str | None) -> str:
    if not url or "://" not in url:
        return ""
    after_scheme = url.split("://", 1)[1]
    return after_scheme.split("/", 1)[0]
