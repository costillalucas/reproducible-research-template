#!/bin/bash
# 19/11: barrido de λ_azul vía z (degeneración z·λ: f ≈ x/(z·λ)) sobre la red 500 l/mm en azul (grilla.a, 17x17).
# λ_modelo fijo 0.470 (config); z_modelo = 145.6 · λ_prueba / 0.470. --tam 200 (rápido), NA 0.0747, 160 ép, --validar.
# Predicción: si λ es el problema, en λ_prueba ≈ 0.486 el pico de la red va a ~0.500 µm⁻¹ y C1 mejora.
cd /home/chanoscopio/Documents/LucasC/reproducible-research-template
I=~/Documents/AleYLu/imagenes_tomadas; D=~/Documents/AleYLu/reconstrucciones/2026-11-19/azul500_lambda
for lam in 0.470 0.486 0.460 0.478 0.494 0.502; do
  z=$(python3 -c "print(round(145.6*$lam/0.470,2))")
  echo "=== $(date +%H:%M) λ_prueba $lam -> z_modelo $z"
  python3 -u scripts/reconstruir.py $I/2026-11-19.2048ms-grilla.a --color b --flat $I/2026-11-19.2048ms-sinmuestra.azul.500 \
    --dark-flat $I/2026-11-19.2048ms-sinmuestra.azul-dark.500 --dark $I/2026-11-19.2048ms-grilla.a-dark --z-mm $z --tam 200 \
    --epocas 160 --validar --guardar-cada 0 --nucleos 3 --salida $D/lam${lam#0.} 2>&1 | grep --line-buffered -E "C1 R|R de ajuste|ERROR|Error|tiempo"
  python3 $D/espectro.py $D/lam${lam#0.} 0.258 2>&1 | grep -E "complejo.*amplitud|mitad.*amplitud"
done
echo "=== $(date +%H:%M) fin"
