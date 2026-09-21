# Plan de experimentos: punto 3 y error de posición de LEDs (2026-09-21)

Estado: **plan + esqueletos ejecutables, ningún experimento completo corrido.**
Los números de costo son estimaciones a partir de cronometrar jobs reducidos
(ver "Cómo se estimó el costo"); la incertidumbre es ~2x.

Contexto (hitos 11-14 del roadmap): el descenso de gradiente (Adam) con
`loss="amplitude"` le gana a Wirtinger flow (WF) en fase, pero (i) todo se
midió con k redondeado a bin (favorable/"justo", no realista), (ii) en un solo
objeto real (Lena/Map, fase 0.3π, geometría "current" 9x9), y (iii) sin
ninguna captura real. Este plan ataca (i) y (ii).

## Scripts (en `scripts/`, todos con `--list`, `--dry-run`, `--exp`, `--out`, `--procs`)

| Script | Experimentos |
|---|---|
| `plan_common.py` | helpers (geometría con span fijo, objetos, k exacto + Poisson, errores de posición físicos) |
| `plan_p3_object_phase_geometry.py` | E1, E2, E3a, E3b, E4 (punto 3) |
| `plan_p4_led_position_error.py` | P1, P2, P3, P4 (error de posición, k exacto) |

Correr desde la raíz del repo. Dry-run verificado (`--dry-run`: 3-7 s por
script, crop 16, 3 iteraciones; **valida que corre, no da resultados
científicos**: en dry-run la calibración no se mueve porque 3 iteraciones <
`warmup_iterations=20`).

## Hallazgos de diseño que cambian cómo leer los resultados

1. **Umbral de overlap.** El "~28%" es el overlap de LEDs vecinos de la
   config actual en z=70 mm (medido: 27.5%). El roadmap ubicó el salto de
   calidad en 35% (z≈80 mm para "current"). Para "future" (NA 0.10) el
   overlap en z=70 ya es 47%; medido: 28% en z≈50 mm y 35% en z≈55 mm. Las tablas
   de z de E3a deben leerse contra ese cruce, no contra z=70.
2. **Confundido canvas/z.** Variar z a grilla fija cambia el NA máximo de
   iluminación, por tanto el canvas HR (el dry-run lo confirma: `hr=[80,80]`
   a z=50 vs `[48,48]` a z=70). Es el mismo confundido que invalidó el barrido
   de grilla anterior. Por eso hay **dos** diseños: E3a (z natural,
   confundido, con `hr` registrado) y E3b (span fijo = canvas fijo).
3. **E3b no separa overlap de redundancia**: a span fijo, más LEDs sube ambos.
   Esa separación es la tarea del otro agente (hito 15); interpretar E3b
   junto a su resultado.
4. Sólo hay dos imágenes en `data_source` (Lena, Map). "Más objetos" se
   construye con: roles intercambiados (`map_lena`), fase pura (`phase_only`),
   `blob` suave y estrella de Siemens de fase (`siemens_star`, detalle radial
   fino). Sin más fotografías el rango de texturas es limitado.

## Punto 3

Base común: canal verde salvo E4, crop 32, grilla 9x9 salvo E3, WF 200 épocas
vs Adam-amplitude 100 iter, Poisson con pico 100 y 1000 fotones (1000 = donde la
fase empezó a ser recuperable; 100 = ruidoso). Métrica: `phase_corr` (y
`amp_corr`) de `metrics.compare_to_ground_truth`; se reportan también `wf_*`
para la diferencia GD−WF por seed. Costo por job ≈ 0.8 min-core (9 LEDs, 32 px).

### E1 — objeto × magnitud de fase × fotones  (prioridad **1**)
- **Hipótesis:** la ventaja de GD-amplitud sobre WF persiste en todos los
  objetos, y el umbral de recuperabilidad de fase se corre a más fotones cuando
  la fase baja de 0.3π a 0.05π (señal ∝ φ).
- **Variables:** objeto {lena_map, map_lena, phase_only, blob, siemens_star} ×
  fase_max {0.05, 0.1, 0.2, 0.3}π × pico {100, 1000}.
- **Seeds:** 4 (160 jobs). Con 2 seeds: 80 jobs.
- **Costo:** ~130 min-core (4 seeds) / ~65 (2 seeds).
- **Refutación:** GD < WF (diferencia media de `phase_corr` < 0 y ≥ 3 de 4
  seeds en contra) en ≥ 1 objeto a pico 1000 con fase ≥ 0.2π → la ventaja
  es específica de Lena/Map. Sin refutación pero `gd_phase` < 0.5 para fase ≤
  0.1π a pico 1000 → "fase débil no recuperable" (resultado negativo útil).

### E2 — contraste de amplitud  (prioridad **3**)
- **Hipótesis:** menor contraste de amplitud (min_amp→1, objeto de fase casi
  puro) empeora la recuperación de fase para ambos, más para WF (la amplitud
  ancla la fase en la inicialización desde el LED central).
- **Variables:** `min_amplitude` {0.1, 0.3, 0.6, 0.9, 1.0} × fase {0.1, 0.3}π ×
  pico {100, 1000}, objeto lena_map.
