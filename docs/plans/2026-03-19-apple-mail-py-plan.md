# apple-mail-py Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Port fruitmail-cli to Python as a split library/CLI following the apple-music-py architecture pattern.

**Architecture:** Split package — `apple_mail` (library, no CLI deps) + `clawmail` (Click CLI). SQLite for reads, AppleScript for open/body. FastMCP server for Claude Code integration.

**Tech Stack:** Python 3.12+, Click, sqlite3 (stdlib), subprocess (AppleScript), FastMCP (optional), hatchling (build)

---

### Task 1: Project scaffolding (pyproject.toml, __init__.py files, justfile)

**Files:**
- Create: `pyproject.toml`
- Create: `src/apple_mail/__init__.py`
- Create: `src/clawmail/__init__.py`
- Create: `justfile`
- Create: `.gitignore`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "apple-mail-py"
version = "0.1.0"
description = "Python library and CLI for reading Apple Mail on macOS"
readme = "README.md"
requires-python = ">=3.12"
dependencies = ["click>=8.1"]

[project.optional-dependencies]
mcp = ["mcp[cli]>=1.0"]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
    "ruff>=0.1",
    "mypy>=1.0",
    "build>=1.0",
]

[project.scripts]
apple-mail = "clawmail.cli:cli"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/clawmail", "src/apple_mail"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true

[tool.ruff]
src = ["src", "tests"]
line-length = 88
```

**Step 2: Create src/apple_mail/__init__.py**

```python
"""Python library for reading Apple Mail on macOS."""

from .client import MailClient
from .models import Mailbox, Message, MessageBody, Stats

__all__ = ["MailClient", "Mailbox", "Message", "MessageBody", "Stats"]
```

**Step 3: Create src/clawmail/__init__.py**

```python
"""CLI for Apple Mail."""

__version__ = "0.1.0"
```

**Step 4: Create justfile**

```just
# apple-mail-py development commands

default:
    @just --list

install:
    pip install -e ".[dev]"

lint: format-check lint-ruff type-check

format:
    ruff format src tests

format-check:
    ruff format --check src tests

lint-ruff:
    ruff check src tests

fix:
    ruff check --fix src tests
    ruff format src tests

type-check:
    mypy src/clawmail src/apple_mail

test:
    pytest -v

test-cov:
    pytest --cov=clawmail --cov=apple_mail --cov-report=term-missing

run *ARGS:
    python -m clawmail.cli {{ARGS}}

clean:
    rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/ .ruff_cache/ htmlcov/ .coverage
    find . -type d -name __pycache__ -exec rm -rf {} +

check: lint type-check test
```

**Step 5: Create .gitignore**

```
__pycache__/
*.egg-info/
dist/
build/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
*.pyc
.venv/
```

**Step 6: Commit**

```bash
git add pyproject.toml src/apple_mail/__init__.py src/clawmail/__init__.py justfile .gitignore
git commit -m "feat: project scaffolding with split library/CLI packages"
```

---

### Task 2: Data models (models.py)

**Files:**
- Create: `src/apple_mail/models.py`
- Create: `tests/test_models.py`

**Step 1: Write the test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd ~/repos/apple-mail-py && uv run pytest tests/test_models.py -v`
Expected: FAIL (ModuleNotFoundError)

**Step 3: Write models.py**

```python
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
```

**Step 4: Run test to verify it passes**

Run: `cd ~/repos/apple-mail-py && uv run pytest tests/test_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/apple_mail/models.py tests/test_models.py
git commit -m "feat: add data models — Message, Mailbox, Stats, MessageBody"
```

---

### Task 3: Database finder (db_finder.py)

**Files:**
- Create: `src/apple_mail/db_finder.py`
- Create: `tests/test_db_finder.py`

**Step 1: Write the test**

```python
"""Tests for Apple Mail database finder."""

import os
from pathlib import Path

from apple_mail.db_finder import find_mail_db


def test_env_override(tmp_path, monkeypatch):
    """MAIL_DB env var should override auto-detection."""
    db = tmp_path / "Envelope Index"
    db.touch()
    monkeypatch.setenv("MAIL_DB", str(db))
    assert find_mail_db() == str(db)


def test_env_override_missing(tmp_path, monkeypatch):
    """MAIL_DB pointing to missing file should raise."""
    monkeypatch.setenv("MAIL_DB", str(tmp_path / "nope"))
    try:
        find_mail_db()
        assert False, "Should have raised"
    except FileNotFoundError:
        pass


def test_auto_detect(tmp_path, monkeypatch):
    """Should find the highest version directory."""
    # Create V9 and V10 dirs
    v9 = tmp_path / "V9" / "MailData"
    v9.mkdir(parents=True)
    (v9 / "Envelope Index").touch()

    v10 = tmp_path / "V10" / "MailData"
    v10.mkdir(parents=True)
    (v10 / "Envelope Index").touch()

    monkeypatch.delenv("MAIL_DB", raising=False)
    result = find_mail_db(mail_dir=str(tmp_path))
    assert "V10" in result


def test_auto_detect_no_versions(tmp_path, monkeypatch):
    """No V* dirs should raise."""
    monkeypatch.delenv("MAIL_DB", raising=False)
    try:
        find_mail_db(mail_dir=str(tmp_path))
        assert False, "Should have raised"
    except FileNotFoundError:
        pass
```

