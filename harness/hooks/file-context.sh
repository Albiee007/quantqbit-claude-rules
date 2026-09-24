#!/usr/bin/env bash
# === harness file context (PreToolUse Edit|Write|MultiEdit) ===
# Path-scoped rules load when Claude *reads* a matching file, but new files are
# written without a read, and a checklist delivered alongside a write arrives
# after the content is already composed. So, once per agent context and topic:
#   * ui / seo (topics with a mandatory skill): the first write is DENIED with
#     the checklist and "load the skill, then retry" — the retry is allowed.
#     Set checklists=inform in .claude/harness.config to only inform instead.
#   * security / infra: the checklist is added as context (never blocks).
# The gate has its own marker per agent context and topic, so a checklist the
# prompt router already showed does not skip it. Checklist text itself is not repeated.
set -uo pipefail
# shellcheck source=_lib.sh
_hd="${BASH_SOURCE[0]%/*}"; [[ "$_hd" == "${BASH_SOURCE[0]}" ]] && _hd=.
source "$_hd/_lib.sh"
hh_read_payload

hh_get file_path "$HH_TI"; p="$HH_V"
[[ -z "$p" ]] && exit 0
p="${p//\\//}"
shopt -s nocasematch

# hh_gate <topic> <skill> — first write for this topic in this agent context:
# mark the gate and queue the skill for the deny. If the marker cannot be
# written, fall back to inform so the gate can never deny forever.
enforce=(); gate_text=""
hh_gate() {
  hh_topic_marker "gate-$1"
  [[ -e "$HH_V" ]] && return 0
  : > "$HH_V" 2>/dev/null || return 0
  enforce+=("$2")
  hh_snippet_text "$1"; gate_text+="$HH_V"$'\n'
}

hh_config checklists; mode="$HH_V"
case "$p" in
  *.tsx|*.jsx|*.vue|*.svelte|*.astro|*.html|*.htm|*.css|*.scss|*.sass|*.less|*.swift|*.xib|*.storyboard|\
  */res/layout/*|*/res/values/*|*Screen.kt|*View.kt|*Component.kt|*Activity.kt|*Fragment.kt|*/tailwind.config.*|\
  */components/*|*/ui/*|*/screens/*|*/views/*|*/theme/*|*/styles/*)
    [[ "$mode" != "inform" ]] && hh_gate ui ui-ux
    hh_add_snippet ui ;;
esac
case "$p" in
  */pages/*|*/app/*/page.*|*/app/page.*|*/app/*layout.*|*/routes/*|*.astro|*.mdx|*/robots.txt|*/robots.ts|*sitemap*|\
  */index.html|*/head.*|*seo*|*metadata*|*/site.webmanifest|*/manifest.json)
    [[ "$mode" != "inform" ]] && hh_gate seo seo
    hh_add_snippet seo ;;
esac
case "$p" in
  */auth/*|*auth*.*|*/api/*|*controller*|*/middleware*|*/migrations/*|*.sql|*/routes/*|*route*.*)
    hh_add_snippet security ;;
esac
case "$p" in
  *.sh|*.bash|*.ps1|*.psm1|*.tf|*docker-compose*|*/compose*.y*ml|*Dockerfile*|*/ansible/*|*/playbooks/*|*/roles/*|*/.github/workflows/*)
    hh_add_snippet infra ;;
esac

if [[ ${#enforce[@]} -gt 0 ]]; then
  skills=""
  for s in "${enforce[@]}"; do
    skills+="${skills:+, }.claude/skills/$s/SKILL.md"
  done
  hh_deny "Harness: ${p##*/} falls under a mandatory skill. Before writing it, load ${skills} (Read tool or Skill tool) and apply this checklist, then retry the same write (it will be allowed):
$gate_text"
fi
[[ -z "$HH_OUT" ]] && exit 0
hh_emit_context PreToolUse "Harness: this file falls under a mandatory checklist:
$HH_OUT"
exit 0