- **Seeds:** 4 (80 jobs). **Costo:** ~65 min-core (2 seeds: ~32).
- **Refutación:** `gd_phase` a min_amp=1.0 ≥ `gd_phase` a 0.1 (±0.05) → el
  contraste de amplitud no importa para GD. Ojo: con amp=1 la inicialización
  `sqrt(centro)` es plana; si GD falla ahí, es un problema de init, no de solver.

### E3a — barrido natural de z, dos objetivos  (prioridad **5**, confundido)
- **Hipótesis:** la calidad de fase sube abruptamente al cruzar overlap ≈
  28-35% para ambos solvers; "future" cruza a z menor.
- **Variables:** objetivo {current, future} × z {50, 60, 70, 80, 90, 100} mm ×
  pico {100, 1000}; grilla 9x9, pitch 6 mm. Se registran `overlap` y `hr`.
- **Seeds:** 4 (96 jobs). **Costo:** ~80 min-core (canvas mayor a z bajo: más caro).
- **Refutación:** no aparece un salto al cruzar el umbral (curva `phase_corr`
  vs `overlap` monótona suave) → el umbral 35% no es una propiedad del solver
  ni de la simulación sino del canvas. **Advertencia:** cualquier efecto está
  mezclado con el tamaño del canvas; no concluir causalidad sólo con esto.

### E3b — span fijo (canvas fijo), variar cantidad de LEDs  (prioridad **2**)
- **Hipótesis:** a canvas fijo y pico 1000, `phase_corr` sube con el número de
  LEDs (7→21) y "future" (NA 0.10) es mejor que "current" a igual grilla por
  más overlap.
- **Variables:** objetivo {current, future} × grilla {7, 9, 11, 15, 21} a span
  48 mm (z 70) × pico {100, 1000}.
- **Seeds:** 4 (80 jobs). **Costo:** ~130 min-core (grillas 15/21 ≈ 2-5x más caras).
  Con 2 seeds y sin grilla 21: ~45.
- **Refutación:** `phase_corr` plana (±0.05) de 9 a 21 LEDs en ambos
  objetivos → más LEDs no ayudan a canvas fijo; contradiría el hito 13.
  Asertar que `hr` es constante dentro de cada objetivo (el script lo registra).

### E4 — canal (rojo/verde/azul) × ruido  (prioridad **4**)
- **Hipótesis:** el azul sigue fallando a pico ≤ 20 para todo solver; con
  amplitude-loss rojo y verde ganan a pico 100-1000 (replicar con lena_map).
- **Variables:** canal × pico {20, 100, 1000}; **seeds** 4 (36 jobs).
- **Costo:** ~30 min-core. **Refutación:** azul con `gd_phase` > 0.5 a pico
  20 (contradice el hito 11), o GD < WF en rojo/verde a pico ≥ 100.

## Error de posición de LEDs (exact-k), (b)

Datos: modelo continuo (`jc.simulate_lr_stack_continuous`, sin redondear k) +
Poisson. Los errores se parametrizan **físicamente** (mm/grados) y se reporta
`k_err_bins` = RMS de (k verdadero − nominal) en bins del espectro HR. Los
solvers reciben el grid **nominal**: `wf` (redondea a bin), `gd_nominal`
(posiciones fijas), `gd_rigid` (objeto + transformación de similitud,
calibración conjunta), `gd_perled`, y `gd_true` (oráculo: posiciones
verdaderas; cota superior). Errores tabulados en `ERR` del script: jitter
0.05/0.2 mm, offset 0.5/2 mm, rotación 1°/3°, z +2/+7 mm, pitch +1%, y un
"combined" plausible (jitter 0.1 mm, offset ~1 mm, rot 1.5°, z +3 mm, pitch
+0.5%). **Ojo, los bins escalan con el canvas** (bin = 1/(HR px × tamaño de píxel)): el mismo error
físico "combined" mide 0.73 bins a crop 16, **1.47 a crop 32** y 2.2 a crop 48
(medido con `perturbed_grid`); por tipo a crop 32: jitter 0.05 mm 0.07, jitter
0.2 mm 0.28, offset 0.5 mm 0.59, rot 1° 0.40, z+2 mm 0.56, pitch+1% 0.20,
offset 2 mm 2.4, z+7 mm 1.9. La calibración rígida sólo recuperaba hasta
~0.5-0.8 bin (hito 11), así que a 32 px el "combined" ya está **más allá** del
acantilado esperado y varios errores individuales caen justo en él: buena
zona para P1/P3, pero P4 (crop) confunde error físico y bins: comparar por
error físico, no por `k_err_bins`.

Costo por job ≈ 3 min-core (5 reconstrucciones; medido: ~0.28 s por
iteración de GD a 32 px, 9 LEDs).

### P1 — tipo y magnitud de error, pico 1000  (prioridad **1**, la incógnita dominante)
- **Hipótesis:** `gd_nominal` degrada rápido con `k_err_bins` (ya visto: 0.995 →
  0.09 con redondeo a bin, ~0.4 bin de error); WF sobre grid nominal degrada
  menos porque su modelo ya es bin-redondeado; `gd_rigid` recupera los errores
  con estructura global (offset, rotación, z, pitch → transformación de
  similitud casi exacta) pero **no** el jitter por LED; `gd_perled` sólo ayuda
  con jitter y a veces sobreajusta.
