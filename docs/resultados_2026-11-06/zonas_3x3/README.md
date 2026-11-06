# zonas_3x3 — espectral + borde (a) zona por zona

Para la captura del 06/11: misma muestra roja, sin reenfocar, ROI 3968,1966, misma exposición BF, varias posiciones XY
de la platina (cada posición = una "zona"; el número de zonas es libre), y en cada zona **solo los 9 LEDs centrales**
(17,15) + anillo 1 (cruz y diagonales). Oscuros y flat al final. La zona 1 se puede tomar dos veces seguidas sin mover
(repetibilidad).

El script **no reescribe los métodos**: importa sin cambios `../zonas/codigo/espectral_zonas.py` (espectral, etapa 1
con radio libre) y `../zonas/codigo/centrado.py` (borde (a), s fijo 3538 y s libre). Si tocás esos archivos, cambia esto.

## Comando

Desde esta carpeta (los nombres son un ejemplo; poné los que hayas usado):

```bash
cd /home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-06/zonas_3x3
python3 analizar_zonas.py '2026-11-06-red-zona*' \
    --flat 2026-11-06-red-sinmuestra \
    --dark 2026-11-06-red-dark \
    --dark-flat 2026-11-06-red-sinmuestra-dark \
    --repeticion 2026-11-06-red-zona1 2026-11-06-red-zona1-b \
    --nombre 2026-11-06
```

- Las capturas van como carpetas o globs (entre comillas), relativas a `/home/chanoscopio/Documents/AleYLu/imagenes_tomadas`
  o con ruta absoluta. Se ordenan "natural" (zona2 antes que zona10). Del glob se saltean las que terminan en `-dark` o
  contienen `sinmuestra` o `prueba`, y las que coinciden con `--flat/--dark/--dark-flat`.
- Si tenés un solo juego de oscuros para todo, pasá la misma carpeta en `--dark` y `--dark-flat` (si falta una exposición
  usa la más cercana y avisa).
- `--repeticion A B`: los dos nombres de carpeta (basename) de la zona 1 repetida; agrega la diferencia B − A. Opcional.
- `--procs 3` por defecto (zonas en paralelo). Tarda ≈ 2 min por zona por proceso.
- `--auto` es solo para pruebas con capturas viejas: por captura C usa `C-sinmuestra`, `C-dark`, `C-sinmuestra-dark`.

## LEDs

Antes de correr nada chequea, y corta con `ERROR` si falta alguno:
- en cada zona, los 9 LEDs del 3x3 (los necesita el borde (a); el espectral usa los 5 de la cruz);
- en el flat, los 5 de la cruz (17,15) (16,15) (17,14) (17,16) (18,15).

Nombres esperados: `fila{r}_col{c}_color{x}/<t>ms/imagen_frame_*.tiff`. LEDs de más se ignoran.

## Qué sale

En `resultados/<nombre>/`:
- `zonas.json`: todo (por zona: espectral A y B con radio y centro por LED, NA·z por LED, sd; contraste; borde (a) con
  eje, R en px y pasos, w, s libre, LOO; resumen y repetición).
- `zonas.md`: tablas por zona (espectral, borde) + resumen entre zonas (media, sd, sd rel, min, max por métrica) +
  diferencia de la repetición si se pidió.

Recortes del espectral: A = filas 360:760, cols 80:480; B = filas 360:760, cols 480:880. Contraste de partículas =
rms del pasa-altos de S/F del LED (17,15) en cada recorte, igual que `survey_contraste.py`.

## Pruebas hechas (06/11)

- `python3 analizar_zonas.py 2026-11-03-red 2026-10-30-red-c --auto --nombre prueba_0311_redc` → reproduce el INFORME:
  03/11 A espectral 7.007/6.938, borde 7.40 (s libre 7.49); red-c A 7.266/7.229, borde 7.16 (s libre 6.98); recorte B
  también igual. Ver `resultados/prueba_0311_redc/`.
- Carpeta temporal con solo los 9 LEDs centrales de 2026-11-03-red (symlinks), corrida con flags explícitos y
  `--repeticion` contra la captura completa → mismos números, diferencia 0 en todo. Ver `resultados/prueba_3x3_symlink/`.
  Con una carpeta sin la fila 18 corta con ERROR listando los LEDs faltantes.
