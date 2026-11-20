# Aislar antes o recortar después (20/11/2026)

**Pregunta.** ¿Reconstruir una ventana chica aislada alrededor de una partícula da la misma partícula que reconstruir
un campo más grande y recortarla después?

- **A:** se reconstruye un recorte de 200x200 px crudos (258 µm) y después se corta la ventana de la partícula.
- **B20:** se recorta primero la imagen cruda, 20x20 px (25.8 µm) centrados en la partícula, y esa ventana se
  reconstruye sola.

Toma: rojo, 21x21 LEDs, `2026-11-18.2048ms`, z 143.5 mm, NA 0.0747, factor 3 (píxel reconstruido 0.43 µm),
160 épocas, `--validar`. Flat, oscuros y `centro.json` son los mismos que en `2026-11-18/correr.sh`.

## ESTADO / CÓMO SEGUIR (20/11, 17:35, antes de reiniciar la PC)

- **Hecho:**
  - 5 recortes A de 200 px;
  - selección de 15 partículas (`seleccion.json`);
  - B20 de **11 de las 15** partículas (P01–P07, P09, P11, P13, P14);
  - comparación de esas 11 (`tabla.csv`, `resultados.json`, figuras).
- **Faltan 4 B20:**

  | id | recorte (`--recorte`) | carpeta |
  |---|---|---|
  | P08 | 596,685 | B20/f596_c685 |
  | P10 | 627,672 | B20/f627_c672 |
  | P12 | 639,742 | B20/f639_c742 |
  | P15 | 678,731 | B20/f678_c731 |

  Las cuatro están en el cuadrante A_200_526_581, que terminó último. Son partículas chicas: extensión de 4–5 µm,
  redondas.
- **Para terminar:** correr `./codigo/continuar.sh` desde esta carpeta. Tarda unos 4 min.
  - Lanza solo los B20 que faltan: saltea las carpetas que ya tienen `resumen.txt` y borra las corridas a medio hacer.
  - Después rehace `tabla.csv`, `resultados.json` y las figuras con `codigo/comparar2.py`.
  - No vuelve a elegir partículas: usa `seleccion.json` tal cual.
- **B40 (40x40 px): NO se corrió.** Si se quiere agregar: `./codigo/correr_B.sh 40 3` y después
  `python3 codigo/comparar2.py .`.
  - Unos 15 min.
  - `comparar2.py` ya agrega B40 a la tabla y a las figuras si existe la carpeta `B40/`.
- Todo lo necesario está en esta carpeta. Nada depende de /tmp.

## Qué se corrió (comandos exactos)

1. **A, recorte por defecto** (lo más cerca del eje: filas 426:626, col 481:681): `codigo/correr_A.sh`.
   ```
   python3 scripts/reconstruir.py $I/2026-11-18.2048ms --flat $I/2026-11-18.2048ms-sinmuestra \
     --dark-flat $I/2026-11-18.2048ms-sinmuestra-dark --dark $I/2026-11-18.2048ms-dark \
     --centro $C/2026-11-18.2048ms-prueba-0959/centro.json --na 0.0747 --tam 200 --epocas 160 --validar --nucleos 3 \
     --salida A_200
   ```
2. **4 recortes A más,** `codigo/correr_A_tejas.sh`.
   - Mismo comando, con `--recorte 326,381 | 326,581 | 526,381 | 526,581` (los 4 cuadrantes del recorte de 400 px del
     18/11) → `A_200_<fila>_<col>`.
   - **Motivo:** el recorte por defecto tiene solo ~7 objetos que pasan los criterios, y hacían falta 15 aislados.
3. **Selección:** `EXT_MAX=22 EL_MAX=2.3 python3 codigo/detectar.py .` → `seleccion.json`, `fig_seleccion.png`.
4. **B20 por partícula:** `codigo/correr_B.sh 20`.
   - Mismo comando que A, con `--recorte <fila>,<col> --tam 20 --nucleos 1`, hasta 3 corridas en paralelo.
   - Salida en `B20/f<fila>_c<col>`.
5. **Comparación:** `python3 codigo/comparar2.py .` → `tabla.csv`, `resultados.json`, `fig_dispersion.png`,
   `fig_grilla_B20.png`.

`reconstruir.py` funcionó a 20 px sin tocarlo, con `--validar` incluido. Cada B20 tarda 1.3–1.7 min, y la mayor parte es
la lectura de las 441 imágenes. Cada A tarda 7.5–10 min.

