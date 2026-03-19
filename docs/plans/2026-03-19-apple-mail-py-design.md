# apple-mail-py Design

**Date:** 2026-03-19
**Status:** Approved
**Source:** Port of [fruitmail-cli](https://github.com/gumadeiras/fruitmail-cli) (TypeScript) to Python
**Architecture:** Follows apple-music-py / apple-notes-py / omnifocus-py patterns

## Overview

Python CLI and library for reading Apple Mail via direct SQLite access (fast search) and AppleScript (message open/body). Split into a zero-dependency access library (`apple_mail`) and a Click-based CLI (`clawmail`).

## File Structure

```
apple-mail-py/
├── src/
│   ├── apple_mail/              # Access library (no CLI deps)
│   │   ├── __init__.py          # Exports: MailClient, Message, Mailbox, Stats
│   │   ├── models.py            # Dataclasses
│   │   ├── client.py            # MailClient: single entry point
│   │   ├── db.py                # SQLite read-only (Envelope Index)
│   │   ├── db_finder.py         # Locate Mail DB across V9/V10+
│   │   ├── applescript.py       # osascript for open/body
│   │   └── server.py            # FastMCP server
│   └── clawmail/                # CLI package
│       ├── __init__.py          # __version__
│       └── cli.py               # Click commands
├── plugin/claude-code/
│   ├── .claude-plugin/plugin.json
│   └── .mcp.json
├── pyproject.toml
└── justfile
```

## Data Models

```python
@dataclass
class Message:
    id: int              # ROWID
    subject: str
    sender: str          # email address
    sender_name: str     # display name
    date: str            # ISO 8601
    mailbox: str         # friendly name
    read: bool
    flagged: bool
    has_attachments: bool
    recipients: list[str]

@dataclass
class Mailbox:
    id: int
    name: str
    path: str
    account: str

@dataclass
class Stats:
    total: int
    unread: int
    deleted: int
    with_attachments: int

@dataclass
class MessageBody:
    id: int
    subject: str
    sender: str
    body: str
```

## Database Layer

- Read-only SQLite connection to `~/Library/Mail/V10/MailData/Envelope Index`
- Tables: messages, subjects, addresses, recipients, mailboxes, attachments
- Dynamic filter builder for search
- Friendly mailbox name mapping (URL → "Inbox", "Sent", etc.)
- Copy mode: shutil.copy2 to tempfile before opening (avoids lock contention)

## DB Finder

- Scan ~/Library/Mail/V* directories, sort descending
- Return first with valid MailData/Envelope Index
- MAIL_DB env var override
- Helpful error on Full Disk Access permission failure

## AppleScript Layer

- open_message(context): activate Mail.app, display message
- get_message_body(context): extract plain text via `content of`
- Lookup context: numeric IDs, message IDs, subject+sender, mailbox hints
- String escaping via json.dumps()

## Client API

```python
class MailClient:
    def __init__(self, db_path=None, copy_mode=False): ...

    # Read (SQLite)
    def search(subject, sender, from_name, to, unread, days, has_attachment, attachment_type, limit) -> list[Message]
    def recent(days, limit) -> list[Message]
    def unread(limit) -> list[Message]
    def stats() -> Stats
    def mailboxes() -> list[Mailbox]

    # App interaction (AppleScript)
    def open_message(message_id) -> None
    def get_body(message_id) -> MessageBody
```

## CLI Commands

```
apple-mail [--json] [--csv] [--db PATH] [--copy] [--limit N]
  search    --subject --sender --from-name --to --unread --read
            --days --has-attachment --attachment-type
  subject   <pattern>
  sender    <pattern>
  to        <pattern>
  unread
  recent    [days]
  open      <id>
  body      <id>
  stats
  mailboxes
```

## Output Formats

- JSON: `{"status": "ok", "data": ...}` envelope (matching siblings)
- CSV: csv.DictWriter
- Human: table with truncated columns

## MCP Server

FastMCP over stdio, tools mapping 1:1 to client methods. Same pattern as omnifocus-py.

## Plugin

Standard .claude-plugin/plugin.json + .mcp.json + skills directory.
