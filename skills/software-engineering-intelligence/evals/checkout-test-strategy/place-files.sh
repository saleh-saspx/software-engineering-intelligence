#!/usr/bin/env bash
set -eu
cp -R "$(dirname "$0")/files/." .
# The fixture stores its GitHub Actions workflow outside .github/ (some sync tools refuse to write
# CI workflow files); put it where the project expects it.
mkdir -p .github/workflows
mv ci-workflow.yml .github/workflows/ci.yml
