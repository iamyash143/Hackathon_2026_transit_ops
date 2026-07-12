#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
NODE_BIN="${NODE_BIN:-npm}"

cd "$ROOT_DIR"

if [[ ! -f ".env" ]]; then
  if [[ -f ".env.example" ]]; then
    cp ".env.example" ".env"
    printf 'Created .env from .env.example\n'
  else
    printf 'Missing .env.example; cannot bootstrap .env\n' >&2
    exit 1
  fi
fi

if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
  printf 'Created virtualenv at %s\n' "$VENV_DIR"
fi

if [[ -x "$VENV_DIR/bin/python" ]]; then
  PYTHON="$VENV_DIR/bin/python"
else
  printf 'Missing Python interpreter inside %s\n' "$VENV_DIR" >&2
  exit 1
fi

"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r requirements.txt

if [[ -f "package.json" ]]; then
  "$NODE_BIN" install
fi

"$PYTHON" manage.py migrate --noinput
"$PYTHON" manage.py seed_groups

printf 'Setup complete. Start the app with:\n'
printf '  %s manage.py runserver\n' "$PYTHON"
printf '  %s run dev\n' "$NODE_BIN"
