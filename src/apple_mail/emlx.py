"""Parse Apple Mail .emlx files to extract plain text body content."""

from __future__ import annotations

import email
import email.policy
import html
import re
from pathlib import Path


def parse_emlx(path: str | Path) -> dict | None:
    """Parse an .emlx file and extract metadata + plain text body.

    Args:
        path: Path to the .emlx file.

    Returns:
        Dict with keys: message_id (int, from filename), subject, sender,
        date, body (plain text). Returns None if the file can't be parsed.
    """
    path = Path(path)
    try:
        raw = path.read_bytes()
    except (OSError, PermissionError):
        return None

    # EMLX format: first line is byte count, then RFC 2822 message
    try:
        first_newline = raw.index(b"\n")
        byte_count = int(raw[:first_newline].strip())
        msg_bytes = raw[first_newline + 1 : first_newline + 1 + byte_count]
    except (ValueError, IndexError):
        return None

    try:
        msg = email.message_from_bytes(msg_bytes, policy=email.policy.default)
    except Exception:
        return None

    # Extract message ID from filename (e.g. "99173.emlx" → 99173)
    stem = path.stem
    if stem.endswith(".partial"):
        stem = stem.rsplit(".partial", 1)[0]
    try:
        message_id = int(stem)
    except ValueError:
        return None

    body = _extract_text(msg)
    if not body:
        return None

    return {
        "message_id": message_id,
        "subject": str(msg.get("Subject", "")),
        "sender": str(msg.get("From", "")),
        "date": str(msg.get("Date", "")),
        "body": body,
    }


def _extract_text(msg: email.message.Message) -> str:
    """Extract plain text from an email message, preferring text/plain."""
    body_part = msg.get_body(preferencelist=("plain", "html"))
    if body_part is None:
        return ""

    try:
        content = body_part.get_content()
    except Exception:
        return ""

    if body_part.get_content_type() == "text/html":
        content = _html_to_text(content)

    return content.strip()


def _html_to_text(html_content: str) -> str:
    """Simple HTML to plain text conversion."""
    # Remove style and script blocks
    text = re.sub(
        r"<style[^>]*>.*?</style>", "", html_content, flags=re.DOTALL | re.IGNORECASE
    )
    text = re.sub(
        r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE
    )
    # Replace common block elements with newlines
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</(p|div|h[1-6]|tr|li)>", "\n", text, flags=re.IGNORECASE)
    # Strip remaining tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode HTML entities
    text = html.unescape(text)
    # Collapse whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def find_emlx_files(mail_dir: str | None = None) -> list[Path]:
    """Find all .emlx files in the Mail directory.

    Args:
        mail_dir: Override the base Mail directory (for testing).

    Returns:
        List of Path objects for all .emlx files found.
    """
    base = Path(mail_dir or "~/Library/Mail/V10").expanduser()
    if not base.exists():
        return []
    return sorted(base.rglob("*.emlx"))
