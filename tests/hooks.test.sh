#!/usr/bin/env bash
# === harness hook tests ===
# Feeds hook JSON payloads to each hook and asserts on the output.
# Usage: bash tests/hooks.test.sh
set -uo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HK="$SRC/harness/hooks"
P="$(mktemp -d "${TMPDIR:-/tmp}/harness-hooks.XXXXXX")"
export TMPDIR="$P/tmp"; mkdir -p "$TMPDIR"
trap 'rm -rf "$P"' EXIT
mkdir -p "$P/.agents/harness/snippets"
cp "$SRC"/harness/snippets/*.md "$P/.agents/harness/snippets/"
for s in ui-ux typography color-science seo creative-direction motion-ui; do mkdir -p "$P/.claude/skills/$s"; : > "$P/.claude/skills/$s/SKILL.md"; done
export CLAUDE_PROJECT_DIR="$P"
pass=0; fail=0

run() { printf '%s' "$2" | bash "$HK/$1" ${HOOK_ARGS:-} 2>/dev/null; }
expect() { # desc, hook, payload, grep-pattern ("" = expect empty output)
  local out; out="$(run "$2" "$3")"
  if [[ -z "$4" ]]; then
    [[ -z "$out" ]] && { pass=$((pass+1)); echo "  [OK] $1"; } || { fail=$((fail+1)); echo "  [FAIL] $1 — got: ${out:0:120}"; }
  else
    grep -q -- "$4" <<<"$out" && { pass=$((pass+1)); echo "  [OK] $1"; } || { fail=$((fail+1)); echo "  [FAIL] $1 — got: ${out:0:120}"; }
  fi
}

echo "guard"
expect "deny sonnet sub-agent"   guard.sh '{"tool_name":"Agent","tool_input":{"subagent_type":"x","model":"sonnet"}}' '"permissionDecision":"deny"'
expect "deny haiku via Task"     guard.sh '{"tool_name":"Task","tool_input":{"model":"claude-haiku-4-5"}}' 'deny'
expect "allow opus"              guard.sh '{"tool_name":"Agent","tool_input":{"model":"opus"}}' ''
expect "allow no model"          guard.sh '{"tool_name":"Agent","tool_input":{"subagent_type":"explorer"}}' ''
expect "top-level model ignored" guard.sh '{"model":"sonnet","tool_name":"Agent","tool_input":{"model":"opus"}}' ''
expect "deny Read .env"          guard.sh '{"tool_name":"Read","tool_input":{"file_path":"/p/.env"}}' 'deny'
expect "deny Edit .env.production (win path)" guard.sh '{"tool_name":"Edit","tool_input":{"file_path":"C:\p\.env.production"}}' 'deny'
expect "allow .env.example"      guard.sh '{"tool_name":"Write","tool_input":{"file_path":"/p/.env.example"}}' ''
expect "allow .envrc-like names" guard.sh '{"tool_name":"Read","tool_input":{"file_path":"/p/src/env.ts"}}' ''
expect "deny cat .env"           guard.sh '{"tool_name":"Bash","tool_input":{"command":"cat .env"}}' 'deny'
expect "deny git add .env.local" guard.sh '{"tool_name":"Bash","tool_input":{"command":"git add app/.env.local"}}' 'deny'
expect "allow cp .env.example x" guard.sh '{"tool_name":"Bash","tool_input":{"command":"diff .env.example .env.template"}}' ''
expect "allow process.env"       guard.sh '{"tool_name":"Bash","tool_input":{"command":"node -e \"console.log(process.env.HOME)\""}}' ''
expect "allow unrelated tool"    guard.sh '{"tool_name":"Glob","tool_input":{"pattern":"**/.env"}}' ''

echo "guard ↔ core: one .env exception list"
core_names="$(grep -m1 'may be edited' "$SRC/harness/core/00-core.md" | grep -oE '`\.env\.[a-z]+`' | tr -d '`' | sort | xargs)"
guard_names="$(grep -m1 '^ENV_OK_RE=' "$HK/guard.sh" | grep -oE '\([a-z|]+\)' | head -n1 | tr -d '()' | tr '|' ' ' | xargs -n1 | sed 's/^/.env./' | sort | xargs)"
if [[ -n "$core_names" && "$core_names" == "$guard_names" ]]; then pass=$((pass+1)); echo "  [OK] core and guard list the same names ($core_names)"
else fail=$((fail+1)); echo "  [FAIL] core lists '$core_names', guard allows '$guard_names'"; fi
for n in $core_names .env.local.example; do
  expect "allow $n" guard.sh "{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"/p/$n\"}}" ''
done
for n in .env.local .env.backup .env.prod .env.example.bak; do
  expect "deny $n" guard.sh "{\"tool_name\":\"Read\",\"tool_input\":{\"file_path\":\"/p/$n\"}}" 'deny'
done

