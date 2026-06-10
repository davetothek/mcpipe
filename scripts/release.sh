#!/usr/bin/env bash
# Release workflow using commitizen.
#
# Usage:
#   uv run poe release              # auto-detect bump from commits
#   bash scripts/release.sh patch   # force patch bump
#   bash scripts/release.sh minor   # force minor bump
#   bash scripts/release.sh major   # force major bump

set -euo pipefail

INCREMENT="${1:-}"

echo "Running pre-release checks..."
uv run poe check

echo ""
echo "Bumping version..."

if [[ -n "$INCREMENT" ]]; then
  uv run cz bump --increment "$INCREMENT" --yes
else
  uv run cz bump --yes
fi

TAG=$(git describe --tags --abbrev=0)
echo ""
echo "Pushing commit and tag..."
git push origin HEAD
git push origin "$TAG"

echo ""
echo "✅ Released $TAG"
echo "   GitHub Actions will create a release and publish to PyPI."

# vim: set ft=sh ts=2 sw=2:
