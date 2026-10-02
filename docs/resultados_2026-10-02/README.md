# Resultados 2026-10-02 — offset de LED por color, LEDs de borde, teselas, z vs NA

Respaldo de `results/{offset_color,teselas,z_vs_na}_2026-10-02/` (gitignored). Objetos reconstruidos (`out/`) no incluidos.

- `offset_color/INFORME.md`: informe principal (etapas 1-2, diagnóstico de rayas, final_z101, final_z102, dfnorm).
- `teselas/`: FPM por teselas (no resuelve), mapa analítico BF/DF (`mapa_bfdf/`), prueba de normalización DF (`dfnorm_test.py`).
- `z_vs_na/`: paso espectral entre LEDs → z/dx ≈ 75 mm/µm; degeneración z/aumento.

## Conclusiones
1. Offset del die por color confirmado (R +1.06, G +0.63, B +0.15 mm en filas); efecto chico en el residuo.
2. Rampa roja y rayas: LEDs (18,14),(18,16) a horcajadas del borde de pupila, normalizadas como BF aunque son DF
   en gran parte del campo. Excluirlas (rojo, verde) lo resuelve. Normalización DF sirve en rojo, rompe verde
   → pendiente: normalización por zonas según la frontera.
3. Teselas no resuelven el problema (rayas 0.26 rad en 3x3).
4. Óptica real: Zeiss N-Achroplan 2.5x/0.07 (tubo de diseño 164.5 mm) + Thorlabs WFA4101 (tubo 150 mm)
   → aumento nominal 2.28×, no 2.5×. Medidas: z·NA ≈ 7.03 mm, z/dx ≈ 75 (paso espectral).
5. Barrido lrpx a z = 102, NA 0.069 (residuo @40): rojo 0.315/0.320/0.331 para 1.28/1.32/1.362 µm (mínimo
   no encerrado), azul 0.408/0.408/0.414, verde plano. El residuo prefiere z/dx ≈ 80 (aumento ~2.5×):
   tensión con la óptica. Decide una foto de micrómetro de platina.
6. El déficit de volumen de fase de verde/azul (V_G/V_R ≈ 0.5, V_B/V_R ≈ 1.1 vs 1.23/1.42) NO viene de la
   geometría de iluminación.

Mejor configuración actual: z = 102 mm, lrpx 1.28 µm, NA 0.069, offset del die por color, sin (18,14),(18,16) en R y G.
