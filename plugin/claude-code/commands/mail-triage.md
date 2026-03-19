---
name: mail-triage
description: Check email and get a structured briefing of unread messages
argument-hint: "[days]"
---

Start an email triage session. Use the mail-triage skill to guide the process.

Run the CLI via the launcher: `${CLAUDE_PLUGIN_ROOT}/bin/run apple-mail`

<$ARGUMENTS>

If the user provided a number of days as an argument, use that as the lookback window. Otherwise, default to 1 day of unread messages.
