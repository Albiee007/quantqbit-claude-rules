#!/usr/bin/env bash
# === application scaffold tests ===
# Renders the platform starters and exercises the transaction around them:
# conflicts, --force backups, uninstall/restore, locking, symlinks and fault
# injection (every failure must leave the project byte-identical).
# Portable: Linux, macOS (incl. /bin/bash 3.2), Windows Git Bash.
# Usage: bash tests/scaffold.test.sh
#   SCAFFOLD_PLATFORM="backend mobile"  platforms for the per-platform pass
#   SCAFFOLD_BUILD=1                    also install/lint/test/build the JS starters
#   SCAFFOLD_QUICK=1                    trimmed fault matrix (slow shells)
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INIT="$ROOT/scaffold/init-scaffold.sh"
source "$ROOT/harness/bin/harness-lib.sh"
source "$ROOT/scaffold/lib/manifest.sh"
set +e  # manifest.sh enables errexit; this suite counts failures instead
W="$(mktemp -d "${TMPDIR:-/tmp}/qqr-scaffold-test.XXXXXX")"
trap 'rm -rf "$W"' EXIT
MANIFEST=".claude/.scaffold-manifest-scaffold.txt"
pass=0; fail=0
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) msys=1 ;; *) msys=0 ;; esac

ok()    { pass=$((pass + 1)); printf '  [OK] %s\n' "$*"; }
bad()   { fail=$((fail + 1)); printf '  [FAIL] %s\n' "$*"; }
check() { local d="$1"; shift; if "$@"; then ok "$d"; else bad "$d"; return 1; fi; }

# tree_sum <dir> [exclude-top-level-name] — every directory and file (with
# contents) under dir; empty string for a missing dir.
tree_sum() {
  [[ -d "$1" ]] || { printf 'missing'; return; }
  hc_py - "$1" "${2:-}" <<'PY'
import hashlib, os, sys
from pathlib import Path
root, skip = Path(sys.argv[1]), sys.argv[2]
digest = hashlib.sha256()
rows = []
for directory, dirs, names in os.walk(root):
    rel_dir = Path(directory).relative_to(root)
    if skip and rel_dir == Path('.'):
        dirs[:] = [d for d in dirs if d != skip]
    for d in dirs:
        rows.append(('d', (rel_dir / d).as_posix(), b''))
    for n in names:
        p = Path(directory) / n
        rows.append(('f', (rel_dir / n).as_posix(), p.read_bytes()))
for kind, rel, data in sorted(rows, key=lambda r: r[1]):
    digest.update(kind.encode() + b'\0' + rel.encode('utf-8') + b'\0' + hashlib.sha256(data).digest())
print(digest.hexdigest())
PY
}

stamp() { # <target> <log name> [args...] — backend unless --platform given
  local target="$1" log="$2"; shift 2
  local platform="--platform=backend"
  case " $* " in *" --platform="*) platform="" ;; esac
  # shellcheck disable=SC2086
  "$BASH" "$INIT" $platform --target="$target" --project-name=Regression \
    --android-package=com.example.regression --non-interactive "$@" > "$W/$log.log" 2>&1
}
uninstall() { "$BASH" "$INIT" --uninstall --target="$1" "${@:2}" > "$W/uninstall.log" 2>&1; }
no_txn_leftovers() { [[ ! -e "$1/.claude/.scaffold-tmp" ]]; }
manifest_hashes_match() { # every file row's hash matches the file on disk
  local t="$1" hash rel origin backup
  while IFS=$'\t' read -r hash rel origin backup; do
    [[ -z "$rel" || "$origin" == dir ]] && continue
    [[ -f "$t/$rel" && "$(manifest_hash "$t/$rel")" == "$hash" ]] || { echo "    mismatch: $rel"; return 1; }
  done < <(manifest_rows "$t/$MANIFEST")
}

