# Plan 2026-11-03: rojo vs azul en el "arco", nulo DF y NA 0.074

Corrido sin supervisión el 03/11/2026 entre las 12:01 y las 13:10 (unos 70 min). El repo no se tocó. Las corridas usan una **copia** parcheada del script, `codigo/reconstruir_plan.py`, que es `scripts/reconstruir.py` del árbol de trabajo actual (con `--anillo-max` sin commitear) más dos parches por variable de entorno:

- `NA_OBJ`: sobrescribe la NA del objetivo. No cambia nada más; la lista de LEDs BF se recalcula sola a partir de la NA.
- `NULO_DF=1`: permuta las fxy (seed 0) **solo entre los LEDs usados que son DF según la geometría verdadera**. Los BF no se tocan.

Para ver el diff: `diff scripts/reconstruir.py codigo/reconstruir_plan.py`.

Las corridas fueron en serie, una por vez, con 3 núcleos, 160 épocas y `--validar` (`codigo/cadena.sh`, `codigo/cadena2.sh`):

```
ARCO = 2026-10-30-red-b --flat …-red-b-sinmuestra --dark …-red-b-dark --dark-flat …-red-b-sinmuestra-dark --color r
       --offset-roi 4000,874 --recorte 290,415 --epocas 160 --guardar-cada 0 --validar
REDC = 2026-10-30-red-c --flat …-red-c-sinmuestra --dark …-red-c-dark --dark-flat …-red-c-sinmuestra-dark --color r
       --offset-roi 3968,1966 --recorte 380,200 --epocas 160 --guardar-cada 0 --validar
NULO_DF=1     reconstruir_plan.py $ARCO --salida red-b_arco_nulo_df     (12:03-12:19)
NA_OBJ=0.074  reconstruir_plan.py $ARCO --salida red-b_arco_na074       (12:19-12:33)
NA_OBJ=0.074  reconstruir_plan.py $REDC --salida red-c_na074            (12:33-12:49)
NULO_DF=1     reconstruir_plan.py $REDC --salida red-c_nulo_df          (12:49-13:03, extra: sobraba tiempo)
```

Los análisis están en `codigo/tarea_a.py`, `codigo/fig_a.py`, `codigo/tarea_bc.py` y `codigo/fig_bc_objetos.py`; las funciones compartidas, en `codigo/comun_plan.py`.

**Definición de C2 que usé.** Es la de `results/captura_2026-10-21/eval/resolucion.py` (igual a `criterios_b.py`): la media del FRC **complejo** entre `objeto_mitadA` y `objeto_mitadB`, sin ventana, con 60 anillos hasta la esquina del espectro, en la banda **[2NA/λ, 0.45] µm⁻¹ = [0.212, 0.45] µm⁻¹** (NA 0.0669, λ 0.63; los periodos van de 4.7 a 2.2 µm). La regla de PASA de ese script es C2 ≥ 1/7 y además C2 ≥ C2_nulo + 0.068. Para las corridas con NA 0.074 doy el C2 en la misma banda y también en la banda propia, [0.235, 0.45].

## A) Rojo vs azul en el arco: **los dos campos NO son el mismo**