- **Variables:** 11 tipos de error (incluye control "none") × 4 seeds = 44 jobs.
- **Costo:** ~130 min-core (2 seeds: ~66).
- **Refutación:** (a) `gd_nominal` > `wf` con `k_err_bins` ≥ 0.5 → el
  inverse-crime no importa tanto como se temía; (b) `gd_rigid` no supera a
  `gd_nominal` en offset/rot/z/pitch con `k_err_bins` < 0.5 → la calibración
  conjunta no sirve ni en el caso que debería. Reportar también
  `k_err_after_rigid` (¿bajó?).

### P3 — escalado del error "combined" ×0.1…×2: acantilado de calibración  (prioridad **2**)
- **Hipótesis:** existe un `k_err_bins` crítico (~0.5-0.8) por encima del cual
  `gd_rigid` no converge; debajo, `gd_rigid` ≈ `gd_true`.
- **Variables:** multiplicador del error "combined" {0.1, 0.25, 0.5, 1, 2} (≈0.15-2.9 bins a 32 px) × 4 seeds = 20 jobs.
- **Costo:** ~60 min-core. **Refutación:** `gd_rigid` mejora a `gd_nominal` (>0.2
  de fase) también con ×1-×2 (>1.5 bins) → el acantilado de 0.8 bin del hito 11 era del
  objeto/init, no un límite del método. Si el acantilado aparece, insumo para
  decidir si hace falta calibración previa (`led_calibration.py`, campo brillante).

### P2 — "combined" × ruido × canal  (prioridad **3**)
- **Hipótesis:** menos fotones (pico 100) empeora la calibración de k más que
  la del objeto; el azul (mayor k, peor SNR) falla primero.
- **Variables:** canal {green, red, blue} × pico {100, 1000, 10000} × 4 seeds =
  36 jobs. **Costo:** ~110 min-core (2 seeds: ~55).
- **Refutación:** `gd_rigid` ≈ `gd_true` (±0.05) a pico 100 en verde → el
  ruido no limita la calibración.

### P4 — tamaño de crop  (prioridad **4**)
- **Hipótesis:** crops chicos (16 px) dan poca señal de posición y sobreajustan
  (`per_led` peor que `rigid`); a 48 px `rigid` mejora.
- **Variables:** crop {16, 32, 48} × 4 seeds = 12 jobs. **Costo:** ~50 min-core
  (48 px ≈ 2-3x más caro; y ver el aviso de bins vs canvas arriba). **Refutación:** `gd_rigid` no cambia con el crop
  (±0.05) → el crop no es el cuello de botella.

## Plan de ejecución sugerido (presupuesto de CPU)

Orden por prioridad, y versión "rápida" (2 seeds) si el presupuesto es de
~1 hora en 2 cores (~120 min-core): P1 (66) → P3 (30) → E1 (65, luego la
mitad si falta tiempo) → E3b (45). Con 4 cores libres el orden completo con 4
seeds de P1, P3, E1, E3b, E2, P2 ronda ~550 min-core (~2.3 h en 4 cores).
Preferir correr 2 seeds y ampliar sólo los experimentos cuyo resultado sea
ambiguo.

```
python3 scripts/plan_p4_led_position_error.py --exp P1 --seeds 2 --procs 2 --out p1.json
python3 scripts/plan_p4_led_position_error.py --exp P3 --seeds 2 --procs 2 --out p3.json
python3 scripts/plan_p3_object_phase_geometry.py --exp E1 --seeds 2 --procs 2 --out e1.json
python3 scripts/plan_p3_object_phase_geometry.py --exp E3b --seeds 2 --procs 2 --out e3b.json
```

## Cómo se estimó el costo

Cronometrado en 1 core con otros agentes corriendo (puede inflar tiempos):
E1 a 32 px con 10 épocas WF + 10 iter GD: 3.6 s; con 20+20: 6.3 s
(≈0.27 s por par época+iter, más ~0.9 s fijos) → ≈0.8 min-core para 200+100
(extrapolación, no medido completo). P1 a 32 px: 12.2 s con 10/10/10 y 23.6 s
con 10/20/20 (≈0.28 s por iteración de GD, 4 corridas GD + 1 WF) →
≈2.7-3 min-core para 100 iter de GD + 150 de calibración. Los jobs con más
LEDs (E3b, 15/21) o canvas mayor (E3a a z bajo) son más caros.

## Limitaciones

- Todo sintético; el error de posición aquí es una parametrización razonable
  pero inventada. Los rangos (mm/grados) hay que cambiarlos por los del
  hardware real apenas haya una medición del array.
- Los objetos "nuevos" son sintéticos o reordenamientos de las mismas dos
  fotos.
- Registro de procedencia (`compute_numbers.py`/`claims.yaml`) no se toca aquí:
  cualquier resultado de estos experimentos debería entrar allí sólo después de
  correrse completo.
