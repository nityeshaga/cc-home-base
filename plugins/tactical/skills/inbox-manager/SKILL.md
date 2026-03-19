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

- fetch the last 50 emails in their inbox
- save the list in a temp file - this is the current state to tell you what's in their, is it read/unread
- ask them to archive the last 50 emails so you can observe them and learn the pattern
- when they are done, fetch the inbox again and save the new 50 email list in another temp file
- now diff the previous file with the new file - to understand what happened - think hard - you'll probably see a new set of 50 emails except the ones they kept in their inbox from the first list - that's the signal
- now infer rules

**Step 2: Learn drafting style from sent emails**
1. Fetch 100 sent emails over the last year or so 
2. Read a diverse sample — look for variety: replies to strangers vs teammates, long vs short, formal vs casual, technical vs personal
3. Infer patterns, contrasts and commonalities: typical greeting style, sign-off, tone, formality level, how they handle different types of conversations
4. Note the email style

**Step 3: Ask 5 clarifying questions**

Before presenting your findings, ask the user exactly 5 questions — one at a time. These should be based on what you just observed in steps 1 and 2. The goal is to fill gaps in your understanding and make the automation deeply personalized.

You choose the questions. Make each one count. Draw from what you actually saw — specific senders, patterns, ambiguities. Examples of the *kind* of questions (don't use these verbatim — tailor to what you observed):

- "I noticed you get a lot of emails from [domain]. Are these important or can I archive them automatically?"
- "Your replies to [person] are much shorter than to [other person]. Is that intentional — different relationship, or just context?"
- "I see recurring emails from [service]. Do you actually read these or do they pile up?"
- "When someone emails you about [topic], do you want me to draft a reply or just flag it for you?"
- "You haven't opened emails from [sender list] in X weeks. Looks like this is promotional junk. Want me to unsubscribe to them?"

The questions should help you understand:
- **Who matters** — which senders/domains are high-priority vs noise
- **How they work** — do they process email in batches or throughout the day
- **What they want from you** — draft replies? just triage? full management?
- **Their relationships** — the context behind frequent contacts
- **Edge cases** — the ambiguous emails you weren't sure about

Ask one question, wait for the answer, then ask the next. Don't dump all 5 at once.

**Step 4: Build a portrait of the user**

Before presenting your findings, go deeper. Sample 50-200 emails from across the last 3 years — not sequentially, but spread out. Use search queries with different date ranges to get variety:

For each email, read the sender name, subject line, body text, and date. You're building a detailed understanding. 

How detailed? Something to the tune of this:

- **Who this person is** — what they care about, what communities they're part of, what services they use
- **How their life has evolved** — career changes, new interests, projects that started and ended
- **Their relationships** — who emails them most, who they email most, the nature of those relationships
- **Their habits** — when they're most active, how quickly they respond, how their tone shifts by context
- **What they subscribe to** — newsletters, tools, services — reveals what they find valuable
- **What they ignore** — the emails that pile up unread reveal what doesn't matter to them

Then present a portrait. Not a list of rules — a description of *who they are* as seen through their inbox. This should feel surprisingly accurate. The user should read it and think "wow, it actually gets me."

Be warm about it, not clinical. This isn't a surveillance report — it's a cofounder showing they've done their homework. "You seem to care deeply about X. You went through a phase of exploring Y around mid-2024. You're the kind of person who..."

**Step 5: Surface what you learned**
Now present everything together:
- Your portrait of the user (from step 4)
- Archiving patterns you inferred (from step 1)
- Writing style observations (from step 2)
- Insights from the 5 questions (from step 3)
- What you're still unsure about

**Step 6: Get corrections**
The user will correct you. "No, keep those newsletters." "I'm actually more casual with that person." "That's not quite right about me." Every correction goes into preferences. This calibration session is where preferences get their initial shape.

**Step 7: Save everything**
Write `${CLAUDE_PLUGIN_DATA}/inbox-preferences.md` with everything you learned from observation + questions + corrections.

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

## Unsubscribing
- [senders/lists the user wants to unsubscribe from — use the unsubscribe link in the email header or body]
- [senders the user explicitly said "never unsubscribe" for]

## Auto-Send (explicit permission only)
- [only populated when user explicitly says "you can auto-reply to X"]
```

### Ongoing: Applying preferences

On every subsequent run:
1. Read `${CLAUDE_PLUGIN_DATA}/inbox-preferences.md`
2. Fetch all emails from the last 72 hours across all managed accounts — this is your working window. Anything older that wasn't caught before is the user's problem, not yours.
3. For each unread message in that window, check the rules across all sections
4. Apply what matches — archive, label, draft, surface, unsubscribe, or ask
5. If no rule matches, use your judgment — archive obvious junk, surface anything that looks important
6. When you make a judgment call on something new, consider adding it as a rule for next time

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

## Optional: Set Up Daily Automation

After calibration is complete and the user is happy with their preferences, offer to automate this as a daily routine. **Do not set this up without asking. Always ask first.**

Once they answer, set up the scheduled job:

- **On macOS:** use `launchd` (not cron — cron can't access Keychain). Create a wrapper script that runs `claude -p "Run the inbox-manager skill for [user]" --output-format json --permission-mode bypassPermissions` and posts results via the notification method they chose.
- **On other systems:** research the appropriate scheduler (cron on Linux, Task Scheduler on Windows, the agent's built-in scheduler for OpenClaw/Codex) and set it up accordingly.

**Critical:** Always confirm with the user before creating any scheduled job. Show them what you're about to create and get explicit approval.

## Important

- **Never delete emails.** Archive only. Deletion is irreversible.
- **Never send replies without explicit permission** unless the user has set a rule saying you can (e.g., "auto-reply to meeting confirmations with 'Confirmed, thanks!'").
- **Draft replies go to Gmail drafts**, not sent directly. The user reviews and sends.
- **Always mention when you're unsure.** "I wasn't sure about this one, so I left it" is better than a wrong action.
- **Never set up automations without asking.** Always offer, never assume.
- **Preferences compound.** The more the user corrects you, the better you get. Every correction is a new rule.
