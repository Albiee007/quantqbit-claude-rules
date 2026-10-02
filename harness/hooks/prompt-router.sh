#!/usr/bin/env bash
# === harness prompt router (UserPromptSubmit) ===
# Keyword-routes the user's prompt to the mandatory skill checklists
# (ui, seo, patterns, security, store, art, media, infra). Each checklist is injected at most
# once per session. Pure bash; no subprocesses on the hot path.
set -uo pipefail
# shellcheck source=_lib.sh
_hd="${BASH_SOURCE[0]%/*}"; [[ "$_hd" == "${BASH_SOURCE[0]}" ]] && _hd=.
source "$_hd/_lib.sh"
hh_read_payload

hh_get prompt; prompt="$HH_V"
[[ -z "$prompt" ]] && exit 0
shopt -s nocasematch

# Word-ish boundaries: bash ERE has no \b, so anchor on non-letters.
B='(^|[^a-z0-9])'
E='([^a-z0-9]|$)'

# "design pattern" / "system design" must not trigger the UI checklist.
ui_text="$prompt"
ui_text="${ui_text//design pattern/ }"
ui_text="${ui_text//system design/ }"

if [[ "$ui_text" =~ $B(ui|ux|frontend|front-end|screens?|layouts?|components?|css|scss|tailwind|styl(e|es|ing)|design|redesign|a11y|accessib(le|ility)|wcag|buttons?|forms?|modals?|dialogs?|navbar|navigation|menu|responsive|dark[[:space:]]mode|theme|colou?rs?|palettes?|fonts?|typefaces?|typography|type[[:space:]]scale|oklch|gamut|animations?|landing[[:space:]]page|dashboard|figma|swiftui|jetpack|compose[[:space:]]ui|onboarding|empty[[:space:]]state)$E ]]; then
  hh_add_snippet ui
fi
if [[ "$prompt" =~ $B(seo|meta[[:space:]]?(tags?|description)|title[[:space:]]tags?|schema\.org|structured[[:space:]]data|json-ld|sitemaps?|robots\.txt|canonical|hreflang|serp|rank(ing)?|search[[:space:]]console|core[[:space:]]web[[:space:]]vitals|lcp|inp|cls|open[[:space:]]?graph|og:|ai[[:space:]]overviews?|llms\.txt|landing[[:space:]]page|blog|backlinks?|keywords?|indexing|crawl(ing|er)?)$E ]]; then
  hh_add_snippet seo
fi
if [[ "$prompt" =~ $B(design[[:space:]]patterns?|patterns?|refactor(ing)?|architect(ure)?|abstract(ion|[[:space:]]class)?|interfaces?|factory|singleton|strategy|observer|decorator|adapter|repository|dependency[[:space:]]injection|di[[:space:]]container|clean[[:space:]]architecture|hexagonal|microservices?|cqrs|event[[:space:]]sourcing|restructure|decouple|layers?|modulari[sz]e)$E ]]; then
  hh_add_snippet patterns
fi
if [[ "$prompt" =~ $B(auth(entication|orization)?|login|sign[[:space:]-]?(up|in)|passwords?|tokens?|jwt|oauth|session[[:space:]-]?(cookies?|tokens?|fixation|hijack(ing)?|management|storage)|cookies?|csrf|xss|sql|injection|uploads?|permissions?|rbac|secrets?|encrypt(ion)?|crypto|api[[:space:]]keys?|webhooks?|cors|pii|gdpr)$E ]]; then
  hh_add_snippet security
fi
# Store / brand work (the snippet ships only to mobile projects, so this is a no-op elsewhere).
if [[ "$prompt" =~ $B(app[[:space:]]store|play[[:space:]]store|google[[:space:]]play|store[[:space:]]listing|store[[:space:]]screenshots?|app[[:space:]]screenshots?|mockups?|aso|testflight|feature[[:space:]]graphic|app[[:space:]]icons?|adaptive[[:space:]]icons?|launcher[[:space:]]icons?|notification[[:space:]]icons?|splash([[:space:]]screen)?|logos?|adb|release[[:space:]]notes|data[[:space:]]safety|app[[:space:]]review)$E ]]; then
  hh_add_snippet store
fi
# Brand and story art (web and mobile; a no-op where the snippet isn't installed).
if [[ "$prompt" =~ $B(illustrations?|artwork|story[[:space:]]art|scene[[:space:]]art|hero[[:space:]](image|art|illustration)s?|logos?|brand[[:space:]](assets?|identity|kit))$E ]]; then
  hh_add_snippet art
fi
# Any media asset: the creative-direction checklist (web and mobile; a no-op elsewhere).
# UI banners, icon buttons and icon fonts are UI work, not media.
media_text="$prompt"
for neg in "cookie banner" "consent banner" "error banner" "alert banner" "banner component" "icon button" "icon font"; do
  media_text="${media_text//$neg/ }"
done
if [[ "$media_text" =~ $B(banners?|panoram(a|as|ic)|og[[:space:]-]?images?|open[[:space:]]graph[[:space:]]images?|social[[:space:]](images?|cards?|previews?|posts?)|share[[:space:]]images?|feature[[:space:]]graphics?|store[[:space:]](screenshots?|visuals?|assets?)|app[[:space:]]screenshots?|mockups?|app[[:space:]]icons?|launcher[[:space:]]icons?|logos?|illustrations?|story[[:space:]]art|hero[[:space:]](image|art|illustration)s?|creative[[:space:]]direction|art[[:space:]]direction|mood[[:space:]]?boards?|visual[[:space:]]identity|brand[[:space:]](assets?|identity|kit|look)|promo[[:space:]](images?|graphics?)|posters?|email[[:space:]]headers?|marketing[[:space:]](images?|visuals?|assets?))$E ]]; then
  hh_add_snippet media
fi
if [[ "$prompt" =~ $B(docker|compose|dockerfile|ansible|playbook|terraform|deploy(ment)?|ci/cd|ci[[:space:]](pipeline|workflow|job)|pipeline|github[[:space:]]actions|bash|shell[[:space:]]script|powershell|ps1|nginx|traefik|kubernetes|k8s|helm|infra(structure)?)$E ]]; then
  hh_add_snippet infra
fi

[[ -n "$HH_OUT" ]] && hh_emit_context UserPromptSubmit "Harness: mandatory checklists for this request (load the named skill before starting):
$HH_OUT"
exit 0
