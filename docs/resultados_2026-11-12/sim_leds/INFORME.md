# Contribución por LED a la reconstrucción FPM (simulación, 12/11)

Todo es simulación; presupuesto de ~18 min de reloj compartiendo CPU con otro estudio, así que el alcance es chico y varias partes quedaron incompletas (ver "Límites").

## Método

- `sim_leds.py` (autocontenido, semilla 20261112): matriz 15x15, pitch 6 mm, z 102 mm, NA 0.07, λ 0.63 µm, LR 1.28 µm/px, factor 3. LR 80x80, HR 240x240. NA_syn = 0.573 (esquinas); sobre los ejes la cobertura llega sólo a NA 0.45.
- Objeto: 14 esferas de 5 µm, dn = 0.046 (2.3 rad en el centro), absorción débil.
- Imágenes: modelo directo con la misma ventana/pupila que el solver. Ruido: Poisson (3000 fotones/px en BF, DF con 30x de exposición) + lectura 2 e-. Variante sin ruido sólo para la línea base.
- Solver: copia del núcleo de `scripts/fpm_solver/fpm_red.py::reconstruct` (step 0.3 con rampa, orden por anillo, init kron del LED central), 20 épocas, sin `fit_sb`, sin EPRY, sin pesos.
- Métricas vs verdad, tras ajustar un escalar complejo global: error complejo normalizado `err`; error espectral relativo por banda `e_*` y FRC por banda `frc_*` (bandas en NA: BF 0-0.07, bajo 0.07-0.2, medio 0.2-0.35, alto 0.35-0.45, fuera > 0.45); RMS de fase dentro de las esferas `ph_esf`.
- Contribución por LED sobre un octante (36 LEDs, replicado por simetría a 15x15): (i) leave-one-out (LOO) y (ii) agregar el LED a la base 3x3 (BF + anillo 1, 9 LEDs).
- Predictores sin reconstruir N veces (usan sólo la reconstrucción base, no la verdad): `geo` = Σ 1/cobertura en la pupila del LED; `fisher` = Σ |Ô(q)|² / cobertura(q) (energía espectral del objeto en la pupila del LED dividida por la redundancia); `fisher_excl` = energía en píxeles que sólo ve ese LED; `grad` = norma del residuo/gradiente de Wirtinger del LED en la solución; `overlap` = solapamiento medio de pupila con los 4 vecinos.
- `resumen.py` lee `results.json` (aunque esté incompleto) y genera tablas y figuras.

## Resultados

### Línea base

| caso | err | e_bajo | e_medio | e_alto | FRC medio | FRC alto | fase esferas (rad) |
|---|---|---|---|---|---|---|---|
| 225 LEDs, sin ruido | 0.034 | 0.040 | 0.274 | 0.601 | 0.971 | 0.844 | 0.111 |
| 225 LEDs, con ruido | 0.037 | 0.040 | 0.304 | 0.734 | 0.958 | 0.749 | 0.118 |
| sólo base 3x3 (9 LEDs), con ruido | 0.074 | 0.277 | 1.005 | 1.092 | 0.018 | 0.021 | 0.232 |

La banda alta no converge ni sin ruido (e_alto 0.60 con 20 épocas): la línea base no está convergida en alta frecuencia, lo que limita la lectura de todo lo que sigue en esa banda.

### Leave-one-out, promedio por anillo (x100; positivo en error = quitar el LED empeora)

| radio (pasos de LED) | n (octante) | Δerr | Δe_bajo | Δe_medio | Δe_alto | ΔFRC alto |
|---|---|---|---|---|---|---|
| 0-1.5 | 2 | +0.429 | +2.780 | +8.191 | +12.490 | -8.253 |
| 1.5-3.5 | 5 | +0.123 | +0.359 | +3.843 | +2.481 | -1.905 |
| 3.5-5.5 | 9 | +0.020 | -0.041 | +0.584 | +0.590 | -0.510 |
| 5.5-7.5 | 12 | +0.007 | -0.003 | -0.025 | +0.512 | -0.381 |
| 7.5-10 (esquinas) | 7 | +0.000 | -0.001 | -0.024 | -0.077 | +0.044 |

