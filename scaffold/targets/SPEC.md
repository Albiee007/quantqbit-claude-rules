# Target spec (M0)

This file records how each target agent works, for the harness adapters in `scaffold/targets/`. It was written on 2026-10-14 from the official docs. **Every row is docs-only until a real run confirms it.** The `Run` column records the result of those runs (the CLIs are installed in WSL `~/.qqr-agents` and `~/.local/bin`; Antigravity is installed on Windows). `UNCONFIRMED` means no official source states it.

## Plan corrections found by M0
1. **`.agents/` is already used by three tools.**
   - Codex, Gemini CLI and Antigravity all read `.agents/skills/`, so one copy of each skill serves all three.
   - Antigravity also owns `.agents/rules/`, `.agents/agents/`, `.agents/hooks.json` and `.agents/AGENTS.md`.
   - The harness runtime at `.agents/harness/` must not clash with those names. It doesn't today.
2. **Antigravity legacy workflows stop working on 2026-10-19.** Drop the plan to "offer agents as `.agent/workflows`". Antigravity has file-defined subagents (`.agents/agents/*.md`) and hooks (`.agents/hooks.json`), so it is not a "no hooks" target.
3. **Gemini CLI was replaced by Antigravity CLI (`agy`) for unpaid-tier and Google One users on 2026-06-18.** Gemini CLI remains for enterprise and API-key users. Both stay as targets, but Antigravity is the main Google target.
4. **Codex hooks use Claude's I/O format.** The PreToolUse deny and `additionalContext` JSON are the same, `apply_patch` also matches `Edit|Write`, shell appears as `Bash`, and `spawn_agent` matches `Agent`. The normaliser for Codex is therefore mostly Claude's.
5. **Gemini CLI sets `CLAUDE_PROJECT_DIR`** (an alias of `GEMINI_PROJECT_DIR`).
6. **No target documents a subagent flag on tool events** (Codex, Gemini, Antigravity). `HH_SUBAGENT=unknown` is the default outside Claude, so the sub-agent approval checks are a documented gap there.
7. **Codex and Copilot `apply_patch` are the multi-file patches** (Codex puts it in `tool_input.command`). Antigravity `multi_replace_file_content` edits several chunks of *one* file.
8. **Cursor and Copilot already read Claude's files.**
   - Cursor (Third-Party Imports, on by default) loads hooks from `.claude/settings*.json`, skills from `.claude/skills`, and agents from `.claude/agents`. Copilot CLI reads the same three.
   - VS Code Local reads `.claude/skills`, `.claude/agents` and `.claude/rules` (`paths:`). It reads `.claude` hooks only with `chat.useClaudeHooks`, and then with **no matchers**.
   - Consequence 1: a project with both `claude` and `cursor` selected must **not** also write `.cursor/hooks.json` entries for the same hooks, or every hook fires twice. The adapters need a dedupe rule: when `claude` is installed, `cursor` and `copilot-cli` reuse the Claude hooks, and only the gaps get native entries.
   - Consequence 2: every hook script must filter on its own operation, never trust the matcher, so it stays correct under VS Code's matcher-less mode.
   - Consequence 3: a 1.x Claude install is already partly active in Cursor and Copilot CLI today. M0 runs must check what our hooks actually receive there (Cursor maps the output; whether it maps the input to Claude format is UNCONFIRMED).
9. **Copilot differs by surface.** Cloud agent reads only `.github/hooks/*.json` (camelCase, `bash` key) from the default branch. CLI accepts PascalCase (Claude-format I/O, Claude tool names) or camelCase. VS Code Local has its own format. Copilot targets split into `copilot` (CLI, plus VS Code via the shared files) and the cloud agent's `.github/hooks`.
10. **Blocking that works everywhere is exit 2 with a reason on stderr.** It works on every surface except Antigravity (UNCONFIRMED). The emitter should print the JSON deny *and* exit 2 where the target accepts both.
11. **Ignore files never cover the shell** (`.cursorignore`, Copilot content exclusion, `.geminiignore`), and Copilot content exclusion does not apply to VS Code agent mode. Hooks and permission deny rules are the only enforcement.

