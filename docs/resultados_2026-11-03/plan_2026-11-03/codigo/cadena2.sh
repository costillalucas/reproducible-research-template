#!/bin/bash
# extra (cabía en el tiempo): nulo DF de red-c, misma config que red-c real
P=/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-03
T=/home/chanoscopio/Documents/AleYLu/imagenes_tomadas
export PYTHONPATH=/home/chanoscopio/Documents/LucasC/reproducible-research-template/src
until grep -q FIN $P/estado.txt; do sleep 10; done
mkdir -p $P/red-c_nulo_df
NULO_DF=1 python3 $P/codigo/reconstruir_plan.py $T/2026-10-30-red-c --flat $T/2026-10-30-red-c-sinmuestra --dark $T/2026-10-30-red-c-dark --dark-flat $T/2026-10-30-red-c-sinmuestra-dark --color r --offset-roi 3968,1966 --recorte 380,200 --epocas 160 --guardar-cada 0 --validar --salida $P/red-c_nulo_df > $P/red-c_nulo_df/log.txt 2>&1 < /dev/null
echo "redc_nulo exit $? $(date)" >> $P/estado.txt; echo FIN2 >> $P/estado.txt
