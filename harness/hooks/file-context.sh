#!/usr/bin/env bash
# === harness file context (PreToolUse Edit|Write|MultiEdit) ===
# Path-scoped rules load when Claude *reads* a matching file, but new files are
# written without a read, and a checklist delivered alongside a write arrives
# after the content is already composed. So, once per agent context and topic:
#   * ui / seo (topics with mandatory skills): the first write is DENIED once
#     with the checklist and "load the skills, then retry" — the retry is allowed.
#     ui names ui-ux, typography and color-science together in that one deny.
#     Set checklists=inform in .agents/harness.config to only inform instead.
#   * media (brand/ direction, tokens, concepts, canvases, logos; mockup-kit config;
#     story-art plans): gated like ui, naming creative-direction with typography,
#     color-science and ui-ux. The direction and brief can be drafted before any
#     approval: the gate only asks for the skills. Approvals are enforced by the
#     production commands, not here.
#   * motion (brand/motion/<id>/motion.json): gated naming motion-ui with creative-direction and
#     ui-ux. Gate 3 (the owner approving the spec) is enforced by motion.py verify, not here.
#   * brand/approvals.json is never edited by hand (direction.py approve writes it), nor are the
#     run manifests in brand/runs/ (the production commands write them).
#   * security / store / infra: the checklist is added as context (never blocks).
# The gate has its own marker per agent context and topic, so a checklist the
# prompt router already showed does not skip it. Checklist text itself is not repeated.
set -uo pipefail
# shellcheck source=_lib.sh
_hd="${BASH_SOURCE[0]%/*}"; [[ "$_hd" == "${BASH_SOURCE[0]}" ]] && _hd=.
source "$_hd/_lib.sh"
hh_read_payload "$@"
# Only writes (an edit, a patch, a move) are checked; VS Code runs Claude hooks
# without their matcher, so the hook filters on the operation itself.
[[ "$HH_OP" == write || "$HH_OP" == rename ]] || exit 0
[[ ${#HH_PATHS[@]} -gt 0 ]] || exit 0
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
  for s in "$@"; do [[ -f "$HH_SKILLS/$s/SKILL.md" ]] && have+=("$s"); done
  [[ ${#have[@]} -gt 0 ]] || return 0
  hh_topic_marker "gate-$topic"
  [[ -e "$HH_V" ]] && return 0
  : > "$HH_V" 2>/dev/null || return 0
  enforce+=("${have[@]}")
  hh_snippet_text "$topic"; gate_text+="$HH_V"$'\n'
}

# protect <message> — refuse a write to a file only the production commands
# write. Where the event can no longer stop it (an after-edit hook), report the
# violation instead so the agent reverts it.
violations=""
protect() {
  [[ "$HH_CAN_BLOCK" == 1 ]] && hh_deny "$1"
  violations+="$1 This write already happened: revert it now."$'\n'
}

hh_config checklists; mode="$HH_V"
# A gate can only deny before the write; afterwards it can only inform.
[[ "$HH_CAN_BLOCK" == 1 ]] || mode="inform"

# Every path of the operation: a protected file anywhere in a multi-file patch,
# or as the target of a move, refuses the whole operation.
for p in "${HH_PATHS[@]}"; do
p="${p//\\//}"
# Patch paths are relative to the project; anchor them so the */dir/ patterns match.
[[ "$p" == /* || "$p" == [A-Za-z]:/* ]] || p="/$p"
case "$p" in
  */brand/approvals.json)
    protect "Harness: brand/approvals.json records the owner's decisions and is written only by direction.py approve, run by the main session after the owner decides (skill creative-direction). Don't edit it by hand." ;;
  */brand/runs/*.json)
    protect "Harness: brand/runs/ holds the immutable run manifests the production commands write (the audit record, including video and motion review items). Don't edit them; render or verify again instead." ;;
esac
case "$p" in
  */brand/direction.json|*/brand/BRIEF.md|*/brand/canvas.json|*/brand/exports.json|*/brand/tokens.json|*/brand/concepts/*|\
  */brand/*.svg|*/frames.json|*/custom-objects.js|*/out/story-art/*/plan.md|*/brand/video/*/video.json)
    [[ "$mode" != "inform" ]] && hh_gate media creative-direction typography color-science ui-ux
    hh_add_snippet media ;;
esac
case "$p" in
  */brand/motion/*/motion.json)
    [[ "$mode" != "inform" ]] && hh_gate motion motion-ui creative-direction ui-ux
    hh_add_snippet motion ;;
esac
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
done

if [[ ${#enforce[@]} -gt 0 ]]; then
  skills=""; n=0
  for s in "${enforce[@]}"; do
    [[ ", $skills," == *", $HH_SKILLS_REL/$s/SKILL.md,"* ]] && continue
    skills+="${skills:+, }$HH_SKILLS_REL/$s/SKILL.md"; n=$((n + 1))
  done
  what="a mandatory skill"; [[ $n -gt 1 ]] && what="mandatory skills"
  name="${HH_PATHS[0]##*/}"; [[ ${#HH_PATHS[@]} -gt 1 ]] && name="this change"
  hh_deny "Harness: ${name} falls under ${what}. Before writing it, load ${skills} (Read tool or Skill tool) and apply this checklist, then retry the same write (it will be allowed):
$gate_text"
fi
out="$violations$HH_OUT"
[[ -z "$out" ]] && exit 0
[[ -n "$violations" ]] && hh_emit_context "${HH_EVENT:-PostToolUse}" "$out"
[[ -z "$violations" ]] && hh_emit_context "${HH_EVENT:-PreToolUse}" "Harness: this file falls under a mandatory checklist:
$HH_OUT"
exit 0
