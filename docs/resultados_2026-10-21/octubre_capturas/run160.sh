#!/bin/bash
# 21/10: rojo_final sobre m2_red (2026-10-16-muestra2) a 160 épocas (snapshots 5/20/40/80/160; el snapshot 40 = corrida de 40):
# full, mitades, mezcladas (nulo), 5 folds; 2 procesos, nice. Orden: full y mitades primero (chequeo a la época 40).
cd "$(dirname "$0")"; mkdir -p logs
date; echo START160
for t in full half0 half1 half0_scr half1_scr f0 f1 f2 f3 f4; do echo "rojo_final m2_red real_A+init_z98.0_$t"; done \
 | xargs -P 2 -L 1 bash -c 'nice python3 runner_oct.py one $0 $1 $2 160 > logs/${0}_${1}_${2##*_}.log 2>&1; echo "FIN $0 $1 $2"; date'
date; echo DONE160
