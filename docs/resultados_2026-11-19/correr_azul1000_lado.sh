#!/bin/bash
# 19/11 tarde: grilla 1000 l/mm (T 1.000 µm) en AZUL, barrido de tamaño de grid + análisis por épocas.
# Mismo recorte que azul1000/tam200 (--recorte 348,459, 200 px), z 145.6, NA 0.0747, λ 0.47, --validar.
# Snapshots cada 20 épocas con objetos (pico del espectro por época a posteriori). 29x29 con 320 épocas (¿meseta?).
# Teoría: orden ±1 entra a 10.4 pasos (crudo: entrada ~10.3, meseta 11–14) -> 23x23 (11 pasos) último completo, 21x21 (10) marginal, 19x19 (9) nada.
cd /home/chanoscopio/Documents/LucasC/reproducible-research-template
I=~/Documents/AleYLu/imagenes_tomadas; D=~/Documents/AleYLu/reconstrucciones/2026-11-19/azul1000_lado
for par in "21 160" "23 160" "19 160" "25 160" "27 160" "29 320"; do
  set -- $par; N=$1; E=$2
  echo "=== $(date +%H:%M) lado $N, $E épocas"
  python3 -u scripts/reconstruir.py $I/2026-11-19.2048ms.grilla.b-1000 --color b --flat $I/2026-11-19.2048ms-sinmuestra.azul.1000 \
    --dark-flat $I/2026-11-19.2048ms-sinmuestra.azul.1000-dark --dark $I/2026-11-19.2048ms.grilla.b-1000-dark --z-mm 145.6 \
    --recorte 348,459 --tam 200 --lado-max $N --epocas $E --validar --guardar-cada 20 --guardar-objetos --nucleos 3 \
    --salida $D/lado$N 2>&1 | grep --line-buffered -E "C1 R|R de ajuste|tiempo|ERROR|Error|lado-max|recorte"
  python3 $D/espectro.py $D/lado$N 0.258 2>&1 | grep -E "amplitud|C3"
done
echo "=== $(date +%H:%M) fin"