En cada B20, el offset de LED por posición (corrección no telecéntrica) está en su `resumen.txt`.
- Va de 0.14 a 0.43 mm según la partícula.
- En A hay un solo offset para todo el recorte: ≈0 en el recorte por defecto y ±0.24 mm en los cuadrantes.
- Esto es una diferencia real entre los dos caminos, no solo de tamaño. El control A vs A' de abajo muestra que un
  cambio de offset de ese orden casi no cambia la partícula.

## Desvíos del plan (importante)

1. **El volumen de fase de octubre no se puede usar en esta toma.**
   - En las reconstrucciones A, las partículas tienen amplitud ≈ 0 en el centro: |o|/fondo mínima < 0.3 en 9 de las 11
     ventanas A medidas.
   - Por eso hay vórtices de fase y la fase desenvuelta no es confiable.
   - La segmentación de octubre (umbral de fase, `results/rojo_fase_2026-10-20/analisis.py`) encontró solo 6 objetos en
     el recorte por defecto. Está en `codigo/detectar_v1_fase_octubre.py`, que no se usó para la selección final.
   - El V "de octubre" (fase desenvuelta − plano del anillo, integrada en r ≤ 6 µm) se calcula igual y queda en la tabla
     (`V_A20`, `V_B20`, columna `vortice`). En A da casi siempre **negativo**: de −25 a +3 rad·µm². Por eso **no se
     informa d_vol**: no tiene sentido físico acá.
2. **Detección por desvío complejo,** D = |o/fondo − 1| (`codigo/detec_comun.py`).
   - "Aislada" quiere decir: ningún otro objeto (D_max ≥ 0.2) dentro de la ventana B20, la ventana a ≥ 10 px crudos
     del borde de A, D_max ≥ 0.3, extensión ≤ 22 µm y elongación ≤ 2.3.
   - Los criterios más estrictos (extensión ≤ 15 µm, elongación ≤ 1.7) dejaban 1 sola partícula en el recorte por
     defecto.
   - **Muchas de las elegidas NO son esferas limpias:** son manchas de 14–21 µm de extensión con elongación ~2. Solo
     P08, P10, P12, P13 y P15 son chicas y redondas (3–5 µm).
3. **Medidas usadas en lugar del volumen de fase.** Son la misma función, con el mismo centro físico y la misma apertura
   (r ≤ 6 µm, fondo en el anillo de 8–11 µm), aplicada a la ventana de A y a B.
   - S = ∫(o/fondo − 1): la integral compleja, que no necesita desenvolver.
   - Área oscura = ∫(1 − |o|/|fondo|).
   - Correlación compleja ρ_c de (o/fondo − 1), y la misma correlación tras un pasa-altos (se quita la gaussiana compleja
     de σ 3 µm): ρ_c_hp.
   - Pearson de amplitud y de fase.
   - Desplazamiento A↔B.
4. **Control A vs A'.** Dos partículas (P03 y P06) caen también dentro de un segundo recorte A. Comparar sus dos ventanas A
   da la variación entre dos reconstrucciones "grandes" con distinto recorte y distinto offset.

## Resultados (11 partículas con B20)

