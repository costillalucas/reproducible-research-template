# Chequeo de literatura externa: unwrapping multi-wavelength + dispersión n(λ) en FPM

Responde la pregunta abierta #4 de `docs/roadmap_agentic_multispectral_pipeline.md`.
Búsqueda externa (fuera de los 37 papers curados en `references/bibliography.yaml`),
hecha vía WebSearch/WebFetch el 2026-09-17. No se agregó nada a
`references/bibliography.yaml` — esto es solo un chequeo, no una curaduría.

## Veredicto

**Parcial.** El unwrapping multi-wavelength ya se aplicó a una técnica de la
misma familia que FPM (Fourier Ptychographic Topography), publicado hace
apenas unos días — vale citarlo y potencialmente adaptar su algoritmo. La
recuperación de la curva de dispersión n(λ) de la muestra a partir de fases
FPM en 3 canales, en cambio, **no apareció como método publicado y concreto**
en ninguna búsqueda — sigue pareciendo la parte genuinamente nueva del
milestone 2b, al menos hasta donde llega una búsqueda web (no es una
revisión sistemática).

## Papers encontrados

1. **Dual-wavelength Fourier Ptychographic Topography** — Yi Shen, Tongyu Li,
   Hao Wang, Jinyong Kim, Hojun Lee, Wookrae Kim, Jonghyeok Park, Junho Shin,
   Seungbeam Park, Lei Tian. arXiv, subido 2025-12-09 (physics.optics), sin
   venue de revista todavía. `https://arxiv.org/abs/2512.08883`.
   **Es el match más cercano encontrado.** Extiende FPT (topografía por
   Fourier ptychography, mismo marco matemático que FPM pero para medir
   altura de superficie en vez de fase de un objeto transparente) a dos
   longitudes de onda simultáneas, calcula una longitud de onda sintética
   λ_s = λ1·λ2/|λ1−λ2| para ampliar el rango sin ambigüedad a λ_s/2, y hace
   unwrapping vía "búsqueda robusta a ruido del número de envolvimiento" por
   píxel + regularización TV circular global. Validado en muestras de
   silicio estructurado para metrología de semiconductores — **no** en
   muestras biológicas, y **no** recupera ni modela n(λ) de la muestra (el
   objetivo ahí es altura de superficie, no dispersión de índice). Autor
   senior (Lei Tian, BU) es una referencia consistente de la bibliografía
   ya curada del repo (coautor de trabajos de multiplexado FPM). Vale leerlo
   con prioridad para el algoritmo de unwrapping del milestone 2b — el
   problema matemático (resolver el entero de envolvimiento por canal) es
   el mismo que necesitamos, aunque la magnitud física recuperada sea otra.

2. **Color-corrected wavelength multiplexed Fourier Ptychography (CWMFP)** —
   referenciado en resultados de búsqueda vía ScienceDirect
   (`S0030401817307526`) y una patente relacionada de FPM con multiplexado
   de longitud de onda (US 10185137). Usa las tres capturas R/G/B como
   *a priori* para mejorar la precisión del multiplexado espectral (varias
   longitudes de onda encendidas a la vez, no secuenciales), acoplando los
   tres canales en la reconstrucción — pero el acoplamiento es para
   *separar* las contribuciones espectrales mezcladas en una sola captura,
   no para explotar la diferencia de fase entre canales con fines de
   unwrapping o dispersión. Distinto propósito que el nuestro (nuestro
   sistema ya captura secuencial, no multiplexado espectralmente), pero
   confirma que el acoplamiento físico entre canales R/G/B en un mismo
   solver FPM sí tiene precedente — solo que para otro fin.

3. **"Ptychography at all wavelengths"** (Nature Reviews Methods Primers,
   2025) — apareció como review general de ptychography multi-longitud de
   onda; no se leyó en profundidad (es una revisión amplia, no un método
   específico), pero podría ser un buen punto de entrada si se quiere
   contextualizar milestone 2b contra el estado del arte general antes de
   implementar. No confirma ni descarta el método de dispersión específico.

