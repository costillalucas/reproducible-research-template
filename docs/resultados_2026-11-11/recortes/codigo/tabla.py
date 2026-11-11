"""tabla.py -- tabla por partícula (markdown) y resúmenes por grupo (con / sin LED que cambia BF/DF a 20 px). Lee medidas.json."""
import json, numpy as np
P0 = "/home/chanoscopio/Documents/AleYLu/reconstrucciones/plan_2026-11-11/recortes/"
M = json.load(open(P0 + "medidas.json"))
def f(r, k, d=1):
    v = r.get(k + "_fwhm"); ok = r.get(k + "_ok", True)
    return "—" if v is None or not np.isfinite(v) else (f"{v:.{d}f}" + ("" if ok else "×"))
print("| id | vecino µm | LR | 200 amp | 200 fase | 20 amp | 20 fase | 20 corr amp/cplx | LED que cambia (20 px) | 20 sin ese LED amp / corr cplx | 40 amp | 80 amp | nulo 200 amp / fase | nulo 20 amp |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for r in M:
    c = r.get("c20_cambian", [])
    print(f"| {r['id']} | {r['vecino_um']:.0f} | {f(r,'LR')} | {f(r,'ref200_amp')} | {f(r,'ref200_fase')} | {f(r,'c20_amp')} | {f(r,'c20_fase')} | "
          f"{r['c20_corr_amp']:.2f} / {r['c20_corr_cplx']:.2f} | {', '.join(f'({a},{b})' for a,b in c) or 'ninguno'} | "
          f"{f(r,'c20_sincambian_amp')} / {r['c20_sincambian_corr_cplx']:.2f} | {f(r,'c40_amp')} | {f(r,'c80_amp')} | "
          f"{f(r,'nulo200_amp')} / {f(r,'nulo200_fase')} | {f(r,'c20_nulo_amp')} |")
def st(rows, k):
    v = np.array([r[k] for r in rows if k in r and np.isfinite(r[k]) and r.get(k.replace("_fwhm", "_ok"), True)])
    return f"{np.median(v):.2f} [{np.percentile(v,25):.2f}–{np.percentile(v,75):.2f}] n={len(v)}" if len(v) else "—"
for nom, g in (("con cambio", [r for r in M if r.get("c20_cambian")]), ("sin cambio", [r for r in M if not r.get("c20_cambian")])):
    print("\n" + nom, len(g))
    for k in ("c20_amp_fwhm", "c20_fase_fwhm", "c20_corr_amp", "c20_corr_cplx", "c20_err_final", "c20_sincambian_corr_cplx", "ref200_amp_fwhm", "ref200_fase_fwhm"):
        print(f"  {k:28s} {st(g, k)}")
# razones por partícula
for a, b in (("ref200_amp", "LR"), ("c20_amp", "ref200_amp"), ("c20_sincambian_amp", "ref200_amp"), ("c40_amp", "ref200_amp"), ("c20_fase", "ref200_fase")):
    v = np.array([r[a + "_fwhm"] / r[b + "_fwhm"] for r in M if r.get(a + "_ok") and r.get(b + "_ok", True) and (a + "_fwhm") in r and np.isfinite(r[a + "_fwhm"])])
    print(f"razón {a}/{b}: mediana {np.median(v):.2f} [{np.percentile(v,25):.2f}–{np.percentile(v,75):.2f}] n={len(v)}")
