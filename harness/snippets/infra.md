Harness infra checklist (bash / PowerShell / Ansible / Compose / Terraform / Docker):
- Delegate the edit to the `infra-implementor` agent. It follows `.claude/rules/harness/<stack>.md`.
- bash: `set -euo pipefail`, quote every expansion, `[[ ]]`, prefixed snake_case functions, `bash -n` + shellcheck.
- Developer-machine scripts ship as a `.sh` + `.ps1` pair. Server-only scripts are bash only.
- Ansible: FQCN modules, a `name:` on every task, idempotent tasks, handlers for restarts, `--syntax-check`.
- Compose: no `version:`, a healthcheck per service, `${VAR}` values only, `docker compose config --quiet`.
- Terraform: variables instead of literals, remote state, never commit `*.tfvars` or state, `fmt -check` + `validate`.
- Never touch `.env` / `.env.*`. Never run destructive commands (apply, destroy, prune) without explicit approval.
- After editing, run the `verifier` agent.
