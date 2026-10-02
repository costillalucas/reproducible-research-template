# FPM por teselas, rojo 28/09b, offset die (0, 4.06) mm (2026-10-02)

**Resultado: las teselas NO quitan las rayas. La causa probable es el preprocesado, no el k por LED.**
En `fpm_red.BF`, (18,14) y (18,16) se normalizan como campo claro (S/F·⟨F⟩, división por el flat) en todo el campo, aunque en ~86 % del campo son DF.
Con esos dos LEDs preprocesados como DF (S − gauss(F, 8)), **conservando todos los LEDs, en campo completo y sin teselas**, las rayas bajan de 0.396 a **0.010 rad** a la ép. 20, igual que die_sin18 (0.008 rad), con rampa de 0.01 rad (`dfnorm_test.py`, `dfnorm_test.json`).
Esto es solo a 20 épocas: no se corrió a 40 y falta el volumen.

## Qué se hizo
- `tiles.py`: arnés de teselas. No toca `src/` ni `iter_runner.py`. Cada tesela usa `IR.reconstruct_snap` (A+init idéntico) con todos los LEDs de la tarea full (225).
  El k de cada LED se calcula desde el centro de la tesela: `offset_eff = (0, 4.06) − (x_t, y_t)` [mm], con x = columnas, y = filas, medidos desde el centro del campo de 400 px.
  Signo verificado con los flats: (18,14) es brillante (BF) a fila alta y columna baja, y (18,16) a fila alta y columna alta. La resta acerca ese lado a la pupila.
  El tamaño de tesela no tiene restricciones: el factor sigue siendo 3, hrpx = 0.4267 µm y la ventana de crop entra.
- `stitch.py`: alinea la constante de fase global en el solape, cose con pluma lineal y mide rayas (`rayas2.rayas`) y rampa (`runner.ramp`).
- **Sanidad:** una sola tesela de 400 px con desplazamiento 0, ép. 5, sale **bit a bit idéntica** a `out/die/b_red/real_A+init_z98.0_full/obj_e005.npy` (max|diff| = 0.0).
- Corrida: 2x2, teselas de 232 px (inicios 0 y 168, solape de 64 px = 82 µm), 40 épocas, 4 procesos en paralelo, ~3 min.

## Números (ép. 40)
| objeto | rms rayas (rad) | período (µm) | MAD fondo (rad) | rampa p-p (rad) | Δy eq. (mm) |
|---|---|---|---|---|---|
| teselas 2x2 cosidas (todos los LEDs) | **0.418** | 62 | 0.75 | 0.16 | −0.000 |
| tesela (0,0) | 0.518 | 103 | 0.75 | 0.55 | −0.012 |
| tesela (0,168) | 0.551 | 102 | 0.79 | 0.59 | +0.014 |
| tesela (168,0) | 0.426 | 114 | 0.73 | 0.30 | +0.010 |
| tesela (168,168) | 0.280 | 134 | 0.74 | 0.64 | −0.005 |
| die full, todos los LEDs | 0.516 | 67 | 0.78 | 0.11 | +0.000 |
| die_sin18 full | 0.008 | 55 | 0.077 | 0.10 | +0.000 |
| nominal full | 0.116 | 119 | 0.31 | 17.8 | −0.283 |

Ép. 5: rayas de 0.12 a 0.16 en todas las teselas, contra 0.13 en die full y 0.005 en die_sin18 (`medidas_g2x2_232_e005.json`).
Con el die, ni el full ni las teselas tienen rampa global: la rampa sigue resuelta.
Las rampas por tesela (0.3 a 0.6 rad p-p) son residuos locales: no son la rampa de 17.8 rad del nominal.

Figura: `figs/fase_teselas_vs_full.png` (fase sin fondo lento a la ép. 40: teselas cosidas, die_sin18, die full).

## Interpretación
El mapa analítico BF/DF (`mapa_bfdf/`) da la frontera de (18,14),(18,16) a unos −171 µm del centro, y solo calza con radio BF 7.07 mm (z ≈ 101 mm o NA ≈ 0.072).
Con z = 98 y NA 0.07, el modelo los pone en DF en todo el campo, también en cada tesela: el desplazamiento de tesela de ~107 µm por eje no alcanza a cruzar el margen de 0.0059 µm⁻¹.
Por eso, en la tesela que contiene el lado brillante, (18,14) y (18,16) **no** quedan en BF en el modelo, y el error de k sigue en todas las teselas.
Teselar solo sirve si el radio pupila/frontera del modelo es el correcto.

## Variante con autoexclusión (z = 101 mm, radio BF ≈ 7.07 mm, el que calza con el mapa)
En cada tesela se excluyen solo los LEDs cuyo estado BF/DF cambia dentro de la tesela (según el modelo en una malla de 7x7 puntos). En el resto de las teselas se conservan.
Ép. 40, rms de rayas en rad:
- 2x2: cosido 0.278. Teselas que excluyen los dos LEDs (abajo): 0.010 y 0.015. Teselas que conservan uno (arriba): 0.41 y 0.29.
- 3x3: cosido 0.262. La única tesela que excluye los dos (232,116) da 0.013. Las demás quedan entre 0.09 y 0.39, incluso las dos que no excluyen ninguno porque el modelo los da DF puro.
- Referencia: z101 full con todos los LEDs = 0.469.

→ Cualquier tesela que conserve (18,14) o (18,16) tiene rayas, también donde el modelo los da DF en toda la tesela con margen.
El problema no es la k local. Es el blanco de intensidad de esos LEDs, que pasan por la división por flat.
La prueba `dfnorm` lo confirma (ver arriba).

## Siguiente paso sugerido
- Preprocesar (18,14),(18,16) como DF, o con un modelo mixto BF/DF por píxel, y correr 40/160 épocas con volumen pareado.
- Revisar lo mismo en verde (también son BF en la lista) y en el resto de LEDs de la lista BF con frontera dentro del campo.

## No hecho (por falta de tiempo)
- dfnorm a 40/160 épocas.
- Residuo de entrenamiento y volumen pareado de las teselas cosidas (`stitch.train_R` está escrito pero no se corrió).