echo "1. fresh stamp per platform (README kept, --src-dir, manifest, scripts executable)"
for platform in ${SCAFFOLD_PLATFORM:-backend frontend mobile android}; do
  T="$W/$platform"; mkdir -p "$T"
  printf 'project documentation\n' > "$T/README.md"
  stamp "$T" "$platform" --platform="$platform" --src-dir=source --features=users --with-auth --with-i18n
  check "$platform: exits 0" test $? -eq 0 || cat "$W/$platform.log"
  check "$platform: README.md kept" grep -qx 'project documentation' "$T/README.md"
  check "$platform: manifest hashes match the files" manifest_hashes_match "$T"
  check "$platform: no staging or lock left behind" no_txn_leftovers "$T"
  if [[ "$platform" != android ]]; then
    check "$platform: sources under source/, none under src/" test -d "$T/source" -a ! -d "$T/src"
  fi
  if [[ $msys -eq 0 ]]; then
    check "$platform: scripts/check-file-size.sh is executable" test -x "$T/scripts/check-file-size.sh"
  fi
  if [[ "${SCAFFOLD_BUILD:-0}" == 1 && "$platform" != android ]]; then
    (
      set -e  # every step must pass, not just the last one
      cd "$T"
      npm install --no-audit --no-fund
      npm run lint
      if [[ "$platform" == frontend ]]; then npm test; else npm test -- --runInBand; fi
      if [[ "$platform" != mobile ]]; then npm run build; fi
      if [[ "$platform" == mobile ]]; then
        # SDK consistency, Metro bundles for both platforms, and native project
        # generation (no native toolchain needed).
        export EXPO_NO_TELEMETRY=1 CI=1
        npm run doctor
        npx expo export --platform android --output-dir "$W/export-android"
        npx expo export --platform ios --output-dir "$W/export-ios"
        npm run native:prebuild -- --platform android --clean
        grep -q "applicationId 'com.example.regression'" android/app/build.gradle
        npm run native:prebuild -- --platform ios --clean
        grep -q 'PRODUCT_BUNDLE_IDENTIFIER = "com.example.regression"' ios/*.xcodeproj/project.pbxproj
      fi
    ) > "$W/build.log" 2>&1
    check "$platform: install, lint, test, build" test $? -eq 0 || tail -40 "$W/build.log"
  fi
done

echo "2. files in the way: refused, nothing written"
T="$W/conflict"; mkdir -p "$T"
printf '{"name":"mine"}\n' > "$T/package.json"; printf 'FROM scratch\n' > "$T/Dockerfile"
before="$(tree_sum "$T")"
stamp "$T" conflict; check "exits 1" test $? -eq 1
check "lists package.json" grep -q 'exists:  package.json' "$W/conflict.log"
check "lists Dockerfile" grep -q 'exists:  Dockerfile' "$W/conflict.log"
check "tree unchanged, no .claude/ created" test "$(tree_sum "$T")" = "$before"

echo "3. --force: originals backed up and recorded; uninstall restores them"
T="$W/force"; mkdir -p "$T"
printf '{"name":"mine"}\n' > "$T/package.json"; printf 'my readme\n' > "$T/README.md"
before="$(tree_sum "$T")"
stamp "$T" force --force; check "exits 0" test $? -eq 0
check "package.json replaced" grep -q '"scripts"' "$T/package.json"
check "original in .claude.bak/" grep -qx '{"name":"mine"}' "$T"/.claude.bak/*/package.json
check "manifest records overwritten + backup" grep -qE $'\tpackage.json\toverwritten\t\\.claude\\.bak/[^\t]+/package.json$' "$T/$MANIFEST"
stamp "$T" restamp --force; check "--force re-stamp exits 0" test $? -eq 0
check "re-stamp keeps the original backup reference" grep -qE $'\tpackage.json\toverwritten\t\\.claude\\.bak/' "$T/$MANIFEST"
uninstall "$T"; check "uninstall exits 0" test $? -eq 0
check "tree restored (apart from .claude.bak/)" test "$(tree_sum "$T" .claude.bak)" = "$before"

echo "4. stamp + uninstall on a clean project leaves it as it was"
T="$W/roundtrip"; mkdir -p "$T"; printf 'x\n' > "$T/notes.txt"
before="$(tree_sum "$T")"
stamp "$T" roundtrip --features=users,orders --with-auth; check "stamp exits 0" test $? -eq 0
stamp "$T" rerun; check "re-run without --force refused (1)" test $? -eq 1
check "refusal names the manifest" grep -q 'already scaffolded' "$W/rerun.log"
uninstall "$T"; check "uninstall exits 0" test $? -eq 0
check "tree identical to before" test "$(tree_sum "$T")" = "$before"

echo "5. uninstall keeps files edited since stamping"
T="$W/edited"; mkdir -p "$T"
stamp "$T" edited
n_files=$(grep -c $'\tcreated\t' "$T/$MANIFEST")   # files in a default stamp (fault matrix)
printf '// mine\n' >> "$T/src/app.ts"
uninstall "$T"; check "uninstall exits 0" test $? -eq 0
check "edited file kept" grep -q '// mine' "$T/src/app.ts"
check "untouched files removed" test ! -e "$T/package.json"

echo "6. faults: every failure leaves the project byte-identical"
faults="AFTER=0 AFTER=1 AFTER=$((n_files / 2)) AFTER=$((n_files - 1)) AT=stage AT=validate AT=backup AT=manifest"
[[ "${SCAFFOLD_QUICK:-0}" == 1 ]] && faults="AFTER=1 AT=manifest"
for kind in fresh force missing; do
  for f in $faults; do
    T="$W/fault-$kind-${f//=/-}"
    case "$kind" in
      fresh)   mkdir -p "$T"; printf 'x\n' > "$T/notes.txt" ;;
      force)   mkdir -p "$T"; printf '{"name":"mine"}\n' > "$T/package.json" ;;
      missing) ;;
    esac
    before="$(tree_sum "$T")"
    extra=""; [[ "$kind" == force ]] && extra="--force"
    # shellcheck disable=SC2086
    env "SCAFFOLD_FAIL_${f%%=*}=${f#*=}" "$BASH" "$INIT" --platform=backend --target="$T" \
      --project-name=Regression --non-interactive $extra > "$W/fault.log" 2>&1
    rc=$?
    if [[ $rc -eq 2 && "$(tree_sum "$T")" == "$before" ]]; then
      ok "$kind target, SCAFFOLD_FAIL_$f: exit 2, unchanged"
    else
      bad "$kind target, SCAFFOLD_FAIL_$f: exit $rc, tree $( [[ "$(tree_sum "$T")" == "$before" ]] && echo same || echo CHANGED)"
      tail -5 "$W/fault.log"
    fi
  done
