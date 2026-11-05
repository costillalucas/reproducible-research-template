# Resultados 2026-11-05

Respaldo de lo hecho el 05/11 sobre la captura roja del 03/11 (esferas PA12 en DMSO, 15x15 LEDs). Se copiaron los
archivos livianos (sin `.npy`/`.npz`). Los originales están en `AleYLu/reconstrucciones/plan_2026-11-04/` y
`AleYLu/reconstrucciones/plan_2026-11-05/sim_borde/`.

## 1. C2 contra las épocas (400 px, recorte 360,80, geometría B: z 102, NA 0.0669, λ 0.63)

`epocas_400b/` (fotos cada 20 épocas con objetos). `epocas_400/` es la misma corrida sin objetos (se olvidó
`--guardar-objetos`): el solver es determinista y sus métricas coinciden.

| época | 20 | 100 | 160 | 260 | 400 |
|---|---|---|---|---|---|
| C2 | 0.126 | 0.171 | 0.185 | 0.199 | 0.210 |
| C1 (R held-out, más bajo es mejor) | 0.597 | 0.596 | 0.592 | 0.588 | 0.585 |
| d_vol [µm] | 4.50 | 4.33 | 4.34 | 4.34 | 4.34 |

- C2 cruza 1/7 en la época ~40. Desacelera (de +0.019 a +0.001 cada 20 épocas), pero a las 400 todavía no se planchó.
- La fase de las esferas queda fija desde la época ~80–100.
- **FRC por banda** (`epocas_400b/frc_bandas.json`). Cambio entre las épocas 160 y 400:
  - BF: 0.000
  - NA 0.13–0.28: +0.025
  - NA 0.28–0.45: +0.053 (se duplica)
  - NA 0.45–0.57: +0.011
  - Más allá de NA_syn (> 0.57): 0.000

  La ganancia de C2 está en las frecuencias que los LEDs sí miden, no más allá. Eso descarta la forma más simple de
  "mitades convergiendo a artefactos", pero no prueba que la resolución gane de verdad. Falta el nulo DF a 400 épocas.

## 2. Geometría (200 px, recorte 460,180, 400 épocas)

| | z | NA | λ | NA/λ | z·λ | NA·z | C1 @160 | C1 @400 | C2 @160 |
|---|---|---|---|---|---|---|---|---|---|
| B (`../resultados_2026-11-04/plan_2026-11-04/epocas_200`) | 102 | 0.0669 | 0.63 | 0.106 | 64.3 | 6.82 | 0.568 | 0.568 | 0.214 |
| física (`epocas_200_fisica`) | 99.5 | 0.070 | 0.617 | 0.1135 | 61.4 | 6.97 | 0.553 | 0.551 | 0.235 |
| solo pupila (`epocas_200_solopupila`) | 102 | 0.0715 | 0.63 | 0.1135 | 64.3 | 7.29 | 0.532 | 0.526 | 0.270 |

- La corrida física carga λ de verdad. Para eso se agregó la variable de entorno `LAM_NM` en `codigo/reconstruir_plan.py`,
  en `cargar_solver`; el log confirma λ 0.617.
- La geometría física queda por debajo de B en C1 en las 20 fotos y en las dos mitades. Pero agrandar solo la pupila
  mejora todavía más. A igual NA/λ, el z·λ físico **empeora** C1 (+0.021).
- C1 mejora a medida que crece NA·z, el radio de la pupila en pasos de LED.

## 3. Simulación de borde duro y blando (`sim_borde/`, ver `sim_borde/INFORME.md`)

- Un borde blando (erf) baja **las dos** mediciones de NA·z, la espectral y la de borde BF/DF, en cantidades parecidas.
  **No explica** la diferencia de 7.0 contra 7.40–7.47.
- Con pupila dura, el método del borde (`centrado.py`, estimación a) recupera la verdad exactamente.
- **Error en el método espectral** (`paso_espectral_0311.py`, que viene de `docs/resultados_2026-10-02/z_vs_na/paso_espectral.py`):
  - La etapa 1 fija el radio en el valor nominal. Con una verdad de 7.40 leía ~6.53.
  - Con el radio libre, sobre los datos reales del 03/11 da **7.01 en filas y 6.94 en columnas** (antes 6.97 / 6.71).
    La anisotropía filas/columnas del 3.8 % era sobre todo un artefacto del método.
  - **No está corregido todavía en el repo.**
- La pupila dura que mejor ajusta una blanda tiene NA ≈ 0.070, igual a la verdad. Una pupila dura no "quiere" crecer.
  Que C1 prefiera NA·z grande sigue sin explicar.
- El ancho de borde ajustado en los datos reales (222–253 px) equivale a un erf de w ≈ 0.011, no 0.0037.

## Pendiente

- Explicar 7.0 (espectral corregido) contra 7.4 (borde). Candidatos sin probar: la escala no telecéntrica s
  (ajustada libre da 2950, se usa 3538 px/paso) y luz de más en DF.
- Decidir la geometría.
- Corregir la etapa 1 del método espectral en el repo.
- Los scripts de análisis tienen λ 0.63 y NA 0.0669 fijos.
- Nulo DF a 400 épocas.
