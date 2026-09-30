# Diagnóstico de la combinación de colores (2026-09-29)

`diag_cadena.py` -> `diag_cadena.json`. Fases VERDADERAS (sin reconstrucción) + ruido de fase gaussiano, grilla 1200 px.
"cadena" = couple_rgb_channels (desenvolvimiento con longitudes de onda sintéticas + ajuste de Cauchy libre, t = C/A).
"disp. conocida" = mismo OPL desenvuelto, pero t = promedio de OPL_c / dn(lambda_c) (A y B conocidos, sin ajustar D).

| muestra | ruido (rad) | cadena corr | disp. conocida corr | vuelta de fase equivocada (verde) |
|---|---|---|---|---|
| delgada (<=3 µm) | 0 / 0.05 / 0.2 | 1.00 / 0.77 / 0.03 | 1.00 / 0.99 / 0.16 | 0 / 0 / 20 % |
| gruesa (<=10 µm, sin superponer) | 0 / 0.05 / 0.2 | 1.00 / 0.98 / 0.13 | 1.00 / 1.00 / 0.57 | 0 / 0 / 23 % |
| superpuesta (<=23 µm, como sim.py) | 0 / 0.05 / 0.2 | 0.55 / 0.54 / 0.14 | 0.97 / 0.97 / 0.65 | 0.2 % / 0.2 % / 24 % |

Error de fase de las reconstrucciones simuladas por color (contra la verdad, sobre partículas): 98 mm rojo 0.54, verde 0.17,
azul 0.17 rad; 74 mm 0.8-1.1 rad. Todas por encima de ~0.1 rad, donde el desenvolvimiento empieza a elegir mal la vuelta.

Conclusiones:
1. La cadena no tiene un error de programación: con fases exactas y sin superposición da 1.00.
2. El techo de 0.59 era real y viene del ajuste de Cauchy LIBRE: amplifica los pocos píxeles (0.2 %) con vuelta equivocada
   (extrapolar C a 1/lambda^2 = 0 con dispersión chica). Con la dispersión conocida, la misma muestra da 0.97.
3. El límite principal es el ruido de fase: por encima de ~0.1 rad el desenvolvimiento con longitudes de onda sintéticas
   se equivoca en 6-24 % de los píxeles. Las reconstrucciones por color tienen 0.17-0.54 rad -> la combinación falla.
4. Mejoras posibles, en orden de costo: (a) usar la dispersión conocida en lugar del ajuste libre (trivial);
   (b) desenvolver con regularización espacial / fase continua por partícula; (c) reconstrucción conjunta de los tres
   colores con un solo mapa de espesor (evita desenvolver; no existe todavía).

Prueba de la mejora (a) sobre las RECONSTRUCCIONES simuladas a 98 mm (espesor contra la verdad sin filtrar):
cadena libre 0.11 -> dispersión conocida, 3 colores 0.55 -> dispersión conocida, verde + azul (sin el rojo, el más ruidoso) 0.80.
Un color solo sin desenvolver: -0.15.