6 de 35 LEDs del octante dan Δerr < 0 al quitarlos (marginalmente perjudiciales; el efecto es del orden de 1e-5 a 1e-4 en err, no distinguible de cero con una sola realización de ruido).

### Agregar un LED a la base 3x3 (x100)

| radio | n | Δerr | Δe_bajo | Δe_medio | Δe_alto | ΔFRC alto |
|---|---|---|---|---|---|---|
| 1.5-3.5 | 5 | +0.006 | +0.058 | -0.025 | -0.003 | +0.000 |
| 3.5-5.5 | 9 | +0.118 | +0.207 | +3.020 | +0.126 | -0.062 |
| 5.5-7.5 | 12 | +0.021 | +0.000 | +0.256 | +1.661 | +0.858 |
| 7.5-10 | 7 | +0.014 | +0.000 | +0.006 | +1.281 | +0.858 |

30 de 33 LEDs aumentan el error total al agregarse solos a la base: un LED aislado, sin solapamiento con la región ya reconstruida, escribe en su ventana un parche con fase no anclada. Este esquema mide el fracaso del solapamiento, no "información aportada".

### Predictores vs LOO medido (Spearman, 35 LEDs del octante)

| predictor | vs Δerr | vs Δe_alto | vs Δe_medio | vs Δe_bajo |
|---|---|---|---|---|
| `fisher` (energía/redundancia) | +0.84 | +0.70 | +0.73 | +0.13 |
| `overlap` (% con vecinos) | -0.74 | -0.59 | -0.64 | -0.09 |
| `grad` (residuo Wirtinger) | +0.41 | +0.33 | +0.21 | -0.31 |
| `geo` (sólo cobertura) | +0.13 | +0.07 | +0.34 | +0.31 |
| `fisher_excl` | -0.00 | +0.00 | +0.16 | +0.07 |

### Simetría y curva calidad vs nº de LEDs

**Simetría: no se cumple LED a LED.** LOO de imágenes especulares (Δerr del espejo vs del representante): (5,2) 4.4e-5 vs 4.5e-5; (2,-5) 7.3e-4 vs 4.5e-5 (16x); (7,4) 2.0e-5 vs 3.3e-5; (4,-7) -9.6e-5 vs +3.3e-5 (cambia de signo); (3,1) 3.7e-4 vs 6.7e-4; (1,-3) 8.0e-4 vs 6.7e-4. Los mapas 15x15 replicados por octante (`fig2_loo.png`, `fig3_add.png`) NO son fiables LED a LED; sólo los promedios por anillo tienen sentido, y aun así con una sola realización.

**Curva calidad vs nº de LEDs** (con ruido; la base 3x3 siempre incluida; N=225: err 0.037, e_bajo 0.040, e_alto 0.734, fase 0.118):

| selección | métrica | N=49 | N=81 | N=113 | N=149 |
|---|---|---|---|---|---|
| ranking LOO medido | err / e_alto / fase | 0.047 / 1.091 / 0.140 | 0.041 / 1.092 / 0.127 | 0.039 / 0.934 / 0.122 | 0.038 / 0.878 / 0.123 |
| ranking `fisher` | err / e_alto / fase | 0.045 / 1.092 / 0.127 | 0.041 / 1.083 / 0.120 | 0.038 / 0.894 / 0.112 | 0.036 / 0.721 / 0.112 |
| anillo, de adentro hacia afuera | err / e_alto / fase | 0.044 / 1.092 / 0.125 | 0.041 / 1.086 / 0.122 | 0.038 / 0.887 / 0.107 | 0.036 / 0.726 / 0.113 |
| anillo, de afuera hacia adentro | err / e_alto / fase | 0.076 / 1.226 / 0.238 | 0.078 / 1.454 / 0.253 | 0.079 / 1.419 / 0.267 | 0.083 / 1.417 / 0.270 |
| azar (2 semillas) | err | 0.080, 0.078 | 0.074, 0.070 | 0.065, 0.064 | 0.054, 0.059 |
| damero (117 LEDs) | err / e_alto / fase | - | - | 0.071 / 1.418 / 0.266 | - |

