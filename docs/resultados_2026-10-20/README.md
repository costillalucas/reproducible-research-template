# Resultados 19–20/10

Respaldo de `results/offset_color_2026-10-02/` (barrido de paso solo): scripts, JSON, logs, `INFORME.md`; ver la última sección.

- **Pregunta:** ¿el aumento es 2.56× a z = 102, o 2.28× nominal con NA viñeteada?
- **Respuesta:** el held-out favorece 2.56× en rojo (+0.055 ± 0.007, también sin las LEDs a horcajadas del borde) y en
  verde (+0.052 ± 0.003), con 5/5 folds en ambos.
- **Además:** el residuo de entrenamiento sobreajusta en verde, así que no sirve como criterio ahí.

## Calibración con micrómetro (20/10)

- **Medición:** la foto del micrómetro (`scripts/calibracion_micrometro.py` → `offset_color/micrometro.json`) da
  **1.290 µm/px, M = 2.48**, con 0.2 % de acuerdo entre mitades. Descarta 2.28× directamente.
- **Reconstrucción:** a lrpx 1.29 (`micrometro_20oct.sh`), el held-out queda apenas peor que a 1.25: +0.010 ± 0.006
  en rojo, +0.014 ± 0.004 en verde.
- **Residuo:** ~3 % en el paso angular de LED. Con la placa y el pixel confirmados por el laboratorio, queda abierto.
- **Geometría de trabajo:** preset `2_5x_medido` (M 2.48, NA 0.067) + `WORKING_Z_DISTANCE_MM = 102`.
  Ver la última sección de `offset_color/INFORME.md`.
