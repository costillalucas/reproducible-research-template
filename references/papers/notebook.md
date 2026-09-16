# Ptychography Notebook — resumen de lectura y aplicabilidad

Guía de lectura de los ~37 papers de Fourier Ptychographic Microscopy recopilados (2013–2026), con notas de qué se puede llevar a `ptyco-full-simulator`. También publicada como artifact interactivo: https://claude.ai/code/artifact/d178237f-f489-423c-a38b-d96b53e9e59f

**Cómo leer esto:** se revisó el pipeline actual (`common.py`, `Reconstruccion_FPM.py`, `real_images_reconstruction.py`, `imagenes_simulacion_reconstruccion.py`) para marcar qué papers atacan un hueco concreto del código — esos llevan la marca **🔧 Aplicable**. El resto son contexto/reviews o técnicas menos directas para el caso actual, con resumen más corto.

La reconstrucción propia ya implementa **Truncated Wirtinger Flow con modelado de ruido** (los comentarios de `common.py` citan explícitamente "Bian 2016" ecuación por ecuación) — un algoritmo sólido y relativamente moderno. Los huecos más claros frente a la literatura: la `pupil` es una máscara circular fija que nunca se actualiza (sin recuperación de aberraciones), no hay auto-calibración de ángulos LED a partir de datos reales (solo se simula el error, no se corrige), el step-size es una rampa fija codeada a mano (con un intento de Barzilai-Borwein ya escrito pero comentado), y no hay ningún componente de deep learning en el pipeline.

---

## ★ Dónde enfocar primero

1. **Recuperación de pupila / aberraciones (EPRY, 2014).** Hueco: `create_pupil()` arma una máscara circular fija; nunca se refina dentro del loop. Agregar la actualización de pupila al mismo bucle de Wirtinger flow que ya existe no es un cambio de arquitectura, es una actualización más por iteración.

2. **Auto-calibración de ángulos LED con datos reales (Eckert/Waller, 2018).** Hueco: `led_offset_incorporated`, `led_spacing_error_incorporated` simulan error, pero `reconstruct_real_images` no lo corrige. Su método de correlación espectral refina los ángulos dentro del propio solver iterativo, sin hardware ni calibración externa adicional.

3. **Step-size adaptativo por convergencia, no por rampa fija (Zuo/Sun/Chen, 2016).** Hueco: `mu = min(1-exp(-alpha*ndx), mu_max)` es una rampa fija hardcodeada. Reduce el step-size solo cuando la convergencia se estanca — y de hecho ya hay un intento de Barzilai-Borwein escrito y comentado en `reconstruct_test` que resuelve el mismo problema por otra vía.

4. **Acelerar reconstrucción con implicit neural representations (FPM-INR, 2023).** Hueco: corridas largas con snapshots cada 100 iteraciones (`imagenes_intermedias_iter_*`) sugieren reconstrucciones costosas en tiempo/memoria. Reporta hasta 25× más velocidad y 80× menos memoria.

5. **Multiplexado de LEDs para acortar la captura (Tian/Waller, 2014).** Hueco: `toma_muchas_imagenes.py` / `iluminacion_con_toma_de_imagene.py` capturan un LED a la vez, secuencialmente. Prender varios LEDs random por captura reduce el número total de imágenes sin perder calidad.

6. **Cuantificar la confianza de la reconstrucción (Uncertainty-aware FP, 2025).** Hueco: las métricas de error solo existen cuando hay target (simulación). Estima un mapa de confianza por región sin necesitar un ground truth — útil justo para datos reales.

---

## 2013 — los fundacionales

- **Wide-field, high-resolution Fourier ptychographic microscopy** — Zheng, Horstmeyer, Yang · Nature Photonics · `10.1038/nphoton.2013.187`. El paper que inventa FPM.
- **Quantitative phase imaging via Fourier ptychographic microscopy** — Ou, Horstmeyer, Yang, Zheng · Optics Letters · `10.1364/OL.38.004845`. Foco en recuperación de fase cuantitativa (OPD).
- **Fourier Ptychographic Microscopy 10 Years on: A Review** — Xu, Wu, Tan, Liao, Wang, Chen, Pan · Cells (2024) · `10.3390/cells13040324`. Mapa de toda la década.

## 2014

- 🔧 **Embedded Pupil Function Recovery for FPM (EPRY)** — Ou, Zheng, Yang · Optics Express · `10.1364/OE.22.004960`. Base de facto de casi todas las implementaciones FPM posteriores a 2014. *Aplicable:* la `pupil` en `common.py` es estática; EPRY agrega una actualización de pupila con el mismo gradiente que ya se calcula para `z`.
- 🔧 **Multiplexed Coded Illumination for FP with an LED Array Microscope** — Tian, Li, Ramchandran, Waller · Biomedical Optics Express · `10.1364/BOE.5.002376`. *Aplicable:* cambia el esquema de `toma_muchas_imagenes.py` de "un LED → una imagen" a "subconjunto de LEDs → una imagen".