echo "guard (gaps found in live verification)"
expect "deny glob cat .env*"          guard.sh '{"tool_name":"Bash","tool_input":{"command":"cat .env*"}}' 'deny'
expect "deny case variant .ENV.Staging" guard.sh '{"tool_name":"Bash","tool_input":{"command":"cat .ENV.Staging"}}' 'deny'
expect "deny PowerShell Get-Content"  guard.sh '{"tool_name":"PowerShell","tool_input":{"command":"Get-Content .env.staging"}}' 'deny'
expect "deny Grep glob .env*"         guard.sh '{"tool_name":"Grep","tool_input":{"pattern":"KEY","glob":".env*"}}' 'deny'
expect "deny comma list"              guard.sh '{"tool_name":"Bash","tool_input":{"command":"cp a,.env.test b"}}' 'deny'
expect "deny chained after ls"        guard.sh '{"tool_name":"Bash","tool_input":{"command":"ls .env && cat .env"}}' 'deny'
expect "allow --exclude=.env*"        guard.sh '{"tool_name":"Bash","tool_input":{"command":"grep -r --exclude=.env* TODO src"}}' ''
expect "allow rg -g !.env*"           guard.sh '{"tool_name":"Bash","tool_input":{"command":"rg -g \"!.env*\" TODO"}}' ''
expect "allow git check-ignore .env"  guard.sh '{"tool_name":"Bash","tool_input":{"command":"git check-ignore .env"}}' ''
expect "allow Grep for process.env"   guard.sh '{"tool_name":"Grep","tool_input":{"pattern":"process.env","path":"src"}}' ''
expect "deny newline after ls"        guard.sh '{"tool_name":"Bash","tool_input":{"command":"ls -la\ncat .env"}}' 'deny'
expect "deny newline after git status" guard.sh '{"tool_name":"Bash","tool_input":{"command":"git status\ncp .env /tmp/x"}}' 'deny'
expect "deny PS newline"              guard.sh '{"tool_name":"PowerShell","tool_input":{"command":"Get-ChildItem\nGet-Content .env"}}' 'deny'
expect "deny PS subexpression"        guard.sh '{"tool_name":"PowerShell","tool_input":{"command":"Get-Item (Get-Content .env)"}}' 'deny'
expect "deny meta ; cat"              guard.sh '{"tool_name":"Bash","tool_input":{"command":"git check-ignore .env ; cat .env"}}' 'deny'
expect "deny brace expansion"         guard.sh '{"tool_name":"Bash","tool_input":{"command":"cat {.env,x}"}}' 'deny'
expect "deny NTFS stream path"        guard.sh '{"tool_name":"Read","tool_input":{"file_path":"C:\\p\\.env:$DATA"}}' 'deny'
expect "deny trailing dot path"       guard.sh '{"tool_name":"Read","tool_input":{"file_path":"/p/.env."}}' 'deny'
expect "allow exclude ; check-ignore" guard.sh '{"tool_name":"Bash","tool_input":{"command":"grep -r --exclude=.env* TODO src ; git check-ignore .env.staging"}}' ''
expect "allow ls .env"                guard.sh '{"tool_name":"Bash","tool_input":{"command":"ls .env"}}' ''
expect "allow Test-Path .env"         guard.sh '{"tool_name":"PowerShell","tool_input":{"command":"Test-Path .env"}}' ''

