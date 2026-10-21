# Captura roja 21/10 (tarde): muestra nueva de esferas de 500 nm, misma geometría que la mañana

Muestra `~/Documents/AleYLu/imagenes_tomadas/2026-10-21.500`: esferas estándar de poliamida de 500 nm, 15x15 LEDs (filas 10–24,
columnas 8–22), 2 frames por LED. Exposiciones: cruz BF a 8 ms, anillo de 8 a 128 ms y el resto a 257 ms. La geometría no cambió
respecto de la mañana: z, matriz y ROI (4000, 1942), y `precaptura.py centro` da (+0.012, +0.013) pasos sobre (17,15). El flat es el
de la mañana (`2026-10-21-sinmuestra`, decisión del usuario) y los oscuros son de `2026-10-21-dark` (5, 8, 128 y 257 ms).
El pipeline es el de `../captura_2026-10-21/`, reutilizado sin reescribirlo; los cambios se listan en §2.

**Resumen.**
1. **Datos:** son buenos. Hay entre 2.5 y 4 veces más contraste DF que a la mañana, la SNR por frame es ≥ 3 hasta el anillo 8 y el
   piso de ruido del held-out es 0.05 (a la mañana, 0.22). No hay saturados ni movimiento de la muestra entre frames.
2. **Criterios C1–C4 (rojo_final):** C1 pasa por muy poco (R held-out 0.889 frente a 0.995 sin FPM; el límite es 0.895), C3 y C4
   pasan, y **C2 falla y queda más lejos que nunca**: 0.011 con un nulo de 0.009 (la mañana dio 0.044 y 28/09b 0.120).
3. **El modelo no predice esta muestra:** el R held-out es 0.88–0.90 en *todos* los anillos, con un piso de ruido de 0.02–0.12. El
   problema no es de SNR. Tampoco es el offset del recorte: con x = −0.34, 0 o +0.34 mm, C1 da 0.8917, 0.8915 y 0.8921.
4. **Las esferas aisladas no son esferas sueltas.** Los puntos "aislados" del BF crudo (FWHM 7.8 µm; la teoría coherente con NA_obj da
   6.6 µm) aparecen en la reconstrucción como agregados de varios µm (cruces, Y, cadenas). Esas formas se repiten en las 2 mitades y
   no aparecen en el nulo.
   - El ancho promediado de esos objetos es ~3 µm en las mitades, contra 5–8 µm en el nulo y 7 µm en el crudo. El límite de la NA
     sintética está entre 0.86 y 1.0 µm, así que no se llega a él.
   - El FRC local sobre los objetos, en la banda de C2, da 0.152 contra 0.085 del nulo. Queda justo en el umbral (exceso de 0.067 contra
     el 0.068 que se pide): hay una señal marginal, **no** concluyente.
5. **Respuesta a la pregunta clave:** que la muestra tenga más contraste **no** hace pasar a C2 y, en el FRC global, ni siquiera lo
   acerca. La limitación pasó de la SNR (mañana) a un error de modelo (esta muestra). La única señal favorable es local, sobre
   agregados, y es marginal.

## 1. QC (`scripts/precaptura.py qc` → `figs/precaptura_qc.png`; `eval/qc_frames.py` → `logs/qc_frames.log`)

- **Completitud:** 225/225 LEDs, 2 frames por LED. Los oscuros cubren todas las exposiciones y no hay saturados (ni en la muestra ni
  en el flat).
- **Flat:** la cruz BF del flat está a 5 ms y la de la muestra a 8 ms (`precaptura` lo marca [CORREGIR]). El preprocesado ya normaliza
  cada imagen por su propio t_ef = t − 0.20 ms después de restar el oscuro de su misma exposición, así que no hizo falta cambiar nada.
- **Señal por anillo** (mediana, cuentas/ms y SNR por frame). La mañana dio 2.8 cuentas en el anillo 8, ahora son 11.1, unas 4 veces más:

| anillo | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| c/ms | 96.8 | 39.7 | 0.39 | 0.26 | 0.16 | 0.11 | 0.077 | 0.056 | 0.043 | 0.032 | 0.026 |
| SNR/frame | 50 | 36 | 12 | 12 | 9.0 | 7.1 | 5.4 | 4.2 | 3.4 | 2.7 | 2.3 |