**Step 2: Run test to verify it fails**

Run: `cd ~/repos/apple-mail-py && uv run pytest tests/test_db_finder.py -v`
Expected: FAIL

**Step 3: Write db_finder.py**

```python
"""Locate the Apple Mail SQLite database (Envelope Index)."""

from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_MAIL_DIR = "~/Library/Mail"


def find_mail_db(*, mail_dir: str | None = None) -> str:
    """Find the Envelope Index database path.

    Resolution order:
    1. MAIL_DB environment variable (explicit override)
    2. Auto-detect: scan ~/Library/Mail/V* for highest version

    Args:
        mail_dir: Override the base Mail directory (for testing).

    Returns:
        Absolute path to the Envelope Index file.

    Raises:
        FileNotFoundError: If the database cannot be located or
            the MAIL_DB path does not exist.
    """
    env_path = os.environ.get("MAIL_DB")
    if env_path:
        path = Path(env_path).expanduser()
        if not path.exists():
            raise FileNotFoundError(
                f"MAIL_DB points to a missing file: {env_path}\n"
                "Check the path or unset MAIL_DB to use auto-detection."
            )
        return str(path)

    base = Path(mail_dir or _DEFAULT_MAIL_DIR).expanduser()
    if not base.exists():
        raise FileNotFoundError(
            f"Mail directory not found: {base}\n"
            "Is Apple Mail installed? Check Full Disk Access in System Settings."
        )

    # Scan for V* directories, sort descending by version number
    versions = sorted(
        (d for d in base.iterdir() if d.is_dir() and d.name.startswith("V")),
        key=lambda d: int(d.name[1:]) if d.name[1:].isdigit() else 0,
        reverse=True,
    )

    for vdir in versions:
        candidate = vdir / "MailData" / "Envelope Index"
        if candidate.exists():
            return str(candidate)

    raise FileNotFoundError(
        f"No Envelope Index found in {base}/V*/MailData/\n"
        "Ensure Apple Mail has been run at least once and you have "
        "Full Disk Access enabled in System Settings > Privacy & Security."
    )
```

**Step 4: Run test to verify it passes**

Run: `cd ~/repos/apple-mail-py && uv run pytest tests/test_db_finder.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/apple_mail/db_finder.py tests/test_db_finder.py
git commit -m "feat: add database finder with auto-detect and MAIL_DB override"
```

---

### Task 4: Database layer (db.py)

**Files:**
- Create: `src/apple_mail/db.py`
- Create: `tests/test_db.py`
- Create: `tests/conftest.py` (shared fixture for test DB)

**Step 1: Write conftest.py with a test database fixture**

This creates an in-memory SQLite database mimicking the Apple Mail schema so we can test queries without needing a real Mail database.

