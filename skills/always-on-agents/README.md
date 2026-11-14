# always-on-agents

Use this skill when you design an agent that wakes up on events or timers, works unattended across many runs, and messages the user without being asked. It first checks whether you really need an always-on agent, then walks through five parts: event inbox, timers, memory, permissions, and outbox.

The agent definition is `SKILL.md`. `PRINCIPLES.md` explains each concept with an everyday analogy first, then a formal definition. `CHECKLIST.md` lists verifiable checks per part. `templates/` holds stack-neutral SQL tables (`inbox.sql`, `timers.sql`, `outbox.sql`) and Markdown templates (`MEMORY.md`, `PERMISSIONS.md`, `SEND_POLICY.md`).

Based on Anthropic's article [Building always-on agents](https://claude.com/resources/articles/building-always-on-agents). The schemas and checks are this repo's own and have not been validated at scale.
