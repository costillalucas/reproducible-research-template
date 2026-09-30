"""COPIA ADAPTADA del trabajo anterior de Lucas Costilla -- no es código original de este repo.

Original:  ~/Documents/LucasC/code/ptyco-full-simulator/real_images_reconstruction.py
           + las funciones que usa de common.py (mismo repo, commit fea5c80, 2026-09-22).
           Copia textual, sin tocar, en scripts/lucas_tpwfp/original/ (sha256 en el README).
Adaptada:  2026-09-28, para la captura roja del 2026-09-25, set 3 (el mismo dato de
           results/captura_2026-09-25_red/, INFORME.md).

La lógica es la de Lucas: TPWFP (Bian 2016, flujo de Wirtinger truncado con la variable de
ruido N y epsilon), paso mu = min(1 - exp(-ndx/330), mu_max) / normest**2, inicialización con
sqrt de la imagen del medio de la lista, las mismas salidas (png, fase/magnitud .npy, imágenes
intermedias, estadísticas de fase, CSV de errores, diferencias y perfiles radiales).

Cada cambio respecto del original está marcado en el código con  # [CAMBIO Cn]  y explicado en
scripts/lucas_tpwfp/README.md:
  C1  datos: los del 25/09 ya preprocesados como en nuestras reconstrucciones (dark, exposición
      por LED, flats, máscara de saturados), no los .tiff crudos de una sola carpeta.
  C2  geometría del 25/09: lambda 630 nm, NA 0.07, 2.5x, píxel 3.2 um, z 74 mm, eje en fila 17.5.
  C3  orientación LED -> frecuencia: las filas de LEDs mueven el espectro a lo largo de las filas
      de la imagen (se ve en los espectros crudos); el original lo tenía rotado 90 grados.
  C4  redondeo del índice k: round en vez de floor (igual que nuestras reconstrucciones).
  C5  pupila con el radio físico NA/lambda (57 px), no la mitad de la imagen (200 px).
  C6  lienzo HR: factor 3 (1200 px, el de nuestras reconstrucciones) con todas las ventanas dentro.
  C7  operador inverso: el original no es el adjunto del directo (ubica el gradiente corrido);
      corregido y verificado con un test de adjunto.
  C8  LEDs: los 169 capturados por defecto; el filtro circular del original queda como opción,
      centrado en el eje óptico real.
  C9  (opcional, NO es la lógica original) normalizar el gradiente por cobertura en vez de por L.

Correr desde la raíz del repo:
    python3 scripts/lucas_tpwfp/real_images_reconstruction_rojo_2026-09-25.py [--iteraciones 76]
Salidas en results/captura_2026-09-25_red/tpwfp_lucas/<corrida>/ (results/ está en .gitignore).
"""
import argparse
import os
import sys

import numpy as np
import numpy.typing as npt
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from skimage import transform as skt
from tqdm import tqdm

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
RED = os.path.join(REPO, "results", "captura_2026-09-25_red")
sys.path.insert(0, os.path.join(HERE, "original"))
sys.path.insert(0, RED)

# Funciones del original que se usan SIN cambios (copia textual en original/common.py)
from common import (calculate_led_positions_equi, led_errors_incorporated,  # noqa: E402
                    calculate_k_vector, sample_tilt_incorporated, calulate_max_angle,
                    calculate_LR_ratio, blind_quality_dict)
import fpm_red as F  # noqa: E402  (datos y geometría de nuestras reconstrucciones, para C1 y las verificaciones)


# ----------------------------------------------------------------------------------------------
# Parámetros (los del original, con los valores del 25/09)
# ----------------------------------------------------------------------------------------------
leds_number_x = 33          # matriz completa, igual que el original
leds_number_y = 29
central_led = (17, 15)      # LED central de la matriz (origen de calculate_led_positions_equi)
led_spacing = 6e-3
matrix_center = (0, 0, 0)
wavelength = 6.3e-7         # [CAMBIO C2] rojo 630 nm (el original usaba 680 nm)
numerical_aperture = 0.07   # [CAMBIO C2] objetivo 2.5x NA 0.07 (el original: 2x NA 0.10)
magnification = 2.5         # [CAMBIO C2]
pixel_size = 3.2e-6         # igual: 3.2 um en la cámara -> 1.28 um en la muestra
sample_height = 74e-3       # [CAMBIO C2] z = 74 mm, medido por Lucas (el original: 76 mm)
sample_position = (0, 0, sample_height)
x_offset = 0.0              # [CAMBIO C2] el eje óptico cae entre las filas 17 y 18 (fila 17.5):
y_offset = -3e-3            #   y_led = (fila - 17)*6 mm - 3 mm. El original usaba (4, 2) mm (julio 2025).
led_alpha = led_beta = led_gamma = 0.0
sample_beta = 0.0
h_error = 0.0
factor_hr = 3               # [CAMBIO C6] HR = 3 x LR, como nuestras reconstrucciones (0.427 um/px)
sigma2 = 0.0                # igual que el original (se pasaba 0 a reconstruct_real_images_test)
mu_max = 0.4
weight = 1
iterations = 76
iteraciones_a_guardar = 5
recovery_error_cut = 0      # 0 = sin corte temprano, igual que el original
congelar = False


