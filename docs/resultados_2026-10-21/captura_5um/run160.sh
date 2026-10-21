#!/bin/bash
# 21/10: rojo_centrado sobre r21_red (captura 2026-10-21, eje sobre (17,15)) a 160 épocas (snapshots 5/20/40/80/160):
# full, mitades, mezcladas (nulo), 5 folds; 3 procesos (de 4 núcleos), nice. Full y mitades primero.
cd "$(dirname "$0")"; mkdir -p logs
date; echo START160
for t in full half0 half1 half0_scr half1_scr f0 f1 f2 f3 f4; do echo "rojo_centrado r21_red real_A+init_z98.0_$t"; done \
 | xargs -P 3 -L 1 bash -c 'nice python3 runner_2110.py one $0 $1 $2 160 > logs/${0}_${1}_${2##*_}.log 2>&1; echo "FIN $0 $1 $2"; date'
date; echo DONE160
