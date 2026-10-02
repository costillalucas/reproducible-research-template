# Mapa BF/DF por LED en el campo de 400 px (captura 28/09b), 2026-10-02

Cálculo analítico (sin reconstrucción). `mapa.py` (corre en ~10 s) -> `salida.txt` (detalle), `resumen.json`, `fraccion_bf.png`.

**Modelo:** fuente puntual. En el punto r de la muestra, el LED j da sinθ = (r_LED − r)/√(|r_LED − r|² + z²), y es campo claro (BF) si |sinθ| < NA.
Geometría de las reconstrucciones 28/09b (`results/captura_2026-09-28b/*/fpm_red.py`): z = 98 mm, NA 0.07, 2.5x, pixel efectivo 1.28 µm, recorte de 400 px (campo ±256 µm),
paso 6 mm, λ = 0.63/0.53/0.47 µm, offset (0, 3) mm más el die por color en filas (R +1.06, G +0.63, B +0.15 mm). 1 bin espectral = 1/512 µm⁻¹.
Supuesto: el centro del recorte está sobre el eje óptico.

Variantes: `nominal` (offset (0,3)); `die` (offset con die, radio BF R = z·tan(asin 0.07) = 6.877 mm);
`die_Rlibre` (offset con die y radio BF ajustado libre en `docs/resultados_2026-10-01/geometria/frontera`: 7.07/7.12/7.11 mm; es el ajuste del que salen los offsets die).

## 1. LEDs a horcajadas (fracción del campo en BF; frontera en µm desde el centro, + = el centro es BF)

| color | nominal | die (R 6.877) | die_Rlibre | dato (frontera.json) |
|---|---|---|---|---|
| R | (17,14),(17,16),(18,14),(18,16): 0.85, +169 | **ninguno** ((18,14/16) DF en todo el campo) | (18,14),(18,16): 0.14, **−171** | −170 / −178 |
| G | los mismos 4: 0.85, +169 | (18,14),(18,16): 0.20, −136 | (18,14),(18,16): 0.74, **+109** | +103 / +111 |
| B | los mismos 4: 0.85, +169 | (17,14/16): 0.94, +234; (18,14/16): 0.72, +100 | (18,14),(18,16): 0.999, **+331** (frontera en la esquina) | +340 / +326 |

- Sólo `die_Rlibre` reproduce las fronteras medidas en los tres colores (dentro de ~10 µm). Con NA 0.07 exacta y die, el rojo **no** tendría LEDs a horcajadas: la frontera a 170 µm exige R_BF ≈ 7.07 mm (z ≈ 101 mm o NA ≈ 0.072), como ya se anotaba en `runner.py`.
- (16,15) etc.: DF en todo el campo en todas las variantes. BF en todo el campo con die: (17,14),(17,15),(17,16),(18,15) (en B con R 6.877 sólo (17,15),(18,15)).

## 2. Error de k del modelo de k único (k evaluado en el centro del campo)

Prácticamente igual para todos los LEDs (lo domina la geometría campo/z, no el LED): máximo en la esquina del campo
**R 3.0, G 3.6, B 4.0 bins = 0.053 del radio de pupila** (mínimo por LED 2.5/3.0/3.4 bins = 0.044 R_pup). Afecta también a los LEDs que no están a horcajadas.

## 3. Teselas (error de k respecto del k del centro de cada tesela; LEDs a horcajadas por tesela, variante die_Rlibre)

| grilla | tesela | err k máx R/G/B (bins) | fracción R_pup | horcajadas por tesela R | G | B |
|---|---|---|---|---|---|---|
| 1x1 | 400 px | 3.0 / 3.6 / 4.0 | 0.053 | 2 | 2 | 2 |
| 2x2 | 200 px | 1.5 / 1.8 / 2.0 | 0.026 | [1,1,1,1] | [2,2,1,1] | [1,1,0,0] |
| 3x3 | 133 px | 1.0 / 1.2 / 1.3 | 0.017 | 5/9 teselas con ≥1 | 6/9 | 2/9 |
| 4x4 | 100 px | 0.75 / 0.89 / 1.0 | 0.013 | 8/16 | 8/16 | 2/16 |

(nominal: las 4 horcajadas en 1x1; 8/9 y 15/16 teselas afectadas en 3x3/4x4.)

## Lectura / recomendación

- El error de k único es chico (≤ 4 bins, 5 % del radio de pupila) y baja como 1/n; con **4x4 (100 px)** queda ≤ 1 bin en los tres colores, con 3x3 ≈ 1–1.3 bins.
- Teselar **no elimina** los LEDs a horcajadas: la frontera es casi una recta que cruza el campo y sigue partiendo ~la mitad de las teselas en R/G. Lo que sí permite es, por tesela, marcar el LED como BF o DF (o excluirlo sólo en las teselas que corta la frontera).
- Recomendación: teselas de **100 px (4x4)** (o 133 px si hace falta más margen de solapamiento), con la frontera de `die_Rlibre` para decidir, por tesela, qué LEDs excluir o tratar aparte. El error de k por sí solo no justifica teselar por debajo de 200 px; lo que lo justifica es la frontera BF/DF.
