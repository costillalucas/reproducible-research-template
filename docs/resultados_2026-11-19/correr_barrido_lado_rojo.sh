#!/bin/bash
# 19/11: barrido de tamaño de grid sobre la red 500 l/mm (2026-11-18.2048ms-grilla.c), mismas opciones que red500 del 18/11.
# Predicción de Lucas (escrita ANTES): orden ±1 entra con LEDs a 6.0–10.3 pasos -> red visible en 19,17,15; gradual en 13; desaparece en 11.
# Umbral: pico/mediana < 10 = "no hay red".
cd /home/chanoscopio/Documents/LucasC/reproducible-research-template
I=~/Documents/AleYLu/imagenes_tomadas; D=~/Documents/AleYLu/reconstrucciones/2026-11-19/barrido_lado
for N in 19 17 15 13 11; do
  echo "=== $(date +%H:%M) lado $N"
  python3 -u scripts/reconstruir.py $I/2026-11-18.2048ms-grilla.c --flat $I/2026-11-18.2048ms-sinmuestra \
    --dark-flat $I/2026-11-18.2048ms-sinmuestra-dark --dark $I/2026-11-18.2048ms-grilla.c-dark --z-mm 145.6 \
    --lado-max $N --epocas 160 --validar --guardar-cada 0 --nucleos 3 --salida $D/lado$N 2>&1 | grep --line-buffered -v "^\s*\[#" | grep --line-buffered -v Axes3D
  python3 docs/resultados_2026-11-18/red500_espectro.py $D/lado$N > $D/lado$N/espectro.txt 2>&1
  cat $D/lado$N/espectro.txt
done
echo "=== $(date +%H:%M) fin"
