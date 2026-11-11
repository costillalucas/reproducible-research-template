#!/bin/bash
# Todo en serie (1 núcleo; el agente hermano usa los otros). Geometría B por defecto del driver (z 102, NA 0.06686, λ 0.63), 160 épocas.
cd /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-11/recortes_5um
export OMP_NUM_THREADS=1
python3 -W ignore codigo/recortes.py --tam 20 > runs/log_r20.txt 2>&1
python3 -W ignore codigo/recortes.py --tam 20 --nulo > runs/log_r20_nulo.txt 2>&1
python3 -W ignore codigo/recortes.py --tam 40 > runs/log_r40.txt 2>&1
python3 -W ignore codigo/recortes.py --tam 80 > runs/log_r80.txt 2>&1
echo FIN > runs/FIN
