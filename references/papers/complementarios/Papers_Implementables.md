# Papers Implementables (Algorítmicos / Deep Learning)

### 2. Self-calibrating Fourier ptychographic microscopy using automatic differentiation
- **Authors:** Ruilin You, Rongguang Liang
- **Year:** 2025 | **Source:** CrossRef | **Citations:** 12
- **URL:** https://doi.org/10.1364/ol.542293
- **Abstract:** Fourier ptychographic microscopy (FPM) can provide high-throughput imaging by computationally combining low-resolution images at different spatial frequencies within the Fourier domain...
- **Por qué es implementable:** Se puede programar un algoritmo de auto-diferenciación (como en PyTorch/TensorFlow) para optimizar los parámetros del sistema y reconstruir la imagen sin información de calibración previa.

### 4. Whole-field, high-resolution Fourier ptychography with neural pupil engineering
- **Authors:** Shuhe Zhang, Liangcai Cao
- **Year:** 2025 | **Source:** CrossRef | **Citations:** 9
- **URL:** https://doi.org/10.1364/optica.575065
- **Abstract:** Fourier ptychographic microscopy (FPM) is a computational imaging technique that achieves high-resolution complex amplitude reconstruction across a large field of view...
- **Por qué es implementable:** Se puede implementar una red neuronal implícita para modelar y corregir de forma continua la función de pupila en los bordes de la imagen para reconstrucciones fuera del eje.

### 6. Latent-wavefront Fourier ptychography for stained tissue microscopy
- **Authors:** Shuhe Zhang, Jiayun Li, Liangcai Cao
- **Year:** 2025 | **Source:** CrossRef | **Citations:** 1
- **URL:** https://doi.org/10.1364/prj.544723
- **Abstract:** Fourier ptychographic microscopy (FPM) is a promising technique for achieving high-resolution and large field-of-view imaging...
- **Por qué es implementable:** Implementación de un algoritmo basado en maximización de expectativas variacional (VEM) para resolver el problema inverso y optimizar el frente de onda latente computacionalmente.

### 8. Deep Learning-Driven Polarization-Sensitive Fourier Ptychographic Microscopy (DL-PFPM)
- **Authors:** T. Phan, Christopher Raub, Shahid Aslam, G. Nehmetallah
- **Year:** 2025 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1364/dh.2025.dm4c.2
- **Abstract:** We developed a deep learning-based polarization Fourier ptychographic microscopy (DL-PFPM) reconstruction approach...
- **Por qué es implementable:** Se puede entrenar una red neuronal profunda para reconstruir directamente información de polarización y retardo a partir del campo complejo recuperado.

### 11. Fourier Ptychography with Unknown Sample Motion
- **Authors:** Matthew A. Chan, Casey J. Pellizzari, Christopher A. Metzler
- **Year:** 2025 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1364/cosi.2025.ctu2b.4
- **Abstract:** We introduce Fourier Ptychography with Unknown Sample Motion, a novel method that generates measurement diversity through target motion...
- **Por qué es implementable:** Programación de un método de recuperación de fase basado en aprendizaje automático que no requiere calibración y corrige el movimiento computacionalmente.

### 12. Space-time Fourier ptychography for in vivo quantitative phase imaging
- **Authors:** Ming Sun, Kunyi Wang, Yogeshwar Nath Mishra, Simeng Qiu, Wolfgang Heidrich
- **Year:** 2024 | **Source:** CrossRef | **Citations:** 17
- **URL:** https://doi.org/10.1364/optica.531646
- **Abstract:** Quantitative phase imaging of living biological specimens is challenging due to their continuous movement and complex behavior...
- **Por qué es implementable:** Desarrollo de un algoritmo de optimización espacio-temporal utilizando priors de movimiento y compressive sensing para procesar secuencias de video.

### 13. Transformed pupil-function misalignment calibration strategy for Fourier ptychographic microscopy
- **Authors:** Hongnian Liu, Tingfa Xu, Yiwen Chen, Yuncheng Wang, Jianan Li
- **Year:** 2024 | **Source:** CrossRef | **Citations:** 9
- **URL:** https://doi.org/10.1364/oe.515196
- **Abstract:** Fourier ptychographic microscopy (FPM) is an enabling quantitative phase imaging technique with both high-resolution (HR) and wide field-of-view (FOV)...
- **Por qué es implementable:** Codificación de una estrategia algorítmica para detectar fronteras en el dominio de Fourier y corregir el error de alineación de las posiciones LED en el software.

