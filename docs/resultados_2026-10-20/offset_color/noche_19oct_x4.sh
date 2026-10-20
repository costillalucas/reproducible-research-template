#!/bin/bash
# 19/10: folds de las variantes _x4 (sin (17,14),(17,16) en entrenamiento) en lrpx 1.25 y 1.40, rojo. Resuelve si la
# preferencia held-out por 1.25 (+0.069) sobrevive sin las dos LEDs a horcajadas (en train cae a +0.003 ± 0.002).
cd "$(dirname "$0")"
until grep -q NOCHE_DONE logs/noche_19oct.log 2>/dev/null; do sleep 60; done
date; echo X4_START
for v in z102_p125_x4 z102_p140_x4; do for f in 0 1 2 3 4; do echo "$v b_red real_A+init_z98.0_f$f"; done; done \
 | xargs -P 4 -L 1 bash -c 'nice python3 runner.py one $0 $1 $2 40 > logs/${0}_${1}_${2##*_}.log 2>&1; echo "FIN $0 $1 $2"'
date; echo X4_DONE
