# Bash / Shell Notes

Use bash for glue (< ~100 lines, simple control flow). Beyond that — data structures, JSON manipulation, error recovery — use Python/Node/Go.

## Idioms

- Shebang `#!/usr/bin/env bash`; strict mode at the top:
  ```bash
  set -Eeuo pipefail
  IFS=$'\n\t'
  ```
  Know its limits: `set -e` is ignored inside `if`/`&&`/`||` conditions and in functions called from them; check critical commands explicitly.
- Quote every expansion: `"$var"`, `"$@"`, `"${arr[@]}"`, `"$(cmd)"`.
- `[[ ... ]]` for tests in bash; `(( ... ))` for arithmetic; `$(...)` not backticks.
- `local` for function variables; `readonly` for constants; UPPER_SNAKE only for exported/env vars.
- Defaults and required vars: `"${PORT:-8080}"`, `"${API_URL:?API_URL is required}"`.
- Functions with a `main "$@"` entry point at the bottom.
- Temp files: `tmp="$(mktemp)"`; cleanup with `trap 'rm -f "$tmp"' EXIT`.
- Errors to stderr: `echo "error: ..." >&2; exit 1`. Meaningful exit codes.
- Iterate lines safely: `while IFS= read -r line; do ...; done < file`.
- Find + act: `find . -name '*.log' -print0 | xargs -0 rm --` or `find ... -exec ... {} +`.
- `command -v tool >/dev/null || { echo "tool required" >&2; exit 1; }` instead of `which`.
- Use `--` to end options before user-supplied paths (`rm -- "$file"`).
- `printf '%s\n' "$x"` over `echo` for arbitrary data.
- Arrays for argument lists: `args=(--verbose --out "$dir"); cmd "${args[@]}"`.
- `jq` for JSON; never parse JSON with grep/sed.

## Pitfalls

- Unquoted vars → word splitting and globbing (`rm $file` with spaces or `*`).
- `cd dir` without `|| exit` (or relying on `set -e`) then destructive commands in the wrong place.
- `rm -rf "$DIR/"` with empty `$DIR` → `rm -rf /`. Use `${DIR:?}`.
- Parsing `ls` output. Use globs or `find`.
- Pipelines hide failures without `pipefail`; `local var=$(cmd)` masks `cmd`'s exit code — declare and assign separately.
- `cmd | while read` runs in a subshell; variables set inside are lost.
- `eval` and building commands from strings with untrusted input → injection.
- Secrets in command-line args are visible in `ps`; pass via env or stdin. Don't `set -x` around secrets.
- `echo -e`/`sed -i` portability differs across GNU/BSD (macOS); test on target platforms or use POSIX forms.
- CRLF line endings break scripts (`$'\r': command not found`) — enforce LF via `.gitattributes`.
- Hard-coded absolute paths; resolve relative to the script: `SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"`.

## Tooling

- Run `shellcheck` on every script; `shfmt` for formatting.
- Test with `bats` for scripts that matter.

## Sources

- ShellCheck wiki: https://www.shellcheck.net/wiki/
- Google Shell Style Guide: https://google.github.io/styleguide/shellguide.html
- Greg's Wiki, Bash Pitfalls: https://mywiki.wooledge.org/BashPitfalls
- BashFAQ/105 (why `set -e` is subtle): https://mywiki.wooledge.org/BashFAQ/105
