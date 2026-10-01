# Iteraciones y criterio de parada en FPM/ptychografía: revisión breve (2026-09-30)

Marcas de verificación: **[L]** leído en el texto completo; **[P]** texto completo leído solo en parte (extracto automático del XML de Europe PMC); **[R]** solo resumen o snippet de búsqueda; **[M]** de memoria o conocimiento general, **no verificado en esta sesión** (tratar como pista, no como cita). Hubo poco tiempo: Optica, Nature y Science bloquearon la descarga y varias fuentes quedaron sin leer.

## 1. Número de iteraciones en papers FPM

| Paper | Iteraciones / criterio | Marca |
|---|---|---|
| Yeh et al. 2015 (comparación de algoritmos) | "To ensure that all algorithms converge to their stable solutions, we use **200 iterations** for each algorithm, except for Wirtinger flow, which requires **500**." Definen convergencia como "the point when the relative phase error reaches its stable point" (necesita la verdad, solo en simulación). Tabla 2: los métodos de segundo orden basados en amplitud convergen en decenas de iteraciones; varios de intensidad divergen con LEDs desalineados. | [L] |
| Bian et al. 2016 (TPWFP) | AP: "100 iterations are enough"; WFP: 1000; PWFP/TPWFP: "200 iterations are enough". El paso μ crece gradualmente (k0 = 330, μ_max = 0.1), truncación a^h = 25. **No hay criterio de parada explícito** ("while not converged"). Fig. 2a: error vs iteración en simulación. | [P] |
| Zuo, Sun, Chen 2016 (AS-FPM) | Paso adaptativo: el paso se mantiene si el cambio relativo de la métrica de error entre ciclos supera una constante η pequeña, y si no se **divide por 2**. Hace estable al método secuencial con ruido sin perder la convergencia rápida inicial. No verifiqué valores de η ni conteos de iteraciones. | [R] |
| Zheng et al. 2013; Ou et al. 2014 (EPRY); Tian et al. 2014 (multiplexado) | No encontré el número de iteraciones en fuentes accesibles. De memoria, AP/EPRY se corre del orden de decenas de ciclos por todos los LEDs, pero **no lo verifiqué**. | [M] |

Yeh 2015 [L] también reporta que (i) **la función de costo es el principal predictor** de robustez experimental: los costos de amplitud y de verosimilitud Poisson son robustos, los de intensidad dan artefactos de alta frecuencia y *phase wrapping* con ruido o desajuste de modelo; (ii) Wirtinger flow de intensidad parece mejor al principio "only due to its slow divergence. If run for many iterations, it will eventually settle on a similarly error-corrupted result"; (iii) Gerchberg-Saxton (primer orden) queda con **errores de baja frecuencia** en la fase y se vuelve inestable con LEDs desalineados porque su paso es demasiado grande; (iv) el ruido Poisson y el desajuste de modelo (aberración, LEDs mal ubicados) producen **artefactos similares**, así que las imágenes solas no permiten separarlos.

## 2. Semi-convergencia y parada temprana

- Landweber y otros métodos iterativos en problemas mal condicionados muestran **semi-convergencia**: el error respecto de la verdad baja y después sube cuando la iteración empieza a ajustar ruido. El número de iteraciones funciona como parámetro de regularización, y la regla clásica para elegirlo es el principio de discrepancia de Morozov: parar cuando el residuo ≈ nivel de ruido (τ·δ, con τ algo mayor que 1). Referencia estándar: Engl, Hanke, Neubauer 1996. [M]
- Para datos Poisson hay una versión del principio de discrepancia: la divergencia de Kullback-Leibler normalizada ≈ 1/2 por píxel (Bertero et al. 2010). [M, no verificado]
- En FPM, Yeh 2015 [L] muestra curvas de error vs iteración (Fig. 6) que se estancan en un piso (amplitud/Poisson) o divergen lentamente (intensidad/WF), lo que coincide cualitativamente con la semi-convergencia. **No encontré un paper FPM que aplique formalmente un principio de discrepancia o parada temprana**; el paso adaptativo de Zuo 2016 [R] es lo más cercano (amortigua la iteración cuando el costo deja de bajar).

## 3. Criterios de parada sin verdad de referencia

1. **Residuo / costo** (amplitud o log-verosimilitud Poisson) vs iteración: necesario pero no suficiente. Baja de forma monótona aunque la reconstrucción se degrade, porque el modelo sobreajusta ruido.
2. **Cambio relativo** ‖x_k − x_{k−1}‖/‖x_k‖: es el criterio implícito de Zuo 2016 [R]. Mide estancamiento, no calidad.
3. **Discrepancia**: comparar el residuo con el nivel de ruido esperado (Poisson: varianza = cuentas; en nuestros datos con darks, Gaussiano de lectura + Poisson). Si el residuo queda por encima del ruido, domina el desajuste de modelo. [M]
4. **Validación cruzada con LEDs apartados**: reconstruir sin un subconjunto de LEDs y medir el error de predicción de esas imágenes vs iteración. Si ese error sube, hay sobreajuste. Es estándar en problemas inversos, pero **no encontré un paper FPM que lo haga** (no significa que no exista).
5. **FRC entre reconstrucciones independientes** (half-set): práctica estándar en cryo-EM (van Heel & Schatz 2005, umbral half-bit [R]) y en ptychografía de rayos X. No pude verificar si Vila-Comamala et al. 2011 usan FRC; su abstract [R] reporta 8 nm de resolución con difference map + refinamiento no lineal. En FPM el half-set es delicado: cada LED muestrea una región distinta de k, así que dos mitades con LEDs disjuntos cubren k de manera distinta. Conviene partir por LEDs intercalados (tablero de ajedrez) o por repeticiones de exposición, si las hay.

