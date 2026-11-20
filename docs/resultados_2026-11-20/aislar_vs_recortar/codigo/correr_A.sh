#!/bin/bash
# (A) recorte 200 px por defecto (lo más cerca del eje), mismas opciones que 2026-11-18/correr.sh (2048 ms, NA 0.0747)
cd /home/chanoscopio/Documents/LucasC/reproducible-research-template
I=~/Documents/AleYLu/imagenes_tomadas; C=~/Documents/AleYLu/chequeos
OUT=~/Documents/AleYLu/reconstrucciones/2026-11-20/aislar_vs_recortar
python3 scripts/reconstruir.py $I/2026-11-18.2048ms --flat $I/2026-11-18.2048ms-sinmuestra --dark-flat $I/2026-11-18.2048ms-sinmuestra-dark \
  --dark $I/2026-11-18.2048ms-dark --centro $C/2026-11-18.2048ms-prueba-0959/centro.json \
  --na 0.0747 --tam 200 --epocas 160 --validar --nucleos 3 --salida $OUT/A_200 2>&1 | grep -v "^\s*\[#" | grep -v Axes3D
