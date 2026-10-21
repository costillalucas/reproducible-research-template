"""cv_common.py -- the ONE held-out-LED cross-validation protocol and the ONE
lattice score every J3 task (T1 baseline, T2 geometry, T3 causes, T4 final) uses,
so the numbers in the final table are comparable line by line.

CV protocol -- taken from `results/geometry_search_2025-12-12/cv.py` (fork K,
December's geometry search): leave out every 4th LED in a FIXED (row, col)
lexicographic order, never the on-axis/init LED, reconstruct on the rest, and
score the mean per-LED relative amplitude residual on the LEDs left out. It
exists because the training residual goes DOWN when a geometry hypothesis simply
uses fewer effective constraints (roadmap 6.10), so it cannot rank geometries.

What is new here vs December: a FOLD INDEX 0..3. December hard-coded `i % 4 == 1`,
i.e. exactly `fold=1` of this function, and so produced one number with no error
bar. Running all four folds gives the spread that criterion 2 ("moving the centre
by half an LED must hurt held-out by MORE than the spread between folds/seeds")
needs to be decidable at all.

`lattice_score` is copied VERBATIM from
`results/captura_2026-09-24/synth_overlap/run.py:19-28` so the periodic-artefact
score of the new runs is on the same scale as the synthetic control already
recorded in `synth_overlap/summary.json` (<= 0.0006) and as
`synth_overlap/real_geometry_scan.json` (0.0024-0.30 on real data).

Nothing in here touches the forward model or the solver.
"""
from __future__ import annotations

import os
import sys

import numpy as np

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))   # copia en scripts/fpm_solver/ (original: results/captura_2026-09-24/j3/common/)
if os.path.join(_REPO, "src") not in sys.path:
    sys.path.insert(0, os.path.join(_REPO, "src"))

from ptyco_full_simulator import config, led_array, optics, reconstruction  # noqa: E402
from ptyco_full_simulator.optics import circular_pupil  # noqa: E402
from ptyco_full_simulator.spectral_ops import led_crop_window  # noqa: E402

#: the 2026-09-24 capture's grid and the LED that `build_led_grid` puts first
#: (so `reconstruction.initial_hr_guess` uses it): with the measured centre
#: offset (0, 3) mm both bright-field LEDs sit 3 mm off axis and the tie is
#: broken row-major, giving (17, 15). It must never be held out.
INIT_LED = (17, 15)
N_FOLDS = 4
DECEMBER_FOLD = 1  # cv.py's hard-coded `i % 4 == 1`


def heldout_keys(all_keys, fold: int = DECEMBER_FOLD, n_folds: int = N_FOLDS,
                  always_in: tuple[int, int] = INIT_LED) -> set[tuple[int, int]]:
    """The LEDs held out for this fold: every `n_folds`-th key of
    `sorted(all_keys)` (row-major lexicographic -- the fixed order), except
    `always_in`. `fold=DECEMBER_FOLD` reproduces cv.py exactly."""
    if not 0 <= fold < n_folds:
        raise ValueError(f"fold must be in 0..{n_folds - 1}, got {fold}")
    ordered = sorted(all_keys)
    return {k for i, k in enumerate(ordered) if i % n_folds == fold and k != always_in}


def per_led_amplitude_residual(obj: np.ndarray, led_grid: list[dict],
                                lr_images: dict, hr_pixel_um: float,
                                lr_pixel_um: float, na: float,
                                wavelength_um: float) -> dict[tuple[int, int], float]:
    """{(row, col): ||est_amp - meas_amp|| / ||meas_amp||} for every LED of
    `led_grid` that has an image -- the same metric as
    `results/geometry_search_2025-12-12/gs.py:residuals`, i.e. the forward model
    evaluated once on the finished object, NOT the solver's own
    `recovery_error` (which is not comparable across upsampling factors, see the
    J3 brief's anti-goals)."""
    lr_shape = next(iter(lr_images.values())).shape
    spec = np.fft.fftshift(np.fft.fft2(obj))
    pupil = circular_pupil(lr_shape, lr_pixel_um, na, wavelength_um)
    out = {}
    for e in led_grid:
        key = (e["row"], e["col"])
        if key not in lr_images:
            continue
        ys, xs = led_crop_window(obj.shape, hr_pixel_um, lr_shape, e["fx"], e["fy"])
        est = np.abs(np.fft.ifft2(np.fft.ifftshift(spec[ys, xs] * pupil)))
        meas = np.sqrt(np.clip(lr_images[key], 0, None))
        out[key] = float(np.linalg.norm(est - meas) / max(np.linalg.norm(meas), 1e-12))
    return out


