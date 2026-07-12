#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

rm -rf \
  .venv \
  django-venv \
  node_modules \
  __pycache__ \
  */__pycache__ \
  */*/__pycache__ \
  .idea \
  staticfiles \
  media

find . -type f \( \
  -name '*.pyc' -o \
  -name '*.pyo' -o \
  -name '*.sqlite3' -o \
  -name 'db.sqlite3' -o \
  -name 'db 2.sqlite3' -o \
  -name '* 2.py' -o \
  -name '* 3.py' -o \
  -name '* 2.txt' -o \
  -name '* 3.txt' -o \
  -name '* 2.pdf' -o \
  -name '* 2.json' -o \
  -name '* 3.json' \
\) -delete

printf 'Workspace cleanup complete.\n'
