"""metricas.py -- métricas por config (out/<cfg>/): escribe metricas.json e imprime la tabla.

  P_verdad   período (µm) donde FRC complejo(full, verdad) cae bajo 1/7 (la verdad = objeto HR del fantoma)
  P_mitades  período (µm) donde FRC complejo(half0, half1) cae bajo 1/7 (como el 3.55 µm real)
  C2         media del FRC entre mitades en [2NA/λ, 0.45] 1/µm (umbral 0.143, como criterios_b.py)
  vol        mediana |V_rec/V_verdad - 1| de partículas aisladas d >= 3 µm (fase desenvuelta en ventana,
             fondo = mediana del anillo r+2.5..r+4.5 µm, integral en disco r+1.5 µm; misma receta en la verdad)
  vol_s      ídem para los dispersores de 1.2 µm (mediana de V_rec/V_verdad, con signo)
  R_ho       residuo afín medio en las LEDs DF retenidas del fold0 (fpm_red.affine_residual), y piso de ruido
  P_v40      P_verdad a 40 épocas (convergencia)
"""
import glob
import json
import os
import sys

import numpy as np
from skimage.restoration import unwrap_phase

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run as RN  # noqa: E402
import sim as S  # noqa: E402

PX = S.LRPX / S.FACTOR
LO = 2 * S.NA / S.LAM


def volumes(o, sph, L):
    H = o.shape[0]
    yy, xx = (np.mgrid[:H, :H] + 0.5) * PX
    out = []
    for i, (cy, cx, d) in enumerate(sph):
        r = d / 2
        iso = all(np.hypot(cy - a, cx - b) > r + e / 2 + 5 for j, (a, b, e) in enumerate(sph) if j != i)
        if not iso:
            out.append(None); continue
        w = r + 5
        sl = (slice(max(int((cy - w) / PX), 0), int((cy + w) / PX) + 1),
              slice(max(int((cx - w) / PX), 0), int((cx + w) / PX) + 1))
        ph = unwrap_phase(np.angle(o[sl]))
        rr = np.hypot(yy[sl] - cy, xx[sl] - cx)
        bg = np.median(ph[(rr > r + 2.5) & (rr < r + 4.5)])
        out.append(float(np.sum(ph[rr < r + 1.5] - bg) * PX * PX))
    return out


def one(cfg):
    od = os.path.join(HERE, "out", cfg)
    need = [f"obj_{k}.npy" for k in ("full", "half0", "half1")]
    if not all(os.path.exists(os.path.join(od, n)) for n in need):
        return None
    ld = lambda n: np.load(os.path.join(od, n)).astype(complex)  # noqa: E731
    tr = ld("truth.npy"); full = ld("obj_full.npy"); h0 = ld("obj_half0.npy"); h1 = ld("obj_half1.npy")
    meta = json.load(open(os.path.join(od, "meta.json")))
    ph = json.load(open(os.path.join(od, "phantom.json")))
    sph, L = [tuple(s) for s in ph["sph"]], ph["L"]
    fv = S.frc(full, tr, PX); fh = S.frc(h0, h1, PX)
    res = dict(cfg=cfg, P_verdad=S.frc_period(fv), P_mitades=S.frc_period(fh), C2=S.band_mean(fh, LO, 0.45),
               C2_verdad=S.band_mean(fv, LO, 0.45), capture_s=meta["capture_s"], n_used=meta["n_used"],
               n_bf=meta["n_bf"], sat_px=int(sum(meta["sat_px"].values())))
    e40 = os.path.join(od, "obj_full_e040.npy")
    if os.path.exists(e40):
        res["P_v40"] = S.frc_period(S.frc(ld("obj_full_e040.npy"), tr, PX))
    vt, vr = volumes(tr, sph, L), volumes(full, sph, L)
    big = [(b / a - 1) for (cy, cx, d), a, b in zip(sph, vt, vr) if a is not None and d >= 3 and a > 0]
    sm = [(b / a) for (cy, cx, d), a, b in zip(sph, vt, vr) if a is not None and d < 1.3 and a > 0]
    res.update(vol=float(np.median(np.abs(big))), vol_sesgo=float(np.median(big)), n_vol=len(big),
               vol_s=float(np.median(sm)) if sm else None, n_s=len(sm))
    # held-out
    g, pol, err, bud = cfg.split("__")
    if not os.path.exists(os.path.join(od, "obj_fold0.npy")):
        res.update(R_ho=np.nan, R_floor=np.nan, n_ho=0)
        return res
    q = RN.geometry(g, RN.ERRS[err])
    d = np.load(os.path.join(od, "data.npz"))
    use = [tuple(int(v) for v in k) for k in d["keys"]]
    trn = set(map(tuple, json.load(open(os.path.join(od, "rec_fold0.json")))["train"]))
    ho = [k for k in use if k not in trn]
    pred = S.predict(ld("obj_fold0.npy"), q["fxy"], ho, RN.N_LR)
    rs, fl = [], []
    for k in ho:
        i = use.index(k)
        r, f = S.affine_residual(pred[k], d["I"][i].astype(float), float(d["V"][i]), d["M"][i])
        rs.append(r); fl.append(f)
    res.update(R_ho=float(np.mean(rs)), R_floor=float(np.mean(fl)), n_ho=len(ho))
    return res


if __name__ == "__main__":
    cfgs = sorted(os.path.basename(p) for p in glob.glob(os.path.join(HERE, "out", "*__*")))
    old = {}
    fj = os.path.join(HERE, "metricas.json")
    if os.path.exists(fj):
        old = {r["cfg"]: r for r in json.load(open(fj))}
    rows = []
    for c in cfgs:
        r = old.get(c) or one(c)
        if r:
            rows.append(r)
    json.dump(rows, open(fj, "w"), indent=1)
    print(f"{'config':32s} {'Pver':>5s} {'Pv40':>5s} {'Pmit':>5s} {'C2':>6s} {'C2ver':>6s} {'vol':>6s} {'sesgo':>6s} "
          f"{'vol_s':>5s} {'R_ho':>6s} {'piso':>6s} {'t_s':>5s} {'nLED':>4s} {'nBF':>3s} {'sat':>5s}")
    for r in rows:
        print(f"{r['cfg']:32s} {r['P_verdad']:5.2f} {r.get('P_v40', np.nan):5.2f} {r['P_mitades']:5.2f} {r['C2']:6.3f} "
              f"{r['C2_verdad']:6.3f} {r['vol']:6.3f} {r['vol_sesgo']:+6.3f} {r['vol_s'] or np.nan:5.2f} {r['R_ho']:6.3f} "
              f"{r['R_floor']:6.3f} {r['capture_s']:5.0f} {r['n_used']:4d} {r['n_bf']:3d} {r['sat_px']:5d}")
