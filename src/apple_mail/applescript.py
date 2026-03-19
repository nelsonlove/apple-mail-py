"""AppleScript interaction with Mail.app for open and body operations."""

from __future__ import annotations

import subprocess

_NOT_FOUND = "__NOT_FOUND__"


def _escape_applescript(s: str) -> str:
    """Escape a string for safe embedding in AppleScript literals."""
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("'", "\\'")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def _run_applescript(script: str) -> str:
    """Execute AppleScript via osascript and return stdout."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(f"AppleScript error: {stderr}")
    return result.stdout.strip()


def _build_action_script(
    *,
    message_id: int,
    subject: str | None = None,
    sender: str | None = None,
    action: str,
) -> str:
    """Build AppleScript to find a message and perform an action on it.

    The action string is AppleScript code that can reference `foundMsg`.
    """
    safe_subject = _escape_applescript(subject or "")
    safe_sender = _escape_applescript(sender or "")

    script = f'''
tell application "Mail"
    set foundMsg to missing value
    set allMailboxes to every mailbox of every account

    repeat with acctBoxes in allMailboxes
        repeat with mb in acctBoxes
            try
                set msgs to (messages of mb whose id is {message_id})
                if (count of msgs) > 0 then
                    set foundMsg to item 1 of msgs
                    exit repeat
                end if
            end try
        end repeat
        if foundMsg is not missing value then exit repeat
    end repeat

    if foundMsg is missing value then
        repeat with acctBoxes in allMailboxes
            repeat with mb in acctBoxes
                try
                    set msgs to (messages of mb whose subject contains "{safe_subject}" and sender contains "{safe_sender}")
                    if (count of msgs) > 0 then
                        set foundMsg to item 1 of msgs
                        exit repeat
                    end if
                end try
            end repeat
            if foundMsg is not missing value then exit repeat
        end repeat
    end if

    if foundMsg is missing value then
        return "{_NOT_FOUND}"
    end if

    {action}
end tell
'''
    return script


def _find_and_act(
    *,
    message_id: int,
    subject: str | None = None,
    sender: str | None = None,
    action: str,
) -> str:
    """Find a message and perform an action. Returns AppleScript result."""
    script = _build_action_script(
        message_id=message_id,
        subject=subject,
        sender=sender,
        action=action,
    )
    result = _run_applescript(script)
    if result == _NOT_FOUND:
        raise RuntimeError(f"Message {message_id} not found in Mail.app")
    return result


# ── Read operations ────────────────────────────────────────────────────


def open_message(
    *,
    message_id: int,
    subject: str | None = None,
    sender: str | None = None,
) -> None:
    """Open a message in Mail.app."""
    _find_and_act(
        message_id=message_id,
        subject=subject,
        sender=sender,
        action='set visible of foundMsg to true\nactivate\nreturn "OK"',
    )


def get_message_body(
    *,
    message_id: int,
    subject: str | None = None,
    sender: str | None = None,
) -> str:
    """Get the full body text of a message via AppleScript."""
    return _find_and_act(
        message_id=message_id,
        subject=subject,
        sender=sender,
        action="return content of foundMsg",
    )


# ── Write operations ────────────────────────────────────────────────────


def mark_read(
    *,
    message_id: int,
    subject: str | None = None,
    sender: str | None = None,
    read: bool = True,
) -> None:
    """Mark a message as read or unread."""
    value = "true" if read else "false"
    _find_and_act(
        message_id=message_id,
        subject=subject,
        sender=sender,
        action=f'set read status of foundMsg to {value}\nreturn "OK"',
    )


def set_flagged(
    *,
    message_id: int,
    subject: str | None = None,
    sender: str | None = None,
    flagged: bool = True,
) -> None:
    """Flag or unflag a message."""
    value = "true" if flagged else "false"
    _find_and_act(
        message_id=message_id,
        subject=subject,
        sender=sender,
        action=f'set flagged status of foundMsg to {value}\nreturn "OK"',
    )


def move_message(
    *,
    message_id: int,
    target_mailbox: str,
    target_account: str | None = None,
    subject: str | None = None,
    sender: str | None = None,
) -> None:
    """Move a message to a different mailbox (e.g. Archive).

    Args:
        message_id: Message ROWID.
        target_mailbox: Mailbox name (e.g. "Archive", "INBOX").
        target_account: Account name. If None, searches all accounts.
        subject: For fallback lookup.
        sender: For fallback lookup.
    """
    safe_mailbox = _escape_applescript(target_mailbox)
    if target_account:
        safe_account = _escape_applescript(target_account)
        find_target = (
            f'set targetBox to mailbox "{safe_mailbox}" of account "{safe_account}"'
        )
    else:
        find_target = f"""
    set targetBox to missing value
    repeat with acct in every account
        try
            set targetBox to mailbox "{safe_mailbox}" of acct
            exit repeat
        end try
    end repeat
    if targetBox is missing value then
        error "Mailbox '{safe_mailbox}' not found"
    end if"""

    action = f"""
    {find_target}
    move foundMsg to targetBox
    return "OK"
