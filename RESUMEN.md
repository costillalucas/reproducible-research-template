# Resumen: reproducible-research-template

**Repositorio: reproducible-research-template**

Se creó una plantilla de investigación reproducible y, sobre ella, se scaffoldeó un proyecto concreto (`ptyco-full-simulator`) para microscopía FPM (Fourier Ptychographic Microscopy).

## 1. Plantilla base de investigación reproducible

Inspirada en `matiaszaldarriaga/pta-gwb-anisotropy`: un registro de procedencia (`data/numbers.json`) generado por un único script, tags `[src:]`/`[srcnum:]` en el reporte final que se verifican contra ese registro (existencia + precisión mostrada), y un grafo de argumentación en `structure/` (`claims.yaml`, `scripts.yaml`, `outputs.yaml`) cruzado por `scripts/check_provenance.py`.

Se incluyó un ejemplo funcional real (estimación Monte Carlo de π) con pipeline completo compute → checks → gate de procedencia, y tests que prueban que el gate efectivamente rechaza un reporte corrupto.

## 2. Scaffold de `ptyco-full-simulator`

Se movió el ejemplo de π a `examples/pi_estimator/` como referencia autocontenida, y se dejó `src/`, `report/`, `structure/` y `scripts/` reseteados a un placeholder mínimo (`template_wired`) que mantiene el pipeline compute→check→gate funcionando end-to-end, listo para el código real del simulador.

## 3. Bibliografía FPM

Se compiló `references/bibliography.yaml` con 37 papers de Fourier Ptychographic Microscopy (2013-2026), cruzando las notas de lectura existentes en `references/papers/` con los PDFs descargados (35/37) y extrayendo autores completos de los PDFs. Incluye una lista `priority_focus` con las seis brechas de mayor valor detectadas en el código actual del simulador. Se documentó en `references/README.md` cómo citar estos papers a través del mecanismo de procedencia.
    
## 4. Modelo directo FPM y reconstrucción Wirtinger flow

Se agregó `src/ptyco_full_simulator/` con geometría del arreglo de LEDs (`config.py`, `led_array.py`), pupila limitada por NA y muestreo HR/LR (`optics.py`, `spectral_ops.py`), modelo directo que simula la pila de imágenes LR capturadas por un microscopio FPM (`forward_model.py`), y un reconstructor ptychográfico incremental por Wirtinger flow (`reconstruction.py`, basado en Bian et al. 2015). Se sumaron `metrics.py` e `io_utils.py` para comparación con ground truth e I/O de imágenes (incluyendo capturas reales de laboratorio `fila<row>_columna<col>.tiff`).

Dos entry points en `pipelines/`: `simulate_and_reconstruct.py` (objeto conocido → LR simulado → HR reconstruido, comparado contra ground truth) y `reconstruct_real_images.py` (capturas reales → HR reconstruido, sin ground truth).

Los tests (`tests/test_ptyco_simulator.py`) probaron que la reconstrucción efectivamente recupera fase para un objeto moderado, con un control negativo de un solo LED que falla de forma confiable. En el proceso se detectó un bug real: al gradiente de Wirtinger flow le faltaba la normalización 1/N en el adjunto de la ifft2, lo que hacía que el paso efectivo escalara con el tamaño de la imagen y divergiera en arrays más grandes que uno de prueba mínimo (verificado con un test numérico de adjunto).

Limitaciones documentadas: el baseline actual no tiene recuperación de pupila, auto-calibración de LEDs ni step size adaptativo (quedan priorizados en `references/bibliography.yaml`). Un objeto de fase grande/alta frecuencia en una grilla de LEDs chica puede converger a un mínimo local — propiedad conocida de Wirtinger flow vanilla, no un bug.

## 5. Ajuste a la convención real de datos del laboratorio

Se actualizó la lectura de imágenes reales para reflejar cómo el laboratorio guarda las capturas, `data/<channel>/<N>x<N>_recortada_<crop>/fila<row>_columna<col>.tiff` (N = tamaño de grilla de LEDs realmente usado, no siempre 31×31 máximo; crop = recorte central ya aplicado). Se ajustaron `io_utils.real_image_path`/`load_real_lr_stack` y el flag `--crop` de `reconstruct_real_images.py`.