- **El arco no aparece en ninguna de las tomas rojas del 30/10** (`fig_a_campos_completos.png`, `fig_a_panel_2x3.png`). Las tomas `2026-10-29-blue` y `2026-10-30-red-b` tienen el mismo ROI (4000,874, según `captura.json`) pero muestran campos distintos. `2026-10-30-red` y `red-b` se ven iguales entre sí; `red-c` es otro campo, también sin el arco.
- **Búsqueda del campo** (`a_busqueda_campo.json`). Tomé cinco parches de 300×300 px del cuadro azul completo del LED (17,15) a 16 ms, uno de ellos el arco, y los busqué con NCC (pasabanda) en todo el cuadro de red-b. El máximo dio entre 0.15 y 0.23, en posiciones dispersas y distintas para cada parche. En el mismo lugar del cuadro rojo, la NCC fue de −0.015 a 0.015. Como control, el parche del arco buscado en otra toma azul (`2026-10-29-blue-prueba-1151`) dio NCC 0.999.
- **El registro (A2) no tiene objeto**. `phase_cross_correlation` devuelve desplazamientos sin sentido: (+69, −35) px en |O|, (+62, −23) px en fase y (0, −199) px en crudo. Después del registro, la NCC queda en 0.003. El barrido de escala entre 0.97 y 1.03 da un "mejor" 1.015 con NCC 0.003, que es ruido (`a_registro_real.json`).
- **Los FRC rojo vs azul (A3)** se calcularon igual: Hann, anillos de 0.012 µm⁻¹, grilla común de 0.43 µm, con el azul remuestreado por Fourier desde 0.258 µm. Todas las curvas (crudo, |O|, fase, complejo, y |O| con escala 1.015) quedan bajo 1/7 desde k ≈ 0.022–0.030 µm⁻¹ (periodos de 33 a 46 µm) y se superponen con el control (|O| corrido 150 px). Ver `fig_a_frc_real.png`, `a_frc_real.csv` y `a_frc_real.json`, que traen también las líneas NA/λ: 0.106 en rojo, 0.142 en azul (NA 0.0669 según el resumen del azul, λ 0.47); corte sintético 0.919 en rojo y 1.215 en azul, este último fuera de la grilla de 0.43 µm, cuyo Nyquist es 1.163.
- Con campos distintos, **el FRC rojo vs azul usando el nulo (control de A3) no tiene sentido y no lo corrí**.
- **A4. Números propios de red-b_arco** (de su `resumen.txt` y su log):
  - R de entrenamiento 0.471; C1 0.710 (A 0.716, B 0.705); sin FPM 0.987; piso 0.129; C3 9.2e-3.
  - **4 LEDs BF**: (17,15), (16,15), (17,14) y (17,16).
  - El LED (18,15) queda fuera de los BF. Con el offset del LED y +1.930 mm (OffsetY 874), su |f|/(NA/λ) es 1.159. Con el mismo cálculo, (16,14) da 1.072 y (16,16) 1.049, ambos DF pero cerca del borde.
  - El log avisa "recorte lejos del eje óptico (> 1/4 de paso de LED)" y "(16,16) 7 px saturados".

## B y C) C2, C1, R y C3: tabla (`bc_tabla.csv` / `bc_tabla.json`)

| corrida (160 ép.) | NA | n BF | R train | C1 mitades (A / B) | sin FPM | C3 | C2 [0.212,0.45] | C2 − nulo propio |
|---|---|---|---|---|---|---|---|---|
| arco real | 0.0669 | 4 | 0.471 | **0.710** (0.716 / 0.705) | 0.987 | 9.2e-3 | **0.0134** | +0.004 |
| arco nulo DF | 0.0669 | 4 | 0.647 | 0.922 (0.923 / 0.921) | 0.995 | 9.3e-2 | 0.0095 | — |
| arco NA 0.074 | 0.074 | 6 (+16,14 +16,16) | 0.486 | **0.685** (0.691 / 0.680) | 0.985 | 0 (\*) | 0.0109 (propia 0.0100) | +0.001 (\*\*) |
| red-c real | 0.0669 | 5 | 0.410 | **0.676** (0.681 / 0.670) | 0.974 | 6.6e-3 | **0.0657** | +0.057 |
| red-c NA 0.074 | 0.074 | 5 | 0.415 | **0.637** (0.646 / 0.628) | 0.971 | 8.2e-4 | 0.1045 (propia 0.1024) | +0.095 (\*\*) |
| red-c nulo DF | 0.0669 | 5 | 0.609 | 0.882 (0.889 / 0.876) | 0.992 | 1.2e-1 | 0.0092 | — |

(\*) Es `lattice_score` = 0.0 exacto: ningún pico supera 20 veces la mediana local. Lo verifiqué recalculándolo sobre el .npy.
(\*\*) El nulo se corrió con NA 0.0669, no con 0.074, así que esta diferencia no compara contra un nulo de la misma geometría.

