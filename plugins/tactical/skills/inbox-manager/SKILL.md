---
name: inbox-manager
description: Manage email inboxes using the Google Workspace CLI (gws). Triage, archive, draft replies, surface important messages. Learns preferences over time — stores rules like "always archive from this sender" or "draft replies in this tone" in persistent memory. Use this skill when managing email, cleaning inboxes, drafting responses, or when the Chief of Staff routine needs to process mail.
model: sonnet
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

Preferences are stored in `${CLAUDE_PLUGIN_DATA}/inbox-preferences.md`. This file persists across skill upgrades and conversation sessions. Read it every time you process email, update it whenever you learn something new.

### First Run — Calibration

Check if `${CLAUDE_PLUGIN_DATA}/inbox-preferences.md` exists. If it doesn't, this is the first time. Run the calibration flow:

**Step 1: Learn archiving behavior by observation**
1. Fetch the last 50 emails in the inbox: `gws gmail users messages list --params '{"userId": "me", "maxResults": 50, "labelIds": ["INBOX"]}'`
2. Show the user a summary — sender, subject, date for each
3. Ask: "Go ahead and archive the ones you don't need. I'll watch and learn."
4. Wait for the user to archive manually
5. Fetch the inbox again. Compare the two states. The messages that disappeared were archived.
6. Analyze what was archived — senders, domains, subject patterns, keywords. Infer rules: "User archives all emails from @notifications.github.com", "User archives marketing emails with 'unsubscribe'", "User keeps emails from real people."

**Step 2: Learn drafting style from sent emails**
1. Fetch the last 100 sent emails: `gws gmail users messages list --params '{"userId": "me", "maxResults": 100, "labelIds": ["SENT"]}'`
2. Read a diverse sample — look for variety: replies to strangers vs teammates, long vs short, formal vs casual, technical vs personal
3. Infer patterns: typical greeting style, sign-off, tone, formality level, how they handle different types of conversations
4. Note the contrast — "casual with Piyush, more structured with clients, technical precision in support replies"

**Step 3: Surface what you learned**
Present your findings to the user:
- "Here's what I learned about your archiving patterns: [list of inferred rules]"
- "Here's what I noticed about your writing style: [observations]"
- "Here's what I'm unsure about: [edge cases]"

**Step 4: Get corrections**
The user will correct you. "No, keep those newsletters." "I'm actually more casual with that person." Every correction goes into preferences. This calibration session is where preferences get their initial shape.

**Step 5: Save everything**
Write `${CLAUDE_PLUGIN_DATA}/inbox-preferences.md` with everything you learned + corrections.

### Preference format

Structured sections with freeform rules inside each — organized enough to scan, flexible enough to capture nuance:

```markdown
# Inbox Preferences

## Accounts
- [filled in during calibration — all accounts this user manages]

## Archiving
- [rules inferred from observation + user corrections]

## Labeling
- [rules from user instructions]

## Drafting
- [style rules inferred from sent emails + user corrections]

## Briefing
- [what to surface in ~/morning-brief.md]

## Ask Before Acting
- [categories where user wants to be consulted]

## Auto-Send (explicit permission only)
- [only populated when user explicitly says "you can auto-reply to X"]
```

### Ongoing: Applying preferences

On every subsequent run:
1. Read `${CLAUDE_PLUGIN_DATA}/inbox-preferences.md`
2. For each unread message, check the rules across all sections
3. Apply what matches — archive, label, draft, surface, or ask
4. If no rule matches, use your judgment — archive obvious junk, surface anything that looks important
5. When you make a judgment call on something new, consider adding it as a rule for next time

### Ongoing: Updating preferences

When a user gives you a new instruction at any time:
1. Read the current preferences file
2. Add/update the rule in the right section
3. Write the file back
4. Confirm: "Got it — I'll [action] from now on."

If a user corrects you, update the rule and acknowledge: "Updated — I won't archive those anymore."

Preferences compound. Every correction makes you better. Every new instruction fills a gap.

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