```python
"""Shared test fixtures."""

import sqlite3
from pathlib import Path

import pytest


@pytest.fixture()
def mail_db(tmp_path):
    """Create a minimal Apple Mail SQLite database for testing."""
    db_path = tmp_path / "Envelope Index"
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE subjects (
            ROWID INTEGER PRIMARY KEY,
            subject TEXT
        );
        CREATE TABLE addresses (
            ROWID INTEGER PRIMARY KEY,
            address TEXT,
            comment TEXT
        );
        CREATE TABLE mailboxes (
            ROWID INTEGER PRIMARY KEY,
            url TEXT
        );
        CREATE TABLE messages (
            ROWID INTEGER PRIMARY KEY,
            subject INTEGER REFERENCES subjects(ROWID),
            sender INTEGER REFERENCES addresses(ROWID),
            date_sent REAL,
            date_received REAL,
            read INTEGER DEFAULT 0,
            flagged INTEGER DEFAULT 0,
            deleted INTEGER DEFAULT 0,
            mailbox INTEGER REFERENCES mailboxes(ROWID)
        );
        CREATE TABLE recipients (
            message_id INTEGER REFERENCES messages(ROWID),
            address_id INTEGER REFERENCES addresses(ROWID),
            type INTEGER DEFAULT 0
        );
        CREATE TABLE attachments (
            ROWID INTEGER PRIMARY KEY,
            message_id INTEGER REFERENCES messages(ROWID),
            name TEXT
        );

        -- Seed data
        INSERT INTO subjects VALUES (1, 'Test Subject');
        INSERT INTO subjects VALUES (2, 'Another Email');
        INSERT INTO subjects VALUES (3, 'Meeting Notes');

        INSERT INTO addresses VALUES (1, 'alice@example.com', 'Alice Smith');
        INSERT INTO addresses VALUES (2, 'bob@example.com', 'Bob Jones');
        INSERT INTO addresses VALUES (3, 'carol@example.com', 'Carol Lee');

        INSERT INTO mailboxes VALUES (1, 'imap://user@imap.mail.me.com/INBOX');
        INSERT INTO mailboxes VALUES (2, 'imap://user@imap.mail.me.com/Sent%20Messages');
        INSERT INTO mailboxes VALUES (3, 'imap://user@imap.mail.me.com/Junk');

        -- Messages: date_sent is Unix timestamp
        INSERT INTO messages VALUES (1, 1, 1, 1742400000, 1742400000, 0, 0, 0, 1);
        INSERT INTO messages VALUES (2, 2, 2, 1742313600, 1742313600, 1, 0, 0, 1);
        INSERT INTO messages VALUES (3, 3, 3, 1742227200, 1742227200, 0, 1, 0, 2);
        INSERT INTO messages VALUES (4, 1, 1, 1742140800, 1742140800, 0, 0, 1, 1);

        -- Recipients
        INSERT INTO recipients VALUES (1, 2, 0);
        INSERT INTO recipients VALUES (2, 3, 0);
        INSERT INTO recipients VALUES (3, 1, 0);

        -- Attachments
        INSERT INTO attachments VALUES (1, 3, 'report.pdf');
    """)
    conn.commit()
    conn.close()
    return str(db_path)
```

**Step 2: Write db tests**

```python
"""Tests for Apple Mail database layer."""

from apple_mail.db import MailDB


def test_search_all(mail_db):
    db = MailDB(mail_db)
    results = db.search(limit=10)
    # 3 non-deleted messages
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
    assert s["total"] == 3  # excludes deleted
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
    # Should be friendly names, not raw URLs
    assert "Inbox" in mailbox_names or "INBOX" in mailbox_names


def test_copy_mode(mail_db):
    """Copy mode should work by copying the DB to a temp file."""
    db = MailDB(mail_db, copy_mode=True)
    results = db.search(limit=10)
    assert len(results) == 3
```

**Step 3: Run tests to verify they fail**

Run: `cd ~/repos/apple-mail-py && uv run pytest tests/test_db.py -v`
Expected: FAIL

**Step 4: Write db.py**

```python
"""SQLite read-only access to the Apple Mail Envelope Index database."""

from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
from contextlib import closing
from typing import Any

from .db_finder import find_mail_db

# Friendly name mapping for common mailbox URL patterns
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
    """Convert a mailbox URL/path to a friendly display name."""
    if not url:
        return "Unknown"
    # Extract the last path component, URL-decode common patterns
    name = url.rstrip("/").rsplit("/", 1)[-1].replace("%20", " ")
    return _MAILBOX_NAMES.get(name, name)


class MailDB:
    """Read-only interface to the Apple Mail SQLite database.

    Args:
        db_path: Explicit path to Envelope Index. If None, auto-detected.
        copy_mode: If True, copy the DB to a temp file before reading
            to avoid lock contention with Mail.app.
    """

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

    def _detect_columns(self) -> dict[str, bool]:
        """Detect which optional columns exist in the messages table."""
        rows = self._query("PRAGMA table_info(messages)")
        cols = {r["name"] for r in rows}
        return {
            "flagged": "flagged" in cols,
            "date_received": "date_received" in cols,
        }

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
        """Search messages with optional filters.

        Returns list of dicts with keys: id, subject, sender, sender_name,
        date, mailbox, read, flagged, has_attachments, recipients.
        """
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
            joins.append(
                "INNER JOIN attachments att ON att.message_id = m.ROWID"
            )
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
            conditions.append(
                "m.date_sent >= strftime('%s', 'now', ?)"
            )
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

        # Post-process: add friendly mailbox names and fetch recipients
        for row in rows:
            row["mailbox"] = _friendly_mailbox(row.pop("mailbox_url", None))
            row["recipients"] = self._get_recipients(row["id"])

        return rows

    def _get_recipients(self, message_id: int) -> list[str]:
        """Fetch recipient addresses for a message."""
        sql = """
        SELECT a.address
        FROM recipients r
        INNER JOIN addresses a ON r.address_id = a.ROWID
        WHERE r.message_id = ?
        """
        rows = self._query(sql, (message_id,))
        return [r["address"] for r in rows]

    def get_message(self, message_id: int) -> dict[str, Any] | None:
        """Get a single message by ROWID."""
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
        """Return database-level statistics."""
        sql = """
        SELECT
            COUNT(*) FILTER (WHERE deleted = 0) AS total,
            COUNT(*) FILTER (WHERE deleted = 0 AND read = 0) AS unread,
            COUNT(*) FILTER (WHERE deleted = 1) AS deleted,
            (SELECT COUNT(DISTINCT message_id) FROM attachments) AS with_attachments
        FROM messages
        """
        # FILTER syntax requires SQLite 3.30+; use CASE fallback for safety
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
        """List all mailboxes."""
        sql = """
        SELECT
            mb.ROWID AS id,
            mb.url AS path
        FROM mailboxes mb
        ORDER BY mb.url
        """
        rows = self._query(sql)
        for row in rows:
            row["name"] = _friendly_mailbox(row["path"])
            row["account"] = _extract_account(row["path"])
        return rows


def _extract_account(url: str | None) -> str:
    """Extract account identifier from a mailbox URL."""
    if not url or "://" not in url:
        return ""
    # imap://user@host/... → user@host
    after_scheme = url.split("://", 1)[1]
    return after_scheme.split("/", 1)[0]
```

