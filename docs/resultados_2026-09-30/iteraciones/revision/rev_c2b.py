"""Tendencias de C2 por tesela (pareadas) y C2 del campo entero con ventana de Hann sobre el interior."""
import json, numpy as np, sys
sys.path.insert(0, "."); import rev_obj as R
d = json.load(open("rev_c2.json"))
for c, pairs in (("red", ((40, 400), (20, 400))), ("green", ((20, 400), (20, 40))), ("blue", ((40, 400), (20, 400)))):
    for a, b in pairs:
        t = np.array(d[c][str(b)]["tiles"]) - np.array(d[c][str(a)]["tiles"]); tn = np.array(d[c][str(b)]["tiles_null"]) - np.array(d[c][str(a)]["tiles_null"])
        print(c, a, "->", b, "tiles diff", np.round(t, 3).tolist(), f"mean {t.mean():+.4f} se {t.std(ddof=1)/3:.4f} n_up {np.sum(t>0)}/9 | null diff mean {tn.mean():+.4f}")
    print(c, "tiles at 40:", np.round(d[c]["40"]["tiles"], 3).tolist())
for c, lam in R.LAM.items():
    p = R.px(c); lo = 2 * R.NA / lam
    for e in (20, 40, 120, 400):
        h0, h1 = R.ld(c, "half0", e), R.ld(c, "half1", e); n = h0.shape[0]; bd = n // 12; s = slice(bd, n - bd); w = np.outer(np.hanning(n - 2 * bd), np.hanning(n - 2 * bd))
        a, b = h0[s, s], h1[s, s]
        print(c, e, f"hann-interior C2 {R.frc_band((a - a.mean()) * w, (b - b.mean()) * w, p, lo, 0.45):.4f}  interior-sin-ventana {R.frc_band(a, b, p, lo, 0.45):.4f}", flush=True)
