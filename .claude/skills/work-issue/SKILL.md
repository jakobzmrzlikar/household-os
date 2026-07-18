---
name: work-issue
description: Take a Linear issue end-to-end — branch from main, implement with TDD across commits, then open a GitHub PR with the user as reviewer. Use when the user says "work issue SOL-123", "pick up <issue>", "implement this Linear ticket", or invokes /work-issue.
argument-hint: <LINEAR-ISSUE-ID e.g. SOL-123>
---

# work-issue

Drive a single Linear issue from "assigned" to "PR open for review", following this
project's conventions (hexagonal layering, attrs/pydantic, TDD, Conventional Commits).

The issue identifier is in `$ARGUMENTS` (e.g. `SOL-123`). If it is empty, ask the user
which issue to work, then stop until they answer.

## Invariants (do not violate)

- **Never commit to `main`.** All work happens on a branch created from an up-to-date `main`.
  (A `PreToolUse` hook also enforces this — if a commit is blocked, you are on the wrong branch.)
- **TDD when feasible**: write a failing test first, then make it pass. Skip only when the
  change is untestable (pure config/docs) — and say so explicitly.
- **One logical change per commit**, Conventional Commits format (`type(scope): subject`).
  commitizen's `commit-msg` hook will reject anything else.
- Run all backend commands from `backend/`.

## Procedure

### 1. Understand the issue
- Fetch it: `mcp__linear__get_issue` with the id from `$ARGUMENTS`.
- Read the title, description, acceptance criteria, and any linked comments
  (`mcp__linear__list_comments`).
- Restate to the user, in 2-3 sentences, what you're about to build and your test plan.
  If the issue is ambiguous or missing acceptance criteria, ask before coding.
- Move the issue to "In Progress": `mcp__linear__save_issue` (set the appropriate state).

### 2. Branch from main
- Use **Linear's own branch name** for the issue (the `branchName` field on the fetched
  issue, e.g. `jakob/sol-123-add-trip-search`) so Linear auto-links the branch.
- Create it from a fresh main:
  ```bash
  git checkout main && git pull --ff-only
  git checkout -b <linear-branch-name>
  ```

### 3. Implement with TDD (iterate over multiple commits)
For each slice of the feature:
1. **Confirm placement first.** Per ADR-0005, decide the layer (`domain` / `application` /
   `adapter` / `infrastructure`) before writing. Read the relevant `.claude/rules/` file for
   any file you create or modify (tests.md, ports.md, code-ordering.md, documentation.md).
2. Write a **failing test** in `backend/tests/` following `tests.md` naming
   (`test_{unit}_should_{expected}_when_{condition}`). Run `uv run pytest <file>` and watch it fail.
3. Implement the minimal code to pass. Re-run the test until green.
4. Commit the slice (Conventional Commits). Repeat for the next slice.

### 4. Gate before pushing
From `backend/`, run the full check suite and fix anything that fails:
```bash
uv run ruff check --fix ./ && uv run ruff format ./
uv run lint-imports          # hexagonal boundaries (ADR-0005)
uv run basedpyright          # strict typing (ADR-0007)
uv run pytest                # full suite
```
Do not open the PR until all four pass.

### 5. Open the PR and assign the user
```bash
git push -u origin <linear-branch-name>
gh pr create \
  --base main \
  --title "<type(scope): subject mirroring the issue>" \
  --body "<summary + 'Closes <issue-url>' + test notes>" \
  --assignee jakobzmrzlikar
```
- Use `--assignee`, **not** `--reviewer`: PRs are authored by jakobzmrzlikar's account,
  and GitHub rejects a review request from the PR's own author. Assigning surfaces the PR
  in the user's dashboard; they review the diff and self-merge.
- Put the Linear issue URL in the PR body so Linear links the PR to the issue.
- End the PR body with the standard trailer:
  `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

### 6. Report back
- Print the PR URL.
- Optionally move the Linear issue to "In Review" via `mcp__linear__save_issue`.
- Summarize what shipped, the commits made, and anything left for the reviewer to note.