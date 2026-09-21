# Nuevos Papers Encontrados (Búsqueda Exhaustiva)

Se encontraron 50 papers adicionales relevantes, omitiendo los 37 que ya existían en los resúmenes anteriores.

### 1. Metalens-Based Imaging System for Fourier Ptychographic Microscopy
- **Authors:** Cheng Hung Chu, Hao-Pin Chiu, Sunil Vyas, Yuan Luo
- **Year:** 2026 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1364/dh.2026.th2a.2
- **Abstract:** We present a compact metasurface-based Fourier ptychographic microscope integrating metalens optics and programmable illumination to achieve miniaturized, wide-field quantitative phase imaging with nearly twofold resolution improvement and demonstrated performance on biological samples.

### 2. Self-calibrating Fourier ptychographic microscopy using automatic differentiation
- **Authors:** Ruilin You, Rongguang Liang
- **Year:** 2025 | **Source:** CrossRef | **Citations:** 12
- **URL:** https://doi.org/10.1364/ol.542293
- **Abstract:** Fourier ptychographic microscopy (FPM) can provide high-throughput imaging by computationally combining low-resolution images at different spatial frequencies within the Fourier domain. The core algorithm for FPM reconstruction draws upon phase retrieval techniques, including methods such as the ptychographic iterative engine (PIE), regularized PIE (rPIE), and embedded pupil function FPM (EPRY-FPM). The calibration of the physical setup plays a crucial role in the quality of the reconstructed high space–bandwidth product (SPB) image. Despite advances, many methods, incorporating either machine learning or calibration algorithm, face challenges. These include the need for extensive parameter tuning and extra optical system information, hindering their practical use. To address these limitations, we introduce a novel, to the best of our knowledge, self-calibrating FPM reconstruction approach that utilizes automatic differentiation. This method diverges from traditional iterative phase and amplitude updates, opting instead to simultaneously recover a complex 2D image and refine the optical system’s physical parameters. Our approach matches the effectiveness of existing recovery techniques while significantly reducing the calibration burden. In this report, we will demonstrate our method is capable of self-calibrating without needing extra system information. We validate our algorithm’s performance through numerical simulations and then show its practicality by reconstructing a full field of view of cervical cell slides using ultraviolet Fourier ptychographic microscopy (UV-FPM).

### 3. Single-shot Fourier ptychography using polarization-encoded illumination
- **Authors:** Hansol Yoon, Hyesuk Chae, Kyung Chul Lee, Kyungwon Lee, Seung Ah Lee
- **Year:** 2025 | **Source:** CrossRef | **Citations:** 10
- **URL:** https://doi.org/10.1063/5.0248101
- **Abstract:** Fourier ptychography (FP) is widely adopted for label-free, high-resolution quantitative phase imaging (QPI) of biological samples. However, its imaging speed is limited by the need for multiple acquisitions. In this work, we propose a single-shot FP technique that uses linear polarizers to encode multiple illumination wavevectors and a polarization camera to capture multiple sets of information simultaneously. A multiplexed FP algorithm, utilizing both the bright-field and dark-field information, reconstructs a high-resolution quantitative phase image from the single-shot intensity image. Verified with resolution targets and a histological sample, our method achieved a resolution improvement of 2.5 times the diffraction limit of the objective lens and provided QPI over a large field-of-view. Additionally, we demonstrated high-speed FP at 75 frames per second, limited only by the sensor's readout speed, enabling QPI of fast-moving microorganisms.

### 4. Whole-field, high-resolution Fourier ptychography with neural pupil engineering
- **Authors:** Shuhe Zhang, Liangcai Cao
- **Year:** 2025 | **Source:** CrossRef | **Citations:** 9
- **URL:** https://doi.org/10.1364/optica.575065
- **Abstract:**                      Fourier ptychographic microscopy (FPM) is a computational imaging technique that achieves high-resolution complex amplitude reconstruction across a large field of view. However, conventional FPM is fundamentally limited to regions near the optical axis due to violations of the shift-invariance assumption in off-axis areas, resulting in challenging edge-of-field-of-view reconstructions. We propose neural pupil engineering FPM, termed NePE-FPM, a physical model that dynamically shifts the pupil function position during reconstruction instead of fixing the pupil function in the center of the pupil plane. NePE-FPM engineers the pupil function using an implicit neural representation with multi-resolution hash encoding, enabling continuous, smooth shifting of the pupil function without introducing additional physical parameters. By optimizing a feature-domain loss function, NePE-FPM adaptively filters Fourier-space information from low-resolution measurements, achieving accurate off-axis reconstruction without modeling off-axis propagation. Experimental results demonstrate isotropic resolution of 1149 lp/mm across an 11mm                     2                     FOV using a 4×/0.1NA objective. The NePE-FPM bridges the gap between theoretical FPM capabilities and practical whole-slide imaging demands.                   

### 5. Fourier ptychography microscopy with programmable beam illumination
- **Authors:** Suyash Mehta, Biswajit Pathak
- **Year:** 2025 | **Source:** CrossRef | **Citations:** 4
- **URL:** https://doi.org/10.1364/oe.544117
- **Abstract:** Fourier ptychographic microscopy (FPM) is a computational imaging technique that combines multiple low-resolution images captured under varying illumination angles to achieve high-resolution, wide-field imaging. In the present work, we develop an advanced FPM system to enhance its flexibility by illuminating the sample with a sequence of programmable beams. Such programmable beams are generated by employing computer-generated holography technique, realized with a spatial light modulator to create re-configurable binary grating patterns, that enable precise and dynamic control over the illumination pattern. Furthermore, the programmability of pattern generation facilitates intensity uniformization, realization of different imaging modalities, and compensation of aberrations, of the illumination beams directly, thereby, enhancing the imaging resolution, accuracy, and robustness of the system. Proof-of-concept simulation and experimental results are provided to demonstrate the feasibility and effectiveness of the proposed programmable-based beam illumination FPM system.

