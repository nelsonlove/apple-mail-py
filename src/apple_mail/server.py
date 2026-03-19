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


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
