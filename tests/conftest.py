"""Shared test fixtures."""

import sqlite3

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
            mailbox INTEGER REFERENCES mailboxes(ROWID),
            conversation_id INTEGER DEFAULT 0
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

        INSERT INTO subjects VALUES (1, 'Test Subject');
        INSERT INTO subjects VALUES (2, 'Another Email');
        INSERT INTO subjects VALUES (3, 'Meeting Notes');

        INSERT INTO addresses VALUES (1, 'alice@example.com', 'Alice Smith');
        INSERT INTO addresses VALUES (2, 'bob@example.com', 'Bob Jones');
        INSERT INTO addresses VALUES (3, 'carol@example.com', 'Carol Lee');

        INSERT INTO mailboxes VALUES (1, 'imap://user@imap.mail.me.com/INBOX');
        INSERT INTO mailboxes VALUES (2, 'imap://user@imap.mail.me.com/Sent%20Messages');
        INSERT INTO mailboxes VALUES (3, 'imap://user@imap.mail.me.com/Junk');

        -- Messages 1 & 2 share conversation_id=100, message 3 is its own thread
        INSERT INTO messages VALUES (1, 1, 1, 1742400000, 1742400000, 0, 0, 0, 1, 100);
        INSERT INTO messages VALUES (2, 2, 2, 1742313600, 1742313600, 1, 0, 0, 1, 100);
        INSERT INTO messages VALUES (3, 3, 3, 1742227200, 1742227200, 0, 1, 0, 2, 200);
        INSERT INTO messages VALUES (4, 1, 1, 1742140800, 1742140800, 0, 0, 1, 1, 100);

        INSERT INTO recipients VALUES (1, 2, 0);
        INSERT INTO recipients VALUES (2, 3, 0);
        INSERT INTO recipients VALUES (3, 1, 0);

        INSERT INTO attachments VALUES (1, 3, 'report.pdf');
    """)
    conn.commit()
    conn.close()
    return str(db_path)