echo "prompt-router"
expect "UI prompt → ui checklist"      prompt-router.sh '{"session_id":"a1","prompt":"Make the login screen responsive"}' 'ui-ux'
expect "same topic not repeated"       prompt-router.sh '{"session_id":"a1","prompt":"tweak the button color"}' ''
expect "font/palette prompt → all three UI skills" prompt-router.sh '{"session_id":"a20","prompt":"change the typeface and palette"}' 'ui-ux, typography, color-science'
expect "oklch prompt → ui checklist"   prompt-router.sh '{"session_id":"a21","prompt":"convert the brand ramp to oklch"}' 'typography, color-science'
expect "UI checklist deduped per session" prompt-router.sh '{"session_id":"a20","prompt":"tweak the font sizes"}' ''
expect "SEO prompt → seo checklist"    prompt-router.sh '{"session_id":"a2","prompt":"add meta description and sitemap"}' 'Load skill: seo'
expect "pattern prompt → gate"         prompt-router.sh '{"session_id":"a3","prompt":"Should we add a factory here?"}' 'design-patterns'
expect "design pattern ≠ UI"           prompt-router.sh '{"session_id":"a4","prompt":"which design pattern fits?"}' 'design-patterns'
out="$(run prompt-router.sh '{"session_id":"a5","prompt":"which design pattern fits?"}')"
grep -q 'ui-ux' <<<"$out" && { fail=$((fail+1)); echo "  [FAIL] design pattern prompt injected UI"; } || { pass=$((pass+1)); echo "  [OK] design pattern prompt has no UI checklist"; }
expect "no security for plain 'session'" prompt-router.sh '{"session_id":"a8","prompt":"summarise this session of work"}' ''
expect "no infra for 'workflow' in prose" prompt-router.sh '{"session_id":"a9","prompt":"explain the order workflow in checkout.ts"}' ''
expect "security for session cookie"   prompt-router.sh '{"session_id":"a10","prompt":"set the session cookie flags"}' 'security'
expect "infra for github actions"      prompt-router.sh '{"session_id":"a11","prompt":"add a github actions workflow"}' 'infra'
expect "store prompt → store checklist" prompt-router.sh '{"session_id":"a12","prompt":"refresh the play store listing and screenshots"}' 'Load skill: store-submission-precheck'
expect "app icon prompt → store checklist" prompt-router.sh '{"session_id":"a13","prompt":"fix the adaptive icon"}' 'store-creative'
expect "no store for plain storage prompt" prompt-router.sh '{"session_id":"a14","prompt":"explain how the storage cache works"}' ''
expect "story art prompt → art checklist" prompt-router.sh '{"session_id":"a14b","prompt":"make story art for the feature rows"}' 'Brand & story art checklist'
expect "hero image prompt → art checklist" prompt-router.sh '{"session_id":"a14c","prompt":"regenerate the hero image"}' 'Load skill: story-art'
expect "no art for plain scene prompt" prompt-router.sh '{"session_id":"a14d","prompt":"fix the scene graph loader"}' ''
# A web install has the art snippet but not the store snippet.
mv "$P/.agents/harness/snippets/store.md" "$P/store.md.off"
expect "web: illustration prompt → art checklist" prompt-router.sh '{"session_id":"a14e","prompt":"add illustrations to the landing sections"}' 'export_art.py'
expect "web: logo prompt → art checklist" prompt-router.sh '{"session_id":"a14f","prompt":"design a new logo"}' 'brand-asset-creator'
mv "$P/store.md.off" "$P/.agents/harness/snippets/store.md"
expect "panorama prompt → media checklist" prompt-router.sh '{"session_id":"m1","prompt":"our panoramic store screenshots all look the same"}' 'Media checklist'
expect "og image prompt → media checklist" prompt-router.sh '{"session_id":"m2","prompt":"make a new OG image for the blog"}' 'creative-director'
expect "banner prompt → media checklist" prompt-router.sh '{"session_id":"m3","prompt":"design a promo banner for the launch"}' 'direction.py approve'
expect "art direction prompt → media checklist" prompt-router.sh '{"session_id":"m4","prompt":"set the art direction for the brand"}' 'Media checklist'
out="$(run prompt-router.sh '{"session_id":"m5","prompt":"fix the cookie banner component spacing"}')"
grep -q 'Media checklist' <<<"$out" && { fail=$((fail+1)); echo "  [FAIL] a UI cookie banner routed to media"; } || { pass=$((pass+1)); echo "  [OK] a cookie banner is UI, not media"; }
out="$(run prompt-router.sh '{"session_id":"m6","prompt":"swap the icon font in the settings screen"}')"
grep -q 'Media checklist' <<<"$out" && { fail=$((fail+1)); echo "  [FAIL] an icon font routed to media"; } || { pass=$((pass+1)); echo "  [OK] an icon font is not media"; }
out="$(run prompt-router.sh '{"session_id":"m7","prompt":"design a new logo and an og image"}')"
[[ "$(grep -o 'Media checklist' <<<"$out" | wc -l | tr -d ' ')" -eq 1 ]] && { pass=$((pass+1)); echo "  [OK] the media checklist is injected once"; } || { fail=$((fail+1)); echo "  [FAIL] media checklist repeated"; }
expect "promo video prompt → media checklist" prompt-router.sh '{"session_id":"m8","prompt":"make a 15 second promo video for instagram reels"}' 'brand-video'
expect "voice-over prompt → media checklist" prompt-router.sh '{"session_id":"m9","prompt":"write the voice-over script for the launch teaser"}' 'Media checklist'
out="$(run prompt-router.sh '{"session_id":"m10","prompt":"the video player controls overlap on mobile"}')"
grep -q 'Media checklist' <<<"$out" && { fail=$((fail+1)); echo "  [FAIL] a video player routed to media"; } || { pass=$((pass+1)); echo "  [OK] a video player is UI, not media"; }
out="$(run prompt-router.sh '{"session_id":"m11","prompt":"add a video call button to the chat screen"}')"
grep -q 'Media checklist' <<<"$out" && { fail=$((fail+1)); echo "  [FAIL] a video call routed to media"; } || { pass=$((pass+1)); echo "  [OK] a video call is not media"; }
for p in "fix the VoiceOver label on the save button" "split Main.storyboard into two scenes" "the <video> element autoplays on iOS" "add a video-player skin"; do
  out="$(run prompt-router.sh "{\"session_id\":\"m12-${#p}\",\"prompt\":\"$p\"}")"
  grep -q 'Media checklist' <<<"$out" && { fail=$((fail+1)); echo "  [FAIL] UI prompt routed to media: $p"; } || { pass=$((pass+1)); echo "  [OK] UI prompt is not media: $p"; }
