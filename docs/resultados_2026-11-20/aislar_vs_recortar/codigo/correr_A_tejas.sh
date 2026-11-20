#!/bin/bash
# (A) 4 recortes más de 200 px (cuadrantes del recorte de 400 px del 18/11, filas 326:726 col 381:781): el recorte por
# defecto (A_200) tiene solo ~6 partículas y hacen falta 15 aisladas. Mismas opciones que correr_A.sh.
cd /home/chanoscopio/Documents/LucasC/reproducible-research-template
I=~/Documents/AleYLu/imagenes_tomadas; C=~/Documents/AleYLu/chequeos
OUT=~/Documents/AleYLu/reconstrucciones/2026-11-20/aislar_vs_recortar
for rc in 326,381 326,581 526,381 526,581; do
  d=$OUT/A_200_${rc/,/_}; echo "=== $(date +%H:%M:%S) $rc"
  python3 scripts/reconstruir.py $I/2026-11-18.2048ms --flat $I/2026-11-18.2048ms-sinmuestra --dark-flat $I/2026-11-18.2048ms-sinmuestra-dark \
    --dark $I/2026-11-18.2048ms-dark --centro $C/2026-11-18.2048ms-prueba-0959/centro.json \
    --na 0.0747 --recorte $rc --tam 200 --epocas 160 --validar --nucleos 3 --salida $d > $d.log 2>&1
done
echo "=== $(date +%H:%M:%S) fin"
