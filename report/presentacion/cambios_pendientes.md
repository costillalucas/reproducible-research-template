# Cambios pendientes de la revisión

Se aplican todos juntos al final de la pasada, sobre `index.html`, y se regenera
`presentacion.pdf`. Estado: **[hecho]** aplicado en `index.html` y verificado en el PDF
(segunda vuelta, 2026-09-23).

Los cuatro ítems que estaban **[?]** los resolvió Lucas así, y se aplicaron con esos valores:
título de portada "FPM multiespectral: estado, validación y límites" con "pipeline asistido
por agentes" como bajada · `[fecha]` y "Departamento de Física, FCEN – UBA" como placeholders ·
bibliografía suavizada a "en la bibliografía que revisamos (37 papers curados)" · slide 14 queda
con `fig12` en el cuerpo y `fig11` en respaldo.

Además se sumaron las dos figuras nuevas: `esquema_fpm.svg` en la slide 2 y
`diagrama_pipeline.svg` en la slide 3, por ruta relativa, y ambas se verificaron en el PDF.

---

## Slide 1 — Portada + tres conclusiones

- [hecho] **Definir los dos términos en la propia slide** (conclusión 2): "necesita contraste
  de amplitud (que la muestra atenúe algo) y no recupera fase débil (retardos ≲ 0.1π ≈ 26 nm
  de camino óptico)". Si la pregunta salió dos veces en la revisión, sale en la sala.
- [hecho] **Reformular la conclusión 3**: no es que no haya reconstrucción, es que ninguna es
  confiable:
  > En **datos reales hay reconstrucciones, pero ninguna confiable**: las previas eran la
  > imagen inicial disfrazada (solver congelado, ya arreglado), y la corregida ajusta las
  > mediciones sin parecerse a la muestra. Piso de residuo ~0.29 sin explicar.
- [hecho] **Título**: hoy "FPM multiespectral asistido por agentes"; alternativa "FPM
  multiespectral: estado, validación y límites", con los agentes en la slide 3.
- [hecho] **Placeholders**: `[fecha]` y nombre real del grupo (hoy "Departamento de Física, FCEN – UBA").

## Slide 2 — FPM y lo que agrega el color

- [hecho] **Sumar el esquema** `esquema_fpm.svg` (dibujado y revisado): panel 1, una captura por
  LED con el ángulo θ y lo que la NA no acepta; panel 2, las pupilas corridas y la apertura
  sintética. Hay que recortar bullets para que entre.
- [hecho] **Bajar a tierra "fase cuantitativa"**: el número de cada píxel es un retardo en
  radianes convertible a camino óptico, no un contraste cualitativo.
- [hecho] **"37 papers de la bibliografía curada"**: dejarlo con la respuesta lista en notas (de
  dónde sale la lista, `references/`) o suavizarlo a "en la bibliografía que revisamos".

## Slide 3 — El pipeline existe de punta a punta

- [hecho] **Sumar el diagrama de bloques** `diagrama_pipeline.svg` (dibujado y revisado).
- [hecho] **Destacar la degeneración A·t / B·t** con la fórmula visible (ya está en el diagrama).
- [hecho] **Mover el costo de los agentes a notas**; en la slide quedan sólo sus dos roles.
- [hecho] **"242 tests automáticos, y cada número publicado con su procedencia verificable"**
  (`check_provenance.py`, `reproduce.sh`).

## Slide 4 — Contraste de amplitud

- [hecho] **Definición al pie**: "contraste = 1 − min|A|, con el máximo normalizado a 1".
- [hecho] **Sacar la jerga "cuenca de atracción, no del paisaje"** y decir el argumento:
  "el óptimo está bien; el problema es desde dónde arranca: arrancando en la verdad converge
  a 0.91".
- [hecho] **Aclarar el alcance**: es una limitación de *estos* solvers en *este* régimen, no de
  FPM en general (y la literatura reporta el mismo fenómeno de bajo contraste).

## Slide 5 — Fase débil y techo de π

- [hecho] **Definición al pie**: "φ_max = retardo máximo del objeto; 0.1π ≈ 26 nm de camino
  óptico a 530 nm" — le da tamaño físico al límite.
- [hecho] **Explicitar la referencia "sin fase"** del segundo bullet: es el RMSE que da poner
  fase cero en todos los píxeles; que el resultado sea peor que eso es el punto.
- [hecho] **Cerrar con la consecuencia de proyecto**, que hoy está al final del bullet 3 y se
  pierde: el aporte novedoso vive arriba de π y el solver no llega. Va como frase destacada.

## Slide 6 — Posición de los LEDs

- [hecho] **Definir "oráculo"** (usar las posiciones verdaderas: es el techo alcanzable) y
  **"bins de error de k"** (1 bin = un paso de la grilla de frecuencias; el acantilado cae
  entre 0.4 y 0.8 bins).
- [hecho] **Decir en la slide que los números son de GD-amplitud**, no de WF, y por qué (la
  columna WF está excluida por el paso congelado). Hoy está sólo en notas y es justo el
  tipo de cosa que un revisor pregunta.