done
echo "motion routing"
expect "reference video prompt → motion checklist" prompt-router.sh '{"session_id":"mo1","prompt":"recreate the hero animation from this reference video"}' 'Motion checklist'
out="$(run prompt-router.sh '{"session_id":"mo2","prompt":"recreate the hero animation from this reference video"}')"
grep -q 'Media checklist' <<<"$out" && { fail=$((fail+1)); echo "  [FAIL] a reference video for UI motion routed to brand-video's media checklist"; } || { pass=$((pass+1)); echo "  [OK] a reference video for UI motion is not the media checklist"; }
k=0
for p in "add a parallax hero to the landing page" "match this scroll-driven animation" "the dolly zoom looks wrong" "make the camera movement smoother" "a cinematic intro for the home page" "slow ken burns on the header image"; do
  k=$((k + 1)); out="$(run prompt-router.sh "{\"session_id\":\"mo3-$k\",\"prompt\":\"$p\"}")"
  grep -q 'Motion checklist' <<<"$out" && { pass=$((pass+1)); echo "  [OK] motion prompt: $p"; } || { fail=$((fail+1)); echo "  [FAIL] motion prompt not routed: $p"; }
done
for p in "add a reduced motion toggle in settings" "respect prefers-reduced-motion in the carousel" "read device motion for the compass" "slow motion replay of the match" "users report motion sickness on scroll"; do
  k=$((k + 1)); out="$(run prompt-router.sh "{\"session_id\":\"mo4-$k\",\"prompt\":\"$p\"}")"
  grep -q 'Motion checklist' <<<"$out" && { fail=$((fail+1)); echo "  [FAIL] not a motion prompt, routed anyway: $p"; } || { pass=$((pass+1)); echo "  [OK] not a motion prompt: $p"; }
done
expect "a promo video still goes to the media checklist" prompt-router.sh '{"session_id":"mo5","prompt":"make a 15 second promo video for instagram reels"}' 'Media checklist'
expect "plain prompt → nothing"        prompt-router.sh '{"session_id":"a6","prompt":"what does this function return?"}' ''
expect "valid JSON escaping"           prompt-router.sh '{"session_id":"a7","prompt":"fix \"auth\" token\nflow"}' '"additionalContext":"Harness'

expect "a sub-agent cannot record an approval" guard.sh '{"session_id":"g1","agent_id":"a-9","agent_type":"store-creative","tool_name":"Bash","tool_input":{"command":"python .claude/skills/creative-direction/scripts/direction.py approve --gate concept --family store --concept x --by me --evidence y"}}' 'only the main session records owner approvals'
expect "the main session can record one" guard.sh '{"session_id":"g1","tool_name":"Bash","tool_input":{"command":"python .claude/skills/creative-direction/scripts/direction.py approve --gate direction --by Owner --evidence chat"}}' ''
expect "a sub-agent cannot approve a storyboard" guard.sh '{"session_id":"g1","agent_id":"a-9","agent_type":"video-creative","tool_name":"Bash","tool_input":{"command":"python .claude/skills/creative-direction/scripts/direction.py approve --gate storyboard --piece launch --by me --evidence y"}}' 'only the main session records owner approvals'
expect "a sub-agent cannot run a generation provider" guard.sh '{"session_id":"g1","agent_id":"a-9","agent_type":"video-creative","tool_name":"Bash","tool_input":{"command":"python .claude/skills/brand-video/scripts/render_video.py generate launch --what tts"}}' 'only the main session runs a generation provider'
expect "a quoted subcommand is still a provider run" guard.sh '{"session_id":"g1","agent_id":"a-9","agent_type":"video-creative","tool_name":"Bash","tool_input":{"command":"python render_video.py \"generate\" launch --what broll"}}' 'only the main session runs a generation provider'
expect "the main session can run one" guard.sh '{"session_id":"g1","tool_name":"Bash","tool_input":{"command":"python .claude/skills/brand-video/scripts/render_video.py generate launch --what tts"}}' ''
expect "a sub-agent cannot acknowledge review items" guard.sh '{"session_id":"g1","agent_id":"a-9","agent_type":"video-creative","tool_name":"Bash","tool_input":{"command":"python3 .claude/skills/creative-direction/scripts/direction.py --project . approve --gate review --run 20261002-120000-0a0b0c --items all --by me --evidence y"}}' 'only the main session records owner approvals'
expect "a sub-agent may check status" guard.sh '{"session_id":"g1","agent_id":"a-9","tool_name":"Bash","tool_input":{"command":"python .claude/skills/creative-direction/scripts/direction.py status"}}' ''

