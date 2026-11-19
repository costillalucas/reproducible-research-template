# Resultados 19/11/2026: límite de resolución con redes de período conocido (rojo y azul)

Reconstrucciones en `~/Documents/AleYLu/reconstrucciones/2026-11-19/`. Todas con z 145,6 mm, NA 0,0747, 160 épocas y
`--validar`, salvo que se indique otra cosa. Las predicciones se escribieron antes de correr.

## 1. Rojo, red 500 l/mm (T = 2,000 µm): barrido de tamaño de grid

Captura `2026-11-18.2048ms-grilla.c` (21×21), subgrid con la nueva opción `--lado-max N` de `scripts/reconstruir.py`.
Predicción de Lucas: el orden ±1 entra con LEDs a 6,0–10,3 pasos → visible en 19/17/15, gradual en 13, ausente en 11.

| Grid | Pico/mediana (completa) | Pico (µm⁻¹) | ¿Red? | C1 |
| --- | --- | --- | --- | --- |
| 21 (18/11) | 165 | 0,499 | sí | 0,794 |
| 19 | 368 | 0,499 | sí | 0,796 |
| 17 | 187 | 0,499 | sí | 0,798 |
| 15 | 170 | 0,506 | sí | 0,797 |
| 13 | 73 | 0,483 | marginal (mitades en 0,43–0,45) | 0,794 |
| 11 | 24 | 0,420 | **no** (borde de la cobertura ≈ 0,44) | 0,792 |

- La forma predicha se cumple. **El umbral pico/mediana < 10 solo no alcanza**: el 11×11 da 24 sin red. Hace falta
  además un criterio de frecuencia (|f − 1/T| chico).
- 19×19 = 368 es atípico (pico ×2, mediana −6 %; `pico_mediana.py`): es una sola corrida y no marca una tendencia.
- C1 no depende del grid: se mide en anillos < 7.

## 2. Azul: capturas y calibración

- **Die azul:** el eje aparece corrido −0,156 pasos respecto del rojo. Coincide con los offsets del die del 01/10
  (B − R = 0,15 − 1,06 mm = −0,152 pasos). Se recentró el ROI (OffsetY 1008).
- **Borde campo claro/oscuro:** R = 1,833 pasos en azul contra 1,794 en rojo a igual z → NA efectiva azul ≈ 0,0763.
- **Darks:** 4 frames por exposición (`N_DARKS = 4` en el script de captura, con `N_CAMARA` corregido).
- **Lóbulos crudos de la red 500** (`lobulos_azul.py`): a 4–7 pasos a lo largo de las filas (predicho 3,9–7,9),
  con meseta constante (|c₁|²).

### Red 500 l/mm en azul (17×17, `2026-11-19.2048ms-grilla.a`)

| NA | Recorte | Pico (µm⁻¹) | T (µm) | C1 |
| --- | --- | --- | --- | --- |
| 0,0747 | 400 | 0,517 | 1,934 | 0,922 (no pasa) |
| 0,0763 | 400 | 0,515 | 1,942 | 0,923 (no pasa) |
| 0,0747 | 200 | 0,498 | 2,010 | 0,900 |

**Barrido de λ vía la degeneración z·λ** (`correr_azul500_lambda.sh`): C1 queda en 0,899–0,902 para λ entre 0,460 y
0,502 → **λ no explica la falla de C1**. El pico queda en el nominal con λ ≈ 0,47–0,48, así que el 0,47 del config es
compatible. El estimador del pico tiene una dispersión de ~2–4 % entre recortes y mitades.

## 3. Azul, grilla 1000 l/mm (T = 1,000 µm), 29×29: primera superresolución a 1 µm

Captura `2026-11-19.2048ms.grilla.b-1000`, flat `…sinmuestra.azul.1000`. Lóbulo crudo (`lobulos_1um.py`,
`perfil_1um.py`): entrada a ~10,3 pasos (predicho 10,4), meseta 11–14. Recorte de 200 px (`--recorte 348,459`).

| Grid | Pico (completa) | Pico/mediana | Mitad A | Mitad B | C1 |
| --- | --- | --- | --- | --- | --- |
| 29 | 0,966 | 544 | 0,963 | 0,970 | 0,765 (pasa) |
| 27 | 0,985 | 375 | 0,967 | 0,962 | 0,764 |
| 25 | 0,966 | 326 | 0,960 | 0,905 ✗ | 0,764 |
| 23 | 0,970 | 430 | 0,960 | 0,884 ✗ | 0,764 |
| 21 | 0,928 | 194 | 0,899 | 0,894 | 0,765 |
| 19 | 0,892 | 47 | 0,811 | 0,822 | 0,767 |

- **Límite: 23×23** (11 pasos, NA de iluminación ≈ 0,41). El 21×21 cae en el borde de la cobertura (0,97 µm⁻¹) y en el
  19×19 el pico es un artefacto del borde (0,90).
- Se ven las líneas en el zoom (`azul1000_29x29_reconstruccion.png`); el objetivo solo resuelve ~6,3 µm.
- La mitad B necesita ≥ 27×27 (pregunta abierta: distribución en tablero de ajedrez de los LEDs del lóbulo).
- C1 pasa con esta muestra y falla con la red 500 con la misma configuración → **la falla de C1 depende del campo o la
  muestra, no del color**.

### Iteraciones (`epocas.py`, `epocas.txt`; 29×29 con 320 épocas)

- C1 converge a las ~40 épocas (0,767 → 0,764), pero no ve la grilla (anillos < 7).
- La posición del pico queda fija desde la época 20 (0,966): el −3,4 % es sistemático, no de convergencia.
- Pico/mediana máximo a las 120–160 épocas (~547) y **baja a 492 a las 320**, mientras R de ajuste sigue bajando
  (0,72 → 0,68): sobreajuste. **160 épocas alcanzan.** Con grids chicos (23×23) el contraste todavía sube a las 160.

## 4. ¿Red de amplitud o de fase? (`ordenes.py`)

Con muestra/flat crudos (|c₁|² con corrección cos⁴θ y patrón angular del LED sin calibrar, ±30 %):
rojo |c₀|² 0,67, |c₁|² 0,032; azul 0,58 y 0,027; cociente 0,047 / 0,046. **No es de amplitud binaria** (0,41). Es una
red débil y a simple vista transparente. La prueba con λ (en una red de fase el cociente crecería ~1,8× en azul) no
alcanza a decidir por la calibración angular.

## Abierto

Derivar λ_azul de forma independiente (z y λ siguen sin separarse), por qué falla C1 en el campo de la red 500,
el moiré diagonal (~15 µm) en las dos redes en azul, la mitad B en 23/25, una métrica de épocas sin patrón conocido,
y medir σ con la resta de los darks de 2012 y 2048 ms.
