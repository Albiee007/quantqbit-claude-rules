# shellcheck shell=bash
# ============================================================================
# harness-lib.sh — shared helpers for harness sync, doctor and release
# ============================================================================
# Sourced (not executed). Bash 3.2-compatible: no associative arrays, no
# mapfile, no ${var,,}. Portable across Linux, macOS, and Git Bash (Windows).
#
# Hashing is CRLF-normalised: every line has a trailing CR stripped and ends
# with LF before hashing, so a Windows checkout with core.autocrlf=true never
# looks "modified" versus the LF source. (This covers hash comparison only;
# script line endings in projects are pinned by the shipped .claude/.gitattributes.)
# ============================================================================

HARNESS_EMPTY_SHA="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

# Canonical upstream recorded in every project lock. Deliberately a constant:
# the syncing checkout's own remote (a local path, SSH form or tokenised URL)
# must never leak into a committed lock or vary between developers.
# shellcheck disable=SC2034  # used by the scripts that source this library
HARNESS_UPSTREAM_URL="https://github.com/Albiee007/quantqbit-claude-rules"

hc_info() { printf '[INFO] %s\n' "$*" >&2; }
hc_ok()   { printf '[OK] %s\n'   "$*" >&2; }
hc_warn() { printf '[WARN] %s\n' "$*" >&2; }
hc_fail() { printf '[FAIL] %s\n' "$*" >&2; }
hc_die()  { hc_fail "$*"; exit 2; }

# hc_sha_tool — echo the sha256 command available on this system.
hc_sha_tool() {
  if command -v sha256sum >/dev/null 2>&1; then
    echo "sha256sum"
  elif command -v shasum >/dev/null 2>&1; then
    echo "shasum -a 256"
  else
    return 1
  fi
}

# hc_python — echo a working python 3 command: python3, python, or the Windows
# "py -3" launcher. Guards against the Windows Store "python" stub, which
# exists but does not run. The result may contain a space ("py -3"), so run it
# through hc_py rather than quoting it.
hc_python() {
  local py
  for py in python3 python "py -3"; do
    # shellcheck disable=SC2086  # intentional word split for "py -3"
    if command -v ${py%% *} >/dev/null 2>&1 \
       && $py -c 'import json, sys; sys.exit(sys.version_info[0] != 3)' >/dev/null 2>&1; then
      echo "$py"
      return 0
    fi
  done
  return 1
}

# hc_py <args…> — run the python found by hc_python.
hc_py() {
  local py
  py="$(hc_python)" || return 127
  # shellcheck disable=SC2086  # intentional word split for "py -3"
  $py "$@"
}

# hc_find_sources — print "<version>\t<path>" for every local harness source
# found, newest first: $HARNESS_HOME, $CLAUDE_PLUGIN_ROOT, the installed Claude
# Code plugin copies (${CLAUDE_CONFIG_DIR:-~/.claude}/plugins/cache/quantqbit/…)
# and ~/.local/share/quantqbit-claude-rules.
hc_find_sources() {
  local cfg="${CLAUDE_CONFIG_DIR:-$HOME/.claude}" c v
  if [[ "$cfg" == *\\* || "$cfg" == [A-Za-z]:* ]] && command -v cygpath >/dev/null 2>&1; then
    cfg="$(cygpath -u "$cfg")"
  fi
  for c in "${HARNESS_HOME:-}" "${CLAUDE_PLUGIN_ROOT:-}" \
           "$cfg"/plugins/cache/quantqbit/quantqbit-claude-rules/* \
           "$HOME/.local/share/quantqbit-claude-rules"; do
    [[ -n "$c" && -f "$c/scaffold/sync.sh" && -f "$c/harness/manifest.tsv" && -f "$c/VERSION" ]] || continue
    v="$(tr -d '[:space:]' < "$c/VERSION")"
    printf '%s\t%s\n' "$v" "$c"
  done | awk -F'\t' '!seen[$2]++' | sort -t. -k1,1nr -k2,2nr -k3,3nr
}

# hc_ver_lt <a> <b> — true when semver a < b. False when equal, newer, or when
# either side is not X.Y.Z (so an unknown version never blocks anything).
hc_ver_lt() {
  local re='^([0-9]+)\.([0-9]+)\.([0-9]+)$' a1 a2 a3
  [[ "${1:-}" =~ $re ]] || return 1
  a1="${BASH_REMATCH[1]}"; a2="${BASH_REMATCH[2]}"; a3="${BASH_REMATCH[3]}"
  [[ "${2:-}" =~ $re ]] || return 1
  if (( 10#$a1 != 10#${BASH_REMATCH[1]} )); then (( 10#$a1 < 10#${BASH_REMATCH[1]} )); return; fi
  if (( 10#$a2 != 10#${BASH_REMATCH[2]} )); then (( 10#$a2 < 10#${BASH_REMATCH[2]} )); return; fi
  (( 10#$a3 < 10#${BASH_REMATCH[3]} ))
}

# hc_hash_list <root> — read relative paths (one per line) on stdin and print
# "<sha256>\t<path>" for each, CRLF-normalised. A missing file prints "-".
# Uses one awk + one sha256 process for the whole batch (fork cost matters on
# Windows).
hc_hash_list() {
  local root="$1" sha tmp i n p
  sha="$(hc_sha_tool)" || hc_die "no sha256sum/shasum found"
  tmp="$(mktemp -d "${TMPDIR:-/tmp}/harness-hash.XXXXXX")"
  local -a all=() nonempty=() idxmap=()
  while IFS= read -r p; do
    [[ -n "$p" ]] && all+=("$p")
  done
  n=0
  for i in "${!all[@]}"; do
    p="$root/${all[$i]}"
    if [[ -f "$p" && -s "$p" ]]; then
      nonempty+=("$p")
      n=$((n + 1))
      idxmap[$i]="$n"
    fi
  done
  if [[ ${#nonempty[@]} -gt 0 ]]; then
    # FNR==1 fires once per non-empty file, so output N maps to nonempty[N-1].
    awk -v d="$tmp" 'FNR==1 { if (out != "") close(out); out = d "/" (++k) }
                     { sub(/\r$/, ""); print > out }' "${nonempty[@]}"
    (cd "$tmp" && $sha -- $(seq 1 "$n")) > "$tmp/.sums" 2>/dev/null \
      || (cd "$tmp" && $sha $(seq 1 "$n")) > "$tmp/.sums"
  else
    : > "$tmp/.sums"
  fi
  # Emit "<key>\t<path>" where key is the awk output index, "-" (missing) or
  # "E" (empty), then join against the sums file in a single awk pass.
  for i in "${!all[@]}"; do
    p="$root/${all[$i]}"
    if [[ ! -f "$p" ]]; then
      printf -- '-\t%s\n' "${all[$i]}"
    elif [[ ! -s "$p" ]]; then
      printf 'E\t%s\n' "${all[$i]}"
    else
      printf '%s\t%s\n' "${idxmap[$i]}" "${all[$i]}"
    fi
  done > "$tmp/.keys"
  # sums line: "<hash>  <N>" (sha256sum may prefix '*' in binary mode)
  awk -F'\t' -v empty="$HARNESS_EMPTY_SHA" '
    FNR == NR { split($0, a, /[ \t]+/); f = a[2]; sub(/^\*/, "", f); h[f] = a[1]; next }
    $1 == "-" { print "-\t" $2; next }
    $1 == "E" { print empty "\t" $2; next }
    { print h[$1] "\t" $2 }
  ' "$tmp/.sums" "$tmp/.keys"
  rm -rf "$tmp"
}

