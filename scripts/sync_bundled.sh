#!/usr/bin/env bash
# Refresh the bundled copies of the tools and REFramework scripts from their own repos.
# Usage: scripts/sync_bundled.sh <path-to-tools-repo> <path-to-mods-repo>
set -euo pipefail
TOOLS=${1:?path to shotokan-sf6/tools checkout}; MODS=${2:?path to shotokan-sf6/mods checkout}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
rm -rf "$ROOT/tools" "$ROOT/mods"; mkdir -p "$ROOT/tools" "$ROOT/mods"
cp "$TOOLS"/tools/*.py "$TOOLS"/tools/base_damage.json "$TOOLS"/tools/.env.example "$ROOT/tools/"
cp -r "$TOOLS/batch" "$ROOT/tools/batch"; rm -f "$ROOT/tools/batch/.env"; rm -rf "$ROOT/tools/batch/__pycache__"
cp -r "$MODS/autorun" "$MODS/data" "$ROOT/mods/"
echo "tools: $(git -C "$TOOLS" log --oneline -1)"; echo "mods:  $(git -C "$MODS" log --oneline -1)"