def cv_run(lr_images: dict, led_grid: list[dict], hr_pixel_um: float,
            lr_pixel_um: float, na: float, wavelength_um: float, factor: int,
            fold: int = DECEMBER_FOLD, iterations: int = 100,
            always_in: tuple[int, int] = INIT_LED,
            return_object: bool = False, **recon_kw) -> dict:
    """One CV fold: reconstruct WITHOUT the held-out LEDs, then score every LED.

    `recon_kw` goes straight to `reconstruction.reconstruct`; the J3 brief pins
    `step_relative=0.3` and `normalize_initial_guess=True` as mandatory, so they
    are the defaults here and a caller has to pass something else on purpose.
    """
    recon_kw.setdefault("step_relative", 0.3)
    recon_kw.setdefault("normalize_initial_guess", True)
    hold = heldout_keys(lr_images.keys(), fold=fold, always_in=always_in)
    train = {k: v for k, v in lr_images.items() if k not in hold}
    if (always_in not in train) and (always_in in lr_images):
        raise AssertionError(f"{always_in} must stay in the training set")
    train_grid = [e for e in led_grid if (e["row"], e["col"]) in train]
    res = reconstruction.reconstruct(train, train_grid, hr_pixel_um, lr_pixel_um,
                                      na, wavelength_um, factor,
                                      iterations=iterations, **recon_kw)
    obj = res["object"]
    r = per_led_amplitude_residual(obj, led_grid, lr_images, hr_pixel_um,
                                   lr_pixel_um, na, wavelength_um)
    tr = [v for k, v in r.items() if k not in hold]
    ho = [v for k, v in r.items() if k in hold]
    out = {
        "fold": fold, "iterations": iterations,
        "n_train": len(tr), "n_heldout": len(ho),
        "train_res": float(np.mean(tr)), "heldout_res": float(np.mean(ho)),
        "heldout_res_median": float(np.median(ho)),
        "lattice_score": lattice_score(obj),
        "heldout_leds": sorted(hold),
        "per_led_residual": {f"{k[0]},{k[1]}": v for k, v in sorted(r.items())},
        "recon_kw": {k: v for k, v in recon_kw.items()},
    }
    if return_object:
        out["object"] = obj
    return out


def cv_all_folds(lr_images: dict, led_grid: list[dict], hr_pixel_um: float,
                  lr_pixel_um: float, na: float, wavelength_um: float, factor: int,
                  n_folds: int = N_FOLDS, **kw) -> dict:
    """Every fold of the same data/geometry: mean and spread of the held-out
    score. The spread is what criterion 2 is compared against."""
    folds = [cv_run(lr_images, led_grid, hr_pixel_um, lr_pixel_um, na,
                    wavelength_um, factor, fold=f, **kw) for f in range(n_folds)]
    ho = [f["heldout_res"] for f in folds]
    tr = [f["train_res"] for f in folds]
    la = [f["lattice_score"] for f in folds]
    return {
        "n_folds": n_folds,
        "heldout_res_mean": float(np.mean(ho)), "heldout_res_std": float(np.std(ho)),
        "heldout_res_min": float(np.min(ho)), "heldout_res_max": float(np.max(ho)),
        "train_res_mean": float(np.mean(tr)), "train_res_std": float(np.std(tr)),
        "lattice_score_mean": float(np.mean(la)), "lattice_score_std": float(np.std(la)),
        "folds": folds,
    }


# --- copied VERBATIM from results/captura_2026-09-24/synth_overlap/run.py:19-28 ---
def lattice_score(o):
    """Fraction of HR spectral energy (outside the lowest 2% band) sitting in sharp isolated peaks:
    energy above 20x the local median, the signature of a periodic artefact."""
    from scipy.ndimage import median_filter
    P = np.abs(np.fft.fftshift(np.fft.fft2(np.abs(o) - np.abs(o).mean()))) ** 2
    H = P.shape[0]; yy, xx = np.mgrid[:H, :H] - H // 2
    m = np.hypot(yy, xx) > 0.02 * H
    loc = median_filter(P, size=9)
    peaks = (P > 20 * loc) & m
    return float(P[peaks].sum() / P[m].sum())
# --- end verbatim copy ---


# ---------------------------------------------------------------- geometry ----
GRID_SIZE, ROW_BASE, COL_BASE = 13, 12, 9
OBJECTIVE, CHANNEL = "2_5x_na007", "green"
NOMINAL_Z_MM, NOMINAL_OFFSET_MM = 75.0, (0.0, 3.0)


def green_setup(z_mm: float = NOMINAL_Z_MM, offset_mm=NOMINAL_OFFSET_MM, crop: int = 128,
                 channel: str = CHANNEL, objective: str = OBJECTIVE):
    """The 2026-09-24 capture's setup, one place only (2.5x/NA0.07, pitch 6,
    13x13 rows 12-24 cols 9-21, centre offset (0, 3) mm = the two bright-field
    LEDs (17,15)/(18,15) straddling the axis at row 17.5)."""
    return config.default_setup(channel, GRID_SIZE, objective=objective,
                                 resolution_px=(crop, crop),
                                 row_index_base=ROW_BASE, col_index_base=COL_BASE,
                                 z_distance_mm=z_mm, led_center_offset_mm=offset_mm)