echo "file-context"
expect "new .tsx → ui"       file-context.sh '{"session_id":"b1","tool_name":"Write","tool_input":{"file_path":"/p/src/components/Card.tsx"}}' 'ui-ux'
expect "robots.txt → seo"    file-context.sh '{"session_id":"b2","tool_name":"Write","tool_input":{"file_path":"/p/public/robots.txt"}}' 'seo'
expect "backend API route → no seo gate" file-context.sh '{"session_id":"b2a","tool_name":"Write","tool_input":{"file_path":"/p/src/api/v1/users/routes/users.routes.ts"}}' 'security'
out="$(run file-context.sh '{"session_id":"b2b","tool_name":"Write","tool_input":{"file_path":"/p/server/routes/index.ts"}}')"
grep -q 'permissionDecision\|SEO checklist' <<<"$out" && { fail=$((fail+1)); echo "  [FAIL] server route gated by seo — got: ${out:0:120}"; } || { pass=$((pass+1)); echo "  [OK] server route not gated by seo"; }
mv "$P/.claude/skills/seo" "$P/.claude/skills/seo.off"
out="$(run file-context.sh '{"session_id":"b2c","tool_name":"Write","tool_input":{"file_path":"/p/public/robots.txt"}}')"
grep -q 'permissionDecision' <<<"$out" && { fail=$((fail+1)); echo "  [FAIL] gate fired for an uninstalled skill"; } || { pass=$((pass+1)); echo "  [OK] no gate when the skill is not installed"; }
mv "$P/.claude/skills/seo.off" "$P/.claude/skills/seo"
expect "auth route → security" file-context.sh '{"session_id":"b3","tool_name":"Edit","tool_input":{"file_path":"/p/src/auth/login.ts"}}' 'security'
expect "app.json → store checklist" file-context.sh '{"session_id":"b8","tool_name":"Edit","tool_input":{"file_path":"/p/mobile/app.json"}}' 'store-submission-precheck'
expect "store-assets file → store checklist" file-context.sh '{"session_id":"b9","tool_name":"Write","tool_input":{"file_path":"C:\\p\\mobile\\store-assets\\LISTING.md"}}' 'store'
expect "plain .go → nothing" file-context.sh '{"session_id":"b4","tool_name":"Edit","tool_input":{"file_path":"/p/internal/math/add.go"}}' ''
expect "first UI write denied (enforce)"   file-context.sh '{"session_id":"b5","tool_name":"Write","tool_input":{"file_path":"C:\\p\\src\\ui\\Chip.tsx"}}' '"permissionDecision":"deny"'
expect "retry allowed"                     file-context.sh '{"session_id":"b5","tool_name":"Write","tool_input":{"file_path":"C:\\p\\src\\ui\\Chip.tsx"}}' ''
expect "sub-agent gets its own gate"       file-context.sh '{"session_id":"b5","agent_id":"a-1","agent_type":"implementor","tool_name":"Write","tool_input":{"file_path":"/p/src/ui/Card.tsx"}}' 'deny'
expect "agent_id in tool_input ignored"    file-context.sh '{"session_id":"b5","tool_name":"Write","tool_input":{"file_path":"/p/src/ui/X.tsx","agent_id":"evil"}}' ''
run prompt-router.sh '{"session_id":"b6","prompt":"restyle the navbar"}' >/dev/null
expect "gate still applies after prompt checklist" file-context.sh '{"session_id":"b6","tool_name":"Write","tool_input":{"file_path":"/p/src/ui/Nav.tsx"}}' 'deny'
out="$(run file-context.sh '{"session_id":"b10","tool_name":"Write","tool_input":{"file_path":"/p/src/theme/tokens.css"}}')"
if [[ $(grep -o '"permissionDecision":"deny"' <<<"$out" | wc -l) -eq 1 ]] && grep -q 'mandatory skills' <<<"$out" \
   && grep -q 'ui-ux/SKILL.md' <<<"$out" && grep -q 'typography/SKILL.md' <<<"$out" && grep -q 'color-science/SKILL.md' <<<"$out"; then
  pass=$((pass+1)); echo "  [OK] one UI deny names ui-ux, typography and color-science"
else fail=$((fail+1)); echo "  [FAIL] UI deny should name all three skills once — got: ${out:0:200}"; fi
expect "retry after three-skill deny allowed" file-context.sh '{"session_id":"b10","tool_name":"Write","tool_input":{"file_path":"/p/src/theme/tokens.css"}}' ''
expect "no second deny for another UI file"   file-context.sh '{"session_id":"b10","tool_name":"Write","tool_input":{"file_path":"/p/src/styles/app.scss"}}' ''
mv "$P/.claude/skills/typography" "$P/.claude/skills/typography.off"; mv "$P/.claude/skills/color-science" "$P/.claude/skills/color-science.off"
out="$(run file-context.sh '{"session_id":"b13","tool_name":"Write","tool_input":{"file_path":"/p/src/ui/Old.tsx"}}')"
if grep -q 'falls under a mandatory skill\.' <<<"$out" && grep -q 'ui-ux/SKILL.md' <<<"$out" && ! grep -q 'typography/SKILL.md' <<<"$out"; then
  pass=$((pass+1)); echo "  [OK] UI deny lists only the installed skills"
else fail=$((fail+1)); echo "  [FAIL] partial install deny — got: ${out:0:200}"; fi
mv "$P/.claude/skills/typography.off" "$P/.claude/skills/typography"; mv "$P/.claude/skills/color-science.off" "$P/.claude/skills/color-science"
expect "SEO deny keeps singular wording"      file-context.sh '{"session_id":"b12","tool_name":"Write","tool_input":{"file_path":"/p/public/robots.txt"}}' 'falls under a mandatory skill\.'
out="$(run file-context.sh '{"session_id":"d1","tool_name":"Write","tool_input":{"file_path":"/p/brand/direction.json"}}')"
if grep -q '"permissionDecision":"deny"' <<<"$out" && grep -q 'creative-direction/SKILL.md' <<<"$out" && grep -q 'color-science/SKILL.md' <<<"$out"; then
  pass=$((pass+1)); echo "  [OK] the first direction write is denied once, naming creative-direction and color-science"
