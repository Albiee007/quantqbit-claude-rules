#!/usr/bin/env bash
# === harness sync bootstrap (vendored into each project) ===
# Finds the harness source and runs its transactional sync against this
# project. Developers need only git + bash; the plugin is optional.
#
# Source lookup order:
#   1. --source DIR                       (explicit checkout)
#   2. $HARNESS_HOME                      (e.g. a local clone)
#   3. $CLAUDE_PLUGIN_ROOT                (when run from the Claude Code plugin)
#   4. ~/.local/share/quantqbit-claude-rules
#   5. git clone of the "source" URL recorded in .claude/harness/lock
#      (--ref TAG pins a release, e.g. --ref v1.2.0; default: default branch)
#
# Usage: bash .claude/harness/bin/harness-sync.sh [--source DIR] [--ref TAG] [sync options…]
#        (sync options: --dry-run --diff --keep --theirs --commit --profiles … ; see sync.sh --help)
set -euo pipefail

BIN="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$BIN/../../.." && pwd)"
LOCK="$ROOT/.claude/harness/lock"

src=""; ref=""; pass=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --source) src="${2:?}"; shift 2 ;;
    --ref) ref="${2:?}"; shift 2 ;;
    *) pass+=("$1"); shift ;;
  esac
done

is_src() { [[ -n "$1" && -f "$1/scaffold/sync.sh" && -f "$1/harness/manifest.tsv" ]]; }

if [[ -z "$src" ]]; then
  for c in "${HARNESS_HOME:-}" "${CLAUDE_PLUGIN_ROOT:-}" "$HOME/.local/share/quantqbit-claude-rules"; do
    if is_src "$c" && [[ -z "$ref" ]]; then src="$c"; break; fi
  done
fi

tmp=""
if [[ -z "$src" ]]; then
  url="$(tr -d '\r' < "$LOCK" 2>/dev/null | awk -F'\t' '$1 == "source" { print $2; exit }' || true)"
  url="${HARNESS_SOURCE_URL:-$url}"
  [[ -z "$url" || "$url" == "local" ]] && url="https://github.com/Albiee007/quantqbit-claude-rules"
  tmp="$(mktemp -d "${TMPDIR:-/tmp}/harness-src.XXXXXX")"
  trap 'rm -rf "$tmp"' EXIT
  echo "[INFO] cloning harness source $url ${ref:+@ $ref}" >&2
  git clone -q --depth 1 ${ref:+--branch "$ref"} "$url" "$tmp/src"
  src="$tmp/src"
fi
is_src "$src" || { echo "[FAIL] not a harness source: $src" >&2; exit 2; }

bash "$src/scaffold/sync.sh" --target "$ROOT" "${pass[@]+"${pass[@]}"}"