### 6. Latent-wavefront Fourier ptychography for stained tissue microscopy
- **Authors:** Shuhe Zhang, Jiayun Li, Liangcai Cao
- **Year:** 2025 | **Source:** CrossRef | **Citations:** 1
- **URL:** https://doi.org/10.1364/prj.544723
- **Abstract:**                      Fourier ptychographic microscopy (FPM) is a promising technique for achieving high-resolution and large field-of-view imaging, which is particularly suitable for pathological applications, such as imaging hematoxylin and eosin (H&amp;E) stained tissues with high space-bandwidth and reduced artifacts. However, current FPM implementations require either precise system calibration and high-quality raw data, or significant computational loads due to iterative algorithms, which limits the practicality of FPM in routine pathological examinations. In this work, latent wavefront denoting the unobservable exiting wave at the surface of the sensor is introduced. A latent wavefront physical model optimized with variational expectation maximization (VEM) is proposed to tackle the inverse problem of FPM. The VEM-FPM alternates between solving a non-convex optimization problem as the main task for the latent wavefront in the spatial domain and merging together their Fourier spectrum in the Fourier plane as an intermediate product by solving a convex closed-formed Fourier space optimization. The VEM-FPM approach enables a stitching-free, full-field reconstruction for Fourier ptychography over a 5.3                       mm                     ×5.3                       mm                     field of view, using a 2.5× objective with a numerical aperture (NA) of 0.08. The synthetic aperture achieves a resolution equivalent to 0.53 NA at 532 nm wavelength. The execution speed of VEM-FPM is twice as fast as that of state-of-the-art feature-domain methods while maintaining comparable reconstruction quality.                   

### 7. High-Speed Fourier Ptychographic Microscopy System for Live Microorganisms Imaging
- **Authors:** Kaizhang Kang, Ming Sun, Yogeshwar Nath Mishra, Wolfgang Heidrich
- **Year:** 2025 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1364/cosi.2025.jm4b.6
- **Abstract:** We present a high-speed Fourier ptychographic microscopy system with a custom LED module that is 535 times brighter than an off-the-shelf board, achieving 150 fps live microorganisms imaging and reducing motion blur.

### 8. Deep Learning-Driven Polarization-Sensitive Fourier Ptychographic Microscopy (DL-PFPM)
- **Authors:** T. Phan, Christopher Raub, Shahid Aslam, G. Nehmetallah
- **Year:** 2025 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1364/dh.2025.dm4c.2
- **Abstract:** We developed a deep learning-based polarization Fourier ptychographic microscopy (DL-PFPM) reconstruction approach that enables simultaneous acquisition of wide field-of-view and high-resolution quantitative birefringence retardance and orientation information of specimen from just a single recovered complex field image.

### 9. High‐Resolution Oil‐Free Imaging of Chromosomes Using Fourier Ptychographic Microscopy
- **Authors:** Changliang Yu, Yuguo Tang
- **Year:** 2025 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1002/jbio.202400534
- **Abstract:** ABSTRACTIn conventional microscopic imaging of chromosomes, the use of high numerical aperture (NA) oil‐immersion objectives is essential. However, the use of oil‐immersion objectives poses a significant challenge to automated imaging systems because it increases the risk of sample contamination and instrumental damage. The shallow depth of field (DOF) of oil‐immersion objectives also demands more sophisticated mechanical focusing. Here, we introduce a chromosome oil‐free microscopic imaging system based on Fourier Ptychographic Microscopy (FPM) technology. The system employs a 100×, 0.8 NA dry objective to achieve a half‐pitch resolution of 194 nm at an incident wavelength of 524 nm. The reconstructed images of chromosomes surpassed the conventional imaging with a 100×, 1.25 NA oil‐immersion objective. We also utilized digital refocusing methods to extend the effective DOF to ±2.4 μm. This study preliminarily validates the possibility of developing a new generation of chromosome scanners without using an oil‐immersion objective.

### 10. Fourier Holo-Ptychographic Microscopy
- **Authors:** Zhuoshi Li, Yefeng Shu, Linpeng Lu, Jiasong Sun, Qian Shen, Peng Gao, Michal Ziemczonok, Maciej Trusiak, Qian Chen, Chao Zuo, Malgorzata Kujawinska
- **Year:** 2025 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1364/cosi.2025.ctu2b.2
- **Abstract:** We present a novel hybrid digital holography-Fourier ptychography approach for high-accuracy, speckle-free synthetic-aperture quantitative phase imaging. The feasibility of FHPM is verified on USAF phase resolution target and complex phantoms mimicking biological samples.

### 11. Fourier Ptychography with Unknown Sample Motion
- **Authors:** Matthew A. Chan, Casey J. Pellizzari, Christopher A. Metzler
- **Year:** 2025 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1364/cosi.2025.ctu2b.4
- **Abstract:** We introduce Fourier Ptychography with Unknown Sample Motion, a novel method that generates measurement diversity through target motion. Furthermore, we incorporate a learning-based approach for calibration-free phase retrieval.

### 12. Space-time Fourier ptychography for in vivo quantitative phase imaging
- **Authors:** Ming Sun, Kunyi Wang, Yogeshwar Nath Mishra, Simeng Qiu, Wolfgang Heidrich
- **Year:** 2024 | **Source:** CrossRef | **Citations:** 17
- **URL:** https://doi.org/10.1364/optica.531646
- **Abstract:** Quantitative phase imaging of living biological specimens is challenging due to their continuous movement and complex behavior. Here, we introduce space-time Fourier ptychography (ST-FP), which combines a fast Fourier ptychography (FP) model based on compressive sensing with space-time motion priors for joint reconstruction of quantitative phase, intensity, and motion fields across consecutive frames. Using the same input data as compressive sensing FP, ST-FP increases the space-bandwidth-time product of the reconstructed complex image sequence while leveraging redundant temporal information to achieve robust reconstruction performance. The efficacy of this approach is demonstrated across various applications, particularly in observing living microorganisms undergoing rapid morphological changes and reconstructing amplitude and phase targets in motion. The improved phase retrieval capability of ST-FP enables digital refocusing, facilitating comprehensive three-dimensional analysis of microorganisms. This advancement paves the way for enhanced visualization of cellular processes, developmental biology studies, and investigations into life mechanics at the microscopic level.

