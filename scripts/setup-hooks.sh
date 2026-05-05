#!/usr/bin/env bash
set -euo pipefail

pip install pre-commit detect-secrets
detect-secrets scan > .secrets.baseline
pre-commit install
pre-commit run --all-files || true
