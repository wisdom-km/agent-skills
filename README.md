# agent-skills

Collection of programming and AI agent skills (primarily `SKILL.md` files) for Cursor, Grok, Claude Code, and other coding agents.

This repository will hold additional skills over time. Current skills:

- [`architecture-from-idea`](skills/architecture-from-idea/) — Choose a throwaway demo, a tracer-bullet skeleton, or a long-lived product, then record the architecture before any code.
- [`agent-constraint-docs`](skills/agent-constraint-docs/) — Write or update the documents coding agents follow once the architecture is agreed.
- [`vibe-coding-loop`](skills/vibe-coding-loop/) — Run each coding task as a scoped loop: brief, plan, implement, verify, and review.
- [`architecture-guardrails`](skills/architecture-guardrails/) — Turn exception-free architecture rules into linters, structural tests, CI gates, or agent hooks.

## Structure

Each skill lives in its own directory:

```
skills/
  skill-name/
    SKILL.md          # required: the skill definition
    README.md         # optional: human-readable description
    examples/         # optional
    scripts/          # optional
```

You can also put individual skill files at the root if preferred, but the directory-per-skill layout scales better.

## How many skills can this repo hold?

GitHub does not impose a hard limit on the number of files in a repository.

Practical recommendations from GitHub:
- Single directory: ideally under ~3,000 entries (to keep Git operations fast)
- Total on-disk size of the `.git` folder: ideally under 10 GB (skills are tiny text files, so this is effectively unlimited for normal use)
- File size: keep individual files under 100 MB (enforced); recommended under 1 MB

For typical `SKILL.md` skills (a few KB each), you can comfortably store **hundreds to several thousand** skills in this repository without issues. Organize them in subdirectories if you exceed a few hundred in one folder.

## Adding a new skill

1. Create a new directory under `skills/` (or wherever you prefer).
2. Add a `SKILL.md` file following the format expected by your agent (usually YAML frontmatter + instructions).
3. Commit and push.

## License

Add a license if you plan to share skills publicly.