### 13. Transformed pupil-function misalignment calibration strategy for Fourier ptychographic microscopy
- **Authors:** Hongnian Liu, Tingfa Xu, Yiwen Chen, Yuncheng Wang, Jianan Li
- **Year:** 2024 | **Source:** CrossRef | **Citations:** 9
- **URL:** https://doi.org/10.1364/oe.515196
- **Abstract:** Fourier ptychographic microscopy (FPM) is an enabling quantitative phase imaging technique with both high-resolution (HR) and wide field-of-view (FOV), which can surpass the diffraction limit of the objective lens by employing an LED array to provide angular-varying illumination. The precise illumination angles are critical to ensure exact reconstruction, while it’s difficult to separate actual positional parameters in conventional algorithmic self-calibration approaches due to the mixing of multiple systematic error sources. In this paper, we report a pupil-function-based strategy for independently calibrating the position of LED array. We first deduce the relationship between positional deviation and pupil function in the Fourier domain through a common iterative route. Then, we propose a judgment criterion to determine the misalignment situations, which is based on the arrangement of LED array in the spatial domain. By combining the mapping of complex domains, we can accurately solve the spatial positional parameters concerning the LED array through a boundary-finding scheme. Relevant simulations and experiments demonstrate the proposed method is accessible to precisely correct the positional misalignment of LED array. The approach based on the pupil function is expected to provide valuable insights for precise position correction in the field of microscopy.

### 14. Simultaneous Multifocal Plane Fourier Ptychographic Microscopy Utilizing a Standard RGB Camera
- **Authors:** Giseok Oh, Hyun Choi
- **Year:** 2024 | **Source:** CrossRef | **Citations:** 2
- **URL:** https://doi.org/10.3390/s24144426
- **Abstract:** Fourier ptychographic microscopy (FPM) is a computational imaging technology that can acquire high-resolution large-area images for applications ranging from biology to microelectronics. In this study, we utilize multifocal plane imaging to enhance the existing FPM technology. Using an RGB light emitting diode (LED) array to illuminate the sample, raw images are captured using a color camera. Then, exploiting the basic optical principle of wavelength-dependent focal length variation, three focal plane images are extracted from the raw image through simple R, G, and B channel separation. Herein, a single aspherical lens with a numerical aperture (NA) of 0.15 was used as the objective lens, and the illumination NA used for FPM image reconstruction was 0.08. Therefore, simultaneous multifocal plane FPM with a synthetic NA of 0.23 was achieved. The multifocal imaging performance of the enhanced FPM system was then evaluated by inspecting a transparent organic light-emitting diode (OLED) sample. The FPM system was able to simultaneously inspect the individual OLED pixels as well as the surface of the encapsulating glass substrate by separating R, G, and B channel images from the raw image, which was taken in one shot.

### 15. High-speed, high-throughput Fourier ptychographic microscopy with hybrid coherent/incoherent illumination
- **Authors:** Yao Fan, Jiasong Sun, Chao Zuo
- **Year:** 2024 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1364/cosi.2024.cw3b.3
- **Abstract:** We propose an efficient synthetic aperture scheme for FPM, termed ESA-FPM, which employs both coherent and incoherent illuminations to maximize the efficiency of data utilization and achieves an imaging bandwidth of  3NA       o       b       j     λ requiring only 7 images.

### 16. Adaptive Optical Quantitative Phase Imaging of Living Cells Based on Fourier Ptychographic Microscopy
- **Authors:** Jiasong Sun, Yefeng Shu, Chao Zuo
- **Year:** 2024 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1364/aopt.2024.ow1f.3
- **Abstract:** In this report, we present an adaptive optical Quantitative Phase Imaging (QPI) method based on annular illumination Fourier Ptychographic Microscopy (FPM). Using only six low-resolution images captured at six different illumination angles that match the objective, we're able to recover high-resolution quantitative phase images and characterize the aberrations in real time.

### 17. Ultra-Violet Reflective Fourier Ptychographic Microscopy Using a Parabolic Mirror
- **Authors:** Van Huan Pham, Byong Hyuk Chon, Hee Kyung Ahn
- **Year:** 2024 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1364/3d.2024.jth2a.14
- **Abstract:** Here, we propose a reflective FPM using ultra-violet LEDs. To show the resolution improvement, a reflective FPM using 365 nm ultra-violet LEDs is demonstrated by resolving 173 nm half-pitch patterns in a USAF 1951 target.

### 18. Fourier ptychographic microscopy and its applications in whole slide imaging system via feature-domain computational framework
- **Authors:** An Pan, Shuhe Zhang, Aiye Wang
- **Year:** 2024 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1364/fio.2024.fm5b.5
- **Abstract:** A feature-domain framework is reported for Fourier ptychographic microscopy, termed FD-FPM, to realize full-FOV reconstruction and reduce the accuracy requirement, achieving data acquisition of 4s/slide at 336nm spatial resolution with the FOV of 4.7mm diameter.

### 19. Sparse Color Fourier Ptychographic Microscopy With Implicit Neural Representations
- **Authors:** Matthew A. Chan, Haowen Zhou, Brandon Y. Feng, Christopher A. Metzler
- **Year:** 2024 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1364/cosi.2024.cw3b.5
- **Abstract:** We apply implicit neural representations—which naturally capture spectral regularity—to reconstruct color Fourier ptychographic microscopy images from spectrally-sparse measurements. We conduct experiments on real-world specimens and demonstrate reconstruction quality comparable with fully sampled methods.

### 20. Fourier Ptychographic Microscopy Reconstruction Method Based on Residual Local Mixture Network
- **Authors:** Yan Wang, Yongshan Wang, Jie Li, Xiaoli Wang
- **Year:** 2024 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.3390/s24134099
- **Abstract:** Fourier Ptychographic Microscopy (FPM) is a microscopy imaging technique based on optical principles. It employs Fourier optics to separate and combine different optical information from a sample. However, noise introduced during the imaging process often results in poor resolution of the reconstructed image. This article has designed an approach based on a residual local mixture network to improve the quality of Fourier ptychographic reconstruction images. By incorporating channel attention and spatial attention into the FPM reconstruction process, the network enhances the efficiency of the network reconstruction and reduces the reconstruction time. Additionally, the introduction of the Gaussian diffusion model further reduces coherent artifacts and improves image reconstruction quality. Comparative experimental results indicate that this network achieves better reconstruction quality, and outperforming existing methods in both subjective observation and objective quantitative evaluation.

### 21. Hybrid Illumination Angle Calibration for Fourier Ptychography Microscope
- **Authors:** Chen Liang, Fan Feng, Pingyong Xu, Heng Mao
- **Year:** 2024 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1364/3d.2024.jm4a.14
- **Abstract:** We proposed a hybrid calibration method for quantitative correction of illumination angle misalignments in Fourier ptychography microscope. This method combines system parameter pre-calibration with online sample-include calibration to ensure high-quality results.

