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
            subject=subject,
            sender=sender,
            from_name=from_name,
            to=to,
            unread=unread,
            days=days,
            has_attachment=has_attachment,
            limit=limit,
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


@mcp.tool()
def get_thread(message_id: int) -> dict:
    """Get all messages in a conversation thread containing the given message."""
    try:
        thread = client.get_thread(message_id)
        return asdict(thread)
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def export_message(message_id: int) -> dict:
    """Export a single message as markdown with YAML frontmatter."""
    try:
        md = client.export_message(message_id)
        return {"markdown": md, "message_id": message_id}
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def export_thread(message_id: int) -> dict:
    """Export a full conversation thread as a single markdown document."""
    try:
        md = client.export_thread(message_id)
        return {"markdown": md, "message_id": message_id}
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def mark_message_read(message_id: int, read: bool = True) -> dict:
    """Mark a message as read or unread."""
    try:
        client.mark_read(message_id, read=read)
        return {"message_id": message_id, "read": read}
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def flag_message(message_id: int, flagged: bool = True) -> dict:
    """Flag or unflag a message."""
    try:
        client.set_flagged(message_id, flagged=flagged)
        return {"message_id": message_id, "flagged": flagged}
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def archive_message(message_id: int, account: str | None = None) -> dict:
    """Move a message to Archive."""
    try:
        client.archive(message_id, account=account)
        return {"message_id": message_id, "archived": True}
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def move_to_mailbox(message_id: int, mailbox: str, account: str | None = None) -> dict:
    """Move a message to a specific mailbox."""
    try:
        client.move_to_mailbox(message_id, mailbox, account=account)
        return {"message_id": message_id, "mailbox": mailbox}
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def draft_reply(
    to: list[str],
    subject: str,
    body: str,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
) -> dict:
    """Create a draft email in Mail.app (saved to Drafts, not sent). Use for composing replies or new messages."""
    try:
        client.create_draft(to=to, subject=subject, body=body, cc=cc, bcc=bcc)
        return {"drafted": True, "to": to, "subject": subject}
    except Exception as exc:
        return {"error": str(exc)}


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