4. Ningún resultado de búsqueda devolvió un método concreto de **ajuste de
   n(λ) paramétrico (tipo Cauchy/Sellmeier) a partir de fases FPM
   multicanal**. Las menciones encontradas son genéricas ("las muestras
   biológicas tienen índice de refracción dependiente de λ", "se puede usar
   para medir dispersión del medio") sin un método/paper concreto detrás.

## Actualización 2026-09-18: búsqueda más profunda, fuera de FPM

Pase adicional, más amplio, específicamente sobre la mitad de dispersión
n(λ) de 2b.ii (la búsqueda del 09-17 fue relativamente estrecha: poca
variación de términos, sin buscar deliberadamente en modalidades QPI
adyacentes a FPM). Sigue sin ser una revisión sistemática (solo
WebSearch/WebFetch, sin bases pagas), pero encontró un precedente mucho
más cercano que el primer pase — con una salvedad importante que queda sin
verificar por paywall.

**Veredicto actualizado: sigue sin aparecer un método publicado
específicamente en FPM**, pero existe una subárea activa y no-FPM
("recuperación simultánea de índice de refracción + espesor/dispersión
desde imagen de fase cuantitativa multi-longitud de onda") con al menos un
paper muy cercano en configuración a este proyecto. La afirmación previa
("no apareció como método publicado y concreto en ninguna búsqueda") era
demasiado fuerte — corregida acá.

### El match más cercano: QPI triple-longitud-de-onda vía QLSI (2022)

**"Triple-wavelength quantitative phase imaging with refractive index
measurement"**, *Optics and Lasers in Engineering*, 2022.
`https://www.sciencedirect.com/science/article/abs/pii/S0143816622001622`
(paywall — solo abstract leído, no el método completo).

Usa quadriwave lateral shearing interferometry (QLSI, una técnica QPI
distinta a FPM) con **tres longitudes de onda: 660, 520 y 488 nm** — casi
idénticas a los LEDs RGB de este proyecto (630/530/470 nm). Según el
abstract y resúmenes de terceros: "las RI en las tres longitudes de onda y
la distribución de espesor físico se calculan de forma independiente con
ayuda de la fórmula de dispersión de Cauchy", y a partir de las RI
recuperadas se puede identificar la composición de la muestra.

**Por qué esto es relevante pero no cierra la pregunta:** la afirmación de
recuperar RI(λ) en 3 puntos *y* el espesor "de forma independiente"
suena exactamente a lo que este proyecto ya probó que es matemáticamente
degenerado (ver `docs/roadmap_agentic_multispectral_pipeline.md`, milestone
2b.ii): con OPL(λ) = n(λ)·t = (A + B/λ²)·t = C + D/λ² (C:=A·t, D:=B·t), la
fase-only en cualquier cantidad de longitudes de onda ≥2 solo determina C y
D — nunca A, B, t por separado, sin importar cuántas ecuaciones haya,
porque el modelo tiene rango 2, no 3. Esta es una restricción de
identificabilidad del modelo, no de qué tan buena sea la implementación
— agregar wavelengths no la rompe.

Dos lecturas posibles del paper de 2022, **sin poder confirmar cuál por el
paywall**:
1. Usa información adicional que el propio QLSI provee más allá de OPL
   pura de transmisión (p. ej. un canal de topografía/deflectometría
   distinto de la fase acumulada) que rompe la degeneración por una vía
   física, no matemática — en ese caso sí sería una solución genuina
   diferente a la nuestra, y valdría la pena adaptarla.
2. Usa una tabla/base de datos de materiales conocidos (consistente con la
   frase "se puede identificar la composición de la muestra") para elegir
   entre las infinitas ternas (A,B,t) consistentes con (C,D) la que
   coincide con un material tabulado — en ese caso es matemáticamente el
   mismo tipo de prior externo que ya usa `resolve_thickness_and_dispersion`
   de este proyecto (un A conocido de antemano), solo que con una tabla en
   vez de un solo valor asumido. Si es este el caso, **valida** el enfoque
   ya tomado acá en vez de superarlo.

**Acción recomendada, no hecha todavía**: conseguir el texto completo (vía
acceso institucional o interbibliotecario) antes de asumir cualquiera de
las dos lecturas. Es el paper más importante para leer si se sigue
invirtiendo en 2b.ii — o bien resuelve el problema que este proyecto
encontró (hay que adaptar su método), o bien confirma independientemente
que el problema es real y su "solución" es el mismo tipo de atajo que ya
usamos (hay que citarlo como respaldo, no como método a copiar).

### Otros hallazgos de este pase, menos centrales

- **Familia "dual-wavelength decoupling" de n y t** (no confundir con lo de
  arriba — resuelve un problema *más simple*): Cardenas & Mohanty,
  "Decoupling of geometric thickness and refractive index in quantitative
  phase microscopy", Opt. Lett. 38(6):1007 (2013); "Dual-wavelength
  diffraction phase microscopy for simultaneous measurement of refractive
  index and thickness", Opt. Lett. 39(10):2908 (2014); más una versión 2025
  por holografía digital dual-wavelength. Estos métodos tratan el índice de
  la muestra como **un solo escalar no-dispersivo** (no una curva n(λ)) y
  resuelven 2 ecuaciones para 2 incógnitas (n, t) — el problema clásico de
  "un solo n·t degenerado" en una sola longitud de onda, no el problema de
  *forma* de la curva de dispersión que persigue 2b.ii. No aplican
  directamente, pero confirman que la estrategia general
  "multi-λ para separar índice de espesor" es un patrón establecido en QPI.
- **"Quantitative dispersion microscopy"** (Fu et al., Biomed. Opt. Express
  1(2):347, 2010, PMC2989611) — el paper fundacional de la línea "dispersión
  como fuente de contraste" (p. ej. hemoglobina). Mide sensibilidad a la
  dispersión, no separa A/B/t; contexto útil, no un método a adaptar
  directamente.
- **"Refractive index estimation in biological tissues by quantitative
  phase imaging"** (ScienceDirect, S0925346723006596, 2023) y
  **"Projected refractive index framework for multi-wavelength phase
  retrieval"** (Opt. Lett. 47(22):5965, 2022) — ambos paywalled, no se pudo
  leer el método; quedan como candidatos a revisar si se profundiza más.
- Búsqueda de citas de `arxiv.org/abs/2512.08883` (Shen et al. 2025) no
  encontró follow-ups enfocados en dispersión — sigue siendo topografía, no
  dispersión de muestra.

### Implicación actualizada para milestone 2b.ii

No cambia la recomendación práctica (seguir con el enfoque de asumir A
externo, ya implementado), pero sí cambia la confianza en la novedad: la
idea de "recuperar dispersión desde fase multi-λ" **tiene precedente
directo fuera de FPM** (el paper QLSI de 2022, con longitudes de onda casi
idénticas a las de este labo). Lo que sigue sin precedente encontrado es
específicamente hacerlo **en un contexto FPM/ptychográfico** — ahí sigue
siendo la parte más nueva del proyecto, pero enmarcarlo como "nadie midió
dispersión con múltiples longitudes de onda antes" ya no sería honesto; hay
que enmarcarlo como "se adapta una técnica ya usada en otras modalidades
QPI a FPM por primera vez" (más modesto, pero más preciso). No se agregó
ningún paper nuevo a `references/bibliography.yaml` — quedan listados acá
para que el usuario confirme cuáles vale la pena curar formalmente.

## Implicación para milestone 2b

- **Unwrapping (primera mitad de 2b):** no partir de cero — leer
  `arxiv.org/abs/2512.08883` (Shen et al. 2025) antes de diseñar el
  algoritmo propio. Su técnica de longitud de onda sintética + búsqueda de
  número de envolvimiento por píxel es directamente aplicable a 2-3 canales
  RGB, aunque haya que adaptarla de "altura de superficie" a "fase de
  objeto transparente". Vale sumarlo a `references/bibliography.yaml` como
  entrada nueva si se decide seguir con 2b (no se agregó automáticamente acá
  para no tocar la curaduría sin que el usuario lo confirme).
- **Dispersión n(λ) (segunda mitad de 2b):** proceder según lo planeado en
  el roadmap — no se encontró un método publicado equivalente al ajuste
  paramétrico de 3 incógnitas (A, B, t) propuesto. Esta sigue siendo la
  parte con mayor chance de ser una contribución genuinamente nueva, pero
  con la salvedad de que esta búsqueda no es exhaustiva (no se revisaron
  papers detrás de paywall más allá de lo que devolvió la búsqueda web, ni
  se hizo una revisión sistemática en bases como Web of Science/Scopus).
