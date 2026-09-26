# shellcheck shell=bash
# ============================================================================
# Transaction helpers — journaled, reversible changes to a target tree.
#
# The pattern proven by sync.sh, shared so other writers get the same
# guarantees:
#   - a mkdir mutex stops two runs mutating one target at once;
#   - work files live inside the target (same filesystem: mv is a rename);
#   - each journal row is written BEFORE the change it records, so a failure
#     at any point can be undone by replaying the journal in reverse;
#   - the caller writes its commit record last (txn_commit_file) and then
#     calls txn_end; an EXIT trap calling txn_on_exit rolls back otherwise.
#
# Journal rows (tab-separated): restore <rel> | delete <rel> | rmdir <rel>.
# Every <rel> must already have passed safe_relative_path (no tabs/newlines).
#
# Usage:
#   txn_begin <root> <tmp_rel> <name> [force_unlock]   (returns 2: mutex held)
#   trap 'txn_on_exit' EXIT
#   ...stage files under "$TXN_STAGE/<rel>"...
#   TXN_APPLYING=1; txn_move_in <rel>; ...; txn_commit_file <tmp> <rel>
#   txn_end
#
# Fault injection for tests: set TXN_FAIL_VAR to the name of an env var (e.g.
# SCAFFOLD_FAIL_AFTER); when that var holds N, the (N+1)th change fails.
# Bash 3.2 compatible.
# ============================================================================

TXN_ROOT=""; TXN_TMP=""; TXN_MUTEX=""; TXN_W=""; TXN_STAGE=""; TXN_BACKUP=""
TXN_JOURNAL=""; TXN_APPLYING=0; TXN_N=0; TXN_ACTIVE=0; TXN_CREATED_DIRS=""
TXN_FAIL_VAR="${TXN_FAIL_VAR:-}"