### 22. Dynamic Fourier Ptychography via Space-Time Optimization
- **Authors:** Ming Sun, Kunyi Wang, Yogeshwar Nath Mishra, Simeng Qiu, Wolfgang Heidrich
- **Year:** 2024 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1364/cosi.2024.cw3b.2
- **Abstract:** We introduce a dynamic Fourier ptychography (FP) technique via a spacetime framework, jointly recovering object states and deformation fields for detailed observation of rapid, complex behaviors in living cells.

### 23. Beyond conventional microscopy: Observing kidney tissues by means of fourier ptychography
- **Authors:** Marika Valentino, Vittorio Bianco, Lisa Miccio, Pasquale Memmolo, Valentina Brancato, Paolo Libretti, Marcello Gambacorta, Marco Salvatore, Pietro Ferraro
- **Year:** 2023 | **Source:** CrossRef | **Citations:** 22
- **URL:** https://doi.org/10.3389/fphys.2023.1120099
- **Abstract:** Kidney microscopy is a mainstay in studying the morphological structure, physiology and pathology of kidney tissues, as histology provides important results for a reliable diagnosis. A microscopy modality providing at same time high-resolution images and a wide field of view could be very useful for analyzing the whole architecture and the functioning of the renal tissue. Recently, Fourier Ptychography (FP) has been proofed to yield images of biology samples such as tissues and in vitro cells while providing high resolution and large field of view, thus making it a unique and attractive opportunity for histopathology. Moreover, FP offers tissue imaging with high contrast assuring visualization of small desirable features, although with a stain-free mode that avoids any chemical process in histopathology. Here we report an experimental measuring campaign for creating the first comprehensive and extensive collection of images of kidney tissues captured by this FP microscope. We show that FP microscopy unlocks a new opportunity for the physicians to observe and judge renal tissue slides through the novel FP quantitative phase-contrast microscopy. Phase-contrast images of kidney tissue are analyzed by comparing them with the corresponding renal images taken under a conventional bright-field microscope both for stained and unstained tissue samples of different thicknesses. In depth discussion on the advantages and limitations of this new stain-free microscopy modality is reported, showing its usefulness over the classical light microscopy and opening a potential route for using FP in clinical practice for histopathology of kidney.

### 24. Fourier ptychographic microscopy image enhancement with bi-modal deep learning
- **Authors:** Lyes Bouchama, Bernadette Dorizzi, Marc Thellier, Jacques Klossa, Yaneck Gottesman
- **Year:** 2023 | **Source:** CrossRef | **Citations:** 10
- **URL:** https://doi.org/10.1364/boe.489776
- **Abstract:**                      Digital pathology based on a whole slide imaging system is about to permit a major breakthrough in automated diagnosis for rapid and highly sensitive disease detection. High-resolution FPM (Fourier ptychographic microscopy) slide scanners delivering rich information on biological samples are becoming available. They allow new effective data exploitation for efficient automated diagnosis. However, when the sample thickness becomes comparable to or greater than the microscope depth of field, we report an observation of undesirable contrast change of sub-cellular compartments in phase images around the optimal focal plane, reducing their usability. In this article, a bi-modal U-Net artificial neural network (i.e., a two channels U-Net fed with intensity and phase images) is trained to reinforce specifically targeted sub-cellular compartments contrast for both intensity and phase images. The procedure used to construct a reference database is detailed. It is obtained by exploiting the FPM reconstruction algorithm to explore images around the optimal focal plane with virtual Z-stacking calculations and selecting those with adequate contrast and focus. By construction and once trained, the U-Net is able to simultaneously reinforce targeted cell compartment visibility and compensate for any focus imprecision. It is efficient over a large field of view at high resolution. The interest of the approach is illustrated considering the use-case of                     Plasmodium falciparum                     detection in blood smear where improvement in the detection sensitivity is demonstrated without degradation of the specificity. Post-reconstruction FPM image processing with such U-Net and its training procedure is general and applicable to demanding biological screening applications.                   

### 25. Undersampled Fourier ptychography for reflective-based long range imaging
- **Authors:** Zhiming Tian, Ming Zhao, Sen Wang, Ning Zou, Jian Li, Junchao Feng
- **Year:** 2023 | **Source:** CrossRef | **Citations:** 4
- **URL:** https://doi.org/10.1364/oe.485563
- **Abstract:** Fourier ptychography (FP) can be a promising technique for long-range and high-resolution imaging. In this work, we explore reconstructions with undersampled data for meter-scale reflective based Fourier ptychographic imaging. To reconstruct with under-sampling captures, we propose a novel cost function for FP phase retrieval and design a new optimization algorithm based on gradient descent. To verify the proposed methods, we perform the high-fidelity reconstruction of the targets with sampling parameter less than one. Compared to the state-of-the-art alternative-projectionbased FP algorithm, the proposed one can achieve the same performance but with much less data.

### 26. Exceeding the limits of algorithmic self-calibrated aberration recovery in Fourier ptychography
- **Authors:** Eric Li, Stuart Sherwin, Gautam Gunjala, Laura Waller
- **Year:** 2023 | **Source:** CrossRef | **Citations:** 3
- **URL:** https://doi.org/10.1364/optcon.475990
- **Abstract:**                      Fourier ptychographic microscopy is a computational imaging technique that provides quantitative phase information and high resolution over a large field-of-view. Although the technique presents numerous advantages over conventional microscopy, model mismatch due to unknown optical aberrations can significantly limit reconstruction quality. A practical way of correcting for aberrations without additional data capture is through algorithmic self-calibration, in which a pupil recovery step is embedded into the reconstruction algorithm. However, software-only aberration correction is limited in accuracy. Here, we evaluate the merits of implementing a simple, dedicated calibration procedure for applications requiring high accuracy. In simulations, we find that for a target sample reconstruction error, we can image without any aberration corrections only up to a maximum aberration magnitude of                     λ                     /40. When we use algorithmic self-calibration, we can tolerate an aberration magnitude up to                     λ                     /10 and with our proposed diffuser calibration technique, this working range is extended further to                     λ                     /3. Hence, one can trade off complexity for accuracy by using a separate calibration process, which is particularly useful for larger aberrations.                   

