#!/bin/bash
# Barrido resumible (salta tareas con done.json). Uso: ./run_all.sh [NPROC] [MAXEP] [datasets coma-separados]
cd "$(dirname "$0")"
NPROC=${1:-3}; MAXEP=${2:-400}; DS=${3:-b_red,b_green,b_blue}
echo "=== $(date) start NPROC=$NPROC MAXEP=$MAXEP DS=$DS" >> run_all.log
python3 -u iter_runner.py run "$NPROC" "$MAXEP" "$DS" >> run_all.log 2>&1
echo "=== $(date) exit $?" >> run_all.log