## Codex CLI (0.162.1, docs: learn.chatgpt.com/docs)
| Area | Spec | Run |
|---|---|---|
| Instructions | `AGENTS.override.md` / `AGENTS.md` / `project_doc_fallback_filenames`, one per directory from the git root down to the cwd, root first. 32 KiB total (`project_doc_max_bytes`). No `@` imports (UNCONFIRMED). | |
| Path rules | None for instructions; scoping is by directory. `.codex/rules/*.rules` (Starlark) are command-prefix exec policies, not globs. | |
| Skills | `.agents/skills` (cwd up to the repo root), `~/.agents/skills`, `/etc/codex/skills`. Frontmatter `name` and `description`. Extras go in `agents/openai.yaml`. `.claude/skills` is not read (UNCONFIRMED). | |
| Subagents | `.codex/agents/*.toml`: `name`, `description`, `developer_instructions` (required); `model*`, `features.*`, `skills.*`. **No tools allowlist.** | |
| Commands | Custom prompts are deprecated in favour of skills. | |
| Hooks config | `.codex/hooks.json` or `[hooks]` in `.codex/config.toml`. Same shape as Claude: `{"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[{"type":"command","command":"…","commandWindows":"…","timeout":30}]}]}}`. All layers are merged. | |
| Events | SessionStart, SessionEnd, PreToolUse, PermissionRequest, PostToolUse, Pre/PostCompact, UserPromptSubmit, SubagentStart/Stop, Stop, Interrupt. | |
| Block | PreToolUse: `hookSpecificOutput.permissionDecision:"deny"`, or exit 2. Unsupported fields such as `ask` make the hook count as failed, and **the call proceeds** (fail-open). PostToolUse block replaces the result; the side effect stays. | |
| Context | `hookSpecificOutput.additionalContext` on SessionStart, UserPromptSubmit, SubagentStart, Pre/PostToolUse. Default cap 2,500 tokens. | |
| Payload | `session_id` (the parent's id inside subagents), `cwd`, `hook_event_name`, `tool_name`, `tool_input`, `tool_use_id`, `turn_id`. Bash and `apply_patch` both use `tool_input.command`. Raw patch text with `*** Move to:` is UNCONFIRMED. Reads go through the shell. | |
| Env | Only plugin vars. The hook's cwd is the session cwd. There is no project-dir var. | |
| Trust | `[projects."<path>"] trust_level="trusted"` is needed, or every `.codex/` layer is skipped. Every non-managed hook must be reviewed with `/hooks`; trust is tied to the hook's hash, so a new or changed hook is skipped until re-trusted. `[features] hooks` is on by default. `allow_managed_hooks_only` exists. Where trust is stored is UNCONFIRMED. | |
| `.env` | `permissions.<profile>.filesystem."**/*.env"="deny"` plus `default_permissions`. No ignore file. | |
| Tools | shell→`Bash`, `apply_patch`, `spawn_agent`, `update_plan`, `view_image`, hosted `web_search` (no hooks fire). | |

## Gemini CLI (0.64.0, docs: geminicli.com/docs)
| Area | Spec | Run |
|---|---|---|
| Instructions | `GEMINI.md`: global, then workspace and ancestors, then just-in-time on paths that tools touch. `context.fileName` can add `AGENTS.md`. `@./file.md` imports (depth 5). | |
| Path rules | None. | |
| Skills | `.agents/skills` (wins) or `.gemini/skills`; `~/.agents/skills` or `~/.gemini/skills`. Frontmatter `name` and `description`. Activated through `activate_skill`, with user consent. | |
| Subagents | `.gemini/agents/*.md` frontmatter: `name`, `description`, `kind`, `tools` (wildcards), `mcpServers`, `model` (default inherit), `temperature`, `max_turns`, `timeout_mins`. | |
| Commands | `.gemini/commands/**/*.toml` (`prompt`, `description`, `{{args}}`). | |
| Hooks config | `hooks` in `.gemini/settings.json`: `{"BeforeTool":[{"matcher":"write_file|replace","hooks":[{"type":"command","command":"…","name":"…","timeout":60000}]}]}`. Timeout is in **ms**. | |
| Events | BeforeTool, AfterTool, BeforeAgent, AfterAgent, BeforeModel, AfterModel, BeforeToolSelection, SessionStart, SessionEnd, PreCompress, Notification. | |
| Block | BeforeTool: `{"decision":"deny","reason":"…"}`, or exit 2. Other exit codes are a warning and the call proceeds (fail-open). Stdout must be JSON only. | |
| Context | `hookSpecificOutput.additionalContext` on BeforeAgent (prompt), AfterTool and SessionStart. | |
| Payload | `session_id`, `cwd`, `hook_event_name`, `tool_name`, `tool_input`. `run_shell_command{command,dir_path}`, `read_file{file_path}`, `replace{file_path,…}`, `write_file{file_path,content}`. No multi-file or rename tool. | |
| Env | `GEMINI_PROJECT_DIR`, `CLAUDE_PROJECT_DIR` (alias), `GEMINI_SESSION_ID`, `GEMINI_CWD`. | |
| Trust | Untrusted folders ignore `.gemini/settings.json` (so project hooks don't load). Trust is stored in `~/.gemini/trustedFolders.json`. The folder-trust default conflicts between doc pages. Project hooks are fingerprinted by name+command, and a changed hook warns before it runs. `hooksConfig.enabled` and `hooksConfig.disabled` exist. | |
| `.env` | `.geminiignore` (gitignore syntax). Whether it blocks `read_file` is UNCONFIRMED. | |
| Tools | `run_shell_command`, `read_file`, `read_many_files`, `write_file`, `replace`, `grep_search`, `glob`, `list_directory`, `web_fetch`, `google_web_search`, `activate_skill`. Each subagent is a tool named after the agent. | |

## Antigravity (app 2.23.0, CLI `agy` 1.3.1, docs: antigravity.google/docs)
| Area | Spec | Run |
|---|---|---|
| Instructions | `AGENTS.md`/`GEMINI.md`, `.agents/AGENTS.md`, `.agents/rules/*.md` (legacy `.agent/rules`) in each directory up to the workspace root. Limit 24,000 bytes per file; a 20k-token always-on budget, above which the largest files become pointer lines. `@[label](path)` inlines a file. | |
| Path rules | **Yes.** `.agents/rules/*.md` frontmatter `trigger: always_on|model_decision|glob|manual`, `description`, `globs: "a, b"` (comma-separated, quoted). A rule with no frontmatter or a bad trigger is **silently dropped**. Only the top level is read unless `.agents/rules.json` says otherwise. | |
| Skills | `.agents/skills/<n>/SKILL.md` (legacy `.agent/skills`). Frontmatter `description` (required) and `name`. The CLI exposes each skill as `/<name>`. | |
| Subagents | `.agents/agents/<n>.md` or `<n>/agent.md`: `name`, `description`, `tools`, `model` (inherit, flash or pro), `commandExecutionPolicy`, `skills`, `rules`, `hooks`, `mcpServers`. A misspelled tool can hang the agent. | |
| Workflows | **Stop working on 2026-10-19.** Replaced by skills. | |
| Hooks config | `.agents/hooks.json`. Top-level keys are hook *names*: `{"harness":{"enabled":true,"PreToolUse":[{"matcher":"run_command","hooks":[{"type":"command","command":"…","timeout":30}]}]}}`. | |
| Events | SessionStart, PreToolUse, PostToolUse, PreInvocation, PostInvocation, Stop. No prompt-submit event. | |
| Block | PreToolUse `{"decision":"deny","reason":"…"}`. Exit-code semantics are UNCONFIRMED. A failing hook does not stop the session (fail-open). | |
| Context | `{"injectSteps":[{"ephemeralMessage":"…"}]}` on SessionStart, PreInvocation and PostInvocation. | |
| Payload | `conversationId`, `workspacePaths`, `toolCall{name,args}`. `run_command{CommandLine,Cwd}`, `view_file{AbsolutePath}`, `replace_file_content{TargetFile}`, `multi_replace_file_content{TargetFile,ReplacementChunks}`, `write_to_file{TargetFile}`, `invoke_subagent{Subagents[]}`. **PascalCase keys.** | |
| Env | UNCONFIRMED. The root comes from `workspacePaths`. | |
| Trust | No trust or hook-approval mechanism is documented. Each hook has its own `enabled` flag. | |
| `.env` | Permission rules `read_file(<path>)` deny (CLI `~/.gemini/antigravity-cli/settings.json`). No project-level key is documented. | |
| Tools | `run_command`, `view_file`, `write_to_file`, `replace_file_content`, `multi_replace_file_content`, `grep_search`, `find_by_name`, `list_dir`, `read_url_content`, `search_web`, `invoke_subagent`, `browser_*`. | |

## Cursor (IDE 3.24, CLI `agent` 2026.10.08, docs: cursor.com/docs)
| Area | Spec | Run |
|---|---|---|
| Instructions | `AGENTS.md` (root and nested; the more specific one wins). The CLI also reads `CLAUDE.md`; for the IDE it is UNCONFIRMED. Team, then Project, then User rules. | |
| Path rules | `.cursor/rules/**/*.mdc` only (plain `.md` is ignored). Frontmatter `description`, `globs` (comma-separated; `**/*.ts` for any depth), `alwaysApply`. | |
| Skills | `.agents/skills`, `.cursor/skills`, plus compatibility dirs `.claude/skills` and `.codex/skills`. `name` must equal the folder name. Optional `paths`, `disable-model-invocation`, `user-invocable`. | |
| Subagents | `.cursor/agents`, `.claude/agents`, `.codex/agents` (`.cursor/` wins on a duplicate name). Fields `name`, `description`, `model`, `readonly`, `is_background`. No `tools` field. | |
| Hooks config | `.cursor/hooks.json` `{"version":1,"hooks":{"preToolUse":[{"command":"…","matcher":"…","timeout":30,"failClosed":false}]}}`. Also reads Claude `.claude/settings*.json` hooks. | |
| Events | sessionStart/End, preToolUse, postToolUse(+Failure), subagentStart/Stop, before/afterShellExecution, before/afterMCPExecution, beforeReadFile, afterFileEdit, beforeSubmitPrompt, preCompact, stop, afterAgentResponse, Tab hooks. | |
| Block | Exit 2, or `{"permission":"deny","user_message","agent_message"}` on preToolUse, beforeShellExecution, beforeMCPExecution, beforeReadFile, subagentStart. Other exits fail open unless `failClosed`. **`afterFileEdit` cannot block.** | |
| Context | `additional_context` on sessionStart, postToolUse, postToolUseFailure. **No prompt-time context.** preToolUse has no context output (UNCONFIRMED). | |
| Payload | `conversation_id`, `workspace_roots[]`, `hook_event_name`. preToolUse `tool_name` is Shell, Read, Write, Grep, Delete, Task or `MCP:x`. `beforeReadFile{file_path}`, `beforeShellExecution{command,cwd}`, `afterFileEdit{file_path,edits[]}`. Write `tool_input` shape, multi-file edits and renames are UNCONFIRMED. Subagent tool events carry a parent tool-call id (since 3.22; field name UNCONFIRMED). | |
| Claude compatibility | Event map PreToolUse→preToolUse, UserPromptSubmit→beforeSubmitPrompt, etc. Tool map Bash→Shell, Edit→Write. **Glob is unsupported.** The output is mapped. | |
| Env | `CURSOR_PROJECT_DIR`, `CLAUDE_PROJECT_DIR` (alias), `CURSOR_VERSION`. | |
| Trust | Project hooks run only in trusted workspaces (workspace trust is off by default). Headless CLI needs `--trust`. No official way to detect activation; use a `sessionStart` canary marker. | |
| `.env` | `.cursorignore` (`.env*` is ignored by default). **The terminal and MCP are not covered.** CLI permissions `Read(...)` deny in `.cursor/cli.json`. | |

## GitHub Copilot (CLI 1.0.97, VS Code 1.141, cloud agent; docs: docs.github.com, code.visualstudio.com)
| Area | Spec | Run |
|---|---|---|
| Instructions | `.github/copilot-instructions.md`, `.github/instructions/**/*.instructions.md`, `AGENTS.md`. CLI: `CLAUDE.md` and `GEMINI.md`. VS Code: `CLAUDE.md` and `.claude/rules/*.md` (`paths:`). All are additive. | |
| Path rules | `*.instructions.md` frontmatter `applyTo: "**/*.ts,**/*.tsx"` and `excludeAgent: code-review|cloud-agent`. VS Code adds `name` and `description`. | |
| Skills | `.github/skills`, `.claude/skills`, `.agents/skills`. `name` (max 64, must equal the directory) and `description` (max 1024). Optional `license`, `allowed-tools`; VS Code adds `argument-hint`, `user-invocable`. | |
| Agents | `.github/agents/*.agent.md`; VS Code and CLI also read `.claude/agents/*.md`. Fields `name`, `description`, `tools` (aliases `execute`, `read`, `edit`, `search`, `agent`, `web`), `model`, `target`, `hooks`. Body max 30,000 chars. | |
| Hooks: CLI | `.github/hooks/*.json`, inline in `.github/copilot/settings.json`, **`.claude/settings*.json`**, `~/.copilot/hooks`. PascalCase events get Claude-format I/O with Claude tool names. `disableAllHooks`. `/env` lists loaded hooks. | |
| Hooks: cloud | Only `.github/hooks/*.json` on the **default branch**. camelCase `{"version":1,"hooks":{"preToolUse":[{"type":"command","bash":"…","timeoutSec":30}]}}`. Payload `toolName` and `toolArgs`. Linux only. | |
| Hooks: VS Code Local | `.github/hooks/*.json` (PascalCase), `~/.copilot/hooks`. `.claude` hooks only with `chat.useClaudeHooks`, with **matchers ignored**. `windows`, `linux`, `osx` command overrides. Tool names are UNCONFIRMED (`edit/editFiles`, …?). | |
| Block | `permissionDecision:"deny"` plus a reason, or exit 2. CLI: any other non-zero exit on preToolUse **denies** (fail-closed), while a timeout fails open. | |
| Context | `additionalContext` on sessionStart, postToolUse, subagentStart. `userPromptSubmitted` output is **dropped** for command hooks. | |
| Subagent | subagentStart/Stop events. Whether tool events carry a subagent id is UNCONFIRMED. | |
| Env | No project-dir var; use the payload's `cwd`. In cloud the cwd is `/workspace`. | |
| Trust | VS Code: a trusted workspace, `chat.useHooks` (on by default), and policies `ChatHooks` / `ChatAllowManagedHooksOnly`. CLI: trust the launch directory. Repo hooks in `-p` mode reportedly need `GITHUB_COPILOT_PROMPT_MODE_REPO_HOOKS=true` (UNCONFIRMED). | |
| `.env` | Content exclusion does **not** apply to VS Code agent mode or the shell. CLI `--deny-tool 'read(.env)'`. Hooks are the only cross-surface enforcement. | |
