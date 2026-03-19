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


def _build_lookup_script(
    *,
    message_id: int,
    subject: str | None = None,
    sender: str | None = None,
    mode: str = "content",
) -> str:
    """Build AppleScript to find and act on a message."""
    safe_subject = _escape_applescript(subject or "")
    safe_sender = _escape_applescript(sender or "")

    action = 'return content of foundMsg' if mode == "content" else (
        'set visible of foundMsg to true\n'
        'activate\n'
        'return "OK"'
    )

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


def open_message(
    *,
    message_id: int,
    subject: str | None = None,
    sender: str | None = None,
) -> None:
    """Open a message in Mail.app."""
    script = _build_lookup_script(
        message_id=message_id, subject=subject, sender=sender, mode="open",
    )
    result = _run_applescript(script)
    if result == _NOT_FOUND:
        raise RuntimeError(f"Message {message_id} not found in Mail.app")


def get_message_body(
    *,
    message_id: int,
    subject: str | None = None,
    sender: str | None = None,
) -> str:
    """Get the full body text of a message via AppleScript."""
    script = _build_lookup_script(
        message_id=message_id, subject=subject, sender=sender, mode="content",
    )
    result = _run_applescript(script)
    if result == _NOT_FOUND:
        raise RuntimeError(f"Message {message_id} not found in Mail.app")
    return result
