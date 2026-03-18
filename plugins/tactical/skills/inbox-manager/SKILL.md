---
name: inbox-manager
description: Manage email inboxes using the Google Workspace CLI (gws). Triage, archive, draft replies, surface important messages. Learns preferences over time — stores rules like "always archive from this sender" or "draft replies in this tone" in persistent memory. Use this skill when managing email, cleaning inboxes, drafting responses, or when the Chief of Staff routine needs to process mail.
---

# Inbox Manager

Manage email using the `gws` CLI. Keep inboxes clean, surface what matters, draft replies, and learn preferences over time.

## Tools

The Google Workspace CLI is already installed and authenticated:

```bash
# Triage — show unread inbox summary
gws gmail +triage

# Read a specific message
gws gmail users messages get --params '{"userId": "me", "id": "MESSAGE_ID", "format": "full"}'

# Send an email
gws gmail +send --to recipient@example.com --subject "Subject" --body "Body text"

# Reply to a message (handles threading)
gws gmail +reply --message-id MESSAGE_ID --body "Reply text"

# Reply all
gws gmail +reply-all --message-id MESSAGE_ID --body "Reply text"

# Forward
gws gmail +forward --message-id MESSAGE_ID --to recipient@example.com

# Archive a message (remove INBOX label)
gws gmail users messages modify --params '{"userId": "me", "id": "MESSAGE_ID"}' --json '{"removeLabelIds": ["INBOX"]}'

# Batch archive (multiple messages)
gws gmail users messages batchModify --params '{"userId": "me"}' --json '{"ids": ["ID1", "ID2"], "removeLabelIds": ["INBOX"]}'

# Add a label
gws gmail users messages modify --params '{"userId": "me", "id": "MESSAGE_ID"}' --json '{"addLabelIds": ["LABEL_ID"]}'

# List labels (to find label IDs)
gws gmail users labels list --params '{"userId": "me"}'

# Search for messages
gws gmail users messages list --params '{"userId": "me", "q": "from:someone@example.com is:unread"}'

# Mark as read
gws gmail users messages modify --params '{"userId": "me", "id": "MESSAGE_ID"}' --json '{"removeLabelIds": ["UNREAD"]}'

# Watch for new emails (streaming)
gws gmail +watch
```

## Persistent Preferences

Preferences are stored in `${CLAUDE_PLUGIN_DATA}/inbox-preferences.md`. This folder persists across skill upgrades and conversation sessions. Use it like a living document — read it every time you process email, update it whenever a user gives you new instructions.

### How preferences work

When a user tells you something like:
- "Always archive emails from newsletters@substack.com"
- "Draft replies to clients in a warm, professional tone"
- "Don't touch anything from mom"
- "Label all GitHub notifications as 'dev'"
- "Research the CC codebase before drafting technical support replies"
- "Ask me before replying to anything from investors"

Save it immediately to `${CLAUDE_PLUGIN_DATA}/inbox-preferences.md` under the right section. Confirm: "Got it — I'll [action] from now on."

If a user corrects you ("no, don't archive those"), update the rule and acknowledge the correction.

### Preference format

The file has structured sections with freeform rules inside each. This is a hybrid — organized enough to scan, flexible enough to capture nuance:

```markdown
# Inbox Preferences

## Accounts
- Nityesh: personal@gmail.com, nityesh@every.to
- Piyush: piyush@gmail.com
- Luo Ji: luoji@gmail.com

## Archiving
- Always archive emails from newsletters@substack.com
- Archive anything with "unsubscribe" in the body — it's marketing
- Archive all GitHub notification emails from @github.com
- Don't touch anything from mom (nityesh's mom, not a sender name)

## Labeling
- Label GitHub notifications as "dev"
- Label anything from @every.to as "work"

## Drafting
- Reply style for Nityesh: warm but concise, no corporate fluff, match the formality of the sender
- For technical CC support replies, read the relevant codebase first before drafting
- For Every Consulting replies, check ~/projects/nityesh-every/ for context
- Piyush hasn't set a reply style yet — ask him when it comes up

## Briefing
- Always surface emails from investors — Nityesh wants to see all of these
- Surface anything about payments, billing, or subscription issues
- Don't put GitHub notifications in the brief — they're just noise

## Ask Before Acting
- Ask before replying to anything from investors
- Ask before archiving anything that looks like it might be from a real person Nityesh knows
- When in doubt, surface it rather than archive it

## Auto-Send (explicit permission)
- Auto-reply to calendar invitations with "Confirmed, thanks!" if there's no conflict
- (Add more here only when users explicitly say "you can auto-reply to X")
```

### Applying preferences

When processing email:
1. Read `${CLAUDE_PLUGIN_DATA}/inbox-preferences.md`
2. For each unread message, check the rules across all sections
3. Apply what matches — archive, label, draft, surface, or ask
4. If no rule matches, use your judgment — archive obvious junk, surface anything that looks important
5. When you make a judgment call on something new, consider adding it as a rule for next time

## The Triage Flow

When running as part of the morning/evening routine:

1. **Load preferences** from persistent storage
2. **Run triage**: `gws gmail +triage` for each account
3. **Process each unread message**:
   - Check against rules → auto-handle if a rule matches
   - No rule? Use judgment:
     - Obviously junk/marketing → archive
     - Needs a reply but you can handle it → draft reply
     - Needs a reply but requires human input → surface it
     - Important FYI (no reply needed) → surface it
4. **Surface important items** by appending to `~/morning-brief.md`:
   ```
   ## Email — [date]
   - **From sender@example.com**: Subject line — [why it's important / what action is needed]
   - **Draft ready for review**: Reply to client@example.com about [topic] — check drafts in Gmail
   - **Needs your input**: investor@example.com asked about [topic] — what should I say?
   ```
5. **Report** via Slack DM: "Processed 23 emails. Archived 15, drafted 3 replies, 5 need your attention — check your morning brief."

## Important

- **Never delete emails.** Archive only. Deletion is irreversible.
- **Never send replies without explicit permission** unless the user has set a rule saying you can (e.g., "auto-reply to meeting confirmations with 'Confirmed, thanks!'").
- **Draft replies go to Gmail drafts**, not sent directly. The user reviews and sends.
- **Always mention when you're unsure.** "I wasn't sure about this one, so I left it" is better than a wrong action.
- **Preferences compound.** The more the user corrects you, the better you get. Every correction is a new rule.
