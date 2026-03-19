---
name: mail-operations
description: Use when the user asks about their email, wants to search mail, read messages, check unread, view threads, or perform any Apple Mail operation. Also use when they mention "email", "mail", "inbox", or ask about messages from a specific person.
---

# Apple Mail Operations

**IMPORTANT:** Global flags (`--json`, `--limit`, `--db`, `--copy`) go BEFORE the subcommand. Subcommand flags go after.

```
apple-mail [--json] [--limit N] [--db PATH] [--copy] <command> [command-flags]
```

## CLI Commands (preferred — use `--json` for structured output)

### Search & Read
```bash
apple-mail --json search --subject "invoice" --sender "alice" --days 7
apple-mail --json subject "meeting notes"
apple-mail --json sender "bob@example.com"
apple-mail --json to "carol@example.com"
apple-mail --json unread
apple-mail --json recent 3                    # last 3 days
apple-mail --json --limit 50 search --unread --days 1  # combine global + subcommand flags
apple-mail --json body 12345                  # full body of message ID
apple-mail --json thread 12345                # all messages in conversation
```

### Search Filters
- `--subject`, `--sender`, `--from-name`, `--to` — text matching
- `--unread` / `--read` — read status filter
- `--days N` — lookback window
- `--has-attachment` — only messages with attachments
- `--attachment-type pdf` — filter by extension
- `-n 50` — max results (default: 20)

### Write Operations
```bash
apple-mail --json mark-read 12345             # mark as read
apple-mail --json mark-read 12345 --unread    # mark as unread
apple-mail --json flag 12345                  # flag message
apple-mail --json flag 12345 --remove         # unflag
apple-mail --json archive 12345               # move to Archive
apple-mail --json draft --to "a@b.com" --subject "Re: Hello" --body "Thanks!"
```

All write operations support `--dry-run` to preview without executing.

### Attachments
```bash
apple-mail --json attachments 12345           # list attachments for a message
apple-mail --json save-attachments 12345 -o ./downloads/  # save to directory
apple-mail save-attachments 12345 --dry-run   # preview what would be saved
```

### Export
```bash
apple-mail --json export 12345                # single message as markdown
apple-mail --json export 12345 --thread       # full thread as markdown
apple-mail export 12345 -o message.md         # save to file
```

### Info
```bash
apple-mail --json stats                       # total, unread, deleted counts
apple-mail --json mailboxes                   # list all mailboxes
```

## JSON Output Envelope

All `--json` output follows the standard envelope:
```json
{"status": "ok", "data": { ... }}
{"status": "error", "error": {"code": "...", "message": "..."}}
```

## Message Fields

Each message includes: `id`, `subject`, `sender`, `sender_name`, `date`, `mailbox`, `read`, `flagged`, `has_attachments`, `conversation_id`, `snippet`, `recipients`.

The `snippet` field contains message preview text when available (~14% of messages have it). For full content, use `body <id>`.

## Usage Patterns

**"What emails do I have?"** — Use `apple-mail --json unread` or `apple-mail --json recent 1`.

**"Any email from Alice?"** — Use `apple-mail --json sender "alice"`.

**"Read that email"** — Use `apple-mail --json body <id>` to get the full text.

**"What's the full conversation?"** — Use `apple-mail --json thread <id>` to see all messages in the thread, then `apple-mail --json export <id> --thread` for a readable markdown document.

**"Archive those newsletters"** — Use `apple-mail --json archive <id>` for each. No delete — archive only.

**"Reply to Bob saying I'll be there"** — Use `apple-mail --json draft --to "bob@example.com" --subject "Re: Meeting" --body "I'll be there."`. This saves to Drafts — user reviews and sends manually.
