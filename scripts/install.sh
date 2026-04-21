#!/usr/bin/env bash
# Curl-one-liner target for Scriptorium v0.3.
# The stable flow is `scriptorium init`; this script is a cuttable wrapper.

set -euo pipefail

if command -v uv >/dev/null 2>&1; then
  uv pip install scriptorium-cli
else
  pip install scriptorium-cli
fi

scriptorium --version

scriptorium init "$@"
