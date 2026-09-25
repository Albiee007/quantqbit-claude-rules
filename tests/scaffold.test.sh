#!/usr/bin/env bash
# Exercise actual renderers. Set SCAFFOLD_BUILD=1 for dependency/build checks.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
W="$(mktemp -d "${TMPDIR:-/tmp}/qqr-scaffold-test.XXXXXX")"
trap 'rm -rf "$W"' EXIT
for platform in ${SCAFFOLD_PLATFORM:-backend frontend mobile android}; do
  target="$W/$platform"
  mkdir -p "$target"
  printf 'project documentation\n' > "$target/README.md"
  bash "$ROOT/scaffold/init-scaffold.sh" --platform="$platform" --target="$target" \
    --project-name=Regression --src-dir=source --features=users --with-auth --with-i18n \
    --android-package=com.example.regression --non-interactive > "$W/render.log" 2>&1 || { cat "$W/render.log"; exit 1; }
  grep -qx 'project documentation' "$target/README.md"
  if [[ "$platform" != android ]]; then
    [[ -d "$target/source" && ! -d "$target/src" ]]
    if [[ "${SCAFFOLD_BUILD:-0}" == 1 ]]; then
      (
        cd "$target"
        npm install --no-audit --no-fund
        npm run lint
        if [[ "$platform" == frontend ]]; then npm test; else npm test -- --runInBand; fi
        if [[ "$platform" != mobile ]]; then npm run build; fi
      ) > "$W/build.log" 2>&1 || { cat "$W/build.log"; exit 1; }
    fi
  fi
  echo "[OK] $platform scaffold"
done
mkdir -p "$W/invalid"
if bash "$ROOT/scaffold/init-scaffold.sh" --platform=backend --target="$W/invalid" \
  --project-name=Regression --src-dir=../outside --non-interactive > "$W/invalid.log" 2>&1; then
  echo '[FAIL] unsafe source directory accepted'; exit 1
fi
[[ ! -e "$W/outside" && ! -e "$W/invalid/package.json" ]]
echo 'scaffold tests passed'
