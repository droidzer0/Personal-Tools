#!/usr/bin/env bash
# run_daily.sh - Daily Assistant Batch Runner for OCI VM (or Local Mac)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs"
mkdir -p "${LOG_DIR}"

LOG_FILE="${LOG_DIR}/daily_$(date +'%Y-%m-%d').log"
exec >> "${LOG_FILE}" 2>&1

echo "=================================================="
echo "Daily Assistant Run Started at $(date)"
echo "=================================================="

# Optional: If running on OCI with livesync-cli, pull latest updates from CouchDB
if command -v livesync-cli &> /dev/null; then
    echo "Syncing latest notes from CouchDB via livesync-cli..."
    livesync-cli sync || true
fi

# Run the Python orchestrator
if [ -f "${SCRIPT_DIR}/venv/bin/python3" ]; then
    PYTHON_BIN="${SCRIPT_DIR}/venv/bin/python3"
else
    PYTHON_BIN="$(which python3)"
fi

echo "Executing daily orchestrator using ${PYTHON_BIN}..."
"${PYTHON_BIN}" "${SCRIPT_DIR}/daily_orchestrator.py"

# Optional: Push newly created note back into CouchDB
if command -v livesync-cli &> /dev/null; then
    echo "Pushing newly created note to CouchDB via livesync-cli..."
    livesync-cli sync || true
fi

echo "Daily Assistant Run Completed Successfully at $(date)"
echo "=================================================="
