#!/usr/bin/env bash
# run_daily.sh - Daily Assistant Batch Runner for OCI VM (or Local Mac)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs"
mkdir -p "${LOG_DIR}"

# Prune daily assistant logs older than 30 days.
find "${LOG_DIR}" -maxdepth 1 -type f -name 'daily_*.log' -mtime +30 -delete 2>/dev/null || true

LOG_FILE="${LOG_DIR}/daily_$(date +'%Y-%m-%d').log"
exec >> "${LOG_FILE}" 2>&1

echo "=================================================="
echo "Daily Assistant Run Started at $(date)"
echo "=================================================="

# Run the Python orchestrator (handles consolidated LiveSync pre-pull & post-push batches)
if [ -f "${SCRIPT_DIR}/venv/bin/python3" ]; then
    PYTHON_BIN="${SCRIPT_DIR}/venv/bin/python3"
else
    PYTHON_BIN="$(which python3)"
fi

echo "Executing daily orchestrator using ${PYTHON_BIN}..."
"${PYTHON_BIN}" "${SCRIPT_DIR}/daily_orchestrator.py" "$@"

echo "Daily Assistant Run Completed Successfully at $(date)"
echo "=================================================="
