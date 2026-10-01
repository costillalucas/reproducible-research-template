# Tabla física para interpretar la fase (poliamida en DMSO, captura 28/09b)

λ = 630 / 530 / 470 nm (`src/ptyco_full_simulator/config.py:16-19`). NA obj 0.07, NA sintética 0.48. Cálculo: `calc.py` (en esta carpeta).

## Fuentes de índice (no coinciden)
| Fuente | Δn |
|---|---|
| `results/captura_2026-09-24/j3/t1_baseline/phantom.py:3,21` | n_p 1.53, n_DMSO 1.479 → 0.05 fijo |
| `results/captura_2026-09-25_red/synth.py:28` | 0.05 fijo |
| `results/sim_multiespectral_2026-09-29/sim.py:5,29` | 0.045 + 0.0015/λ² (solo verdad simulada; signo de B opuesto al real) |
| `docs/plan_reconstruccion_conjunta_2026-09-29.md:24-25`, `docs/roadmap_agentic_multispectral_pipeline.md:3138-3140` | DMSO 1.492/1.485/1.477 (470/530/630); nylon 12 n_d ≈ 1.52-1.53 sin dispersión medida; Δn = 0.04-0.05, B ∈ [−0.002, 0] |

**Estimación usada:** nylon Cauchy con n_d = 1.525 y B = 0.006 µm² (Abbe ~45, supuesto) menos el DMSO de la tabla. Incertidumbre ±0.005 en Δn (±10 %).

## Fase esperada
| | R 630 | G 530 | B 470 |
|---|---|---|---|
| n nylon / n DMSO | 1.523 / 1.477 | 1.529 / 1.485 | 1.535 / 1.492 |
| Δn | 0.046 | 0.044 | 0.043 |
| rad/µm (2πΔn/λ) | 0.457 | 0.523 | 0.573 |
| espesor para π / 2π (µm) | 6.9 / 13.7 | 6.0 / 12.0 | 5.5 / 11.0 |
| φ centro D=1 µm | 0.46 | 0.52 | 0.57 |
| D=2 | 0.91 | 1.05 | 1.15 |
| D=5 | 2.29 | 2.61 | 2.87 |
| D=8 | 3.66 | 4.18 | 4.59 |
| D=10 | 4.57 | 5.23 | 5.73 |
| φ con Δn = 0.05 fijo, D=5 | 2.49 | 2.96 | 3.34 |

**Cocientes (misma partícula):** φ_G/φ_R = 1.15, φ_B/φ_R = 1.25 (estimación real). Con Δn constante: 1.19 / 1.34 (= λ_R/λ). Verdad de `sim.py`: 1.23 / 1.42. Un cociente lejos de 1.1-1.35 indica problema de reconstrucción, no de muestra.

## Límites de validez
| | R | G | B |
|---|---|---|---|
| Profundidad de foco λ/NA², NA 0.07 (µm) | 129 | 108 | 96 |
| Profundidad de foco, NA sint. 0.48 (µm) | 2.7 | 2.3 | 2.0 |
| Gradiente máx., grilla (π/píxel; px 0.427 / 0.256 µm) | 7.4 rad/µm | 12.3 | 12.3 |
| Gradiente máx., banda 2π·NA_s/λ | 4.8 rad/µm | 5.7 | 6.4 |
| Fracción del radio representable (banda) | 98.2 % | 98.4 % | 98.4 % |

- Esfera: dφ/dr = 2k·(r/R)/√(1−(r/R)²), infinita en el borde. La fracción representable **no depende del tamaño**: ~98 % por banda, ~99.5 % por grilla. Para D = 10 µm el anillo perdido mide ~0.09 µm, menos de un píxel. **La pendiente del borde no es el límite.** El salto de fase en el píxel del borde llega a π recién con R ≈ 14 µm.
- **El límite real es el modelo de objeto delgado.** Con NA 0.48, la profundidad de foco es de 2-2.7 µm. Para **D ≳ 2-3 µm**, la esfera es más gruesa que esa profundidad, y la fase pasa a ser cualitativa (refracción, desenfoque interno). Además, para **D ≳ 5.5-7 µm**, φ > π y hay riesgo de envolvimiento (>2π para D ≳ 11-14 µm).
- **Resumen:** la fase es cuantitativa para D ≲ 3 µm, aproximada para D de 3 a 6 µm (cerca de un 10-20 % de error esperable) y no confiable para D > ~6-7 µm, donde también hay que desenvolver la fase.