**Step 5: Run tests to verify they pass**

Run: `cd ~/repos/apple-mail-py && uv run pytest tests/test_db.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/apple_mail/db.py tests/test_db.py tests/conftest.py
git commit -m "feat: add SQLite database layer with search, stats, mailboxes"
```

---

### Task 5: AppleScript layer (applescript.py)

**Files:**
- Create: `src/apple_mail/applescript.py`
- Create: `tests/test_applescript.py`

**Step 1: Write the test**

Tests for AppleScript must mock `subprocess.run` since we can't depend on Mail.app in CI.

```python
"""Tests for Apple Mail AppleScript layer."""

import json
import subprocess

from apple_mail.applescript import (
    _build_lookup_script,
    _escape_applescript,
    get_message_body,
    open_message,
)


def test_escape_applescript():
    assert _escape_applescript('say "hello"') == 'say \\"hello\\"'
    assert _escape_applescript("it's") == "it\\'s"
    assert _escape_applescript("back\\slash") == "back\\\\slash"


def test_build_lookup_script_by_id():
    script = _build_lookup_script(message_id=42, mode="content")
    assert "42" in script
    assert "content" in script.lower() or "body" in script.lower()


def test_open_message_calls_osascript(monkeypatch):
    called = {}

    def mock_run(cmd, **kwargs):
        called["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)
    open_message(message_id=42, subject="Hello", sender="a@b.com")
    assert "osascript" in called["cmd"][0]


def test_get_body_returns_content(monkeypatch):
    def mock_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout="Email body text\n", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)
    body = get_message_body(message_id=42, subject="Hello", sender="a@b.com")
    assert body == "Email body text"


def test_get_body_not_found(monkeypatch):
    def mock_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout="__NOT_FOUND__\n", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)
    try:
        get_message_body(message_id=42, subject="Hello", sender="a@b.com")
        assert False, "Should have raised"
    except RuntimeError as e:
        assert "not found" in str(e).lower()
```

**Step 2: Run test to verify it fails**

Run: `cd ~/repos/apple-mail-py && uv run pytest tests/test_applescript.py -v`
Expected: FAIL

**Step 3: Write applescript.py**

This is the Python port of fruitmail-cli's `mail-actions.ts`. The AppleScript locates messages by searching all mailboxes, matching by message ID or subject+sender.

