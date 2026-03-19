"""Python library for reading Apple Mail on macOS."""

from .client import MailClient
from .models import Mailbox, Message, MessageBody, Stats, Thread

__all__ = ["MailClient", "Mailbox", "Message", "MessageBody", "Stats", "Thread"]