- **Contraste DF por anillo**, que es lo que ve el solver: mediana de std(I) en `eval/datos_cmp.py`.

| anillo | 2 | 3 | 4 | 5 | 6 | piso de ruido del R (anillos < 7) |
|---|---|---|---|---|---|---|
| **r500 (tarde)** | 0.89 | 0.56 | 0.31 | 0.19 | 0.13 | **0.050** |
| r21 (mañana) | 0.29 | 0.15 | 0.08 | 0.05 | 0.03 | 0.204 |
| m2 (16/10) | 1.05 | 0.41 | 0.21 | 0.13 | 0.08 | 0.077 |
| 28/09b | 1.31 | 0.94 | 0.62 | 0.34 | 0.17 | 0.027 |

- **BF:** muestra/flat da 0.70 de media en el BF (17,15). La muestra quita ~30 % de la luz BF (extinción y dispersión fuera de la NA),
  así que es una muestra densa y fuerte. La ganancia del ajuste fotónico es 0.28 (a la mañana, 0.19).
- **Movimiento:** se descarta entre los 2 frames de cada LED (~0.3 s). var(f1−f2) da 0.8–1.3 veces lo esperado por ruido y la
  correlación f1–f2 es ≥ 0.98.
- **Defecto de adquisición, nuevo:** en el LED (15,15), que es el primero a 128 ms, el **frame 1 sale casi a oscuras** en los 3 sets:
  muestra .500 con 7 frente a 101 cuentas, muestra de la mañana con 1.6 frente a 23 y flat con 1.4 frente a 5.4. El pipeline promedia
  los 2 frames, así que ese LED entra con ~la mitad de intensidad (en el held-out solo pesa por escala). Conviene descartar el
  frame 1 de ese LED, o el primer frame tras un cambio de exposición, en el software de captura.
- **Recorte (filas 140:540, columnas 560:960, 400 px):**
  - Va arriba a la derecha del centro del ROI.
  - Evita la aguja de abajo a la izquierda, las partículas oscuras grandes de (650, 520) y (740, 760) y el arco óptico de la derecha.
    La mancha de polvo de la mañana en (600, 572) queda fuera.
  - La máscara de polvo, calculada desde el flat, enmascara 332 px (0.21 %).
  - Vista del campo: `eval/vista_campo.py`.

## 2. Reconstrucción (`prep_500.py`, `r500_red/`, `runner_500.py`, `run160.sh`)

- **`prep_500.py`** es una copia de `prep_2110.py` con estos cambios: la carpeta de la muestra, el recorte, el BF de la muestra a 8 ms
  y el oscuro de 8 ms.
- **`runner_500.py`** envuelve `runner_2110.py` sin copiarlo. Registra `r500_red` y la variante `rojo_500`, que es `rojo_centrado`
  (z 102, lrpx 1.29, NA 0.0669, factor 3, sin exclusiones) con el offset del recorte, el mismo sistema no telecéntrico que a la mañana:
  - y: +220 px · 0.0017 mm/px = **+0.374 mm**;
  - x: −200 px → **−0.340 mm**. Está en `r500_red/fpm_red.py` (`CROP_OFFSET_X_MM`), porque `runner_2110` fija offset_x = 0. El signo
    es el de las filas: los arcos del flat de la mañana dan la misma orientación en filas y columnas.
- **Corridas:** full, mitades, mitades mezcladas y 5 folds a 160 épocas, con 3 procesos. Tardaron 58 min de reloj.
- **Control de signo de x** (`run_xoff.sh`, folds a 40 épocas): C1 da 0.8915 con x = 0 y 0.8921 con x = +0.34 mm, contra 0.8917 con
  x = −0.34 mm. El held-out por anillo es idéntico en los tres casos. El offset no es lo que limita.

## 3. Criterios y comparación (mismas definiciones; `eval/criterios_r500_red.json`, `resolucion_r500_red_final.json`, `heldout_anillos.json`)