```python
"""AppleScript interaction with Mail.app for open and body operations."""

from __future__ import annotations

import subprocess

_NOT_FOUND = "__NOT_FOUND__"
_SCRIPT_ERROR = "__SCRIPT_ERROR__"


def _escape_applescript(s: str) -> str:
    """Escape a string for safe embedding in AppleScript literals."""
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("'", "\\'")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def _run_applescript(script: str) -> str:
    """Execute AppleScript via osascript and return stdout."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(f"AppleScript error: {stderr}")
    return result.stdout.strip()


def _build_lookup_script(
    *,
    message_id: int,
    subject: str | None = None,
    sender: str | None = None,
    mailbox_hint: str | None = None,
    mode: str = "content",
) -> str:
    """Build AppleScript to find and act on a message.

    Args:
        message_id: The ROWID from the database.
        subject: Subject line for fallback matching.
        sender: Sender address for fallback matching.
        mailbox_hint: Partial mailbox name to narrow search.
        mode: "content" to return body text, "open" to display in Mail.

    Returns:
        AppleScript source code as a string.
    """
    safe_subject = _escape_applescript(subject or "")
    safe_sender = _escape_applescript(sender or "")

    action = 'return content of foundMsg' if mode == "content" else (
        'set visible of foundMsg to true\n'
        'activate\n'
        'return "OK"'
    )

    script = f'''
tell application "Mail"
    set foundMsg to missing value
    set allMailboxes to every mailbox of every account

    repeat with acctBoxes in allMailboxes
        repeat with mb in acctBoxes
            try
                set msgs to (messages of mb whose id is {message_id})
                if (count of msgs) > 0 then
                    set foundMsg to item 1 of msgs
                    exit repeat
                end if
            end try
        end repeat
        if foundMsg is not missing value then exit repeat
    end repeat

    -- Fallback: search by subject + sender
    if foundMsg is missing value then
        repeat with acctBoxes in allMailboxes
            repeat with mb in acctBoxes
                try
                    set msgs to (messages of mb whose subject contains "{safe_subject}" and sender contains "{safe_sender}")
                    if (count of msgs) > 0 then
                        set foundMsg to item 1 of msgs
                        exit repeat
                    end if
                end try
            end repeat
            if foundMsg is not missing value then exit repeat
        end repeat
    end if

    if foundMsg is missing value then
        return "{_NOT_FOUND}"
    end if

    {action}
end tell
'''
    return script


def open_message(
    *,
    message_id: int,
    subject: str | None = None,
    sender: str | None = None,
) -> None:
    """Open a message in Mail.app.

    Raises:
        RuntimeError: If the message cannot be found.
    """
    script = _build_lookup_script(
        message_id=message_id,
        subject=subject,
        sender=sender,
        mode="open",
    )
    result = _run_applescript(script)
    if result == _NOT_FOUND:
        raise RuntimeError(f"Message {message_id} not found in Mail.app")


def get_message_body(
    *,
    message_id: int,
    subject: str | None = None,
    sender: str | None = None,
) -> str:
    """Get the full body text of a message via AppleScript.

    Returns:
        Plain text body content.

    Raises:
        RuntimeError: If the message cannot be found.
    """
    script = _build_lookup_script(
        message_id=message_id,
        subject=subject,
        sender=sender,
        mode="content",
    )
    result = _run_applescript(script)
    if result == _NOT_FOUND:
        raise RuntimeError(f"Message {message_id} not found in Mail.app")
    return result
```

**Step 4: Run test to verify it passes**

Run: `cd ~/repos/apple-mail-py && uv run pytest tests/test_applescript.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/apple_mail/applescript.py tests/test_applescript.py
git commit -m "feat: add AppleScript layer for open and body operations"
```

---

### Task 6: Client layer (client.py)

**Files:**
- Create: `src/apple_mail/client.py`
- Create: `tests/test_client.py`

**Step 1: Write the test**

```python
"""Tests for MailClient."""

from apple_mail.client import MailClient


def test_search(mail_db):
    client = MailClient(db_path=mail_db)
    messages = client.search(limit=10)
    assert len(messages) == 3
    # Should return Message dataclasses
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
```

**Step 2: Run test to verify it fails**

Run: `cd ~/repos/apple-mail-py && uv run pytest tests/test_client.py -v`
Expected: FAIL

**Step 3: Write client.py**

```python
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
```

**Step 4: Run test to verify it passes**

Run: `cd ~/repos/apple-mail-py && uv run pytest tests/test_client.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/apple_mail/client.py tests/test_client.py
git commit -m "feat: add MailClient — unified entry point for all operations"
```

---

### Task 7: CLI layer (clawmail/cli.py)

**Files:**
- Create: `src/clawmail/cli.py`
- Create: `tests/test_cli.py`

**Step 1: Write the test**

```python
"""Tests for the apple-mail CLI."""

import json

from click.testing import CliRunner

from clawmail.cli import cli


def test_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "search" in result.output


def test_stats_json(mail_db):
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "--db", mail_db, "stats"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "ok"
    assert data["data"]["total"] == 3


def test_search_json(mail_db):
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "--db", mail_db, "search"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "ok"
    assert len(data["data"]) == 3


def test_search_subject_json(mail_db):
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "--db", mail_db, "subject", "Test"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data["data"]) == 1


def test_search_sender_json(mail_db):
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "--db", mail_db, "sender", "alice"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data["data"]) == 1


def test_unread_json(mail_db):
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "--db", mail_db, "unread"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert all(not m["read"] for m in data["data"])


def test_mailboxes_json(mail_db):
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "--db", mail_db, "mailboxes"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "ok"


def test_stats_human(mail_db):
    runner = CliRunner()
    result = runner.invoke(cli, ["--db", mail_db, "stats"])
    assert result.exit_code == 0
    assert "Total" in result.output or "total" in result.output


def test_search_csv(mail_db):
    runner = CliRunner()
    result = runner.invoke(cli, ["--csv", "--db", mail_db, "search"])
    assert result.exit_code == 0
    lines = result.output.strip().split("\n")
    assert len(lines) >= 2  # header + data rows


def test_recent_json(mail_db):
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "--db", mail_db, "recent"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "ok"
```

