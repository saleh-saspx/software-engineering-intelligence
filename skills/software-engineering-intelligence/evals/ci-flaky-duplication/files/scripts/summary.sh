#!/usr/bin/env bash
# Prints the pass rate shown on the PR.
total=$(grep -ho '<testcase ' "$@" | wc -l)
failed=$(grep -ho '<failure' "$@" | wc -l)
passed=$((total - failed))
echo "pass rate: $((100 * passed / total))%"
