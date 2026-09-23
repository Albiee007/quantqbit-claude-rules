# Project rules (project-owned)

Put this project's own agent rules here. The files in this folder belong to the project: the harness never modifies them, so edits cannot conflict with harness updates.

- **Where each kind of file lives:**
  - Harness rules are in `.claude/rules/harness/`. They are managed by the harness, so do not edit them there.
  - Put project conventions, overrides and domain rules in this folder, one topic per file, for example `api-errors.md` or `design-system.md`.
- **When rules conflict:** project rules and `CLAUDE.md` take precedence over harness rules. The exceptions are `.env` and secrets handling, the Opus model policy, and the accessibility minimums, which cannot be overridden.
- **Scoping a rule to files:** add YAML frontmatter:

  ```markdown
  ---
  paths:
    - "src/api/**/*.ts"
  ---
  # API rules
  - All endpoints return the ApiError envelope from src/api/errors.ts
  ```

  A rule without `paths` loads in every session. Keep those short.
- **Team settings:** permissions, env and extra hooks go in `.claude/settings.project.json`. After editing it, re-run harness sync to regenerate `.claude/settings.json`.
- **Personal settings:** these belong in `CLAUDE.local.md` and `.claude/settings.local.json`, both of which must be gitignored.