- Con NA 0.074, C1 bajó 0.025 en el arco y 0.039 en red-c, y R train subió 0.015 y 0.005. El conjunto held-out es el mismo (145 LEDs de anillo < 7), pero en el arco la lista de BF cambió de 4 a 6 LEDs.
- **El C2 con Hann** (misma banda) da: arco 0.031, nulo del arco 0.015, arco NA 0.074 0.022, red-c 0.063, red-c NA 0.074 0.109 y nulo de red-c 0.015. Ninguna corrida llega a 1/7 con ninguna de las dos variantes.
- **Las curvas de FRC entre mitades** están en `fig_bc_frc_mitades.png` (Hann, media móvil de 3 anillos). En red-c con NA 0.074 hay una joroba de hasta unos 0.14 alrededor de k ≈ 0.30–0.35 µm⁻¹ que no aparece con NA 0.0669 ni en el nulo. En el arco con NA 0.074, el FRC entre mitades queda **bajo 0.05 también en k < 0.2**, mientras que con NA 0.0669 llega a 0.1–0.23 en esa zona.
- **Los objetos** están en `fig_bc_objetos.png` (zoom de 172 µm). El arco con NA 0.074 tiene una estructura de baja frecuencia grande (bandas y manchas claras arriba) que no aparece con NA 0.0669. En los nulos, los objetos BF siguen visibles pero con textura de alta frecuencia distinta.

## Qué NO se hizo / limitaciones

- **A2 y A3 (registro y FRC rojo vs azul en el mismo campo) no son posibles con estas tomas**: no hay campo común. Dejé las curvas como evidencia de no-coincidencia, no como medida de resolución.
- No hice el FRC rojo vs azul con el nulo, por el mismo motivo.
- No corrí nulos con NA 0.074. Por eso, en las filas de NA 0.074, "C2 − nulo" usa el nulo de 0.0669.
- Hay un solo seed de permutación por nulo (seed 0).
- C1 se mide con 2 mitades, no con 5 folds. La comparación con el 23/10 (otra captura, otra configuración) es solo cualitativa.
- Sobre el arco con NA 0.074: además de la NA, cambia la lista de BF (+2 LEDs), así que no se puede aislar el efecto de la NA sola.
- Las carpetas de corrida pesan unos 113 MB cada una, la mayor parte en `datos/prep.npz`, que es una copia de un preprocesado idéntico al original. Se pueden borrar si hace falta espacio. No guardé ningún .npy por época.
- No toqué Nyquist, la conversión Ph1 → fase, el volumen de fase ni la firma de inclinación de la matriz.

## Preguntas para Lucas

1. El 03/11 verificaste "(0,0), pico 0.064 contra 0.005" entre el LED central de 29/10-blue y el de 30/10-red-b. ¿Qué estructura comparten esos cuadros si la muestra es distinta? ¿Polvo del sensor o patrón fijo del ROI 874? ¿O se comparó otra carpeta?
2. ¿Hay alguna toma roja del campo del arco, o se movió la platina entre el 29/10 y el 30/10? Si no la hay, ¿vale la pena tomar rojo en ese campo antes de seguir con A?
3. En el arco, C2 real (0.013) y nulo (0.0095) casi coinciden. En red-c, el real (0.066) sí se separa del nulo (0.009), aunque por menos que el margen de 0.068 y por debajo de 1/7. ¿Qué diferencia entre los dos campos o recortes podría explicarlo: el offset del LED (+1.93 mm contra 0.33 mm), el contenido de la muestra, el número de LEDs BF (4 contra 5)?
4. En red-c, NA 0.074 sube C2 a 0.10 y baja C1 en 0.039. En el arco baja C1 pero no mueve C2, y además destruye el acuerdo entre mitades a baja frecuencia y mete estructura grande en |O|. ¿Qué papel juegan los dos LEDs (16,14) y (16,16), que pasan a BF con |f|/(NA/λ) 1.07 y 1.05?
5. ¿La joroba del FRC entre mitades en red-c con NA 0.074 (k ≈ 0.3 µm⁻¹, unos 3 µm de periodo) aparecería también en un nulo hecho con NA 0.074?
