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

Your preferences are stored in `${CLAUDE_PLUGIN_DATA}/inbox-preferences.json`. This file persists across skill upgrades and conversation sessions.

### How preferences work

When a user tells you something like:
- "Always archive emails from newsletters@substack.com"
- "Draft replies to clients in a warm, professional tone"
- "Don't touch anything from mom"
- "Label all GitHub notifications as 'dev'"
- "Research the CC codebase before drafting technical support replies"
- "Ask me before replying to anything from investors"

Save it immediately:

```bash
# Read current preferences
cat "${CLAUDE_PLUGIN_DATA}/inbox-preferences.json"

# Write updated preferences (merge, don't overwrite)
```

### Preference schema

```json
{
  "users": {
    "nityesh": {
      "accounts": ["personal@gmail.com", "nityesh@every.to"],
      "rules": [
        {
          "match": {"from": "newsletters@substack.com"},
          "action": "archive",
          "reason": "User said: always archive these"
        },
        {
          "match": {"from": "*@github.com"},
          "action": "label",
          "label": "dev",
          "reason": "User said: label GitHub notifications as dev"
        },
        {
          "match": {"from": "*@investor-domain.com"},
          "action": "ask_user",
          "reason": "User said: ask me before replying to investors"
        }
      ],
      "reply_style": "Warm but concise. No corporate fluff. Match the formality of the sender.",
      "drafting_context": [
        "For technical CC support replies, read the relevant codebase first",
        "For Every Consulting replies, check ~/projects/nityesh-every/ for context"
      ]
    },
    "piyush": {
      "accounts": ["piyush@gmail.com"],
      "rules": [],
      "reply_style": "",
      "drafting_context": []
    }
  },
  "global_rules": [
    {
      "match": {"subject_contains": "unsubscribe"},
      "action": "archive",
      "reason": "Default: marketing emails with unsubscribe links"
    }
  ]
}
```

### Applying preferences

When processing email:
1. Load preferences from `${CLAUDE_PLUGIN_DATA}/inbox-preferences.json`
2. For each unread message, check rules in order
3. Apply the matching action: `archive`, `label`, `draft_reply`, `ask_user`, or `surface` (add to briefing)
4. If no rule matches, use your judgment — archive obvious junk, surface anything that looks important

### Updating preferences

When a user gives you a new preference:
1. Read the current file
2. Add/update the rule
3. Write the file back
4. Confirm: "Got it — I'll [action] emails from [sender] from now on."

If a user corrects you ("no, don't archive those"), update the rule and acknowledge the correction.

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
4. **Surface important items** by appending to `~/work/morning-brief.md`:
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
