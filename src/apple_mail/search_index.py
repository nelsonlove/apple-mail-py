"""FTS5 full-text search index for Apple Mail message bodies."""

from __future__ import annotations

import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from typing import Any

from .emlx import find_emlx_files, parse_emlx

# Default index location (XDG cache)
_DEFAULT_INDEX_DIR = "~/.cache/apple-mail-py"
_INDEX_FILENAME = "search.db"


def _index_path(index_dir: str | None = None) -> Path:
    """Get the path to the FTS5 index database."""
    base = Path(index_dir or _DEFAULT_INDEX_DIR).expanduser()
    base.mkdir(parents=True, exist_ok=True)
    return base / _INDEX_FILENAME


class SearchIndex:
    """FTS5 full-text search index over Apple Mail message bodies.

    The index is stored in a separate SQLite database (not the Envelope Index)
    at ~/.cache/apple-mail-py/search.db.
    """

    def __init__(self, index_dir: str | None = None, mail_dir: str | None = None):
        self._db_path = str(_index_path(index_dir))
        self._mail_dir = mail_dir
        self._ensure_schema()

    def _ensure_schema(self):
        """Create the FTS5 table if it doesn't exist."""
        with closing(sqlite3.connect(self._db_path)) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY,
                    subject TEXT,
                    sender TEXT,
                    body TEXT,
                    file_path TEXT,
                    mtime REAL
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                    subject, sender, body,
                    content='messages',
                    content_rowid='message_id'
                );
                CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
                    INSERT INTO messages_fts(rowid, subject, sender, body)
                    VALUES (new.message_id, new.subject, new.sender, new.body);
                END;
                CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
                    INSERT INTO messages_fts(messages_fts, rowid, subject, sender, body)
                    VALUES ('delete', old.message_id, old.subject, old.sender, old.body);
                END;
                CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
                    INSERT INTO messages_fts(messages_fts, rowid, subject, sender, body)
                    VALUES ('delete', old.message_id, old.subject, old.sender, old.body);
                    INSERT INTO messages_fts(rowid, subject, sender, body)
                    VALUES (new.message_id, new.subject, new.sender, new.body);
                END;
            """)

    def build(self, *, force: bool = False, progress: bool = False) -> dict[str, int]:
        """Build or update the search index from .emlx files.

        Incremental: only indexes new/changed files (by mtime) unless force=True.

        Args:
            force: Drop and rebuild the index from scratch.
            progress: Print progress to stderr.

        Returns:
            Dict with keys: indexed, skipped, errors, total_files.
        """
        emlx_files = find_emlx_files(self._mail_dir)

        with closing(sqlite3.connect(self._db_path)) as conn:
            if force:
                conn.executescript("""
                    DELETE FROM messages;
                    INSERT INTO messages_fts(messages_fts) VALUES ('delete-all');
                """)
                existing = {}
            else:
                rows = conn.execute("SELECT message_id, mtime FROM messages").fetchall()
                existing = {r[0]: r[1] for r in rows}

            indexed = 0
            skipped = 0
            errors = 0

            for i, path in enumerate(emlx_files):
                if progress and i % 500 == 0:
                    print(
                        f"\r  Indexing: {i}/{len(emlx_files)}...",
                        end="",
                        file=sys.stderr,
                        flush=True,
                    )

                parsed = parse_emlx(path)
                if parsed is None:
                    errors += 1
                    continue

                mid = parsed["message_id"]
                mtime = path.stat().st_mtime

                # Skip if already indexed with same mtime
                if mid in existing and existing[mid] == mtime:
                    skipped += 1
                    continue

                if mid in existing:
                    conn.execute("DELETE FROM messages WHERE message_id = ?", (mid,))

                conn.execute(
                    """INSERT INTO messages (message_id, subject, sender, body, file_path, mtime)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        mid,
                        parsed["subject"],
                        parsed["sender"],
                        parsed["body"],
                        str(path),
                        mtime,
                    ),
                )
                indexed += 1

            conn.commit()

            if progress:
                print(
                    f"\r  Done: {indexed} indexed, {skipped} unchanged, {errors} errors",
                    file=sys.stderr,
                )

        return {
            "indexed": indexed,
            "skipped": skipped,
            "errors": errors,
            "total_files": len(emlx_files),
        }

    def search(self, query: str, *, limit: int = 20) -> list[dict[str, Any]]:
        """Full-text search over indexed message bodies.

        Uses FTS5 BM25 ranking for relevance.

        Args:
            query: Search query (FTS5 syntax — supports AND, OR, NOT, phrases).
            limit: Maximum results to return.

        Returns:
            List of dicts with: message_id, subject, sender, snippet, rank.
        """
        with closing(sqlite3.connect(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT
                    m.message_id,
                    m.subject,
                    m.sender,
                    snippet(messages_fts, 2, '**', '**', '...', 40) AS snippet,
                    rank
                FROM messages_fts
                JOIN messages m ON m.message_id = messages_fts.rowid
                WHERE messages_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def status(self) -> dict[str, Any]:
        """Return index statistics."""
        with closing(sqlite3.connect(self._db_path)) as conn:
            row = conn.execute("SELECT COUNT(*) FROM messages").fetchone()
            count = row[0] if row else 0

        db_path = Path(self._db_path)
        size_mb = db_path.stat().st_size / (1024 * 1024) if db_path.exists() else 0

        return {
            "indexed_messages": count,
            "index_path": self._db_path,
            "index_size_mb": round(size_mb, 1),
        }
