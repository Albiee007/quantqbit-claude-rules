#!/usr/bin/env bash
# === harness sync bootstrap (vendored into each project) ===
# Finds a harness source and runs its transactional sync against this project.
# Developers need only git + bash; the Claude Code plugin is optional.
#
# Source selection:
#   --source DIR   use this checkout
#   --ref TAG      clone that release tag of the upstream repo (e.g. --ref v1.0.1)
#   --remote       clone the upstream default branch (latest, unreleased)
#   (default)      the NEWEST local source among: $HARNESS_HOME, $CLAUDE_PLUGIN_ROOT,
#                  the installed plugin (~/.claude/plugins/cache/quantqbit/...), and
#                  ~/.local/share/quantqbit-claude-rules. With none, clone upstream.
#   Upstream URL:  $HARNESS_SOURCE_URL, else the https "source" in the lock, else
#                  https://github.com/Albiee007/quantqbit-claude-rules (private repo:
#                  needs git credentials with read access).
#
# Usage: bash .claude/harness/bin/harness-sync.sh [--source DIR|--ref TAG|--remote] [sync options…]
#        sync options: --dry-run --diff --keep --theirs --commit --profiles … (see --help of sync.sh)
set -euo pipefail
unset MSYS_NO_PATHCONV MSYS2_ARG_CONV_EXCL

BIN="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$BIN/../../.." && pwd)"
LOCK="$ROOT/.claude/harness/lock"
# shellcheck source=harness-lib.sh
source "$BIN/harness-lib.sh"

src=""; ref=""; remote=0; pass=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --source) src="${2:?--source needs a dir}"; shift 2 ;;
    --source=*) src="${1#*=}"; shift ;;
    --ref) ref="${2:?--ref needs a tag}"; shift 2 ;;
    --ref=*) ref="${1#*=}"; shift ;;
    --remote) remote=1; shift ;;
    -h|--help) awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) pass+=("$1"); shift ;;
  esac
done
[[ -n "$src" && ( -n "$ref" || $remote -eq 1 ) ]] && hc_warn "--source given: ignoring --ref/--remote"

is_src() { [[ -n "$1" && -f "$1/scaffold/sync.sh" && -f "$1/harness/manifest.tsv" ]]; }

if [[ -z "$src" && -z "$ref" && $remote -eq 0 ]]; then
  best="$(hc_find_sources | head -n 1 || true)"
  if [[ -n "$best" ]]; then
    src="${best#*$'\t'}"
    hc_info "using local harness source v${best%%$'\t'*}: $src"
    [[ -d "$src/.git" ]] && hc_info "(a git clone: run 'git -C \"$src\" pull' first if you want the latest)"
  fi
fi

tmp=""
if [[ -z "$src" ]]; then
  url=""
  [[ -f "$LOCK" ]] && url="$(tr -d '\r' < "$LOCK" | awk -F'\t' '$1 == "source" { print $2; exit }')"
  # Only trust plain https URLs from a lock (older locks may hold a local path,
  # 'local', an SSH form or a tokenised URL).
  [[ "$url" =~ ^https://[^@/]+/ ]] || url=""
  url="${HARNESS_SOURCE_URL:-${url:-$HARNESS_UPSTREAM_URL}}"
  tmp="$(mktemp -d "${TMPDIR:-/tmp}/harness-src.XXXXXX")"
  trap 'rm -rf "$tmp"' EXIT
  hc_info "cloning harness source $url${ref:+ @ $ref}"
  if ! git -c advice.detachedHead=false clone -q --depth 1 ${ref:+--branch "$ref"} "$url" "$tmp/src"; then
    hc_fail "could not clone $url${ref:+ at '$ref'} — check your access to the repo and that the tag exists (git ls-remote --tags $url)"
    exit 2
  fi
  src="$tmp/src"
fi
is_src "$src" || { hc_fail "not a harness source: $src"; exit 2; }

bash "$src/scaffold/sync.sh" --target "$ROOT" "${pass[@]+"${pass[@]}"}"
