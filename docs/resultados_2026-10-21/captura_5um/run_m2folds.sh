#!/bin/bash
# 21/10: completa el C1 de m2_red (octubre): folds f3, f4 de rojo_final a 40 épocas (en octubre quedaron cortados en 30 / sin correr),
# escritos en ESTE out/ (no se toca octubre_capturas_2026-10-21/). Espera a run160.sh.
cd "$(dirname "$0")"
while pgrep -f run160.sh > /dev/null; do sleep 30; done
date; echo START_M2
for t in f3 f4; do echo "rojo_final m2_red real_A+init_z98.0_$t"; done \
 | xargs -P 2 -L 1 bash -c 'nice python3 runner_2110.py one $0 $1 $2 40 > logs/${0}_${1}_${2##*_}.log 2>&1; echo "FIN $0 $1 $2"; date'
date; echo DONE_M2
