"""Typed exceptions for Apple Mail operations."""


class MailError(Exception):
    """Base exception for apple-mail-py."""

    def __init__(self, message: str, code: str = "error"):
        self.code = code
        super().__init__(message)


class MessageNotFoundError(MailError):
    """Raised when a message cannot be found."""

    def __init__(self, message_id: int):
        super().__init__(f"Message {message_id} not found", code="not_found")
        self.message_id = message_id


class MailboxNotFoundError(MailError):
    """Raised when a mailbox cannot be found."""

    def __init__(self, mailbox: str):
        super().__init__(f"Mailbox '{mailbox}' not found", code="mailbox_not_found")
        self.mailbox = mailbox


class AppleScriptError(MailError):
    """Raised when an AppleScript operation fails."""

    def __init__(self, detail: str):
        super().__init__(f"AppleScript error: {detail}", code="applescript_error")


class DatabaseError(MailError):
    """Raised when a database operation fails."""

    def __init__(self, detail: str):
        super().__init__(f"Database error: {detail}", code="database_error")