### 18. Fourier ptychographic microscopy and its applications in whole slide imaging system via feature-domain computational framework
- **Authors:** An Pan, Shuhe Zhang, Aiye Wang
- **Year:** 2024 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1364/fio.2024.fm5b.5
- **Abstract:** A feature-domain framework is reported for Fourier ptychographic microscopy, termed FD-FPM, to realize full-FOV reconstruction...
- **Por qué es implementable:** Programación de un framework computacional operando en el dominio de características que acelera la reconstrucción del campo completo.

### 19. Sparse Color Fourier Ptychographic Microscopy With Implicit Neural Representations
- **Authors:** Matthew A. Chan, Haowen Zhou, Brandon Y. Feng, Christopher A. Metzler
- **Year:** 2024 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1364/cosi.2024.cw3b.5
- **Abstract:** We apply implicit neural representations—which naturally capture spectral regularity—to reconstruct color Fourier ptychographic microscopy images...
- **Por qué es implementable:** Implementación de redes neuronales implícitas (INR) para hacer renderizado de color a partir de mediciones dispersas espectralmente.

### 20. Fourier Ptychographic Microscopy Reconstruction Method Based on Residual Local Mixture Network
- **Authors:** Yan Wang, Yongshan Wang, Jie Li, Xiaoli Wang
- **Year:** 2024 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.3390/s24134099
- **Abstract:** Fourier Ptychographic Microscopy (FPM) is a microscopy imaging technique based on optical principles...
- **Por qué es implementable:** Diseño de una arquitectura de red residual con mecanismos de atención espacial y difusión Gaussiana para reconstruir imágenes FPM mitigando el ruido.

### 21. Hybrid Illumination Angle Calibration for Fourier Ptychography Microscope
- **Authors:** Chen Liang, Fan Feng, Pingyong Xu, Heng Mao
- **Year:** 2024 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1364/3d.2024.jm4a.14
- **Abstract:** We proposed a hybrid calibration method for quantitative correction of illumination angle misalignments...
- **Por qué es implementable:** Codificación de una rutina de calibración híbrida algorítmica para corregir dinámicamente desviaciones de ángulo de iluminación.

### 22. Dynamic Fourier Ptychography via Space-Time Optimization
- **Authors:** Ming Sun, Kunyi Wang, Yogeshwar Nath Mishra, Simeng Qiu, Wolfgang Heidrich
- **Year:** 2024 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1364/cosi.2024.cw3b.2
- **Abstract:** We introduce a dynamic Fourier ptychography (FP) technique via a spacetime framework...
- **Por qué es implementable:** Creación de un script de optimización conjunto que estima el estado del objeto y los campos de deformación a lo largo del tiempo.

### 24. Fourier ptychographic microscopy image enhancement with bi-modal deep learning
- **Authors:** Lyes Bouchama, Bernadette Dorizzi, Marc Thellier, Jacques Klossa, Yaneck Gottesman
- **Year:** 2023 | **Source:** CrossRef | **Citations:** 10
- **URL:** https://doi.org/10.1364/boe.489776
- **Abstract:** Digital pathology based on a whole slide imaging system is about to permit a major breakthrough...
- **Por qué es implementable:** Entrenamiento de una arquitectura tipo U-Net bimodal (procesando amplitud y fase simultáneamente) para mejorar el contraste celular computacionalmente.

### 25. Undersampled Fourier ptychography for reflective-based long range imaging
- **Authors:** Zhiming Tian, Ming Zhao, Sen Wang, Ning Zou, Jian Li, Junchao Feng
- **Year:** 2023 | **Source:** CrossRef | **Citations:** 4
- **URL:** https://doi.org/10.1364/oe.485563
- **Abstract:** Fourier ptychography (FP) can be a promising technique for long-range and high-resolution imaging...
- **Por qué es implementable:** Modificación del algoritmo clásico introduciendo una nueva función de pérdida y descenso de gradiente adaptado para muestras submuestreadas.

### 27. Contrast‐enhanced, single‐shot LED array microscopy based on Fourier ptychographic algorithm and deep learning
- **Authors:** Shengping Wang, Zibang Zhang, Manhong Yao, Zihao Deng, Junzheng Peng, Jingang Zhong
- **Year:** 2023 | **Source:** CrossRef | **Citations:** 2
- **URL:** https://doi.org/10.1111/jmi.13218
- **Abstract:** LED array microscopes have the advantages of miniaturisation and low cost...
- **Por qué es implementable:** Uso de Redes Neuronales Convolucionales (CNN) preentrenadas para generar imágenes de baja resolución simulando iluminación angulada a partir de una única toma real.

