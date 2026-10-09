#!/usr/bin/env bash
set -euo pipefail
mkdir -p test-results
rom="pokeyellow.gbc"
test -s "$rom" || { echo "Missing built $rom" >&2; exit 1; }
{
  echo "PROJECT YELLOW BASELINE — SOURCE ONLY"
  printf 'git_commit=%s\n' "$(git rev-parse HEAD)"
  printf 'rom_filename=%s\n' "$rom"
  printf 'rom_bytes=%s\n' "$(wc -c < "$rom" | tr -d ' ')"
  printf 'rom_sha256=%s\n' "$(sha256sum "$rom" | awk '{print $1}')"
  printf 'rgbasm=%s\n' "$(rgbasm --version | head -1)"
  echo "status=CLEAN_BUILD_PASS"
  echo "emulator_status=NOT_TESTED"
} > test-results/baseline.txt
cat test-results/baseline.txt