## 2015

- **Fourier Ptychographic Reconstruction Using Wirtinger Flow Optimization** — Bian, Suo, Zheng, Guo, Chen, Dai · Optics Express · `10.1364/OE.23.004856`. **Ya en uso**: el framework que `reconstruct()`/`reconstruct_test()` implementan casi literalmente.
- **Experimental Robustness of FP Phase Retrieval Algorithms** — Yeh, Dong, Zhong, Tian, Chen, Tang, Soltanolkotabi, Waller · Optics Express · `10.1364/OE.23.033214`. Checklist para diagnosticar por qué una reconstrucción real sale peor que la simulada.

## 2016

- 🔧 **Adaptive Step-Size Strategy for Noise-Robust FPM** — Zuo, Sun, Chen · Optics Express · `10.1364/OE.24.020724`. *Aplicable:* contrastar contra la rampa fija de `mu` en `reconstruct()`; condicionar la reducción de `mu` al `recovery_errs[ndx]` ya trackeado.
- **Diffraction Tomography with Fourier Ptychography** — Horstmeyer, Chung, Ou, Zheng, Yang · Optica · `10.1364/OPTICA.3.000827`. Extiende FPM a 3D. Relevante solo si se quiere ir más allá de fase 2D/OPD.

## 2017

- 🔧 **FPM with Sparse Representation** — Zhang, Song, Zhang, Dai · Scientific Reports · `10.1038/s41598-017-09090-8`. *Aplicable:* sumar un término extra a `Cz` en el update de `z` dentro de `reconstruct()`.
- **Resolution-Enhanced FPM Based on High-NA Illuminations** — Sun, Zuo, Zhang, Chen · Scientific Reports · `10.1038/s41598-017-01346-7`. Relevante si el montaje admite inmersión en aceite.

## 2018

- 🔧 **Efficient Illumination Angle Self-Calibration in FP** — Eckert, Phillips, Waller · Applied Optics · `10.1364/AO.57.005434`. *Aplicable:* corrige las posiciones LED asumidas en `calculate_k_vectors_k_indices` a partir de los propios datos capturados.
- **High-Speed FPM Based on Programmable Annular Illuminations** — Sun, Zuo, Zhang, Fan, Chen · Scientific Reports · `10.1038/s41598-018-25797-8`. Acelera adquisición con patrones anulares programables.

## 2019

- **Illumination Pattern Design with Deep Learning for Single-Shot FPM** — Cheng, Strachan, Weiss, Deb, Carone, Ganapati · Optics Express · `10.1364/OE.27.000644`. Hasta 69× menos tiempo de adquisición.
- **Data-Driven Design for FPM** — Kellman, Bostan, Chen, Waller · IEEE ICCP 2019 · `10.1109/ICCPHOT.2019.8747339`. Aprende el patrón de fuente óptimo vía red "physics-based".

## 2020

- **High-Resolution and Large FOV FPM and Its Applications in Biomedicine** — Pan, Zuo, Yao · Reports on Progress in Physics · `10.1088/1361-6633/aba6f0`. Review de referencia muy citado.
- **Fourier Ptychography: Current Applications and Future Promises** — Konda, Loetgering, Zhou, Xu, Harvey, Horstmeyer · Optics Express · `10.1364/OE.386168`. Con Roarke Horstmeyer, coautor del fundacional.
- 🔧 **Forward Imaging NN with Correction of Positional Misalignment for FPM** — Zhang, Tao, Yang, Wu, Sun, Wang, Zheng · Optics Express · `10.1364/OE.398951`. *Aplicable:* alternativa basada en NN al método de auto-calibración de Eckert/Waller (2018) — mismo problema, enfoque de aprendizaje en vez de correlación espectral.

## 2021

- **High-Speed FPM for Quantitative Phase Imaging** — Xiao, Wei, Xue, Kuang, Yang, Wei, Lin, Zhou · Optics Letters · `10.1364/OL.428731`. Láser + DMD, >42 fps. Sin copia de acceso abierto disponible.
- 🔧 **NN Model Assisted FP with Zernike Aberration Recovery and TV Constraint** — Zhang, Liu, Jiang, Dixit, Song, Zhang, Ji, Li · J. Biomedical Optics · `10.1117/1.JBO.26.3.036502`. *Aplicable:* tercer enfoque para el mismo hueco de pupila/aberraciones que EPRY (2014), con parametrización de Zernike y entrenamiento por gradiente — útil si se migra parte del solver a un framework diferenciable (PyTorch/JAX).

