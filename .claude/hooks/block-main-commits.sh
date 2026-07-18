#!/usr/bin/env bash
# PreToolUse(Bash) guardrail: refuse `git commit` / `git push` while on the main branch.
# Enforces the work-issue invariant ("never commit to main") deterministically, so it
# holds even outside the /work-issue skill. Reads the hook payload from stdin.
set -euo pipefail

payload="$(cat)"
command="$(printf '%s' "$payload" | jq -r '.tool_input.command // ""')"

# Only inspect git commit / git push invocations.
if ! printf '%s' "$command" | grep -Eq '\bgit\b.*\b(commit|push)\b'; then
  exit 0
fi

branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
if [ "$branch" != "main" ]; then
  exit 0
fi

reason="Blocked: you are on 'main'. Create a feature branch first (e.g. via /work-issue, which uses the Linear branch name) before committing or pushing."
jq -n --arg r "$reason" '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: $r
  }
}'
exit 0