### 27. Contrast‐enhanced, single‐shot LED array microscopy based on Fourier ptychographic algorithm and deep learning
- **Authors:** Shengping Wang, Zibang Zhang, Manhong Yao, Zihao Deng, Junzheng Peng, Jingang Zhong
- **Year:** 2023 | **Source:** CrossRef | **Citations:** 2
- **URL:** https://doi.org/10.1111/jmi.13218
- **Abstract:** AbstractLED array microscopes have the advantages of miniaturisation and low cost. It has been demonstrated that LED array microscopes outperform Köhler illumination microscopes in some applications. A LED array allows for a large numerical aperture of illumination. The larger numerical aperture of illumination brings the higher spatial resolution, but the lower image contrast as well. Therefore, there is a tradeoff between resolution and contrast for LED array microscopes. The Fourier ptychographic algorithm can overcome this tradeoff by increasing image contrast without sacrificing spatial resolution. However, the Fourier ptychographic algorithm requires acquisition of multiple images, which is time‐consuming and results in live sample imaging challenging. To solve this problem, we develop contrast‐enhanced, single‐shot LED array microscopy based on the Fourier ptychographic algorithm and deep learning. The sample to be imaged is under illumination by all LEDs of the array simultaneously. The image captured is fed to several trained convolutional neural networks to generate the same number of images that are required by the Fourier ptychographic algorithm. We experimentally present that the image contrast of the final reconstruction is remarkably improved in comparison with the image captured. The proposed method can also produce chromatic‐aberration‐free results, even when an objective without aberration correction is used. We believe the method might provide live sample imaging with a low‐cost approach.

### 28. Deep Learning-Based Polarization Capable Fourier Ptychographic Microscopy (DL-PFPM)
- **Authors:** T. Phan, Brad Bazow, Shahid Aslam, G. Nehmetallah
- **Year:** 2023 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1364/3d.2023.jw2a.8
- **Abstract:** We developed a deep learning-based polarization Fourier ptychographic microscopy (DL-PFPM) reconstruction technique that can obtain wide field-of-view and high-resolution quantitative birefringence retardance and orientation information of specimens from just a single recovered complex field image.

### 29. Instantaneous, high-resolution imaging of turbid media using FRAME-based Fourier Ptychography
- **Authors:** Sam Taylor, Vassily Kornienko, Elias Kristensson
- **Year:** 2023 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1364/cleo_at.2023.am4k.6
- **Abstract:** Visualizing fine details in a turbid media is extremely challenging due to multiple light scattering. Here we combine spatial filtering, Fourier Ptychography and image multiplexing to enable instantaneous high-resolution imaging of turbid media.

### 30. Sparsely sampled Fourier ptychography in diffuse reflection
- **Authors:** Sheng Li
- **Year:** 2023 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1088/1742-6596/2478/6/062013
- **Abstract:** Abstract                Fourier ptychography microscopy combines the idea of aperture synthesis, which enables the synthesis of multiple low-resolution images in the frequency domain to achieve large field-of-view and high-resolution imaging results. The Fourier ptychography imaging technique applied to the field of far-field diffuse reflectance imaging needs to consider the impact of diffuse reflectance speckle formed by the object’s rough surface on the imaging results. Therefore, far-field diffuse reflectance Fourier ptychography often requires more than microscopic imaging of low-resolution images to achieve super-resolution. In response, we design a sparse sampling method that can reduce the number of required low-resolution images to one-fourth of the original sampling, and does not affect the imaging resolution. Experimental results show that our method can significantly improve imaging efficiency and achieve super-resolution far-field imaging with fast sampling.

### 31. Synthetic aperture ptychography: coded sensor translation for joint spatial-Fourier bandwidth expansion
- **Authors:** Pengming Song, Shaowei Jiang, Tianbo Wang, Chengfei Guo, Ruihai Wang, Terrance Zhang, Guoan Zheng
- **Year:** 2022 | **Source:** CrossRef | **Citations:** 41
- **URL:** https://doi.org/10.1364/prj.460549
- **Abstract:** Conventional ptychography translates an object through a localized probe beam to widen the field of view in real space. Fourier ptychography translates the object spectrum through a pupil aperture to expand the Fourier bandwidth in reciprocal space. Here we report an imaging modality, termed synthetic aperture ptychography (SAP), to get the best of both techniques. In SAP, we illuminate a stationary object using an extended plane wave and translate a coded image sensor at the far field for data acquisition. The coded layer attached on the sensor modulates the object exit waves and serves as an effective ptychographic probe for phase retrieval. The sensor translation process in SAP synthesizes a large complex-valued wavefront at the intermediate aperture plane. By propagating this wavefront back to the object plane, we can widen the field of view in real space and expand the Fourier bandwidth in reciprocal space simultaneously. We validate the SAP approach with transmission targets and reflection silicon microchips. A 20-mm aperture was synthesized using a 5-mm sensor, achieving a fourfold gain in resolution and 16-fold gain in field of view for object recovery. In addition, the thin sample requirement in ptychography is no longer required in SAP. One can digitally propagate the recovered exit wave to any axial position for post-acquisition refocusing. The SAP scheme offers a solution for far-field sub-diffraction imaging without using lenses. It can be adopted in coherent diffraction imaging setups with radiation sources from visible light, extreme ultraviolet, and X-ray, to electron.

### 32. Implementation of free-space Fourier Ptychography with near maximum system numerical aperture
- **Authors:** Mingshu Liang, Changhuei Yang
- **Year:** 2022 | **Source:** CrossRef | **Citations:** 15
- **URL:** https://doi.org/10.1364/oe.459833
- **Abstract:** Over the past decade, the research field of Fourier Ptychographic Microscopy (FPM) has seen numerous innovative developments that significantly expands its utility. Here, we report a high numerical aperture (NA) FPM implementation that incorporates some of these innovations to achieve a synthetic NA of 1.9 – close to the maximum possible synthetic NA of 2 for a free space FPM system. At this high synthetic NA, we experimentally found that it is vital to homogenize the illumination field in order to achieve the best resolution. Our FPM implementation has a full pitch resolution of 266 nm for 465 nm light, and depth of field of 3.6 µm. In comparison, a standard transmission microscope (incoherent) with close to maximum possible NA of 0.95 has a full pitch resolution of 318 nm for 465 nm light, and depth of field of 0.65 µm. While it is generally assumed that a free-space coherent imaging system and a free-space incoherent imaging system operating at their respective maximum NA should give comparable resolution, we experimentally find that an FPM system significantly outperforms its incoherent standard microscopy counterpart in resolution by a factor of 20%. Coupled with FPM’s substantially longer effective depth of field (5.5 times longer), our work indicates that, in the near-maximum NA operation regime, the FPM has significant resolution and depth of field advantages over incoherent standard microscopy.