# txn_begin <root> <tmp_rel> <name> [force_unlock]
txn_begin() {
  local root="$1" tmp_rel="$2" name="$3" force_unlock="${4:-0}" d rel="" part rest
  TXN_ROOT="$root"
  TXN_TMP="$root/$tmp_rel"
  TXN_MUTEX="$TXN_TMP/$name.lock.d"

  # Remember which components of the tmp path this run creates so cleanup can
  # remove exactly those (e.g. a .claude/ that did not exist before).
  TXN_CREATED_DIRS=""
  rest="$tmp_rel"
  while [[ -n "$rest" ]]; do
    part="${rest%%/*}"
    rel="${rel:+$rel/}$part"
    d="$root/$rel"
    if [[ ! -d "$d" ]]; then
      mkdir "$d" || return 2
      TXN_CREATED_DIRS="$d
$TXN_CREATED_DIRS"
    fi
    [[ "$rest" == */* ]] || break
    rest="${rest#*/}"
  done

  if ! mkdir "$TXN_MUTEX" 2>/dev/null; then
    if [[ "$force_unlock" == 1 ]]; then
      rm -rf "$TXN_MUTEX" && mkdir "$TXN_MUTEX" || return 2
    else
      echo "[FAIL] another run holds ${TXN_MUTEX#"$root"/} ($(cat "$TXN_MUTEX/owner" 2>/dev/null || echo unknown))." >&2
      echo "       If it crashed, re-run with --force-unlock." >&2
      txn_rmdirs_created
      return 2
    fi
  fi
  printf 'pid=%s host=%s\n' "$$" "$(hostname 2>/dev/null || echo ?)" > "$TXN_MUTEX/owner"

  TXN_W="$TXN_TMP/work.$$"
  TXN_STAGE="$TXN_W/stage"
  TXN_BACKUP="$TXN_W/backup"
  TXN_JOURNAL="$TXN_W/journal.tsv"
  rm -rf "$TXN_W"
  mkdir -p "$TXN_STAGE" "$TXN_BACKUP" || return 2
  : > "$TXN_JOURNAL"
  TXN_APPLYING=0
  TXN_N=0
  TXN_ACTIVE=1
}

# txn_rmdirs_created — remove tmp-path directories this run created (if empty).
txn_rmdirs_created() {
  local d
  while IFS= read -r d; do
    [[ -n "$d" ]] && { rmdir "$d" 2>/dev/null || true; }
  done <<< "$TXN_CREATED_DIRS"
  return 0
}

# txn_fault_point — test hook; fails the (N+1)th change when ${!TXN_FAIL_VAR}=N.
txn_fault_point() {
  [[ -n "$TXN_FAIL_VAR" ]] || return 0
  local limit="${!TXN_FAIL_VAR:-}"
  if [[ -n "$limit" && $TXN_N -ge $limit ]]; then
    echo "[FAIL] ${TXN_FAIL_VAR}=${limit} (test fault injection)" >&2
    return 1
  fi
}

# txn_mkdirs <rel_dir> — create each missing component, journaling each one.
txn_mkdirs() {
  local rest="$1" rel="" part
  [[ -z "$rest" || "$rest" == "." ]] && return 0
  while :; do
    part="${rest%%/*}"
    rel="${rel:+$rel/}$part"
    if [[ ! -d "$TXN_ROOT/$rel" ]]; then
      printf 'rmdir\t%s\n' "$rel" >> "$TXN_JOURNAL"
      mkdir "$TXN_ROOT/$rel" || return 1
    fi
    [[ "$rest" == */* ]] || break
    rest="${rest#*/}"
  done
}

# _txn_prepare <rel> — fault point, parent dirs, then back up or mark new.
_txn_prepare() {
  local p="$1" d
  txn_fault_point || return 1
  d="${p%/*}"; [[ "$d" == "$p" ]] && d=""
  txn_mkdirs "$d" || return 1
  if [[ -e "$TXN_ROOT/$p" ]]; then
    mkdir -p "$(dirname "$TXN_BACKUP/$p")" || return 1
    cp -p "$TXN_ROOT/$p" "$TXN_BACKUP/$p" || return 1
    printf 'restore\t%s\n' "$p" >> "$TXN_JOURNAL"
  else
    printf 'delete\t%s\n' "$p" >> "$TXN_JOURNAL"
  fi
}

# txn_move_in <rel> — move $TXN_STAGE/<rel> into place.
txn_move_in() {
  _txn_prepare "$1" || return 1
  mv -f "$TXN_STAGE/$1" "$TXN_ROOT/$1" || return 1
  TXN_N=$((TXN_N + 1))
}

# txn_copy_in <abs_src> <rel> — copy a file into place (backups, restores).
txn_copy_in() {
  _txn_prepare "$2" || return 1
  cp -p "$1" "$TXN_ROOT/$2" || return 1
  TXN_N=$((TXN_N + 1))
}

# txn_remove <rel> — delete a file, keeping a copy for rollback.
txn_remove() {
  _txn_prepare "$1" || return 1
  rm -f "$TXN_ROOT/$1" || return 1
  TXN_N=$((TXN_N + 1))
}

# txn_commit_file <abs_tmp> <rel> — atomic rename of the commit record.
txn_commit_file() {
  _txn_prepare "$2" || return 1
  mv -f "$1" "$TXN_ROOT/$2" || return 1
  TXN_N=$((TXN_N + 1))
}

# txn_rollback — replay the journal in reverse. Returns 1 if incomplete.
txn_rollback() {
  local act path ok=0
  while IFS=$'\t' read -r act path; do
    case "$act" in
      restore) mkdir -p "$(dirname "$TXN_ROOT/$path")" && cp -p "$TXN_BACKUP/$path" "$TXN_ROOT/$path" || ok=1 ;;
      delete)  rm -f "$TXN_ROOT/$path" || ok=1 ;;
      rmdir)   rmdir "$TXN_ROOT/$path" 2>/dev/null || true ;;
    esac
  done < <(awk '{ l[NR] = $0 } END { for (i = NR; i >= 1; i--) print l[i] }' "$TXN_JOURNAL")
  [[ $ok -eq 0 ]] && TXN_APPLYING=0
  return $ok
}

# txn_end — success path: drop work files, mutex and created tmp dirs.
txn_end() {
  TXN_APPLYING=0
  [[ $TXN_ACTIVE -eq 1 ]] || return 0
  rm -rf "$TXN_W" "$TXN_MUTEX"
  rmdir "$TXN_TMP" 2>/dev/null || true
  txn_rmdirs_created
  TXN_ACTIVE=0
}

# txn_on_exit [rc] — EXIT-trap helper. Rolls back an interrupted apply and
# always releases the mutex. Returns the exit code the caller should use:
# 2 after a rollback (or when one is incomplete), otherwise rc.
txn_on_exit() {
  local rc="${1:-0}"
  [[ $TXN_ACTIVE -eq 1 ]] || return "$rc"
  if [[ $TXN_APPLYING -eq 1 ]]; then
    echo "[FAIL] failed mid-apply — rolling back" >&2
    if ! txn_rollback; then
      echo "[FAIL] ROLLBACK INCOMPLETE — inspect ${TXN_W} (kept for recovery)" >&2
      rm -rf "$TXN_MUTEX"
      TXN_ACTIVE=0
      return 2
    fi
    echo "[OK] rollback complete — target is unchanged" >&2
    rc=2
  fi
  rm -rf "$TXN_W" "$TXN_MUTEX"
  rmdir "$TXN_TMP" 2>/dev/null || true
  txn_rmdirs_created
  TXN_ACTIVE=0
  return "$rc"
}
