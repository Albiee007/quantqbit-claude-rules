#!/usr/bin/env bash
# === harness session start (SessionStart) ===
# Injects a short harness summary (version, profiles, agent roster) and cheap
# health warnings. Heavy checks (hashing) live in harness-doctor, not here.
set -uo pipefail
# shellcheck source=_lib.sh
_hd="${BASH_SOURCE[0]%/*}"; [[ "$_hd" == "${BASH_SOURCE[0]}" ]] && _hd=.
source "$_hd/_lib.sh"
hh_read_payload

lock="$HH_ROOT/.claude/harness/lock"
cfg="$HH_ROOT/.claude/harness.config"

# New context (startup / clear / compact): forget which checklists were shown.
hh_marker_prefix
rm -f "$HH_V"* 2>/dev/null || true

ver="?"; profiles="all"; kept=0; conflict=0
if [[ -f "$lock" ]]; then
  while IFS=$'\t' read -r a b _ _ e; do
    case "$a" in
      harness_version) ver="$b" ;;
      profiles) profiles="$b" ;;
      '<<<<<<<'*|'>>>>>>>'*|'=======') conflict=1 ;;
    esac
    [[ "${e:-}" == "kept-local" ]] && kept=$((kept + 1))
  done < "$lock"
fi
if [[ -f "$cfg" ]]; then
  while IFS='=' read -r k v; do
    [[ "$k" == "profiles" && -n "$v" ]] && profiles="${v%$'\r'}"
  done < "$cfg"
fi

msg="QuantQbit agent harness v$ver (profiles: $profiles).
Agents (all Opus): explorer → implementor / infra-implementor → verifier → reviewer (lens: code|patterns|ux|seo|security).
Mandatory skills: ui-ux (UI work), seo (public web pages), design-patterns (before any abstraction), coding-standards (always).
Project overrides: .claude/rules/project/ and CLAUDE.md. Do not edit harness:managed files."
[[ -f "$lock" ]] || msg+="
WARNING: .claude/harness/lock is missing, so harness files are untracked. Run harness sync."
[[ $conflict -eq 1 ]] && msg+="
WARNING: .claude/harness/lock has merge-conflict markers. Take either side, then re-run harness sync."
[[ $kept -gt 0 ]] && msg+="
NOTE: $kept harness file(s) are kept-local (diverged from upstream). Run: bash .claude/harness/bin/harness-doctor.sh"

hh_emit_context SessionStart "$msg"
exit 0