else fail=$((fail+1)); echo "  [FAIL] media gate — got: ${out:0:200}"; fi
expect "retry of the direction write allowed (drafting needs no approval)" file-context.sh '{"session_id":"d1","tool_name":"Write","tool_input":{"file_path":"/p/brand/direction.json"}}' ''
expect "a kit frames.json falls under the media gate" file-context.sh '{"session_id":"d2","tool_name":"Edit","tool_input":{"file_path":"C:\\p\\store-assets\\mockup-kit\\frames.json"}}' 'creative-direction'
expect "a video piece falls under the media gate" file-context.sh '{"session_id":"d6","tool_name":"Write","tool_input":{"file_path":"/p/brand/video/launch/video.json"}}' 'creative-direction'
out="$(run file-context.sh '{"session_id":"d8","tool_name":"Write","tool_input":{"file_path":"/p/brand/motion/hero/motion.json"}}')"
if grep -q '"permissionDecision":"deny"' <<<"$out" && grep -q 'motion-ui/SKILL.md' <<<"$out" && grep -q 'creative-direction/SKILL.md' <<<"$out"; then
  pass=$((pass+1)); echo "  [OK] the first motion spec write is denied once, naming motion-ui and creative-direction"
else fail=$((fail+1)); echo "  [FAIL] motion gate — got: ${out:0:200}"; fi
expect "retry of the motion spec write allowed" file-context.sh '{"session_id":"d8","tool_name":"Write","tool_input":{"file_path":"/p/brand/motion/hero/motion.json"}}' ''
expect "motion run manifests are never hand-edited" file-context.sh '{"session_id":"d9","tool_name":"Edit","tool_input":{"file_path":"/p/brand/runs/motion/20261012-120000-0a0b0c.json"}}' 'immutable run manifests'
expect "run manifests are never hand-edited" file-context.sh '{"session_id":"d7","tool_name":"Edit","tool_input":{"file_path":"/p/brand/runs/video/20261002-120000-0a0b0c.json"}}' 'immutable run manifests'
expect "approvals are never hand-edited" file-context.sh '{"session_id":"d3","tool_name":"Edit","tool_input":{"file_path":"/p/brand/approvals.json"}}' 'written only by direction.py approve'
expect "approvals stay denied on retry" file-context.sh '{"session_id":"d3","tool_name":"Edit","tool_input":{"file_path":"/p/brand/approvals.json"}}' '"permissionDecision":"deny"'
out="$(run file-context.sh '{"session_id":"d4","tool_name":"Write","tool_input":{"file_path":"/p/mobile/store-assets/LISTING.md"}}')"
grep -q 'creative-direction' <<<"$out" && { fail=$((fail+1)); echo "  [FAIL] LISTING.md got the media gate"; } || { pass=$((pass+1)); echo "  [OK] LISTING.md is copy, not media"; }
printf 'checklists=inform\n' > "$P/.agents/harness.config"
expect "inform mode: the media gate only informs" file-context.sh '{"session_id":"d5","tool_name":"Write","tool_input":{"file_path":"/p/brand/canvas.json"}}' '"additionalContext"'
expect "inform mode adds context only"     file-context.sh '{"session_id":"b7","tool_name":"Write","tool_input":{"file_path":"/p/src/ui/Y.tsx"}}' '"additionalContext"'
out="$(run file-context.sh '{"session_id":"b11","tool_name":"Write","tool_input":{"file_path":"/p/src/ui/Z.tsx"}}')"
if ! grep -q 'deny' <<<"$out" && grep -q 'ui-ux, typography, color-science' <<<"$out"; then
  pass=$((pass+1)); echo "  [OK] inform mode names all three skills without denying"
else fail=$((fail+1)); echo "  [FAIL] inform mode — got: ${out:0:200}"; fi
rm -f "$P/.agents/harness.config"

echo "normalised operations (multi-file patches, moves, after-edit events, agents)"
P1='*** Begin Patch\n*** Update File: src/a.go\n@@\n-x\n+y\n'
expect "patch: protected second file denies the patch" file-context.sh '{"session_id":"m1","hook_event_name":"PreToolUse","tool_name":"apply_patch","tool_input":{"command":"'"$P1"'*** Update File: brand/approvals.json\n@@\n-a\n+b\n*** End Patch"}}' '"permissionDecision":"deny"'
expect "patch: a move onto a protected path is denied" file-context.sh '{"session_id":"m2","hook_event_name":"PreToolUse","tool_name":"apply_patch","tool_input":{"command":"*** Begin Patch\n*** Update File: brand/old.json\n*** Move to: brand/runs/20261001.json\n*** End Patch"}}' 'brand/runs'
expect "patch: .env as the second file is denied" guard.sh '{"hook_event_name":"PreToolUse","tool_name":"apply_patch","tool_input":{"command":"'"$P1"'*** Add File: config/.env.local\n+K=V\n*** End Patch"}}' '"permissionDecision":"deny"'
expect "Edit carrying a patch body (Copilot CLI) checks every file" guard.sh '{"hook_event_name":"PreToolUse","tool_name":"Edit","tool_input":{"command":"'"$P1"'*** Delete File: .env\n*** End Patch"}}' 'deny'
expect "patch of ordinary files is allowed" guard.sh '{"hook_event_name":"PreToolUse","tool_name":"apply_patch","tool_input":{"command":"'"$P1"'*** End Patch"}}' ''
out="$(run file-context.sh '{"session_id":"m3","hook_event_name":"PostToolUse","tool_name":"Write","tool_input":{"file_path":"/p/brand/approvals.json"}}')"
if ! grep -q 'permissionDecision' <<<"$out" && grep -q 'revert it now' <<<"$out"; then
  pass=$((pass+1)); echo "  [OK] an after-edit event reports the violation instead of denying"