## 4. Amplitud vs fase

- Las bajas frecuencias de fase convergen lento o quedan con error en los métodos de primer orden (Yeh 2015, GS [L]).
- El *phase wrapping* y los artefactos de alta frecuencia aparecen con costos de intensidad cuando los datos no son perfectos [L].
- Ringing y lattice que crecen con las iteraciones: es observación común en la comunidad (grilla ligada al paso de los LEDs, bordes de las pupilas), pero **no tengo una cita verificada**. [M]

## 5. Recomendaciones para nuestro barrido

- **Métricas por iteración** (guardar cada 1-5 iteraciones): (a) costo de amplitud y NLL Poisson, separados en campo claro y campo oscuro; (b) cambio relativo del objeto y de la pupila; (c) error de predicción en ~10 % de LEDs apartados (intercalados, que incluyan DF); (d) FRC entre dos reconstrucciones con LEDs intercalados disjuntos, midiendo el corte half-bit vs iteración; (e) energía espectral fuera de la banda del campo claro (lo que aportaría la super-resolución) vs iteración, junto con un indicador de artefactos de grilla (picos en el espectro en múltiplos del paso de LEDs); (f) rango y fondo de la fase (deriva de baja frecuencia, wrapping).
- **Forma esperada**: costo de entrenamiento monótono decreciente hasta un piso; error de LEDs apartados con **forma de U** (mínimo = parada óptima) si hay sobreajuste, o plano si el piso lo pone el desajuste de modelo; corte FRC que sube y se estanca, o baja si los artefactos no correlacionados crecen; la fase de baja frecuencia sigue cambiando después de que la amplitud se estabilizó.
- **Criterio de parada**: el mínimo del error de validación en LEDs apartados, con desempate por la iteración más temprana dentro de 1 σ (estimado con 2-3 particiones distintas). Como resguardo, parar cuando el cambio relativo del costo sea menor a ~1e-3 por ciclo durante 3 ciclos, o cuando el residuo alcance el nivel de ruido Poisson+lectura. Umbrales a calibrar en simulación: no salen de la literatura. Reportar el conteo elegido junto con la curva, no un número fijo tipo "200 como Yeh".

## Referencias

- Zheng G., Horstmeyer R., Yang C. (2013). Wide-field, high-resolution Fourier ptychographic microscopy. *Nat. Photonics* 7, 739-745. doi:10.1038/nphoton.2013.187 [M]
- Ou X., Zheng G., Yang C. (2014). Embedded pupil function recovery for Fourier ptychographic microscopy. *Opt. Express* 22(5), 4960-4972. doi:10.1364/OE.22.004960 [R]
- Tian L., Li X., Ramchandran K., Waller L. (2014). Multiplexed coded illumination for Fourier ptychography with an LED array microscope. *Biomed. Opt. Express* 5(7), 2376-2389. doi:10.1364/BOE.5.002376 [M]
- Yeh L.-H., Dong J., Zhong J., Tian L., Chen M., Tang G., Soltanolkotabi M., Waller L. (2015). Experimental robustness of Fourier ptychography phase retrieval algorithms. *Opt. Express* 23(26), 33214-33240. doi:10.1364/OE.23.033214; arXiv:1511.02986 [L]
- Zuo C., Sun J., Chen Q. (2016). Adaptive step-size strategy for noise-robust Fourier ptychographic microscopy. *Opt. Express* 24(18), 20724-20744. doi:10.1364/OE.24.020724 [R]
- Bian L., Suo J., Chung J., Ou X., Yang C., Chen F., Dai Q. (2016). Fourier ptychographic reconstruction using Poisson maximum likelihood and truncated Wirtinger gradient. *Sci. Rep.* 6, 27384. doi:10.1038/srep27384 (PMC4901273) [P]
- Vila-Comamala J., Diaz A., Guizar-Sicairos M., Mantion A., Kewish C. M., Menzel A., Bunk O., David C. (2011). Characterization of high-resolution diffractive X-ray optics by ptychographic coherent diffractive imaging. *Opt. Express* 19(22), 21333-21344. doi:10.1364/OE.19.021333 [R]
- van Heel M., Schatz M. (2005). Fourier shell correlation threshold criteria. *J. Struct. Biol.* 151, 250-262. doi:10.1016/j.jsb.2005.05.009 [R; DOI de memoria]
- Engl H. W., Hanke M., Neubauer A. (1996). *Regularization of Inverse Problems*. Kluwer. [M]
- Bertero M., Boccacci P., Talenti G., Zanella R., Zanni L. (2010). A discrepancy principle for Poisson data. *Inverse Problems* 26, 105004. [M, no verificado]
