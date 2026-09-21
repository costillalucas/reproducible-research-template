"""Audit finding A1 (2026-09-21): the "GD 0.995 vs WF 0.076" measurement on exact-k data generates its data
with `joint_calibration.simulate_lr_stack_continuous`, the SAME operator the gradient-descent solver inverts (an
inverse crime for GD, and a model mismatch only for WF). This script generates the data with a forward model that
shares nothing with either solver's discretization and asks how much of GD's advantage survives.

Independent model (`simulate_independent`), physically motivated, all steps different from the solvers':
  * the object lives on a FINER grid (x S_OBJ, bicubic interpolation of the solver-grid truth, real and imaginary
    parts separately), so sub-HR-pixel structure and aliasing exist that the solver's grid cannot represent;
  * the LED tilt exp(-2 pi i (fx x + fy y)) is applied in real space on that fine grid at the exact continuous k
    (sign convention shared with the solvers -- it defines what k means);
  * the objective pupil has a raised-cosine edge EDGE_BINS wide (the solvers assume a hard circular mask);
  * the camera integrates intensity over the pixel area (S_CAM x S_CAM centred sub-samples of the band-limited
    field), the solvers point-sample it;
  * Poisson noise exactly as elsewhere (stack peak = `peak` expected counts).
`selfcheck` switches the three differences off (hard pupil, no pixel integration) and compares with the GD
operator, so a bug in this file cannot pass for "realistic mismatch".

Data models per (object, peak, seed):
  A same-op   : jc.simulate_lr_stack_continuous, exact k          (the milestone-14 / 0.995 regime)
  B indep     : simulate_independent, exact k                     (independent operator, real-hardware k)
  C indep-bin : simulate_independent, k rounded to a spectrum bin (isolates the operator mismatch from k)
  D wf-model  : forward_model.simulate_lr_stack, k rounded to bin (the bin-rounded model WF inverts; milestones 11-14)
Solvers, all given the TRUE positions (no calibration): GD-amplitude as shipped (`--solver gd-amplitude`,
jc.reconstruct_gradient_descent, 100 steps, lr 0.02), the same with lr 0.01 (the audit's tuned lr for the
full-batch amplitude cell), and Wirtinger flow with step_max 2 / 5 / 20 (100 epochs; 20 = the milestones 11-14
setting, 2 and 5 the tuned candidates of scripts/audit_wf_tuning_and_gd_ablation.py). Nothing is tuned here.

Usage (repo root, 1 core):
  python3 scripts/audit_independent_forward_model.py selfcheck
  python3 scripts/audit_independent_forward_model.py run out.jsonl      # resumable, JSON lines
  python3 scripts/audit_independent_forward_model.py summary out.jsonl
Not part of the provenance pipeline."""
import os
os.environ["OMP_NUM_THREADS"] = "1"; os.environ["OPENBLAS_NUM_THREADS"] = "1"; os.environ["MKL_NUM_THREADS"] = "1"
import sys, json, time, numpy as np
from scipy import ndimage
sys.path.insert(0, "src"); sys.path.insert(0, "tests")
from ptyco_full_simulator import config, forward_model, led_array, metrics, optics, reconstruction, joint_calibration as jc
from ptyco_full_simulator.test_objects import lena_map_object
from test_joint_calibration import _synthetic_object

CROP = 16
S_OBJ = 3        # object oversampling of the independent model
S_CAM = 5        # camera-pixel sub-samples per axis (odd, so the block is centred on the pixel)
EDGE_BINS = 1.0  # raised-cosine pupil edge width, in spectrum bins
ITERS = 100
SEEDS = range(3)
PEAK = 1000
GD_VARIANTS = (("gd_lr.02", 0.02), ("gd_lr.01", 0.01))
WF_VARIANTS = (("wf_s2", 2.0), ("wf_s5", 5.0), ("wf_s20", 20.0))
MODELS = ("A_same_op", "B_indep", "C_indep_bin", "D_wf_model")


def geometry():
    setup = config.default_setup(channel="green", grid_size=9, objective="current", resolution_px=(CROP, CROP))
    factor = optics.upsampling_factor(setup); hp = optics.actual_hr_pixel_size_um(setup, factor)
    hs = optics.hr_shape((CROP, CROP), factor)
    dk = 1 / (hs[1] * hp)
    grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    return dict(setup=setup, factor=factor, hp=hp, hs=hs, dk=dk, grid=grid,
                lp=setup.lr_pixel_size_um, na=setup.objective.na, wl=setup.wavelength_um)


