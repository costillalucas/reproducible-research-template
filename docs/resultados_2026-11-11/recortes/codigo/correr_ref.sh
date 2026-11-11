#!/bin/bash
# Brazo de referencia (200 px) y nulo DF para las dos regiones. Geometría: z 99.5 mm, λ 0.617 µm, NA 0.0720 (NA·z 7.16 = borde (a) s fijo de red-c).
P=/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-11/recortes
DRV=/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-04/codigo/reconstruir_plan.py
IMG=/home/chanoscopio/Documents/AleYLu/imagenes_tomadas
ARGS="$IMG/2026-10-30-red-c --flat $IMG/2026-10-30-red-c-sinmuestra --dark $IMG/2026-10-30-red-c-dark --dark-flat $IMG/2026-10-30-red-c-sinmuestra-dark --tam 200 --epocas 160 --guardar-cada 0 --nucleos 1 --offset-roi 3968,1966"
corre() {  # nombre recorte nulo
  mkdir -p $P/runs/$1
  ( date +%s > $P/runs/$1/t_ini; OMP_NUM_THREADS=1 Z_MM=99.5 NA_OBJ=0.0720 LAM_NM=617 NULO_DF=$3 python3 $DRV $ARGS --recorte $2 --salida $P/runs/$1 > $P/runs/$1/log.txt 2>&1 < /dev/null; echo "exit $?" >> $P/runs/$1/log.txt; date +%s > $P/runs/$1/t_fin ) &
}
corre ref_A 440,380 0
corre ref_B 770,460 0
corre nulo_A 440,380 1
corre nulo_B 770,460 1
wait