else fail=$((fail+1)); echo "  [FAIL] after-edit should report, not deny — got: ${out:0:160}"; fi
expect "after-edit: a UI gate only informs" file-context.sh '{"session_id":"m4","hook_event_name":"PostToolUse","tool_name":"Write","tool_input":{"file_path":"/p/src/ui/Late.tsx"}}' 'mandatory checklist'
expect "a read is not a write (matcher-less hosts)" file-context.sh '{"session_id":"m5","tool_name":"Read","tool_input":{"file_path":"/p/brand/approvals.json"}}' ''
echo "  Cursor runs .claude/settings.json hooks with its own payload (recognised by cursor_version)"
expect "cursor: Shell reading .env denied" guard.sh '{"cursor_version":"3.24","hook_event_name":"preToolUse","tool_name":"Shell","tool_input":{"command":"cat .env"}}' 'deny'
expect "cursor: beforeReadFile .env denied" guard.sh '{"cursor_version":"3.24","hook_event_name":"beforeReadFile","file_path":"/p/.env.local","content":""}' 'deny'
expect "cursor: Write gates a UI file" file-context.sh '{"cursor_version":"3.24","conversation_id":"c1","hook_event_name":"preToolUse","tool_name":"Write","tool_input":{"file_path":"/p/src/ui/Nav.tsx","content":"x"}}' 'deny'
expect "cursor: afterFileEdit on approvals.json reports" file-context.sh '{"cursor_version":"3.24","hook_event_name":"afterFileEdit","file_path":"/p/brand/approvals.json","edits":[]}' 'revert it now'
echo "  Copilot CLI: Claude event and tool names, native arguments (path)"
expect "copilot: Read path .env denied" guard.sh '{"hook_event_name":"PreToolUse","session_id":"s","tool_name":"Read","tool_input":{"path":"/p/.env"}}' 'deny'
expect "copilot: Write (create) to brand/runs denied" file-context.sh '{"hook_event_name":"PreToolUse","session_id":"s","tool_name":"Write","tool_input":{"path":"/p/brand/runs/r1.json","file_text":"{}"}}' 'brand/runs'
HOOK_ARGS="--agent codex"
expect "Opus policy is Claude-only (codex keeps its model)" guard.sh '{"tool_name":"spawn_agent","tool_input":{"model":"gpt-5"}}' ''
expect "codex: .env read via patch still denied" guard.sh '{"tool_name":"apply_patch","tool_input":{"command":"*** Begin Patch\n*** Update File: .env\n*** End Patch"}}' 'deny'
expect "codex: a thread-spawned sub-agent (agent_id) cannot approve" guard.sh '{"agent_id":"x","tool_name":"Bash","tool_input":{"command":"python direction.py approve --gate concept"}}' 'only the main session'
HOOK_ARGS="--agent gemini"
expect "gemini: read_file .env denied (decision JSON)" guard.sh '{"hook_event_name":"BeforeTool","tool_name":"read_file","tool_input":{"file_path":"/p/.env"}}' '"decision":"deny"'
expect "gemini: read_many_files with .env among paths denied" guard.sh '{"hook_event_name":"BeforeTool","tool_name":"read_many_files","tool_input":{"paths":["src/a.ts",".env.local"]}}' '"decision":"deny"'
expect "gemini: run_shell_command cat .env denied" guard.sh '{"hook_event_name":"BeforeTool","tool_name":"run_shell_command","tool_input":{"command":"cat .env"}}' 'deny'
expect "gemini: write_file gates a UI file" file-context.sh '{"session_id":"g9","hook_event_name":"BeforeTool","tool_name":"write_file","tool_input":{"file_path":"/p/src/ui/G.tsx","content":"x"}}' '"decision":"deny"'
HOOK_ARGS="--agent antigravity --event PreToolUse"
expect "antigravity: view_file .env denied" guard.sh '{"conversationId":"c","workspacePaths":["/p"],"toolCall":{"name":"view_file","args":{"AbsolutePath":"/p/.env"}}}' '"decision":"deny"'
expect "antigravity: run_command cat .env denied" guard.sh '{"conversationId":"c","toolCall":{"name":"run_command","args":{"CommandLine":"cat .env","Cwd":"/p"}}}' 'deny'
expect "antigravity: write_to_file approvals.json denied" file-context.sh '{"conversationId":"c","toolCall":{"name":"write_to_file","args":{"TargetFile":"/p/brand/approvals.json","CodeContent":"{}"}}}' '"decision":"deny"'
expect "antigravity: ordinary read allowed" guard.sh '{"conversationId":"c","toolCall":{"name":"view_file","args":{"AbsolutePath":"/p/src/a.ts"}}}' ''
HOOK_ARGS="--agent gemini"
expect "gemini: no sub-agent marker, so approval is not guessed" guard.sh '{"tool_name":"Bash","tool_input":{"command":"python direction.py approve --gate concept"}}' ''
HOOK_ARGS=""

