# `.claude/` — project Claude Code config

Per-project configuration that Claude Code reads when working in this repo.

| Path | Committed? | Purpose |
| --- | --- | --- |
| `settings.json` | yes | Shared project settings (permissions, hooks, env). |
| `settings.local.json` | no (gitignored) | Your personal overrides — not shared. |
| `rules/` | yes | Path-scoped coding conventions (read before editing matching files). |
| `skills/` | yes | Project skills — reusable capabilities. |
| `agents/` | yes | Project subagents. |

Note: **`.mcp.json` lives at the repo root, not here.** That is the path
Claude Code uses for project-scoped MCP servers (e.g. the Linear server).
