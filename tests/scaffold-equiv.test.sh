#!/usr/bin/env bash
# === scaffold renderer equivalence (golden) test ===
# Renders every platform across a matrix of flags with a BASELINE copy of
# scaffold/ (extracted from git) and with the working tree, then compares
# fingerprints of the two output trees. Use it to prove that a renderer
# refactor changes no generated output. Template changes are expected to
# differ, so this is a refactor tool, not a permanent CI gate.
#
# Usage: SCAFFOLD_EQUIV_BASE=<git ref, default HEAD> bash tests/scaffold-equiv.test.sh
#        SCAFFOLD_PLATFORM="backend mobile" limits the platforms.
#        SCAFFOLD_EQUIV_SKIP_MANIFEST=1 ignores the manifest (format changes).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_REF="${SCAFFOLD_EQUIV_BASE:-HEAD}"
source "$ROOT/harness/bin/harness-lib.sh"
W="$(mktemp -d "${TMPDIR:-/tmp}/qqr-scaffold-equiv.XXXXXX")"
trap 'rm -rf "$W"' EXIT
pass=0; fail=0

ok()  { pass=$((pass + 1)); printf '  [OK] %s\n' "$*"; }
bad() { fail=$((fail + 1)); printf '  [FAIL] %s\n' "$*"; }

# Both sides come out of `git archive`, so checkout line-ending conversion is
# identical. The working tree (including untracked files) is snapshotted
# through a throwaway index; the real index is untouched.
mkdir -p "$W/base" "$W/work"
work_tree="$(GIT_INDEX_FILE="$W/index" sh -c \
  'git -C "$1" read-tree HEAD && git -C "$1" add -A scaffold 2>/dev/null && git -C "$1" write-tree' _ "$ROOT")" \
  || { echo "[FAIL] cannot snapshot the working tree" >&2; exit 2; }
if ! git -C "$ROOT" archive "$BASE_REF" scaffold | tar -x -C "$W/base" \
   || ! git -C "$ROOT" archive "$work_tree" scaffold | tar -x -C "$W/work"; then
  echo "[FAIL] cannot extract scaffold/ from ${BASE_REF} or the working tree" >&2; exit 2
fi

# Fingerprint: one row per directory and file. Backup timestamps and the
# manifest's Stamped line are normalised; manifest rows are sorted.
fingerprint() {
  hc_py - "$1" <<'PY'
import hashlib, os, re, sys
from pathlib import Path
root = Path(sys.argv[1])
check_exec = os.name != 'nt' and not sys.platform.startswith(('msys', 'cygwin'))
norm = lambda rel: re.sub(r'^\.claude\.bak/[^/]+', '.claude.bak/TS', rel)
rows = []
for directory, dirs, names in os.walk(root):
    for d in dirs:
        rows.append('d ' + norm((Path(directory) / d).relative_to(root).as_posix()))
    for name in names:
        path = Path(directory) / name
        rel = norm(path.relative_to(root).as_posix())
        data = path.read_bytes()
        if rel.endswith('.claude/.scaffold-manifest-scaffold.txt') and os.environ.get('SCAFFOLD_EQUIV_SKIP_MANIFEST') == '1':
            continue
        if rel.endswith('.claude/.scaffold-manifest-scaffold.txt'):
            lines = data.decode('utf-8').splitlines()
            head = [l for l in lines if l.startswith('#') and not l.startswith('# Stamped:')]
            body = sorted(re.sub(r'\.claude\.bak/[^/\t]+/', '.claude.bak/TS/', l)
                          for l in lines if l and not l.startswith('#'))
            data = '\n'.join(head + body).encode('utf-8')
        mode = ('x' if os.access(path, os.X_OK) else '-') if check_exec else '?'
        rows.append('f %s %s %s' % (rel, mode, hashlib.sha256(data).hexdigest()))
print('\n'.join(sorted(rows)))
PY
}

