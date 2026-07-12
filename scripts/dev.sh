#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-transit_project.settings.local}"

cd "$ROOT_DIR"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  printf 'Missing virtualenv at %s. Run scripts/setup.sh first.\n' "$VENV_DIR" >&2
  exit 1
fi

if [[ ! -f "package.json" ]]; then
  printf 'Missing package.json; cannot start Tailwind watcher.\n' >&2
  exit 1
fi

TAILWIND_PID=""

cleanup() {
  if [[ -n "$TAILWIND_PID" ]] && kill -0 "$TAILWIND_PID" 2>/dev/null; then
    kill "$TAILWIND_PID" 2>/dev/null || true
    wait "$TAILWIND_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

npm run dev &
TAILWIND_PID=$!

env DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS_MODULE" "$VENV_DIR/bin/python" manage.py runserver "$HOST:$PORT"