# ----------------------------------------------------------------------------------------------
# Geometría
# ----------------------------------------------------------------------------------------------
def calculate_k_vectors_k_indices_sample_tilt(led_positions, wavelength, sample_position, dc_location,
                                               fourier_pixel_factor, sample_tilt, h_error):
    """Igual que en common.py salvo C3 y C4."""
    k_vectors_tilt, k_indices = {}, {}
    for key, led_position in led_positions.items():
        k = sample_tilt_incorporated(calculate_k_vector(led_position, wavelength, sample_position, h_error), sample_tilt)
        k_vectors_tilt[key] = k
        # [CAMBIO C3] original: k_pixel = dc + k[:2] / (2 pi fpf)  -> eje 0 de la imagen <- columna del LED.
        # En estas imágenes el eje 0 (filas) corresponde a la FILA del LED (figs/real_espectro_crudo_circulos.png:
        # (16,15)/(19,15) corren los discos en vertical, (17,14)/(17,16) en horizontal). Con las posiciones de
        # calculate_led_positions_equi (x = (15 - col) p, y = (fila - 17) p) y k ~ (muestra - LED):
        #   eje 0 <- -k_y,  eje 1 <- +k_x   (la convención ya validada en nuestras reconstrucciones).
        k_pixel = dc_location + np.array([-k[1], k[0]]) / (2 * np.pi * fourier_pixel_factor)
        k_indices[key] = np.rint(k_pixel).astype(int)   # [CAMBIO C4] original: math.floor
    return k_vectors_tilt, k_indices


def create_pupil(pupil_radio: float, lr_shape: tuple[int, int]) -> npt.NDArray[np.bool_]:
    """Igual que en common.py (el radio ahora es físico, ver C5)."""
    center = int(lr_shape[0] / 2), int(lr_shape[1] / 2)
    Y, X = np.ogrid[:lr_shape[1], :lr_shape[0]]
    return (X - center[0]) ** 2 + (Y - center[1]) ** 2 < pupil_radio ** 2


