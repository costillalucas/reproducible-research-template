# ¿Qué mejoró la captura (b)? Foco por color contra solapamiento (2026-09-29)

1. Solo cambia la geometría (verde, en foco en las dos capturas; 74 -> 98 mm, solapamiento 31 -> 46 %):
   mitades (C2) 0.024 -> 0.043 (x1.8).
2. Solo cambia el foco (rojo a 98 mm, misma noche y campo; `criterios_foco.py` -> `criterios_foco.json`):

| rojo, 98 mm | fotos no vistas (C1, sin FPM ~0.98) | mitades (C2) |
|---|---|---|
| en su foco | 0.46 | 0.083 |
| con el foco del verde | 0.81 | 0.021 |
| con el foco del azul | 0.86 | 0.024 |

Conclusión: el foco de cada color pesa mucho más que el solapamiento (C2 x3.5-4 contra x1.8; C1 0.46 contra 0.81-0.86).
Con el rojo desenfocado a 98 mm, C2 (0.021) queda al nivel del rojo a 74 mm desenfocado (0.014).
Advertencia: el modelo no incluye el desenfoque; un modelo con desenfoque por color podría recuperar parte.