### 33. High numerical aperture reflective deep ultraviolet Fourier ptychographic microscopy for nanofeature imaging
- **Authors:** Kwan Seob Park, Yoon Sung Bae, Sang-Soo Choi, Martin Y. Sohn
- **Year:** 2022 | **Source:** CrossRef | **Citations:** 14
- **URL:** https://doi.org/10.1063/5.0102413
- **Abstract:** Pushing the resolution limit to the nanoscale is a critical challenge for applying the reflective Fourier ptychographic microscopy (FPM) to metrologies for characterization of nanoscale features. Characterization of opaque nanoscale samples using reflective FPM requires chiefly a light source with shorter wavelength to obtain nanoscale resolution, as state-of-the-art device sizes have become sub-100 nm or deep sub-wavelength. We report a reflective deep ultraviolet (DUV) FPM featured by an aperture scanning illumination based on the epi-illumination scheme for accommodating a 193 nm excimer laser source and a high numerical aperture (NA) catadioptric objective lens. The illumination system enables robust control of high-NA angular illumination and optimal energy fluence for FPM imaging and prevention of damage to the sample and optical components. The implemented reflective DUV FPM demonstrated image reconstruction of multiline targets with a minimum linewidth of 80 nm with an average contrast six times higher than conventional DUV microscopy.

### 34. High-speed multi-objective Fourier ptychographic microscopy
- **Authors:** Tomas Aidukas, Pavan C. Konda, Andrew R. Harvey
- **Year:** 2022 | **Source:** CrossRef | **Citations:** 14
- **URL:** https://doi.org/10.1364/oe.466075
- **Abstract:** The ability of a microscope to rapidly acquire wide-field, high-resolution images is limited by both the optical performance of the microscope objective and the bandwidth of the detector. The use of multiple detectors can increase electronic-acquisition bandwidth, but the use of multiple parallel objectives is problematic since phase coherence is required across the multiple apertures. We report a new synthetic-aperture microscopy technique based on Fourier ptychography, where both the illumination and image-space numerical apertures are synthesized, using a spherical array of low-power microscope objectives that focus images onto mutually incoherent detectors. Phase coherence across apertures is achieved by capturing diffracted fields during angular illumination and using ptychographic reconstruction to synthesize wide-field, high-resolution, amplitude and phase images. Compared to conventional Fourier ptychography, the use of multiple objectives reduces image acquisition times by increasing the area for sampling the diffracted field. We demonstrate the proposed scaleable architecture with a nine-objective microscope that generates an 89-megapixel, 1.1 µm resolution image nine-times faster than can be achieved with a single-objective Fourier-ptychographic microscope. New calibration procedures and reconstruction algorithms enable the use of low-cost 3D-printed components for longitudinal biological sample imaging. Our technique offers a route to high-speed, gigapixel microscopy, for example, imaging the dynamics of large numbers of cells at scales ranging from sub-micron to centimetre, with an enhanced possibility to capture rare phenomena.

### 35. Cellular analysis using label-free parallel array microscopy with Fourier ptychography
- **Authors:** Devin L. Wakefield, Richard Graham, Kevin Wong, Songli Wang, Christopher Hale, Chung-Chieh Yu
- **Year:** 2022 | **Source:** CrossRef | **Citations:** 13
- **URL:** https://doi.org/10.1364/boe.451128
- **Abstract:** Quantitative phase imaging (QPI) is an ideal method to non-invasively monitor cell populations and provide label-free imaging and analysis. QPI offers enhanced sample characterization and cell counting compared to conventional label-free techniques. We demonstrate this in the current study through a comparison of cell counting data from digital phase contrast (DPC) imaging and from QPI using a system based on Fourier ptychographic microscopy (FPM). Our FPM system offers multi-well, parallel imaging and a QPI-specific cell segmentation method to establish automated and reliable cell counting. Three cell types were studied and FPM showed improvement in the ability to resolve fine details and thin cells, despite limitations of the FPM system incurred by imaging artifacts. Relative to manually counted fluorescence ground-truth, cell counting results after automated segmentation showed improved accuracy with QPI over DPC.

### 36. Addressing phase-curvature in Fourier ptychography
- **Authors:** Tomas Aidukas, Lars Loetgering, Andrew R. Harvey
- **Year:** 2022 | **Source:** CrossRef | **Citations:** 12
- **URL:** https://doi.org/10.1364/oe.458657
- **Abstract:** In Fourier ptychography, multiple low resolution images are captured and subsequently combined computationally into a high-resolution, large-field of view micrograph. A theoretical image-formation model based on the assumption of plane-wave illumination from various directions is commonly used, to stitch together the captured information into a high synthetic aperture. The underlying far-field (Fraunhofer) diffraction assumption connects the source, sample, and pupil planes by Fourier transforms. While computationally simple, this assumption neglects phase-curvature due to non-planar illumination from point sources as well as phase-curvature from finite-conjugate microscopes (e.g., using a single-lens for image-formation). We describe a simple, efficient, and accurate extension of Fourier ptychography by embedding the effect of phase-curvature into the underlying forward model. With the improved forward model proposed here, quantitative phase reconstruction is possible even for wide fields-of-views and without the need of image segmentation. Lastly, the proposed method is computationally efficient, requiring only two multiplications: prior and following the reconstruction.

### 37. Fourier ptychographic dark field x-ray microscopy
- **Authors:** Mads Carlsen, Trygve M Ræder, Can Yildirim, Raquel Rodriguez-Lamas, Carsten Detlefs, Hugh Simons
- **Year:** 2022 | **Source:** CrossRef | **Citations:** 9
- **URL:** https://doi.org/10.1364/oe.447657
- **Abstract:** Dark-field x-ray microscopy (DFXM) is an x-ray imaging technique for mapping three-dimensional (3D) lattice strain and rotation in bulk crystalline materials. At present, these maps of local structural distortions are derived from the raw intensity images using an incoherent analysis framework. In this work, we describe a coherent, Fourier ptychographic approach that requires little change in terms of instrumentation and acquisition strategy, and may be implemented on existing DFXM instruments. We demonstrate the method experimentally and are able to achieve quantitative phase reconstructions of thin film samples and maps of the aberrations in the objective lens. The method holds particular promise for the characterization of crystalline materials containing weak structural contrast.

