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
