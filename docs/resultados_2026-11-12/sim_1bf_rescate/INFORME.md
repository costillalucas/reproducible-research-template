# Rescate del 1 BF atacando la fase del DC (simulación, 12/11)

Todo es simulación, hecha en ~15 min. `python sim_1bf_rescate.py` (semillas fijas) y luego `python figs.py` regeneran `runs.jsonl`, `resumen.txt`, `fig1_costo_vs_theta.png` y `fig2_variantes.png`. Importa sin modificar `sim_1bf_diag.py` (solver ePIE, pupila dura) y `sim_z_1bf.py`.

**Cobertura real:** 6 casos completos: z = 73 mm (1 BF real) objetos 0 y 1, semillas 0 y 1; z = 103 mm (1 BF artificial) objetos 0 y 1, semilla 0. El proceso se cortó por tiempo: z = 103 con semilla 1 **no se corrió** (puede quedar una fila parcial al final de `runs.jsonl`). Las tablas y los "5 de 5" de abajo se redactaron con 5 casos; el sexto (z73 obj1 s1) terminó después y repite el patrón (θ0=π/2: 0.36 rad, elegido por costo; signo ok 0.61, signo mal 2.42; ganancia 1.71), o sea 6 de 6. 20 épocas por corrida. Fase = RMS en esferas (rad); costo = residuo de amplitud relativo sobre todos los LEDs (x1e-3).

## Resultado principal

**Sí: con 1 BF la fase converge si el DC del init se rota +π/2** (init habitual: amplitud del BF, fase plana; sólo se multiplica el pixel DC del espectro por i). Elegir por menor costo entre θ0 ∈ {0, π/2, π, 3π/2} acertó en **5 de 5 casos**:

| caso | base (θ0=0) | θ0=π/2 | θ0=π | θ0=3π/2 | init=verdad |
|---|---|---|---|---|---|
| z73 obj0 s0: fase / costo | 2.12 / 3.42 | **0.30 / 2.21** | 1.25 / 9.78 | 2.52 / 2.99 | 0.05 / 1.16 |
| z73 obj1 s0 | 2.02 / 5.30 | **0.33 / 3.67** | 1.43 / 18.5 | 2.61 / 4.81 | 0.06 / 1.79 |
| z73 obj0 s1 | 2.18 / 3.33 | **0.28 / 2.04** | 1.24 / 9.56 | 2.52 / 3.08 | 0.05 / 1.16 |
| z103 obj0 s0 | 2.34 / 2.79 | **0.19 / 2.14** | 1.13 / 10.2 | 2.65 / 3.21 | 0.06 / 1.90 |
| z103 obj1 s0 | 2.02 / 4.63 | **0.23 / 3.25** | 1.34 / 21.6 | 2.73 / 4.08 | 0.05 / 2.80 |

0.19-0.33 rad a 20 épocas (ref. 5 BF: ~0.13); no se midió si con más épocas llega a 0.05.

## Lo que NO funciona, y la advertencia importante

- **Barrido de θ post-hoc sobre la solución base: nulo.** El costo vs θ aplicado al DC de la solución falsa tiene su mínimo en θ ≈ 0 (−0.26 rad), no en el θ que corrige la fase (≈ +0.8-1.05). Refinar desde ahí sólo profundiza el mínimo falso (fase 2.5-2.6). El campo difractado a 20 épocas está adaptado al DC equivocado: rotar sólo el DC no baja el costo.
- **El costo no discrimina de forma fiable el mínimo correcto del falso una vez convergidos.** A z = 103 el mínimo falso refinado (60 épocas en total) tiene costo 1.892 / 2.795 contra 1.903 / 2.799 del correcto (init = verdad): **degenerados dentro del ruido**. A z = 73 el falso queda más alto (1.53 vs 1.16; 2.20 vs 1.79) pero seguía bajando. El barrido alrededor de la solución verdadera muestra dos mínimos locales (θ = 0 y θ ≈ 4.97 ≈ −1.3 rad) con costos 1.16 vs 1.29 (z 73) y 1.90 vs 2.00 (z 103): esto apoya la hipótesis de ambigüedad de dos fases del DC, casi degenerada a z = 103.
- Por lo tanto, el acierto 5/5 del multi-inicio "por costo" a 20 épocas puede deberse en parte a que θ0 = π/2 converge más rápido, no a que el costo final distinga. **Lo robusto es saber de qué lado arrancar, no el criterio de costo.** No se probó con más épocas ni con inicios aleatorios.
- **Ganancia libre s_k del BF: nulo** (fase 1.6-1.9, ganancia ajustada 1.01-1.02). En el mínimo falso s_bf = 0.996-0.998: no hay desajuste de escala BF/DF que explique el problema (en simulación no se inyectó ninguno).

## Prior de signo

Proyección por época "fase respecto del fondo ≥ 0" (signo verdadero de las esferas), amplitud intacta:

- Signo correcto: 0.55-0.65 rad; soltando el prior 10 épocas más: 0.44-0.47 (θ DC residual 0.36). **Rescate parcial**, peor que el init rotado.
- **Signo incorrecto: 2.39-2.46 rad (cae en el mínimo falso) y con costo MENOR que el signo correcto** (p. ej. 1.58 vs 2.01). El costo no avisa que el signo está mal: el prior tiene que ser cierto.
- No se probó prior de fase suave/TV ni combinar prior de signo con init rotado.

## Respuesta

Con 1 BF la fase se puede hacer converger en simulación con el recurso mínimo de **inicializar con el DC adelantado π/2** (equivale a suponer objeto de fase débil con signo dado: o ≈ 1 + iφ). El lado correcto (+π/2 vs −π/2) es el mismo en los 5 casos, que comparten signo de fase de las esferas; presumiblemente depende de ese signo (no se probó con signo opuesto), o sea que es información física previa, igual que el prior de signo. Sin esa información, el costo de datos solo no alcanza de forma segura (degeneración a z = 103).

## Límites

Simulación idealizada (sin aberraciones, desenfoque ni errores de posición, pupila conocida), esferas de fase pura, 20 épocas, 2 objetos, semilla 1 sólo en un caso (sin desvíos útiles), grilla de θ0 de 4 valores. No verificado en datos reales. Las figuras no fueron inspeccionadas visualmente al redactar; los números salen de `resumen.txt`.

## Archivos

`sim_1bf_rescate.py`, `figs.py`, `runs.jsonl`, `run.log`, `resumen.txt`, `fig1_costo_vs_theta.png`, `fig2_variantes.png`, `INFORME.md`.
