#!/bin/bash
# Fase B: C2 con K particiones aleatorias. Resumible (salta done.json). Uso: ./run_part.sh [NPROC] [MAXEP] [DS] [K]
cd "$(dirname "$0")"
NPROC=${1:-3}; MAXEP=${2:-400}; DS=${3:-b_red,b_blue}; K=${4:-5}
echo "=== $(date) start NPROC=$NPROC MAXEP=$MAXEP DS=$DS K=$K" >> particiones.log
nice -n 10 python3 -u particiones.py run "$NPROC" "$MAXEP" "$DS" "$K" >> particiones.log 2>&1
echo "=== $(date) exit $?" >> particiones.log
