#!/bin/bash
# 19/11 noche: grilla 1000 l/mm (T 1.000 µm) en AZUL, recorte de siempre (--tam 400, por defecto cerca del eje),
# barrido de grid 29 -> 21 (límite con 200 px: 23x23; 21 = borde de cobertura). z 145.6, NA 0.0747, λ 0.47,
# 160 épocas, --validar, snapshots + objetos cada 40 épocas. Al final: espectro por grid y análisis por épocas (epocas.txt).
cd /home/chanoscopio/Documents/LucasC/reproducible-research-template
I=~/Documents/AleYLu/imagenes_tomadas; D=~/Documents/AleYLu/reconstrucciones/2026-11-19/azul1000_lado400
for N in 29 27 25 23 21; do
  echo "=== $(date '+%d/%m %H:%M') lado $N"
  python3 -u scripts/reconstruir.py $I/2026-11-19.2048ms.grilla.b-1000 --color b --flat $I/2026-11-19.2048ms-sinmuestra.azul.1000 \
    --dark-flat $I/2026-11-19.2048ms-sinmuestra.azul.1000-dark --dark $I/2026-11-19.2048ms.grilla.b-1000-dark --z-mm 145.6 \
    --tam 400 --lado-max $N --epocas 160 --validar --guardar-cada 40 --guardar-objetos --nucleos 3 \
    --salida $D/lado$N 2>&1 | grep --line-buffered -E "C1 R|R de ajuste|tiempo|ERROR|Error|Traceback|lado-max|filas"
  python3 $D/espectro.py $D/lado$N 0.258 2>&1 | grep -E "amplitud|fase|C3" | tee $D/lado$N/espectro.txt
done
python3 $D/epocas.py > $D/epocas.txt 2>&1
echo "=== $(date '+%d/%m %H:%M') fin"