### 38. Experimental Study on the Exploration of Camera Scanning Reflective Fourier Ptychography Technology for Far-Field Imaging
- **Authors:** Mingyang Yang, Xuewu Fan, Yuming Wang, Hui Zhao
- **Year:** 2022 | **Source:** CrossRef | **Citations:** 8
- **URL:** https://doi.org/10.3390/rs14092264
- **Abstract:** Fourier ptychography imaging is a powerful phase retrieval method that can be used to realize super-resolution. In this study, we establish a mathematical model of long-distance camera scanning based on reflective Fourier ptychography imaging. In order to guarantee the effective recovery of a high-resolution image in the experiment, we analyze the influence of laser coherence in different modes and the surface properties of diverse materials for diffused targets. For the analysis, we choose a single-mode fiber laser as the illumination source and metal materials with high diffused reflectivity as the experimental targets to ensure the validity of the experimental results. Based on the above, we emulate camera scanning with a single camera attached to an X-Y translation stage, and an experimental system with a working distance of 3310 mm is used as an example to image a fifty-cent coin. We also perform speckle analysis for rough targets and calculate the average speckle size using a normalized autocorrelation function in different positions. The method of calculating the average speckle size for everyday objects provides the premise for subsequent research on image quality evaluation; meanwhile, the coherence of the light field and the targets with high reflectivity under this experiment provide an application direction for the further development of the technique, such as computer vision, surveillance and remote sensing.

### 39. Angularly resolved polarization microscopy for birefringent materials with Fourier ptychography
- **Authors:** Arthur Baroni, Lyes Bouchama, Bernadette Dorizzi, Yaneck Gottesman
- **Year:** 2022 | **Source:** CrossRef | **Citations:** 7
- **URL:** https://doi.org/10.1364/oe.469377
- **Abstract:** Polarization light microscopy is a very popular approach for structural imaging in optics. So far these methods mainly probe the sample at a fixed angle of illumination. They are consequently only sensitive to the polarization properties along the microscope optical axis. This paper presents a novel method to resolve angularly the polarization properties of birefringent materials, by retrieving quantitatively the spatial variation of their index ellipsoids. Since this method is based on Fourier ptychography microscopy the latter properties are retrieved with a spatial super-resolution factor. An adequate formalism for the Fourier ptychography forward model is introduced to cope with angularly resolved polarization properties. The inverse problem is solved using an unsupervised deep neural network approach that is proven efficient thanks to its performing regularization properties together with its automatic differentiation. Simulated results are reported showing the feasibility of the methods.

### 40. Hyperspectral microscopy imaging based on Fourier ptychographic microscopy
- **Authors:** Peiwei Zhang, Jufeng Zhao, Binbin Lin, Xiaohui Wu, Guangmang Cui
- **Year:** 2022 | **Source:** CrossRef | **Citations:** 6
- **URL:** https://doi.org/10.1088/2040-8986/ac57b3
- **Abstract:** Abstract                   Hyperspectral resolution, high spatial resolution, and a wide field of view (FOV) are the targets of optical spectral microscopy imaging. However, hyperspectral microscopy imaging technology cannot provide a wide FOV and a high spatial resolution at the same time. Fourier ptychographic microscopy (FPM) is a novel microscopy imaging technique that uses LEDs at varying angles to capture a series of low-spatial-resolution images that are used to recover images that have both high spatial resolution and a wide FOV. Since FPM cannot obtain the spectral resolution of the sample, in this paper, an efficient strategy based on the FPM system is proposed for the reconstruction of hyperspectral images. First, the traditional FPM setup is optimized, with a new experimental setup based on halogen lamp illumination and a narrow band-pass filter to capture a series of low-spatial-resolution images at different wavelengths. Second, a new algorithm, combining hyperspectral resolution imaging using interpolation compensation and a phase retrieval algorithm, is proposed to reconstruct high-spatial-resolution, wide FOV, and hyperspectral resolution images. Finally, we verified the feasibility and effectiveness of our experimental setup and algorithm by both simulation and experiment. The results show that our method can not only reconstruct high-spatial-resolution and wide FOV images, but also has a spectral resolution of 5 nm.

### 41. Introduction to Fourier Ptychography: Part I
- **Authors:** Kevin C. Zhou, Tomas Aidukas, Lars Loetgering, Felix Wechsler, Roarke Horstmeyer
- **Year:** 2022 | **Source:** CrossRef | **Citations:** 4
- **URL:** https://doi.org/10.1017/s1551929522000670
- **Abstract:** Abstract:Fourier ptychography is an emerging computational microscopy technique that can generate gigapixel-scale images of biological samples. With only the addition of a low-cost LED array to a standard digital microscope and a reconstruction algorithm, Fourier ptychography overcomes the fundamental trade-off between a microscope's resolution and field-of-view without any moving parts. This article is the first in a three-part series that aims to introduce the fundamentals of the technology to the broader microscopy community and beyond, using intuitive explanations.

### 42. Applications and Extensions of Fourier Ptychography
- **Authors:** Tomas Aidukas, Felix Wechsler, Lars Loetgering, Kevin Zhou, Roarke Horstmeyer
- **Year:** 2022 | **Source:** CrossRef | **Citations:** 3
- **URL:** https://doi.org/10.1017/s1551929522001298
- **Abstract:** Abstract:                This is the third article within a three-part series on Fourier ptychography, which is a computational microscopy technique for high-resolution, large field-of-view imaging. While the previous articles introduced the working principles of the technique, in this article we focus on the practical benefits that it brings to the imaging community. We present a didactic overview of the most important and well-established practical use-cases such as gigapixel imaging, quantitative phase contrast, thick sample imaging, and aberration metrology. We also discuss how Fourier ptychography can leave the visible light domain and venture into the realm of smaller wavelengths such as X-rays and electrons, among other topics.