## 2022

- 🔧 **FPM via Alternating Direction Method of Multipliers (ADMM-FPM)** — Cells · `10.3390/cells11091512`. *Aplicable:* punto de comparación directo para `reconstruct()` si el TWF actual se estanca con datos muy ruidosos.
- **Integration of FP with Machine Learning: An Alternative Scheme** — Biomedical Optics Express · `10.1364/BOE.464001`. Discusión de trade-offs, no un método nuevo específico.
- **Deep Multi-Feature Transfer Network for FPM Reconstruction** — Sensors · `10.3390/s22031237`. Transfer learning de tres redes preentrenadas fusionadas.
- **Rapid Full-Color FPM via Spatially Filtered Color Transfer** — Chen, Wang, Pan, Zheng, Ma, Yao · Photonics Research · `10.1364/PRJ.473038`. Relevante solo si el sensor/pipeline es a color.

## 2023

- 🔧 **FPM-INR: Reconstrucción con Implicit Neural Representations** — Zhou, Feng, Guo, Lin, Liang, Metzler, Yang · Optica · `10.1364/OPTICA.505283`. *Aplicable:* si el tiempo/memoria de `reconstruct()` es un límite, esta es la mejora de mayor impacto de toda la lista.
- **Long-Range FP Imaging of the Dynamic Object with a Single Camera** — Jiang, Shi, Wang · Optics Express (Editor's Pick) · `10.1364/OE.498226`. Solo relevante para objetivos no estáticos.
- **FPM Reconstruction Based on Residual Hybrid Attention Network** — Li, Hao, Wang, Wang, Wang, Wang, Wang · Sensors · `10.3390/s23167301`.
- 🔧 **Physics-Inspired DL Framework for FPM Under Low Overlap Conditions** — Bouchama et al. · Sensors · `10.3390/s23156829`. *Aplicable:* revisar el espaciado de LEDs — si el solapamiento entre iluminaciones vecinas es bajo por geometría del array, esto podría evitar rediseñar el hardware.

## 2024

- **Spatially-Coded Fourier Ptychography (scFP)** — Wang, Yang, Lee, ... Zheng · Advanced Optical Materials · `10.1002/adom.202303028`. Requiere modificación física del sensor.
- **Fast FP Quantitative Phase Microscopy (FQP-FPM)** — Wu, Luo, Liu, Zhang, Zhen, Yan, Luo, Wu · Biomedical Optics Express · `10.1364/BOE.505267`. 10 imágenes crudas en vez de cientos.
- **Multi-Scale Fractal FPM** — Bianco, Miccio, Pirone, Cavalletti, Behal, Memmolo, Sardo, Ferraro · Scientific Reports · `10.1038/s41598-024-52184-3`. Paper de aplicación (diatomeas).

## 2025 – 2026

- 🔧 **Perturbative FPM for Fast Quantitative Phase Imaging** — Zach, Shen, Cao, Unser, Waller, Dong · Optics Express (2025) · `10.1364/OE.560811`. *Aplicable:* del mismo grupo (Waller) que Wirtinger flow — buen candidato para comparar convergencia/velocidad directamente.
- **Uncertainty-Aware Fourier Ptychography** — Chen, Wu, Tan, Cao, Wang, Lam · Light: Science & Applications (2025) · `10.1038/s41377-025-01915-w`. Ver prioridad 6 arriba.
- **FPM Aided with Transport of Intensity Equation** — Rogalski, Martinez-Carranza, Górski, ... Zuo, Trusiak · Photonics Research (2025) · `10.1364/PRJ.569444`.
- **Inverse Synthetic Aperture Fourier Ptychography** *(publicado 2026)* — Chan, Pellizzari, Metzler · Optics Express · `10.1364/OE.571892`. Pensado para sensado remoto, poco relevante para microscopio de banco.
- **Video-Rate Gigapixel Ptychography via Space-Time Neural Field Representations** *(publicado 2026)* — Wang, Zhao, Hong, ... Zheng · Nature Communications · `10.1038/s41467-026-75092-8`. El techo actual de la rama "reconstrucción vía redes neuronales implícitas".
- **A Residual-Subspace Constraint Framework for FPM** *(preprint 2026)* — Wang, Xie, Cai, Wei, Chen · Optica Open · `10.1364/opticaopen.32346429.v2`.

---

*Compilado a partir de `papers/*.md` en este repo, con los huecos de código identificados contra `ptyco-full-simulator/common.py`. Los DOI enlazan a la página del editor.*