**Step 2: Run test to verify it fails**

Run: `cd ~/repos/apple-mail-py && uv run pytest tests/test_cli.py -v`
Expected: FAIL

**Step 3: Write cli.py**

```python
"""Click CLI for Apple Mail — thin layer over MailClient."""

from __future__ import annotations

import csv
import io
import json
import sys
from dataclasses import asdict

import click

from apple_mail.client import MailClient


@click.group()
@click.option("--json", "as_json", is_flag=True, envvar="APPLE_MAIL_OUTPUT",
              help="Output as JSON (structured envelope).")
@click.option("--csv", "as_csv", is_flag=True,
              help="Output as CSV.")
@click.option("--db", "db_path", default=None, envvar="MAIL_DB",
              help="Path to Envelope Index database.")
@click.option("--copy", "copy_mode", is_flag=True,
              help="Copy database to temp file before reading (avoids lock contention).")
@click.option("-n", "--limit", default=20, type=int,
              help="Max results to return (default: 20).")
@click.pass_context
def cli(ctx, as_json, as_csv, db_path, copy_mode, limit):
    """Read and search Apple Mail from the command line."""
    ctx.ensure_object(dict)
    ctx.obj["client"] = MailClient(db_path=db_path, copy_mode=copy_mode)
    ctx.obj["json"] = as_json
    ctx.obj["csv"] = as_csv
    ctx.obj["limit"] = limit


def _client(ctx) -> MailClient:
    return ctx.obj["client"]


def _output_json(ctx) -> bool:
    return ctx.obj["json"]


def _output_csv(ctx) -> bool:
    return ctx.obj["csv"]


def _limit(ctx) -> int:
    return ctx.obj["limit"]


def _emit(ctx, data):
    """Emit structured JSON envelope: {"status": "ok", "data": ...}."""
    click.echo(json.dumps({"status": "ok", "data": data}, indent=2, default=str))


def _emit_error(code: str, message: str):
    """Emit structured JSON error envelope."""
    click.echo(
        json.dumps({"status": "error", "error": {"code": code, "message": message}}, indent=2),
        err=True,
    )
    sys.exit(1)


def _emit_messages(ctx, messages):
    """Output a list of messages in the requested format."""
    data = [asdict(m) for m in messages]

    if _output_json(ctx):
        _emit(ctx, data)
        return

    if _output_csv(ctx):
        _write_csv(data, ["id", "date", "sender", "subject", "mailbox", "read"])
        return

    if not messages:
        click.echo("No messages found.")
        return

    for m in messages:
        flag = "*" if m.flagged else " "
        read = " " if m.read else "●"
        date = m.date[:16] if len(m.date) > 16 else m.date
        click.echo(f" {read}{flag} {m.id:>6}  {date}  {m.sender:<30.30}  {m.subject:<50.50}  {m.mailbox}")


def _write_csv(data: list[dict], fields: list[str]):
    """Write CSV to stdout."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(data)
    click.echo(buf.getvalue().rstrip())


# ── search ─────────────────────────────────────────────────────────────────

@cli.command("search")
@click.option("--subject", default=None, help="Match subject line.")
@click.option("--sender", default=None, help="Match sender email.")
@click.option("--from-name", default=None, help="Match sender display name.")
@click.option("--to", default=None, help="Match recipient.")
@click.option("--unread", is_flag=True, default=False, help="Only unread messages.")
@click.option("--read", "only_read", is_flag=True, default=False, help="Only read messages.")
@click.option("--days", default=None, type=int, help="Lookback window in days.")
@click.option("--has-attachment", is_flag=True, default=False, help="Only messages with attachments.")
@click.option("--attachment-type", default=None, help="Filter by attachment extension (e.g. pdf).")
@click.pass_context
def search_cmd(ctx, subject, sender, from_name, to, unread, only_read, days, has_attachment, attachment_type):
    """Search messages with filters."""
    client = _client(ctx)
    unread_filter = True if unread else (False if only_read else None)
    messages = client.search(
        subject=subject, sender=sender, from_name=from_name, to=to,
        unread=unread_filter, days=days, has_attachment=has_attachment,
        attachment_type=attachment_type, limit=_limit(ctx),
    )
    _emit_messages(ctx, messages)


# ── shortcuts ──────────────────────────────────────────────────────────────

@cli.command("subject")
@click.argument("pattern")
@click.pass_context
def subject_cmd(ctx, pattern):
    """Search by subject."""
    client = _client(ctx)
    messages = client.search(subject=pattern, limit=_limit(ctx))
    _emit_messages(ctx, messages)


@cli.command("sender")
@click.argument("pattern")
@click.pass_context
def sender_cmd(ctx, pattern):
    """Search by sender."""
    client = _client(ctx)
    messages = client.search(sender=pattern, limit=_limit(ctx))
    _emit_messages(ctx, messages)


@cli.command("to")
@click.argument("pattern")
@click.pass_context
def to_cmd(ctx, pattern):
    """Search by recipient."""
    client = _client(ctx)
    messages = client.search(to=pattern, limit=_limit(ctx))
    _emit_messages(ctx, messages)


@cli.command("unread")
@click.pass_context
def unread_cmd(ctx):
    """List unread messages."""
    client = _client(ctx)
    messages = client.unread(limit=_limit(ctx))
    _emit_messages(ctx, messages)


@cli.command("recent")
@click.argument("days", default=7, type=int)
@click.pass_context
def recent_cmd(ctx, days):
    """Show recent messages (default: 7 days)."""
    client = _client(ctx)
    messages = client.recent(days=days, limit=_limit(ctx))
    _emit_messages(ctx, messages)


# ── message operations ─────────────────────────────────────────────────────

@cli.command("open")
@click.argument("id", type=int)
@click.pass_context
def open_cmd(ctx, id):
    """Open a message in Mail.app."""
    client = _client(ctx)
    try:
        client.open_message(id)
        if _output_json(ctx):
            _emit(ctx, {"opened": id})
        else:
            click.echo(f"Opened message {id} in Mail.app")
    except RuntimeError as e:
        if _output_json(ctx):
            _emit_error("not_found", str(e))
        else:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)


@cli.command("body")
@click.argument("id", type=int)
@click.pass_context
def body_cmd(ctx, id):
    """Get the full body of a message."""
    client = _client(ctx)
    try:
        msg_body = client.get_body(id)
        if _output_json(ctx):
            _emit(ctx, asdict(msg_body))
        else:
            click.echo(msg_body.body)
    except RuntimeError as e:
        if _output_json(ctx):
            _emit_error("not_found", str(e))
        else:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)


# ── stats ──────────────────────────────────────────────────────────────────

@cli.command("stats")
@click.pass_context
def stats_cmd(ctx):
    """Show database statistics."""
    client = _client(ctx)
    stats = client.stats()

    if _output_json(ctx):
        _emit(ctx, asdict(stats))
        return

    if _output_csv(ctx):
        _write_csv([asdict(stats)], ["total", "unread", "deleted", "with_attachments"])
        return

    click.echo(f"  Total:            {stats.total:,}")
    click.echo(f"  Unread:           {stats.unread:,}")
    click.echo(f"  Deleted:          {stats.deleted:,}")
    click.echo(f"  With attachments: {stats.with_attachments:,}")


# ── mailboxes ──────────────────────────────────────────────────────────────

@cli.command("mailboxes")
@click.pass_context
def mailboxes_cmd(ctx):
    """List all mailboxes."""
    client = _client(ctx)
    mbs = client.mailboxes()

    if _output_json(ctx):
        _emit(ctx, [asdict(mb) for mb in mbs])
        return

    if not mbs:
        click.echo("No mailboxes found.")
        return

    for mb in mbs:
        acct = f"({mb.account})" if mb.account else ""
        click.echo(f"  {mb.name:<30} {acct}")
```

