#!/usr/bin/env bash
# === harness file context (PreToolUse Edit|Write|MultiEdit) ===
# Path-scoped rules load when Claude *reads* a matching file, but new files are
# written without a read, and a checklist delivered alongside a write arrives
# after the content is already composed. So, once per agent context and topic:
#   * ui / seo (topics with mandatory skills): the first write is DENIED once
#     with the checklist and "load the skills, then retry" — the retry is allowed.
#     ui names ui-ux, typography and color-science together in that one deny.
#     Set checklists=inform in .claude/harness.config to only inform instead.
#   * security / store / infra: the checklist is added as context (never blocks).
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

# hh_gate <topic> <skill>... — first write for this topic in this agent context:
# mark the gate and queue the skills for one deny. Skills this project's
# profiles don't install are dropped (the deny would point at a missing file);
# if none is installed, there is no gate. If the marker cannot be written,
# fall back to inform so the gate can never deny forever.
enforce=(); gate_text=""
hh_gate() {
  local topic="$1" s have=()
  shift
  for s in "$@"; do [[ -f "$HH_ROOT/.claude/skills/$s/SKILL.md" ]] && have+=("$s"); done
  [[ ${#have[@]} -gt 0 ]] || return 0
  hh_topic_marker "gate-$topic"
  [[ -e "$HH_V" ]] && return 0
  : > "$HH_V" 2>/dev/null || return 0
  enforce+=("${have[@]}")
  hh_snippet_text "$topic"; gate_text+="$HH_V"$'\n'
}

hh_config checklists; mode="$HH_V"
case "$p" in
  *.tsx|*.jsx|*.vue|*.svelte|*.astro|*.html|*.htm|*.css|*.scss|*.sass|*.less|*.swift|*.xib|*.storyboard|\
  */res/layout/*|*/res/values/*|*Screen.kt|*View.kt|*Component.kt|*Activity.kt|*Fragment.kt|*/tailwind.config.*|\
  */components/*|*/ui/*|*/screens/*|*/views/*|*/theme/*|*/styles/*)
    [[ "$mode" != "inform" ]] && hh_gate ui ui-ux typography color-science
    hh_add_snippet ui ;;
esac
# Server-side code (API routes, controllers, middleware) is never a public
# page, even when it lives in a routes/ folder.
server=0
case "$p" in */api/*|*/server/*|*/backend/*|*/controllers/*|*/middlewares/*) server=1 ;; esac
[[ $server -eq 0 ]] && case "$p" in
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
  */app.json|*/app.config.*|*/eas.json|*/store-assets/*|*/fastlane/*|*.xcassets/*|*/res/mipmap-*|*LISTING.md|*listing-guardrails.txt)
    hh_add_snippet store ;;
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
  what="a mandatory skill"; [[ ${#enforce[@]} -gt 1 ]] && what="mandatory skills"
  hh_deny "Harness: ${p##*/} falls under ${what}. Before writing it, load ${skills} (Read tool or Skill tool) and apply this checklist, then retry the same write (it will be allowed):
$gate_text"
fi
[[ -z "$HH_OUT" ]] && exit 0
hh_emit_context PreToolUse "Harness: this file falls under a mandatory checklist:
$HH_OUT"
exit 0
