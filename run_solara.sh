#!/bin/bash
set -euo pipefail

SOLARA_FILE="app.py"
PORT="8769"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)
      PORT="$2"
      shift 2
      ;;
    --port=*)
      PORT="${1#--port=}"
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [filename] [--port PORT]"
      exit 0
      ;;
    *)
      SOLARA_FILE="$1"
      shift
      ;;
  esac
done

if [[ -f .env ]]; then
  while IFS= read -r line; do
    [[ $line =~ ^#.*$ || -z $line ]] && continue
    if [[ $line =~ ^([^=]+)=(.*)$ ]]; then
      name="${BASH_REMATCH[1]}"
      value="${BASH_REMATCH[2]}"
      value="${value#\'}"
      value="${value%\'}"
      value="${value#\"}"
      value="${value%\"}"
      export "$name=$value"
    fi
  done < .env
fi

solara run "$SOLARA_FILE" --port "$PORT" --no-open
