#!/bin/bash
# 20/11: esferas 5 µm, ROJO, red.a (29x29 = 841 LEDs, todos), flat red.a-sinmuestra (eje del flat corrido -0.23 pasos:
# dentro del recorte solo afecta al LED (15,15)). z 142.1 (R del borde 1.753), NA por defecto 0.0747, 160 épocas, --validar.
cd /home/chanoscopio/Documents/LucasC/reproducible-research-template
I=~/Documents/AleYLu/imagenes_tomadas; D=~/Documents/AleYLu/reconstrucciones/2026-11-20/red_a_todos
echo "=== $(date '+%d/%m %H:%M') inicio"
python3 -u scripts/reconstruir.py $I/2026-11-20.2048ms-red.a --flat $I/2026-11-20.2048ms-red.a-sinmuestra \
  --dark $I/2026-11-20.2048ms-red.a-dark --dark-flat $I/2026-11-20.2048ms-red.a-sinmuestra-dark --z-mm 142.1 \
  --tam 400 --epocas 160 --validar --guardar-cada 40 --guardar-objetos --nucleos 3 --salida $D
echo "=== $(date '+%d/%m %H:%M') fin"