echo "session-start"
expect "summary without lock warns" session-start.sh '{"session_id":"c1","source":"startup"}' 'lock is missing'
printf 'harness_version\t9.9.9\nprofiles\tweb\nmanaged\tx\t1\th\tkept-local\n' > "$P/.agents/harness/lock"
expect "reads version"      session-start.sh '{"session_id":"c1"}' 'v9.9.9'
expect "reports kept-local" session-start.sh '{"session_id":"c1"}' 'kept-local'
run prompt-router.sh '{"session_id":"c2","prompt":"style the navbar"}' >/dev/null
run session-start.sh '{"session_id":"c2","source":"compact"}' >/dev/null
expect "compact resets dedupe" prompt-router.sh '{"session_id":"c2","prompt":"style the navbar"}' 'ui-ux'
printf 'harness_version\t9.9.9\r\nprofiles\tweb\r\nmanaged\tx\t1\th\tkept-local\r\n' > "$P/.agents/harness/lock"
expect "CRLF lock: kept-local still seen" session-start.sh '{"session_id":"c3"}' 'kept-local'
out="$(run session-start.sh '{"session_id":"c4"}')"
grep -q 'store-creative' <<<"$out" && { fail=$((fail+1)); echo "  [FAIL] store roster shown without store agents"; } || { pass=$((pass+1)); echo "  [OK] no store roster when store agents absent"; }
mkdir -p "$P/.claude/agents" && : > "$P/.claude/agents/store-creative.md"
expect "store roster when installed" session-start.sh '{"session_id":"c5"}' 'store-precheck-auditor'
expect "store roster names the illustrator" session-start.sh '{"session_id":"c6"}' 'illustrator'
expect "store roster starts with the creative-director" session-start.sh '{"session_id":"c6b"}' 'Store agents: creative-director'
: > "$P/.claude/agents/illustrator.md"
out="$(run session-start.sh '{"session_id":"c7"}')"
[[ "$(grep -o 'illustrator' <<<"$out" | wc -l | tr -d ' ')" -eq 1 ]] && { pass=$((pass+1)); echo "  [OK] mobile: one roster line, not two"; } || { fail=$((fail+1)); echo "  [FAIL] mobile roster repeats the illustrator"; }
rm -f "$P/.claude/agents/store-creative.md"
expect "web roster when only the art agents are installed" session-start.sh '{"session_id":"c8"}' 'Brand, art, video and motion agents: creative-director (direction, concept critique) → brand-asset-creator / illustrator / video-creative / motion-designer'
expect "web roster names the motion skill" session-start.sh '{"session_id":"c8b"}' 'brand-video, motion-ui)'
rm -f "$P/.claude/agents/illustrator.md"

echo "post-edit-lint"
printf 'if [ x\n' > "$P/bad.sh"
expect "bash syntax error reported" post-edit-lint.sh "{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$P/bad.sh\"}}" 'bash -n'
printf '#!/usr/bin/env bash\necho ok\n' > "$P/good.sh"   # shebang: shellcheck (installed on CI) flags SC2148 without it
expect "clean file → nothing" post-edit-lint.sh "{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$P/good.sh\"}}" ''

echo "JSON validity"
if PY="$(command -v python3 || command -v python)"; then
  bad=0
  for pl in '{"tool_name":"Agent","tool_input":{"model":"sonnet"}}' '{"session_id":"z","prompt":"UI \ back\"slash"}'; do
    for h in guard.sh prompt-router.sh; do
      o="$(run "$h" "$pl")"; [[ -z "$o" ]] && continue
      "$PY" -c 'import json,sys; json.loads(sys.stdin.read())' <<<"$o" || bad=1
    done
  done
  [[ $bad -eq 0 ]] && { pass=$((pass+1)); echo "  [OK] hook output parses as JSON"; } || { fail=$((fail+1)); echo "  [FAIL] invalid JSON output"; }
fi

echo "performance"
start=$(date +%s%N 2>/dev/null || echo 0)
for _ in 1 2 3 4 5 6 7 8 9 10; do run guard.sh '{"tool_name":"Bash","tool_input":{"command":"ls -la"}}' >/dev/null; done
end=$(date +%s%N 2>/dev/null || echo 0)
if [[ "$start" != 0 && "$start" != *N ]]; then
  ms=$(( (end - start) / 10000000 ))
  # Informational only: shared CI runners are noisy. Correctness is asserted above.
  if [[ $ms -lt 300 ]]; then echo "  [OK] guard avg ${ms}ms (<300ms incl. bash startup)"
  else echo "  [WARN] guard avg ${ms}ms (>300ms; slow or busy runner?)"; fi
fi

echo; echo "hook tests: $pass passed, $fail failed"
[[ $fail -eq 0 ]]
