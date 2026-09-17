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
