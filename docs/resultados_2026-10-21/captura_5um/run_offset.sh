#!/bin/bash
# 21/10: control de centrado del eje en r21_red: folds f0-f4 a 40 épocas con offset total -0.6 / +0.6 / +1.06 mm en filas
# (rojo_centrado = +0.085). Espera a run160.sh y run_m2folds.sh; 3 procesos.
cd "$(dirname "$0")"
while pgrep -f "run160.sh|run_m2folds.sh" > /dev/null; do sleep 30; done
date; echo START_OFF
for v in rc_om060 rc_op060 rc_op106; do for t in f0 f1 f2 f3 f4; do echo "$v r21_red real_A+init_z98.0_$t"; done; done \
 | xargs -P 3 -L 1 bash -c 'nice python3 runner_2110.py one $0 $1 $2 40 > logs/${0}_${1}_${2##*_}.log 2>&1; echo "FIN $0 $1 $2"; date'
date; echo DONE_OFF