# hc_hash_file <file> — normalised sha256 of a single file ("-" if missing).
hc_hash_file() {
  local f="$1" d b
  d="$(dirname "$f")"; b="$(basename "$f")"
  printf '%s\n' "$b" | hc_hash_list "$d" | cut -f1
}

# hc_inject_header <src> <dest> <version> [rel] — copy src to dest with LF line
# endings, adding the harness:managed marker in a format-appropriate place.
# Data files (json, tsv, snippets, dotfiles) get no marker; the lock covers
# them. The marker is plain ASCII so Windows PowerShell 5.1 renders it cleanly.
hc_inject_header() {
  local src="$1" dest="$2" ver="$3" rel="${4:-}"
  local md="<!-- harness:managed v${ver} - do not edit; override in .claude/rules/project/ (see .claude/harness/README.md) -->"
  local sh="# harness:managed v${ver} - do not edit; re-run harness sync to update"
  mkdir -p "$(dirname "$dest")"
  case "$rel" in
    snippets/*|*.json|*.tsv|*.txt|dotfiles/*)
      tr -d '\r' < "$src" > "$dest"; return 0 ;;
  esac
  case "$src" in
    *.md)
      # After YAML frontmatter if present, else as the first line.
      tr -d '\r' < "$src" | awk -v m="$md" '
        NR == 1 && $0 ~ /^---$/ { fm = 1; print; next }
        fm == 1 && $0 ~ /^---$/ { print; print m; fm = 2; next }
        NR == 1 && fm != 1 { print m }
        { print }
      ' > "$dest" ;;
    *.sh)
      tr -d '\r' < "$src" \
        | awk -v m="$sh" 'NR == 1 && /^#!/ { print; print m; next } NR == 1 { print m } { print }' > "$dest" ;;
    *.ps1)
      { printf '%s\n' "$sh"; tr -d '\r' < "$src"; } > "$dest" ;;
    *)
      cp "$src" "$dest" ;;
  esac
}

# hc_profile_match <row_profiles> <selected_profiles> — true if the manifest
# row applies. "all" on either side matches everything.
hc_profile_match() {
  local row="$1" sel="$2" p q
  [[ "$row" == "all" || "$sel" == "all" ]] && return 0
  local IFS=','
  for p in $row; do
    for q in $sel; do
      [[ "$p" == "$q" ]] && return 0
    done
  done
  return 1
}

# hc_config_get <config_file> <key> — read KEY=VALUE from harness.config.
hc_config_get() {
  local f="$1" k="$2"
  [[ -f "$f" ]] || return 0
  awk -F'=' -v k="$k" '
    /^[[:space:]]*#/ { next }
    { key = $1; gsub(/^[[:space:]]+|[[:space:]]+$/, "", key) }
    key == k { sub(/^[^=]*=/, ""); gsub(/^[[:space:]]+|[[:space:]]+$|\r/, ""); print; exit }
  ' "$f"
}
