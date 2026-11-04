#!/usr/bin/env bash
set -eu
cp -R "$(dirname "$0")/files/." .
bash "$(dirname "$0")/make_history.sh" .
