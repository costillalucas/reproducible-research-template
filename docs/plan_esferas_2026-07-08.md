# Plan de trabajo: captura de esferas 2026-07-08 (13×13, RGB)

**Estado: preparado, sin correr nada.** Este documento es el brief para arrancar una
sesión nueva con agentes/jobs. Todo lo que está acá fue verificado leyendo el código y
los nombres de archivo, no corriendo nada.

## Por qué este dataset importa

La campaña de 2025-12-12 terminó en un callejón (roadmap 6.7–6.10): el solver estaba
congelado, la referencia era ciega, y una vez arreglado todo quedó un piso de residuo
~0.29 que no es ruido, con la geometría **indistinguible** dentro de ±1.5 LED y una
reconstrucción que no generaliza (0.29 entrenamiento contra 0.50 en LEDs excluidos).
La hipótesis principal es que la muestra viola el modelo de objeto delgado.

Una muestra de **esferas de ~5 µm de tamaño conocido** ataca exactamente eso, y además
cubre el rol que el roadmap le asignaba al target USAF:

- es una muestra fina y de geometría conocida → si tampoco cierra, el problema no es la
  muestra;
- da **ground truth parcial sin microscopio de referencia**: el tamaño de las esferas es
  una regla incorporada en la imagen;
- permite calibrar aumento, NA y centro del arreglo **con el objeto**, en vez de buscar
  la geometría a ciegas contra el residuo (que fue lo que dio el paisaje plano).

## Los datos

Raíz: `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-07-08/organizado`

| | |
|---|---|
| canales | `red`, `green`, `blue` |
| set a usar | `<canal>/13x13_recortada_400/fila<R>_col<C>.tiff` |
| imágenes | 169 por canal (13×13), 400×400, uint16 |
| índices | filas **11–23**, columnas **9–21** → centro geométrico (17, 15) |
| centro real | **(18, 15)** según Lucas — a verificar por radiancia |
| exposición | **1 ms para todas** según Lucas — a verificar |
| rango observado | LED central: 227–597 cuentas (media 418) |
| otros sets | `13x13` (sin recortar), `13x13_bis`, recortes a 200 px |

Sin confirmar todavía, hay que preguntarle al laboratorio:

1. Que este set sea efectivamente el de esferas de ~5 µm (diámetro nominal y dispersión).
2. **Material de las esferas y medio de montaje** (poliestireno n≈1.59 a 530 nm en aire,
   en agua, en medio de montaje…). Sin eso hay resolución y tamaño, pero no fase
   cuantitativa contra verdad.
3. Nivel de oscuro de esta sesión de cámara (o una captura sin LEDs).
4. Confirmación del 1 ms y de si hubo saturación en los LEDs centrales.

## Lo que el código ya soporta (verificado leyendo las CLIs)

`pipelines/reconstruct_real_images.py` y `scripts/sweep_real_reconstruction_quality.py`
aceptan, vía `src/ptyco_full_simulator/cli_args.py`:

- `--grid-size 13 --crop 400 --row-index-base 11 --col-index-base 9` (calzan con las rutas de arriba)
- `--objective 2x_na010` (default) o `--na` / `--magnification` para override explícito
- `--z-distance-mm` (default 76 para datos reales)
- `--led-center-offset-mm DX DY` — **verificar la convención de ejes antes de usarlo**;
  el pitch es 6 mm, así que un LED de corrimiento en fila son 6 mm
- `--no-exposure-normalization` y `--dark-level <cuentas>`
- `--step-epie 0.3` (el paso descongelado; sigue siendo opt-in a propósito)
- `--no-normalize-initial-guess` (no usar: la init escalada es la correcta)

### Bloqueo conocido y su solución

`io_utils.load_exposure_map` **falla** si no encuentra `leds_por_tiempo_*.json` o carpetas
`<N>ms/` con archivos. Este set no tiene ninguna de las dos (las carpetas `1ms`…`1000ms`
existen pero están **vacías**). Como la exposición es uniforme, la salida correcta es
`--no-exposure-normalization --dark-level <medido>`: con un solo tiempo de exposición,
normalizar es multiplicar todo por una constante, que el solver absorbe en la escala.
**No hay que tocar el loader para esto.** Si más adelante aparece el JSON del laboratorio,
se vuelve al camino normal.

