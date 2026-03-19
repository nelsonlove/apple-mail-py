"""Click CLI for Apple Mail — thin layer over MailClient."""

from __future__ import annotations

import csv
import io
import json
import sys
from dataclasses import asdict

import click

from .client import MailClient
from .errors import MailError


@click.group()
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    envvar="APPLE_MAIL_OUTPUT",
    help="Output as JSON (structured envelope).",
)
@click.option("--csv", "as_csv", is_flag=True, help="Output as CSV.")
@click.option(
    "--db",
    "db_path",
    default=None,
    envvar="MAIL_DB",
    help="Path to Envelope Index database.",
)
@click.option(
    "--copy",
    "copy_mode",
    is_flag=True,
    help="Copy database to temp file before reading (avoids lock contention).",
)
@click.option(
    "-n", "--limit", default=20, type=int, help="Max results to return (default: 20)."
)
@click.pass_context
def cli(ctx, as_json, as_csv, db_path, copy_mode, limit):
    """Read and search Apple Mail from the command line."""
    ctx.ensure_object(dict)
    ctx.obj["client"] = MailClient(db_path=db_path, copy_mode=copy_mode)
    ctx.obj["json"] = as_json
    ctx.obj["csv"] = as_csv
    ctx.obj["limit"] = limit


def _client(ctx) -> MailClient:
    return ctx.obj["client"]


def _output_json(ctx) -> bool:
    return ctx.obj["json"]


def _output_csv(ctx) -> bool:
    return ctx.obj["csv"]


def _limit(ctx) -> int:
    return ctx.obj["limit"]


def _emit(ctx, data):
    """Emit structured JSON envelope: {"status": "ok", "data": ...}."""
    click.echo(json.dumps({"status": "ok", "data": data}, indent=2, default=str))


def _emit_error(code: str, message: str):
    """Emit structured JSON error envelope."""
    click.echo(
        json.dumps(
            {"status": "error", "error": {"code": code, "message": message}}, indent=2
        ),
        err=True,
    )
    sys.exit(1)


def _emit_messages(ctx, messages):
    """Output a list of messages in the requested format."""
    data = [asdict(m) for m in messages]

    if _output_json(ctx):
        _emit(ctx, data)
        return

    if _output_csv(ctx):
        _write_csv(data, ["id", "date", "sender", "subject", "mailbox", "read"])
        return

    if not messages:
        click.echo("No messages found.")
        return

    for m in messages:
        flag = "*" if m.flagged else " "
        read = " " if m.read else "●"
        date = m.date[:16] if len(m.date) > 16 else m.date
        click.echo(
            f" {read}{flag} {m.id:>6}  {date}  {m.sender:<30.30}  {m.subject:<50.50}  {m.mailbox}"
        )


