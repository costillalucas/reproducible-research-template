"""Números del resumen report/resumen/resumen.md (datos reales y geometría).

No escribe nada: compute_numbers.py (el único que escribe data/numbers.json) llama a entries() y
agrega estas entradas al registro. Varios números salen de archivos de results/, que está fuera de
git: para reproducirlos hace falta tener esas corridas en disco (cada entrada dice cuál).
"""
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
RED = "results/captura_2026-09-25_red"


def _j(path):
    return json.load(open(os.path.join(ROOT, path)))


def leds_utiles_2409():
    """LEDs con señal estructural / ruido > 3, verde, enfoque verde, 100 ms (fórmula de an.py)."""
    L = _j("results/captura_2026-09-24/stats_por_led/set_greenfoc_green_100ms.json")
    snr = [np.sqrt(max(d["struct"] ** 2 - d["struct_noise"] ** 2, 0)) / d["struct_noise"] for d in L]
    return int(np.sum(np.array(snr) > 3)), len(L), {(d["r"], d["c"]): float(s) for d, s in zip(L, snr)}


def cv_heldout(prefix, ring_max=7.0):
    """Promedio sobre los 5 folds del R held-out de los LEDs con anillo < 7 (= analyze.cv_summary)."""
    per_fold = []
    for f in sorted(glob.glob(os.path.join(ROOT, RED, "out", "tasks", prefix + "_f*.json"))):
        d = json.load(open(f))
        per_fold.append(np.mean([v[0] for v in d["per_led"].values() if v[2] < ring_max and not v[3]]))
    assert len(per_fold) == 5, prefix
    return float(np.mean(per_fold))


def solapamiento_vecinos_pct(z_mm=74.0):
    """Área común de las pupilas de dos LEDs vecinos (17,15)-(17,16), en % del área de una."""
    sys.path.insert(0, os.path.join(ROOT, RED))
    import fpm_red as F
    geo = F.geometry(z_mm)
    r = geo["na"] / geo["lam"]                                  # 1/um
    d = float(np.hypot(*np.subtract(geo["fxy"][(17, 16)], geo["fxy"][(17, 15)])))
    area = 2 * r * r * np.arccos(d / (2 * r)) - d / 2 * np.sqrt(4 * r * r - d * d)
    return float(100 * area / (np.pi * r * r))