- [hecho] **Marcar que esta slide es la que arma la expectativa** que los datos reales después
  no cumplen (slide 14): en sintético la geometría manda; en real, no se siente.

## Slide 7 — Acople de los tres canales

- [hecho] **Decir qué se mide**: correlación del **mapa de espesor** con el verdadero, no fase
  ni resolución. Es exactamente la pregunta que salió en la revisión.
- [hecho] **Definir "escala del espesor"** (cuántas veces se agranda la señal de OPL; a escala 8
  la fase envuelve tanto que enmascarar ya tira señal real).
- [hecho] **Agregar el número complementario**: el 183x es reducción de *error* de espesor con
  fase inyectada; la correlación de Pearson es insensible a escala y offset.

## Slide 8 — La referencia no podía validar nada

- [hecho] **Subir el segundo error a la slide** (hoy sólo en notas): el objetivo estaba mal en
  todas las corridas reales (2.5x/0.07 en vez de 2x/0.10) y corregirlo casi no cambió nada.
  El título dice "los dos errores de método" y en la slide se ve uno solo.
- [hecho] **Definir "Nyquist LR"** en media línea: la máxima frecuencia que la grilla de la
  cámara puede representar.

## Slide 9 — La curva histórica

- [hecho] **Definir semi-convergencia** en cuatro palabras (fenómeno real en problemas inversos
  mal condicionados: mejora y después empeora). Sin eso, la anécdota metodológica no se
  entiende.
- [hecho] **Marcarla como candidata a recortar** si la charla va con el tiempo justo: es la
  única slide que no aporta un resultado, sino una advertencia de método. Va anotado en las
  notas del orador, no en la slide.

## Slide 10 — El solver estaba congelado

- [hecho] **Decir cómo se encontró** (control sintético del mismo solver a distintos recortes):
  es el mérito metodológico y hoy no está dicho.
- [hecho] **Acotar la invalidación**: qué queda en pie (lo sintético a recortes 16–32, que es
  donde el paso por defecto todavía era razonable, y todo lo de GD-amplitud) y qué no.
  Tal como está, "todas las corridas reales previas quedan invalidadas" suena a que se cayó
  el proyecto entero.

## Slide 11 — Sintético con la geometría real

- [hecho] **Definir "piso de ruido"**: el residuo que queda cuando el único error restante es el
  ruido de la cámara — es el patrón de comparación de toda la parte real.

## Slide 12 — Fase tipo ruido en la muestra real

- [hecho] **Agregar la distinción que salió en la revisión**: imágenes de la muestra sí hay (el
  primer panel de la figura es la captura LR y se ve el objeto); lo que no está demostrado es
  el valor agregado de FPM. Sin esto la slide suena peor de lo que es.
- [hecho] **Definir *speckle*** en tres palabras (granulado de interferencia).

## Slide 13 — El piso de residuo ~0.29

- [hecho] **Pasar los descartes a formato de tabla** (candidato → qué se midió → veredicto):
  ruido, paso, campo oscuro, brillo por LED, pupila. Hoy es un bullet largo con cinco
  números y es la slide más densa de la charla.
- [hecho] **Aclarar en notas los dos "0.29"**: el piso de residuo es a crop 400 (0.295) y el
  0.29 de la slide 14 es el residuo de entrenamiento del barrido a crop 96. Son corridas
  distintas y conviene no decirlos como si fueran el mismo número.

## Slide 14 — Geometría plana y sobreajuste

- [hecho] **Definir la validación cruzada sobre LEDs** en una línea: se reconstruye sin 20 de los
  81 y se mide el residuo justo sobre esos 20 — separa "ajusta los datos" de "reconstruye el
  objeto". Es el diagnóstico más fuerte de la charla y necesita entenderse en 10 segundos.

## Slide 15 — Estado y qué sigue

- [hecho] **Verificar que los tres encabezados se lean sin ambigüedad** ("Lo que está firme" /
  "Lo que no está" / "Próximos pasos"): el primer ítem de la segunda lista es "reconstrucción
  confiable de la muestra real" y, mal maquetado, se lee como logro.
- [hecho] **Agregar el pedido concreto al grupo**: qué necesita Lucas de ellos (la captura del
  target USAF y el mosaico Zeiss 10x/0.25). Una charla de estado se vuelve útil cuando
  termina en un pedido, no en una lista.
- [hecho] **Arreglar la numeración** de los próximos pasos 3-4-5, que hoy van comprimidos en una
  sola línea con separadores.

## Globales

- [hecho] **Los epígrafes impresos dentro de los PNG son ilegibles a tamaño de slide.** No se
  arreglan (están pensados para el PDF y para el informe), pero conviene que ningún dato
  esencial viva sólo ahí: lo importante ya está en los bullets. Verificar slide por slide al
  aplicar la tanda.
- [hecho] **Reparto de tiempo en notas** por bloque: marco 3 min, sintético 5, campaña real 5,
  estado 5, cierre 2.
- [hecho] **Las dos figuras de respaldo** (fig07, fig11) quedan al final; si el director es de los
  que quiere ver el paisaje de geometría, se puede intercambiar fig11 por fig12 en la
  slide 14.
