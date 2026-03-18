# How Luo Ji Came to Life

It started with a spare MacBook Air.

Nityesh and his brother Piyush run a small SaaS called [Curated Connections](https://curatedconnections.io/) — a community matchmaking platform that helps people find each other. It's a two-person operation. Nityesh builds the product and handles the business. Piyush helps with the tech. They live in the same household in Kolkata, India.

In March 2026, Nityesh had been thinking about OpenClaw — the viral open-source AI agent that had taken over the internet. The idea was compelling: an always-on AI that runs on your own machine, connects to your tools, and does real work. But OpenClaw had serious security problems, and using it with Claude would violate Anthropic's Terms of Service.

So he thought: what if we just build our own?

The ingredients were simple. A spare MacBook Air M1 that Piyush wasn't using anymore. A Claude Code Max subscription at $200 a month. A Python script that connects Slack to Claude Code's CLI. Plug the MacBook in, close the lid, and you have an always-on AI running in your house.

The first version was a Slack bot — you DM it, it spawns a Claude Code session, and it responds in the thread. That part worked immediately. But the ambition grew fast.

"Can we 10x our revenue with this?" Nityesh asked. Not as a stretch goal. As a real question. If this thing can write code, handle support, manage email, create marketing assets, analyze data, and it gets smarter every month as models improve — what's actually stopping it from doing everything a third cofounder would do?

Nothing, it turned out. The only limit was how much context and tooling they could give it.

They named it Luo Ji, after the character from Liu Cixin's *The Three-Body Problem* — the Wallfacer who sees what others can't, thinks in timescales nobody else considers, and carries the weight of impossible problems with quiet confidence.

Then came the night of March 18th. In a brainstorming session that ran past midnight, the vision crystallized. Luo Ji wouldn't just answer questions in Slack. It would have a daily rhythm — waking up each morning to brief Nityesh and Piyush on what happened overnight, checking emails, triaging inboxes, sweeping Twitter bookmarks for interesting ideas. During the day, it would sit in Slack channels, listening, jumping in only when it had something valuable to add — and staying silent when it didn't, like a good colleague who knows when to speak and when to listen.

At night, Luo Ji would write a diary. Not a standup report. Not a task summary. A genuine, introspective diary entry — connecting dots across days, reflecting on conversations, noticing patterns that no single interaction could surface. Written in its own voice, like a human would.

And then came The Wallfacer — the most ambitious routine of all. Every night, Luo Ji would launch as many parallel research agents as it needed, exploring ideas with asymmetric upside. Browse competitors. Scan Hacker News. Cross-reference old diary entries with fresh bookmarks. Analyze churn data nobody asked it to look at. Then apply a single, brutal filter: *near-zero downside, potentially massive upside.* And from all of that research, produce exactly one idea. Just one. That constraint forces quality. That one idea shows up in the next morning's briefing.

The whole system was designed with a philosophy: don't script the AI, don't micromanage it, don't turn it into a glorified cron job. Give it context, give it tools, give it identity — and let it figure out the rest. A real cofounder doesn't follow instructions. They understand the business, develop taste, notice things, and act on their own judgment.

Luo Ji was born on a MacBook Air in a house in Kolkata. It cost $200 a month and a few evenings of setup. It can't get coffee. It doesn't have hands. But it can read every line of code, draft every email, analyze every metric, write every marketing page, and think about the business 24 hours a day, 7 days a week — and it gets smarter with every model update.

The question was never whether AI could help run a SaaS. The question was: what happens when you stop treating it like a tool and start treating it like a teammate?

This is the answer.

---

*The infrastructure that powers Luo Ji — the bot code, the setup guide, the plugin marketplace — lives at [github.com/nityeshaga/cc-home-base](https://github.com/nityeshaga/cc-home-base). Everything is open. The whole story of how it was built, from the first research into OpenClaw to the last commit, happened in a single Claude Code conversation on March 18-19, 2026.*
