#!/usr/bin/env bash
# Builds the Lambda layer WITHOUT Docker.
# pip downloads ready-made Linux (manylinux x86_64) wheels for Python 3.12,
# so this works on macOS, Linux and WSL. Windows: use build_layer.ps1.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf layer/build
mkdir -p layer/build/python
python3 -m pip install \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.12 \
  --only-binary=:all: \
  --target layer/build/python \
  -r layer/requirements.txt
echo "Layer built in layer/build/python ($(du -sh layer/build | cut -f1))"