**Step 4: Run test to verify it passes**

Run: `cd ~/repos/apple-mail-py && uv run pytest tests/test_cli.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/clawmail/cli.py tests/test_cli.py
git commit -m "feat: add Click CLI with search, shortcuts, stats, mailboxes, open, body"
```

---

### Task 8: MCP server (server.py)

**Files:**
- Create: `src/apple_mail/server.py`

**Step 1: Write server.py**

```python
"""MCP server for Apple Mail."""

from __future__ import annotations

from dataclasses import asdict

try:
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError:
    raise SystemExit(
        "apple-mail MCP server requires the 'mcp' package.\n"
        "Install with: pip install 'apple-mail-py[mcp]'"
    )

from .client import MailClient

mcp = FastMCP("Apple Mail", json_response=True)
client = MailClient()


@mcp.tool()
def search_messages(
    subject: str | None = None,
    sender: str | None = None,
    from_name: str | None = None,
    to: str | None = None,
    unread: bool | None = None,
    days: int | None = None,
    has_attachment: bool = False,
    limit: int = 20,
) -> list[dict] | dict:
    """Search Apple Mail messages with optional filters."""
    try:
        messages = client.search(
            subject=subject, sender=sender, from_name=from_name,
            to=to, unread=unread, days=days,
            has_attachment=has_attachment, limit=limit,
        )
        return [asdict(m) for m in messages]
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def get_unread(limit: int = 20) -> list[dict] | dict:
    """Get unread messages from Apple Mail."""
    try:
        return [asdict(m) for m in client.unread(limit=limit)]
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def get_recent(days: int = 7, limit: int = 20) -> list[dict] | dict:
    """Get recent messages from Apple Mail."""
    try:
        return [asdict(m) for m in client.recent(days=days, limit=limit)]
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def get_stats() -> dict:
    """Get Apple Mail database statistics."""
    try:
        return asdict(client.stats())
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def get_mailboxes() -> list[dict] | dict:
    """List all Apple Mail mailboxes."""
    try:
        return [asdict(mb) for mb in client.mailboxes()]
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def get_message_body(message_id: int) -> dict:
    """Get the full body text of a message."""
    try:
        return asdict(client.get_body(message_id))
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def open_message(message_id: int) -> dict:
    """Open a message in Mail.app."""
    try:
        client.open_message(message_id)
        return {"opened": message_id}
    except Exception as exc:
        return {"error": str(exc)}


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
```

