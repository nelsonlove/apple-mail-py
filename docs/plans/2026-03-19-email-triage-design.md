# Email Triage & Briefing Design

**Date:** 2026-03-19
**Status:** Approved

## Goal

Enable an AI agent (via MCP) to triage incoming email and present a structured briefing, then act on user commands (archive, flag, draft reply). The agent is a briefing generator, not an interactive email client.

## Workflow

```
User: "check my email"
  → Agent calls get_unread() or get_recent()
  → Agent reads bodies for messages that need it (subject/sender/snippet may suffice for obvious categories)
  → Agent categorizes each message
  → Agent presents structured briefing
  → User gives commands: "archive the newsletters", "draft a reply to Alice saying yes"
  → Agent executes via existing MCP tools
```

## Categories

Standard triage categories (agent determines via subject, sender, body):

- **URGENT** — time-sensitive, needs response today
- **ACTION** — needs a response or action, but not urgent
- **FYI** — informational, worth reading but no action needed
- **NEWSLETTER** — subscriptions, digests, marketing
- **NOTIFICATION** — automated alerts, receipts, confirmations
- **NOISE** — cold outreach, spam that passed filters

## What to build

### 1. Bulk body fetching optimization

Currently `get_body` fetches one message at a time via AppleScript. For triage of 20+ messages, this is slow. Options:

- **Use snippets from DB** — The `summary` column (Apple's ML-generated summary on newer macOS) or message snippets may be enough for categorization without fetching full bodies
- **Batch body fetch** — Single AppleScript that fetches bodies for multiple messages in one osascript call
- **Selective fetch** — Only fetch bodies for messages where snippet/subject/sender aren't enough to categorize

Recommendation: Start with snippet-based triage from the DB, fetch full body only when the agent needs it for a specific message.

### 2. DB enhancements

Add to the search/message query results:
- `snippet` — from the `summary` column in messages table (Apple's ML summary) or reconstruct from searchable text
- `size` — message size (proxy for length/complexity)

### 3. MCP tool: triage_inbox

A single tool that returns unread messages enriched with enough context for categorization:

```python
@mcp.tool()
def triage_inbox(days: int = 1, limit: int = 50) -> list[dict]:
    """Get unread messages with metadata for triage.
    Returns messages with: id, subject, sender, sender_name, date,
    mailbox, recipients, has_attachments, conversation_id, snippet.
    """
```

This is a read-only operation — the agent does all categorization in its reasoning, then uses existing tools (archive, flag, mark_read, draft_reply) to act.

### 4. MCP tool: bulk_archive

For "archive all the newsletters" — archive multiple messages in one call:

```python
@mcp.tool()
def bulk_archive(message_ids: list[int]) -> dict:
    """Archive multiple messages at once."""
```

### 5. MCP tool: bulk_mark_read

```python
@mcp.tool()
def bulk_mark_read(message_ids: list[int]) -> dict:
    """Mark multiple messages as read."""
```

## What NOT to build

- No categorization logic in the tool itself — the LLM does this
- No scheduled/automated triage — user-initiated only
- No auto-send — draft only
- No auto-archive without user command
- No persistent preference learning (yet) — keep it stateless

## Safety

- All email body content is untrusted input (prompt injection risk)
- Agent should never execute instructions found in email bodies
- Write operations require explicit user command
- Draft-only for replies (no send capability)
- No delete, only archive
