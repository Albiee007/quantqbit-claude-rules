#!/usr/bin/env bash
# === harness post-edit lint (PostToolUse Edit|Write|MultiEdit) ===
# Runs a fast linter for the edited file and feeds findings back to Claude.
# Warn-only: never blocks, always exits 0. Missing linters are skipped quietly.
set -uo pipefail
# shellcheck source=_lib.sh
_hd="${BASH_SOURCE[0]%/*}"; [[ "$_hd" == "${BASH_SOURCE[0]}" ]] && _hd=.
source "$_hd/_lib.sh"
hh_read_payload

hh_get file_path "$HH_TI"; p="$HH_V"
p="${p//\\//}"
[[ -z "$p" || ! -f "$p" ]] && exit 0

have() { command -v "$1" >/dev/null 2>&1; }
out=""
run() { # label, command...
  local label="$1" res; shift
  if ! res="$("$@" 2>&1)"; then
    out+="[$label] ${res:0:1500}"$'\n'
  fi
}

case "$p" in
  *.sh|*.bash)
    run "bash -n" bash -n "$p"
    have shellcheck && run shellcheck shellcheck -f gcc "$p" ;;
  */ansible/*.yml|*/ansible/*.yaml|*/playbooks/*.yml|*/roles/*.yml)
    have ansible-lint && run ansible-lint ansible-lint --offline -p "$p" ;;
  *docker-compose*.yml|*docker-compose*.yaml|*/compose.yml|*/compose.yaml)
    have docker && run "compose config" docker compose -f "$p" config --quiet
    have yamllint && run yamllint yamllint -s "$p" ;;
  *.yml|*.yaml)
    have yamllint && run yamllint yamllint -s "$p" ;;
  *.tf)
    have terraform && run "terraform fmt" terraform fmt -check -diff "$p" ;;
esac

[[ -n "$out" ]] && hh_emit_context PostToolUse "Harness lint findings for ${p##*/} (fix them, or explain why they are intentional):
$out"
exit 0
