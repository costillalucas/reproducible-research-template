#!/bin/bash
# 19/11: grilla ~1 µm en AZUL, 29x29 (2026-11-19.2048ms.grilla.b-1000), z 145.6, ROI 4160,1008, NA 0.0747, λ 0.47.
# Lóbulo crudo: entrada ~10.3 pasos, meseta 11-14 a lo largo de filas -> T ≈ 1.01 µm esperado (pico ~0.99 µm⁻¹).
# Rápido: --tam 200, 160 ép, --validar. Espectro en banda 0.80-1.30 µm⁻¹.
cd /home/chanoscopio/Documents/LucasC/reproducible-research-template
I=~/Documents/AleYLu/imagenes_tomadas; D=~/Documents/AleYLu/reconstrucciones/2026-11-19/azul1000
echo "=== $(date +%H:%M) grilla 1 µm azul, tam 200"
python3 -u scripts/reconstruir.py $I/2026-11-19.2048ms.grilla.b-1000 --color b --flat $I/2026-11-19.2048ms-sinmuestra.azul.1000 \
  --dark-flat $I/2026-11-19.2048ms-sinmuestra.azul.1000-dark --dark $I/2026-11-19.2048ms.grilla.b-1000-dark --z-mm 145.6 --tam 200 \
  --epocas 160 --validar --guardar-cada 0 --nucleos 3 --salida $D/tam200 2>&1 | grep --line-buffered -v "^\s*\[#" | grep --line-buffered -v Axes3D
python3 $D/espectro.py $D/tam200 0.258
echo "=== $(date +%H:%M) fin"
