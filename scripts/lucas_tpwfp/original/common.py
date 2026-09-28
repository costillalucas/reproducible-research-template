from numbers import Number
import os
import pathlib
from typing import Generator, Callable, NewType
from matplotlib import pyplot as plt
from matplotlib.pyplot import cm
import numpy as np
import numpy.typing as npt
from PIL import Image
from skimage import transform as skt
import math
from tqdm import tqdm
import re
import pandas as pd
import time


PixelPosition = tuple[int, int] | npt.NDArray[np.int_]
Vector2 = tuple[float, float]
Vector3 = tuple[float, float, float]
RealSpace3 = NewType("RealSpace3", Vector3)
FourierSpace3 = NewType("FourierSpace3", Vector3)
FourierPixel2 = NewType("FourierPixel2", Vector2)
FourierImage = NewType("FourierImage", npt.NDArray[np.complex128])

def calculate_k_vectors_k_indices_integral(led_positions: dict[tuple[int, int], RealSpace3],
                                info, sample_position, dc_location, fourier_pixel_factor) -> (dict, dict):
    k_vectors = {}
    k_pixels = {}
    k_indices = {}
    for key, led_position in led_positions.items():
        k_vectors[key] = calculate_k_vector(led_position, info['wave'], sample_position, 0)
    for key, k_vector in k_vectors.items():
        k_pixels[key] = dc_location + k_vector[:2] / (2 * np.pi * fourier_pixel_factor)
    for key, k_pixel in k_pixels.items():
        k_indices[key] = construir_indices(k_pixel)
    return k_vectors, k_indices

def calculate_k_vectors_k_indices(led_positions: dict[tuple[int, int], RealSpace3],
                                wavelength, sample_position, dc_location, fourier_pixel_factor) -> (dict, dict):
    k_vectors = {}
    k_pixels = {}
    k_indices = {}
    for key, led_position in led_positions.items():
        k_vectors[key] = calculate_k_vector(led_position, wavelength, sample_position, 0)
    for key, k_vector in k_vectors.items():
        k_pixels[key] = dc_location + k_vector[:2] / (2 * np.pi * fourier_pixel_factor)
    for key, k_pixel in k_pixels.items():
        k_indices[key] = construir_indices(k_pixel)
    return k_vectors, k_indices

def calculate_led_position_square_matrix(
    m: int, n: int, 
    central_led: tuple[int, int],
    matrix_center: RealSpace3, led_spacing: float, 
    # tilt angles
    ) -> RealSpace3:
    """Calcula la posicion del LED dada las propiedades de la matriz
    """
    """La diferencia en el cálculo de x_led e y_led está dado por el orden de toma de imágenes de la cámara"""
    x_led = (central_led[1] - n) * led_spacing + matrix_center[1]
    y_led = (m - central_led[0]) * led_spacing + matrix_center[0]

    return (x_led, y_led, matrix_center[2])

def calculate_k_vector(led_position: RealSpace3, wavelength: float, sample_position: RealSpace3, h_error) -> FourierSpace3:
    """Calcula el vector k (en dimensiones fisicas) dado un led encendido.
    """

    coordenadas = np.asarray(sample_position) + np.asarray((0,0,h_error)) - np.asarray(led_position)

    r = np.linalg.norm(coordenadas)

    vector_de_onda = (2*np.pi / wavelength) * coordenadas / r

    return vector_de_onda

def calculate_fourier_pixel_factor(
    pixel_size: float,
    magnification: float,
    lr_shape: tuple[int, int],
    ) -> float:

    assert lr_shape[0] == lr_shape[1], "The image is not square"
    fourier_pixel_factor = magnification / (lr_shape[0]*pixel_size)
    return fourier_pixel_factor

def calulate_max_angle(led_positions: dict[tuple[int, int], RealSpace3], central_led: tuple[int, int], sample_heigth:float) -> float:
    deltas = np.asarray(list(led_positions.values())) - np.asarray(led_positions[central_led])
    angles = np.arctan2(deltas,sample_heigth)
    return np.max(angles)

def calculate_LR_ratio(numerical_aperture:float, max_angle: float) -> float:
    LR_ratio = numerical_aperture / np.sin(max_angle)
    return LR_ratio

def create_pupil(pupil_radio: int, lr_shape: tuple[int, int]) ->  npt.NDArray[np.bool]:
    center = int(lr_shape[0]/2), int(lr_shape[1]/2)
    Y, X = np.ogrid[:lr_shape[1], :lr_shape[0]]
    dist_from_center2 = (X - center[0])**2 + (Y-center[1])**2
    pupil = dist_from_center2 < pupil_radio**2
    return pupil

def create_aberrated_pupil(
        pupil_radio: int,
        lr_shape: tuple[int, int],
        zernike_coeffs: dict[str, float] | None = None,
    ) -> npt.NDArray[np.complex128]:
    """Pupila compleja con aberraciones conocidas, para validar EPRY.

    Magnitud: la misma apertura binaria de `create_pupil` (soporte físico del
    sistema). Fase: combinación de unos pocos polinomios de Zernike de bajo
    orden (defocus + coma en x), evaluados en coordenadas normalizadas al
    radio de la pupila.

    Parameters
    ----------
    zernike_coeffs
        coeficientes conocidos por nombre, p.ej. {"defocus": 0.3, "coma_x": 0.15}
        (en radianes, pico de cada término). Default: un caso de prueba fijo,
        no nulo pero moderado, para tener siempre algo real que EPRY deba
        recuperar sin sacar a la reconstrucción de su cuenca de convergencia
        -- una aberración demasiado fuerte (probado: 1.5/0.8 rad) hace que el
        objeto colapse a ruido en las primeras iteraciones, antes de que
        EPRY llegue a corregir nada (ver diagnóstico real, sesión 2026-09-11).

    Returns
    -------
    pupila compleja (magnitud = soporte binario, fase = aberración de Zernike)
    """
    if zernike_coeffs is None:
        zernike_coeffs = {"defocus": 0.3, "coma_x": 0.15}

    support = create_pupil(pupil_radio, lr_shape)

    center = int(lr_shape[0] / 2), int(lr_shape[1] / 2)
    Y, X = np.ogrid[:lr_shape[1], :lr_shape[0]]
    rho_x = (X - center[0]) / pupil_radio
    rho_y = (Y - center[1]) / pupil_radio
    rho2 = rho_x**2 + rho_y**2

    z_defocus = 2 * rho2 - 1               # Z_2^0
    z_coma_x = (3 * rho2 - 2) * rho_x      # Z_3^1, componente en x

    phase = (
        zernike_coeffs.get("defocus", 0.0) * z_defocus
        + zernike_coeffs.get("coma_x", 0.0) * z_coma_x
    )

    return support.astype(np.complex128) * np.exp(1j * phase)

def calculate_led_positions_equi(leds_number_x: int, leds_number_y: int ,led_spacing: float,
                            matrix_center: RealSpace3) -> dict [tuple[int, int], RealSpace3]:
    led_positions = {}
    central_led = ((leds_number_x + 1)/ 2 , (leds_number_y +1) / 2)
    for i in range(1,leds_number_x+1):
        for j in range(1,leds_number_y+1):
            led_positions[(i,j)] = calculate_led_position_square_matrix(i, j, central_led, matrix_center, led_spacing)
    return led_positions

def calculate_led_positions_no_equi(
        k_distributions: dict, central_led: tuple, sample_heigth: float, wavelength: float,
        matrix_center: RealSpace3) -> dict [tuple[int, int], RealSpace3]:
    led_positions = {}
    k_distributions_r3 = {}
    for key, k_vector in k_distributions.items():
        kz = np.sqrt((2*np.pi/wavelength)**2 - (k_vector[0])**2 - (k_vector[1])**2)
        k_distributions_r3[key] = -1 * np.asarray(k_vector) + np.asarray((0,0,kz))
    for key, k_vector in k_distributions_r3.items():
        k_magnitude = np.linalg.norm(k_vector)
    
        if k_magnitude == 0:
            led_positions[key] = np.asarray((0,0,0))
        else:
            r_magnitude = k_magnitude * sample_heigth / k_vector[2]
            r_vector = - (r_magnitude / k_magnitude) * k_vector  # Direccionamos con la normalización de k
    
            led_position = r_vector + np.asarray((0,0,sample_heigth))
            led_positions[key] = led_position
    return led_positions

def construir_indices(k_pixel) -> npt.NDArray[np.int16]:
    axs0 = math.floor(k_pixel[0])
    axs1 = math.floor(k_pixel[1])
    # maximum_value_x, minimum_value_x = round((hr_shape[0])*3/4), round((hr_shape[0])/4)
    # maximum_value_y, minimum_value_y = round((hr_shape[1])*3/4), round((hr_shape[1])/4)
    
    # if axs0 < minimum_value_x or axs0 > maximum_value_x or axs1 < minimum_value_y or axs1 > maximum_value_y:
    #     pass
    # else:
    mask = np.stack((axs0, axs1)).T
    return mask

def read_into_complex_image(mag_filename: str | pathlib.Path, phase_filename: str | pathlib.Path) -> npt.NDArray[np.complex128]:    
    """Read two monochrome image files corresponding to magnitude and phase and
    generate an complex image.
    """
    magnitude = plt.imread(str(mag_filename)).astype(np.float64)
    phase = plt.imread(str(phase_filename)).astype(np.float64)
    if magnitude.ndim == 3:
        magnitude = magnitude[:, :, 0]
    if phase.ndim == 3:
        phase = phase[:, :, 0]
    phase = phase - np.min(phase)
    phase = phase / np.max(phase)
    phase = phase * np.pi / 2
    return magnitude * np.exp(1j * phase)

