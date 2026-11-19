#!/bin/bash
# 19/11: red 500 l/mm en AZUL (2026-11-19.2048ms-grilla.a), 17x17, z 145.6 (misma altura que grilla.c del 18/11), ROI 4160,1008 (recentrado al die azul).
# NA: 0.0747 (la del rojo) y 0.0763 (radio del borde en azul 1.833 vs 1.794 en rojo a igual z). λ modelo 0.470 (config, sin fuente).
# Lobulos observados a 4–7 pasos a lo largo de filas (predicho 3.9–7.9). Píxel reconstruido 1.29/5 = 0.258 µm (FACTOR azul 5).
cd /home/chanoscopio/Documents/LucasC/reproducible-research-template
I=~/Documents/AleYLu/imagenes_tomadas; D=~/Documents/AleYLu/reconstrucciones/2026-11-19/azul500
FLAT=$1; DXR=0.258
for na in 0.0747 0.0763; do
  echo "=== $(date +%H:%M) azul500 NA $na, flat $FLAT"
  python3 -u scripts/reconstruir.py $I/2026-11-19.2048ms-grilla.a --color b --flat $FLAT --dark-flat $FLAT-dark \
    --dark $I/2026-11-19.2048ms-grilla.a-dark --z-mm 145.6 --na $na --epocas 160 --validar --guardar-cada 0 --nucleos 3 \
    --salida $D/na${na#0.} 2>&1 | grep --line-buffered -v "^\s*\[#" | grep --line-buffered -v Axes3D
  python3 $D/espectro.py $D/na${na#0.} $DXR > $D/na${na#0.}/espectro.txt 2>&1; cat $D/na${na#0.}/espectro.txt
done
echo "=== $(date +%H:%M) fin"