def _write_csv(data: list[dict], fields: list[str]):
    """Write CSV to stdout."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(data)
    click.echo(buf.getvalue().rstrip())


# ── search ─────────────────────────────────────────────────────────────────


@cli.command("search")
@click.option("--subject", default=None, help="Match subject line.")
@click.option("--sender", default=None, help="Match sender email.")
@click.option("--from-name", default=None, help="Match sender display name.")
@click.option("--to", default=None, help="Match recipient.")
@click.option("--unread", is_flag=True, default=False, help="Only unread messages.")
@click.option(
    "--read", "only_read", is_flag=True, default=False, help="Only read messages."
)
@click.option("--days", default=None, type=int, help="Lookback window in days.")
@click.option(
    "--has-attachment",
    is_flag=True,
    default=False,
    help="Only messages with attachments.",
)
@click.option(
    "--attachment-type", default=None, help="Filter by attachment extension (e.g. pdf)."
)
@click.pass_context
def search_cmd(
    ctx,
    subject,
    sender,
    from_name,
    to,
    unread,
    only_read,
    days,
    has_attachment,
    attachment_type,
):
    """Search messages with filters."""
    client = _client(ctx)
    unread_filter = True if unread else (False if only_read else None)
    messages = client.search(
        subject=subject,
        sender=sender,
        from_name=from_name,
        to=to,
        unread=unread_filter,
        days=days,
        has_attachment=has_attachment,
        attachment_type=attachment_type,
        limit=_limit(ctx),
    )
    _emit_messages(ctx, messages)


# ── shortcuts ──────────────────────────────────────────────────────────────


@cli.command("subject")
@click.argument("pattern")
@click.pass_context
def subject_cmd(ctx, pattern):
    """Search by subject."""
    client = _client(ctx)
    messages = client.search(subject=pattern, limit=_limit(ctx))
    _emit_messages(ctx, messages)


@cli.command("sender")
@click.argument("pattern")
@click.pass_context
def sender_cmd(ctx, pattern):
    """Search by sender."""
    client = _client(ctx)
    messages = client.search(sender=pattern, limit=_limit(ctx))
    _emit_messages(ctx, messages)


@cli.command("to")
@click.argument("pattern")
@click.pass_context
def to_cmd(ctx, pattern):
    """Search by recipient."""
    client = _client(ctx)
    messages = client.search(to=pattern, limit=_limit(ctx))
    _emit_messages(ctx, messages)


@cli.command("unread")
@click.pass_context
def unread_cmd(ctx):
    """List unread messages."""
    client = _client(ctx)
    messages = client.unread(limit=_limit(ctx))
    _emit_messages(ctx, messages)


@cli.command("recent")
@click.argument("days", default=7, type=int)
@click.pass_context
def recent_cmd(ctx, days):
    """Show recent messages (default: 7 days)."""
    client = _client(ctx)
    messages = client.recent(days=days, limit=_limit(ctx))
    _emit_messages(ctx, messages)


# ── message operations ─────────────────────────────────────────────────────


@cli.command("open")
@click.argument("id", type=int)
@click.pass_context
def open_cmd(ctx, id):
    """Open a message in Mail.app."""
    client = _client(ctx)
    try:
        client.open_message(id)
        if _output_json(ctx):
            _emit(ctx, {"opened": id})
        else:
            click.echo(f"Opened message {id} in Mail.app")
    except MailError as e:
        if _output_json(ctx):
            _emit_error(e.code, str(e))
        else:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)


@cli.command("body")
@click.argument("id", type=int)
@click.pass_context
def body_cmd(ctx, id):
    """Get the full body of a message."""
    client = _client(ctx)
    try:
        msg_body = client.get_body(id)
        if _output_json(ctx):
            _emit(ctx, asdict(msg_body))
        else:
            click.echo(msg_body.body)
    except MailError as e:
        if _output_json(ctx):
            _emit_error(e.code, str(e))
        else:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)


# ── attachments ────────────────────────────────────────────────────────────


@cli.command("attachments")
@click.argument("id", type=int)
@click.pass_context
def attachments_cmd(ctx, id):
    """List attachments for a message."""
    client = _client(ctx)
    atts = client.get_attachments(id)

    if _output_json(ctx):
        _emit(ctx, [asdict(a) for a in atts])
        return

    if not atts:
        click.echo("No attachments.")
        return

    for a in atts:
        click.echo(f"  {a.name}")


@cli.command("save-attachments")
@click.argument("id", type=int)
@click.option(
    "-o",
    "--output",
    default=".",
    type=click.Path(file_okay=False),
    help="Directory to save attachments to (default: current directory).",
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be done without doing it."
)
@click.pass_context
def save_attachments_cmd(ctx, id, output, dry_run):
    """Save all attachments from a message to a directory."""
    if dry_run:
        client = _client(ctx)
        atts = client.get_attachments(id)
        names = [a.name for a in atts]
        if _output_json(ctx):
            _emit(
                ctx,
                {
                    "action": "save_attachments",
                    "message_id": id,
                    "output": output,
                    "files": names,
                    "dry_run": True,
                },
            )
        else:
            if not names:
                click.echo("No attachments to save.")
            else:
                for n in names:
                    click.echo(f"  Would save: {n}")
        return

    from pathlib import Path

    Path(output).mkdir(parents=True, exist_ok=True)

    client = _client(ctx)
    try:
        saved = client.save_attachments(id, str(Path(output).resolve()))
        if _output_json(ctx):
            _emit(ctx, {"message_id": id, "saved": saved, "output": output})
        else:
            if not saved:
                click.echo("No attachments saved.")
            else:
                for name in saved:
                    click.echo(f"  Saved: {name}")
    except MailError as e:
        if _output_json(ctx):
            _emit_error(e.code, str(e))
        else:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)


# ── thread ─────────────────────────────────────────────────────────────────


@cli.command("thread")
@click.argument("id", type=int)
@click.pass_context
def thread_cmd(ctx, id):
    """Show all messages in a conversation thread."""
    client = _client(ctx)
    try:
        thread = client.get_thread(id)
    except MailError as e:
        if _output_json(ctx):
            _emit_error(e.code, str(e))
        else:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    if _output_json(ctx):
        _emit(ctx, asdict(thread))
        return

    click.echo(f"Thread: {thread.subject}")
    click.echo(f"Messages: {thread.message_count}")
    click.echo(f"Participants: {', '.join(thread.participants)}")
    click.echo(f"Date range: {thread.date_start} to {thread.date_end}")
    click.echo()

    for m in thread.messages:
        read = " " if m.read else "●"
        click.echo(f"  {read} {m.id:>6}  {m.date[:16]}  {m.sender:<30.30}  {m.subject}")


# ── export ─────────────────────────────────────────────────────────────────


@cli.command("export")
@click.argument("id", type=int)
@click.option("--thread", is_flag=True, help="Export the full conversation thread.")
@click.option("-o", "--output", default=None, help="Write to file instead of stdout.")
@click.pass_context
def export_cmd(ctx, id, thread, output):
    """Export a message (or thread) as markdown."""
    client = _client(ctx)
    try:
        if thread:
            md = client.export_thread(id)
        else:
            md = client.export_message(id)
    except MailError as e:
        if _output_json(ctx):
            _emit_error(e.code, str(e))
        else:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    if _output_json(ctx):
        _emit(ctx, {"markdown": md, "thread": thread, "message_id": id})
        return

    if output:
        from pathlib import Path

        Path(output).write_text(md, encoding="utf-8")
        click.echo(f"Exported to {output}")
    else:
        click.echo(md)


# ── write operations ───────────────────────────────────────────────────────


@cli.command("mark-read")
@click.argument("id", type=int)
@click.option("--unread", is_flag=True, help="Mark as unread instead of read.")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be done without doing it."
)
@click.pass_context
def mark_read_cmd(ctx, id, unread, dry_run):
    """Mark a message as read (or --unread)."""
    action = "unread" if unread else "read"
    if dry_run:
        if _output_json(ctx):
            _emit(ctx, {"action": f"mark_{action}", "message_id": id, "dry_run": True})
        else:
            click.echo(f"Would mark message {id} as {action}")
        return
    client = _client(ctx)
    try:
        client.mark_read(id, read=not unread)
        if _output_json(ctx):
            _emit(ctx, {"message_id": id, "read": not unread})
        else:
            click.echo(f"Marked message {id} as {action}")
    except MailError as e:
        if _output_json(ctx):
            _emit_error(e.code, str(e))
        else:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)


@cli.command("flag")
@click.argument("id", type=int)
@click.option("--remove", is_flag=True, help="Remove flag instead of adding.")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be done without doing it."
)
@click.pass_context
def flag_cmd(ctx, id, remove, dry_run):
    """Flag a message (or --remove to unflag)."""
    action = "unflag" if remove else "flag"
    if dry_run:
        if _output_json(ctx):
            _emit(ctx, {"action": action, "message_id": id, "dry_run": True})
        else:
            click.echo(f"Would {action} message {id}")
        return
    client = _client(ctx)
    try:
        client.set_flagged(id, flagged=not remove)
        if _output_json(ctx):
            _emit(ctx, {"message_id": id, "flagged": not remove})
        else:
            click.echo(f"{'Unflagged' if remove else 'Flagged'} message {id}")
    except MailError as e:
        if _output_json(ctx):
            _emit_error(e.code, str(e))
        else:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)


@cli.command("archive")
@click.argument("id", type=int)
@click.option("--account", default=None, help="Target account name.")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be done without doing it."
)
@click.pass_context
def archive_cmd(ctx, id, account, dry_run):
    """Move a message to Archive."""
    if dry_run:
        if _output_json(ctx):
            _emit(ctx, {"action": "archive", "message_id": id, "dry_run": True})
        else:
            click.echo(f"Would archive message {id}")
        return
    client = _client(ctx)
    try:
        client.archive(id, account=account)
        if _output_json(ctx):
            _emit(ctx, {"message_id": id, "archived": True})
        else:
            click.echo(f"Archived message {id}")
    except MailError as e:
        if _output_json(ctx):
            _emit_error(e.code, str(e))
        else:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)


@cli.command("draft")
@click.option(
    "--to",
    "to_addrs",
    required=True,
    multiple=True,
    help="Recipient address (repeatable).",
)
@click.option("--subject", required=True, help="Email subject.")
@click.option("--body", required=True, help="Email body text.")
@click.option("--cc", "cc_addrs", multiple=True, help="CC address (repeatable).")
@click.option("--bcc", "bcc_addrs", multiple=True, help="BCC address (repeatable).")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be done without doing it."
)
@click.pass_context
def draft_cmd(ctx, to_addrs, subject, body, cc_addrs, bcc_addrs, dry_run):
    """Create a draft email (saved to Drafts, not sent)."""
    if dry_run:
        data = {
            "action": "draft",
            "to": list(to_addrs),
            "subject": subject,
            "dry_run": True,
        }
        if cc_addrs:
            data["cc"] = list(cc_addrs)
        if bcc_addrs:
            data["bcc"] = list(bcc_addrs)
        if _output_json(ctx):
            _emit(ctx, data)
        else:
            click.echo(f'Would create draft: "{subject}" to {", ".join(to_addrs)}')
        return
    client = _client(ctx)
    try:
        client.create_draft(
            to=list(to_addrs),
            subject=subject,
            body=body,
            cc=list(cc_addrs) or None,
            bcc=list(bcc_addrs) or None,
        )
        if _output_json(ctx):
            _emit(ctx, {"drafted": True, "to": list(to_addrs), "subject": subject})
        else:
            click.echo(f'Draft created: "{subject}" to {", ".join(to_addrs)}')
    except MailError as e:
        if _output_json(ctx):
            _emit_error(e.code, str(e))
        else:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)


# ── full-text search ───────────────────────────────────────────────────────


@cli.command("index")
@click.option("--force", is_flag=True, help="Drop and rebuild the index from scratch.")
@click.option(
    "--status", "show_status", is_flag=True, help="Show index stats and exit."
)
@click.pass_context
def index_cmd(ctx, force, show_status):
    """Build or update the full-text search index."""
    client = _client(ctx)

    if show_status:
        info = client.index_status()
        if _output_json(ctx):
            _emit(ctx, info)
        else:
            click.echo(f"  Indexed messages: {info['indexed_messages']:,}")
            click.echo(f"  Index size:       {info['index_size_mb']} MB")
            click.echo(f"  Index path:       {info['index_path']}")
        return

    result = client.build_index(force=force, progress=True)
    if _output_json(ctx):
        _emit(ctx, result)
    else:
        click.echo(f"  Indexed: {result['indexed']:,}")
        click.echo(f"  Unchanged: {result['skipped']:,}")
        click.echo(f"  Errors: {result['errors']:,}")
        click.echo(f"  Total files: {result['total_files']:,}")


@cli.command("search-body")
@click.argument("query")
@click.pass_context
def search_body_cmd(ctx, query):
    """Full-text search over message bodies (requires index)."""
    client = _client(ctx)
    messages = client.search_body(query, limit=_limit(ctx))
    _emit_messages(ctx, messages)


# ── stats ──────────────────────────────────────────────────────────────────


@cli.command("stats")
@click.pass_context
def stats_cmd(ctx):
    """Show database statistics."""
    client = _client(ctx)
    stats = client.stats()

    if _output_json(ctx):
        _emit(ctx, asdict(stats))
        return

    if _output_csv(ctx):
        _write_csv([asdict(stats)], ["total", "unread", "deleted", "with_attachments"])
        return

    click.echo(f"  Total:            {stats.total:,}")
    click.echo(f"  Unread:           {stats.unread:,}")
    click.echo(f"  Deleted:          {stats.deleted:,}")
    click.echo(f"  With attachments: {stats.with_attachments:,}")


# ── mailboxes ──────────────────────────────────────────────────────────────


@cli.command("mailboxes")
@click.pass_context
def mailboxes_cmd(ctx):
    """List all mailboxes."""
    client = _client(ctx)
    mbs = client.mailboxes()

    if _output_json(ctx):
        _emit(ctx, [asdict(mb) for mb in mbs])
        return

    if not mbs:
        click.echo("No mailboxes found.")
        return

    for mb in mbs:
        acct = f"({mb.account})" if mb.account else ""
        click.echo(f"  {mb.name:<30} {acct}")