### 28. Deep Learning-Based Polarization Capable Fourier Ptychographic Microscopy (DL-PFPM)
- **Authors:** T. Phan, Brad Bazow, Shahid Aslam, G. Nehmetallah
- **Year:** 2023 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1364/3d.2023.jw2a.8
- **Abstract:** We developed a deep learning-based polarization Fourier ptychographic microscopy (DL-PFPM)...
- **Por qué es implementable:** Modelado de una red neuronal para inferir retardo de birrefringencia cuantitativa y mapas de orientación directamente en software.

### 30. Sparsely sampled Fourier ptychography in diffuse reflection
- **Authors:** Sheng Li
- **Year:** 2023 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1088/1742-6596/2478/6/062013
- **Abstract:** Fourier ptychography microscopy combines the idea of aperture synthesis...
- **Por qué es implementable:** Implementación de un esquema matemático de muestreo disperso (sparse sampling) que reduce el número de imágenes procesadas sin degradar la resolución final.

### 36. Addressing phase-curvature in Fourier ptychography
- **Authors:** Tomas Aidukas, Lars Loetgering, Andrew R. Harvey
- **Year:** 2022 | **Source:** CrossRef | **Citations:** 12
- **URL:** https://doi.org/10.1364/oe.458657
- **Abstract:** In Fourier ptychography, multiple low resolution images are captured and subsequently combined computationally...
- **Por qué es implementable:** Reprogramación del "forward model" de ptychografía en código, incorporando la curvatura de fase de ondas no planas para una reconstrucción más realista.

### 39. Angularly resolved polarization microscopy for birefringent materials with Fourier ptychography
- **Authors:** Arthur Baroni, Lyes Bouchama, Bernadette Dorizzi, Yaneck Gottesman
- **Year:** 2022 | **Source:** CrossRef | **Citations:** 7
- **URL:** https://doi.org/10.1364/oe.469377
- **Abstract:** Polarization light microscopy is a very popular approach for structural imaging in optics...
- **Por qué es implementable:** Uso de una red neuronal profunda no supervisada y diferenciación automática para resolver el problema inverso recuperando propiedades de polarización.

### 45. Fourier Ptychographic Microscopy Reconstruction Method Based on Residual Transfer Networks
- **Authors:** Xiaoli Wang, Yan Piao, Jie Li, Jinyang Yu
- **Year:** 2022 | **Source:** CrossRef | **Citations:** 1
- **URL:** https://doi.org/10.1088/1742-6596/2400/1/012015
- **Abstract:** Fourier ptychographic microscopy reconstruction mostly adopts the traditional alternating iterative phase recovery...
- **Por qué es implementable:** Creación de una red de transferencia residual (basada en ResNet152) para realizar recuperación de fase end-to-end puramente desde IA.

### 46. Physics-Informed Variational Autoencoder for Undersampled Fourier Ptychography
- **Authors:** Yolanda Hu, Andrew Olsen, Jan Funke, Srinivas Turaga, Vidya Ganapati
- **Year:** 2022 | **Source:** CrossRef | **Citations:** 1
- **URL:** https://doi.org/10.1364/cosi.2022.cf1d.8
- **Abstract:** This paper presents an unsupervised deep learning method for complex object reconstruction...
- **Por qué es implementable:** Diseño y entrenamiento de un Autoencoder Variacional Informado por la Física (Physics-Informed VAE) sin necesidad de ground-truth.

### 49. Fourier ptychography multi-parameter neural network with composite physical priori optimization
- **Authors:** Delong Yang, Shaohui Zhang, Chuanjian Zheng, Guocheng Zhou, Lei Cao, Yao Hu, Qun Hao
- **Year:** 2022 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1364/cleopr.2022.ctha13b_05
- **Abstract:** Fourier ptychography microscopy(FPM) is a recently developed computational imaging approach...
- **Por qué es implementable:** Implementación de una red neuronal paramétrica donde las capas simulan el modelo físico real para optimizar ruido, enfoque y pupila simultáneamente.

### 50. Fourier ptychography algorithm based on scaled Fourier transform
- **Authors:** Mojde Hasanzade, Nazabat Hussain, Dag W. Breiby, Muhammad N. Akram
- **Year:** 2021 | **Source:** CrossRef | **Citations:** 3
- **URL:** https://doi.org/10.1049/ell2.12081
- **Abstract:** This letter discusses an alternative Fourier ptychography algorithm based on the scaled fast Fourier transform propagation...
- **Por qué es implementable:** Modificación matemática en el script de propagación óptica utilizando una Transformada de Fourier Rápida Escalada para mayor eficiencia computacional.