def error_adjunto_original():
    """Test de adjunto del operador inverso original de Lucas (common.py, commit fea5c80)."""
    import contextlib
    import io
    sys.path.insert(0, os.path.join(ROOT, "scripts", "lucas_tpwfp", "original"))
    import common as C
    rng = np.random.default_rng(0)
    n, H = 32, 96
    P = C.create_pupil(n // 2, (n, n)).astype(float)
    S = np.asarray([[i, j] for i in range(20, 77, 14) for j in range(20, 77, 14)])
    L = len(S)
    y = rng.normal(size=(n, n, L)) + 1j * rng.normal(size=(n, n, L))
    with contextlib.redirect_stdout(io.StringIO()):
        AHy = C.inverse_linear_operator_real_images_vectorized(y, S, np.zeros((H, H), complex), P) * L / (n * n)
    ref = np.zeros((H, H), complex)
    Y = np.fft.fftshift(np.fft.fft2(y, axes=(0, 1)), axes=(0, 1)) / (n * n)
    for k, (a, b) in enumerate(S):
        ref[a - n // 2:a - n // 2 + n, b - n // 2:b - n // 2 + n] += Y[:, :, k] * P
    return float(np.linalg.norm(AHy - ref) / np.linalg.norm(ref))


def entries():
    synth = {(r["label"], r["iterations"]): r for r in _j("results/captura_2026-09-24/synth_overlap/summary.json")["runs"]}
    s75, s100 = synth[("hoy_2.5x_z75", 100)], synth[("2.5x_z100", 100)]
    real = _j(f"{RED}/resumen_real.json")
    n_utiles, n_leds, _ = leds_utiles_2409()
    E = {
        "resumen_abbe_verde_um": dict(
            value=0.53 / (2 * 0.07), type="derivation", reproduce="lambda/(2 NA) con lambda = 0.53 um y NA = 0.07",
            statement="Límite de resolución (Abbe) del objetivo 2.5x NA 0.07 en luz verde, en µm"),
        "resumen_leds_utiles_julio": dict(
            value=_j("results/esferas_2026-07-08/sanity/radiance_census.json")["channels"]["green"]["census"]["n_ge_10pct_peak"],
            type="data", reproduce="results/esferas_2026-07-08/sanity/radiance_census.json",
            statement="Captura 08/07/2026, verde, 1 ms: LEDs (de 182) con al menos 10 % del brillo del LED más brillante "
                      "(channels.green.census.n_ge_10pct_peak)"),
        "resumen_leds_utiles_2409": dict(
            value=n_utiles, type="script", reproduce="scripts/resumen_numbers.py::leds_utiles_2409",
            statement=f"Captura 24/09, verde con enfoque verde, 100 ms: LEDs (de {n_leds}) con señal estructural/ruido > 3 "
                      "(fórmula de results/captura_2026-09-24/stats_por_led/an.py)"),
        "resumen_centro_fila": dict(
            value=_j("results/led_geometry_2025-12-12/center_from_radiance.json")["main_z76_poly4"]["row"], type="data",
            reproduce="results/led_geometry_2025-12-12/center_from_radiance.json",
            statement="Captura 12/12/2025: fila del eje óptico ajustada con el brillo por LED (main_z76_poly4.row; "
                      "la columna es main_z76_poly4.col)"),
        "resumen_centro_col": dict(
            value=_j("results/led_geometry_2025-12-12/center_from_radiance.json")["main_z76_poly4"]["col"], type="data",
            reproduce="results/led_geometry_2025-12-12/center_from_radiance.json",
            statement="Captura 12/12/2025: columna del eje óptico ajustada con el brillo por LED (main_z76_poly4.col)"),
        "resumen_sint_amplitud": dict(
            value=s75["amplitude_correlation"], type="data", reproduce="results/captura_2026-09-24/synth_overlap/summary.json",
            statement="Simulación sin ruido con la geometría real (2.5x, z = 75 mm, 100 iteraciones): correlación del brillo "
                      "reconstruido con el de la muestra (runs[hoy_2.5x_z75, 100].amplitude_correlation)"),
        "resumen_sint_fase": dict(
            value=s75["phase_correlation"], type="data", reproduce="results/captura_2026-09-24/synth_overlap/summary.json",
            statement="La misma simulación: correlación de la fase (runs[hoy_2.5x_z75, 100].phase_correlation)"),
        "resumen_sint_fase_z100": dict(
            value=s100["phase_correlation"], type="data", reproduce="results/captura_2026-09-24/synth_overlap/summary.json",
            statement="La misma simulación con la matriz a 100 mm, es decir más solapamiento entre LEDs vecinos "
                      "(runs[2.5x_z100, 100].phase_correlation)"),
        "resumen_paso_congelado_factor": dict(
            value=400 * 400 / 20.0, type="derivation",
            reproduce="lr_n_px / step_max = (400*400)/20, src/ptyco_full_simulator/reconstruction.py (step_max = 20)",
            statement="Cuántas veces más chico que el paso ePIE unitario era el paso de Wirtinger flow con recortes de 400 px "
                      "(roadmap sección 6.9)"),
        "resumen_zeiss_um_px": dict(
            value=2.344, type="source",
            reproduce="~/Documents/AleYLu/elefante/2025-12-02/3x3/3x3_Metadata(tif).xml (Scaling Distance X = 2.344e-6 m; "
                      "objetivo Plan-Neofluar 2.5x/0.075)",
            statement="Tamaño de píxel en la muestra de la imagen de referencia Zeiss, en µm"),
        "resumen_adjunto_error": dict(
            value=error_adjunto_original(), type="script", reproduce="scripts/resumen_numbers.py::error_adjunto_original",
            statement="Error relativo del operador inverso original (common.py de ptyco-full-simulator) frente al adjunto "
                      "exacto del operador directo (0 = correcto)"),
        "resumen_R_Ainit": dict(
            value=real["cv"]["A+init"]["mean"], type="data", reproduce=f"{RED}/resumen_real.json",
            statement="Rojo 25/09 set 3, método A+init: error de predicción de LEDs no vistos, promedio de 5 folds "
                      "(cv.A+init.mean; 1 = no mejor que una constante)"),
        "resumen_R_sinfpm": dict(
            value=real["nofpm"]["mean"], type="data", reproduce=f"{RED}/resumen_real.json",
            statement="El mismo error sin reconstruir, prediciendo desde la imagen inicial (nofpm.mean)"),
        "resumen_frc_real": dict(
            value=real["C2"]["frc_sel"], type="data", reproduce=f"{RED}/resumen_real.json",
            statement="Rojo 25/09: coincidencia (FRC) entre las dos mitades de LEDs en la banda 0.222-0.45 1/µm, "
                      "más allá del límite del objetivo (C2.frc_sel)"),
        "resumen_frc_umbral": dict(
            value=float(np.clip(0.5 * _j(f"{RED}/resumen_synth.json")["C2"]["frc_sel"], 0.143, 0.5)), type="derivation",
            reproduce=f"clip(0.5 x FRC sintético, 0.143, 0.5), regla de {RED}/criterios.md",
            statement="Umbral de C2, fijado con la simulación antes de mirar los datos reales"),
        "resumen_frc_sint": dict(
            value=_j(f"{RED}/resumen_synth.json")["C2"]["frc_sel"], type="data", reproduce=f"{RED}/resumen_synth.json",
            statement="La misma coincidencia entre mitades en la simulación de la captura (C2.frc_sel, método B)"),
        "resumen_z115_R": dict(
            value=cv_heldout("real_B_z115.0"), type="script", reproduce="scripts/resumen_numbers.py::cv_heldout",
            statement=f"Rojo 25/09, método B con z = 115 mm: error de predicción de LEDs no vistos "
                      f"({RED}/out/tasks/real_B_z115.0_f*.json)"),
        "resumen_solapamiento_pct": dict(
            value=solapamiento_vecinos_pct(), type="script", reproduce="scripts/resumen_numbers.py::solapamiento_vecinos_pct",
            statement="Solapamiento entre las pupilas de dos LEDs vecinos en el espectro, z = 74 mm, en % del área"),
    }
    S1 = "results/captura_2026-09-25_red_set1"
    v1 = _j(f"{S1}/veredicto.json")
    E.update({
        "resumen_set1_R": dict(
            value=v1["C1"]["sel_mean"], type="data", reproduce=f"{S1}/veredicto.json",
            statement="Rojo 25/09 set 1 (otra zona), A+init: error de predicción de LEDs no vistos (C1.sel_mean)"),
        "resumen_set1_sinfpm": dict(
            value=v1["C1"]["nofpm"], type="data", reproduce=f"{S1}/veredicto.json",
            statement="Set 1: el mismo error sin reconstruir (C1.nofpm)"),
        "resumen_set1_sint_R": dict(
            value=v1["sintetico"]["C1"]["sel_mean"], type="data", reproduce=f"{S1}/veredicto.json",
            statement="Simulación con los niveles de señal y ruido del set 1 (muestra delgada): error de predicción "
                      "de LEDs no vistos (sintetico.C1.sel_mean)"),
        "resumen_set1_sint_frc": dict(
            value=v1["sintetico"]["C2"]["frc_sel"], type="data", reproduce=f"{S1}/veredicto.json",
            statement="La misma simulación: coincidencia entre las dos mitades en la banda más allá del objetivo "
                      "(sintetico.C2.frc_sel)"),
    })
    R = "results/captura_2026-09-28_rgb"
    me, reg, band, raw = (_j(f"{R}/{f}.json") for f in ("multiespectral", "multiespectral_registrado", "multiespectral_por_banda",
                                                        "fotos_crudas_entre_colores"))
    nof = _j(f"{R}/red/out/tasks/real_nofpm_z74.0.json")
    E.update({
        "resumen_rgb_R_rojo": dict(value=reg["C1_rojo"][0], type="data", reproduce=f"{R}/multiespectral_registrado.json",
                                   statement="RGB 28/09, rojo, A+init: error de predicción de LEDs no vistos (5 folds, C1_rojo)"),
        "resumen_rgb_sinfpm_rojo": dict(value=float(np.mean([v[0] for v in nof["per_led"].values() if v[2] < 7])), type="data",
                                        reproduce=f"{R}/red/out/tasks/real_nofpm_z74.0.json",
                                        statement="RGB 28/09, rojo: el mismo error sin reconstruir"),
        "resumen_rgb_frc_verde": dict(value=me["frc_mitades"]["green"]["frc"], type="data", reproduce=f"{R}/multiespectral.json",
                                      statement="RGB 28/09, verde: coincidencia entre mitades de LEDs en la banda [2NA/lambda, 0.45] 1/µm "
                                                "(el rojo da 0.014 y el azul 0.009, mismo archivo)"),
        "resumen_rgb_crudas_min": dict(value=min(v["corr"] for v in raw.values()), type="data", reproduce=f"{R}/fotos_crudas_entre_colores.json",
                                       statement="RGB 28/09: correlación entre colores de la foto cruda (18,15), registrada (mínimo de rojo-verde y azul-verde)"),
        "resumen_rgb_crudas_max": dict(value=max(v["corr"] for v in raw.values()), type="data", reproduce=f"{R}/fotos_crudas_entre_colores.json",
                                       statement="Ídem, máximo"),
        "resumen_rgb_banda_max": dict(value=max(band["banda del objetivo (NA/lambda rojo)"].values()), type="data",
                                      reproduce=f"{R}/multiespectral_por_banda.json",
                                      statement="RGB 28/09: correlación del brillo reconstruido entre colores dentro de la banda del objetivo "
                                                "(máximo de los tres pares; el mínimo es 0.18)"),
        "resumen_rgb_todo_max": dict(value=max(band["todo"].values()), type="data", reproduce=f"{R}/multiespectral_por_banda.json",
                                     statement="RGB 28/09: la misma correlación con todo el espectro reconstruido (máximo de los tres pares)"),
    })
    return E


if __name__ == "__main__":
    for k, v in entries().items():
        print(f"{k:32s} {v['value']}")
