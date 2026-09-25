# shellcheck shell=bash
# Reject metadata paths that could escape a target or follow a symlink.
# Root must already be absolute. No subprocesses: this runs once per file.
safe_relative_path() {
  local rel="$2" part current="$1" rest="$2"
  case "$rel" in
    ''|/*|*\\*|*:*|*$'\t'*|*$'\n'*|*$'\r'*) return 1 ;;
  esac
  while :; do
    part="${rest%%/*}"
    case "$part" in ''|.|..|*[.\ ]) return 1 ;; esac
    current="$current/$part"
    [[ ! -L "$current" ]] || return 1
    [[ "$rest" == */* ]] || break
    rest="${rest#*/}"
  done
}
