"""Python library for reading Apple Mail on macOS."""

from .client import MailClient
from .errors import AppleScriptError, DatabaseError, MailError, MessageNotFoundError
from .models import Attachment, Mailbox, Message, MessageBody, Stats, Thread

__all__ = [
    "AppleScriptError",
    "Attachment",
    "DatabaseError",
    "MailClient",
    "MailError",
    "Mailbox",
    "Message",
    "MessageNotFoundError",
    "MessageBody",
    "Stats",
    "Thread",
]
