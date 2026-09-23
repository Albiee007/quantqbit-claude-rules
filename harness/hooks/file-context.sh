#!/usr/bin/env bash
# === harness file context (PreToolUse Edit|Write|MultiEdit) ===
# Path-scoped rules load when Claude *reads* a matching file; brand-new files
# are written without a read. This hook closes that gap by injecting the
# matching mandatory checklist (once per session) before the first write.
set -uo pipefail
# shellcheck source=_lib.sh
_hd="${BASH_SOURCE[0]%/*}"; [[ "$_hd" == "${BASH_SOURCE[0]}" ]] && _hd=.
source "$_hd/_lib.sh"
hh_read_payload

hh_get file_path "$HH_TI"; p="$HH_V"
[[ -z "$p" ]] && exit 0
p="${p//\\//}"
shopt -s nocasematch

case "$p" in
  *.tsx|*.jsx|*.vue|*.svelte|*.astro|*.html|*.htm|*.css|*.scss|*.sass|*.less|*.swift|*.xib|*.storyboard|\
  */res/layout/*|*/res/values/*|*Screen.kt|*View.kt|*Component.kt|*Activity.kt|*Fragment.kt|*/tailwind.config.*|\
  */components/*|*/ui/*|*/screens/*|*/views/*|*/theme/*|*/styles/*)
    hh_add_snippet ui ;;
esac
case "$p" in
  */pages/*|*/app/*/page.*|*/app/page.*|*/app/*layout.*|*/routes/*|*.astro|*.mdx|*/robots.txt|*/robots.ts|*sitemap*|\
  */index.html|*/head.*|*seo*|*metadata*|*/site.webmanifest|*/manifest.json)
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

[[ -n "$HH_OUT" ]] && hh_emit_context PreToolUse "Harness: this file falls under a mandatory checklist:
$HH_OUT"
exit 0