def linear_operator(xx: npt.NDArray[np.complex128],
                     indices: dict[tuple[int, int], tuple[int, int]],
                     lr_shape: tuple[int, int], 
                     pupil: npt.NDArray[np.uint8]
                     )-> npt.NDArray[np.complex128]: 
    """Linear transform of the signal.

    Parameters
    ----------
    xx
        original signal (HR spectrum)
    masks
        each point indicates the index of the left-upper point of the LR image in the HR spectrum
    n0_LR, n1_LR
        the pixel numbers of xx_c (LR) in two dimensions
    pupil

    Returns
    -------
    sampling output
    """   

    xx_c = {} 
    n0_LR, n1_LR = lr_shape
    for key, (ndx0, ndx1) in indices.items(): 
        s0 = safe_slice_lo(ndx0 - n0_LR//2, n0_LR, 0, xx.shape[0])
        s1 = safe_slice_lo(ndx1 - n1_LR//2, n1_LR, 0, xx.shape[1])
        xx_c[key] = xx[s0, s1] * pupil
    for key in xx_c:
        xx_c[key] = np.fft.ifft2(np.fft.ifftshift(xx_c[key], axes=(0, 1)), axes=(0, 1))
    return xx_c

def simulate(
        obj: npt.NDArray[np.complex128],
        lr_shape: tuple[int, int],
        lr_pupil_radio: int,
        indices: dict[tuple[int, int], tuple[int, int]],
        real_pupil: npt.NDArray[np.complex128] | None = None,
    ) -> npt.NDArray[np.complex128]:
    """Given an object transmission, the ratio between low and high resolution and the 'masks'

    return the acquired data, maximum value and the pupil.

    real_pupil
        pupila (potencialmente compleja/aberrada, ver `create_aberrated_pupil`)
        usada para generar los datos simulados. Default None: se usa la misma
        máscara binaria trivial de siempre (comportamiento sin cambios). La
        pupila devuelta para inicializar la reconstrucción sigue siendo
        siempre la binaria plana, sin importar qué pupila se usó para simular
        — así queda una aberración real conocida que EPRY debería recuperar.
    """
    pupil = create_pupil(lr_pupil_radio, lr_shape)
    simulation_pupil = pupil if real_pupil is None else real_pupil

    objf = np.fft.fftshift(np.fft.fft2(obj))

    xx_c = linear_operator(objf, indices, lr_shape, simulation_pupil)
    y = {}
    for key in xx_c:
        y[key] = np.abs(xx_c[key]) ** 2

    y_original_max = np.max(y)

    # Esto es problematico porque puede dar negativo. Cambiar a rudio de poisson.
    # y = np.random.normal(y, sigmaN)
    return y, pupil

def simulate_integral(
        obj: npt.NDArray[np.complex128], 
        lr_shape: tuple[int, int], 
        lr_pupil_radio: int,
        indices: dict[tuple[int, int], tuple[int, int],],
        color
    ) -> npt.NDArray[np.complex128]:
    """Given an object transmission, the ratio between low and high resolution and the 'masks' 

    return the acquired data, maximum value and the pupil.
    """
    pupil = create_pupil(lr_pupil_radio, lr_shape)

    objf = np.fft.fftshift(np.fft.fft2(obj))

    xx_c = linear_operator(objf, indices, lr_shape, pupil)
    y = {}
    for key in xx_c:
        y[key, color] = np.abs(xx_c[key]) ** 2

    y_original_max = np.max(y)

    # Esto es problematico porque puede dar negativo. Cambiar a rudio de poisson.
    # y = np.random.normal(y, sigmaN)
    return y, pupil


def safe_zero(mx0, mn0, mx1, mn1, n0_LR, n1_LR, L, hr_shape):
    mx_0 = mx0 - mn0 + n0_LR
    mx_1 = mx1 - mn1 + n1_LR
    if mx_0 > hr_shape[0]:
        mx_0 = hr_shape[0]
    if mx_1 > hr_shape[1]:
        mx_1 = hr_shape[1]
    return np.zeros(
        (mx_0,
         mx_1,
         L), dtype = np.complex128
         )

def safe_zero_2D(mx0, mn0, mx1, mn1, n0_LR, n1_LR, hr_shape):
    mx_0 = mx0 - mn0 + n0_LR
    mx_1 = mx1 - mn1 + n1_LR
    if mx_0 > hr_shape[0]: mx_0 = hr_shape[0]
    if mx_1 > hr_shape[1]: mx_1 = hr_shape[1]
    return np.zeros((mx_0, mx_1), dtype=np.complex128)

def safe_slice_lo(start: int, n0_LR: int, minimun_value: int, maximum_value: int):
    start = max(start, minimun_value)
    stop = start + n0_LR
    
    if stop > maximum_value:
        print("linear operator")
        print(start, stop)
        stop = maximum_value
        start = stop - n0_LR
        
    return slice(start, stop)

def safe_slice_ilo(start: int, n0_LR: int, minimun_value: int, maximum_value: int):
    start = max(start, minimun_value)
    stop = start + n0_LR
    
    if stop > maximum_value:
        print("inverse linear operator")
        print(start, stop)
        stop = maximum_value
        start = stop - n0_LR
        
    return slice(start, stop)

def safe_slice_ilo2(start: int, n0_LR: int, minimun_value: int, maximum_value: int):
    start = max(start, minimun_value)
    stop = start + n0_LR
    
    if stop > maximum_value:
        print("inverse linear operator 2")
        print(start, stop)
        stop = maximum_value
        start = stop - n0_LR
        
    return slice(start, stop)

def safe_slice(start: int, n0_LR: int, minimun_value: int, maximum_value: int):
    start = max(start, minimun_value)
    stop = start + n0_LR
    
    if stop > maximum_value:
        print("suma pupilas")
        print(start, stop)
        stop = maximum_value
        start = stop - n0_LR
        
    return slice(start, stop)

def sum_pupils(hr_shape: tuple[int, int], lr_shape: tuple[int, int], radio:float, indices: dict[tuple[int,int], tuple[int, int]]):
    matriz_ceros = np.zeros(hr_shape)
    pupil = create_pupil(radio, lr_shape)
    n0_LR, n1_LR = lr_shape
    for key, (ndx0, ndx1) in indices.items():
        s0 = safe_slice(ndx0 - (n0_LR+1) // 2, n0_LR, 0, hr_shape[0])
        s1 = safe_slice(ndx1 - (n1_LR+1) // 2, n1_LR, 0, hr_shape[1])
        if s0 is None or s1 is None:
            pass
        else:
            matriz_ceros[s0, s1] += pupil
    return matriz_ceros

def save_images_integral(data, carpeta):
    filedir = pathlib.Path(carpeta)
    filedir.mkdir(parents=True, exist_ok=True)
    
    for key, array in data.items():
        if isinstance(key, tuple):
            # Convierte todos los elementos de la tupla (incluso si hay sub-tuplas) en una lista plana
            def aplanar(t):
                elementos = []
                for item in t:
                    if isinstance(item, tuple):
                        elementos.extend(aplanar(item))
                    else:
                        elementos.append(str(item).zfill(2) if isinstance(item, int) else str(item))
                return elementos
            
            partes_nombre = aplanar(key)
            nombre = "point_" + "_".join(partes_nombre)
        else:
            nombre = f"point_{key}"
            
        np.save(filedir / nombre, array)

def save_images(data, carpeta):
    filedir = pathlib.Path(carpeta)
    for key, array in data.items():
        nombre = f"point_{str(key[0]).zfill(2)}_{str(key[1]).zfill(2)}"
        np.save(filedir / nombre, array)

def save_images_2(data, carpeta):
    filedir = pathlib.Path(carpeta)
    for key, array in data.items():
        nombre = f"iteracion_{str(key)}"
        np.save(filedir / nombre, array)

def inverse_linear_operator(xx_c: npt.NDArray[np.complex128],
                             indices: npt.NDArray[np.intp],
                             hr_shape: tuple[int, int],
                             pupil: npt.NDArray[np.uint8]
                             )-> npt.NDArray[np.complex128]:
    """Inverse linear transform of the signal.

    Parameters
    ----------
    xx_c
        sampling output
    masks
        each point indicates the index of the left-upper point of the LR image in the HR spectrum
    n0, n1
        the pixel numbers of xx_mean_large (HR) in two dimensions
    pupil

    Returns
    -------
    original signal (HR spectrum).
    """

    n0_LR, n1_LR, L = xx_c.shape
    indices_stack = np.asarray(list(indices.values())) 
    xx_c = np.fft.fftshift(np.fft.fft2(xx_c, axes=(0, 1)), axes=(0, 1))
    mn0, mn1 = np.min(indices_stack, axis=0)
    mx0, mx1 = np.max(indices_stack, axis=0)

    xx = np.zeros(
        (mx0 - mn0 + n0_LR,
         mx1 - mn1 + n1_LR,
         L), dtype = np.complex128
         )

    for k in range(L):
        ndx0 = indices_stack[k, 0]
        ndx1 = indices_stack[k, 1]

        s0 = slice(ndx0 - mn0, ndx0 + n0_LR - mn0)
        s1 = slice(ndx1 - mn1, ndx1 + n1_LR - mn1)
        
        xx[s0, s1, k] = xx_c[:, :, k] * np.conj(pupil)
    
    xx_mean = np.mean(xx, axis=2)
    xx_mean_large = np.zeros((hr_shape), dtype=np.complex128)

    s0 = slice(mn0, mn0 + xx_mean.shape[0])
    s1 = slice(mn1, mn1 + xx_mean.shape[1])
    xx_mean_large[s0, s1] = xx_mean

    return xx_mean_large

def inverse_linear_operator_real_images(xx_c: npt.NDArray[np.complex128],
                             indices: npt.NDArray[np.intp],
                             hr_shape: tuple[int, int],
                             pupil: npt.NDArray[np.uint8]
                             )-> npt.NDArray[np.complex128]:
    """Inverse linear transform of the signal.

    Parameters
    ----------
    xx_c
        sampling output
    masks
        each point indicates the index of the left-upper point of the LR image in the HR spectrum
    n0, n1
        the pixel numbers of xx_mean_large (HR) in two dimensions
    pupil

    Returns
    -------
    original signal (HR spectrum).
    """

    n0_LR, n1_LR, L = xx_c.shape
    indices_stack = np.asarray(list(indices.values())) 
    xx_c = np.fft.fftshift(np.fft.fft2(xx_c, axes=(0, 1)), axes=(0, 1))
    mn0, mn1 = np.min(indices_stack, axis=0)
    mx0, mx1 = np.max(indices_stack, axis=0)
    xx = safe_zero(mx0, mn0, mx1, mn1, n0_LR, n1_LR, L, hr_shape)

    for k in range(L):
        ndx0 = indices_stack[k, 0]
        ndx1 = indices_stack[k, 1]

        s0 = safe_slice_ilo(ndx0 - mn0, n0_LR, 0, hr_shape[0])
        s1 = safe_slice_ilo(ndx1 - mn1, n1_LR, 0, hr_shape[1])
        
        xx[s0, s1, k] = xx_c[:, :, k] * np.conj(pupil)
    
    xx_mean = np.mean(xx, axis=2)
    xx_mean_large = np.zeros((hr_shape), dtype=np.complex128)

    s0 = safe_slice_ilo2(mn0, xx_mean.shape[0], 0, hr_shape[0])
    s1 = safe_slice_ilo2(mn1, xx_mean.shape[1], 0, hr_shape[1])
    xx_mean_large[s0, s1] = xx_mean

    return xx_mean_large

def quality(x: npt.NDArray[np.complex128], target: npt.NDArray[np.complex128]) -> float:
    """Calculate the quality of the reconstruction by comparing 
    the reconstruction to the target value.
    """
    return np.sum(np.abs(np.abs(x) - np.abs(target))) / np.sum(np.abs(target))

from skimage.metrics import structural_similarity as ssim
from skimage.metrics import peak_signal_noise_ratio as psnr

def quality_dict(x: npt.NDArray[np.complex128], target: npt.NDArray[np.complex128]) -> dict:
    """Calcula la calidad de la reconstrucción pticográfica.
    Retorna un diccionario con errores relativos, correlaciones, MSE complejo, SSIM y PSNR.
    """
    mag_x = np.abs(x)
    mag_target = np.abs(target)

    phase_x = np.angle(x)
    phase_target = np.angle(target)

    # 1. Correlaciones (Aplanado)
    mag_corr = np.corrcoef(mag_x.ravel(), mag_target.ravel())[0, 1]
    phase_corr = np.corrcoef(phase_x.ravel(), phase_target.ravel())[0, 1]
    
    # 2. Compensación de Fase Global y MSE Complejo
    # Encuentra la fase constante que mejor alinea 'x' con 'target'
    cross_corr = np.sum(x * np.conj(target))
    global_phase = np.angle(cross_corr)
    
    # Aplica la corrección y calcula el error cuadrático del campo complejo
    x_shifted = x * np.exp(-1j * global_phase)
    mse_complex = np.mean(np.abs(x_shifted - target)**2)

    # 3. Métricas de Imagen: SSIM y PSNR (sobre la magnitud)
    # Definimos el rango de datos en base al target para que skimage no use valores por defecto
    data_range_mag = mag_target.max() - mag_target.min()
    
    # Si las imágenes son 2D, data_range es suficiente. 
    # (Añadir channel_axis=-1 si fueran multicanal, que no suele ser el caso en FP)
    ssim_mag = ssim(mag_target, mag_x, data_range=data_range_mag)
    psnr_mag = psnr(mag_target, mag_x, data_range=data_range_mag)

    return {
        "err_relativo_magnitud": np.sum(np.abs(mag_x - mag_target)) / np.sum(mag_target),
        "err_relativo_fase": np.sum(np.abs(np.angle(x * np.conj(target)))) / np.sum(np.abs(phase_target)),
        "corr_magnitud": mag_corr,
        "corr_fase": phase_corr,
        "fase_global_rad": global_phase,
        "mse_complejo_alineado": mse_complex,
        "ssim_magnitud": ssim_mag,
        "psnr_magnitud": psnr_mag
    }

from scipy.stats import entropy

def blind_quality_dict(x: np.ndarray, 
                       lr_intensities_measured=None, 
                       lr_intensities_simulated=None, 
                       x_old: np.ndarray = None) -> dict:
    """
    Calcula métricas de calidad de reconstrucción pticográfica sin imagen de referencia.
    """
    mag_x = np.abs(x)
    phase_x = np.angle(x)
    
    # --- MÉTRICAS DE MAGNITUD (Ya las tenías) ---
    diff_h_mag = np.diff(mag_x, axis=0)
    diff_v_mag = np.diff(mag_x, axis=1)
    total_variation_mag = np.sum(np.abs(diff_h_mag)) + np.sum(np.abs(diff_v_mag))
    laplacian_var_mag = np.var(diff_h_mag) + np.var(diff_v_mag) 
    
    # hist_mag, _ = np.histogram(mag_x, bins=256, density=True)
    # hist_mag = hist_mag[hist_mag > 0]
    # img_entropy_mag = -np.sum(hist_mag * np.log2(hist_mag))
    
    # --- NUEVAS MÉTRICAS DE FASE ---
    phase_std = np.std(phase_x)
    
    # A. Variación Total de la Fase (Suavidad estructural de la fase)
    diff_h_phase = np.diff(phase_x, axis=0)
    diff_v_phase = np.diff(phase_x, axis=1)
    total_variation_phase = np.sum(np.abs(diff_h_phase)) + np.sum(np.abs(diff_v_phase))
    
    # B. Entropía de la Fase (Nivel de organización)
    # hist_phase, _ = np.histogram(phase_x, bins=256, density=True)
    # hist_phase = hist_phase[hist_phase > 0]
    # img_entropy_phase = -np.sum(hist_phase * np.log2(hist_phase))

    metrics = {
        "total_variation_magnitude": total_variation_mag,
        "sharpness_score_laplacian": laplacian_var_mag,
        # "shannon_entropy_magnitude": img_entropy_mag,
        "phase_global_std": phase_std,
        "total_variation_phase": total_variation_phase,
        # "shannon_entropy_phase": img_entropy_phase
    }
    
    # C. Tasa de Convergencia Inter-Iteracional (Requiere x_old)
    if x_old is not None:
        # Usamos multiplicación compleja para evitar errores de fase direccional (wrapping)
        phase_difference = np.angle(x * np.conj(x_old))
        metrics["phase_convergence_step"] = np.sum(np.abs(phase_difference)) / phase_difference.size
        
        # También podemos medir el cambio en magnitud
        metrics["mag_convergence_step"] = np.sum(np.abs(mag_x - np.abs(x_old))) / mag_x.size
    
    # --- ERROR DE REPROYECCIÓN ---
    if lr_intensities_measured is not None and lr_intensities_simulated is not None:
        reprojection_err = np.sum(np.abs(np.abs(lr_intensities_measured) - np.abs(lr_intensities_simulated))) / np.sum(np.abs(lr_intensities_measured))
        metrics["reprojection_data_error"] = reprojection_err

    return metrics

def reconstruct(recovery_error_required,
        data: dict[tuple[int, int],npt.NDArray[np.float128]],
        hr_shape: tuple[int, int],
        sigma2: float,
        indices: npt.NDArray[np.intp],
        pupil: npt.NDArray[np.uint8],
        iterations: int,
        mu_max: float,
        weight: float,
        target: npt.NDArray[np.complex128],
        on_iteration: Callable[[int, npt.NDArray[np.complex128]], None]
        ) -> tuple[npt.NDArray[np.complex128], npt.NDArray[np.complex128], npt.NDArray[np.float64]]: 
    """
    Algorithm 1: TPWFP algorithm for FP reconstruction. 
    Input: linear transform matrix A, measurement vector c, and initialization z(0). 
    Ouput: retrieved complex signal z (the sample’s HR spatial spectrum). 
    1. k= 0;
    2. while not converged do
    3. Update ξ according to Eq. (9);
    4. Update μ(k+1) according to Eq. (12);
    5. Update z(k+1) according to Eq. (11);
    6. k :=k+ 1.
    7. end
    
    Parameters
    ----------
    data
        captured LR images (shape: n1_LR, n2_LR, L);
    n0, n1
        the pixel numbers of im_r (HR) in two dimensions.
    sigma2
        variance of additive noise.
    masks
        L * 2 (each point indicates the index of the left-upper point of the LR image in the HR spectrum).
    pupil
        the pupil function.
    iterations
        the number of iterations.
    mu_max
        the stepsize parameter.
    weight
        the weighting parameter.
    newfolder
        folder for saving results.
    target
        original benchmark HR spectrum for calculating recovery error.

    Returns
    -------
    z0, final recovered image, recovery erros vs iterations
    """
    n0, n1, L = data.shape
    lr_shape = int(n0), int(n1)
    z_im = np.sqrt(data[:,:,int(np.fix(L/2))]) * lr_shape[0] * lr_shape[1] / hr_shape[0] / hr_shape[1] 
    # z_im = np.sqrt(data[:, :, int(np.fix(L / 2))]) * n0_LR * n1_LR / n0 / n1

    z_im = skt.resize(z_im, hr_shape) 
    z0 = np.fft.fftshift(np.fft.fft2(z_im))
    z = z0

    recovery_errs = np.zeros(iterations)
    recovery_errs[0] = quality(z, target)
    N = np.zeros(data.shape)
    epsilon = N
    normest = np.sqrt(np.sum(data) / L / lr_shape[0] / lr_shape[1])
    
    step_size_n = 0.01
    alpha = - np.log(0.997)

    ## Si se necesitan recopilar imágenes intermedias
    imagenes_magnitud_200_300 = {}
    imagenes_fase_200_300 = {}
    recovery_errs_records = []
    imagenes_intermedias = {}
    phase_max_list = []
    phase_min_list = []
    for ndx in tqdm(range(1, iterations)):

        # update z
        Bz = linear_operator(z, indices, lr_shape, pupil)
        Bz_array = np.stack([Bz[key] for key in sorted(Bz.keys())], axis=-1)
        Cz = (np.abs(Bz_array) ** 2 + N - data) * Bz_array  #eq 9 Bian 2016
        w = inverse_linear_operator_real_images(Cz, indices, hr_shape, pupil) #eq 10 Bian 2016 truncated Wirtinger gradient 
        
        mu = 1 - np.exp(- alpha * ndx)  
        mu = min(mu, mu_max) / normest ** 2 #eq 12 Bian 2016

        z = z - mu * w  #eq 11 Bian 2016

        # update N
        CN = (np.abs(Bz_array) ** 2 + N - data) + weight * (N * N - 9 * sigma2 + epsilon * epsilon) * 2.0 * N
        step_n = mu * step_size_n
        N = N - step_n * CN
        
        # update epsilon
        e_temp = 9 * sigma2 - N * N
        e_temp[e_temp < 0] = 0
        epsilon = np.sqrt(e_temp)
        recovery_errs[ndx] = quality(z, target)

        qd = quality_dict(z, target)
        qd["recovery_err"] = recovery_errs[ndx]

        recovery_errs_records.append(qd)
        on_iteration(ndx, z)
        fase = np.angle(np.fft.ifft2(np.fft.ifftshift(z.astype(np.complex128))).astype(np.complex128))

        phase_max_list.append(np.max(fase))
        phase_min_list.append(np.min(fase))

        # Si en un quinto de las iteraciones no llega a un error de corte se interrumpe el ciclo
        if recovery_error_required != 0:

            if recovery_errs[round(iterations * 1/ 9)] > (recovery_error_required + 0.10 * recovery_error_required):
                recovery_errs[round(iterations * 1 / 9):] = recovery_errs[ndx]
                break  

            # if recovery_errs[round(iterations * 1/ 9)] > (recovery_error_required):
            #     recovery_errs[round(iterations * 1 / 9):] = recovery_errs[ndx]
            #     break  

            if recovery_errs[round(iterations * 1/ 3)] > (recovery_error_required):
                recovery_errs[round(iterations * 1 / 3):] = recovery_errs[ndx]
                break   

            # if recovery_errs[round(iterations * 1 / 3)] > (recovery_error_required - 0.10 * recovery_error_required):
            #     recovery_errs[round(iterations * 1 / 3):] = recovery_errs[ndx]
            #     break  

            if recovery_errs[round(iterations * 3 / 5)] > (recovery_error_required - 0.10 * recovery_error_required):
                recovery_errs[round(iterations * 3 / 5):] = recovery_errs[ndx]
                break   

            # if recovery_errs[round(iterations * 3 / 5)] > (recovery_error_required - 0.30 * recovery_error_required):
            #     recovery_errs[round(iterations * 3 / 5):] = recovery_errs[ndx]
            #     break   

            # Si en un quinto de las iteraciones no llega a un error de corte se interrumpe el ciclo
            if recovery_errs[round(iterations * 9/ 10)] > (recovery_error_required - 0.9 * recovery_error_required):
                recovery_errs[round(iterations * 9 / 10):] = recovery_errs[ndx]
                break   

        if ndx % 100 == 0:
            imagen = np.fft.ifft2(np.fft.ifftshift(z))
            imagenes_intermedias[ndx] = imagen
        # ## Si se necesitan recopilar imágenes intermedias
        # if ndx > 240 and ndx < 399:
        #     imagen = np.fft.ifft2(np.fft.ifftshift(z))
        #     imagenes_magnitud_200_300[ndx] = np.abs(imagen)
        #     imagenes_fase_200_300[ndx] = np.angle(imagen)
        # Si necesitamos saber la velocidad con la que llega a cierto error
        # if recovery_errs[ndx] < 0.85:
        #     print (f"Iteracion {ndx}")
    im_r = np.fft.ifft2(np.fft.ifftshift(z))

    # ## Si se necesitan recopilar imágenes intermedias
    # carpeta_magnitud = "/home/chanoscopio/Documents/LucasC/code/ptyco-full-simulator/test/results/200_a_300_iteraciones/magnitud"
    # carpeta_fase = "/home/chanoscopio/Documents/LucasC/code/ptyco-full-simulator/test/results/200_a_300_iteraciones/fase"
    # save_images_2(imagenes_magnitud_200_300, carpeta_magnitud)
    # save_images_2(imagenes_fase_200_300, carpeta_fase)
    # ##

    return z0, im_r, recovery_errs_records, imagenes_intermedias, phase_max_list, phase_min_list

def linear_operator_vectorized(xx: npt.NDArray[np.complex128],
                               indices_stack: npt.NDArray[np.intp],
                               xx_c_buffer: tuple[int, int], 
                               pupil: npt.NDArray[np.uint8],
                               L: int
                               )-> npt.NDArray[np.complex128]: 
    n0_LR, n1_LR = xx_c_buffer.shape[:2]
    # # Pre-reservar memoria una sola vez
    # xx_c = np.zeros((n0_LR, n1_LR, L), dtype=np.complex128)
    xx_c = xx_c_buffer
    for k in range(L): 
        ndx0, ndx1 = indices_stack[k]
        s0 = safe_slice_lo(ndx0 - n0_LR//2, n0_LR, 0, xx.shape[0])
        s1 = safe_slice_lo(ndx1 - n1_LR//2, n1_LR, 0, xx.shape[1])
        xx_c[:, :, k] = xx[s0, s1] * pupil
        
    # Una sola IFFT 3D altamente optimizada por NumPy a lo largo de los ejes espaciales
    return np.fft.ifft2(np.fft.ifftshift(xx_c, axes=(0, 1)), axes=(0, 1))

def inverse_linear_operator_real_images_vectorized(xx_c: npt.NDArray[np.complex128],
                             indices_stack: npt.NDArray[np.intp], # Usamos el stack
                             xx_mean_large_buffer: tuple[int, int],
                             pupil: npt.NDArray[np.uint8],
                             return_fft_xx_c: bool = False,
                             )-> npt.NDArray[np.complex128]:
    # ¡Bórrar la línea de indices_stack = np.asarray(...) que tenías aquí adentro!
    n0_LR, n1_LR, L = xx_c.shape
    xx_c = np.fft.fftshift(np.fft.fft2(xx_c, axes=(0, 1)), axes=(0, 1))
    mn0, mn1 = np.min(indices_stack, axis=0)
    mx0, mx1 = np.max(indices_stack, axis=0)
    xx_sum = safe_zero_2D(mx0, mn0, mx1, mn1, n0_LR, n1_LR, xx_mean_large_buffer.shape)

    for k in range(L):
        ndx0 = indices_stack[k, 0]
        ndx1 = indices_stack[k, 1]

        s0 = safe_slice_ilo(ndx0 - mn0 - n0_LR//2, n0_LR, 0, xx_mean_large_buffer.shape[0])
        s1 = safe_slice_ilo(ndx1 - mn1 - n1_LR//2, n1_LR, 0, xx_mean_large_buffer.shape[1])

        xx_sum[s0, s1] += xx_c[:, :, k] * np.conj(pupil)

    xx_mean = xx_sum/L
    xx_mean_large = xx_mean_large_buffer

    s0 = safe_slice_ilo2(mn0, xx_mean.shape[0], 0, xx_mean_large_buffer.shape[0])
    s1 = safe_slice_ilo2(mn1, xx_mean.shape[1], 0, xx_mean_large_buffer.shape[1])
    xx_mean_large[s0, s1] = xx_mean

    # return_fft_xx_c=False (default): comportamiento sin cambios, un solo
    # valor de retorno. En True, además devuelve xx_c ya transformado a
    # Fourier LR (shape n0_LR, n1_LR, L) para que accumulate_pupil_gradient
    # lo reuse sin recalcular la FFT (ver EPRY, Paso 2 del plan).
    if return_fft_xx_c:
        return xx_mean_large, xx_c
    return xx_mean_large

def accumulate_pupil_gradient(z: npt.NDArray[np.complex128],
                               indices_stack: npt.NDArray[np.intp],
                               xx_c_fft: npt.NDArray[np.complex128],
                               pupil_shape: tuple[int, int],
                               return_energy: bool = False,
                               ) -> npt.NDArray[np.complex128]:
    """Gradiente de la pupila para EPRY (Ou/Zheng/Yang 2014).

    El modelo de formación de imagen es exit_wave_k = z[ventana_k] * pupil,
    simétrico al de z: el mismo residuo que corrige z (acumulado en el
    canvas HR, ponderado por conj(pupil)) corrige la pupila, acumulado en
    un buffer del tamaño de la pupila (LR), ponderado por conj(z[ventana_k])
    -- el recorte de objeto que ya se usó para generar Bz_array, no la pupila.

    Reusa la misma lógica de slicing que `linear_operator_vectorized` para
    recortar cada ventana de z, y el `xx_c_fft` ya calculado por
    `inverse_linear_operator_real_images_vectorized(..., return_fft_xx_c=True)`
    para no duplicar la FFT.

    Parameters
    ----------
    z
        objeto HR actual (mismo array que recibe linear_operator_vectorized).
    indices_stack
        posiciones de cada LED, misma convención que en linear_operator_vectorized.
    xx_c_fft
        residuo por LED ya transformado a Fourier LR (shape n0_LR, n1_LR, L).
    pupil_shape
        forma (n0_LR, n1_LR) de la pupila / del buffer de salida.
    return_energy
        si True, además devuelve la energía |z[ventana_k]|² acumulada sobre
        los mismos LEDs (mismo loop, sin recalcular slicing) -- se usa para
        normalizar el update de pupila, análogo a normest**2 para z.

    Returns
    -------
    gradiente de la pupila, shape == pupil_shape, dtype complejo. Si
    return_energy=True, devuelve (gradiente, energía) con energía real,
    misma shape.
    """
    n0_LR, n1_LR = pupil_shape
    L = indices_stack.shape[0]
    grad = np.zeros((n0_LR, n1_LR), dtype=np.complex128)
    if return_energy:
        energy = np.zeros((n0_LR, n1_LR), dtype=np.float64)
    for k in range(L):
        ndx0, ndx1 = indices_stack[k]
        s0 = safe_slice_lo(ndx0 - n0_LR//2, n0_LR, 0, z.shape[0])
        s1 = safe_slice_lo(ndx1 - n1_LR//2, n1_LR, 0, z.shape[1])
        z_window = z[s0, s1]
        grad += np.conj(z_window) * xx_c_fft[:, :, k]
        if return_energy:
            energy += np.abs(z_window) ** 2
    if return_energy:
        return grad, energy
    return grad

def reconstruct_test_integral(recovery_error_required,
        data: dict[tuple[int, int],npt.NDArray[np.float128]],
        hr_shape: tuple[int, int],
        sigma2: float,
        indices: npt.NDArray[np.intp],
        pupil: npt.NDArray[np.uint8],
        big_pupil,
        iterations: int,
        mu_max: float,
        weight: float,
        target: npt.NDArray[np.complex128],
        on_iteration: Callable[[int, npt.NDArray[np.complex128]], None],
        iteraciones_a_guardar, 
        congelar_leds
        ) -> tuple[npt.NDArray[np.complex128], npt.NDArray[np.complex128], npt.NDArray[np.float64]]: 
    """
    Algorithm 1: TPWFP algorithm for FP reconstruction. 
    Input: linear transform matrix A, measurement vector c, and initialization z(0). 
    Ouput: retrieved complex signal z (the sample’s HR spatial spectrum). 
    1. k= 0;
    2. while not converged do
    3. Update ξ according to Eq. (9);
    4. Update μ(k+1) according to Eq. (12);
    5. Update z(k+1) according to Eq. (11);
    6. k :=k+ 1.
    7. end
    
    Parameters
    ----------
    data
        captured LR images (shape: n1_LR, n2_LR, L);
    n0, n1
        the pixel numbers of im_r (HR) in two dimensions.
    sigma2
        variance of additive noise.
    masks
        L * 2 (each point indicates the index of the left-upper point of the LR image in the HR spectrum).
    pupil
        the pupil function.
    iterations
        the number of iterations.
    mu_max
        the stepsize parameter.
    weight
        the weighting parameter.
    newfolder
        folder for saving results.
    target
        original benchmark HR spectrum for calculating recovery error.

    Returns
    -------
    z0, final recovered image, recovery erros vs iterations
    """
    n0, n1, L = data.shape
    lr_shape = int(n0), int(n1)
    z_im = np.sqrt(data[:,:,int(np.fix(L/2))]) * lr_shape[0] * lr_shape[1] / hr_shape[0] / hr_shape[1] 
    # z_im = np.sqrt(data[:, :, int(np.fix(L / 2))]) * n0_LR * n1_LR / n0 / n1

    z_im = skt.resize(z_im, hr_shape) 
    z0 = np.fft.fftshift(np.fft.fft2(z_im))
    z = z0.copy()

    recovery_errs = np.zeros(iterations)
    recovery_errs[0] = quality(z, target)
    N = np.zeros(data.shape)
    epsilon = N
    normest = np.sqrt(np.sum(data) / L / lr_shape[0] / lr_shape[1])
    
    step_size_n = 0.01
    alpha = - np.log(0.997)

    ## Si se necesitan recopilar imágenes intermedias
    imagenes_magnitud_200_300 = {}
    imagenes_fase_200_300 = {}
    recovery_errs_records = []
    imagenes_intermedias = {}
    imagenes_intermedias[0] = z_im
    phase_max_list = []
    phase_min_list = []
    warmup_iters = int(iterations * 0.05) # 10% de las iteraciones para calentar
    mu_dynamic = mu_max  # Empezamos con el máximo
    z_old = None
    w_old = None
    indices_stack = np.asarray(list(indices.values()))
    L = len(indices_stack)
    diccionario_records = []
    hito_1 = round(iterations * 1 / 9)
    hito_2 = round(iterations * 1 / 3)
    hito_3 = round(iterations * 3 / 5)
    hito_4 = round(iterations * 9 / 10)
    xx_c_buffer = np.empty((lr_shape[0], lr_shape[1], L),dtype=np.complex128)
    xx_mean_large = np.zeros(hr_shape, dtype=np.complex128)
    pasos = []
    diferencias_LR = {}
    registros = []
    # --- ANTES DEL BUCLE DE ITERACIONES ---

    # Asumiendo que 'z' tiene frecuencias centradas (frecuencia 0 en el centro de la matriz)
    Ny, Nx = z.shape
    ky = np.linspace(-Ny//2, Ny//2 - 1, Ny)
    kx = np.linspace(-Nx//2, Nx//2 - 1, Nx)
    KX, KY = np.meshgrid(kx, ky)

    # Matriz 2D con el módulo k para cada píxel
    K_mag = np.sqrt(KX**2 + KY**2)
    # Redondeamos a enteros para poder usarlo como índices de agrupamiento (bins)
    K_int = np.round(K_mag).astype(int)

    # Precalculamos el número de píxeles que caen en cada radio k para el promedio
    conteo_radios = np.bincount(K_int.flatten())
    conteo_radios[conteo_radios == 0] = 1 # Para evitar advertencias de división por cero
    # --- ANTES DEL BUCLE ---
    # Transformamos el target al espacio de Fourier para tener el espectro ideal
    Z_target = np.fft.fftshift(np.fft.fft2(target))
    # Calculamos su perfil radial usando la misma lógica rápida
    perfiles_radiales_records = []
    perfil_radial_target = np.bincount(K_int.flatten(), weights=(np.abs(target*big_pupil)**2).flatten()) / conteo_radios
    perfil_target_record = []
    perfil_target_record.append(perfil_radial_target)
    # Diccionario donde guardaremos la historia del espectro
    espectros_radiales_records = {}
    """Intento de congelar informacion en el espectro de Fourier"""
    # --- NUEVO: Inicialización del sistema de congelamiento ---
    metrica_anterior = None
    leds_congelados = np.zeros(L, dtype=bool)
    umbral_congelamiento = 0.3  # Congela si el error normalizado baja del 90%
    for ndx in tqdm(range(1, iterations)):


        # 1. Aplicamos el operador directo vectorizado (ya te devuelve un array 3D)
        Bz_array = linear_operator_vectorized(z, indices_stack, xx_c_buffer, pupil, L)
        
        # 2. Operaciones in-place para ahorrar memoria
        error_term = np.abs(Bz_array)
        error_term **= 2
        error_term += N
        error_term -= data
        Cz = error_term * Bz_array
        """# --- NUEVO: Apagar el gradiente de los LEDs congelados ---
        Esto hace que la diferencia entre la data y las imágenes simuladas sea cero
        por lo que no hay nada que agregar o cambiar en la imagen de HR en esas frecuencias"""
        Cz[:, :, leds_congelados] = 0
        # 3. Aplicamos el operador inverso pasándole el stack directamente
        w = inverse_linear_operator_real_images_vectorized(Cz, indices_stack, xx_mean_large, pupil)

        # 1. Calculamos el mu base con tu warm-up actual
        # mu = np.float64(1 - np.exp(-alpha * ndx))
        mu = np.float64(1 - np.exp(-ndx/330))
        mu = np.minimum(mu, mu_max) / (normest ** 2)


        z -= mu * w  #eq 11 Bian 2016

        # update N
        CN = error_term + weight * (N * N - 9 * sigma2 + epsilon * epsilon) * 2.0 * N
        step_n = mu * step_size_n
        CN *= step_n
        N -= CN
        
        # update epsilon
        e_temp = 9 * sigma2 - N * N
        e_temp[e_temp < 0] = 0
        epsilon = np.sqrt(e_temp)
        recovery_errs[ndx] = quality(z, target)

        # qd = quality_dict(z, target)
        # qd["recovery_err"] = recovery_errs[ndx]

        # recovery_errs_records.append(qd)
        on_iteration(ndx, z)
        # fase = np.angle(np.fft.ifft2(np.fft.ifftshift(z.astype(np.complex128))).astype(np.complex128))/np.pi

        # phase_max_list.append(np.max(fase))
        # phase_min_list.append(np.min(fase))

        if recovery_error_required != 0:
            if ndx == hito_1 and recovery_errs[hito_1] > (recovery_error_required * 1.10):
                recovery_errs[hito_1:] = recovery_errs[ndx] 
                break
            elif ndx == hito_2 and recovery_errs[hito_2] > recovery_error_required:
                recovery_errs[hito_2:] = recovery_errs[ndx]
                break
            elif ndx == hito_3 and recovery_errs[hito_3] > (recovery_error_required * 0.90):
                recovery_errs[hito_3:] = recovery_errs[ndx] 
                break
            elif ndx == hito_4 and recovery_errs[hito_4] > (recovery_error_required * 0.10):
                recovery_errs[hito_4:] = recovery_errs[ndx]
                break


        if ndx % iteraciones_a_guardar == 0:
            # 1. Calculamos la intensidad y perfil de 'z' (lo que vimos antes)
            suma_radial = np.bincount(K_int.flatten(), weights=(np.abs(z*big_pupil)**2).flatten())
            perfil_radial = suma_radial / conteo_radios
            
            # --- NUEVO: Comparación ---
            # 2. Calculamos el Error Cuadrático Medio entre el perfil actual y el ideal
            error_radial_mse = np.mean((perfil_radial - perfil_radial_target)**2)
            # --------------------------
            perfiles_radiales_records.append(perfil_radial)
            imagen = np.fft.ifft2(np.fft.ifftshift(z))
            imagenes_intermedias[ndx] = imagen
            fase = np.angle(imagen)/np.pi

            phase_max_list.append(np.max(fase))
            phase_min_list.append(np.min(fase))
            
            qd_HR = quality_dict(z, target)
            qd_HR["recovery_err"] = recovery_errs[ndx]
            
            # --- NUEVO: Guardamos en el diccionario de calidad ---
            # qd_HR["perfil_radial"] = perfil_radial
            qd_HR["error_radial_mse"] = error_radial_mse
            # -----------------------------------------------------
            qd_LR = blind_quality_dict(z, lr_intensities_measured=data, lr_intensities_simulated=(np.abs(Bz_array))**2, x_old=z_old)
            qd_LR["recovery_err"] = recovery_errs[ndx]
            recovery_errs_records.append(qd_HR)
            diccionario_records.append(qd_LR)
            pasos.append(mu)
            diferencias = np.sum(np.abs(np.abs(data) - np.abs((np.abs(Bz_array))**2)),axis=(0, 1))
            data_sum = np.sum(np.abs(data), axis=(0, 1))
            simuladas_sum = np.sum(np.abs((np.abs(Bz_array))**2), axis=(0, 1))
            """# --- NUEVO: Cálculo de la métrica normalizada y actualización de máscara ---
            # Sumamos data_sum + simuladas_sum. Evitamos división por cero sumando un epsilon (1e-12)"""
            suma_total_led = data_sum + simuladas_sum + 1e-12
            metrica_error_normalizada = diferencias / suma_total_led
            # Actualizamos qué LEDs quedan congelados (True) y cuáles siguen activos (False)
            if congelar_leds:
                if metrica_anterior is not None:

                    # LEDs cuya métrica empeoró
                    empeoro = ((~leds_congelados) & (metrica_error_normalizada > 1.02 * metrica_anterior))

                    # Una vez congelado, queda congelado
                    leds_congelados |= empeoro
                    # for i in range(0, len(leds_congelados), L):
                    #     print(leds_congelados[i:i+L])            # Guardar la métrica para la próxima comparación
                metrica_anterior = metrica_error_normalizada.copy()
            """Si volvemos al sistema de iteraciones de  congelamiento"""
            # Actualizamos qué LEDs quedan congelados (True) y cuáles siguen activos (False)
            # if ndx > iteraciones_congelamiento:
            #     leds_congelados = metrica_error_normalizada < umbral_congelamiento
                # print(leds_congelados)
            for ((x, y), color), dif, dat, sim in zip(
                indices.keys(),
                diferencias,
                data_sum,
                simuladas_sum):
                registros.append({
                    "Iteracion": ndx,
                    "led_x": x,
                    "led_y": y,
                    "color": color, 
                    "Diferencia": dif,
                    "Data": dat,
                    "Simuladas": sim
                })        # ## Si se necesitan recopilar imágenes intermedias
        z_old = z.copy()
        w_old = w
    im_r = np.fft.ifft2(np.fft.ifftshift(z))

    return z0, im_r, recovery_errs_records, diccionario_records, imagenes_intermedias, phase_max_list, phase_min_list, pasos, registros, perfiles_radiales_records, perfil_target_record


def reconstruct_test(recovery_error_required,
        data: dict[tuple[int, int],npt.NDArray[np.float128]],
        hr_shape: tuple[int, int],
        sigma2: float,
        indices: npt.NDArray[np.intp],
        pupil: npt.NDArray[np.uint8],
        big_pupil,
        iterations: int,
        mu_max: float,
        weight: float,
        target: npt.NDArray[np.complex128],
        on_iteration: Callable[[int, npt.NDArray[np.complex128]], None],
        iteraciones_a_guardar,
        congelar_leds,
        update_pupil: bool = False,
        ) -> tuple[npt.NDArray[np.complex128], npt.NDArray[np.complex128], npt.NDArray[np.float64]]:
    """
    Algorithm 1: TPWFP algorithm for FP reconstruction.
    Input: linear transform matrix A, measurement vector c, and initialization z(0). 
    Ouput: retrieved complex signal z (the sample’s HR spatial spectrum). 
    1. k= 0;
    2. while not converged do
    3. Update ξ according to Eq. (9);
    4. Update μ(k+1) according to Eq. (12);
    5. Update z(k+1) according to Eq. (11);
    6. k :=k+ 1.
    7. end
    
    Parameters
    ----------
    data
        captured LR images (shape: n1_LR, n2_LR, L);
    n0, n1
        the pixel numbers of im_r (HR) in two dimensions.
    sigma2
        variance of additive noise.
    masks
        L * 2 (each point indicates the index of the left-upper point of the LR image in the HR spectrum).
    pupil
        the pupil function.
    iterations
        the number of iterations.
    mu_max
        the stepsize parameter.
    weight
        the weighting parameter.
    newfolder
        folder for saving results.
    target
        original benchmark HR spectrum for calculating recovery error.
    update_pupil
        si True, ademas del objeto se recupera la pupila (EPRY, Ou/Zheng/Yang
        2014), arrancando despues de warmup_iters. Default False: cero
        impacto en el resultado (ver pupilas_intermedias en el retorno).

    Returns
    -------
    z0, final recovered image, recovery erros vs iterations
    """
    n0, n1, L = data.shape
    lr_shape = int(n0), int(n1)
    z_im = np.sqrt(data[:,:,int(np.fix(L/2))]) * lr_shape[0] * lr_shape[1] / hr_shape[0] / hr_shape[1] 
    # z_im = np.sqrt(data[:, :, int(np.fix(L / 2))]) * n0_LR * n1_LR / n0 / n1

    z_im = skt.resize(z_im, hr_shape) 
    z0 = np.fft.fftshift(np.fft.fft2(z_im))
    z = z0.copy()

    recovery_errs = np.zeros(iterations)
    recovery_errs[0] = quality(z, target)
    N = np.zeros(data.shape)
    epsilon = N
    normest = np.sqrt(np.sum(data) / L / lr_shape[0] / lr_shape[1])
    
    step_size_n = 0.01
    alpha = - np.log(0.997)

    ## Si se necesitan recopilar imágenes intermedias
    imagenes_magnitud_200_300 = {}
    imagenes_fase_200_300 = {}
    recovery_errs_records = []
    imagenes_intermedias = {}
    imagenes_intermedias[0] = z_im
    phase_max_list = []
    phase_min_list = []
    warmup_iters = int(iterations * 0.05) # 10% de las iteraciones para calentar
    mu_dynamic = mu_max  # Empezamos con el máximo
    z_old = None
    w_old = None
    indices_stack = np.asarray(list(indices.values()))
    L = len(indices_stack)
    diccionario_records = []
    hito_1 = round(iterations * 1 / 9)
    hito_2 = round(iterations * 1 / 3)
    hito_3 = round(iterations * 3 / 5)
    hito_4 = round(iterations * 9 / 10)
    xx_c_buffer = np.empty((lr_shape[0], lr_shape[1], L),dtype=np.complex128)
    xx_mean_large = np.zeros(hr_shape, dtype=np.complex128)
    # --- EPRY: soporte binario original de la pupila, para restringir el
    # update a la apertura fisica real (ver Paso 3 del plan). Se captura
    # ANTES de convertir `pupil` a complejo, asi que siempre es la mascara
    # binaria pasada por el caller, sin importar update_pupil.
    pupil_support = pupil.astype(bool)
    if update_pupil:
        pupil = pupil.astype(np.complex128).copy()
    pupilas_intermedias = {}
    if update_pupil:
        pupilas_intermedias[0] = pupil.copy()
    pasos = []
    diferencias_LR = {}
    registros = []
    # --- ANTES DEL BUCLE DE ITERACIONES ---

    # Asumiendo que 'z' tiene frecuencias centradas (frecuencia 0 en el centro de la matriz)
    Ny, Nx = z.shape
    ky = np.linspace(-Ny//2, Ny//2 - 1, Ny)
    kx = np.linspace(-Nx//2, Nx//2 - 1, Nx)
    KX, KY = np.meshgrid(kx, ky)

    # Matriz 2D con el módulo k para cada píxel
    K_mag = np.sqrt(KX**2 + KY**2)
    # Redondeamos a enteros para poder usarlo como índices de agrupamiento (bins)
    K_int = np.round(K_mag).astype(int)

    # Precalculamos el número de píxeles que caen en cada radio k para el promedio
    conteo_radios = np.bincount(K_int.flatten())
    conteo_radios[conteo_radios == 0] = 1 # Para evitar advertencias de división por cero
    # --- ANTES DEL BUCLE ---
    # Transformamos el target al espacio de Fourier para tener el espectro ideal
    Z_target = np.fft.fftshift(np.fft.fft2(target))
    # Calculamos su perfil radial usando la misma lógica rápida
    perfiles_radiales_records = []
    perfil_radial_target = np.bincount(K_int.flatten(), weights=(np.abs(target*big_pupil)**2).flatten()) / conteo_radios
    perfil_target_record = []
    perfil_target_record.append(perfil_radial_target)
    # Diccionario donde guardaremos la historia del espectro
    espectros_radiales_records = {}
    """Intento de congelar informacion en el espectro de Fourier"""
    # --- NUEVO: Inicialización del sistema de congelamiento ---
    metrica_anterior = None
    leds_congelados = np.zeros(L, dtype=bool)
    umbral_congelamiento = 0.3  # Congela si el error normalizado baja del 90%
    for ndx in tqdm(range(1, iterations)):

        # # update z
        # Bz = linear_operator_vectorized(z, indices, lr_shape, pupil)
        # Bz_array = np.stack([Bz[key] for key in sorted(Bz.keys())], axis=-1)
        # Cz = (np.abs(Bz_array) ** 2 + N - data) * Bz_array  #eq 9 Bian 2016
        # w = inverse_linear_operator_real_images_vectorized(Cz, indices, hr_shape, pupil) #eq 10 Bian 2016 truncated Wirtinger gradient 

        # 1. Aplicamos el operador directo vectorizado (ya te devuelve un array 3D)
        Bz_array = linear_operator_vectorized(z, indices_stack, xx_c_buffer, pupil, L)
        
        # 2. Operaciones in-place para ahorrar memoria
        error_term = np.abs(Bz_array)
        error_term **= 2
        error_term += N
        error_term -= data
        Cz = error_term * Bz_array
        """# --- NUEVO: Apagar el gradiente de los LEDs congelados ---
        Esto hace que la diferencia entre la data y las imágenes simuladas sea cero
        por lo que no hay nada que agregar o cambiar en la imagen de HR en esas frecuencias"""
        Cz[:, :, leds_congelados] = 0
        # 3. Aplicamos el operador inverso pasándole el stack directamente
        # --- EPRY (Paso 3): si toca actualizar la pupila esta iteración,
        # pedimos también el xx_c ya transformado a Fourier LR para
        # reusarlo en accumulate_pupil_gradient sin duplicar la FFT.
        actualizar_pupila_este_paso = update_pupil and ndx > warmup_iters
        if actualizar_pupila_este_paso:
            w, xx_c_fft = inverse_linear_operator_real_images_vectorized(
                Cz, indices_stack, xx_mean_large, pupil, return_fft_xx_c=True
            )
        else:
            w = inverse_linear_operator_real_images_vectorized(Cz, indices_stack, xx_mean_large, pupil)

        # 1. Calculamos el mu base con tu warm-up actual
        # mu = np.float64(1 - np.exp(-alpha * ndx))
        mu = np.float64(1 - np.exp(-ndx/330))
        mu = np.minimum(mu, mu_max) / (normest ** 2)

        # if ndx == 1 or z_old is None:
        #     mu = mu_max / normest ** 2  # Paso inicial por defecto
        # else:
        #     s = z - z_old  # Diferencia de soluciones
        #     y = w - w_old  # Diferencia de gradientes (w es tu gradiente truncado)

        #     s_flat = s.ravel()
        #     y_flat = y.ravel()

        #     denom = np.real(np.vdot(s_flat, y_flat))
        #     if denom > 1e-12:
        #         # Ecuación clásica de Barzilai-Borwein
        #         mu_bb = np.real(np.vdot(s_flat, s_flat)) / denom
        #         # Guardrail para evitar pasos ridículamente grandes
        #         mu = min(mu_bb, mu_max * 10 / normest ** 2)
        #     else:
        #         mu = mu_max / normest ** 2


        # --- EPRY (Paso 3): update de la pupila, simétrico al de z, ANTES
        # de que z cambie (mismo z que generó Bz_array/Cz). mu_pupil = mu
        # por ahora (ver plan, ajustar si hace falta un paso propio).
        if actualizar_pupila_este_paso:
            pupil_grad, pupil_energy = accumulate_pupil_gradient(
                z, indices_stack, xx_c_fft, pupil.shape, return_energy=True
            )
            # Normalización global (no por-pixel, que dispara el update donde
            # |z_ventana| es casi cero) por la energía máxima -- estándar en
            # updates de sonda estilo ePIE/rPIE: grad /= max(|objeto|^2).
            pupil_grad /= (np.max(pupil_energy) + 1e-12)
            mu_pupil = 0.3 * mu

            # --- Trust region (en vez de confiar en que mu_pupil quedó bien
            # calibrado para CUALQUIER escala de problema): no existe una
            # constante que se haya podido validar de antemano para un
            # sistema con cientos de LEDs y datos reales de rango dinámico
            # desconocido -- ya vimos que 0.1x y 0.3x no alcanzan a acotar
            # el paso en ese régimen. En vez de seguir adivinando mu_pupil,
            # se acota el cambio POR ITERACIÓN a una fracción fija de la
            # amplitud típica actual de la pupila (5%), sin importar qué tan
            # mal escalado venga pupil_grad. Esto es invariante de escala por
            # construcción: no puede explotar en un solo paso, y sobre las
            # ~190 iteraciones activas el cambio total igual puede acumular
            # una corrección sustancial si la dirección es consistente.
            propuesta = pupil - mu_pupil * pupil_grad
            propuesta *= pupil_support
            if np.all(np.isfinite(propuesta)):
                escala_pupila = np.mean(np.abs(pupil[pupil_support])) + 1e-12
                cambio = propuesta - pupil
                cambio_max_por_pixel = 0.05 * escala_pupila
                factor_clip = np.minimum(1.0, cambio_max_por_pixel / (np.abs(cambio) + 1e-12))
                pupil = pupil + cambio * factor_clip
                pupil *= pupil_support
            # si propuesta trae NaN/Inf (gradiente mal escalado esta
            # iteración puntual), no tocamos la pupila -- se sigue con la
            # del paso anterior en vez de contaminarla para siempre.

        z -= mu * w  #eq 11 Bian 2016

        # update N
        CN = error_term + weight * (N * N - 9 * sigma2 + epsilon * epsilon) * 2.0 * N
        step_n = mu * step_size_n
        CN *= step_n
        N -= CN
        
        # update epsilon
        e_temp = 9 * sigma2 - N * N
        e_temp[e_temp < 0] = 0
        epsilon = np.sqrt(e_temp)
        recovery_errs[ndx] = quality(z, target)

        # qd = quality_dict(z, target)
        # qd["recovery_err"] = recovery_errs[ndx]

        # recovery_errs_records.append(qd)
        on_iteration(ndx, z)
        # fase = np.angle(np.fft.ifft2(np.fft.ifftshift(z.astype(np.complex128))).astype(np.complex128))/np.pi

        # phase_max_list.append(np.max(fase))
        # phase_min_list.append(np.min(fase))

        if recovery_error_required != 0:
            if ndx == hito_1 and recovery_errs[hito_1] > (recovery_error_required * 1.10):
                recovery_errs[hito_1:] = recovery_errs[ndx] 
                break
            elif ndx == hito_2 and recovery_errs[hito_2] > recovery_error_required:
                recovery_errs[hito_2:] = recovery_errs[ndx]
                break
            elif ndx == hito_3 and recovery_errs[hito_3] > (recovery_error_required * 0.90):
                recovery_errs[hito_3:] = recovery_errs[ndx] 
                break
            elif ndx == hito_4 and recovery_errs[hito_4] > (recovery_error_required * 0.10):
                recovery_errs[hito_4:] = recovery_errs[ndx]
                break

        # Si en un quinto de las iteraciones no llega a un error de corte se interrumpe el ciclo
        # if recovery_error_required != 0:

        #     if recovery_errs[round(iterations * 1/ 9)] > (recovery_error_required + 0.10 * recovery_error_required):
        #         recovery_errs[round(iterations * 1 / 9):] = recovery_errs[ndx]
        #         break  

        #     # if recovery_errs[round(iterations * 1/ 9)] > (recovery_error_required):
        #     #     recovery_errs[round(iterations * 1 / 9):] = recovery_errs[ndx]
        #     #     break  

        #     if recovery_errs[round(iterations * 1/ 3)] > (recovery_error_required):
        #         recovery_errs[round(iterations * 1 / 3):] = recovery_errs[ndx]
        #         break   

        #     # if recovery_errs[round(iterations * 1 / 3)] > (recovery_error_required - 0.10 * recovery_error_required):
        #     #     recovery_errs[round(iterations * 1 / 3):] = recovery_errs[ndx]
        #     #     break  

        #     if recovery_errs[round(iterations * 3 / 5)] > (recovery_error_required - 0.10 * recovery_error_required):
        #         recovery_errs[round(iterations * 3 / 5):] = recovery_errs[ndx]
        #         break   

        #     # if recovery_errs[round(iterations * 3 / 5)] > (recovery_error_required - 0.30 * recovery_error_required):
        #     #     recovery_errs[round(iterations * 3 / 5):] = recovery_errs[ndx]
        #     #     break   

        #     # Si en un quinto de las iteraciones no llega a un error de corte se interrumpe el ciclo
        #     if recovery_errs[round(iterations * 9/ 10)] > (recovery_error_required - 0.9 * recovery_error_required):
        #         recovery_errs[round(iterations * 9 / 10):] = recovery_errs[ndx]
        #         break   

        if ndx % iteraciones_a_guardar == 0:
            # 1. Calculamos la intensidad y perfil de 'z' (lo que vimos antes)
            suma_radial = np.bincount(K_int.flatten(), weights=(np.abs(z*big_pupil)**2).flatten())
            perfil_radial = suma_radial / conteo_radios
            
            # --- NUEVO: Comparación ---
            # 2. Calculamos el Error Cuadrático Medio entre el perfil actual y el ideal
            error_radial_mse = np.mean((perfil_radial - perfil_radial_target)**2)
            # --------------------------
            perfiles_radiales_records.append(perfil_radial)
            imagen = np.fft.ifft2(np.fft.ifftshift(z))
            imagenes_intermedias[ndx] = imagen
            fase = np.angle(imagen)/np.pi
            if update_pupil:
                pupilas_intermedias[ndx] = pupil.copy()

            phase_max_list.append(np.max(fase))
            phase_min_list.append(np.min(fase))
            
            qd_HR = quality_dict(z, target)
            qd_HR["recovery_err"] = recovery_errs[ndx]
            
            # --- NUEVO: Guardamos en el diccionario de calidad ---
            # qd_HR["perfil_radial"] = perfil_radial
            qd_HR["error_radial_mse"] = error_radial_mse
            # -----------------------------------------------------
            qd_LR = blind_quality_dict(z, lr_intensities_measured=data, lr_intensities_simulated=(np.abs(Bz_array))**2, x_old=z_old)
            qd_LR["recovery_err"] = recovery_errs[ndx]
            recovery_errs_records.append(qd_HR)
            diccionario_records.append(qd_LR)
            pasos.append(mu)
            diferencias = np.sum(np.abs(np.abs(data) - np.abs((np.abs(Bz_array))**2)),axis=(0, 1))
            data_sum = np.sum(np.abs(data), axis=(0, 1))
            simuladas_sum = np.sum(np.abs((np.abs(Bz_array))**2), axis=(0, 1))
            """# --- NUEVO: Cálculo de la métrica normalizada y actualización de máscara ---
            # Sumamos data_sum + simuladas_sum. Evitamos división por cero sumando un epsilon (1e-12)"""
            suma_total_led = data_sum + simuladas_sum + 1e-12
            metrica_error_normalizada = diferencias / suma_total_led
            # Actualizamos qué LEDs quedan congelados (True) y cuáles siguen activos (False)
            if congelar_leds:
                if metrica_anterior is not None:

                    # LEDs cuya métrica empeoró
                    empeoro = ((~leds_congelados) & (metrica_error_normalizada > 1.02 * metrica_anterior))

                    # Una vez congelado, queda congelado
                    leds_congelados |= empeoro
                    # for i in range(0, len(leds_congelados), L):
                    #     print(leds_congelados[i:i+L])            # Guardar la métrica para la próxima comparación
                metrica_anterior = metrica_error_normalizada.copy()
            """Si volvemos al sistema de iteraciones de  congelamiento"""
            # Actualizamos qué LEDs quedan congelados (True) y cuáles siguen activos (False)
            # if ndx > iteraciones_congelamiento:
            #     leds_congelados = metrica_error_normalizada < umbral_congelamiento
                # print(leds_congelados)
            for (x, y), dif, dat, sim in zip(
                indices.keys(),
                diferencias,
                data_sum,
                simuladas_sum):
                registros.append({
                    "Iteracion": ndx,
                    "led_x": x,
                    "led_y": y,
                    "Diferencia": dif,
                    "Data": dat,
                    "Simuladas": sim
                })        # ## Si se necesitan recopilar imágenes intermedias
        # if ndx > 240 and ndx < 399:
        #     imagen = np.fft.ifft2(np.fft.ifftshift(z))
        #     imagenes_magnitud_200_300[ndx] = np.abs(imagen)
        #     imagenes_fase_200_300[ndx] = np.angle(imagen)
        # Si necesitamos saber la velocidad con la que llega a cierto error
        # if recovery_errs[ndx] < 0.85:
        #     print (f"Iteracion {ndx}")
                # --- ¡CRUCIAL! Al final del for (justo antes de terminar el bucle ndx) ---
        z_old = z.copy()
        w_old = w
    im_r = np.fft.ifft2(np.fft.ifftshift(z))

    # ## Si se necesitan recopilar imágenes intermedias
    # carpeta_magnitud = "/home/chanoscopio/Documents/LucasC/code/ptyco-full-simulator/test/results/200_a_300_iteraciones/magnitud"
    # carpeta_fase = "/home/chanoscopio/Documents/LucasC/code/ptyco-full-simulator/test/results/200_a_300_iteraciones/fase"
    # save_images_2(imagenes_magnitud_200_300, carpeta_magnitud)
    # save_images_2(imagenes_fase_200_300, carpeta_fase)
    # ##

    return z0, im_r, recovery_errs_records, diccionario_records, imagenes_intermedias, phase_max_list, phase_min_list, pasos, registros, perfiles_radiales_records, perfil_target_record, pupilas_intermedias


def reconstruct_epry_paper(
        data: npt.NDArray[np.float64],
        hr_shape: tuple[int, int],
        indices: dict[tuple[int, int], tuple[int, int]],
        pupil_support: npt.NDArray[np.bool_],
        iterations: int,
        target: npt.NDArray[np.complex128],
        alpha: float = 1.0,
        beta: float = 1.0,
    ) -> tuple[npt.NDArray[np.complex128], npt.NDArray[np.complex128], list[float]]:
    """EPRY-FPM tal como está descripto en Ou, Zheng & Yang 2014 (Optics
    Express 22(5), 4960 -- "Embedded pupil function recovery for Fourier
    ptychographic microscopy"), Fig. 1 y Ecs. (2)-(4).

    A diferencia de `reconstruct_test` (Wirtinger flow truncado de Bian 2016,
    batched, con warmup y trust-region para la pupila -- ver EPRY_PLAN), este
    es el algoritmo PIE-style secuencial original: objeto y pupila se
    actualizan juntos desde la primera iteración, imagen por imagen, con
    alpha=beta=1 constantes y sin ningún período de calentamiento. Sirve como
    referencia "de libro" para comparar contra nuestra implementación real.

    pupil_support
        apertura binaria (soporte físico real, ver `create_pupil`). Se usa
        como guess inicial de la pupila (magnitud=soporte, fase=0, igual que
        el paper) y como restricción de ruido tras cada update (Sección 2).
    """
    n0, n1, L = data.shape
    lr_shape = (n0, n1)
    keys = list(indices.keys())
    data_por_key = {key: data[:, :, ndx] for ndx, key in enumerate(keys)}

    # Semilla del objeto: la primera imagen de la secuencia, sobremuestreada
    # (mismo criterio que el paper: "the first image ... is up-sampled and
    # Fourier transformed to serve as the initial sample spectrum guess").
    z_im = np.sqrt(np.maximum(data[:, :, 0], 0.0))
    z_im = skt.resize(z_im, hr_shape)
    z = np.fft.fftshift(np.fft.fft2(z_im)).astype(np.complex128)

    # Semilla de la pupila: soporte real, fase uniforme cero -- igual que el
    # paper ("the initial pupil function guess is set as a circular shape
    # low-pass filter, with all ones inside the pass band ... and uniform
    # zero phase").
    pupil = pupil_support.astype(np.complex128).copy()

    eps = 1e-12
    recovery_errs = []

    for _ in tqdm(range(iterations)):
        for key in keys:
            ndx0, ndx1 = indices[key]
            s0 = safe_slice_lo(ndx0 - n0 // 2, n0, 0, hr_shape[0])
            s1 = safe_slice_lo(ndx1 - n1 // 2, n1, 0, hr_shape[1])

            s_window = z[s0, s1]
            phi = pupil * s_window
            Phi = np.fft.ifft2(np.fft.ifftshift(phi))

            amp_medida = np.sqrt(np.maximum(data_por_key[key], 0.0))
            Phi_prima = amp_medida * Phi / (np.abs(Phi) + eps)  # Ec. (2)

            phi_prima = np.fft.fftshift(np.fft.fft2(Phi_prima))
            diff = phi_prima - phi

            denom_pupil = np.max(np.abs(pupil) ** 2) + eps
            denom_objeto = np.max(np.abs(s_window) ** 2) + eps

            s_window_nuevo = s_window + alpha * np.conj(pupil) / denom_pupil * diff  # Ec. (3)
            # Ec. (4): usa el s_window VIEJO (previo al update de arriba),
            # igual que el paper -- ambas ecs. parten del mismo par (phi, phi').
            pupil = pupil + beta * np.conj(s_window) / denom_objeto * diff
            pupil *= pupil_support  # restricción de soporte, elimina ruido fuera de la NA (Sección 2)

            z[s0, s1] = s_window_nuevo

        recovery_errs.append(quality(z, target))

    return z, pupil, recovery_errs


def reconstruct_real_images(
        recovery_error_cut,
        data: np.ndarray,  # ahora float32
        hr_shape: tuple[int, int],
        sigma2: float,
        indices: np.ndarray,
        pupil: np.ndarray,
        iterations: int,
        mu_max: float,
        weight: float,
        on_iteration: Callable[[int, np.ndarray], None]
    ) -> tuple[np.ndarray, np.ndarray]:

    """
    Optimized TPWFP algorithm for FP reconstruction (memory friendly).
    Now uses float32 and complex64 to reduce memory footprint.

    Parameters
    ----------
    data : np.ndarray (float32)
        captured LR images (shape: n1_LR, n2_LR, L);
    hr_shape : tuple[int,int]
        size of reconstructed HR image
    sigma2 : float
        variance of additive noise.
    indices : np.ndarray
        frequency indices for reconstruction
    pupil : np.ndarray
        pupil function.
    iterations : int
        number of iterations.
    mu_max : float
        stepsize parameter.
    weight : float
        weighting parameter.
    on_iteration : Callable
        callback for each iteration

    Returns
    -------
    z0 : complex64
        initial HR spectrum
    im_r : complex64
        final recovered image (HR)
    """

    # --- Ensure input is float64 ---
    # data = data.astype(np.float64)

    n0, n1, L = data.shape
    lr_shape = (int(n0), int(n1))

    # Inicialización z_im → HR size
    z_im = np.sqrt(data[:, :, int(np.fix(L/2))]) * \
           (lr_shape[0] * lr_shape[1]) / (hr_shape[0] * hr_shape[1])

    # Resize to HR shape
    z_im = skt.resize(z_im, hr_shape).astype(np.float64)

    # FFT inicial en precision simple
    z0 = np.fft.fftshift(np.fft.fft2(z_im.astype(np.complex128)))
    z = z0.copy()

    # Arrays auxiliares en float32
    # recovery_errs = np.zeros(iterations, dtype=np.float64)
    N = np.zeros(data.shape, dtype=np.float64)
    epsilon = np.zeros_like(N, dtype=np.float64)

    # Norm estimation 
    normest = np.sqrt(np.sum(data, dtype=np.float64) / L / lr_shape[0] / lr_shape[1]).astype(np.float64)

    step_size_n = np.float64(0.01)
    alpha = np.float64(- np.log(0.997))

    # Si se necesitan imágenes intermedias (desactivado por ahora)
    imagenes_intermedias = {}
    phase_max_list = []
    phase_min_list = []
    diccionario_records = []

    for ndx in tqdm(range(1, iterations)):

        # update z (linear operator)
        Bz = linear_operator(z, indices, lr_shape, pupil)

        # 
        Bz_array = np.stack([Bz[key] for key in sorted(Bz.keys())], axis=-1).astype(np.complex128)

        Cz = ((np.abs(Bz_array))**2 + N - data) * Bz_array

        # Wirtinger gradient
        w = inverse_linear_operator_real_images(Cz, indices, hr_shape, pupil).astype(np.complex128)

        # step mu
        mu = np.float64(1 - np.exp(-alpha * ndx))
        mu = np.minimum(mu, mu_max) / (normest ** 2)
        if ndx > 40:
            # Opción A: Reducción exponencial (suave)
            mu = mu * (0.95 ** (ndx - 40))

        # update z 
        z = z - mu * w

        # update N
        CN = ((np.abs(Bz_array))**2 + N - data) + weight * (N * N - 9 * sigma2 + epsilon * epsilon) * np.float64(2.0) * N
        step_n = mu * step_size_n
        N = N - step_n * CN

        # update epsilon
        e_temp = 9 * sigma2 - N * N
        e_temp[e_temp < 0] = 0
        epsilon = np.sqrt(e_temp, dtype=np.float64)

        # Callback opcional
        on_iteration(ndx, z)
        fase = np.angle(np.fft.ifft2(np.fft.ifftshift(z.astype(np.complex128))).astype(np.complex128))

        phase_max_list.append(np.max(fase))
        phase_min_list.append(np.min(fase))
        ## Si se necesitan recopilar imágenes intermedias
        if ndx % 1000 == 0:
            imagen = np.fft.ifft2(np.fft.ifftshift(z.astype(np.complex128))).astype(np.complex128)
            imagenes_intermedias[ndx] = imagen
            qd = blind_quality_dict(z)
            diccionario_records.append(qd)
            # imagenes_fase_intermedias[ndx] = np.angle(imagen)
        #Si necesitamos saber la velocidad con la que llega a cierto error
        # if recovery_errs[ndx] < 0.85:
        #     print (f"Iteracion {ndx}")


    ## Si se necesitan recopilar imágenes intermedias
    # carpeta_magnitud = "/home/chanoscopio/Documents/LucasC/code/ptyco-full-simulator/test/results/200_a_300_iteraciones/magnitud"
    # carpeta_fase = "/home/chanoscopio/Documents/LucasC/code/ptyco-full-simulator/test/results/200_a_300_iteraciones/fase"
    # save_images_2(imagenes_magnitud_intermedias, carpeta_magnitud)
    # save_images_2(imagenes_fase_intermedias, carpeta_fase)
    ##

    # Recovered HR image (IFFT en complex64)
    im_r = np.fft.ifft2(np.fft.ifftshift(z.astype(np.complex128))).astype(np.complex128)

    return z0.astype(np.complex128), im_r.astype(np.complex128),diccionario_records, imagenes_intermedias, phase_max_list, phase_min_list


def reconstruct_real_images_test_integral(
        recovery_error_cut: float,
        data: np.ndarray,  # Usualmente float64 internamente
        hr_shape: tuple[int, int],
        sigma2: float,
        indices: dict, # Cambiado a dict para coincidir con tu uso interno de .keys() y .values()
        pupil: np.ndarray,
        iterations: int,
        mu_max: float,
        weight: float,
        on_iteration: Callable[[int, np.ndarray], None], 
        iteraciones_a_guardar: int,
        congelar_leds= False
    ) -> tuple:
    """
    Optimized TPWFP algorithm for FP reconstruction of real data.
    Aligned with the simulated architecture, tracking radial profiles 
    and blind metrics.
    """
    n0, n1, L = data.shape
    lr_shape = (int(n0), int(n1))

    # Inicialización z_im
    z_im = np.sqrt(data[:, :, int(np.fix(L/2))]) * \
           (lr_shape[0] * lr_shape[1]) / (hr_shape[0] * hr_shape[1])

    # Resize to HR shape
    z_im = skt.resize(z_im, hr_shape)

    # FFT inicial
    z0 = np.fft.fftshift(np.fft.fft2(z_im))
    z = z0.copy()

    # Arrays auxiliares
    N = np.zeros(data.shape, dtype=np.float64)
    epsilon = np.zeros_like(N)

    # Norm estimation 
    normest = np.sqrt(np.sum(data) / L / lr_shape[0] / lr_shape[1])

    step_size_n = 0.01

    imagenes_intermedias = {}
    phase_max_list = []
    phase_min_list = []
    z_old = None
    
    indices_stack = np.asarray(list(indices.values()))
    L = len(indices_stack)
    diccionario_records = []
    pasos = []
    registros = []
    perfiles_radiales_records = []

    # --- HITOS DE CORTE TEMPRANO ---
    hito_1 = round(iterations * 1 / 9)
    hito_2 = round(iterations * 1 / 3)
    hito_3 = round(iterations * 3 / 5)
    hito_4 = round(iterations * 9 / 10)

    xx_c_buffer = np.empty((lr_shape[0], lr_shape[1], L), dtype=np.complex128)
    xx_mean_large = np.zeros(hr_shape, dtype=np.complex128)

    # --- ANTES DEL BUCLE: Preparación de Perfiles Radiales ---
    Ny, Nx = z.shape
    ky = np.linspace(-Ny//2, Ny//2 - 1, Ny)
    kx = np.linspace(-Nx//2, Nx//2 - 1, Nx)
    KX, KY = np.meshgrid(kx, ky)

    # Matriz 2D con el módulo k para cada píxel
    K_mag = np.sqrt(KX**2 + KY**2)
    K_int = np.round(K_mag).astype(int)

    # Precalculamos el número de píxeles que caen en cada radio k
    conteo_radios = np.bincount(K_int.flatten())
    conteo_radios[conteo_radios == 0] = 1 # Evitar división por cero
    metrica_anterior = None
    leds_congelados = np.zeros(L, dtype=bool)

    for ndx in tqdm(range(1, iterations)):
        # 1. Operador directo vectorizado
        Bz_array = linear_operator_vectorized(z, indices_stack, xx_c_buffer, pupil, L)

        # 2. Operaciones in-place para ahorrar memoria
        error_term = np.abs(Bz_array)
        error_term **= 2
        error_term += N
        error_term -= data
        Cz = error_term * Bz_array
        """# --- NUEVO: Apagar el gradiente de los LEDs congelados ---
        Esto hace que la diferencia entre la data y las imágenes simuladas sea cero
        por lo que no hay nada que agregar o cambiar en la imagen de HR en esas frecuencias"""
        Cz[:, :, leds_congelados] = 0
        
        # 3. Operador inverso
        w = inverse_linear_operator_real_images_vectorized(Cz, indices_stack, xx_mean_large, pupil)

        # step mu (Calentamiento exponencial estándar)
        mu = np.float64(1 - np.exp(-ndx/330))
        mu = np.minimum(mu, mu_max) / (normest ** 2)

        # update z 
        z -= mu * w

        # update N (Reutilizando error_term para máximo rendimiento)
        CN = error_term + weight * (N * N - 9 * sigma2 + epsilon * epsilon) * 2.0 * N
        step_n = mu * step_size_n
        CN *= step_n
        N -= CN

        # update epsilon
        e_temp = 9 * sigma2 - N * N
        e_temp[e_temp < 0] = 0
        epsilon = np.sqrt(e_temp)

        on_iteration(ndx, z)

        # --- SECCIÓN DE MÉTRICAS Y GUARDADO ---
        if ndx % iteraciones_a_guardar == 0:
            # Cálculo de perfil radial ciego
            suma_radial = np.bincount(K_int.flatten(), weights=(np.abs(z)**2).flatten())
            perfil_radial = suma_radial / conteo_radios
            perfiles_radiales_records.append(perfil_radial)

            imagen = np.fft.ifft2(np.fft.ifftshift(z))
            imagenes_intermedias[ndx] = imagen
            fase = np.angle(imagen) / np.pi

            phase_max_list.append(np.max(fase))
            phase_min_list.append(np.min(fase))

            # Evaluación ciega
            qd = blind_quality_dict(z, lr_intensities_measured=data, lr_intensities_simulated=(np.abs(Bz_array))**2, x_old=z_old)
            # qd["perfil_radial"] = perfil_radial
            diccionario_records.append(qd)
            pasos.append(mu)

            diferencias = np.sum(np.abs(np.abs(data) - np.abs((np.abs(Bz_array))**2)), axis=(0, 1))
            data_sum = np.sum(np.abs(data), axis=(0, 1))
            simuladas_sum = np.sum(np.abs((np.abs(Bz_array))**2), axis=(0, 1))
            suma_total_led = data_sum + simuladas_sum + 1e-12
            metrica_error_normalizada = diferencias / suma_total_led

            if congelar_leds:
                if metrica_anterior is not None:
                    empeoro = (
                        (~leds_congelados) &
                        (metrica_error_normalizada > 1.02 * metrica_anterior)
                    )

                    leds_congelados |= empeoro

                metrica_anterior = metrica_error_normalizada.copy()
            for ((x, y), color), dif, dat, sim in zip(indices.keys(), diferencias, data_sum, simuladas_sum):
                registros.append({
                    "Iteracion": ndx,
                    "led_x": x,
                    "led_y": y,
                    "color": color, 
                    "Diferencia": dif,
                    "Data": dat,
                    "Simuladas": sim
                })

            # Early stopping basado en error ciego (opcional)
            if recovery_error_cut != 0:
                current_err = qd.get("reprojection_data_error", float('inf'))
                if ndx == hito_1 and current_err > (recovery_error_cut * 1.10):
                    break
                elif ndx == hito_2 and current_err > recovery_error_cut:
                    break
                elif ndx == hito_3 and current_err > (recovery_error_cut * 0.90):
                    break
                elif ndx == hito_4 and current_err > (recovery_error_cut * 0.10):
                    break

        z_old = z.copy()

    # Recovered HR image 
    im_r = np.fft.ifft2(np.fft.ifftshift(z))

    return z0, im_r, diccionario_records, imagenes_intermedias, phase_max_list, phase_min_list, pasos, registros, perfiles_radiales_records

def reconstruct_real_images_test(
        recovery_error_cut: float,
        data: np.ndarray,  # Usualmente float64 internamente
        hr_shape: tuple[int, int],
        sigma2: float,
        indices: dict, # Cambiado a dict para coincidir con tu uso interno de .keys() y .values()
        pupil: np.ndarray,
        iterations: int,
        mu_max: float,
        weight: float,
        on_iteration: Callable[[int, np.ndarray], None], 
        iteraciones_a_guardar: int,
        congelar_leds= False
    ) -> tuple:
    """
    Optimized TPWFP algorithm for FP reconstruction of real data.
    Aligned with the simulated architecture, tracking radial profiles 
    and blind metrics.
    """
    n0, n1, L = data.shape
    lr_shape = (int(n0), int(n1))

    # Inicialización z_im
    z_im = np.sqrt(data[:, :, int(np.fix(L/2))]) * \
           (lr_shape[0] * lr_shape[1]) / (hr_shape[0] * hr_shape[1])

    # Resize to HR shape
    z_im = skt.resize(z_im, hr_shape)

    # FFT inicial
    z0 = np.fft.fftshift(np.fft.fft2(z_im))
    z = z0.copy()

    # Arrays auxiliares
    N = np.zeros(data.shape, dtype=np.float64)
    epsilon = np.zeros_like(N)

    # Norm estimation 
    normest = np.sqrt(np.sum(data) / L / lr_shape[0] / lr_shape[1])

    step_size_n = 0.01

    imagenes_intermedias = {}
    phase_max_list = []
    phase_min_list = []
    z_old = None
    
    indices_stack = np.asarray(list(indices.values()))
    L = len(indices_stack)
    diccionario_records = []
    pasos = []
    registros = []
    perfiles_radiales_records = []

    # --- HITOS DE CORTE TEMPRANO ---
    hito_1 = round(iterations * 1 / 9)
    hito_2 = round(iterations * 1 / 3)
    hito_3 = round(iterations * 3 / 5)
    hito_4 = round(iterations * 9 / 10)

    xx_c_buffer = np.empty((lr_shape[0], lr_shape[1], L), dtype=np.complex128)
    xx_mean_large = np.zeros(hr_shape, dtype=np.complex128)

    # --- ANTES DEL BUCLE: Preparación de Perfiles Radiales ---
    Ny, Nx = z.shape
    ky = np.linspace(-Ny//2, Ny//2 - 1, Ny)
    kx = np.linspace(-Nx//2, Nx//2 - 1, Nx)
    KX, KY = np.meshgrid(kx, ky)

    # Matriz 2D con el módulo k para cada píxel
    K_mag = np.sqrt(KX**2 + KY**2)
    K_int = np.round(K_mag).astype(int)

    # Precalculamos el número de píxeles que caen en cada radio k
    conteo_radios = np.bincount(K_int.flatten())
    conteo_radios[conteo_radios == 0] = 1 # Evitar división por cero
    metrica_anterior = None
    leds_congelados = np.zeros(L, dtype=bool)

    for ndx in tqdm(range(1, iterations)):
        # 1. Operador directo vectorizado
        Bz_array = linear_operator_vectorized(z, indices_stack, xx_c_buffer, pupil, L)

        # 2. Operaciones in-place para ahorrar memoria
        error_term = np.abs(Bz_array)
        error_term **= 2
        error_term += N
        error_term -= data
        Cz = error_term * Bz_array
        """# --- NUEVO: Apagar el gradiente de los LEDs congelados ---
        Esto hace que la diferencia entre la data y las imágenes simuladas sea cero
        por lo que no hay nada que agregar o cambiar en la imagen de HR en esas frecuencias"""
        Cz[:, :, leds_congelados] = 0
        
        # 3. Operador inverso
        w = inverse_linear_operator_real_images_vectorized(Cz, indices_stack, xx_mean_large, pupil)

        # step mu (Calentamiento exponencial estándar)
        mu = np.float64(1 - np.exp(-ndx/330))
        mu = np.minimum(mu, mu_max) / (normest ** 2)

        # update z 
        z -= mu * w

        # update N (Reutilizando error_term para máximo rendimiento)
        CN = error_term + weight * (N * N - 9 * sigma2 + epsilon * epsilon) * 2.0 * N
        step_n = mu * step_size_n
        CN *= step_n
        N -= CN

        # update epsilon
        e_temp = 9 * sigma2 - N * N
        e_temp[e_temp < 0] = 0
        epsilon = np.sqrt(e_temp)

        on_iteration(ndx, z)

        # --- SECCIÓN DE MÉTRICAS Y GUARDADO ---
        if ndx % iteraciones_a_guardar == 0:
            # Cálculo de perfil radial ciego
            suma_radial = np.bincount(K_int.flatten(), weights=(np.abs(z)**2).flatten())
            perfil_radial = suma_radial / conteo_radios
            perfiles_radiales_records.append(perfil_radial)

            imagen = np.fft.ifft2(np.fft.ifftshift(z))
            imagenes_intermedias[ndx] = imagen
            fase = np.angle(imagen) / np.pi

            phase_max_list.append(np.max(fase))
            phase_min_list.append(np.min(fase))

            # Evaluación ciega
            qd = blind_quality_dict(z, lr_intensities_measured=data, lr_intensities_simulated=(np.abs(Bz_array))**2, x_old=z_old)
            # qd["perfil_radial"] = perfil_radial
            diccionario_records.append(qd)
            pasos.append(mu)

            diferencias = np.sum(np.abs(np.abs(data) - np.abs((np.abs(Bz_array))**2)), axis=(0, 1))
            data_sum = np.sum(np.abs(data), axis=(0, 1))
            simuladas_sum = np.sum(np.abs((np.abs(Bz_array))**2), axis=(0, 1))
            suma_total_led = data_sum + simuladas_sum + 1e-12
            metrica_error_normalizada = diferencias / suma_total_led

            if congelar_leds:
                if metrica_anterior is not None:
                    empeoro = (
                        (~leds_congelados) &
                        (metrica_error_normalizada > 1.02 * metrica_anterior)
                    )

                    leds_congelados |= empeoro

                metrica_anterior = metrica_error_normalizada.copy()
            for (x, y), dif, dat, sim in zip(indices.keys(), diferencias, data_sum, simuladas_sum):
                registros.append({
                    "Iteracion": ndx,
                    "led_x": x,
                    "led_y": y,
                    "Diferencia": dif,
                    "Data": dat,
                    "Simuladas": sim
                })

            # Early stopping basado en error ciego (opcional)
            if recovery_error_cut != 0:
                current_err = qd.get("reprojection_data_error", float('inf'))
                if ndx == hito_1 and current_err > (recovery_error_cut * 1.10):
                    break
                elif ndx == hito_2 and current_err > recovery_error_cut:
                    break
                elif ndx == hito_3 and current_err > (recovery_error_cut * 0.90):
                    break
                elif ndx == hito_4 and current_err > (recovery_error_cut * 0.10):
                    break

        z_old = z.copy()

    # Recovered HR image 
    im_r = np.fft.ifft2(np.fft.ifftshift(z))

    return z0, im_r, diccionario_records, imagenes_intermedias, phase_max_list, phase_min_list, pasos, registros, perfiles_radiales_records

"""funcion sin optimizar la memoria RAM"""
# def reconstruct_real_images(recovery_error_cut,
#         data: dict[tuple[int, int],npt.NDArray[np.float128]],
#         hr_shape: tuple[int, int],
#         sigma2: float,
#         indices: npt.NDArray[np.intp],
#         pupil: npt.NDArray[np.uint8],
#         iterations: int,
#         mu_max: float,
#         weight: float,
#         on_iteration: Callable[[int, npt.NDArray[np.complex128]], None]
#         ) -> tuple[npt.NDArray[np.complex128], npt.NDArray[np.complex128], npt.NDArray[np.float64]]: 
#     """
#     Algorithm 1: TPWFP algorithm for FP reconstruction. 
#     Input: linear transform matrix A, measurement vector c, and initialization z(0). 
#     Ouput: retrieved complex signal z (the sample’s HR spatial spectrum). 
#     1. k= 0;
#     2. while not converged do
#     3. Update ξ according to Eq. (9);
#     4. Update μ(k+1) according to Eq. (12);
#     5. Update z(k+1) according to Eq. (11);
#     6. k :=k+ 1.
#     7. end
    
#     Parameters
#     ----------
#     data
#         captured LR images (shape: n1_LR, n2_LR, L);
#     n0, n1
#         the pixel numbers of im_r (HR) in two dimensions.
#     sigma2
#         variance of additive noise.
#     masks
#         L * 2 (each point indicates the index of the left-upper point of the LR image in the HR spectrum).
#     pupil
#         the pupil function.
#     iterations
#         the number of iterations.
#     mu_max
#         the stepsize parameter.
#     weight
#         the weighting parameter.
#     newfolder
#         folder for saving results.
#     target
#         original benchmark HR spectrum for calculating recovery error.

#     Returns
#     -------
#     z0, final recovered image, recovery erros vs iterations
#     """
#     n0, n1, L = data.shape
#     lr_shape = int(n0), int(n1)
#     z_im = np.sqrt(data[:,:,int(np.fix(L/2))]) * lr_shape[0] * lr_shape[1] / hr_shape[0] / hr_shape[1] 
#     # z_im = np.sqrt(data[:, :, int(np.fix(L / 2))]) * n0_LR * n1_LR / n0 / n1

#     z_im = skt.resize(z_im, hr_shape) 
#     z0 = np.fft.fftshift(np.fft.fft2(z_im))
#     z = z0

#     recovery_errs = np.zeros(iterations)
#     N = np.zeros(data.shape)
#     epsilon = N
#     normest = np.sqrt(np.sum(data) / L / lr_shape[0] / lr_shape[1])
    
#     step_size_n = 0.01
#     alpha = - np.log(0.997)

#     ## Si se necesitan recopilar imágenes intermedias
#     imagenes_magnitud_200_300 = {}
#     imagenes_fase_200_300 = {}
#     recovery_errs_records = []
#     for ndx in tqdm(range(1, iterations)):

#         # update z
#         Bz = linear_operator(z, indices, lr_shape, pupil)
#         Bz_array = np.stack([Bz[key] for key in sorted(Bz.keys())], axis=-1)
#         Cz = (np.abs(Bz_array) ** 2 + N - data) * Bz_array  #eq 9 Bian 2016
#         w = inverse_linear_operator(Cz, indices, hr_shape, pupil) #eq 10 Bian 2016 truncated Wirtinger gradient 
        
#         mu = 1 - np.exp(- alpha * ndx)  
#         mu = min(mu, mu_max) / normest ** 2 #eq 12 Bian 2016

#         z = z - mu * w  #eq 11 Bian 2016

#         # update N
#         CN = (np.abs(Bz_array) ** 2 + N - data) + weight * (N * N - 9 * sigma2 + epsilon * epsilon) * 2.0 * N
#         step_n = mu * step_size_n
#         N = N - step_n * CN
        
#         # update epsilon
#         e_temp = 9 * sigma2 - N * N
#         e_temp[e_temp < 0] = 0
#         epsilon = np.sqrt(e_temp)


#         on_iteration(ndx, z)


#         # Si en un quinto de las iteraciones no llega a un error de corte se interrumpe el ciclo
#         # if recovery_error_required != 0:

#         #     if recovery_errs[round(iterations * 1/ 9)] > (recovery_error_required + 0.10 * recovery_error_required):
#         #         recovery_errs[round(iterations * 1 / 9):] = recovery_errs[ndx]
#         #         break  

#         #     # if recovery_errs[round(iterations * 1/ 9)] > (recovery_error_required):
#         #     #     recovery_errs[round(iterations * 1 / 9):] = recovery_errs[ndx]
#         #     #     break  

#         #     if recovery_errs[round(iterations * 1/ 3)] > (recovery_error_required):
#         #         recovery_errs[round(iterations * 1 / 3):] = recovery_errs[ndx]
#         #         break   

#         #     # if recovery_errs[round(iterations * 1 / 3)] > (recovery_error_required - 0.10 * recovery_error_required):
#         #     #     recovery_errs[round(iterations * 1 / 3):] = recovery_errs[ndx]
#         #     #     break  

#         #     if recovery_errs[round(iterations * 3 / 5)] > (recovery_error_required - 0.10 * recovery_error_required):
#         #         recovery_errs[round(iterations * 3 / 5):] = recovery_errs[ndx]
#         #         break   

#             # if recovery_errs[round(iterations * 3 / 5)] > (recovery_error_required - 0.30 * recovery_error_required):
#             #     recovery_errs[round(iterations * 3 / 5):] = recovery_errs[ndx]
#             #     break   

#             # Si en un quinto de las iteraciones no llega a un error de corte se interrumpe el ciclo
#             # if recovery_errs[round(iterations * 9/ 10)] > (recovery_error_required - 0.9 * recovery_error_required):
#             #     recovery_errs[round(iterations * 9 / 10):] = recovery_errs[ndx]
#             #     break   

#         # ## Si se necesitan recopilar imágenes intermedias
#         # if ndx > 240 and ndx < 399:
#         #     imagen = np.fft.ifft2(np.fft.ifftshift(z))
#         #     imagenes_magnitud_200_300[ndx] = np.abs(imagen)
#         #     imagenes_fase_200_300[ndx] = np.angle(imagen)
#         # Si necesitamos saber la velocidad con la que llega a cierto error
#         # if recovery_errs[ndx] < 0.85:
#         #     print (f"Iteracion {ndx}")
#     im_r = np.fft.ifft2(np.fft.ifftshift(z))

#     # ## Si se necesitan recopilar imágenes intermedias
#     # carpeta_magnitud = "/home/chanoscopio/Documents/LucasC/code/ptyco-full-simulator/test/results/200_a_300_iteraciones/magnitud"
#     # carpeta_fase = "/home/chanoscopio/Documents/LucasC/code/ptyco-full-simulator/test/results/200_a_300_iteraciones/fase"
#     # save_images_2(imagenes_magnitud_200_300, carpeta_magnitud)
#     # save_images_2(imagenes_fase_200_300, carpeta_fase)
#     # ##

#     return z0, im_r


def convertir_matrices_a_imagenes(input_folder, output_folder):
    # Crear la carpeta de salida si no existe
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Recorrer todos los archivos en la carpeta de entrada
    for filename in os.listdir(input_folder):
        if filename.endswith('.npy'):
            # Cargar la matriz
            matriz = np.load(os.path.join(input_folder, filename))
            
            # Normalizar los valores para que estén en el rango 0-255 (si es necesario)
            matriz_normalizada = (255 * (matriz - np.min(matriz)) / (np.max(matriz) - np.min(matriz))).astype(np.uint8)

            # Convertir la matriz normalizada a imagen y guardarla
            imagen = Image.fromarray(matriz_normalizada)
            nombre_salida = os.path.splitext(filename)[0] + '.png'
            imagen.save(os.path.join(output_folder, nombre_salida))
            print(f'Imagen guardada como {nombre_salida}')
    return "Listo"


def euler_angles_incorporated(a: float, b: float, g: float, coordenadas: RealSpace3):
    """Trabajamos con la rotación extrínseca de los ángulos de Euler siguiendo las rotaciones alrededor de ejes fijos, primero sobre z con gamma, luego en y con beta y finalmente en x con alpha.
    """
    alpha = (-1) * np.deg2rad(a)
    beta = (-1) * np.deg2rad(b)
    gamma = (-1) * np.deg2rad(g)
    x, y, z = coordenadas
    x_led = (np.cos(beta) * np.cos(gamma)) * x + (np.sin(alpha) * np.sin(beta) * np.cos(gamma) - np.cos(alpha) * np.sin(gamma)) * y + (np.cos(alpha) * np.sin(beta) * np.cos(gamma) + np.sin(alpha) * np.sin(gamma)) * z
    y_led = (np.cos(beta) * np.sin(gamma)) * x + (np.sin(alpha) * np.sin(beta) * np.sin(gamma) + np.cos(alpha) * np.cos(gamma)) * y + (np.cos(alpha) * np.sin(beta) * np.sin(gamma) - np.sin(alpha) * np.cos(gamma)) * z
    z_led = (-np.sin(beta)) * x     + (np.sin(alpha) * np.cos(beta)) * y              + (np.cos(alpha) * np.cos(beta)) * z

    return (x_led, y_led, z_led)

def sample_tilt_incorporated(vector_de_onda: FourierSpace3, tilt: float):
    beta = (-1) * np.deg2rad(tilt)
    vector = np.asarray((vector_de_onda[0], vector_de_onda[1] * np.cos(beta) + vector_de_onda[2] * np.sin(beta), vector_de_onda[2] * np.cos(beta) - vector_de_onda[1] * np.sin(beta)))
    return vector

def calculate_k_vectors_k_indices_sample_tilt_integral(led_positions: dict[tuple[int, int], RealSpace3],
                                info, sample_position, dc_location, fourier_pixel_factor, sample_tilt, h_error) -> (dict, dict):
    k_vectors = {}
    k_vectors_tilt = {}
    k_pixels = {}
    k_indices = {}
    for key, led_position in led_positions.items():
        k_vectors[key] = calculate_k_vector(led_position, info['wave'], sample_position, h_error)
    for key, k_vector in k_vectors.items():
        k_vectors_tilt[key] = sample_tilt_incorporated(k_vector, sample_tilt)    
    for key, k_vector in k_vectors_tilt.items():
        k_pixels[key] = dc_location + k_vector[:2] / (2 * np.pi * fourier_pixel_factor)
    for key, k_pixel in k_pixels.items():
        k_indices[key] = construir_indices(k_pixel)
    return k_vectors_tilt, k_indices

def calculate_k_vectors_k_indices_sample_tilt(led_positions: dict[tuple[int, int], RealSpace3],
                                wavelength, sample_position, dc_location, fourier_pixel_factor, sample_tilt, h_error) -> (dict, dict):
    k_vectors = {}
    k_vectors_tilt = {}
    k_pixels = {}
    k_indices = {}
    for key, led_position in led_positions.items():
        k_vectors[key] = calculate_k_vector(led_position, wavelength, sample_position, h_error)
    for key, k_vector in k_vectors.items():
        k_vectors_tilt[key] = sample_tilt_incorporated(k_vector, sample_tilt)    
    for key, k_vector in k_vectors_tilt.items():
        k_pixels[key] = dc_location + k_vector[:2] / (2 * np.pi * fourier_pixel_factor)
    for key, k_pixel in k_pixels.items():
        k_indices[key] = construir_indices(k_pixel)
    return k_vectors_tilt, k_indices

def led_spacing_error_incorporated(led_spacing_error: float, coordenadas: RealSpace3):
    x, y, z = coordenadas   
    x_led = x + np.random.choice([-1, 0, 1]) * led_spacing_error
    y_led = y + np.random.choice([-1, 0, 1]) * led_spacing_error
    z_led = z + np.random.choice([-1, 0, 1]) * led_spacing_error 
    return (x_led, y_led, z_led)

def led_offset_incorporated(x_offset:float, y_offset: float, coordenadas: RealSpace3):
    x, y, z = coordenadas
    x_led = x + x_offset
    y_led = y + y_offset
    z_led = z
    return (x_led, y_led, z_led)

def led_errors_incorporated(led_positions, x_offset, y_offset, led_spacing_error, led_alpha, led_beta, led_gamma):
    led_positions_offset = {}
    for key, coordenada in led_positions.items():
        led_positions_offset[key] = led_offset_incorporated(x_offset, y_offset, coordenada)

    led_positions_failed = {}
    for key, coordenada in led_positions_offset.items():
        led_positions_failed[key] = led_spacing_error_incorporated(led_spacing_error, coordenada)

    led_positions_tilt = {}
    for key, coordenada in led_positions_failed.items():
        led_positions_tilt[key] = euler_angles_incorporated(led_alpha, led_beta, led_gamma, coordenada)
    
    return led_positions_tilt

def plot_convergence(result_list, true_minimum=None, yscale=None, title="Convergence plot"):

    ax = plt.gca()
    ax.set_title(title)
    ax.set_xlabel("Number of calls $n$")
    ax.set_ylabel(r"$\min f(x)$ after $n$ calls")
    ax.grid()
    if yscale is not None:
        ax.set_yscale(yscale)
    colors = cm.hsv(np.linspace(0.25, 1.0, len(result_list)))

    for entry, color in zip(result_list, colors):
        name, results = entry
        n_calls = len(results.x_iters)
        iterations = range(1, n_calls + 1)
        mins = [np.min(results.func_vals[:i]) for i in iterations]
        ax.plot(iterations, mins, c=color, label=name)
        #ax.errorbar(iterations, np.mean(mins, axis=0),
        #             yerr=np.std(mins, axis=0), c=color, label=name)
    if true_minimum:
        ax.axhline(true_minimum, linestyle="--",
                   color="r", lw=1,
                   label="True minimum")
    ax.legend(loc="best")
    return ax

def read_numpy_file(numpy_file):
    pass

def extraer_parametros(filename: str) -> dict:
    """
    Extrae parámetros en formato clave_valor desde el nombre de un archivo.
    
    Args:
        filename (str): nombre del archivo
    
    Returns:
        dict: diccionario con los parámetros encontrados
    """
    # Patrón: busca clave_valor donde valor puede ser int, float o notación científica
    pattern = re.compile(r'([a-zA-Z]+(?:_[a-zA-Z]+)*)_(-?\d+(?:\.\d+)?(?:e-?\d+)?)')

    # Extraer pares clave-valor
    matches = dict(pattern.findall(filename))

    # Convertir a int o float según corresponda
    for k, v in matches.items():
        if "e" in v or "." in v:
            matches[k] = float(v)
        else:
            matches[k] = int(v)

    return matches


def renombrar_archivos(carpeta: str, carpeta_salida: str):
    patron = re.compile(r"^point_(\d{2})_(\d{2})(\..+)?$")
    os.makedirs(carpeta_salida, exist_ok=True)

    for nombre in os.listdir(carpeta):
        match = patron.match(nombre)
        if match:
            primero, segundo, extension = match.groups()
            extension = extension or ""
            nuevo_primero = int(primero) + 2
            nuevo_nombre = f"point_{nuevo_primero:02d}_{segundo}{extension}"

            ruta_vieja = os.path.join(carpeta, nombre)
            ruta_nueva = os.path.join(carpeta_salida, nuevo_nombre)

            os.rename(ruta_vieja, ruta_nueva)
            print(f"{nombre}  -->  {nuevo_nombre}")
    return "Listo"

def simulation_pipeline(
        input_filedir, 
        output_filedir, 
        transmission_image,
        # mag_image, 
        # phase_image, 
        ratio_LR, 
        led_positions, 
        wavelength, 
        sample_position, 
        fourier_pixel_factor,
        led_spacing_error,
        x_offset,
        y_offset, 
        led_alpha,
        led_beta,
        led_gamma,
        sample_beta,
        h_error):
    
    if isinstance(transmission_image, (tuple, list)):
        mag_image, phase_image = transmission_image
        obj = read_into_complex_image(input_filedir / mag_image, input_filedir / phase_image)
    elif isinstance(transmission_image, str):
        obj = read_numpy_file(transmission_image)
    elif isinstance(transmission_image, np.ndarray) and transmission_image.ndim == 2:
        obj = transmission_image
    else:
        raise Exception(f"No se que hacer con {transmission_image}")
    
    # Leemos las imágenes de magnitud y fase de alta resolución (HR) y ubicamos el centro de la misma
    dc_location_HR = np.asarray((obj.shape)) // 2

    # Luego calculamos el tamaño de las imágenes de baja resolución (LR)
    lr_shape = np.round(np.asarray(obj.shape) * ratio_LR).astype(np.int_)

    # Calculamos las coordenadas de los índices en el espacio de frecuencias en pixeles
    # Estos serán el centro de cada imagen simulada de LR 

    led_positions_tilted = led_errors_incorporated(led_positions, x_offset, y_offset, led_spacing_error, led_alpha, led_beta, led_gamma)

    k_vectors, k_indexes = calculate_k_vectors_k_indices_sample_tilt(
            led_positions_tilted, wavelength, sample_position, dc_location_HR, fourier_pixel_factor, sample_beta, h_error)    

    # Simulamos las imágenes
    data, pupil = simulate(obj, lr_shape, round(min(lr_shape)*.5), k_indexes)

    plt.imshow(pupil, cmap="gray", interpolation="nearest")
    plt.axis("off")  # Ocultar ejes
    plt.show()

    save_images(data, output_filedir)

    return "Imágenes de Baja Resolucion simuladas"

def recontruction_metricas(
        recovery_error_cut,
        output_filedir, 
        input_filedir, 
        carpeta_de_guardado,
        transmission_image,
        # mag_image, 
        # phase_image,
        debug, 
        iterations,
        mu_max,
        weight,
        sigmaN, 
        led_positions,
        wavelength, 
        numerical_aperture,
        sample_position, 
        fourier_pixel_factor,
        leds_number_x,
        leds_number_y,
        numb_external_leds_discarded_row_column,
        numb_internal_leds_discarded_row_column,
        led_spacing_error,
        x_offset,
        y_offset, 
        led_alpha,
        led_beta,
        led_gamma,
        sample_beta,
        h_error):
    
    # Tomamos las imágenes simuladas y las cargamos identificando a que led corresponden (key)
    imglist = sorted([filename for filename in output_filedir.glob("point*.npy")])

    data = leds_indexes = None

    for ndx, path in enumerate(imglist):
        
        if debug:
            if ndx == 0:
                img = np.load(path)
        else:
            img = np.load(path)
            
        if data is None:
            data = {}
            leds_indexes = []
            
        key = (int(path.stem[6:8]),int(path.stem[9:11]))
        data[key] = img
        leds_indexes.append(key)

    # Añadimos ruido
    data_original_max = np.max([np.max(arr) for arr in data.values()])

    sigma2 = (data_original_max * sigmaN) ** 2

    # Tomamos la dimension de las imágenes de LR
    lr_shape = data[list(data.keys())[0]].shape

    # Tomamos las imagenes de HR de magnitud y fase
    if isinstance(transmission_image, (tuple, list)):
        mag_image, phase_image = transmission_image
        obj = read_into_complex_image(input_filedir / mag_image, input_filedir / phase_image)
    elif isinstance(transmission_image, str):
        obj = read_numpy_file(transmission_image)
    elif isinstance(transmission_image, np.ndarray) and transmission_image.ndim == 2:
        obj = transmission_image
    else:
        raise Exception(f"No se que hacer con {transmission_image}")

    objf = np.fft.fftshift(np.fft.fft2(obj))
    hr_shape = (obj.shape[0], obj.shape[1])
    ratio_LR_synt = lr_shape[0]/hr_shape[0]
    NA_synth = numerical_aperture / ratio_LR_synt
    max_angle = np.arctan(1 / (np.sqrt((1 / NA_synth) ** 2 - 1)))

    dc_location = np.asarray((obj.shape)) // 2
    
    #Calculamos los vectores en el espacio de frecuencias y los indices en el espacio de frecuencias en pixeles que usaremos en la reconstruccion
    
    led_positions_tilted = led_errors_incorporated(led_positions, x_offset, y_offset, led_spacing_error, led_alpha, led_beta, led_gamma)

    k_vectors_tilt, k_indexes_tilt = calculate_k_vectors_k_indices_sample_tilt(
            led_positions_tilted, wavelength, sample_position, dc_location, fourier_pixel_factor, sample_beta, h_error)   

    k_vectors, k_indexes = calculate_k_vectors_k_indices( 
    led_positions, wavelength, sample_position, dc_location, fourier_pixel_factor)  

    # Filtramos los datos quitando un número de imagenes correspondientes a un número de leds en cada lado de las filas y columnas
    filtered_coordinates = [(i, j) for i in range(numb_external_leds_discarded_row_column+1, leds_number_x+1-numb_external_leds_discarded_row_column,numb_internal_leds_discarded_row_column +1) for j in range(numb_external_leds_discarded_row_column+1, leds_number_y+1-numb_external_leds_discarded_row_column,numb_internal_leds_discarded_row_column +1)]
    filtered_indexes = {key: k_indexes[key] for key in filtered_coordinates if key in leds_indexes}
    filtered_indexes_tilt = {key: k_indexes_tilt[key] for key in filtered_coordinates if key in leds_indexes}
    filtered_data = {key: data[key] for key in filtered_indexes_tilt if key in leds_indexes}

    def _on_iteration(ndx: int, z: npt.NDArray[np.complex128]):
        """This will be call on each iteration
        """
        if np.mod(ndx, 50) != 0:
            return

    # Creamos la pupila que usaremos en cada imagen simulada al reconstruir
    synthetic_pupil = create_pupil(round(.5 * np.min(data[list(data.keys())[0]].shape)), data[list(data.keys())[0]].shape)

    # Definimos los indices en los que reconstruiremos, sumando y restando diez pixeles a los valores de los indices calculados anteriormente
    z0 = im_r = np.zeros((hr_shape[0],hr_shape[1])).astype(complex)
    recovery_errs = np.zeros((iterations))

    # Sumo las pupilas utilizadas en la reconstruccion para luego visualizarlas
    filtered_matrix_overlapped_with_pupils = sum_pupils(obj.shape, lr_shape, round(min(lr_shape)* 0.5), filtered_indexes)
    filtered_matrix_overlapped_with_pupils_tilt = sum_pupils(obj.shape, lr_shape, round(min(lr_shape)* 0.5), filtered_indexes_tilt)

    # fig, axes = plt.subplots(2, 2, figsize=(8, 8))
    # tmp = np.asarray(list(led_positions.values()))
    # axes[0,0].scatter(tmp[:, 0], tmp[:, 1], c="g")
    # axes[0,0].set_title("Espacio real")

    # tmp1 = np.asarray(list(k_vectors.values()))
    # tmp2 = np.asarray(list(k_vectors_tilt.values()))
    # axes[0,1].scatter(tmp1[:, 0], tmp1[:, 1], c="r", label="k_vectors")
    # axes[0,1].scatter(tmp2[:, 0], tmp2[:, 1], c="b", label="k_vectors_tilt")
    # axes[0,1].set_title("Espacio k")

    # tmp = np.asarray(list(k_indexes_tilt.values()))
    # axes[1,0].scatter(tmp[:, 0], tmp[:, 1], c="r")
    # axes[1,0].set_title("k en la Simulacion - pixeles")

    # tmp1 = np.asarray(list(filtered_indexes.values()))
    # tmp2 = np.asarray(list(filtered_indexes_tilt.values()))
    # axes[1,1].scatter(tmp1[:, 0], tmp1[:, 1], c="r", label="indices_filtrados")
    # axes[1,1].scatter(tmp2[:, 0], tmp2[:, 1], c="b", label="indices_filtrados_tilt")
    # axes[1,1].set_title("k en la reconstruccion")
    # axes[1,1].legend()

    # plt.tight_layout()
    # nombre_del_archivo_2 = f"Reconstruccion quitando {2*numb_external_leds_discarded_row_column} filas-columnas"
    # fig.canvas.manager.set_window_title(nombre_del_archivo_2)
    # plt.show()

    # fig, axes = plt.subplots(1, 2, figsize=(12, 6)) 
    # axes[0].imshow(filtered_matrix_overlapped_with_pupils)
    # axes[1].imshow(filtered_matrix_overlapped_with_pupils_tilt)
    # titulo = f"Solapamiento en la Reconstrucción quitando {2 * numb_external_leds_discarded_row_column} filas-columnas"
    # fig.suptitle(titulo)  # Usé suptitle para un título general de la figura

    # fig.canvas.manager.set_window_title(titulo)  

    # plt.show()

    print(f"\nSample height: {h_error}, Sample beta: {sample_beta}\nOffset_y: {y_offset}, Offset_x: {x_offset}\nAlpha led: {led_alpha}, Beta led: {led_beta}, Gamma led: {led_gamma}")
                    

    data_array = np.stack([filtered_data[key] for key in sorted(filtered_data.keys())], axis=-1) 
    z0, im_r, recovery_errs_dict, imagenes_intermedias = reconstruct(recovery_error_cut, data_array, hr_shape, sigma2, filtered_indexes_tilt, synthetic_pupil, iterations, mu_max, weight, objf, _on_iteration)

    recovery_errs_df = pd.DataFrame.from_records(recovery_errs_dict)
    recovery_errs = recovery_errs_df["recovery_err"].to_list()
    # z0=np.append(z0,z00,axis=0)   #z0.append(z00)
    # im_r=np.append(im_r,im_r00)  #im_r.append(im_r00)
    print(f'El recovery error es: {recovery_errs[-1]}')
    default_filename = f"t_im_iteraciones_{iterations}_size_{hr_shape[0]}_color{wavelength}_max_angle_{max_angle}_leds_discarded_{numb_external_leds_discarded_row_column}.png"
    if len(recovery_errs) == (iterations-1):
        plt.figure()
        plt.subplot(1, 2, 1)
        plt.imshow(np.abs(im_r))
        plt.title(f'Recovery Error {recovery_errs[-1]}')
        plt.subplot(1, 2, 2)
        plt.imshow(np.angle(im_r))
        plt.savefig(default_filename)
        np.save(carpeta_de_guardado/f"Matriz_transmision_{default_filename}", im_r)
        # np.save(f"fase_{default_filename}.npy", np.angle(im_r))
        # np.save(f"magnitud_{default_filename}.npy", np.abs(im_r))
        # plt.show()
        
        plt.figure()
        plt.plot(recovery_errs)
        plt.xlabel('Iteration')
        plt.ylabel('Recovery Error')
        RE_default_filename = f"RE_{default_filename}"
        plt.savefig(RE_default_filename)
        # plt.show()
        plt.legend()
        np.save(carpeta_de_guardado/RE_default_filename,recovery_errs)
    
    for key, imagen in imagenes_intermedias.items():
        default_filename_2 = f"t_im_iteraciones_{key}_size_{hr_shape[0]}_color{wavelength}_max_angle_{max_angle}_leds_discarded_{numb_external_leds_discarded_row_column}.png"
        # if len(recovery_errs) == (iterations-1):
        plt.figure()
        plt.subplot(1, 2, 1)
        plt.imshow(np.abs(imagen))
        # plt.title(f'Recovery Error {recovery_errs[-1]}')
        plt.subplot(1, 2, 2)
        plt.imshow(np.angle(imagen))
        plt.savefig(default_filename_2)
        np.save(carpeta_de_guardado/f"Matriz_transmision_{default_filename_2}", imagen)
        # np.save(f"fase_{default_filename_2}.npy", np.angle(imagen))
        # np.save(f"magnitud_{default_filename_2}.npy", np.abs(imagen))

    recovery_errs_df.attrs = {
        "recovery_error_cut": recovery_error_cut,
        "transmision_image": transmission_image,
        "iterations": iterations,
        "mu_max": mu_max,
        "weight": weight,
        "sigmaN": sigmaN, 
        "led_positions": led_positions,
        "wavelength": wavelength, 
        "sample_position": sample_position, 
        "fourier_pixel_factor": fourier_pixel_factor,
        "leds_number_x": leds_number_x,
        "leds_number_y": leds_number_y,
        "numb_external_leds_discarded_row_column": numb_external_leds_discarded_row_column,
        "numb_internal_leds_discarded_row_column": numb_internal_leds_discarded_row_column,
        "led_spacing_error": led_spacing_error,
        "x_offset": x_offset,
        "y_offset": y_offset, 
        "led_alpha": led_alpha,
        "led_beta": led_beta,
        "led_gamma": led_gamma,
        "sample_beta": sample_beta,
        "h_error": h_error
    }
    return recovery_errs_df