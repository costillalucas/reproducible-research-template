#!/bin/bash
# 21/10 tarde: control del signo del offset en columnas del recorte (C1, folds a 40 épocas; 2 procesos para dejar 1 núcleo a la evaluación): x = 0 y +0.340 mm (rojo_500 usa -0.340).
cd "$(dirname "$0")"
while pgrep -f run160.sh > /dev/null; do sleep 30; done
date; echo START_X
for v in "r500_x000 0.0" "r500_xp034 0.340"; do for t in f0 f1 f2 f3 f4; do echo "$v real_A+init_z98.0_$t"; done; done \
 | xargs -P 2 -L 1 bash -c 'R500_XOFF=$1 nice python3 runner_500.py one $0 r500_red $2 40 > logs/${0}_${2##*_}.log 2>&1; echo "FIN $0 $2"; date'
date; echo DONE_X
