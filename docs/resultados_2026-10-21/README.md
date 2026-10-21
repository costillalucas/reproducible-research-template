# Resultados 21/10

Respaldo de `results/` del día (scripts, JSON, logs, figuras e informes; sin `.npy`/`.npz` ni salidas del solver).

- **`captura_5um/`** (`results/captura_2026-10-21/`, `INFORME.md`): captura roja 15x15 con el eje centrado sobre el LED
  (17,15) (ROI 4000,1942). Centrar arregla los LEDs de borde: rampa de fase 0.03–0.10 → 0.004 rad, held-out del anillo 1
  0.86–0.90 → 0.75, sin excluir LEDs; el offset del die rojo ya está en el eje medido. C1/C3/C4 pasan, C2 falla
  (0.044 < 0.143); el campo tiene 2–6× menos contraste que 28/09b y m2, así que C1/C2 no se comparan entre capturas.
- **`captura_500nm/`** (`results/captura_2026-10-21_500/`, `INFORME.md`): esferas de 500 nm, misma geometría, flat de la
  mañana. ~4× más señal DF y piso de ruido 0.05, pero C1 0.889 y C2 0.011: el límite es el modelo, no el ruido
  (hipótesis: muestra densa y gruesa). Objetos "aislados" = agregados: FWHM promedio 7.0 µm crudo → 3.0–3.2 µm en las
  mitades (nulo 5.3–7.9). Defecto de adquisición: el primer frame tras cambiar la exposición sale casi oscuro.
- **`octubre_capturas/`** y **`diseno_captura/`**: QC/reconstrucción de las capturas de octubre y simulaciones de diseño
  de captura de la mañana (sin informe escrito).

Herramientas nuevas (en la raíz y en `scripts/`, ver README principal): `chequeo.sh` (`scripts/precaptura.py`,
`scripts/leer_offset.py`), `reconstruir.sh` (`scripts/reconstruir.py` + `scripts/fpm_solver/`), `comparar.sh`
(`scripts/comparar.py`) y `puntos.sh` (`scripts/puntos.py`). Prueba con 500 nm, 60 épocas: C1 mínimo en la época 10
(0.873), sobreajuste después (0.880 en la 60). Protocolo de medición: https://claude.ai/artifact/EzybiD26XqJd51XQks4XRy
