"""Python library for reading Apple Mail on macOS."""

from .client import MailClient
from .models import Attachment, Mailbox, Message, MessageBody, Stats, Thread

__all__ = [
    "Attachment",
    "MailClient",
    "Mailbox",
    "Message",
    "MessageBody",
    "Stats",
    "Thread",
]
