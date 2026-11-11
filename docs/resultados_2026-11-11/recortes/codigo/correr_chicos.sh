#!/bin/bash
# Brazo de recortes chicos: 20 px (todas), 20 px nulo DF (todas), 40 y 80 px (las que entran en su recorte de 200 px).
P=/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-11/recortes
export Z_MM=99.5 NA_OBJ=0.0720 LAM_NM=617 OMP_NUM_THREADS=1
cd $P
python3 codigo/recortes_chicos.py --tam 20 --procs 2 > runs/log_chicos_20.txt 2>&1
python3 codigo/recortes_chicos.py --tam 20 --nulo --procs 2 > runs/log_chicos_20_nulo.txt 2>&1
python3 codigo/recortes_chicos.py --tam 40 --procs 2 > runs/log_chicos_40.txt 2>&1
python3 codigo/recortes_chicos.py --tam 80 --procs 2 > runs/log_chicos_80.txt 2>&1
python3 codigo/recortes_chicos.py --tam 20 --excluir-cambian --procs 2 > runs/log_chicos_20_sincambian.txt 2>&1
