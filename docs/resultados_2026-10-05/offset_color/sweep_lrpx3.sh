#!/bin/bash
# 05/10, segunda tanda: descomposición pupila/paso (rojo), azul y verde en 1.24/1.20, folds rojos en 1.16/1.24/1.362
cd "$(dirname "$0")"
date
{
for v in z102_desc_paso z102_desc_pupila; do echo "$v b_red real_A+init_z98.0_full"; done
for v in z102_m258 z102_m267; do echo "$v b_blue real_A+init_z98.0_full"; echo "$v b_green real_A+init_z98.0_full"; done
for v in z102_m276 z102_m258 final_z102; do for f in 0 1 2 3 4; do echo "$v b_red real_A+init_z98.0_f$f"; done; done
} | xargs -P 3 -L 1 bash -c 'nice python3 runner.py one $0 $1 $2 40 > logs/${0}_${1}_${2##*_}.log 2>&1; echo "FIN $0 $1 $2"'
date; echo TANDA3_DONE
