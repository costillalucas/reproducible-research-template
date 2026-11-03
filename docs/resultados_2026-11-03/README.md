# Resultados 2026-11-03 (rojo, capturas del 30/10)

Respaldo sin arrays pesados (.npy y `datos/prep.npz` quedan en `~/Documents/AleYLu/reconstrucciones/`).
Todas las corridas: 400 px, 160 épocas, `--validar`. C2 = FRC complejo medio entre mitades en [0.212, 0.45] 1/µm
(`plan_2026-11-03/codigo/comun_plan.py:c2`, misma banda para todas). Umbral C2 1/7 ≈ 0.143; empate en C1 0.005.

## Corridas

| carpeta | captura | geometría | C1 (mitades) | C2 | C3 |
|---|---|---|---|---|---|
| `red-c_base` | red-c | z 102, NA 0.0669 | 0.676 | 0.066 | 6.6e-3 |
| `plan_2026-11-03/red-c_na074` | red-c | z 102, NA 0.074 | **0.637** | **0.105** | 8.2e-4 |
| `plan_2026-11-03/red-c_z97_na072` | red-c | z 97.4, NA 0.072 (medida) | 0.674 | 0.078 | 4.3e-4 |
| `plan_2026-11-03/red-c_z97_na072_blanda` | red-c | z 97.4, NA 0.072, pupila erf ancho 0.011 NA | 0.661 | 0.076 | 5.6e-5 |
| `plan_2026-11-03/red-c_nulo_df` | red-c | nulo DF, z 102, NA 0.0669 | 0.882 | 0.009 | 1.2e-1 |
| `red-b_arco_base` | red-b | z 102, NA 0.0669 | 0.710 | 0.013 | 9.2e-3 |
| `plan_2026-11-03/red-b_arco_na074` | red-b | z 102, NA 0.074 (+2 LEDs BF) | 0.685 | 0.011 | 0 |
| `plan_2026-11-03/red-b_arco_nulo_df` | red-b | nulo DF | 0.922 | 0.010 | 9.3e-2 |

Copia parcheada del solver: `plan_2026-11-03/codigo/reconstruir_plan.py` (env `NA_OBJ`, `Z_MM`, `NULO_DF`, `PUPILA_W_NA`).

## Hallazgos

1. **`red-b` NO es el campo del arco** del azul 29/10 (mismo ROI, la platina se movió). La comparación rojo–azul
   (tarea A del plan) no se puede hacer con estos datos. Ver `plan_2026-11-03/INFORME.md` y `fig_a_campos_completos.png`.
2. **Mitades con signo invertido** (`plan_2026-11-03/theta_k/`, `filtro_banda/`): en red-c las mitades A y B coinciden
   como campo complejo (|c| 0.108 en 0.25–0.35 1/µm con NA 0.074, nulo 0.005) pero con ángulo relativo ≈ 180°
   desde k ≈ 0.07 hasta 0.45; no es desenfoque (k² no ajusta), ni corrimiento (sin dependencia de dirección), ni
   conjugado. El nulo muestra lo mismo a k bajo → viene de lo compartido (LEDs BF). Pista sin verificar: la mitad A
   tiene solo el LED central, la B solo los 4 BF inclinados.
3. **Cierre de geometría** (`geometria_fpm.html`): paso espectral 28/09 (s = 50.44 bins) + micrómetro (Δx 1.29) →
   z = 97.4 mm; frontera z·NA = 7.04 mm → NA 0.0723; círculo FFT de la misma captura → 0.0721. El solver usaba
   z 102 / NA 0.0669 (reetiquetado de 0.069·1.25/1.29, no medido). Pero la geometría medida no mejora C1, y la
   pupila blanda recupera solo ~1/3 de la diferencia con NA 0.074 (criterio previo: ambiguo). La NA inflada
   (z·NA 7.55 mm, inconsistente con la frontera) sigue siendo la mejor; queda abierto qué compensa.

## Cambio de código

`scripts/precaptura.py`: N de frames por anillo DF desde la SNR de PICO (p99.9 de bloques 4x4 de muestra − oscuro
píxel a píxel, menos el piso de ruido 3.09σ), tope N_MAX = 4, "sin señal" si el pico < 1σ; SNR de energía como
diagnóstico; misma métrica en `qc`. Antes la mediana (fondo ~0 en DF ralo) daba N ≈ 9 000 000.
`scripts/reconstruir.py`: `--anillo-max N` (29/10).