| id | A | ROI (fila, col) | V A / B20 (rad·µm²) | vórtice A / B | \|S\| A / B20 (µm²) | fondo B/A | ρ_c | ρ_c_hp | estructura fina B/A (sin normalizar) | C1 A / B20 | C2 ventana A / B20 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P01 | A_326_381 | (370, 545) | 3.2 / −34.6 | 1 / 1 | 6.8 / 42.1 | 0.32 | 0.37 | 0.54 | 1.04 | 0.581 / 0.657 | 0.28 / 0.27 |
| P02 | A_326_381 | (452, 456) | −3.8 / −50.2 | 1 / 1 | 32.5 / 60.2 | 0.27 | 0.63 | 0.66 | 0.91 | 0.581 / 0.704 | 0.51 / 0.28 |
| P03 | A_326_581 | (457, 657) | −7.1 / −12.1 | 0 / 1 | 6.7 / 23.6 | 0.23 | 0.38 | 0.60 | 0.97 | 0.590 / 0.693 | 0.39 / 0.51 |
| P04 | A | (458, 577) | −17.4 / −45.6 | 1 / 1 | 25.2 / 57.8 | 0.25 | 0.66 | 0.78 | 0.93 | 0.547 / 0.656 | 0.58 / 0.53 |
| P05 | A | (524, 517) | −11.7 / −62.0 | 1 / 1 | 15.1 / 60.0 | 0.24 | 0.58 | 0.69 | 0.93 | 0.547 / 0.484 | 0.75 / 0.61 |
| P06 | A | (581, 593) | −15.5 / −51.5 | 1 / 0 | 13.2 / 65.4 | 0.25 | 0.65 | 0.77 | 0.91 | 0.547 / 0.655 | 0.68 / 0.64 |
| P07 | A | (606, 574) | 3.2 / −66.2 | 1 / 1 | 30.4 / 94.5 | 0.26 | 0.65 | 0.81 | 0.96 | 0.547 / 0.572 | 0.76 / 0.69 |
| P08 | A_526_581 | (606, 695) | falta B20 | | | | | | | | |
| P09 | A_526_381 | (619, 428) | −3.5 / 0.0 | 1 / 0 | 19.9 / 219.4 | 0.16 | 0.27 | 0.47 | 1.32 | 0.485 / 0.560 | 0.75 / 0.43 |
| P10 | A_526_581 | (637, 682) | falta B20 | | | | | | | | |
| P11 | A_526_381 | (645, 495) | −24.8 / 72.1 | 1 / 1 | 40.4 / 237.5 | 0.23 | 0.65 | 0.72 | 0.96 | 0.485 / 0.672 | 0.65 / 0.29 |
| P12 | A_526_581 | (649, 752) | falta B20 | | | | | | | | |
| P13 | A_526_381 | (649, 526) | −3.4 / −42.1 | 0 / 0 | 3.1 / 49.8 | 0.24 | 0.42 | 0.55 | 0.98 | 0.485 / 0.537 | 0.58 / 0.54 |
| P14 | A_526_381 | (676, 523) | −17.8 / 10.9 | 1 / 0 | 24.8 / 187.1 | 0.18 | 0.20 | 0.39 | 1.31 | 0.485 / 0.493 | 0.78 / 0.65 |
| P15 | A_526_581 | (688, 741) | falta B20 | | | | | | | | |

La tabla completa, con más columnas, está en `tabla.csv`.

**Resumen (medianas sobre 11, con [p25–p75]):**

| medida | B20 vs A | control A vs A' (N = 2) |
|---|---|---|
| fondo (\|media del anillo\|) B/A | 0.24 [0.23–0.26] | — |
| estructura fina sin normalizar B/A | 0.96 [0.93–1.01] | 1.00 |
| ρ_c (complejo, todo) | 0.58 [0.37–0.65] | 0.87 y 0.97 |
| ρ_c_hp (pasa-altos σ 3 µm) | 0.66 [0.55–0.75] | 0.86 y 0.96 |
| Pearson de amplitud | 0.02 [−0.18–0.11] | 0.76 y 0.91 |
| \|S\| B/A | 5.0 [3.3–6.9] | 0.90 y 1.00 |
| error relativo ‖A − B‖/‖A‖ | 0.77 | 0.04 |
| desplazamiento A↔B | 0.10 µm (máx. 1.4) | — |
| C1 | B20 0.655 [0.55–0.67]; A 0.485–0.590 | — |
| C2 en la ventana de 60x60 px HR | A 0.65 vs B20 0.53 | — |

- **C1 sin FPM en B20:** 0.936. Todos los B20 pasan C1 (R ≤ sin FPM − 0.10).
- **C3 en B20:** alto en 5 de 11 (0.015–0.12). En los A dio 0.005–0.025.
- **C2 de cada A entero** (FRC complejo de mitades, banda [0.212, 0.45] µm⁻¹, = `c2_rojo.py`): A_200 0.33,
  A_326_381 0.25, A_326_581 0.23, A_526_381 0.38, A_526_581 0.40.
- **C1 de cada A:** 0.547, 0.581, 0.590, 0.485 y 0.526.

## Qué muestran los números (sin ir más allá)

1. **La ventana chica pierde el fondo (las frecuencias más bajas), pero no la estructura fina.**
   - En B20, la amplitud del fondo queda en ~0.24 de la de A, y en las 11 partículas.
   - La estructura fina tiene la misma energía absoluta: 0.96 de la de A.
   - Por eso, con cada imagen normalizada por su propio fondo, las partículas de B20 aparecen **claras** donde en A son
     **oscuras**: el área oscura de B es negativa en las 11.
   - |S| es de 2 a 16 veces el de A, y el Pearson de amplitud es ~0.
   - La posición sí coincide: el desplazamiento mediano es de 0.1 µm.
   - Esto se ve también en `fig_grilla_B20.png`: misma forma, contraste invertido, y una "silla" de fase de baja
     frecuencia en la columna fase A−B.