- El ranking LOO medido ("greedy" de una pasada) **no le gana** a la heurística trivial por anillo; es igual o algo peor (N=149: e_alto 0.878 vs 0.726). El resultado candidato a publicación sale negativo.
- `fisher` y anillo-adentro-afuera son indistinguibles (el predictor es un proxy del radio).
- Con 149 LEDs contiguos (66 %) se iguala a los 225 en todas las métricas (err 0.036 vs 0.037, e_alto 0.72-0.73 vs 0.73). Con 113 (50 %) err y fase son iguales o mejores, pero e_alto es 0.89 vs 0.73: se pierde alta frecuencia. Los ~76 LEDs más externos no aportan nada medible aquí.
- Azar, damero y borde-primero son mucho peores que un disco contiguo del mismo tamaño: lo que importa es la contigüidad/solapamiento, no la cantidad. El damero al 52 % da err 0.071, igual que usar 9 LEDs.

## Conclusiones

1. La hipótesis "las frecuencias altas las dominan los LEDs del borde" **no se sostiene en esta simulación**. En LOO, quitar un LED central (anillo 0-1.5) es lo que más daña TODAS las bandas, incluida la alta (Δe_alto +0.125 frente a +0.005 para los anillos 5.5-7.5). Los LEDs internos sostienen la cadena de fase de la que dependen los externos (el solver recorre por anillo creciente). Los LEDs de las esquinas tienen contribución LOO indistinguible de cero.
2. Las bajas frecuencias sí dependen casi sólo de BF + anillos cercanos (Δe_bajo es apreciable sólo para radio < 3.5).
3. El predictor `fisher` (energía espectral estimada en la pupila del LED dividida por la redundancia de cobertura) ordena la contribución LOO total con Spearman +0.84 sin reconstruir N veces. Es en buena parte un proxy del radio (la energía espectral cae con la frecuencia), así que no está demostrado que aporte más que "ordenar por anillo"; no se hizo la correlación parcial controlando por radio.
4. El solapamiento correlaciona negativamente con la contribución (-0.74), pero en esta geometría el solapamiento crece hacia el borde (sin θ se comprime), así que también está confundido con el radio. No se separó el mecanismo.

## Lo que no funcionó / límites

- Línea base sin converger en la banda alta (20 épocas); los Δ en esa banda mezclan información y velocidad de convergencia.
- Una sola realización de ruido y un solo objeto: sin barras de error. Los Δ LOO de anillos externos (1e-5 a 1e-4) no son significativos.
- "Greedy" = ranking de una sola pasada por LOO, no selección secuencial.
- Crimen inverso: mismo modelo y mismo redondeo de k para generar y reconstruir; sin error de geometría, sin calibración de brillo por LED, sin aberraciones, sin stray light, sin saturación, condiciones periódicas.
- Simetría de octante asumida para los mapas (el objeto no es simétrico); la verificación está en `results.json["simetria"]` si llegó a correr.
- Bandas: "alto" se redefinió a 0.35-0.45 a mitad del estudio porque 0.4-0.573 incluía regiones no cubiertas por la matriz cuadrada (FRC 0.30 engañoso).
- `fisher_excl` y `geo` no predicen nada.

## Archivos

`sim_leds.py`, `resumen.py`, `results.json`, `objetos.npz`, `run.log`, `mapa_loo.png`, `mapa_add.png`, `prediccion.png`, `curva.png` (si hay curva); si `sim_leds.py` terminó, además `fig1_objeto.png` ... `fig5_prediccion.png`.
