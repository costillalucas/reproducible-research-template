# Estado — barrido de épocas en datos reales (lanzado 2026-09-30 15:07)

## Qué corre (independiente de la sesión: setsid nohup)
- `run_all.sh 3 400 b_red,b_green,b_blue` → `python3 -u iter_runner.py run 3 400 ...` (pid padre 14713, 3 workers).
  30 tareas = 3 colores × (full, half0, half1, half0_scr, half1_scr, 5 folds CV), A+init, hasta 400 épocas.
  Orden: rojo, verde, azul; dentro de cada color, full y mitades primero, folds después.
  Log: `run_all.log` (una línea por snapshot: `[dataset tarea] ep N trainR .. hoR .. Ns`, y `FIN ...` por tarea).
- `smoke.py` (pid 14880, log `smoke.log`, resultado `smoke.json`): verificaciones, ver abajo.

## Chequear progreso
    pgrep -af iter_runner
    grep -c FIN results/iteraciones_2026-09-30/run_all.log        # tareas terminadas (de 30)
    tail results/iteraciones_2026-09-30/run_all.log
    python3 results/iteraciones_2026-09-30/iter_runner.py list    # estado por tarea (DONE si hay done.json)

## Relanzar / reanudar
Resumible: salta tareas con `done.json`; una tarea a medias se rehace entera (su metrics.jsonl se trunca).

    cd results/iteraciones_2026-09-30 && setsid nohup ./run_all.sh 3 400 b_red,b_green,b_blue >/dev/null 2>&1 </dev/null &

Set 3 del 25/09 (rojo, z 74) todavía NO lanzado: `./run_all.sh 3 400 s3_red` cuando termine lo anterior.
Si hay que recortar tiempo: MAXEP menor (p. ej. 240) solo sirve para tareas que no empezaron;
las tareas guardan todos los SNAPS ≤ MAXEP.

## Smoke test
- (1) Copia del solver (`reconstruct_snap`) vs `fpm_red.reconstruct` A+init, 3 épocas, rojo full: **diferencia máxima 0.0 (bit a bit) — VALIDADO.**
  Como la rampa del paso depende solo del índice de época, el snapshot de la época e de la corrida de 400 = corrida de e épocas.
- (2) fold f0 rojo a 40 épocas vs `captura_2026-09-28b/red/out/tasks/real_A+init_z98.0_f0.json` (per_led): en curso → mirar `smoke.json`
  (`f0_per_led_maxabsdiff` debería ser ~0; `f0_40ep_heldout_R_ring_lt7` vs `f0_ref_heldout_R_ring_lt7`).
- (3) s/época por dataset: en curso → `smoke.json` (`s_per_epoch_*`). Medido con carga (3 workers + pytest ajeno), es pesimista.
- Estimación a priori (log del 28/09 b: ~4 min por tarea de 40 épocas con 3 procesos): verde/azul ~6 s/época →
  400 épocas ≈ 40 min + métricas por tarea; 10 tareas/color / 3 procesos ≈ 2,3 h por color verde/azul; rojo (factor 3) menos.
  Total 28/09 b ≈ 5-6 h de pared. Confirmar con smoke.json y con los tiempos por línea en run_all.log.

## Formato de salidas
`out/<dataset>/<tarea>/` con dataset ∈ {b_red, b_green, b_blue, s3_red}, tarea = nombres de run.py
(`real_A+init_z98.0_full`, `..._half0`, `..._half1`, `..._half0_scr`, `..._half1_scr`, `..._f0`..`_f4`):
- `metrics.jsonl`: una línea JSON por snapshot, épocas SNAPS = 0,1,2,3,5,8,12,20,30,40,60,80,120,160,240,320,400
  (0 = objeto inicial = "sin FPM" de A+init). Campos: `epoch`, `train_R` (media R afín sobre LEDs de entrenamiento),
  `heldout_R_ring_lt7` (media R sobre LEDs NO entrenados con anillo < 7 = C1 del fold; None en full),
  `n_train`, `n_heldout_ring_lt7`, `solver_err` (error interno del solver en esa época), `lattice`
  (cv_common.lattice_score), `wall_s`, `metric_s`, `per_led` = {"r,c": [R, piso_ruido, anillo, en_train]}
  — mismo formato que `per_led` de los tasks/*.json de run.py (R = F.affine_residual: ajuste meas ≈ s·pred + b,
  R = ||meas − fit|| / ||meas − mean(meas)||; OJO: NO es per_led_amplitude_residual de cv_common).
- `obj_eNNN.npy` (complex64, HR 1200² rojo / 2000² verde-azul) solo para full, half*, half*_scr (no para folds).
- `done.json`: metadatos (train, snaps, hist por época, hrpx, factor, lam, na, wall_s).

Cálculos para el análisis:
- C1(e) = media sobre f0..f4 de `heldout_R_ring_lt7` en la época e (criterios_b.py usa exactamente eso a e=40).
  Referencia sin FPM: `captura_2026-09-28b/<color>/out/tasks/real_nofpm_z98.0.json` (media de per_led[..][0] con anillo < 7).
- C2(e) = `F.band_mean(F.frc(obj_half0_eNNN, obj_half1_eNNN, hrpx), 2*0.07/lam, 0.45)`; nulo con half*_scr.
  F = fpm_red.py del dataset (iter_runner._load).