def led_grid_rotated(setup, theta_deg: float = 0.0) -> list[dict]:
    """`led_array.build_led_grid` plus an in-plane rotation of the array about
    the optical axis, which `LEDArrayConfig` has no field for (T2 sweeps it).

        pos = R(theta) @ [(col-cc)*pitch, (row-cr)*pitch] + center_offset_mm

    i.e. the array rotates about its own nominal centre and the centre offset is
    applied after, exactly as `led_array.led_position_mm` composes them. At
    theta == 0 this returns bit-identical output to `build_led_grid` (checked in
    this file's __main__ self-test)."""
    cfg = setup.led_array
    lam = setup.wavelength_um
    if theta_deg == 0.0:
        return led_array.build_led_grid(cfg, lam)
    th = np.deg2rad(theta_deg)
    cs, sn = np.cos(th), np.sin(th)
    off_x, off_y = cfg.center_offset_mm
    entries = []
    for row in range(cfg.row_base, cfg.row_base + cfg.grid_size):
        for col in range(cfg.col_base, cfg.col_base + cfg.grid_size):
            x0 = (col - cfg.center_col) * cfg.pitch_mm
            y0 = (row - cfg.center_row) * cfg.pitch_mm
            dx = cs * x0 - sn * y0 + off_x
            dy = sn * x0 + cs * y0 + off_y
            d = np.sqrt(dx * dx + dy * dy + cfg.z_distance_mm ** 2)
            entries.append({"row": row, "col": col, "fx": dx / d / lam, "fy": dy / d / lam,
                            "radial_mm": float(np.hypot(dx, dy))})
    entries.sort(key=lambda e: e["radial_mm"])
    return entries


def scrambled_led_grid(led_grid: list[dict], seed: int,
                        always_in: tuple[int, int] = INIT_LED) -> list[dict]:
    """Negative control (cv.py's `scr` tag): permute the (fx, fy) of every LED
    but `always_in`. A geometry score that does not clearly beat this is not
    measuring geometry."""
    g = [dict(e) for e in led_grid]
    rng = np.random.default_rng(seed)
    rest = [e for e in g if (e["row"], e["col"]) != always_in]
    ks = [(e["fx"], e["fy"]) for e in rest]
    for e, j in zip(rest, rng.permutation(len(ks))):
        e["fx"], e["fy"] = ks[j]
    return g


def factor_for(setup) -> int:
    return optics.upsampling_factor(setup)


if __name__ == "__main__":
    s = green_setup()
    f = factor_for(s)
    print(f"factor={f} hr_px_um={optics.actual_hr_pixel_size_um(s, f):.4f} "
          f"lr_px_um={s.lr_pixel_size_um} na={s.objective.na} lam={s.wavelength_um}")
    a = led_array.build_led_grid(s.led_array, s.wavelength_um)
    b = led_grid_rotated(s, 0.0)
    assert a == b, "theta=0 must reproduce build_led_grid"
    # theta=0 taken through the rotation branch too (bypassing the shortcut)
    import copy
    s90 = green_setup()
    b2 = led_grid_rotated(s90, 1e-15)
    assert max(abs(x["fx"] - y["fx"]) + abs(x["fy"] - y["fy"]) for x, y in zip(a, b2)) < 1e-15
    print(f"grid[0]={a[0]['row']},{a[0]['col']} radial={a[0]['radial_mm']:.3f} "
          f"grid[1]={a[1]['row']},{a[1]['col']} radial={a[1]['radial_mm']:.3f}")
    assert (a[0]["row"], a[0]["col"]) == INIT_LED, a[0]
    keys = {(e["row"], e["col"]) for e in a}
    hold = {fd: heldout_keys(keys, fold=fd) for fd in range(N_FOLDS)}
    for fd, h in hold.items():
        print(f"fold {fd}: n_heldout={len(h)} (18,15) held out: {(18, 15) in h} "
              f"{INIT_LED} held out: {INIT_LED in h}")
    assert all(INIT_LED not in h for h in hold.values())
    assert sum(len(h) for h in hold.values()) == len(keys) - 1, "folds must partition"
    assert not set.intersection(*[set(h) for h in hold.values()])
    sc = scrambled_led_grid(a, 0)
    assert [(e["row"], e["col"]) for e in sc] == [(e["row"], e["col"]) for e in a]
    assert sorted((e["fx"], e["fy"]) for e in sc) == sorted((e["fx"], e["fy"]) for e in a)
    print("self-test OK")
