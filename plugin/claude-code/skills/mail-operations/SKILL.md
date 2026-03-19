---
name: mail-operations
description: Use when the user asks about their email, wants to search mail, read messages, check unread, view threads, or perform any Apple Mail operation. Also use when they mention "email", "mail", "inbox", or ask about messages from a specific person.
---

# Apple Mail Operations

**Run CLI via the launcher:**
```bash
${CLAUDE_PLUGIN_ROOT}/bin/run apple-mail [--json] [--limit N] <command> [flags]
```

Global flags (`--json`, `--limit`, `--db`, `--copy`) go BEFORE the subcommand.

## CLI Commands (use `--json` for structured output)

### Search & Read
```bash
${CLAUDE_PLUGIN_ROOT}/bin/run apple-mail --json search --subject "invoice" --sender "alice" --days 7
${CLAUDE_PLUGIN_ROOT}/bin/run apple-mail --json subject "meeting notes"
${CLAUDE_PLUGIN_ROOT}/bin/run apple-mail --json sender "bob@example.com"
${CLAUDE_PLUGIN_ROOT}/bin/run apple-mail --json to "carol@example.com"
${CLAUDE_PLUGIN_ROOT}/bin/run apple-mail --json unread
${CLAUDE_PLUGIN_ROOT}/bin/run apple-mail --json recent 3
${CLAUDE_PLUGIN_ROOT}/bin/run apple-mail --json --limit 50 search --unread --days 1
${CLAUDE_PLUGIN_ROOT}/bin/run apple-mail --json body 12345
${CLAUDE_PLUGIN_ROOT}/bin/run apple-mail --json thread 12345
```

### Search Filters
- `--subject`, `--sender`, `--from-name`, `--to` — text matching
- `--unread` / `--read` — read status filter
- `--days N` — lookback window
- `--has-attachment` — only messages with attachments
- `--attachment-type pdf` — filter by extension
- `--limit 50` — max results (default: 20)

### Write Operations
```bash
${CLAUDE_PLUGIN_ROOT}/bin/run apple-mail --json mark-read 12345
${CLAUDE_PLUGIN_ROOT}/bin/run apple-mail --json mark-read 12345 --unread
${CLAUDE_PLUGIN_ROOT}/bin/run apple-mail --json flag 12345
${CLAUDE_PLUGIN_ROOT}/bin/run apple-mail --json flag 12345 --remove
${CLAUDE_PLUGIN_ROOT}/bin/run apple-mail --json archive 12345
${CLAUDE_PLUGIN_ROOT}/bin/run apple-mail --json draft --to "a@b.com" --subject "Re: Hello" --body "Thanks!"
```

All write operations support `--dry-run` to preview without executing.

### Attachments
```bash
${CLAUDE_PLUGIN_ROOT}/bin/run apple-mail --json attachments 12345
${CLAUDE_PLUGIN_ROOT}/bin/run apple-mail --json save-attachments 12345 -o ./downloads/
${CLAUDE_PLUGIN_ROOT}/bin/run apple-mail save-attachments 12345 --dry-run
```

### Export
```bash
${CLAUDE_PLUGIN_ROOT}/bin/run apple-mail --json export 12345
${CLAUDE_PLUGIN_ROOT}/bin/run apple-mail --json export 12345 --thread
${CLAUDE_PLUGIN_ROOT}/bin/run apple-mail export 12345 -o message.md
```

### Info
```bash
${CLAUDE_PLUGIN_ROOT}/bin/run apple-mail --json stats
${CLAUDE_PLUGIN_ROOT}/bin/run apple-mail --json mailboxes
```

## JSON Output Envelope

```json
{"status": "ok", "data": { ... }}
{"status": "error", "error": {"code": "...", "message": "..."}}
```

## Message Fields

Each message includes: `id`, `subject`, `sender`, `sender_name`, `date`, `mailbox`, `read`, `flagged`, `has_attachments`, `conversation_id`, `snippet`, `recipients`.

The `snippet` field contains message preview text when available (~14% of messages have it). For full content, use `body <id>`.

## Usage Patterns

**"What emails do I have?"** — `unread` or `recent 1`

**"Any email from Alice?"** — `sender "alice"`

**"Read that email"** — `body <id>`

**"What's the full conversation?"** — `thread <id>`, then `export <id> --thread` for readable markdown

**"Archive those newsletters"** — `archive <id>` for each. No delete — archive only.

**"Reply to Bob saying I'll be there"** — `draft --to "bob@example.com" --subject "Re: Meeting" --body "I'll be there."` — saves to Drafts, user sends manually.

**"Save the attachments from that email"** — `save-attachments <id> -o ~/Downloads/`