## Lo que NO hay que repetir

- No usar `img_mov_alineada_*` ni ninguna referencia Zeiss 2.5x como métrica de calidad:
  es ciega por encima de ~0.7 del Nyquist LR (roadmap 6.8).
- No correr con el paso por defecto y sacar conclusiones sobre el solver: a crop 400 el
  paso efectivo es ~1/8000 del de ePIE (roadmap 6.9). Siempre `--step-epie`.
- No leer `convergence_summary` (el residuo interno) como precisión: en datos reales no
  es un proxy confiable.
- No declarar "funciona" por correlación contra nada sin una validación cruzada dejando
  LEDs afuera: es el único diagnóstico que separó "ajusta los datos" de "reconstruye el
  objeto" (roadmap 6.10.3).

---

# Jobs propuestos

Orden pensado para gastar poco antes de gastar mucho. J1 es barato y condiciona al resto:
**no arrancar J3 sin J1**.

## J1 — Sanidad y metrología del dataset (barato, primero)

**Objetivo**: saber si estos datos sirven, y con qué geometría, antes de reconstruir nada.

1. Nivel de oscuro: histograma global, percentiles bajos, esquinas de las imágenes de
   campo oscuro lejano. Comparar con los 188 de la otra sesión (`config.REAL_CAPTURE_DARK_LEVEL`).
2. Saturación y rango útil por LED; señal sobre ruido de lectura en los LEDs de campo
   oscuro (con 1 ms fijo pueden estar en el piso: si lo están, decirlo y descartarlos).
3. Mapa 13×13 de radiancia media (después de restar el oscuro) → **estimar el centro del
   arreglo** con el método que en 2025-12-12 dio 17.45 ± 0.1 / 14.65 ± 0.1. Contrastar con
   el (18, 15) que reporta Lucas y con el centro geométrico (17, 15).
4. Transición campo claro → campo oscuro sobre ese mapa → **NA·píxel** medido, y de ahí
   aumento y NA efectivos (mismo método que `results/mag_check_2025-12-12/`, que dio
   NA·px = 0.194 ± 0.003 µm ⇒ ~1.83x / NA ~0.11).
5. Repetir 3 y 4 en los tres canales: el centro no debe depender del color; si depende,
   hay algo mal.

**Salida**: `results/esferas_2026-07-08/sanity/` con JSON de números y PNGs de
diagnóstico. **Criterio**: centro estimado con incertidumbre < 0.2 LED y un veredicto
explícito sobre si los LEDs de campo oscuro tienen señal.

## J2 — Geometría medida con el objeto, no con el residuo (responde la pregunta 4 de Lucas)

**Objetivo**: calibrar la geometría directamente, sin pasar por el solver.

Idea central: entre dos LEDs vecinos, la imagen de campo claro **se corre** una cantidad
que predice el modelo (el desplazamiento lateral asociado al ángulo de iluminación, y el
desenfoque residual). Ese corrimiento se mide por correlación cruzada entre capturas
vecinas, píxel a píxel, **sin reconstruir nada**.

1. Medir el corrimiento de todas las parejas de LEDs vecinos de campo claro.
2. Ajustar el modelo geométrico (centro del arreglo, z, pitch efectivo, rotación) a ese
   campo de corrimientos medido.
3. Comparar el resultado con J1 (radiancia) y con lo que dice el laboratorio.
4. Como control: el tamaño aparente de las esferas da el aumento efectivo de forma
   independiente (5 µm conocidos ÷ tamaño medido en píxeles).

**Por qué importa**: en 2025-12-12 la geometría se buscó minimizando el residuo del
solver, y el paisaje salió plano. Esto la mide con datos crudos, y es un diagnóstico que
el proyecto todavía no tiene.

**Salida**: `results/esferas_2026-07-08/geometria/`. **Criterio**: centro y z con barra de
error, y acuerdo (o desacuerdo explícito) con J1.

## J3 — Reconstrucción real, con validación cruzada desde el principio

**Objetivo**: reconstruir verde y ver si aparecen las esferas.

Comando base (ajustar centro y oscuro con lo que salga de J1/J2):

