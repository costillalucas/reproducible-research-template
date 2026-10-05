"""zernike.py -- descompone la pupila recuperada (out/<run>/pupil_eXXX.npy) en Zernikes de orden bajo (Noll, rms=1
sobre el disco) y convierte a unidades físicas. También perfil radial de |P|.

Uso: python3 zernike.py RUN [RUN ...]   -> imprime y escribe zernike.json
"""
from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np
from skimage.restoration import unwrap_phase

HERE = os.path.dirname(os.path.abspath(__file__))


def zbasis(r, t):
    s3, s6, s8, s5 = np.sqrt(3), np.sqrt(6), np.sqrt(8), np.sqrt(5)
    return {
        "Z1_piston": np.ones_like(r),
        "Z2_tilt_x": 2 * r * np.cos(t),
        "Z3_tilt_y": 2 * r * np.sin(t),
        "Z4_defocus": s3 * (2 * r ** 2 - 1),
        "Z5_astig_45": s6 * r ** 2 * np.sin(2 * t),
        "Z6_astig_0": s6 * r ** 2 * np.cos(2 * t),
        "Z7_coma_y": s8 * (3 * r ** 3 - 2 * r) * np.sin(t),
        "Z8_coma_x": s8 * (3 * r ** 3 - 2 * r) * np.cos(t),
        "Z11_spherical": s5 * (6 * r ** 4 - 6 * r ** 2 + 1),
    }


def analyse(pfile, geo):
    P = np.load(pfile).astype(complex)
    sup = np.abs(P) > 0
    yy, xx = np.indices(P.shape)
    cy, cx = yy[sup].mean(), xx[sup].mean()
    rpx = np.sqrt(sup.sum() / np.pi)                      # radio del soporte en bins
    r = np.hypot(yy - cy, xx - cx) / rpx
    t = np.arctan2(yy - cy, xx - cx)                      # x = columnas, y = filas
    ph = np.ma.array(np.angle(P), mask=~sup)
    ph = np.asarray(unwrap_phase(ph).filled(0.0))
    w = np.abs(P)[sup]
    B = zbasis(r[sup], t[sup])
    A = np.stack(list(B.values()), 1)
    sw = np.sqrt(w)
    c, *_ = np.linalg.lstsq(A * sw[:, None], ph[sup] * sw, rcond=None)
    coef = dict(zip(B.keys(), map(float, c)))
    fit = A @ c
    resid = ph[sup] - fit
    lam, na, lrpx = geo["lam"], geo["na"], geo["lrpx"]
    N = P.shape[0]
    kedge = na / lam                                       # ciclos/µm en el borde
    # defocus: fase cuadrática pi*lam*dz*rho^2 ; en el borde pi*dz*NA^2/lam = 2*sqrt3*c4
    dz_um = 2 * np.sqrt(3) * coef["Z4_defocus"] * lam / (np.pi * na ** 2)
    # tilt: fase 2*c*r = 2*pi*rho*dx -> dx = c/(pi*kedge)
    dx_um = coef["Z2_tilt_x"] / (np.pi * kedge)
    dy_um = coef["Z3_tilt_y"] / (np.pi * kedge)
    # perfil radial de |P|
    edges = np.linspace(0, 1, 11)
    prof = [float(np.abs(P)[sup & (r >= a) & (r < b)].mean()) for a, b in zip(edges[:-1], edges[1:])]
    amp = np.abs(P)[sup]
    # radio efectivo de la amplitud: sqrt(sum|P|^2 / max^2 / pi) en bins
    # (normalizado por la media de |P|^2 en r < 0.3, no por el máximo, que es un píxel suelto)
    ref = float(np.mean(np.abs(P[sup & (r < 0.3)]) ** 2))
    r_eff_px = float(np.sqrt((np.abs(P) ** 2).sum() / ref / np.pi))
    return dict(file=os.path.relpath(pfile, HERE), support_radius_bins=float(rpx), bin_cyc_per_um=1 / (N * lrpx),
                zernike_rad=coef, phase_rms_rad=float(np.sqrt(np.average((ph[sup] - coef["Z1_piston"]) ** 2, weights=w))),
                resid_rms_after_lowZ_rad=float(np.sqrt(np.average(resid ** 2, weights=w))),
                phase_ptp_edge_defocus_rad=float(2 * np.sqrt(3) * coef["Z4_defocus"]),
                defocus_dz_um=float(dz_um), tilt_shift_um=[float(dx_um), float(dy_um)],
                amp_mean=float(amp.mean()), amp_std_rel=float(amp.std() / amp.mean()),
                amp_radial_profile_10bins=[p / prof[0] for p in prof], r_eff_amp_bins=r_eff_px,
                dof_um=float(lam / na ** 2))


if __name__ == "__main__":
    out = {}
    for run in sys.argv[1:]:
        d = os.path.join(HERE, "out", run)
        geo = json.load(open(os.path.join(d, "done.json")))["geo"]
        for f in sorted(glob.glob(os.path.join(d, "pupil_e*.npy"))):
            res = analyse(f, geo)
            out[res["file"]] = res
            z = res["zernike_rad"]
            print(f"{res['file']}: rms {res['phase_rms_rad']:.3f} rad, resid {res['resid_rms_after_lowZ_rad']:.3f}; "
                  + " ".join(f"{k.split('_',1)[0]} {v:+.3f}" for k, v in z.items() if k != "Z1_piston")
                  + f" | dz {res['defocus_dz_um']:+.1f} µm (DOF {res['dof_um']:.0f}) tilt {res['tilt_shift_um'][0]:+.2f},"
                  f"{res['tilt_shift_um'][1]:+.2f} µm | |P| radial {np.round(res['amp_radial_profile_10bins'], 2).tolist()}"
                  f" r_eff {res['r_eff_amp_bins']:.1f}/{res['support_radius_bins']:.1f} bins", flush=True)
    path = os.path.join(HERE, "zernike.json")
    old = json.load(open(path)) if os.path.exists(path) else {}
    old.update(out)
    json.dump(old, open(path, "w"), indent=1)
