# apple-mail-py

Python library and CLI for Apple Mail on macOS.

## Architecture

```
src/apple_mail/
├── client.py            # MailClient: unified API (single entry point)
├── models.py            # Data classes: Message, Mailbox, Stats, MessageBody, Thread
├── db.py                # SQLite read-only access to Envelope Index
├── db_finder.py         # Auto-detect Mail database location
├── applescript.py       # AppleScript for read + write operations
├── cli.py               # Click CLI: `apple-mail` command
└── mcp_server.py        # FastMCP server (optional)
plugin/claude-code/      # Claude Code plugin
```

Dependency: `plugin → CLI (apple-mail --json) → MailClient → SQLite/AppleScript`

## Development

```bash
uv run pytest              # run tests
uv run apple-mail --help   # run CLI
just check                 # lint + type-check + test
```

## CLI conventions

- `apple-mail --json <command>` for structured JSON output
- `apple-mail --csv <command>` for CSV output
- Envelope: `{"status": "ok", "data": {...}}` or `{"status": "error", "error": {...}}`
- `--dry-run` on all write operations (mark-read, flag, archive, draft)
- `--copy` flag copies DB to temp file to avoid lock contention with Mail.app
- `--db` flag or `MAIL_DB` env var to override database path

## Key constraints

- `MailClient` is the only public API — all external consumers use it
- Methods return data classes (`Message`, `Mailbox`, `Stats`, `MessageBody`, `Thread`), never dicts
- CLI `--json` is the primary agent interface (not MCP — see ecosystem-architecture.md)
- AppleScript calls are lazy-imported to avoid subprocess overhead on read-only paths
- MCP dependency (`mcp` package) is optional — only needed for the server
- Database reads are via SQLite (fast), writes are via AppleScript (Mail.app)
- No delete operation — archive only (by design)
- No send — draft only (human reviews and sends)
- `snippet` field comes from Mail's `summaries` table (~14% coverage)
