"""Locate the Apple Mail SQLite database (Envelope Index)."""

from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_MAIL_DIR = "~/Library/Mail"


def find_mail_db(*, mail_dir: str | None = None) -> str:
    """Find the Envelope Index database path.

    Resolution order:
    1. MAIL_DB environment variable (explicit override)
    2. Auto-detect: scan ~/Library/Mail/V* for highest version

    Args:
        mail_dir: Override the base Mail directory (for testing).

    Returns:
        Absolute path to the Envelope Index file.

    Raises:
        FileNotFoundError: If the database cannot be located or
            the MAIL_DB path does not exist.
    """
    env_path = os.environ.get("MAIL_DB")
    if env_path:
        path = Path(env_path).expanduser()
        if not path.exists():
            raise FileNotFoundError(
                f"MAIL_DB points to a missing file: {env_path}\n"
                "Check the path or unset MAIL_DB to use auto-detection."
            )
        return str(path)

    base = Path(mail_dir or _DEFAULT_MAIL_DIR).expanduser()
    if not base.exists():
        raise FileNotFoundError(
            f"Mail directory not found: {base}\n"
            "Is Apple Mail installed? Check Full Disk Access in System Settings."
        )

    versions = sorted(
        (d for d in base.iterdir() if d.is_dir() and d.name.startswith("V")),
        key=lambda d: int(d.name[1:]) if d.name[1:].isdigit() else 0,
        reverse=True,
    )

    for vdir in versions:
        candidate = vdir / "MailData" / "Envelope Index"
        if candidate.exists():
            return str(candidate)

    raise FileNotFoundError(
        f"No Envelope Index found in {base}/V*/MailData/\n"
        "Ensure Apple Mail has been run at least once and you have "
        "Full Disk Access enabled in System Settings > Privacy & Security."
    )
