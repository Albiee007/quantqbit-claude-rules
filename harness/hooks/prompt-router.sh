#!/usr/bin/env bash
# === harness prompt router (UserPromptSubmit) ===
# Keyword-routes the user's prompt to the mandatory skill checklists
# (ui, seo, patterns, security, infra). Each checklist is injected at most
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

if [[ "$ui_text" =~ $B(ui|ux|frontend|front-end|screens?|layouts?|components?|css|scss|tailwind|styl(e|es|ing)|design|redesign|a11y|accessib(le|ility)|wcag|buttons?|forms?|modals?|dialogs?|navbar|navigation|menu|responsive|dark[[:space:]]mode|theme|colou?rs?|fonts?|typography|animations?|landing[[:space:]]page|dashboard|figma|swiftui|jetpack|compose[[:space:]]ui|onboarding|empty[[:space:]]state)$E ]]; then
  hh_add_snippet ui
fi
if [[ "$prompt" =~ $B(seo|meta[[:space:]]?(tags?|description)|title[[:space:]]tags?|schema\.org|structured[[:space:]]data|json-ld|sitemaps?|robots\.txt|canonical|hreflang|serp|rank(ing)?|search[[:space:]]console|core[[:space:]]web[[:space:]]vitals|lcp|inp|cls|open[[:space:]]?graph|og:|ai[[:space:]]overviews?|llms\.txt|landing[[:space:]]page|blog|backlinks?|keywords?|indexing|crawl(ing|er)?)$E ]]; then
  hh_add_snippet seo
fi
if [[ "$prompt" =~ $B(design[[:space:]]patterns?|patterns?|refactor(ing)?|architect(ure)?|abstract(ion|[[:space:]]class)?|interfaces?|factory|singleton|strategy|observer|decorator|adapter|repository|dependency[[:space:]]injection|di[[:space:]]container|clean[[:space:]]architecture|hexagonal|microservices?|cqrs|event[[:space:]]sourcing|restructure|decouple|layers?|modulari[sz]e)$E ]]; then
  hh_add_snippet patterns
fi
if [[ "$prompt" =~ $B(auth(entication|orization)?|login|sign[[:space:]-]?(up|in)|passwords?|tokens?|jwt|oauth|sessions?|cookies?|csrf|xss|sql|injection|uploads?|permissions?|rbac|secrets?|encrypt(ion)?|crypto|api[[:space:]]keys?|webhooks?|cors|pii|gdpr)$E ]]; then
  hh_add_snippet security
fi
if [[ "$prompt" =~ $B(docker|compose|dockerfile|ansible|playbook|terraform|deploy(ment)?|ci|cd|pipeline|github[[:space:]]actions|workflow|bash|shell[[:space:]]script|powershell|ps1|nginx|traefik|kubernetes|k8s|helm|infra(structure)?)$E ]]; then
  hh_add_snippet infra
fi

[[ -n "$HH_OUT" ]] && hh_emit_context UserPromptSubmit "Harness: mandatory checklists for this request (load the named skill before starting):
$HH_OUT"
exit 0
