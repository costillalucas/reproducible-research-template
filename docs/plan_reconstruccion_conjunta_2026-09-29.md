# Plan: reconstrucción conjunta de los tres colores (borrador 2026-09-29, ~4 h sin supervisión)

## Por qué
La cadena actual (reconstruir cada color por separado, después combinar) falla en simulación: el desenvolvimiento con
longitudes de onda sintéticas necesita error de fase < ~0.1 rad y las reconstrucciones por color tienen 0.17-0.54 rad
(`results/sim_multiespectral_2026-09-29/DIAGNOSTICO.md`). Mejor resultado hoy: dispersión conocida, verde + azul, correlación
del espesor 0.80. Reconstruir los tres colores juntos con UN espesor compartido evita desenvolver: el ajuste va directo
contra las fotos.

## Modelo
- Espesor t(x) compartido, en una grilla común para los tres colores: 1600 px, 0.32 µm (factor 4 sobre la cámara). A 98 mm la
  frecuencia máxima (esquinas de la matriz) es 0.96 / 1.14 / 1.28 1/µm (rojo / verde / azul) y el límite de esta grilla es
  1.56 1/µm. 1200 px (0.427 µm, límite 1.17) NO alcanza para el azul. Hay que verificar que `led_crop_window` funcione
  con factor 4 en los tres colores.
- Objeto por color: O_c(x) = a_c(x) · exp(i · 2π · dn(λ_c) · t(x) / λ_c), con dn(λ) = A + B/λ².
- Amplitud: a_c(x) libre por color (A1) o un solo a(x) compartido (A2). Se prueban las dos:
  - simulación, sobre la muestra actual (amplitud 0.9 igual en los tres colores: A2 gana por construcción) y sobre una
    variante con amplitud distinta por color (0.95 / 0.90 / 0.85 dentro de las partículas), para medir cuánto pierde A2
    cuando su suposición es falsa;
  - datos reales: las dos; se elige la que mejor predice las fotos no vistas (C1, promedio de los tres colores). Regla fijada
    antes de correr.
- Dispersión, dn(λ) = A + B/λ² (diferencia partícula - medio). Tablas (2026-09-29): DMSO n = 1.492 / 1.485 / 1.477
  (470 / 530 / 630 nm; refractiveindex.info, Li 2022 y Kozma 2005), B_DMSO = 0.006-0.0075; nylon 12 n_d ≈ 1.52-1.53, sin dato
  de dispersión (supuesto Abbe 40-55 -> B_nylon 0.005-0.007). Resultado: A = 0.04-0.05, B = -0.002 a 0 (las dispersiones casi
  se cancelan; la simulación usó +0.0015, signo opuesto).
  - Simulación: A y B verdaderos conocidos; además D2 (B ajustado, arrancando en 0) debe recuperar 0.0015, si no, no se usa.
  - Datos reales: A = 0.045 fijo (solo escala t). D1: B = 0 (principal, lo que dicen las tablas). D2: B ajustado, limitado a
    [-0.003, +0.001]. Decide C1. Si D2 da un B fuera del rango de las tablas, anotarlo como señal de que compensa otra cosa.
- Datos reales: el corrimiento lateral de cada color respecto del verde (ya medido en `comparar_colores.json`) entra como
  corrimiento conocido de t para ese color.
- Fotos: mismo modelo directo que `fpm_red.predict` (recorte del espectro por LED y pupila circular NA/λ_c), con la geometría
  de LEDs de cada color.

## Algoritmo
- Función de costo: Σ_c Σ_k w_k ‖ |ψ_ck| − √I_ck ‖² (la misma del solver actual, pero sumando los tres colores).
- Gradiente a mano (Wirtinger): el gradiente respecto de O_c es el del solver actual; después, por regla de la cadena,
  ∂L/∂t = Σ_c Re(conj(i κ_c O_c) · g_c), con κ_c = 2π dn(λ_c)/λ_c, y ∂L/∂a_c = Re(conj(O_c/a_c) · g_c).
- Actualización: descenso con momento (Nesterov) o Adam, lote completo, 150 vueltas.
- Inicio: t a partir del verde reconstruido por separado (fase envuelta → t en la zona sin vueltas), o la cadena con dispersión
  conocida (0.55-0.80). Opción de arranque grueso a fino: primero campo claro y el primer anillo, después el resto.
- Chequeo obligatorio antes de usarlo: gradiente contra diferencias finitas en un problema chico (64 px, 9 LEDs).

## Criterios fijados ANTES de correr
Simulación (98 mm, ruido medido; verdad en `results/sim_multiespectral_2026-09-29/verdad.npz`):
- S1: correlación del espesor con la verdad ≥ 0.90 (hoy, lo mejor: 0.80).
- S2: error de fase por color menor que el de la reconstrucción independiente (0.54 / 0.17 / 0.17 rad).
- S3: FRC entre mitades (damero) en la banda fina ≥ la de las reconstrucciones independientes.
Si S1 falla, no se pasa a datos reales: se informa por qué.

Datos reales (captura 28/09 b):
- R1: por color, el error de predicción de fotos no vistas (5 grupos) no empeora más de 0.05 respecto de lo independiente
  (0.46 / 0.62 / 0.60).
- R2: FRC entre mitades de t conjunto en [2NA/λ_rojo, 0.45] 1/µm ≥ 0.143 y ≥ nulo (geometría desordenada) + 0.068.
  Hoy, lo mejor por color: 0.099 (azul).

## Cronograma (~4 h)
| h | qué | salida |
|---|---|---|
| 0:00-0:50 | solver `results/conjunta_2026-09-30/joint.py`, chequeo de gradiente, prueba chica | joint.py, test_gradiente.txt |
| 0:50-2:00 | simulación 98 mm: conjunta (A1, A2), mitades; comparación con independiente y cadena | sim.json, figs |
| 2:00-3:20 | datos reales (b): completa, mitades, nulo, 5 grupos (si pasó S1) | real.json, figs |
| 3:20-4:00 | informe, figuras, nota de retome | INFORME.md |
CPU: 4 núcleos, hasta 3 procesos en paralelo; el que ejecuta revisa el avance cada ~20 min.

## Reglas
- No tocar el repositorio de Lucas (`ptyco-full-simulator` de Lucas), `jobs/` ni `_factor_probe.py`; no commitear en main.
- No cambiar la charla ni el resumen.
- Si algo se atasca más de 30 min, anotarlo y pasar a lo siguiente del cronograma.
