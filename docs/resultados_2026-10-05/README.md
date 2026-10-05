# Resultados 2026-10-05 — barrido de lrpx extendido y recuperación de pupila (EPRY)

Respaldo de `results/offset_color_2026-10-02/` (actualizado el 05/10) y `results/pupila_2026-10-05/` (gitignored).
Objetos reconstruidos (`out/`) no incluidos. Sin foto de micrómetro disponible.

- `offset_color/INFORME.md`: última sección "Barrido de lrpx extendido a z = 102 (05/10…)"; `barrido_lrpx.py/.json`, `sweep_lrpx{2,3,4}.sh`.
- `pupila/INFORME.md`: EPRY sobre z102_m250 y final_z102 (`epry.py`, `zernike.py`, `zernike.json`).

## Conclusiones
1. Mínimo de R_train en rojo encerrado: lrpx ≈ 1.25 ± 0.02 µm → aumento ≈ 2.56 ± 0.04× a z = 102 mm, NA 0.069.
   No es sobreajuste: residuo en LEDs de validación (5 folds) 0.406 (1.24) vs 0.461 (1.362).
   Verde y azul no fijan el valor (plano / irregular por redondeo de ventanas).
2. El modelo solo ve NA·lrpx (radio de pupila, ~2/3 de la preferencia) y lrpx/z (paso de LEDs, ~1/3).
   El mismo ajuste lo reproduce 2.28× nominal con z ≈ 114 mm y NA ≈ 0.062; z ≈ 114 está descartado
   (z medido ≈ 98–102 mm), así que la tensión con la óptica nominal persiste.
3. EPRY: nunca baja el residuo; pupila recuperada casi sin aberración (desenfoque 7–15 µm ≪ 130 µm de DOF),
   igual a 2.5× y 2.35×. Una fase de pupila no puede imitar el cambio de aumento.

Todo a 40 épocas, conclusiones solo en rojo. En curso: barrido de lrpx a radio de pupila fijo (NA·lrpx constante).
