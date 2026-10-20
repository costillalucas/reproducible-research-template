#!/bin/bash
# 05/10 (tarde): barrido de PASO solo a radio de pupila fijo (NA·lrpx = 0.069·1.25), rojo, z 102 (y z 100 de referencia),
# folds en lrpx 1.25 y 1.40; '_x4' = sin (17,14),(17,16) además (pasan a horcajadas en el modelo con lrpx >= 1.35)
cd "$(dirname "$0")"
date
{
for p in 125 130 135 140 145; do echo "z102_p$p b_red real_A+init_z98.0_full"; done
for v in z100_p125 z100_p140 z102_p125_x4 z102_p140_x4; do echo "$v b_red real_A+init_z98.0_full"; done
for v in z102_p125 z102_p140; do for f in 0 1 2 3 4; do echo "$v b_red real_A+init_z98.0_f$f"; done; done
} | xargs -P 4 -L 1 bash -c 'nice python3 runner.py one $0 $1 $2 40 > logs/${0}_${1}_${2##*_}.log 2>&1; echo "FIN $0 $1 $2"'
date; echo TANDA5_DONE
