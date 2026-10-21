#!/bin/bash
# 21/10: control "objeto delgado": rojo_final sobre o02_red (2026-10-02_red_enfocado, BF con un solo pico de correlación) a 160
# épocas, full + mitades + nulo (sin folds). Espera a que termine run160.sh (máx. 2 procesos).
cd "$(dirname "$0")"
while pgrep -f run160.sh > /dev/null; do sleep 30; done
date; echo START_O02
for t in full half0 half1 half0_scr half1_scr; do echo "rojo_final o02_red real_A+init_z98.0_$t"; done \
 | xargs -P 2 -L 1 bash -c 'nice python3 runner_oct.py one $0 $1 $2 160 > logs/${0}_${1}_${2##*_}.log 2>&1; echo "FIN $0 $1 $2"; date'
date; echo DONE_O02
