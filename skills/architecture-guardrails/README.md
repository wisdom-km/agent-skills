# architecture-guardrails

Use this skill when an architecture rule must hold with no exceptions and should be enforced by a linter, structural test, CI gate, or agent hook.

The agent definition is `SKILL.md`. Concrete recipes are in `recipes/`.

`templates/project/` holds copy-in files that make the mandatory items block for real: `scripts/check` (plus `check.ps1`), `.pre-commit-config.yaml`, a GitHub Actions `ci.yml`, Stop hooks for Claude Code, Cursor, and Codex, and a Cursor Always Apply rule. `recipes/mandatory-gates.md` explains setup, which mandatory item each check enforces, and how to require the CI check with branch protection.