| | 28/09b `rojo_final` | 21/10 mañana `rojo_centrado` | **21/10 tarde `rojo_500`** |
|---|---|---|---|
| C1 R held-out e40 / e160 (sin FPM) | 0.420 / 0.374 (0.986) | 0.724 / 0.708 (0.982) | **0.892 / 0.889 (0.995)**, pasa por 0.006 |
| piso de ruido medio de esos LEDs | 0.050 | 0.219 | 0.060 |
| C2 FRC [2NA/λ, 0.45] e40 / e160 (umbral 0.143), nulo | 0.085 / 0.120, 0.007 | 0.029 / 0.044 | **0.015 / 0.011**, nulo 0.012 / 0.009, falla |
| C3 lattice e160 (≤ 0.01) | 1.9e-3 | 1.0e-4 | 3.1e-4, pasa |
| C4 nuevas en ambas mitades e160 (azar) | 28 % (5.5 %) | 39 % (8.5 %) | 47 % (13 %), pasa, 2647 blobs |
| FRC complejo ≥ 1/7, e40 / e160 | 4.1 / 3.55 µm | — / 5.06 µm | 7.9 / 8.8 µm |
| FRC complejo sobre el nulo, e160 | 1.6 µm | 3.0 µm | 7.3 µm |
| FRC de fase ≥ 1/7, e160 | 3.7 µm | 5.4 µm | no cruza (e40: 18.5 µm) |
| FRC entre los 2 BF crudos, k para FRC 1/7 (1/µm) | 0.139 | 0.091 | 0.103 |
| rampa global de fase p-p, e160 | 0.027 rad | 0.004 rad | 0.029 rad |
| R held-out mediano por anillo, del 1 al 7 | 0.89 → 0.25 | 0.75 / 0.67 → 0.74 | **0.88 / 0.88 / 0.89 / 0.90 / 0.89 / 0.88 / 0.90** |

- **Lectura:** con 4 veces más señal y un piso de ruido 4 veces más bajo que a la mañana, el held-out empeora (0.89 frente a 0.71) y es
  plano en todos los anillos.
  - En 28/09b, que tiene un piso parecido, baja de 0.89 a 0.25 con el anillo. Aquí el modelo explica solo ~20 % de la varianza de
    las imágenes DF que no vio (1 − R² ≈ 0.21), y eso no es ruido.
  - El FRC entre mitades se corta en ~NA/λ (`figs/frc_r500.png`): lo que el solver pone por encima de NA_obj no es reproducible a
    escala global.
  - Las causas candidatas, sin verificar, vienen de la naturaleza de la muestra:
    - es densa y gruesa: hay agregados 3D y cadenas, y el BF cae al 70 %, de modo que el modelo de objeto delgado multiplicativo
      deja de valer;
    - hay dispersión múltiple;
    - puede haber esferas en más de un plano.
  - La geometría queda descartada como causa: el control de offset en x da lo mismo, la de la mañana con esta misma geometría daba
    0.71 y el eje está verificado.
- **C4 pasa con holgura**, pero en esta muestra no discrimina: la textura granular de la reconstrucción da miles de blobs (6357), y
  el 13 % coincide con las mitades corridas al azar.

## 4. Resolución directa con esferas (`eval/esferas.py` → `esferas_r500_red*.json`, `figs/esferas_r500_red_relajado.png`)

Esto se agregó a pedido del usuario. **Teoría coherente**, con PSF de amplitud 2J1(v)/v y FWHM = 0.705·λ/NA a λ = 0.63 µm:

| NA | FWHM |
|---|---|
| NA_obj 0.0669 | 6.64 µm |
| NA_sint con anillos < 7 (0.438) | 1.01 µm |
| NA_sint con anillos ≤ 8 (0.517) | 0.86 µm |
| NA_sint con todas las LEDs (0.573) | 0.77 µm |

El píxel HR es de 0.43 µm, así que el FWHM mínimo medible es ~0.86–1.0 µm (validado con gaussianas sintéticas).

- **Detección:** picos de |LoG| en el BF crudo. Con aislamiento estricto (nada a < 15 µm) quedan solo **2** objetos: el campo es
  denso. Con aislamiento relajado (pico vecino < 0.6 a < 10 µm y anillo de 7–10 µm < 0.8 de la amplitud central) quedan **34**.
- **Cómo son en la reconstrucción:** no son puntos. Son agregados de 3–10 µm con brazos de ~1–2 µm (cruces, Y, cadenas) dentro de una
  mancha cruda de 7–8 µm. La forma se repite en la mitad 0 y la mitad 1 y no aparece en el nulo (filas 2–5 de la figura). Es evidencia
  cualitativa de estructura reproducible por debajo de la resolución de NA_obj, pero no es una PSF puntual.
