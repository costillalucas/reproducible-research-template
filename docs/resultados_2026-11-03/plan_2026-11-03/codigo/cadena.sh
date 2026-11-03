#!/bin/bash
# Corridas serializadas del plan 2026-11-03 (una por vez, 3 núcleos)
P=/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-03
T=/home/chanoscopio/Documents/AleYLu/imagenes_tomadas
S=$P/codigo/reconstruir_plan.py
export PYTHONPATH=/home/chanoscopio/Documents/LucasC/reproducible-research-template/src
while pgrep -f "reconstruir.py.*red-b_arco" >/dev/null; do sleep 10; done
echo "inicio $(date)" > $P/estado.txt
ARCO="$T/2026-10-30-red-b --flat $T/2026-10-30-red-b-sinmuestra --dark $T/2026-10-30-red-b-dark --dark-flat $T/2026-10-30-red-b-sinmuestra-dark --color r --offset-roi 4000,874 --recorte 290,415 --epocas 160 --guardar-cada 0 --validar"
REDC="$T/2026-10-30-red-c --flat $T/2026-10-30-red-c-sinmuestra --dark $T/2026-10-30-red-c-dark --dark-flat $T/2026-10-30-red-c-sinmuestra-dark --color r --offset-roi 3968,1966 --recorte 380,200 --epocas 160 --guardar-cada 0 --validar"
mkdir -p $P/red-b_arco_nulo_df $P/red-b_arco_na074 $P/red-c_na074
NULO_DF=1 python3 $S $ARCO --salida $P/red-b_arco_nulo_df > $P/red-b_arco_nulo_df/log.txt 2>&1 < /dev/null; echo "nulo exit $? $(date)" >> $P/estado.txt
NA_OBJ=0.074 python3 $S $ARCO --salida $P/red-b_arco_na074 > $P/red-b_arco_na074/log.txt 2>&1 < /dev/null; echo "arco_na074 exit $? $(date)" >> $P/estado.txt
NA_OBJ=0.074 python3 $S $REDC --salida $P/red-c_na074 > $P/red-c_na074/log.txt 2>&1 < /dev/null; echo "redc_na074 exit $? $(date)" >> $P/estado.txt
echo FIN >> $P/estado.txt