def make_truth(obj_kind, hs):
    return _synthetic_object(hs) if obj_kind == "phantom" else lena_map_object(hs, phase_max_rad=0.3 * np.pi)[0]


def bin_aligned(grid, dk):
    return [{**e, "fx": round(e["fx"] / dk) * dk, "fy": round(e["fy"] / dk) * dk} for e in grid]


def _zoom_complex(a, s):
    kw = dict(order=3, mode="grid-wrap", grid_mode=True)
    return ndimage.zoom(a.real, s, **kw) + 1j * ndimage.zoom(a.imag, s, **kw)


def simulate_independent(truth, hp, grid, lr_shape, lp, na, wl, peak=None, rng=None,
                         s_obj=S_OBJ, s_cam=S_CAM, edge_bins=EDGE_BINS, integrate=True):
    """{(row, col): intensity} in object-amplitude^2 units (flat |object| = 1 gives 1), see module docstring.
    edge_bins=0 -> hard pupil; integrate=False -> point-sampled camera (both only for `selfcheck`)."""
    h, w = truth.shape
    fine = _zoom_complex(truth, s_obj)
    nh, nw = fine.shape
    # fine-pixel centres in the solver's frame (solver pixel i is centred at (i - h//2) * hp)
    Y, X = np.meshgrid(((np.arange(nh) - (s_obj - 1) / 2) / s_obj - h // 2) * hp,
                       ((np.arange(nw) - (s_obj - 1) / 2) / s_obj - w // 2) * hp, indexing="ij")
    ly, lx = lr_shape
    y0, x0 = nh // 2 - ly // 2, nw // 2 - lx // 2
    fy = np.fft.fftshift(np.fft.fftfreq(ly, d=lp)); fx = np.fft.fftshift(np.fft.fftfreq(lx, d=lp))
    FX, FY = np.meshgrid(fx, fy)
    r = np.hypot(FX, FY); c = na / wl; dkl = 1 / (lx * lp)
    if edge_bins > 0:
        half = edge_bins * dkl / 2
        pupil = np.where(r <= c - half, 1.0, np.where(r >= c + half, 0.0,
                         0.5 * (1 + np.cos(np.pi * (r - (c - half)) / (2 * half)))))
    else:
        pupil = (r <= c).astype(float)
    m = s_cam if integrate else 1
    my, mx = ly * m, lx * m
    out = {}
    for e in grid:
        tilt = np.exp(-2j * np.pi * (e["fx"] * X + e["fy"] * Y))
        c_k = np.fft.fftshift(np.fft.fft2(fine * tilt)) / (nh * nw)      # mean-normalised Fourier coefficients
        patch = c_k[y0:y0 + ly, x0:x0 + lx] * pupil
        padded = np.zeros((my, mx), complex)
        oy, ox = my // 2 - ly // 2, mx // 2 - lx // 2
        padded[oy:oy + ly, ox:ox + lx] = patch
        field = np.fft.ifft2(np.fft.ifftshift(padded)) * (my * mx)
        inten = np.abs(field) ** 2
        if integrate:
            inten = np.roll(inten, (m // 2, m // 2), axis=(0, 1))
            inten = inten.reshape(ly, m, lx, m).mean(axis=(1, 3))
        out[(e["row"], e["col"])] = inten
    pk = max(float(v.max()) for v in out.values())
    if peak is None or pk <= 0:
        return out
    rng = rng or np.random.default_rng()
    scale = peak / pk
    return {k: rng.poisson(v * scale).astype(float) / scale for k, v in out.items()}


def make_data(model, g, truth, peak, seed):
    """-> (images in object^2 units for GD, positions the solvers are given)."""
    rng = np.random.default_rng(seed) if peak is not None else None
    lr = (CROP, CROP)
    if model == "A_same_op":
        return jc.simulate_lr_stack_continuous(truth, g["hp"], g["grid"], lr, g["lp"], g["na"], g["wl"],
                                               peak_photon_count=peak, rng=rng), g["grid"]
    if model == "B_indep":
        return simulate_independent(truth, g["hp"], g["grid"], lr, g["lp"], g["na"], g["wl"], peak, rng), g["grid"]
    ba = bin_aligned(g["grid"], g["dk"])
    if model == "C_indep_bin":
        return simulate_independent(truth, g["hp"], ba, lr, g["lp"], g["na"], g["wl"], peak, rng), ba
    raw = forward_model.simulate_lr_stack(truth, g["hp"], ba, lr, g["lp"], g["na"], g["wl"],
                                          peak_photon_count=peak, rng=rng)
    return {k: v / g["factor"] ** 4 for k, v in raw.items()}, ba   # the WF model's units differ by factor^4


def score(o, truth):
    m = metrics.compare_to_ground_truth(o, truth)
    return {"ph": m["phase_correlation"], "rmse": m["phase_rmse_rad"], "amp": m["amplitude_correlation"]}


def run_solvers(g, images, positions, truth):
    raw = {k: v * g["factor"] ** 4 for k, v in images.items()}     # what the Wirtinger-flow model expects
    center = (positions[0]["row"], positions[0]["col"])
    init = jc.initial_object_from_center_led(images[center], g["hs"])
    row = {"init": score(init, truth)}
    for name, lr in GD_VARIANTS:
        o = jc.reconstruct_gradient_descent(images, positions, g["hp"], g["lp"], g["na"], g["wl"], g["factor"],
                                            iterations=ITERS, loss="amplitude", object_lr=lr)["object"]
        row[name] = score(o, truth)
    for name, sm in WF_VARIANTS:
        o = reconstruction.reconstruct(raw, positions, g["hp"], g["lp"], g["na"], g["wl"], g["factor"],
                                       iterations=ITERS, step_max=sm)["object"]
        row[name] = score(o, truth)
    return row


def selfcheck():
    g = geometry()
    print(f"factor {g['factor']}  hs {g['hs']}  hr pixel {g['hp']:.4f} um  pupil cutoff {g['na']/g['wl']/g['dk']:.2f} bins")
    for kind in ("phantom", "lenamap"):
        truth = make_truth(kind, g["hs"])
        ref = jc.simulate_lr_stack_continuous(truth, g["hp"], g["grid"], (CROP, CROP), g["lp"], g["na"], g["wl"])
        rms = lambda d: np.sqrt(np.mean([np.mean((d[k] - ref[k]) ** 2) for k in ref])) / np.sqrt(np.mean([np.mean(ref[k] ** 2) for k in ref]))
        common = (truth, g["hp"], g["grid"], (CROP, CROP), g["lp"], g["na"], g["wl"])
        print(f"{kind}: relative RMS intensity difference to the GD operator (all LEDs)")
        for label, kw in (("independent, hard pupil, point-sampled, fine object x1 (no interpolation)", dict(edge_bins=0, integrate=False, s_obj=1)),
                          ("independent, hard pupil, point-sampled, fine object x3", dict(edge_bins=0, integrate=False)),
                          ("+ pixel integration", dict(edge_bins=0)),
                          ("+ soft pupil edge (full independent model)", dict())):
            print(f"   {label:72s} {rms(simulate_independent(*common, **kw)):.4f}")


def main():
    mode = sys.argv[1]
    if mode == "selfcheck":
        return selfcheck()
    read = lambda p: [json.loads(l) for l in open(p)] if os.path.exists(p) else []
    if mode == "run":
        out = sys.argv[2]
        done = {(r["obj"], r["peak"], r["seed"]) for r in read(out)}
        g = geometry()
        for obj in ("phantom", "lenamap"):
            truth = make_truth(obj, g["hs"])
            for peak, seed in [(None, 0)] + [(PEAK, s) for s in SEEDS]:
                if (obj, peak, seed) in done:
                    continue
                t = time.time(); row = {"obj": obj, "peak": peak, "seed": seed}
                for model in MODELS:
                    images, positions = make_data(model, g, truth, peak, seed)
                    row[model] = run_solvers(g, images, positions, truth)
                row["secs"] = time.time() - t
                open(out, "a").write(json.dumps(row) + "\n")
                print(obj, peak, seed, f"{row['secs']:.0f}s", flush=True)
    elif mode == "summary":
        rows = read(sys.argv[2])
        names = ["init"] + [n for n, _ in GD_VARIANTS] + [n for n, _ in WF_VARIANTS]
        for obj in ("phantom", "lenamap"):
            for peak in (None, PEAK):
                rs = [r for r in rows if r["obj"] == obj and r["peak"] == peak]
                if not rs:
                    continue
                print(f"\n{obj}  peak {peak}  (n={len(rs)})  phase correlation mean+-sd [phase_rmse rad]")
                print(f"  {'':10s}" + "".join(f"{m:>26s}" for m in MODELS))
                for n in names:
                    cells = []
                    for m in MODELS:
                        ph = np.array([r[m][n]["ph"] for r in rs], float); rm = np.array([r[m][n]["rmse"] for r in rs], float)
                        cells.append(f"{np.nanmean(ph):+.3f}+-{np.nanstd(ph):.3f} [{np.nanmean(rm):.3f}]")
                    print(f"  {n:10s}" + "".join(f"{c:>26s}" for c in cells))


if __name__ == "__main__":
    main()
