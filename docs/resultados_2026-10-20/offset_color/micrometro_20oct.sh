#!/bin/bash
# 20/10: lrpx 1.29 (micrómetro del 16/10: 7.750 px por 10 µm -> 1.290 µm/px, M 2.48) en la familia de paso solo
# (NA·lrpx = 0.069·1.25 -> NA 0.0669), rojo y verde, full + 5 folds; held-out pareado contra 1.25 en barrido_paso.py.
cd "$(dirname "$0")"
date; echo MICRO_START
for ds in b_red b_green; do echo "z102_p129 $ds real_A+init_z98.0_full"; for f in 0 1 2 3 4; do echo "z102_p129 $ds real_A+init_z98.0_f$f"; done; done \
 | xargs -P 4 -L 1 bash -c 'nice python3 runner.py one $0 $1 $2 40 > logs/${0}_${1}_${2##*_}.log 2>&1; echo "FIN $0 $1 $2"'
python3 barrido_paso.py 40 b_red > logs/barrido_paso_b_red.txt 2>&1
python3 barrido_paso.py 40 b_green > logs/barrido_paso_b_green.txt 2>&1
date; echo MICRO_DONE
