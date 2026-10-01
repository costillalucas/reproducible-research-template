"""Revisión independiente: C2 (FRC propia + F.frc), C2 por teselas, estabilidad de bajas, fondo lento, colores con
corrimiento por snapshot. Lee obj_eNNN.npy. Uso: nice -n 19 python3 rev_obj.py [c2|stab|col]"""
import json, os, sys, importlib.util
import numpy as np
from scipy import ndimage as ndi
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(H, "out"); B = os.path.join(H, "..", "captura_2026-09-28b")
LAM = {"red": 0.63, "green": 0.53, "blue": 0.47}; NA = 0.07
SN = [0, 2, 3, 5, 8, 12, 20, 30, 40, 60, 80, 120, 160, 240, 320, 400]
def ld(c, t, e): return np.load(f"{OUT}/b_{c}/real_A+init_z98.0_{t}/obj_e{e:03d}.npy")
def px(c): return json.load(open(f"{OUT}/b_{c}/real_A+init_z98.0_full/done.json"))["hrpx"]
def F_(c):
    s = importlib.util.spec_from_file_location("F" + c, f"{B}/{c}/fpm_red.py"); F = importlib.util.module_from_spec(s); s.loader.exec_module(F); return F
def kgrid(n, p):
    f = np.fft.fftfreq(n, p); return np.hypot(*np.meshgrid(f, f, indexing="ij"))
def frc_band(a, b, p, lo, hi, nb=60):
    """FRC propia: media de los anillos (60 bins hasta kmax como F.frc) con centro en [lo,hi)."""
    n = a.shape[0]; A = np.fft.fft2(a - a.mean()); Bb = np.fft.fft2(b - b.mean()); k = kgrid(n, p)
    edges = np.linspace(0, k.max(), nb + 1); idx = np.digitize(k.ravel(), edges) - 1
    num = np.abs(np.bincount(idx, (A * np.conj(Bb)).ravel().real, nb + 1) + 1j * np.bincount(idx, (A * np.conj(Bb)).ravel().imag, nb + 1))
    den = np.sqrt(np.bincount(idx, np.abs(A.ravel()) ** 2, nb + 1) * np.bincount(idx, np.abs(Bb.ravel()) ** 2, nb + 1)) + 1e-30
    c = 0.5 * (edges[:-1] + edges[1:]); v = (num / den)[:nb]; m = (c >= lo) & (c < hi)
    return float(v[m].mean())
def c2():
    res = {}
    for c, lam in LAM.items():
        F = F_(c); p = px(c); lo = 2 * NA / lam; r = {}
        for e in SN:
            h0, h1, s0, s1 = (ld(c, t, e) for t in ("half0", "half1", "half0_scr", "half1_scr"))
            off = F.band_mean(F.frc(h0, h1, p), lo, 0.45); offn = F.band_mean(F.frc(s0, s1, p), lo, 0.45)
            mine = frc_band(h0, h1, p, lo, 0.45); minen = frc_band(s0, s1, p, lo, 0.45)
            # teselas 3x3 con ventana de Hann, interior (descarta borde n/12)
            n = h0.shape[0]; bd = n // 12; T = (n - 2 * bd) // 3; w = np.outer(np.hanning(T), np.hanning(T)); tl = []; tn = []
            for i in range(3):
                for j in range(3):
                    sl = (slice(bd + i * T, bd + (i + 1) * T), slice(bd + j * T, bd + (j + 1) * T))
                    tl.append(frc_band(h0[sl] * w, h1[sl] * w, p, lo, 0.45, nb=30))
                    tn.append(frc_band(s0[sl] * w, s1[sl] * w, p, lo, 0.45, nb=30))
            r[e] = dict(C2_F=off, C2n_F=offn, C2_mine=mine, C2n_mine=minen, tiles=tl, tiles_null=tn)
            print(c, e, f"F {off:.4f} ({offn:.4f}) mine {mine:.4f} ({minen:.4f}) tiles {np.mean(tl):.4f}+-{np.std(tl):.4f} null {np.mean(tn):.4f}", flush=True)
            del h0, h1, s0, s1
        res[c] = r
    json.dump(res, open(f"{H}/revision/rev_c2.json", "w"))
def lp(a, k, kmax): return np.real(np.fft.ifft2(np.fft.fft2(a) * (k <= kmax)))
def corr(a, b, m):
    a, b = a[m] - a[m].mean(), b[m] - b[m].mean(); return float(np.sum(a * b) / np.sqrt(np.sum(a * a) * np.sum(b * b)))