def sum_pupils(hr_shape, lr_shape, pupil, indices):
    """Como en common.py, pero sin corrimientos silenciosos (C6: todo tiene que caber)."""
    m = np.zeros(hr_shape)
    n0, n1 = lr_shape
    for (a, b) in indices.values():
        m[a - n0 // 2:a - n0 // 2 + n0, b - n1 // 2:b - n1 // 2 + n1] += pupil
    return m


# ----------------------------------------------------------------------------------------------
# Operadores
# ----------------------------------------------------------------------------------------------
def linear_operator_vectorized(xx, indices_stack, xx_c_buffer, pupil, L):
    """Igual que en common.py; safe_slice_lo se reemplaza por un corte directo porque con C6 ninguna
    ventana sale del lienzo (el original la corría en silencio hasta que entraba)."""
    n0, n1 = xx_c_buffer.shape[:2]
    for k in range(L):
        a, b = indices_stack[k]
        xx_c_buffer[:, :, k] = xx[a - n0 // 2:a - n0 // 2 + n0, b - n1 // 2:b - n1 // 2 + n1] * pupil
    return np.fft.ifft2(np.fft.ifftshift(xx_c_buffer, axes=(0, 1)), axes=(0, 1))


def inverse_linear_operator_real_images_vectorized(xx_c, indices_stack, xx_mean_large_buffer, pupil, cobertura=None):
    """[CAMBIO C7] Mismo cálculo que en common.py (fft2 sin normalizar, conj(pupila), promedio sobre
    los L LEDs) pero cada LED vuelve a SU ventana, la misma que usó el operador directo.

    En el original el bloque acumulado se arma con ventanas relativas a mn0 - n0//2 (índice
    ndx0 - mn0 - n0//2) pero se pega en el lienzo empezando en mn0, no en mn0 - n0//2; cuando se sale
    del lienzo safe_slice lo corre hasta que entra y, además, recorta en 0 las ventanas de los LEDs con
    ndx0 - mn0 < n0//2. El resultado no es el adjunto del directo (test en README: error relativo 1.4).
    [CAMBIO C9, opcional] cobertura: en vez de /L, divide cada píxel por cuántos LEDs lo cubren."""
    n0, n1, L = xx_c.shape
    X = np.fft.fftshift(np.fft.fft2(xx_c, axes=(0, 1)), axes=(0, 1))
    out = xx_mean_large_buffer
    out[:] = 0
    cp = np.conj(pupil)
    for k in range(L):
        a, b = indices_stack[k]
        out[a - n0 // 2:a - n0 // 2 + n0, b - n1 // 2:b - n1 // 2 + n1] += X[:, :, k] * cp
    if cobertura is None:
        out /= L
    else:
        out /= cobertura
    return out


# ----------------------------------------------------------------------------------------------
# Solver: reconstruct_real_images_test de common.py
# ----------------------------------------------------------------------------------------------
def reconstruct_real_images_test(recovery_error_cut, data, hr_shape, sigma2, indices, pupil, iterations,
                                 mu_max, weight, on_iteration, iteraciones_a_guardar, congelar_leds=False,
                                 mask=None, cobertura=None, guardar_intermedias=True):
    """TPWFP para datos reales, igual que en common.py. Cambios: C7 (adjunto), C9 (opcional),
    máscara de saturados (C1: esos píxeles no aportan gradiente) y clip a 0 en la inicialización
    (los LEDs de campo oscuro, ya sin la luz parásita del flat, pueden tener píxeles negativos)."""
    n0, n1, L = data.shape
    lr_shape = (int(n0), int(n1))

    # Inicialización z_im (igual): sqrt de la imagen del medio de la lista, reescalada y agrandada
    z_im = np.sqrt(np.clip(data[:, :, int(np.fix(L / 2))], 0, None)) * \
        (lr_shape[0] * lr_shape[1]) / (hr_shape[0] * hr_shape[1])   # [CAMBIO C1] clip
    z_im = skt.resize(z_im, hr_shape)
    z0 = np.fft.fftshift(np.fft.fft2(z_im))
    z = z0.copy()

    N = np.zeros(data.shape, dtype=np.float64)
    epsilon = np.zeros_like(N)
    normest = np.sqrt(np.sum(data) / L / lr_shape[0] / lr_shape[1])
    step_size_n = 0.01

    imagenes_intermedias, phase_max_list, phase_min_list = {}, [], []
    z_old = None
    indices_stack = np.asarray(list(indices.values()))
    diccionario_records, pasos, registros, perfiles_radiales_records = [], [], [], []

    hito_1, hito_2 = round(iterations * 1 / 9), round(iterations * 1 / 3)
    hito_3, hito_4 = round(iterations * 3 / 5), round(iterations * 9 / 10)

    xx_c_buffer = np.empty((lr_shape[0], lr_shape[1], L), dtype=np.complex128)
    xx_mean_large = np.zeros(hr_shape, dtype=np.complex128)

    Ny, Nx = z.shape
    KX, KY = np.meshgrid(np.linspace(-Nx // 2, Nx // 2 - 1, Nx), np.linspace(-Ny // 2, Ny // 2 - 1, Ny))
    K_int = np.round(np.sqrt(KX ** 2 + KY ** 2)).astype(int)
    conteo_radios = np.bincount(K_int.flatten())
    conteo_radios[conteo_radios == 0] = 1
    metrica_anterior = None
    leds_congelados = np.zeros(L, dtype=bool)

    for ndx in tqdm(range(1, iterations)):
        Bz_array = linear_operator_vectorized(z, indices_stack, xx_c_buffer, pupil, L)
        error_term = np.abs(Bz_array)
        error_term **= 2
        error_term += N
        error_term -= data
        if mask is not None:
            error_term[~mask] = 0          # [CAMBIO C1] píxeles saturados: sin gradiente
        Cz = error_term * Bz_array
        Cz[:, :, leds_congelados] = 0

        w = inverse_linear_operator_real_images_vectorized(Cz, indices_stack, xx_mean_large, pupil, cobertura)

        mu = np.float64(1 - np.exp(-ndx / 330))
        mu = np.minimum(mu, mu_max) / (normest ** 2)
        z -= mu * w

        CN = error_term + weight * (N * N - 9 * sigma2 + epsilon * epsilon) * 2.0 * N
        CN *= mu * step_size_n
        N -= CN
        e_temp = 9 * sigma2 - N * N
        e_temp[e_temp < 0] = 0
        epsilon = np.sqrt(e_temp)

        on_iteration(ndx, z)

        if ndx % iteraciones_a_guardar == 0:
            suma_radial = np.bincount(K_int.flatten(), weights=(np.abs(z) ** 2).flatten())
            perfiles_radiales_records.append(suma_radial / conteo_radios)
            imagen = np.fft.ifft2(np.fft.ifftshift(z))
            if guardar_intermedias:
                imagenes_intermedias[ndx] = imagen
            fase = np.angle(imagen) / np.pi
            phase_max_list.append(np.max(fase))
            phase_min_list.append(np.min(fase))
            sim = np.abs(Bz_array) ** 2
            qd = blind_quality_dict(z, lr_intensities_measured=data, lr_intensities_simulated=sim, x_old=z_old)
            diccionario_records.append(qd)
            pasos.append(mu)
            diferencias = np.sum(np.abs(np.abs(data) - np.abs(sim)), axis=(0, 1))
            data_sum = np.sum(np.abs(data), axis=(0, 1))
            simuladas_sum = np.sum(np.abs(sim), axis=(0, 1))
            metrica_error_normalizada = diferencias / (data_sum + simuladas_sum + 1e-12)
            if congelar_leds:
                if metrica_anterior is not None:
                    leds_congelados |= (~leds_congelados) & (metrica_error_normalizada > 1.02 * metrica_anterior)
                metrica_anterior = metrica_error_normalizada.copy()
            for (x, y), dif, dat, si in zip(indices.keys(), diferencias, data_sum, simuladas_sum):
                registros.append({"Iteracion": ndx, "led_x": x, "led_y": y, "Diferencia": dif,
                                  "Data": dat, "Simuladas": si})
            if recovery_error_cut != 0:
                e = qd.get("reprojection_data_error", float("inf"))
                if ((ndx == hito_1 and e > recovery_error_cut * 1.10) or (ndx == hito_2 and e > recovery_error_cut)
                        or (ndx == hito_3 and e > recovery_error_cut * 0.90)
                        or (ndx == hito_4 and e > recovery_error_cut * 0.10)):
                    break
        z_old = z.copy()

    im_r = np.fft.ifft2(np.fft.ifftshift(z))
    return (z0, im_r, diccionario_records, imagenes_intermedias, phase_max_list, phase_min_list, pasos,
            registros, perfiles_radiales_records)


# ----------------------------------------------------------------------------------------------
# Pipeline (recontruction_pipeline_real_images del original)
# ----------------------------------------------------------------------------------------------
def geometria(keys, lr_shape, z_m=sample_height):
    """Posiciones -> índices k, lienzo y pupila, con los parámetros de arriba."""
    led_positions = calculate_led_positions_equi(leds_number_x, leds_number_y, led_spacing, matrix_center)
    leds = {k: led_positions[k] for k in keys}
    hr_shape = (lr_shape[0] * factor_hr, lr_shape[1] * factor_hr)                    # [CAMBIO C6]
    dc_location = np.asarray(hr_shape) // 2
    fourier_pixel_factor = magnification / (lr_shape[0] * pixel_size)              # igual (= 1/(n_LR dx))
    leds_t = led_errors_incorporated(leds, x_offset, y_offset, 0, led_alpha, led_beta, led_gamma)
    _, k_indexes = calculate_k_vectors_k_indices_sample_tilt(leds_t, wavelength, (0, 0, z_m), dc_location,
                                                             fourier_pixel_factor, sample_beta, h_error)
    # [CAMBIO C5] radio de la pupila en píxeles del espectro LR: (NA/lambda) / (1/(n_LR dx)).
    # El original usaba round(0.5*min(lr_shape)) = 200 px, lo que supone píxel = lambda/(2 NA) = 4.5 um;
    # acá el píxel es 1.28 um (3.5 veces más fino) y la pupila real mide 57 px.
    radio = numerical_aperture / wavelength / fourier_pixel_factor
    pupil = create_pupil(radio, lr_shape)
    n0, n1 = lr_shape
    for key, (a, b) in k_indexes.items():                                            # [CAMBIO C6]
        if a - n0 // 2 < 0 or b - n1 // 2 < 0 or a + n0 - n0 // 2 > hr_shape[0] or b + n1 - n1 // 2 > hr_shape[1]:
            raise ValueError(f"la ventana del LED {key} sale del lienzo HR {hr_shape}")
    return k_indexes, hr_shape, pupil, radio


def verificar_contra_repo(k_indexes, hr_shape, pupil, lr_shape, z_mm):
    """Chequeo de C2-C6: ventanas y pupila idénticas a las de nuestras reconstrucciones (fpm_red)."""
    geo = F.geometry(z_mm)
    assert geo["factor"] == factor_hr, geo["factor"]
    from ptyco_full_simulator.spectral_ops import led_crop_window
    from ptyco_full_simulator.optics import circular_pupil
    for k, (a, b) in k_indexes.items():
        ys, xs = led_crop_window(hr_shape, geo["hrpx"], lr_shape, *geo["fxy"][k])
        assert (ys.start, xs.start) == (a - lr_shape[0] // 2, b - lr_shape[1] // 2), (k, ys, xs, a, b)
    assert np.array_equal(pupil, circular_pupil(lr_shape, geo["lrpx"], geo["na"], geo["lam"]))


def recontruction_pipeline_real_images(output_filedir, iterations=iterations, keys_usadas=None,
                                       radio_leds=None, cobertura=False, guardar=True, z_m=sample_height,
                                       D=None):
    """Como el original: carga, filtra LEDs, calcula geometría, reconstruye y guarda.
    Devuelve (im_r, recovery_errs_df, diferencias_df, perfiles_df)."""
    # [CAMBIO C1] datos del 25/09 set 3, preprocesados igual que nuestras reconstrucciones
    # (prep.py + fpm_red.load_real): S = (muestra - dark_t)/t; BF divididos por el flat; DF menos el
    # flat suavizado; máscara de saturados. El original leía fila*.tiff crudos de una carpeta.
    D = D or F.load_real()
    keys = sorted(keys_usadas if keys_usadas is not None else D["keys"])
    # [CAMBIO C8] filtro circular del original (opcional), centrado en el eje óptico real (17.5, 15)
    if radio_leds is not None:
        keys = [k for k in keys if (k[0] - 17.5) ** 2 + (k[1] - 15) ** 2 <= radio_leds ** 2]
    lr_shape = D["I"][keys[0]].shape

    k_indexes, hr_shape, pupil, radio = geometria(keys, lr_shape, z_m)
    verificar_contra_repo(k_indexes, hr_shape, pupil, lr_shape, z_m * 1e3)

    # Diagnósticos del original: ángulo máximo, ratio_LR, solapamiento y tasa de muestreo
    led_positions = calculate_led_positions_equi(leds_number_x, leds_number_y, led_spacing, matrix_center)
    max_angle = calulate_max_angle({k: led_positions[k] for k in keys + [central_led]}, central_led, z_m)
    ratio_LR = calculate_LR_ratio(numerical_aperture, max_angle)
    una = sum_pupils(hr_shape, lr_shape, pupil, {(17, 15): k_indexes[(17, 15)]}) if (17, 15) in k_indexes else None
    if una is not None and (17, 16) in k_indexes:
        par = sum_pupils(hr_shape, lr_shape, pupil, {k: k_indexes[k] for k in [(17, 15), (17, 16)]})
        tasa = np.sum(par == 2) / np.sum(una > 0)
        n_lado = int(np.sqrt(len(keys)))
        etha = (n_lado * lr_shape[0]) ** 2 / ((1 - tasa) * lr_shape[0] * (n_lado - 1) + lr_shape[0]) ** 2
        print(f"Solapamiento entre vecinos {(17, 15)}-{(17, 16)}: {tasa * 100:.1f} %; tasa de muestreo {etha:.1f}")
    print(f"LEDs {len(keys)}, LR {lr_shape}, HR {hr_shape}, radio pupila {radio:.1f} px; "
          f"(la fórmula del original daría HR {int(round(lr_shape[0] / ratio_LR))} px: supone pupila = imagen)")

    data_array = np.stack([D["I"][k] for k in keys], axis=-1).astype(np.float64)
    mask = np.stack([D["mask"][k] for k in keys], axis=-1)
    indices = {k: k_indexes[k] for k in keys}
    cob = None
    if cobertura:                                                                    # [CAMBIO C9]
        cob = np.maximum(sum_pupils(hr_shape, lr_shape, pupil, indices), 1)

    res = reconstruct_real_images_test(recovery_error_cut, data_array, hr_shape, sigma2, indices, pupil.astype(float),
                                       iterations, mu_max, weight, lambda i, z: None, iteraciones_a_guardar,
                                       congelar, mask=mask, cobertura=cob, guardar_intermedias=guardar)
    z0, im_r, dictionary, intermedias, phase_max, phase_min, pasos, diferencias, perfiles = res

    iteraciones_x = np.arange(iteraciones_a_guardar, (len(phase_max) + 1) * iteraciones_a_guardar, iteraciones_a_guardar)
    recovery_errs_df = pd.DataFrame.from_records(dictionary)
    recovery_errs_df["iteraciones"] = iteraciones_x
    diferencias_df = pd.DataFrame.from_records(diferencias)
    perfiles_df = pd.DataFrame.from_records(perfiles)
    perfiles_df["iteraciones"] = iteraciones_x
    if not guardar:
        return im_r, recovery_errs_df, diferencias_df, perfiles_df

    os.makedirs(output_filedir, exist_ok=True)
    nombre = f"t_im_iteraciones_{iterations}_size_{lr_shape[0]}_color{wavelength}_max_angle_{max_angle:.4f}_used_leds_{len(keys)}.png"
    plt.figure(); plt.subplot(1, 2, 1); plt.imshow(np.abs(im_r)); plt.subplot(1, 2, 2); plt.imshow(np.angle(im_r))
    plt.savefig(os.path.join(output_filedir, nombre)); plt.close()
    np.save(os.path.join(output_filedir, f"fase_{nombre}.npy"), np.angle(im_r))
    np.save(os.path.join(output_filedir, f"magnitud_{nombre}.npy"), np.abs(im_r))
    np.save(os.path.join(output_filedir, "objeto_complejo.npy"), im_r.astype(np.complex64))  # para evaluar
    carpeta = os.path.join(output_filedir, f"imagenes_intermedias_iter_{iterations}")
    os.makedirs(carpeta, exist_ok=True)
    for clave, img in intermedias.items():
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7, 3))
        ax1.imshow(np.abs(img), cmap="gray"); ax1.set_title(f"Mag - Paso {clave}"); ax1.axis("off")
        ax2.imshow(np.angle(img), cmap="magma"); ax2.set_title(f"Fase - Paso {clave}"); ax2.axis("off")
        plt.tight_layout()
        plt.savefig(os.path.join(carpeta, f"intermedia_t_im_iteraciones_{clave}_size_{hr_shape[0]}.png"), bbox_inches="tight")
        plt.close(fig)
    plt.figure()
    plt.plot(iteraciones_x, phase_max, "b-", label="Phase max")
    plt.plot(iteraciones_x, phase_min, "r-", label="Phase min")
    plt.xlabel("Iteration"); plt.ylabel("Phase value"); plt.legend()
    plt.savefig(os.path.join(output_filedir, f"Phase_stats_{nombre}")); plt.close()
    recovery_errs_df.to_csv(os.path.join(output_filedir, "resultados_errores_reconstruccion.csv"), index=False)
    diferencias_df.to_csv(os.path.join(output_filedir, "resultados_diferencias_reconstruccion.csv"), index=False)
    perfiles_df.to_csv(os.path.join(output_filedir, "resultados_perfiles_reconstruccion.csv"), index=False)
    return im_r, recovery_errs_df, diferencias_df, perfiles_df


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--iteraciones", type=int, default=iterations)
    ap.add_argument("--radio-leds", type=float, default=None, help="filtro circular del original, en pasos de LED")
    ap.add_argument("--cobertura", action="store_true", help="C9: normalizar el gradiente por cobertura (no es la lógica original)")
    a = ap.parse_args()
    tag = f"it{a.iteraciones}" + (f"_r{a.radio_leds:g}" if a.radio_leds else "") + ("_cob" if a.cobertura else "")
    out = os.path.join(RED, "tpwfp_lucas", tag)
    recontruction_pipeline_real_images(out, a.iteraciones, radio_leds=a.radio_leds, cobertura=a.cobertura)
    print("salidas en", out)