2. **La forma coincide solo en parte.** La correlación compleja de la estructura fina da 0.66 (0.39–0.81). El control
   entre dos reconstrucciones A da 0.86–0.96. Es decir, B20 no reproduce la partícula de A ni siquiera en la estructura
   fina, aunque se le parece.
   - **Incertidumbre:** el control A vs A' tiene solo 2 pares.
3. **Volumen de fase:** no se puede responder con esta toma. En A, las partículas tienen vórtices (9 de 11) y V sale
   negativo o cerca de 0. En B, V va de −66 a +72 sin relación con A (`fig_dispersion.png`, panel izquierdo).
4. **Métricas:**
   - C1 de B20 (0.66) es peor que el de los A (0.49–0.59), pero pasa el criterio. Es decir, el held-out a 20 px se ajusta
     aunque el objeto esté mal en baja frecuencia. C1 no detecta este problema.
   - C2 en la ventana: A 0.65 contra B20 0.53.

## Advertencias

- **PSF coherente.** Con NA 0.0747 y λ 0.63 µm, el primer cero de la PSF coherente está a 0.61·λ/NA ≈ 5.1 µm, y los
  anillos llegan a ~10 µm.
  - La ventana B20 tiene semilado 12.9 µm. El anillo de fondo (8–11 µm) ya está dentro de la PSF de la partícula, y la
    luz de campo oscuro que la partícula desparrama más allá de 12.9 µm queda fuera de la ventana o vuelve a entrar por
    el borde opuesto (el borde es periódico).
  - Las partículas detectadas además se extienden 14–21 µm (con halo).
- **Muestreo de Fourier.**
  - En 20 px crudos, Δf = 1/(20·1.29 µm) = 0.039 µm⁻¹, y el radio de la pupila NA/λ = 0.119 µm⁻¹ ≈ 3 muestras: ~29
    muestras dentro del disco de la pupila por imagen. En 200 px son ~2900 muestras, y en 40 px ~117.
  - Las frecuencias más bajas, el DC incluido, quedan determinadas por muy pocas muestras y por el borde. Esto es
    compatible con el fondo perdido del punto 1, pero **la causa no se investigó**.
- **C2 en ventanas de 60x60 px HR.** Δk = 0.039 µm⁻¹, y la banda [0.212, 0.45] µm⁻¹ tiene ~330 muestras de Fourier en
  total, contra ~330 000 en un recorte de 600 px.
  - El FRC por anillo tiene un piso de ruido de ~1/√n ≈ 0.15–0.2.
  - Sirve para comparar A contra B **en la misma ventana**, no para comparar con el C2 de un recorte grande.
  - C3 (lattice) en 20 px tampoco es comparable con el de 200 px.
- **Offset de LED distinto.** B usa el offset de la posición de cada partícula; A usa el del centro de su recorte (hasta
  ~0.4 mm de diferencia). El control A vs A' (±0.24 mm) sugiere que esto no explica la diferencia, pero son solo 2 pares.
- **La muestra no es la ideal para la pregunta.** El campo tiene pocos objetos; muchos son alargados o dobles, y es
  posible que no todos sean esferas. Las conclusiones valen para "objetos de esta toma", no para esferas de 5 µm de
  volumen conocido.
- **Todavía faltan 4 partículas** (las más chicas y redondas). Pueden cambiar las medianas, pero no el patrón del fondo,
  que es el mismo en las 11.

## Archivos

- `A_200*/`: reconstrucciones A (resumen.txt, objeto_complejo.npy, mitades).
- `B20/f<fila>_c<col>/` y `.log`: una reconstrucción B20 por partícula.
- `seleccion.json`: las 15 partículas (A asignado, centro en px del ROI, `rec20` y `rec40`), los criterios usados y todos
  los objetos detectados.
- `fig_seleccion.png`: mapa de los recortes A y de las ventanas B20.
- `tabla.csv`, `resultados.json`: todos los números, incluidos el agregado y `control_A_vs_A2_w20`.
- `fig_dispersion.png`: V, |S| y área oscura, A contra B.
- `fig_grilla_B20.png`: por partícula, la amplitud y la fase de A y de B20 (cada una normalizada por su propio fondo) y
  las diferencias.
- `codigo/`:
  - `correr_A.sh`, `correr_A_tejas.sh`, `correr_B.sh`: corridas de A y de B;
  - `detectar.py` y `detec_comun.py`: selección de partículas;
  - `comparar2.py`: comparación;
  - `continuar.sh`: termina lo que falta;
  - `detectar_v1_fase_octubre.py`: el primer intento, con la segmentación de octubre.
- Logs: `A_200.log`, `A_tejas.log`, `B20_pre*.log`, `comparar.log`.
