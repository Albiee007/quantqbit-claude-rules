# Git Commits

Only commit or push when the user/task asks for it. Follow the project's existing commit style if it differs from below (check `git log --oneline -20`, commitlint config, CONTRIBUTING).

## Conventional Commits

```
<type>(<optional scope>): <imperative summary, <= 72 chars, no period>

<body: why the change was needed, what approach, trade-offs. Wrap at 72.>

<footers: BREAKING CHANGE: ..., Refs: #123, Co-Authored-By: ...>
```

| Type | Use for |
|---|---|
| `feat` | new user-facing capability (minor bump) |
| `fix` | bug fix (patch bump) |
| `refactor` | code change with no behavior change |
| `perf` | performance improvement |
| `test` | adding/fixing tests only |
| `docs` | documentation only |
| `build` / `ci` | build system, dependencies, CI config |
| `chore` | maintenance that fits nothing else |
| `revert` | reverts a previous commit |

Breaking change: `feat(api)!: remove v1 endpoints` and/or `BREAKING CHANGE:` footer.

Good: `fix(auth): reject expired refresh tokens before rotation`
Bad: `fixed stuff`, `WIP`, `update file.ts`, `Addressed review comments`.

## Atomic commits

- One logical change per commit; the build and tests pass at every commit (bisectable).
- Separate refactors/renames/formatting from behavior changes.
- Don't mix unrelated fixes. Don't split one change so that intermediate commits are broken.

## Staging

- **Stage by explicit path:** `git add src/auth/token.ts test/auth/token.test.ts`.
- Avoid `git add -A` / `git add .` / `git commit -a` — they sweep in stray files, build output, local config, and secrets.
- Review before committing: `git status` and `git diff --staged`.
- Never commit: `.env*` (except `.env.example`), credentials, keystores (`*.jks`, `*.keystore`, `*.p12`, `*.pem`), `node_modules`, build outputs, IDE files, large binaries (use LFS), local DB dumps.
- If a secret was committed: stop, rotate it, then clean history with the team's agreement. Deleting in a new commit is not enough.

## Safety

- Never `--force` push to shared branches; use `--force-with-lease` on your own branch only when needed.
- Never skip hooks (`--no-verify`) or signing unless explicitly asked. If a hook fails, fix the cause.
- Prefer new commits over amending pushed commits.
- Don't rewrite history on `main`/release branches.
- Branch from the default branch for new work; keep branches short-lived; rebase or merge per project convention.

## PR hygiene

- PR title follows the commit convention; description covers what, why, how tested, risks/rollback, and screenshots for UI.
- Keep PRs small (< ~400 changed lines where possible); stack if larger.
- If you introduced a design pattern/abstraction, include the `design-patterns` Decision Gate answers.

## Sources

- Conventional Commits 1.0.0: https://www.conventionalcommits.org/en/v1.0.0/
- Chris Beams, "How to Write a Git Commit Message": https://cbea.ms/git-commit/
- Git documentation, `git add`: https://git-scm.com/docs/git-add
- GitHub, "Removing sensitive data from a repository": https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