"""
    _find_and_act(
        message_id=message_id,
        subject=subject,
        sender=sender,
        action=action,
    )


def create_draft(
    *,
    to_addresses: list[str],
    subject: str,
    body: str,
    cc_addresses: list[str] | None = None,
    bcc_addresses: list[str] | None = None,
) -> None:
    """Create a draft message in Mail.app (saved to Drafts, not sent).

    Args:
        to_addresses: List of recipient email addresses.
        subject: Email subject line.
        body: Plain text body.
        cc_addresses: Optional CC recipients.
        bcc_addresses: Optional BCC recipients.
    """
    safe_subject = _escape_applescript(subject)
    safe_body = _escape_applescript(body)

    # Build recipient lines
    to_lines = "\n".join(
        f"        make new to recipient at end of to recipients with properties "
        f'{{address:"{_escape_applescript(addr)}"}}'
        for addr in to_addresses
    )
    cc_lines = ""
    if cc_addresses:
        cc_lines = "\n".join(
            f"        make new cc recipient at end of cc recipients with properties "
            f'{{address:"{_escape_applescript(addr)}"}}'
            for addr in cc_addresses
        )
    bcc_lines = ""
    if bcc_addresses:
        bcc_lines = "\n".join(
            f"        make new bcc recipient at end of bcc recipients with properties "
            f'{{address:"{_escape_applescript(addr)}"}}'
            for addr in bcc_addresses
        )

    script = f'''
tell application "Mail"
    set newMsg to make new outgoing message with properties {{subject:"{safe_subject}", content:"{safe_body}", visible:false}}
    tell newMsg
{to_lines}
{cc_lines}
{bcc_lines}
    end tell
    save newMsg
    return "OK"
end tell
'''
    _run_applescript(script)


def save_attachments(
    *,
    message_id: int,
    output_dir: str,
    subject: str | None = None,
    sender: str | None = None,
) -> list[str]:
    """Save all attachments from a message to a directory.

    Args:
        message_id: Message ROWID.
        output_dir: Directory to save attachments to.
        subject: For fallback message lookup.
        sender: For fallback message lookup.

    Returns:
        List of saved filenames.
    """
    safe_dir = _escape_applescript(output_dir)

    result = _find_and_act(
        message_id=message_id,
        subject=subject,
        sender=sender,
        action=f'''
    set attList to every mail attachment of foundMsg
    set savedNames to {{}}
    repeat with att in attList
        set attName to name of att
        set savePath to "{safe_dir}/" & attName
        try
            save att in POSIX file savePath
            set end of savedNames to attName
        end try
    end repeat
    set AppleScript's text item delimiters to "||"
    return savedNames as text
''',
    )
    if not result:
        return []
    return [name for name in result.split("||") if name]
