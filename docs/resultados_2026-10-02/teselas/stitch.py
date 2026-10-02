"""stitch.py -- cose teselas (fase global alineada en el solape, pluma lineal) y mide rayas/rampa/residuo vs full.
Uso: python3 stitch.py TAG EP"""
import glob, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
OC = os.path.join(HERE, "..", "offset_color_2026-10-02")
sys.path.insert(0, OC); sys.path.insert(0, os.path.join(HERE, "..", "iteraciones_2026-09-30"))
import rayas2, runner, iter_runner as IR


def feather(n, ov_lo, ov_hi):
    w = np.ones(n)
    if ov_lo: w[:ov_lo] = (np.arange(ov_lo) + 0.5) / ov_lo
    if ov_hi: w[n - ov_hi:] = ((np.arange(ov_hi) + 0.5) / ov_hi)[::-1]
    return w


def stitch(tag, ep):
    ds = sorted(glob.glob(os.path.join(HERE, "out", tag, "t*")))
    T = [(dict(y0=int(os.path.basename(d)[1:4]), x0=int(os.path.basename(d)[5:8]), tile=int(tag.split("_")[1]), factor=3), np.load(d + f"/obj_e{ep:03d}.npy").astype(complex)) for d in ds]
    f = T[0][0]["factor"]; tile = T[0][0]["tile"] * f; N = 400 * f
    ys = sorted({m["y0"] * f for m, _ in T}); xs = sorted({m["x0"] * f for m, _ in T})
    acc = np.zeros((N, N), complex); wacc = np.zeros((N, N)); ref = np.zeros((N, N), complex)
    for m, o in sorted(T, key=lambda t: (t[0]["y0"], t[0]["x0"])):
        y0, x0 = m["y0"] * f, m["x0"] * f
        iy, ix = ys.index(y0), xs.index(x0)
        ovy = lambda i: (ys[i - 1] + tile - ys[i]) if i > 0 else 0
        ovx = lambda i: (xs[i - 1] + tile - xs[i]) if i > 0 else 0
        wy = feather(tile, ovy(iy), ovy(iy + 1) if iy + 1 < len(ys) else 0)
        wx = feather(tile, ovx(ix), ovx(ix + 1) if ix + 1 < len(xs) else 0)
        sl = (slice(y0, y0 + tile), slice(x0, x0 + tile))
        have = wacc[sl] > 0
        if have.any():   # quitar constante de fase global relativa
            o = o * np.exp(-1j * np.angle(np.sum((o * np.conj(acc[sl] / np.maximum(wacc[sl], 1e-9)))[have])))
        W = np.outer(wy, wx)
        acc[sl] += W * o; wacc[sl] += W
    return acc / wacc, f


def measures(o, hrpx=0.4266666666666667, lam=0.63):
    r = rayas2.rayas(o.astype(np.complex64)); rp = runner.ramp(o, hrpx, lam)
    return dict(rayas_rms=r["rms_perfil_rad"], periodo_um=r["periodo_um"], mad=r["mad_fondo_rad"],
                rampa_ptp=rp["ptp"], dy_mm=rp["dy_mm"], dx_mm=rp["dx_mm"])


def train_R(o):
    F, R = IR._load("b_red"); D = F.load_real(); geo = F.geometry(98.0, offset_mm=(0, 4.06))
    pred = F.predict(o, D["keys"], geo)
    rs = {k: F.affine_residual(pred[k], D["I"][k], D["V"][k], D["mask"][k])[0] for k in D["keys"]}
    return float(np.mean(list(rs.values()))), {f"{k[0]},{k[1]}": rs[k] for k in [(18, 14), (18, 16), (18, 15), (17, 15)]}


if __name__ == "__main__":
    tag, ep = sys.argv[1], int(sys.argv[2])
    o, f = stitch(tag, ep)
    np.save(os.path.join(HERE, "out", tag, f"stitched_e{ep:03d}.npy"), o.astype(np.complex64))
    res = {"stitched": measures(o)}
    for d in sorted(glob.glob(os.path.join(HERE, "out", tag, "t*"))):
        res[os.path.basename(d)] = measures(np.load(d + f"/obj_e{ep:03d}.npy").astype(complex))
    for v in ("die", "die_sin18", "nominal_full"):
        p = os.path.join(OC, "out", v if v != "nominal_full" else "nominal", "b_red", "real_A+init_z98.0_full", f"obj_e{ep:03d}.npy")
        if v == "nominal_full":
            p = os.path.join(HERE, "..", "iteraciones_2026-09-30", "out", "b_red", "real_A+init_z98.0_full", f"obj_e{ep:03d}.npy")
        if os.path.exists(p):
            res[v] = measures(np.load(p).astype(complex))
    print(json.dumps(res, indent=1))
    json.dump(res, open(os.path.join(HERE, f"medidas_{tag}_e{ep:03d}.json"), "w"), indent=1)
