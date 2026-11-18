#!/bin/bash
# 18/11: diseño 2x2 (exposición máx 1025 / 2048 ms) x (NA_OBJ 0.0669 = preferido por C1 / 0.0747 = FFT de la pupila).
# z 143.5, 21x21, flat 2048ms-sinmuestra (sirve para ambos: todo en cuentas/ms), eje del chequeo de centrado de cada toma.
cd /home/chanoscopio/Documents/LucasC/reproducible-research-template
I=~/Documents/AleYLu/imagenes_tomadas; C=~/Documents/AleYLu/chequeos; D=~/Documents/AleYLu/reconstrucciones/2026-11-18
FLAT="--flat $I/2026-11-18.2048ms-sinmuestra --dark-flat $I/2026-11-18.2048ms-sinmuestra-dark"
for set in 2048 1025; do
  case $set in 2048) CEN=$C/2026-11-18.2048ms-prueba-0959/centro.json;; 1025) CEN=$C/2026-11-17.1025ms-prueba-1732/centro.json;; esac
  for na in 0.0669 0.0747; do
    echo "=== $(date +%H:%M) set $set ms, NA $na"
    python3 scripts/reconstruir.py $I/2026-11-18.${set}ms $FLAT --dark $I/2026-11-18.${set}ms-dark --centro $CEN \
      --na $na --epocas 160 --validar --nucleos 3 --salida $D/${set}ms_na${na#0.} 2>&1 | grep -v "^\s*\[#" | grep -v Axes3D
  done
done
echo "=== $(date +%H:%M) fin"
