#!/bin/bash
# uso: correr_uno.sh "nombre|captura|flat|dark|darkflat"   (flat=SELF -> la propia captura; espectral sin sentido)
A=/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/archivo
I=/home/chanoscopio/Documents/AleYLu/imagenes_tomadas
IFS='|' read n c f d df <<< "$1"
[ "$f" = SELF ] && f=$I/$c || f=$I/$f
cd /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/zonas_3x3
python3 analizar_zonas.py $A/enlaces/$n --flat $f --dark $I/$d --dark-flat $I/$df --procs 1 --out $A/runs --nombre $n > $A/logs/$n.log 2>&1
echo "$n rc=$?"