done
T="$W/uninstall-fault"; mkdir -p "$T"; stamp "$T" ufault
before="$(tree_sum "$T")"
SCAFFOLD_FAIL_AFTER=10 "$BASH" "$INIT" --uninstall --target="$T" > "$W/ufault2.log" 2>&1
check "uninstall fault: exit 2" test $? -eq 2
check "uninstall fault: project unchanged" test "$(tree_sum "$T")" = "$before"

echo "7. lock: a second run is refused; --force-unlock clears a stale lock"
T="$W/locked"; mkdir -p "$T/.claude/.scaffold-tmp/scaffold.lock.d"
stamp "$T" locked; check "locked run exits 2" test $? -eq 2
check "message names the lock" grep -q 'force-unlock' "$W/locked.log"
stamp "$T" unlocked --force-unlock; check "--force-unlock run exits 0" test $? -eq 0
check "lock released" no_txn_leftovers "$T"

echo "8. rejected input writes nothing"
stamp "$W/dup" dup --features=users,Users; check "duplicate feature refused (1)" test $? -eq 1
stamp "$W/example" example --features=health; check "feature named like the example refused (1)" test $? -eq 1
stamp "$W/mobile-example" mexample --platform=mobile --features=home; check "mobile 'home' refused (1)" test $? -eq 1
stamp "$W/invalid" invalid --src-dir=../outside; check "unsafe --src-dir refused (1)" test $? -eq 1
check "no target directories created" test ! -e "$W/dup" -a ! -e "$W/example" -a ! -e "$W/invalid" -a ! -e "$W/outside"
stamp "$W/dry" dry --dry-run; check "--dry-run exits 0" test $? -eq 0
check "--dry-run lists the files" grep -q 'ADD .*package.json' "$W/dry.log"
check "--dry-run creates nothing" test ! -e "$W/dry"

if [[ $msys -eq 0 ]]; then
  echo "9. a symlinked directory in the project is refused"
  T="$W/symlink"; mkdir -p "$T" "$W/outside-src"; ln -s "$W/outside-src" "$T/source"
  stamp "$T" symlink --src-dir=source; check "exits 1" test $? -eq 1
  check "reported as unsafe" grep -q 'unsafe:' "$W/symlink.log"
  check "symlink target untouched" test -z "$(ls -A "$W/outside-src")"
fi

printf '\nscaffold tests: %d passed, %d failed\n' "$pass" "$fail"
[[ $fail -eq 0 ]]
