#!/bin/bash
# 18/11: grilla (2,4 mm + ~0,8 mm de soportes) en las dos orientaciones. z del borde campo claro/oscuro (precaptura centro
# sobre la toma completa): grilla R 1.807 -> 146.7 mm; grilla.b R 1.796 -> 145.8 mm (ref. esferas 1.768 a 143.5).
# Flat: 2048ms-sinmuestra (único sin muestra a esta altura; no incluye los vidrios de los soportes). Eje: 'centro' de captura.json.
cd /home/chanoscopio/Documents/LucasC/reproducible-research-template
I=~/Documents/AleYLu/imagenes_tomadas; D=~/Documents/AleYLu/reconstrucciones/2026-11-18/grilla
FLAT="--flat $I/2026-11-18.2048ms-sinmuestra --dark-flat $I/2026-11-18.2048ms-sinmuestra-dark"
for par in "grilla 146.7" "grilla.b 145.8"; do
  set -- $par
  echo "=== $(date +%H:%M) $1, z $2"
  python3 scripts/reconstruir.py $I/2026-11-18.2048ms-$1 $FLAT --dark $I/2026-11-18.2048ms-$1-dark --z-mm $2 \
    --epocas 160 --validar --nucleos 3 --salida $D/$1 2>&1 | grep -v "^\s*\[#" | grep -v Axes3D
done
echo "=== $(date +%H:%M) fin"
