#!/usr/bin/env bash
# === harness file context (PreToolUse Edit|Write|MultiEdit) ===
# Path-scoped rules load when Claude *reads* a matching file, but new files are
# written without a read, and a checklist delivered alongside a write arrives
# after the content is already composed. So, once per agent context and topic:
#   * ui / seo (topics with a mandatory skill): the first write is DENIED with
#     the checklist and "load the skill, then retry" — the retry is allowed.
#     Set checklists=inform in .claude/harness.config to only inform instead.
#   * security / infra: the checklist is added as context (never blocks).
# A topic whose checklist was already shown in this agent context (e.g. by the
# prompt router) is not repeated.
set -uo pipefail
# shellcheck source=_lib.sh
_hd="${BASH_SOURCE[0]%/*}"; [[ "$_hd" == "${BASH_SOURCE[0]}" ]] && _hd=.
source "$_hd/_lib.sh"
hh_read_payload

hh_get file_path "$HH_TI"; p="$HH_V"
[[ -z "$p" ]] && exit 0
p="${p//\\//}"
shopt -s nocasematch

enforce=()   # topics whose first write is denied
case "$p" in
  *.tsx|*.jsx|*.vue|*.svelte|*.astro|*.html|*.htm|*.css|*.scss|*.sass|*.less|*.swift|*.xib|*.storyboard|\
  */res/layout/*|*/res/values/*|*Screen.kt|*View.kt|*Component.kt|*Activity.kt|*Fragment.kt|*/tailwind.config.*|\
  */components/*|*/ui/*|*/screens/*|*/views/*|*/theme/*|*/styles/*)
    hh_add_snippet ui && enforce+=("ui-ux") ;;
esac
case "$p" in
  */pages/*|*/app/*/page.*|*/app/page.*|*/app/*layout.*|*/routes/*|*.astro|*.mdx|*/robots.txt|*/robots.ts|*sitemap*|\
  */index.html|*/head.*|*seo*|*metadata*|*/site.webmanifest|*/manifest.json)
    hh_add_snippet seo && enforce+=("seo") ;;
esac
case "$p" in
  */auth/*|*auth*.*|*/api/*|*controller*|*/middleware*|*/migrations/*|*.sql|*/routes/*|*route*.*)
    hh_add_snippet security ;;
esac
case "$p" in
  *.sh|*.bash|*.ps1|*.psm1|*.tf|*docker-compose*|*/compose*.y*ml|*Dockerfile*|*/ansible/*|*/playbooks/*|*/roles/*|*/.github/workflows/*)
    hh_add_snippet infra ;;
esac

[[ -z "$HH_OUT" ]] && exit 0
hh_config checklists
if [[ ${#enforce[@]} -gt 0 && "$HH_V" != "inform" ]]; then
  skills=""
  for s in "${enforce[@]}"; do
    skills+="${skills:+, }.claude/skills/$s/SKILL.md"
  done
  hh_deny "Harness: ${p##*/} falls under a mandatory skill. Before writing it, read ${skills} (Read tool) and apply this checklist, then retry the same write (it will be allowed):
$HH_OUT"
fi
hh_emit_context PreToolUse "Harness: this file falls under a mandatory checklist:
$HH_OUT"
exit 0