- **Mediciones (34 objetos):**

| medición | valor |
|---|---|
| FWHM del crudo, por objeto | **7.8 µm** (rango intercuartil 6.9–8.5) |
| \|Δo\| full / mitades / nulo, por objeto (mediana) | 1.8 / 2.4–3.1 / 1.2–1.4 µm. **No sirve como medida:** el máximo local de una textura ruidosa da el tamaño de grano (el nulo sale más "fino") |
| promedio del Δo complejo alineado en el centroide crudo, sin sesgo: mitad 0 / mitad 1 | **3.0 / 3.2 µm** |
| ídem, nulo 0 / nulo 1 | **5.3 / 7.9 µm** |
| ídem, crudo | **7.0 µm** |
| promedio cruzado (centro y fase de una mitad, promedio de la otra): mitades | 2.1 / 4.6 µm |
| ídem, nulo | 4.6 / 7.1 µm |
| **FRC local** (Hann de 20 µm sobre los 34 objetos), banda C2 [2NA/λ, 0.45]: mitades / nulo | **0.152 / 0.085** (medias 0.196 / 0.095) |
| ídem, en 300 ventanas al azar: mitades / nulo | 0.135 / 0.104 |
| ídem, banda [0.45, 0.9]: objetos | 0.113 frente a 0.072 del nulo |
| ídem, banda [0.45, 0.9]: azar | 0.093 frente a 0.068 |
| refoco digital ±40 µm (FWHM por objeto) | dz = 0 es un mínimo local (1.8 µm, contra 2.5–3.6 µm a ±5–20 µm); no hay evidencia de desenfoque |

- **Lectura:** los objetos se ven 2–3 veces más angostos que en el crudo y de forma reproducible. Eso equivale a una NA efectiva
  ~0.15–0.2, muy por debajo de la NA sintética de 0.44–0.57.
  - Sobre los objetos, el FRC local en la banda de C2 llega justo al umbral 1/7, con un exceso sobre el nulo de 0.067 (C2 pide 0.068).
    Es la señal más cercana a "pasa" que se vio en una medición local, pero es marginal, con n = 34 y sin intervalo de confianza.
  - Hace falta un campo con esferas sueltas de verdad (más diluido) para medir una PSF limpia.

## 5. Conclusión y siguientes pasos

- Más contraste no alcanza: esta muestra es demasiado densa y gruesa para el modelo de objeto delgado. C1 empeora y C2 global falla
  peor.
- Lo útil del set:
  1. confirma que la geometría (eje, offset y NA) no es lo que limita, porque C1 es insensible a ±0.34 mm en x;
  2. muestra estructura reproducible de ~2–3 µm dentro de manchas de 7–8 µm;
  3. detectó el defecto del frame 1 en (15,15).
- **Para una prueba limpia de superresolución:**
  1. esferas de 500 nm **diluidas** (separadas > 15–20 µm), monocapa secada o pegada al vidrio, en foco;
  2. mismo esquema de exposición: es el que da SNR ≥ 3 hasta el anillo 8;
  3. medir la PSF con `eval/esferas.py` (FWHM de mitades contra el nulo, y FRC local).
- **Tests baratos posibles sobre este set:**
  - barrido de z del solver o de desenfoque de pupila a 40 épocas, para un plano de muestra distinto;
  - un recorte más chico en una zona menos densa.

## Figuras

- `figs/recon_r500.png`: BF crudo (amplitud) frente a la amplitud y la fase reconstruidas (full, e160), con el recorte entero de 516 µm
  y un zoom de 60 µm.
- `figs/frc_r500.png`: FRC entre mitades (complejo y fase) con el nulo, r500 frente a la mañana y 28/09b; R held-out por anillo con el
  piso de ruido.
- `figs/esferas_r500_red_relajado.png`: 6 objetos aislados (crudo, \|Δo\| full, mitad 0, mitad 1 y nulo) y perfiles radiales
  medianos. `esferas_r500_red.png` es la versión estricta (2 objetos).
- `figs/precaptura_qc.png`: salida de `precaptura.py qc`.