### 43. Fourier Ptychography Part II: Phase Retrieval and High-Resolution Image Formation
- **Authors:** Lars Loetgering, Tomas Aidukas, Kevin C Zhou, Felix Wechsler, Roarke Horstmeyer
- **Year:** 2022 | **Source:** CrossRef | **Citations:** 3
- **URL:** https://doi.org/10.1017/s1551929522001055
- **Abstract:** Abstract:                This article is the second within a three-part series on Fourier ptychography, which is a computational microscopy technique for high-resolution, large field-of-view imaging. While the first article laid out the basics of Fourier ptychography, this second part sheds light on its algorithmic ingredients. We present a non-technical discussion of phase retrieval, which allows for the synthesis of high-resolution images from a sequence of low-resolution raw data. Fourier ptychographic phase retrieval can be carried out on standard, widefield microscopy platforms with the simple addition of a low-cost LED array, thus offering a convenient alternative to other phase-sensitive techniques that require more elaborate hardware such as differential interference contrast and digital holography.

### 44. Multimodal imaging using combined Optical Fourier Ptychographic Microscopy and Atomic Force Microscopy for biological measures
- **Authors:** Omer Wagner, Alexander K Winkel, Eva Kreysing, Kristian Franze
- **Year:** 2022 | **Source:** CrossRef | **Citations:** 1
- **URL:** https://doi.org/10.1364/cleo_at.2022.atu5i.3
- **Abstract:** We present a platform that perform live imaging using Fourier Ptychographic Microscopy co-localised with Atomic Force Microscopy. This specially fit emerging research on cellular biological processes regulated by tissue mechanics, including neuronal growth and stem-cell differentiation.

### 45. Fourier Ptychographic Microscopy Reconstruction Method Based on Residual Transfer Networks
- **Authors:** Xiaoli Wang, Yan Piao, Jie Li, Jinyang Yu
- **Year:** 2022 | **Source:** CrossRef | **Citations:** 1
- **URL:** https://doi.org/10.1088/1742-6596/2400/1/012015
- **Abstract:** Abstract                Fourier ptychographic microscopy reconstruction mostly adopts the traditional alternating iterative phase recovery method and optimization method, which has high computational complexity, high redundancy of image acquisition data, low reconstruction quality and high time consumption. In this paper, the model of residual transfer networks based on Resnet152 is proposed for Fourier ptychographic microscopy reconstruction, the learning process of deep convolution neural network is introduced, and the image reconstruction method based on deep learning realizes the end-to-end reconstruction of low-resolution images to high-resolution images. Through comparative experiments and analysis, the residual network can overcome the gradient explosion, make the feature information more complete and efficient, and the incremental up-sampling reconstruction network has higher image quality, lower computational complexity and shorter running time.

### 46. Physics-Informed Variational Autoencoder for Undersampled Fourier Ptychography
- **Authors:** Yolanda Hu, Andrew Olsen, Jan Funke, Srinivas Turaga, Vidya Ganapati
- **Year:** 2022 | **Source:** CrossRef | **Citations:** 1
- **URL:** https://doi.org/10.1364/cosi.2022.cf1d.8
- **Abstract:** This paper presents an unsupervised deep learning method for complex object reconstruction in severely undersampled Fourier ptychographic microscopy. The method requires no ground truth objects, only a dataset of undersampled measurements.

### 47. Adaptive optical quantitative phase imaging with annular illumination Fourier ptychographic microscopy
- **Authors:** Chao Zuo, Yefeng Shu, Jiasong Sun
- **Year:** 2022 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1364/dh.2022.w7a.3
- **Abstract:** We propose an adaptive optical QPI method to solve time-varying aberrations in long-term imaging based on Fourier ptychographic microscopy. Only a few images captured under the annular matched illumination are required to realize the aberration-free live-cell observation.

### 48. High-Resolution Display Screen as Illumination for Fourier Ptychographic Microscopy
- **Authors:** Kyungwon Lee, Kyung Chul Lee, Jaewoo Jung, Hyesuk Chae, Seung Ah Lee
- **Year:** 2022 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1364/cosi.2022.cth3c.2
- **Abstract:** We propose a technique for using a display screen as a light source for Fourier Ptychographic Microscopy (FPM). This method easily modulates multiple patterns to cover the entire sensor and build a compact optical system.

### 49. Fourier ptychography multi-parameter neural network with composite physical priori optimization
- **Authors:** Delong Yang, Shaohui Zhang, Chuanjian Zheng, Guocheng Zhou, Lei Cao, Yao Hu, Qun Hao
- **Year:** 2022 | **Source:** CrossRef | **Citations:** 0
- **URL:** https://doi.org/10.1364/cleopr.2022.ctha13b_05
- **Abstract:** Fourier ptychography microscopy(FPM) is a recently developed computational imaging approach for microscopic super-resolution imaging. Nevertheless, FPM has high requirements for the system construction and data acquisition processes which brings many limitations to its practical applications. In this paper, we propose a Fourier ptychography multi-parameter neural network (FPMN) with composite physical prior optimization. A hybrid parameter determination strategy combining physical imaging model and data-driven network training is proposed to recover the multi layers of the network corresponding to different physical parameters, including sample complex function, system pupil function, defocus distance, LED array position deviation and illumination intensity fluctuation, etc. Among these parameters, LED array position deviation is recovered based on the features of brightfield to darkfield transition low-resolution images while the others are recovered in the process of training of the neural network. The feasibility and effectiveness of FPMN are verified through simulations and actual experiments. Therefore, FPMN can evidently reduce the requirement for practical applications of FPM.

### 50. Fourier ptychography algorithm based on scaled Fourier transform
- **Authors:** Mojde Hasanzade, Nazabat Hussain, Dag W. Breiby, Muhammad N. Akram
- **Year:** 2021 | **Source:** CrossRef | **Citations:** 3
- **URL:** https://doi.org/10.1049/ell2.12081
- **Abstract:** Abstract                   This letter discusses an alternative Fourier ptychography algorithm based on the scaled fast Fourier transform propagation. The advantage of this scheme is that it enables a zoom‐in capability of the object spectrum and complex pupil within the synthetic numerical aperture without increasing the overall matrix size. Thus, the high‐resolution complex object and complex pupil are recovered utilising a larger fraction of the elements in their respective representation matrices. Experimental results are presented showing the performance of this scheme against the tradition fast‐Fourier‐transform‐based approach.