```
python3 pipelines/reconstruct_real_images.py \
  --data-root /home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-07-08/organizado \
  --channel green --grid-size 13 --crop 400 \
  --row-index-base 11 --col-index-base 9 \
  --objective 2x_na010 --z-distance-mm 76 \
  --no-exposure-normalization --dark-level <J1> \
  --step-epie 0.3 --iterations 100 \
  --output-dir results/esferas_2026-07-08/green_epie03
```

Variantes mínimas: centro de J1/J2 contra (17,15) contra (18,15), vía
`--led-center-offset-mm`. Y para cada variante, **validación cruzada dejando 20 de los
169 LEDs afuera** (el diagnóstico de `results/geometry_search_2025-12-12/cv.py`).

**Criterios de éxito, decididos antes de mirar** (esto es importante: en la campaña
anterior el criterio se fue moviendo):

- las esferas se ven como discos del tamaño esperado (5 µm ÷ píxel de muestra ≈ 3 px en
  la grilla LR, ~14 px en la HR con factor 5);
- el residuo de los LEDs excluidos **baja** respecto de la campaña anterior (0.50) y se
  acerca al de entrenamiento;
- la geometría **sí discrimina**: el residuo de held-out empeora al mover el centro medio
  LED, como pasa en sintético (0.035 → 0.22).

Si los tres fallan igual que en diciembre, el problema no era la muestra y hay que mirar
el modelo directo (redondeo de k, coherencia parcial, ancho espectral del LED).

## J4 — Ground truth sintético de esferas (responde la pregunta 1 de Lucas)

**Objetivo**: tener un patrón de comparación cuantitativo y decidir qué métricas usar
cuando hay verdad.

1. Simular esferas de 5 µm con el forward model del repo, usando la geometría que salga
   de J1/J2 y ruido tipo captura (gain y varianza de lectura medidos en J1).
2. Reconstruir con el mismo comando de J3 y medir todo: correlación y RMSE de fase y
   amplitud, y además métricas sensibles a la forma (perfil radial de una esfera, tamaño
   recuperado, contraste de borde, FRC contra la verdad).
3. Con eso se responde cuál métrica detecta antes un error de geometría, que es lo que
   interesa: la correlación de fase satura y engaña (ver el techo de π), el residuo de
   datos no distingue geometría, y el tamaño recuperado sí es interpretable.

**Salida**: `results/esferas_2026-07-08/sintetico/`.

## J5 — Métricas sin ground truth (responde la pregunta 2 de Lucas)

**Objetivo**: cerrar la pregunta metodológica que atraviesa todo el proyecto.

Candidatas a evaluar sobre J3 y J4 (en J4 se puede contrastar cada una contra la verdad,
que es lo que las valida):

- residuo en **LEDs excluidos** (hoy el mejor que tenemos);
- **FRC** entre dos reconstrucciones independientes, cada una con la mitad de los LEDs
  → da una resolución en µm sin necesidad de verdad;
- consistencia **entre canales** (el QC que ya existe) sobre el mismo objeto;
- **tamaño conocido de las esferas** como regla interna;
- `pair_disagreement` como confianza por píxel (ya calculado, nunca usado).

**Salida**: una sección nueva del roadmap más una tabla de recomendación: qué mirar
cuando hay verdad, qué mirar cuando no.

---

## Cómo arrancar la sesión nueva

1. Leer este archivo y `docs/roadmap_agentic_multispectral_pipeline.md` secciones 6.8–6.10.
2. Lanzar **J1** (barato, un solo fork, ~minutos) y esperar: J2 y J3 dependen de su centro
   y su nivel de oscuro.
3. Con J1 en la mano, lanzar **J2** y **J4** en paralelo (uno mide geometría con datos
   crudos, el otro genera el patrón sintético; no compiten por los mismos archivos).
4. **J3** después de J2. Es el único que consume CPU pesada: 169 LEDs a crop 400.
5. **J5** al final, cuando J3 y J4 dieron resultados que comparar.

Recordatorios operativos de esta máquina: 4 núcleos, sólo `python3` (para `reproduce.sh`
hace falta un shim `python` → `python3` en el PATH), y la suite completa tarda ~8 minutos.