# seed <dir> <case>: pre-existing project files for a scenario.
seed() {
  local dir="$1" case="$2" platform="$3"
  mkdir -p "$dir"
  case "$case" in
    existing) printf 'project documentation\n' > "$dir/README.md"
              printf '# my rules\n' > "$dir/CLAUDE.md" ;;
    agents)   printf '# agents\n' > "$dir/AGENTS.md" ;;
    force)    printf 'project documentation\n' > "$dir/README.md"
              if [[ "$platform" == android ]]; then printf '// mine\n' > "$dir/build.gradle.kts"
              else printf '{"name":"mine"}\n' > "$dir/package.json"; fi ;;
  esac
}

# args_for <case> <platform>: extra CLI flags for a scenario.
args_for() {
  local pkg="--android-package=com.example.golden"
  case "$1" in
    defaults|existing|agents) echo "$pkg" ;;
    full)    echo "$pkg --src-dir=source --features=users,orders --with-auth --with-i18n --api-version=v2" ;;
    nested)  echo "$pkg --src-dir=packages/app" ;;
    force)   echo "$pkg --force --features=users" ;;
    collide) if [[ "$2" == mobile ]]; then echo "--features=home"; else echo "--features=health"; fi ;;
    package) echo "--android-package=com.acme.golden.app" ;;
  esac
}

render() { # <scaffold dir> <target> <platform> <case>
  local extra; extra="$(args_for "$4" "$3")"
  # shellcheck disable=SC2086
  "$BASH" "$1/init-scaffold.sh" --platform="$3" --target="$2" --project-name=Golden \
    --non-interactive $extra > "$2.log" 2>&1
}

# run_case <platform> <case>: render both sides, write a one-line verdict.
run_case() {
  local platform="$1" c="$2" old new rc_old rc_new
  old="$W/out/$platform-$c-base"; new="$W/out/$platform-$c-work"
  seed "$old" "$c" "$platform"; seed "$new" "$c" "$platform"
  render "$W/base/scaffold" "$old" "$platform" "$c"; rc_old=$?
  render "$W/work/scaffold" "$new" "$platform" "$c"; rc_new=$?
  # A feature named like the built-in example is refused (exit 1) since the
  # transactional scaffolder; every other case must succeed.
  local expect=0
  [[ "$c" == collide ]] && expect=1
  if [[ $rc_old -ne $expect || $rc_new -ne $expect ]]; then
    { echo "FAIL $platform/$c: exit ${rc_old} (base) / ${rc_new} (work), expected ${expect}"
      tail -3 "$old.log"; tail -3 "$new.log"; } > "$new.verdict"
    return
  fi
  fingerprint "$old" > "$old.fp"; fingerprint "$new" > "$new.fp"
  if cmp -s "$old.fp" "$new.fp"; then
    echo "OK $platform/$c identical ($(wc -l < "$new.fp" | tr -d ' ') entries)" > "$new.verdict"
  else
    { echo "FAIL $platform/$c differs"; diff "$old.fp" "$new.fp" | head -20; } > "$new.verdict"
  fi
}

echo "scaffold equivalence against ${BASE_REF} (bash ${BASH_VERSION}, ${SCAFFOLD_EQUIV_JOBS:-4} jobs)"
mkdir -p "$W/out"
jobs_max="${SCAFFOLD_EQUIV_JOBS:-4}"; running=0; case_ids=""
for platform in ${SCAFFOLD_PLATFORM:-backend frontend mobile android}; do
  cases="defaults full nested existing agents force"
  [[ "$platform" != android ]] && cases="$cases collide"
  [[ "$platform" == android ]] && cases="$cases package"
  for c in $cases; do
    case_ids="$case_ids $platform-$c"
    run_case "$platform" "$c" &
    running=$((running + 1))
    if [[ $running -ge $jobs_max ]]; then wait; running=0; fi
  done
done
wait

for id in $case_ids; do
  v="$W/out/$id-work.verdict"
  if [[ ! -f "$v" ]]; then bad "$id: no verdict"; continue; fi
  case "$(head -1 "$v")" in
    OK\ *) ok "$(head -1 "$v" | cut -c4-)" ;;
    *)     bad "$(head -1 "$v" | cut -c6-)"; tail -n +2 "$v" | sed 's/^/        /' ;;
  esac
done

printf '\n%d passed, %d failed\n' "$pass" "$fail"
[[ $fail -eq 0 ]]
