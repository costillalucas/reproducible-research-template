"""Shared helpers for the plan_*.py experiment skeletons (see
docs/plan_experimentos_punto3_y_hardware_real.md). Not part of the
provenance pipeline. Import with `sys.path.insert(0, "scripts")`."""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
import sys, dataclasses, numpy as np
sys.path.insert(0, "src")
from ptyco_full_simulator import (config, forward_model, led_array, metrics, optics,
                                   reconstruction, joint_calibration as jc)
from ptyco_full_simulator.test_objects import lena_map_object, _load_resized, DEFAULT_DATA_DIR


def build_setup(channel="green", grid_size=9, objective="current", crop=32,
                pitch_mm=None, span_mm=None, z_mm=None):
    """SetupConfig for the lab hardware with optional geometry overrides.
    `span_mm` (LED array side) wins over `pitch_mm`: pitch = span/(N-1),
    which holds the outermost LED -- hence the HR canvas -- fixed while the
    LED count changes."""
    s = config.default_setup(channel=channel, grid_size=grid_size, objective=objective,
                             resolution_px=(crop, crop))
    if span_mm is not None:
        pitch_mm = span_mm / (grid_size - 1)
    kw = {"grid_size": grid_size, "pitch_mm": pitch_mm if pitch_mm is not None else s.led_array.pitch_mm,
          "z_distance_mm": z_mm if z_mm is not None else s.led_array.z_distance_mm}
    return dataclasses.replace(s, led_array=config.LEDArrayConfig(**kw))


def geometry(setup, crop):
    factor = optics.upsampling_factor(setup)
    hp = optics.actual_hr_pixel_size_um(setup, factor)
    hs = optics.hr_shape((crop, crop), factor)
    return factor, hp, hs


def bin_align(grid, hs, hp):
    """Round each LED's k to a spectrum bin (the model Wirtinger flow
    inverts; 'fair' comparison used in all milestone 11-14 sweeps)."""
    dk = 1 / (hs[1] * hp)
    return [{**e, "fx": round(e["fx"] / dk) * dk, "fy": round(e["fy"] / dk) * dk} for e in grid]


def make_object(kind, hs, phase_max_rad, min_amplitude=0.1):
    """Complex test objects. Returns (object, phase). Kinds:
    lena_map (amp=Lena, phase=Map), map_lena (swapped roles), phase_only
    (amp=1, phase=Map), blob (smooth Gaussian bumps, amp+phase),
    siemens_star (phase-only star, sharp radial detail)."""
    if kind == "lena_map":
        return lena_map_object(hs, phase_max_rad, min_amplitude)
    lena = _load_resized(os.path.join(DEFAULT_DATA_DIR, "Lena_512.png"), hs)
    mp = _load_resized(os.path.join(DEFAULT_DATA_DIR, "Map_512.tiff"), hs)
    norm = lambda a: (a - a.min()) / max(np.ptp(a), 1e-12)
    yy, xx = np.mgrid[0:hs[0], 0:hs[1]]
    if kind == "map_lena":
        amp = min_amplitude + (1 - min_amplitude) * norm(mp)
        ph = phase_max_rad * norm(lena)
    elif kind == "phase_only":
        amp = np.ones(hs)
        ph = phase_max_rad * norm(mp)
    elif kind == "blob":
        cy, cx = hs[0] / 2, hs[1] / 2
        g = lambda y0, x0, s: np.exp(-((yy - y0) ** 2 + (xx - x0) ** 2) / (2 * (s * hs[0]) ** 2))
        b = g(cy * .8, cx * .8, .12) + .8 * g(cy * 1.2, cx * 1.15, .09)
        amp = min_amplitude + (1 - min_amplitude) * (1 - .6 * norm(b))
        ph = phase_max_rad * norm(b)
    elif kind == "siemens_star":
        th = np.arctan2(yy - hs[0] / 2, xx - hs[1] / 2)
        r = np.hypot(yy - hs[0] / 2, xx - hs[1] / 2)
        star = (np.sin(12 * th) > 0) & (r < .45 * hs[0])
        amp = np.ones(hs)
        ph = phase_max_rad * star.astype(float)
    else:
        raise ValueError(kind)
    return amp * np.exp(1j * ph), ph


def simulate_exact_k(truth, hp, grid, lr_shape, lp, na, wl, peak=None, rng=None):
    """Continuous-k forward model (what real hardware produces) + optional
    Poisson noise. Output stays in object intensity units (counts/scale) so
    it feeds jc.* directly."""
    clean = jc.simulate_lr_stack_continuous(truth, hp, grid, lr_shape, lp, na, wl)
    if peak is None:
        return clean
    pk = max(float(v.max()) for v in clean.values())
    s = peak / pk
    rng = rng or np.random.default_rng()
    return {k: rng.poisson(v * s).astype(float) / s for k, v in clean.items()}


def perturbed_grid(setup, wl, hs, hp, rng, z_err_mm=0.0, offset_mm=(0.0, 0.0), rot_deg=0.0,
                   pitch_err_frac=0.0, jitter_mm=0.0):
    """TRUE LED positions = nominal geometry + physically-parametrized
    errors (the solver is later handed the NOMINAL grid). Errors: array
    height error, lateral offset of the whole array, in-plane rotation,
    pitch scale error, iid per-LED placement jitter. Returns
    (true_grid, rms_k_error_in_bins vs nominal)."""
    cfg = setup.led_array
    nominal = led_array.build_led_grid(cfg, wl)
    th = np.deg2rad(rot_deg)
    out = []
    for e in nominal:
        dx, dy = led_array.led_position_mm(e["row"], e["col"], cfg)
        dx, dy = dx * (1 + pitch_err_frac), dy * (1 + pitch_err_frac)
        dx, dy = dx * np.cos(th) - dy * np.sin(th), dx * np.sin(th) + dy * np.cos(th)
        dx += offset_mm[0] + rng.normal(0, jitter_mm)
        dy += offset_mm[1] + rng.normal(0, jitter_mm)
        d = np.sqrt(dx ** 2 + dy ** 2 + (cfg.z_distance_mm + z_err_mm) ** 2)
        out.append({**e, "fx": dx / d / wl, "fy": dy / d / wl})
    dk = 1 / (hs[1] * hp)
    err = np.array([[t["fx"] - n["fx"], t["fy"] - n["fy"]] for t, n in zip(out, nominal)]) / dk
    return out, float(np.sqrt(np.mean(np.sum(err ** 2, axis=1))))


def k_error_bins(grid_a, grid_b, hs, hp):
    dk = 1 / (hs[1] * hp)
    d = np.array([[a["fx"] - b["fx"], a["fy"] - b["fy"]] for a, b in zip(grid_a, grid_b)]) / dk
    return float(np.sqrt(np.mean(np.sum(d ** 2, axis=1))))


def score(rec, truth):
    m = metrics.compare_to_ground_truth(rec, truth)
    return {"phase_corr": m["phase_correlation"], "amp_corr": m["amplitude_correlation"],
            "phase_rmse": m["phase_rmse_rad"]}
