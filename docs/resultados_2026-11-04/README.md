# Resultados 2026-11-04 (cierre semanal)

Respaldo de lo hecho el 04/11 sobre la captura roja del 03/11 (esferas Dantec PSP-5, poliamida 12, en DMSO;
`~/Documents/AleYLu/imagenes_tomadas/2026-11-03-red`, 15x15 LEDs, 2 cuadros/LED, ROI 3968,1966). Los originales y los
`.npy` están en `~/Documents/AleYLu/reconstrucciones/` (fuera del repo); acá van informes, tablas, figuras y código, sin objetos.

## Resultados principales

| Corrida (recorte 360:760 / 80:480, 160 épocas) | C1 mitades | C2 [0,212; 0,45] µm⁻¹ | Nota |
| --- | --- | --- | --- |
| Base, z 102 / NA 0,0669 (`recon_2026-11-03-red_1311`) | 0,592 | **0,185** | primer C2 > 1/7; cruce 1/7 en 2,35 µm (estimador de oct.) |
| Nulo, campo oscuro permutado (`plan_2026-11-04/red_nulo_df`) | 0,882 | 0,008 | |
| Geometría medida, paso por filas (`A_filas`: z·λ 61,4, NA/λ 0,1135) | 0,581 | 0,187 | mejora marginal |
| Geometría medida, promedio filas/columnas (`A_prom`) | 0,594 | 0,162 | |
| Partición "diseño 2" (`particion2`) | 0,780 | 0,042 | **INVÁLIDA**: deja 20–24 % del espectro sin cubrir por mitad |

- **Fase** (`plan_2026-11-04/auditoria/`): 62 partículas, pico mediano 1,97 rad, volumen 22,8 rad·µm²,
  d_vol 4,3 µm (Δn 0,046). d_pico ≈ d_vol con Δn 0,046; con n = 1,50 (Δn 0,023) d_pico 8,6 > d_vol 5,5 → se descarta.
- **Épocas** (`plan_2026-11-04/epocas_200/`, recorte 200 px, hasta 400): C1 y la fase se estabilizan en ~100–160 épocas;
  C2 sigue subiendo (0,214 a 160 → 0,240 a 400). Decisión: 160 épocas fijas como estándar.
- **Geometría**: el solver solo ve z·λ (paso espectral) y NA/λ (radio espectral). Con regla z = 99–100 mm resulta
  NA 0,070 y λ 0,617 µm (predicción). La hoja de datos del panel (Adafruit 1484) no da λ. Radio/paso espectral 1,162
  frente a 1,233–1,245 del borde ajustado (blando). Filas y columnas difieren un 4 % (sin explicar; inclinación descartada).
- **Centrado** (`plan_2026-11-04/centrado/`): ninguno de los dos métodos del chequeo ajusta bien; en rojo, eje ≈ +0,05 pasos.
- **Auditoría** (`plan_2026-11-04/auditoria/AUDITORIA.md`): corrige la fase "±0,15 rad" (era la barra de color), el
  rótulo del C2 0,120 (es la 28/09b) y el origen de z 97,4 / borde 7,04 mm (también la 28/09b).

## Reservas abiertas

- La subida de C2 frente a la 28/09b tiene varias causas posibles (muestra, SNR, centrado, reparto BF, recorte).
- Partición por tablero: BF 1:4 y las 4 diagonales del anillo 1 en la mitad A. La prueba que aísla el reparto BF
  (`plan_2026-11-04/particion2b/particion.json`: campo oscuro por tablero y BF equilibrado) no se corrió.
- C2 solo evalúa hasta NA ≈ 0,28.

## Otros

- `captura_2026-11-03/`: chequeo, figuras de centrado/QC, recorte elegido y comparación con el campo del arco (29/10).
- `deck_fuente/`: fuente del deck semanal (formato del tipo Slides de claude.ai; las figuras son blobs del artifact).
- Código parcheado (copias, no el repo): `plan_2026-11-04/codigo/reconstruir_plan.py` (env NA_OBJ, Z_MM, NULO_DF,
  PUPILA_W_NA) y `reconstruir_plan_part.py` (env PARTICION).
