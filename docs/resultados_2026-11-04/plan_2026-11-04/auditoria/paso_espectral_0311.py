"""Auditoría ítem 2: paso espectral entre LEDs BF vecinos en la MISMA captura 03/11 (no la del 28/09).
Método = docs/resultados_2026-10-02/z_vs_na/paso_espectral.py (score de borde, centro y radio libres), copiado aquí
con N 400, dx 1.29, guess nominal z 102 eje (17,15). Usa datos/prep.npz de 2026-11-03-red_1311 (recorte 360:760, 80:480)."""
import numpy as np, json
from scipy.ndimage import gaussian_filter, map_coordinates
P = "/home/chanoscopio/Documents/AleYLu/reconstrucciones/2026-11-03-red_1311/datos/prep.npz"
PX, N, PITCH, lam = 1.29, 400, 6.0, 0.63
df = 1.0 / (N * PX); win = np.outer(np.hanning(N), np.hanning(N))
TH = np.linspace(0, 2 * np.pi, 360, endpoint=False); DD = 3.0
def score(L, c0, c1, rb, d=DD):
    s = []
    for sg in (1, -1):
        p0, p1 = sg * c0 + rb * np.sin(TH), sg * c1 + rb * np.cos(TH)
        keep = np.hypot(p0 + sg * c0, p1 + sg * c1) > rb + d
        if keep.sum() < 20: return -1e9
        inn = map_coordinates(L, [N // 2 + sg * c0 + (rb - d) * np.sin(TH[keep]), N // 2 + sg * c1 + (rb - d) * np.cos(TH[keep])], order=1)
        out = map_coordinates(L, [N // 2 + sg * c0 + (rb + d) * np.sin(TH[keep]), N // 2 + sg * c1 + (rb + d) * np.cos(TH[keep])], order=1)
        s.append(inn - out)
    return float(np.mean(np.concatenate(s)))
def grid(L, g0, g1, rbs, half, step):
    a = np.arange(-half, half + 1e-9, step); best = (-1e18, None)
    for rb in rbs:
        for u in a:
            for v in a:
                sc = score(L, g0 + u, g1 + v, rb)
                if sc > best[0]: best = (sc, (g0 + u, g1 + v, rb))
    return best[1]
d = np.load(P); keys = [tuple(int(v) for v in k) for k in d["keys"]]
BF = [(17, 15), (16, 15), (17, 14), (17, 16), (18, 15)]
rb0 = 0.0669 / lam / df; rows = []
for k in BF:
    i = keys.index(k); f = d["F"][i].astype(float); I = d["S"][i].astype(float) / f * f.mean()
    I = (I - I.mean()) * win
    L = gaussian_filter(np.log(np.abs(np.fft.fftshift(np.fft.fft2(I))) + 1e-6), 2.0)
    n0 = (k[0] - 17) * PITCH / 102 / lam / df; n1 = ((k[1] - 15) * PITCH + 0.529) / 102 / lam / df
    c0, c1, rb = grid(L, n0, n1, [rb0], half=round(0.45 * rb0), step=1.0)
    c0, c1, rb = grid(L, c0, c1, rb0 * np.linspace(0.90, 1.15, 26), half=3, step=0.5)
    c0, c1, rb = grid(L, c0, c1, rb + np.arange(-0.6, 0.61, 0.15), half=0.75, step=0.125)
    if (c0 - n0) ** 2 + (c1 - n1) ** 2 > (c0 + n0) ** 2 + (c1 + n1) ** 2: c0, c1 = -c0, -c1
    rows.append(dict(led=list(k), c0=float(c0), c1=float(c1), rb=float(rb))); print(k, "c=(%.2f,%.2f) rb=%.2f (nom %.2f)" % (c0, c1, rb, rb0), flush=True)
g = {tuple(r["led"]): r for r in rows}
s_col = (g[(17, 16)]["c1"] - g[(17, 14)]["c1"]) / 2; s_row = (g[(18, 15)]["c0"] - g[(16, 15)]["c0"]) / 2
rb = np.mean([r["rb"] for r in rows]); rbs = np.std([r["rb"] for r in rows], ddof=1)
out = dict(leds=rows, s_col_bins=s_col, s_row_bins=s_row, rb_bins=rb, rb_sd=rbs)
for nom, s in (("col", s_col), ("fila", s_row)):
    out[f"z_{nom}_mm"] = PITCH * N * PX / (lam * s)
out["NA_radio_dx1.29"] = rb * lam / (N * PX)
out["zNA_mm_col"] = out["z_col_mm"] * out["NA_radio_dx1.29"]
print(json.dumps(out, indent=1)); json.dump(out, open("paso_espectral_0311.json", "w"), indent=1)
