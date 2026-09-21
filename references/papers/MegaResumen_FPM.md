# Mega-Resumen: Avances en Fourier Ptychographic Microscopy (FPM) (2013-2025)

## 📌 Visión General
La **Fourier Ptychographic Microscopy (FPM)** revolucionó la microscopía en 2013 al desacoplar el tradicional compromiso entre campo de visión (FOV) y resolución. Reemplazando sistemas láser complejos e interferométricos por una simple matriz de LEDs y algoritmos computacionales, FPM logra reconstruir imágenes de **gigapíxeles** con resolución ampliada y perfiles topográficos de fase cuantitativa.

> [!IMPORTANT]
> Tras procesar los 35 papers de tu repositorio, es evidente que la última década de investigación en FPM se ha centrado en solucionar tres cuellos de botella fundamentales: (1) El altísimo **tiempo de adquisición** de imágenes, (2) La necesidad de pre-calibraciones perfectas (alineación, aberraciones, ruido) y (3) El salto a **recuperación volumétrica 3D**.

---

## 🛠️ Evolución Algorítmica y Recuperación de Fase
El verdadero núcleo de FPM son sus algoritmos iterativos. Las innovaciones matemáticas han logrado que la técnica deje de depender de setups perfectos:

*   **Autocorrección Óptica (EPRY & Algoritmos Ciegos):** Algoritmos como EPRY recuperan simultáneamente la imagen y la "función de pupila" del sistema, corrigiendo las aberraciones de las lentes computacionalmente sin necesidad de medir imperfecciones previamente.
*   **Robusticidad Matemática:** Se ha descubierto que optimizar basándose en *funciones de costo de amplitud* (en lugar de intensidad pura) y la aplicación del algoritmo **Wirtinger Flow** o **ADMM** disminuyen el impacto del ruido y permiten el uso de exposiciones de cámara reducidas un ~80%.
*   **Calibración Automática:** Estrategias híbridas eliminan el problema crónico de los LEDs desalineados usando análisis estadístico durante las mismas iteraciones (Self-Calibration).
*   **Residual-Subspace Constraint Framework (RSCF):** Aprovecha métodos de descomposición matemática para discriminar el ruido estocástico del desajuste del modelo, convergiendo más rápido en casos de severa aberración óptica.
*   **FPM Híbrido + TIE (Transport of Intensity Equation):** Mezclar ambas teorías permite, con un solo disparo extra desenfocado, recuperar el espectro de fase de bajísima frecuencia (tradicionalmente difícil en FPM), abriendo las puertas para tomar muestras orgánicas sumamente gruesas.

---

## 🤖 El Boom de la Inteligencia Artificial (Deep Learning)
Las redes neuronales (CNNs) están desplazando gradualmente las iteraciones algebraicas lentas, buscando el escurridizo *Single-Shot FPM* o reconstrucción en tiempo real:

*   **Physics-Informed Neural Networks (PINNs):** En lugar de usar millones de fotos como "caja negra" que a veces causan alucinaciones, la IA de FPM integra la física de propagación de la luz (T-FP, FNN-CP, PbNN). Los parámetros de la muestra y el hardware se auto-optimizan por *back-propagation*.
*   **Representaciones Neuronales Implícitas (INRs):** Para capturas en 3D, se abandonaron los pesados vóxeles cartesianos. FPM-INR modela el volumen de luz de manera matemática continua, logrando **25 veces más velocidad** y reduciendo drásticamente la memoria RAM necesaria.
*   **Co-Diseño Hardware/IA:** Las redes neuronales no solo reconstruyen la imagen; ahora calculan de manera inteligente qué patrón de encendido de los LEDs capta la mayor información posible de la muestra específica, permitiendo usar apenas un par de imágenes para reconstrucciones de altísima fidelidad.

---

## 💡 Innovaciones Extrema de Hardware
Dado que FPM no requiere motores, el enfoque en hardware ha sido maximizar los ángulos y el tiempo de respuesta:

*   **Coded Multiplexing & Downsampling Anular:** Encender múltiples LEDs al mismo tiempo, o limitarse a los extremos de apertura numérica (iluminación anular). Se ha pasado de disparar 200 luces individuales a tomar solo **10 o menos fotografías**, dando pie al FPM Dinámico (Video-Rate / Macro) con un solo sensor.
*   **Spatially-coded FPM (scFP):** La inserción de películas codificadas directamente encima del chip de la cámara para eliminar los problemas de subestimación del índice de refracción.
*   **FPM de Apertura Numérica Sintética Gigante (REFPM):** El acoplamiento de iluminaciones inmersivas (aceite) a LEDs llevó la apertura a un bestial **1.6 NA** y 154 nanómetros de resolución.
*   **Inverse Synthetic Aperture (ISA-FP):** Un enfoque totalmente nuevo donde el sensor de iluminación es fijo y es **la muestra** la que rota mecánicamente. Sumamente útil para objetos espaciales (telescopios/astronomía) o muestras biológicas tridimensionales muy gruesas.

---

## 🧬 Aplicaciones Destacadas
> [!NOTE]
> Gracias a los incrementos en velocidad (algunos setups superan los 25Hz y logran casi medio giga-píxel de ancho de banda espacial por segundo), FPM ha dado el salto de ser una técnica exótica, a dominar múltiples campos en investigación médica e industrial.

1.  **Patología Digital y Transferencia de Color (CFFPM):** Se ha logrado usar algoritmos para teñir/colorear muestras multicapas super-rápidas evadiendo defectos como motas de polvo en el microscopio.
2.  **Imágenes Biológicas "Live-Cell" e In-Vitro:** Observación rápida y libre de marcajes, ideal para visualizar los cambios subcelulares sobre la marcha.
3.  **Monitoreo Ecológico In-Situ:** Se implementó el FPM combinándolo con análisis fractal para seguir colonias enteras de *diatomeas* (algas marinas) determinando al momento si su crecimiento está siendo estresado por metales pesados como cobre.
