# Papers Relevantes de 2025 en Fourier Ptychographic Microscopy (FPM)

*Nota:* al revisar los metadatos reales de los PDFs (vía Crossref), 3 de los 6 archivos que estaban en esta carpeta resultaron ser publicaciones de **2026**, no 2025 (probablemente guardados acá porque el preprint de arXiv es de 2025, aunque la versión final de revista salió en 2026). Los separo en dos secciones para que la clasificación por año quede correcta.

## Publicados en 2025

1. **Perturbative Fourier Ptychographic Microscopy for Fast Quantitative Phase Imaging**
   - *Authors:* Martin Zach, Kuan-Chen Shen, Ruiming Cao, Michael Unser, Laura Waller, Jonathan Dong
   - *Journal:* Optics Express, vol. 33(18), p. 38984 (5 sep 2025)
   - *Summary:* Del laboratorio de Laura Waller. Interpreta la microscopía de contraste de fase diferencial (DPC) como la primera iteración de un algoritmo Gauss-Newton con regularización cuadrática, y lo generaliza a múltiples iteraciones con regularizadores más sofisticados. Combina esto con un patrón de iluminación de campo oscuro anular a medida, superando las limitaciones de resolución de DPC y logrando ventajas simultáneas en velocidad de imagen y resolución.
   - *DOI:* [10.1364/OE.560811](https://doi.org/10.1364/OE.560811)
   - *PDF (ya en la carpeta):* `Perturbative-Fourier-ptychographic-microscopy-for-fast-quantitative-phase-imaging.pdf`

2. **Uncertainty-Aware Fourier Ptychography**
   - *Authors:* Ni Chen, Yang Wu, Chao Tan, Liangcai Cao, Jun Wang, Edmund Y. Lam
   - *Journal:* Light: Science & Applications, vol. 14, art. 236 (7 jul 2025), open access
   - *Summary:* Incorpora cuantificación de incertidumbre al pipeline de reconstrucción FP — en vez de entregar solo una imagen reconstruida, el método estima también la confiabilidad/incertidumbre de cada región reconstruida, relevante para aplicaciones donde la confianza en el resultado importa tanto como el resultado mismo (diagnóstico, control de calidad).
   - *DOI:* [10.1038/s41377-025-01915-w](https://doi.org/10.1038/s41377-025-01915-w)
   - *PDF (ya en la carpeta, renombrado):* `UncertaintyAwareFP_s41377-025-01915-w.pdf` — **antes tenía el nombre `cells-13-00324-v2.pdf`** (el mismo nombre que el review fundacional de 2024 en `papers/foundational_papers.md`), pero el contenido real es este paper de 2025. Lo renombré para evitar confusión con el archivo correcto en `papers/cells-13-00324-v2.pdf`.

3. **Fourier Ptychographic Microscopy Aided with Transport of Intensity Equation for Robust Full Phase Spectrum Reconstruction**
   - *Authors:* Mikołaj Rogalski, Juan Martinez-Carranza, Bartosz Górski, Piotr Arcab, Michał Józwik, Piotr Zdańkowski, Magdalena Sobień, Marzena Stefaniuk, Shun Zhou, Chao Zuo, Maciej Trusiak
   - *Journal:* Photonics Research (24 oct 2025)
   - *Summary:* Combina FPM con la ecuación de transporte de intensidad (TIE) para mejorar la robustez de la reconstrucción del espectro de fase completo. Con la participación de Chao Zuo (grupo SCILab, NJUST), autor recurrente en esta línea de trabajo desde 2016-2018.
   - *DOI:* [10.1364/PRJ.569444](https://doi.org/10.1364/PRJ.569444)
   - *PDF (ya en la carpeta):* `2505.24322v1.pdf`

## Publicados en 2026 (preprints de 2025, guardados en esta carpeta)

4. **Inverse Synthetic Aperture Fourier Ptychography**
   - *Authors:* Matthew A. Chan, Casey J. Pellizzari, Christopher A. Metzler
   - *Journal:* Optics Express (13 feb 2026); preprint arXiv:2507.03733 (jul 2025)
   - *Summary:* Invierte la lógica habitual de FP: en vez de sintetizar una apertura amplia a partir de muchas iluminaciones angulares con apertura de detección fija, exploran la síntesis de apertura mediante variación del lado de detección/sensado (ISAR-like), relevante para escenarios de sensado remoto/largo alcance donde controlar la iluminación no es viable pero sí el sistema de detección.
   - *DOI:* [10.1364/OE.571892](https://doi.org/10.1364/OE.571892)
   - *PDF (ya en la carpeta):* `2507.03733v2.pdf`

5. **Video-Rate Gigapixel Ptychography via Space-Time Neural Field Representations**
   - *Authors:* Ruihai Wang, Qianhao Zhao, Zhixuan Hong, Qiong Ma, Tianbo Wang, Lingzhi Jiang, Liming Yang, Shaowei Jiang, Feifei Huang, Thanh D. Nguyen, Leslie Shor, Daniel Gage, Mary Lipton, Christopher Anderton, Arunima Bhattacharjee, David Brady, Guoan Zheng
   - *Journal:* Nature Communications (30 jun 2026); preprint arXiv:2511.06126 (nov 2025)
   - *Summary:* Con la participación de Guoan Zheng (autor del paper fundacional de 2013). Combina ptychography con representaciones de campo neuronal espacio-temporales (siguiendo la línea de FPM-INR de 2023) para lograr reconstrucción de video gigapíxel a velocidad de video, empujando FPM hacia la imagen dinámica de muestras vivas a gran escala.
   - *DOI:* [10.1038/s41467-026-75092-8](https://doi.org/10.1038/s41467-026-75092-8)
   - *PDF (ya en la carpeta):* `2511.06126v1.pdf`

6. **A Residual-Subspace Constraint Framework for Fourier Ptychographic Microscopy**
   - *Authors:* Suipeng Wang, Siyi Xie, Changtao Cai, Zhun Wei, Rui Chen
   - *Preprint:* Optica Open (26 may 2026), aún sin versión de revista confirmada
   - *Summary:* Propone una restricción de subespacio residual para el problema inverso de reconstrucción FPM, otra variante algorítmica dentro de la línea de regularización avanzada de FP (en la tradición de sparse representation / TV / group-based sparse de años previos).
   - *DOI:* [10.1364/opticaopen.32346429.v2](https://doi.org/10.1364/opticaopen.32346429.v2)
   - *PDF (ya en la carpeta):* `2605.22197v1.pdf`
