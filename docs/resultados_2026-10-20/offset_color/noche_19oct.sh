#!/bin/bash
# 19/10 noche: espera la tanda 5 (paso solo, rojo) y sigue con: rojo lrpx 1.15/1.20 (NA > 0.069) y el mismo barrido en VERDE
# (el paso de LED no depende del color: test independiente). Al final corre barrido_paso.py para rojo y verde.
cd "$(dirname "$0")"
until grep -q TANDA5_DONE logs/sweep_lrpx5.log 2>/dev/null; do sleep 60; done
date; echo NOCHE_START
{
for p in 115 120; do echo "z102_p$p b_red real_A+init_z98.0_full"; done
for p in 125 130 135 140 145; do echo "z102_p$p b_green real_A+init_z98.0_full"; done
for v in z102_p125 z102_p140; do for f in 0 1 2 3 4; do echo "$v b_green real_A+init_z98.0_f$f"; done; done
} | xargs -P 4 -L 1 bash -c 'nice python3 runner.py one $0 $1 $2 40 > logs/${0}_${1}_${2##*_}.log 2>&1; echo "FIN $0 $1 $2"'
python3 barrido_paso.py 40 b_red > logs/barrido_paso_b_red.txt 2>&1
python3 barrido_paso.py 40 b_green > logs/barrido_paso_b_green.txt 2>&1
date; echo NOCHE_DONE
