#!/bin/bash
# 05/10, tercera tanda (tras sweep_lrpx3): barrido de NA en rojo a lrpx 1.362, z 102
cd "$(dirname "$0")"
until grep -q TANDA3_DONE logs/sweep_lrpx3.log; do sleep 30; done
date
for v in z102_na062 z102_na059; do echo "$v b_red real_A+init_z98.0_full"; done \
 | xargs -P 2 -L 1 bash -c 'nice python3 runner.py one $0 $1 $2 40 > logs/${0}_${1}_${2##*_}.log 2>&1; echo "FIN $0 $1 $2"'
date; echo TANDA4_DONE
