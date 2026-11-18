#!/bin/bash
# 18/11: red de transmisión 500 l/mm (T nominal 2,0 µm). z del borde (precaptura centro sobre la toma completa): R 1.794 -> 145.6 mm.
# Flat 2048ms-sinmuestra (10:19, mismo ROI). Eje: 'centro' de captura.json (prueba 15:26). NA por defecto 0.0747.
cd /home/chanoscopio/Documents/LucasC/reproducible-research-template
I=~/Documents/AleYLu/imagenes_tomadas; O=~/Documents/AleYLu/reconstrucciones/2026-11-18/red500
echo "=== $(date +%H:%M) red500, z 145.6"
python3 -u scripts/reconstruir.py $I/2026-11-18.2048ms-grilla.c --flat $I/2026-11-18.2048ms-sinmuestra \
  --dark-flat $I/2026-11-18.2048ms-sinmuestra-dark --dark $I/2026-11-18.2048ms-grilla.c-dark --z-mm 145.6 \
  --epocas 160 --validar --nucleos 3 --salida $O/recon 2>&1 | grep --line-buffered -v "^\s*\[#" | grep --line-buffered -v Axes3D
echo "=== $(date +%H:%M) fin"
