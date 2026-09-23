# Harness Core Rules

Always loaded. Vendored by the QuantQbit agent harness into `.claude/rules/harness/`.
Detail lives in skills and path-scoped rules. This file stays short on purpose.

## 1. Precedence
- Project instructions (`CLAUDE.md`, `AGENTS.md`, `.claude/rules/project/`) override harness rules where they conflict.
- **Not overridable:** secrets/`.env` handling (§8), the Opus model policy (§2), and accessibility minimums (skill `ui-ux`).
- If two instructions conflict and neither clearly wins, ask the user. Do not pick one silently.

## 2. Model: Opus only
- Every sub-agent runs on Opus. Pass `model: "opus"` when spawning with the Agent tool.
- Settings force this (`CLAUDE_CODE_SUBAGENT_MODEL=opus` overrides agent frontmatter), and a hook denies any other requested model. Do not try to work around either.
- If a tool, skill or plugin routes to a smaller model, tell the user before continuing.

## 3. Plan mode
- In plan mode, take only read-only actions until the user approves the plan.
- A plan names: the files to change, the approach, the risks, and how the change will be verified.

## 4. Orchestration (who does what)
| Situation | Delegate to |
|---|---|
| Unknown area, or more than 3 files/searches needed to answer | `explorer` (read-only; run several in parallel for independent questions) |
| Application code change (backend, frontend, mobile) | `implementor` |
| Shell, PowerShell, Ansible, Compose, Terraform, CI change | `infra-implementor` |
| After every change | `verifier` (lint, typecheck, tests, syntax checks) |
| Before calling a non-trivial change done | `reviewer` with the right lens: `code`, `patterns`, `ux`, `seo`, `security` or `all` |

- Never delegate understanding: read the explorer's findings yourself before planning.
- Brief sub-agents fully: goal, files, constraints, the definition of done. They start with no context.
- Independent work runs in parallel. Dependent work runs in sequence.
- Review what a worker produced before reporting it. A worker saying "done" is not proof.

## 5. Mandatory skills
Load the skill **before** starting the matching work. This is required, not optional.

| Work | Skill |
|---|---|
| Any UI: screens, components, styles, layout, forms, UI copy, design tokens | `ui-ux` |
| Public web pages, routes, metadata/head, sitemap, robots, structured data, content | `seo` |
| Introducing a pattern, abstraction, new layer, interface, or refactoring architecture | `design-patterns` (run the decision gate first) |
| Writing or reviewing any code | `coding-standards` (always in effect) |

Hooks inject a short checklist when a prompt or file matches one of these. That checklist does not replace the skill.
The first UI or SEO file write in each agent context is denied once: read the named `.claude/skills/<skill>/SKILL.md`, apply it, then retry the same write.

## 6. Verification before "done"
Run the checks that match the change, and report the actual result:
- Project lint command (`lint_cmd` in `.claude/harness.config`, otherwise `scripts/lint.sh` or `make lint`)
- Typecheck and unit tests for touched code
- Bash: `bash -n` and `shellcheck`. PowerShell: parse check and PSScriptAnalyzer if installed
- Ansible: `ansible-playbook --syntax-check`. Terraform: `terraform fmt -check && terraform validate`. Compose: `docker compose config --quiet`

If a check cannot run (tool missing, network blocked), say so and state what remains unverified. Never claim a check passed if it did not run.

## 7. Cross-platform
- Scripts that run on Linux servers are bash only.
- Scripts that developers run on their own machines ship as a `.sh` + `.ps1` pair.
- Use LF line endings.
- Never hardcode user-specific absolute paths (`C:\Users\...`, `/home/...`, `/Users/...`).

## 8. Secrets and `.env`: never touch (critical)
- Never read, write, edit, delete, restore, stage or commit `.env` / `.env.*` files. Only `.env.example` and `.env.template` may be edited.
- Never print secrets, tokens or credentials in output, logs, commits or PRs.
- If a `.env` looks lost or broken, tell the user and let them fix it.
- Reason: a past incident destroyed a developer's `.env`.

## 9. Git
- Commit on the current branch. If a worker made commits in a worktree branch, cherry-pick them onto the current branch.
- Stage explicit paths only. Never `git add -A`, `git add .` or `git add --all`.
- Follow the repo's commit style. Never skip hooks (`--no-verify`) unless the user asks.
- Never push directly to the staging or deploy branch (`develop`, `dev`, `staging` or `main`, per the project) while it is checked out. Ask the user first.
- Never merge into `main` automatically. Never force-push shared branches.
- Surface unrelated uncommitted changes to the user. Never fold them into your commit.

## 10. Engineering discipline
- Make the smallest change that solves the task. No drive-by refactors or speculative features.
- YAGNI and the rule of three: no abstraction without at least three real uses or a stated requirement.
- Match the idiom, naming and structure of the surrounding code before adding anything new.
- Reuse existing utilities and components. Search before writing new ones.
- Leave no dead code, commented-out code, or TODOs without an owner.

## 11. Harness-managed files
- Files marked `harness:managed` (in `.claude/rules/harness/`, `.claude/skills/<harness skill>/`, `.claude/agents/<harness agent>.md` and `.claude/harness/`) are owned by the harness. Do not edit them.
- To change behaviour, add or edit files in `.claude/rules/project/`, the project `CLAUDE.md`, or `.claude/settings.project.json`.
- `.claude/settings.json` is generated. Put setting changes in `.claude/settings.project.json`, then run harness sync.
- Run `bash .claude/harness/bin/harness-doctor.sh` to check harness health (stale, modified or missing files).