**Step 2: Commit**

```bash
git add src/apple_mail/server.py
git commit -m "feat: add FastMCP server with search, stats, mailboxes, body, open tools"
```

---

### Task 9: Claude Code plugin

**Files:**
- Create: `plugin/claude-code/.claude-plugin/plugin.json`
- Create: `plugin/claude-code/.mcp.json`

**Step 1: Create plugin.json**

```json
{
  "name": "apple-mail",
  "version": "0.1.0",
  "description": "Apple Mail — search, read, and open emails",
  "keywords": ["apple-mail", "email", "mail", "mcp"]
}
```

**Step 2: Create .mcp.json**

```json
{
  "apple-mail": {
    "type": "stdio",
    "command": "python3",
    "args": ["-m", "apple_mail.server"]
  }
}
```

**Step 3: Commit**

```bash
git add plugin/
git commit -m "feat: add Claude Code plugin with MCP server config"
```

---

### Task 10: CLAUDE.md and final wiring

**Files:**
- Create: `CLAUDE.md`
- Update: `src/apple_mail/__init__.py` (verify exports)

**Step 1: Create CLAUDE.md**

```markdown
# apple-mail-py

Python library and CLI for reading Apple Mail on macOS.

## Architecture

```
src/
├── apple_mail/              # Access library (no CLI dependencies)
│   ├── client.py            # MailClient: unified API (single entry point)
│   ├── models.py            # Data classes: Message, Mailbox, Stats, MessageBody
│   ├── db.py                # SQLite read-only access to Envelope Index
│   ├── db_finder.py         # Auto-detect Mail database location
│   ├── applescript.py       # AppleScript for open/body operations
│   └── server.py            # FastMCP server (optional)
├── clawmail/                # CLI package (consumes apple_mail)
│   └── cli.py               # Click-based commands
plugin/
  claude-code/               # Claude Code plugin (MCP server)
```

Dependency direction: `plugin → CLI (apple-mail) → MailClient (apple_mail) → SQLite/AppleScript`

## Development

```bash
uv run pytest              # run tests
uv run apple-mail --help   # run CLI
uv sync --extra mcp --extra dev  # full install
just check                 # lint + type-check + test
```

## CLI conventions

- `apple-mail --json <command>` for structured JSON output
- `apple-mail --csv <command>` for CSV output
- Envelope: `{"status": "ok", "data": ...}` or `{"status": "error", "error": {...}}`
- `--copy` flag copies DB to temp file to avoid lock contention with Mail.app
- `--db` flag or `MAIL_DB` env var to override database path

## Key constraints

- `MailClient` is the only public API — all external consumers use it
- Methods return data classes (`Message`, `Mailbox`, `Stats`, `MessageBody`), never dicts
- AppleScript calls are lazy-imported to avoid subprocess overhead on read-only paths
- MCP dependency (`mcp` package) is optional — only needed for the server
- Database access is strictly read-only
```

**Step 2: Run all tests**

Run: `cd ~/repos/apple-mail-py && uv run pytest -v`
Expected: All tests pass

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "feat: add CLAUDE.md with architecture documentation"
```

---

### Task 11: Run full check and verify

**Step 1: Install and run tests**

```bash
cd ~/repos/apple-mail-py
uv sync --extra dev
uv run pytest -v
```

Expected: All tests pass

**Step 2: Try the CLI help**

```bash
uv run apple-mail --help
```

Expected: Shows help with all commands listed

**Step 3: Run linter**

```bash
uv run ruff check src tests
uv run ruff format --check src tests
```

Fix any issues found.

**Step 4: Final commit (if any fixes)**

```bash
git add -A
git commit -m "fix: address linter findings"
```
