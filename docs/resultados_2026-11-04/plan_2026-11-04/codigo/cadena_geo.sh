#!/bin/bash
# 03/11 rojo: geometría medida en la propia captura (λ fijo 0.63 en el código; el solver solo ve z·λ y NA/λ)
# A-filas: z·λ 61.36 -> z 97.4 ; A-prom: z·λ 60.23 -> z 95.6 ; NA/λ 0.1135 -> NA 0.0715
P=/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-04
T=/home/chanoscopio/Documents/AleYLu/imagenes_tomadas
export PYTHONPATH=/home/chanoscopio/Documents/LucasC/reproducible-research-template/src
ARGS="$T/2026-11-03-red --flat $T/2026-11-03-red-sinmuestra --dark $T/2026-11-03-red-dark --dark-flat $T/2026-11-03-red-sinmuestra-dark --color r --recorte 360,80 --epocas 160 --guardar-cada 0 --validar"
for cfg in "A_filas 97.4" "A_prom 95.6"; do set -- $cfg; mkdir -p $P/$1
  Z_MM=$2 NA_OBJ=0.0715 python3 $P/codigo/reconstruir_plan.py $ARGS --salida $P/$1 > $P/$1/log.txt 2>&1 < /dev/null
  echo "$1 exit $? $(date +%H:%M)" >> $P/estado_geo.txt
done
echo FIN >> $P/estado_geo.txt
