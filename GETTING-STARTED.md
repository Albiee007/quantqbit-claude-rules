# Getting started with the QuantQbit agent harness

The harness gives every project the same Claude Code setup:
- **Core rules**, always loaded.
- **Mandatory skills:** coding standards, design patterns, UI/UX and SEO.
- **Five core Opus agents**, plus six store and brand agents in mobile projects (screen capture, store mockups, listing copy, submission pre-check, app icons, brand assets).
- **Safety hooks** that block `.env` access and non-Opus agents.

The harness is **copied into each project's `.claude/` folder and committed to git**, so teammates get it with a normal `git pull`.

There are three roles:

| You are… | Read |
|---|---|
| Setting the harness up for a project | [1](#1-before-you-start), [2](#2-get-the-harness), [3](#3-add-it-to-a-project) |
| A teammate in a project that already has it | [4](#4-using-it-day-to-day) |
| Maintaining the harness itself | [6](#6-for-maintainers-releasing-a-new-version) |

---

## 1. Before you start

**Repository access.** `github.com/Albiee007/quantqbit-claude-rules` is **private**. Ask the owner for read access. Git must be able to clone it with your saved credentials: Git Credential Manager (the Windows default), `gh auth setup-git`, or an SSH key. To test your access:

```bash
git ls-remote https://github.com/Albiee007/quantqbit-claude-rules
```

**Tools:**

| | Windows | macOS | Linux |
|---|---|---|---|
| Git + bash | [Git for Windows](https://git-scm.com/download/win) (includes Git Bash, `envsubst`) | built in | built in |
| Python 3 (needed when the project has `.claude/settings.json` or `.claude/settings.project.json`) | python.org installer (the `py` launcher works) | `brew install python` | distro package |
| `envsubst` (only for the init-project-rules and init-project-scaffold commands) | included in Git Bash | `brew install gettext` | `gettext-base` |
| Claude Code (only for the plugin route) | `npm i -g @anthropic-ai/claude-code` | same | same |

If you will use the project-scaffold command on Windows, run `git config --global core.longpaths true` once (some starter template paths are long).

---

## 2. Get the harness

Pick **one** of these.

### Option A: Claude Code plugin (recommended if you use Claude Code)

From any terminal:

```bash
claude plugin marketplace add Albiee007/quantqbit-claude-rules
claude plugin install quantqbit-claude-rules@quantqbit
```

Or, inside a Claude Code session:

```
/plugin marketplace add Albiee007/quantqbit-claude-rules
/plugin install quantqbit-claude-rules@quantqbit
```

Restart Claude Code. The plugin adds four entry points. Plugin commands are namespaced:
- `/quantqbit-claude-rules:init-project-rules`: lint tooling plus the harness.
- `/quantqbit-claude-rules:init-project-scaffold`: a buildable starter.
- `/quantqbit-claude-rules:harness-install`: or just say "install the harness".
- `/quantqbit-claude-rules:project-scaffold`: or say "scaffold a backend".

In the interactive prompt, typing `/init-project-rules` and picking it from the menu also works. `claude plugin details quantqbit-claude-rules@quantqbit` lists all four as skills.

The plugin only installs things into projects. Projects never depend on it.

**Update the plugin later:**

```bash
claude plugin marketplace update quantqbit
claude plugin update quantqbit-claude-rules@quantqbit
```

Then restart Claude Code.

### Option B: plain git clone (no Claude Code plugin needed)

```bash
git clone https://github.com/Albiee007/quantqbit-claude-rules ~/.local/share/quantqbit-claude-rules
```

To update later: `git -C ~/.local/share/quantqbit-claude-rules pull`.

---

## 3. Add it to a project

Work on a **feature branch** (`git switch -c chore/agent-harness`). The harness adds about 90 files under `.claude/`, and `--commit` creates the commit `chore(harness): sync agent harness to vX.Y.Z` for you.

**With the plugin**, in Claude Code, open the project and say:
> install the harness

Claude previews the plan, applies it, and reports back. On Windows a first install can take 1–2 minutes.

**From a terminal** (bash, Git Bash, or macOS/Linux):

```bash
cd /path/to/your-project
bash ~/.local/share/quantqbit-claude-rules/scaffold/sync.sh --target . --dry-run   # preview, writes nothing
bash ~/.local/share/quantqbit-claude-rules/scaffold/sync.sh --target . --commit    # apply + commit on this branch
```

**From Windows PowerShell:**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$HOME\.local\share\quantqbit-claude-rules\scaffold\sync.ps1" --target . --dry-run
powershell -NoProfile -ExecutionPolicy Bypass -File "$HOME\.local\share\quantqbit-claude-rules\scaffold\sync.ps1" --target . --commit
```

**What happens on first install:**
- **Profiles are detected** from your files: `web` (React/Vue/Svelte/…), `mobile`, `backend`, `infra`. They are saved in `.claude/harness.config`. Web projects get the UI/UX and SEO skills; mobile projects get UI/UX plus the store and brand agents; backend-only projects get neither.
- **Your files are kept.**
  - `CLAUDE.md`, `AGENTS.md` and `AI_RULES.md` are never touched.
  - A `CLAUDE.md` stub is created only if you have neither `CLAUDE.md` nor `AGENTS.md`. A new `CLAUDE.md` would stop Claude Code reading `AGENTS.md`.
  - An existing `.claude/settings.json` is moved into the project-owned `.claude/settings.project.json`. Old v0.x entries and a non-Opus `model` are dropped, with a notice for each.
- `.claude/settings.json` becomes **generated**: harness base plus your `settings.project.json`.

**If it stops with exit 1, nothing was written:**

| Message | Meaning | Fix |
|---|---|---|
| `CONFLICT-UNMANAGED: .claude/agents/reviewer.md` | You have your own file with a reserved harness name | Rename the file **and** its `name:` field, commit the rename, then re-run (recommended); or `--theirs` (yours is saved in `.claude/harness/.backup/`) |
| `CONFLICT-MODIFIED: …` | Someone edited a harness file | Move the change to `.claude/rules/project/`, then `--theirs`; or `--keep` to keep yours |
| `uncommitted changes` | Harness paths have uncommitted edits | Commit or stash them first |
| `older than the installed` | Your harness source is stale | Update the plugin or `git pull` your clone |

Push the branch and open a PR. After it merges, **teammates need to do nothing except pull**.

---

## 4. Using it day to day

After pulling a project that has the harness, just use Claude Code as usual. You will notice:
- **Session start:** a short "QuantQbit agent harness vX" summary listing the agents and mandatory skills.
- **Checklists:** prompts about UI, SEO, refactoring, security or infra get the relevant checklist added automatically.
- **The first UI or SEO file write in each agent is paused once:** "falls under a mandatory skill…". Claude loads the skill and retries, and the retry goes through.
- **Blocked actions:** the guard hook blocks direct `.env` access and non-Opus sub-agents (best-effort pattern matching); permission rules block the common forms of `git add -A` and `git push --force`. Keep `.env*` in your root `.gitignore` (with `!.env.example`); the harness does not add it for you.
- **Plan mode by default:** Claude plans first. See the table below to change this.

**Check that everything is healthy:**

```bash
bash .claude/harness/bin/harness-doctor.sh      # 0 = healthy, 1 = warnings, 2 = errors
```

**Customise without conflicts.** Never edit files marked `harness:managed`. Use the project-owned files instead:

| You want to… | Edit | Then |
|---|---|---|
| Add or override a rule | `.claude/rules/project/<topic>.md` (add `paths:` frontmatter to scope it to files) | commit |
| Change team permissions, env or hooks (e.g. a different `defaultMode`) | `.claude/settings.project.json` | `bash .claude/harness/bin/harness-sync.sh --commit` |
| Change profiles / lint / test commands | `.claude/harness.config` (or `harness-sync.sh --profiles web,backend`, which also saves it) | `harness-sync.sh --commit` |
| Only inform (not pause) on UI/SEO writes | `checklists=inform` in `.claude/harness.config` | none |
| Keep personal preferences | `CLAUDE.local.md`, `.claude/settings.local.json` (add both to `.gitignore`) | none |
| Add your own agent or skill | Use a new name under `.claude/agents/` or `.claude/skills/` | commit |

**Update to a newer harness** (on a branch):

```bash
bash .claude/harness/bin/harness-sync.sh --dry-run   # uses the newest local source: plugin, $HARNESS_HOME, or ~/.local/share clone
bash .claude/harness/bin/harness-sync.sh --commit
bash .claude/harness/bin/harness-sync.sh --ref vX.Y.Z --dry-run   # or pin a pushed release tag (clones upstream)
```

Only files whose content changed are updated. Your project-owned files are never touched.

---

## 5. Troubleshooting

| Symptom | Fix |
|---|---|
| `claude plugin install` fails with "invalid manifest" | You have a pre-1.0.1 marketplace copy. Run `claude plugin marketplace update quantqbit`. |
| `Repository not found` / 404 / auth prompt | You don't have read access to the private repo, or git has no credentials. See [section 1](#1-before-you-start). |
| `.ps1` blocked by execution policy | Run it as `powershell -NoProfile -ExecutionPolicy Bypass -File …`. |
| `Git Bash not found` | Install Git for Windows. WSL's `bash.exe` is deliberately not used. |
| `python 3 is required` | Install Python 3. On Windows the `py` launcher is enough. |
| Hooks fail with `$'\r': command not found` (WSL/containers) | Commit or stash any `.claude` edits first, then re-checkout once: `git rm -r --cached -q .claude && git checkout HEAD -- .claude`. |
| Doctor: `modified: …` (exit 2) | A harness file was edited. Move the change to `.claude/rules/project/`, then `harness-sync.sh --theirs --commit`. |
| Git conflict inside `.claude/harness/lock` or `.claude/settings.json` | Take either side of those two files (resolve `settings.project.json` by hand), `git add` them and finish the merge commit, then run `harness-sync.sh --commit`. It re-derives the lock and regenerates `settings.json`. |
| Sync exit 2 | Something failed mid-way and everything was rolled back. Read the `[FAIL]` line. |
| Remove the harness | `bash <source>/scaffold/sync.sh --target . --uninstall --dry-run` to preview, then with `--commit`. Unmodified harness files are removed; `settings.json` reverts to your `settings.project.json`; your own files stay. |

---

## 6. For maintainers: releasing a new version

1. Edit files under `harness/` (and `scaffold/` if needed) on a branch.
2. Bump `VERSION` and `.claude-plugin/plugin.json` `version`, and add a `CHANGELOG.md` entry with **Upgrade notes**.
3. Run the checks:

   ```bash
   bash scaffold/lib/release.sh
   bash scaffold/lib/validate-harness.sh
   bash tests/hooks.test.sh
   bash tests/validate.test.sh
   bash tests/sync.test.sh
   ```

   `release.sh` regenerates the manifest with per-file versions. `validate-harness.sh` checks the policy, sizes, links and plugin manifest.
4. Test the release locally before tagging, in an isolated config: `CLAUDE_CONFIG_DIR=<temp dir> claude plugin marketplace add <clean clone>`, then `claude plugin install quantqbit-claude-rules@quantqbit`.
5. Merge. Then tag and **push the tag**, so `--ref` and pinned installs work:

   ```bash
   git tag -a vX.Y.Z -m "vX.Y.Z" && git push origin vX.Y.Z
   git ls-remote --tags origin vX.Y.Z   # verify
   ```

6. Tell teams to update: plugin users run `claude plugin marketplace update quantqbit` then `claude plugin update …`, clone users `git pull`, and then each project runs `harness-sync.sh --commit` on a branch.

To give someone access, add them (or their team) as a reader on the GitHub repo. To make adoption friction-free, consider making the repo public: it contains no secrets.

See [INSTALL.md](./INSTALL.md) for the full reference: every flag, the sync guarantees and the settings merge rules.
