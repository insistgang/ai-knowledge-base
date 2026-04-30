#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${AI_KB_PROJECT_DIR:-/home/insistgang/ai-knowledge-base}"
PYTHON_BIN="${AI_KB_PYTHON:-$PROJECT_DIR/.venv/bin/python}"
SOURCES="${AI_KB_SOURCES:-github}"
LIMIT="${AI_KB_LIMIT:-5}"
LOG_FILE="${AI_KB_LOG_FILE:-$PROJECT_DIR/logs/local-collect.log}"

cd "$PROJECT_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

{
  echo "==== $(date -Is) local collect start ===="

  if [[ -f ".env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source ".env"
    set +a
  fi

  if [[ ! -x "$PYTHON_BIN" ]]; then
    PYTHON_BIN="python3"
  fi

  if ! "$PYTHON_BIN" -c "import httpx, dotenv, yaml" >/dev/null 2>&1; then
    "$PYTHON_BIN" -m pip install -r requirements.txt
  fi

  args=(pipeline/pipeline.py --sources "$SOURCES" --limit "$LIMIT" --verbose)
  if [[ "${AI_KB_DRY_RUN:-0}" == "1" ]]; then
    args+=(--dry-run)
  fi

  "$PYTHON_BIN" "${args[@]}"
  "$PYTHON_BIN" hooks/validate_json.py knowledge/articles/*.json
  "$PYTHON_BIN" hooks/check_quality.py knowledge/articles/*.json

  echo "==== $(date -Is) local collect success ===="
} >> "$LOG_FILE" 2>&1