def stab():
    res = {}
    for c, lam in LAM.items():
        p = px(c); O = {e: ld(c, "full", e) for e in (5, 20, 40, 60, 80, 120, 240, 400)}
        n = O[40].shape[0]; bd = n // 12; m = np.zeros((n, n), bool); m[bd:-bd, bd:-bd] = True; k = kgrid(n, p)
        A = {e: np.abs(o) for e, o in O.items()}
        r = {}
        for e in O:
            # bajas = <= NA/lam ; "muy lento" = <= 0.02 1/um (escalas > 50 um); "medio" = (0.02, NA/lam]
            r[e] = dict(corr_bajas_400=corr(lp(A[e], k, NA / lam), lp(A[400], k, NA / lam), m),
                        corr_muylento_400=corr(lp(A[e], k, 0.02), lp(A[400], k, 0.02), m),
                        corr_medio_400=corr(lp(A[e], k, NA / lam) - lp(A[e], k, 0.02), lp(A[400], k, NA / lam) - lp(A[400], k, 0.02), m))
        # descomposición del cambio de amplitud 40->400 y 40->120 por banda (fracción de energía del cambio)
        for a_, b_ in ((40, 120), (40, 400), (5, 40)):
            d = A[b_] - A[a_]; d = d - d[m].mean(); D = np.fft.fft2(d * m); P = np.abs(D) ** 2; tot = P.sum()
            r[f"dA_{a_}_{b_}"] = dict(frac_muylento=float(P[k <= 0.02].sum() / tot), frac_medio=float(P[(k > 0.02) & (k <= NA / lam)].sum() / tot),
                                     frac_hasta_2NA=float(P[(k > NA / lam) & (k < 2 * NA / lam)].sum() / tot),
                                     frac_C2=float(P[(k >= 2 * NA / lam) & (k < 0.45)].sum() / tot), frac_resto=float(P[k >= 0.45].sum() / tot),
                                     rel_norm=float(np.linalg.norm(d[m]) / np.linalg.norm(A[a_][m])))
        res[c] = r; print(c, json.dumps(r, default=float), flush=True)
    json.dump(res, open(f"{H}/revision/rev_stab.json", "w"), default=float)
def to_grid(o, n=1200):
    Hh = o.shape[0]
    if Hh == n: return o
    S = np.fft.fftshift(np.fft.fft2(o)); a = (Hh - n) // 2
    return np.fft.ifft2(np.fft.ifftshift(S[a:a + n, a:a + n])) * (n / Hh) ** 2
def shift_sub(a, s):
    n = a.shape[0]; f = np.fft.fftfreq(n); fy, fx = np.meshgrid(f, f, indexing="ij")
    return np.real(np.fft.ifft2(np.fft.fft2(a) * np.exp(-2j * np.pi * (fy * s[0] + fx * s[1]))))
def register(a, b, up=10):
    """corrimiento de a respecto de b (a ≈ b corrido s): correlación de fase con refinamiento parabólico."""
    R = np.fft.fft2(a) * np.conj(np.fft.fft2(b)); R /= np.abs(R) + 1e-12; rr = np.real(np.fft.ifft2(R)); n = a.shape[0]
    i = np.array(np.unravel_index(np.argmax(rr), rr.shape)); s = []
    for ax in (0, 1):
        im = i.copy(); ip = i.copy(); im[ax] -= 1; ip[ax] = (ip[ax] + 1) % n
        y0, ym, yp = rr[tuple(i)], rr[tuple(im)], rr[tuple(ip)]
        s.append(((i[ax] + n // 2) % n - n // 2) + 0.5 * (ym - yp) / (ym - 2 * y0 + yp))
    return np.array(s)
def col():
    sh = json.load(open(f"{B}/comparar_colores.json"))["reconstrucciones"]; fix = {"red": sh["corrimiento_red_px_HR"], "blue": sh["corrimiento_blue_px_HR"]}
    n = 1200; P = 512.0 / n; k = kgrid(n, P); m = np.zeros((n, n), bool); m[100:-100, 100:-100] = True; kb = 0.07 / 0.63
    res = {}
    for e in SN:
        A = {c: np.abs(to_grid(ld(c, "full", e))) for c in LAM}
        hp = {c: A[c] - ndi.gaussian_filter(A[c], 20) for c in LAM}
        r = {}
        for c in ("red", "blue"):
            s = register(hp[c], hp["green"])
            fixed = np.roll(A[c], tuple(-np.array(fix[c])), (0, 1)); own = shift_sub(A[c], -s)
            r[c] = dict(shift=s.tolist(), corr_fijo=corr(lp(fixed, k, kb), lp(A["green"], k, kb), m), corr_propio=corr(lp(own, k, kb), lp(A["green"], k, kb), m))
        sr = register(hp["red"], hp["blue"])
        r["red_blue"] = dict(shift=sr.tolist(), corr_propio=corr(lp(shift_sub(A["red"], -sr), k, kb), lp(A["blue"], k, kb), m))
        res[e] = r; print(e, json.dumps(r), flush=True)
    json.dump(res, open(f"{H}/revision/rev_col.json", "w"))
if __name__ == "__main__":
    for a in sys.argv[1:]: {"c2": c2, "stab": stab, "col": col}[a]()
