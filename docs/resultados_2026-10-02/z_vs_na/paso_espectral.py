"""z vs NA, captura 28/09b: paso angular entre LEDs vecinos medido en el espectro (FFT) de las
imagenes BF del recorte de 400 px (results/captura_2026-09-28b/<color>/prep.npz).
Por LED se ajusta centro (c0,c1) Y radio rb del circulo de pupila (score de borde de
docs/resultados_2026-10-01/geometria/independiente/medir.py, con su gemelo -k).
Luego, ajuste de red: c = c_off + (j, i) * s  (s = paso en bins por LED, igual en x e y)
  s  [bins] = (pitch / z) * N*dx / lam      -> z = pitch*N*dx/(lam*s)          (depende de dx!)
  rb [bins] = NA * N*dx / lam                -> NA = rb*lam/(N*dx)
  s/rb      = pitch/(z*NA)                   (independiente de dx: misma combinacion que la frontera)
Correr desde la raiz con nice 19. Solo CPU liviana (~1 min)."""
import numpy as np, json
from scipy.ndimage import gaussian_filter, map_coordinates
R = "results/captura_2026-09-28b/"
OUT = "results/z_vs_na_2026-10-02/"
PX, N, PITCH = 1.28, 400, 6.0
LAMS = dict(red=0.63, green=0.53, blue=0.47)
df = 1.0 / (N * PX)
win = np.outer(np.hanning(N), np.hanning(N))
TH = np.linspace(0, 2*np.pi, 360, endpoint=False)
DD = 3.0

def score(L, c0, c1, rb, d=DD):
    s = []
    for sg in (1, -1):
        p0, p1 = sg*c0 + rb*np.sin(TH), sg*c1 + rb*np.cos(TH)
        keep = np.hypot(p0 + sg*c0, p1 + sg*c1) > rb + d
        if keep.sum() < 20: return -1e9
        inn = map_coordinates(L, [N//2 + sg*c0 + (rb-d)*np.sin(TH[keep]), N//2 + sg*c1 + (rb-d)*np.cos(TH[keep])], order=1)
        out = map_coordinates(L, [N//2 + sg*c0 + (rb+d)*np.sin(TH[keep]), N//2 + sg*c1 + (rb+d)*np.cos(TH[keep])], order=1)
        s.append(inn - out)
    return float(np.mean(np.concatenate(s)))

def grid(L, g0, g1, rbs, half, step):
    a = np.arange(-half, half + 1e-9, step)
    best = (-1e18, None)
    for rb in rbs:
        for u in a:
            for v in a:
                sc = score(L, g0+u, g1+v, rb)
                if sc > best[0]: best = (sc, (g0+u, g1+v, rb))
    return best[1]

res = {}
for col, lam in LAMS.items():
    d = np.load(R + col + "/prep.npz")
    keys = [tuple(int(v) for v in k) for k in d["keys"]]
    S, F = d["S"], d["F"]
    means = np.array([S[i].mean() for i in range(len(keys))])
    order = np.argsort(means)[::-1]
    rb0 = 0.07 / lam / df
    rows = []
    for i in order[:6]:
        row, cc = keys[i]
        f = F[i].astype(float); I = S[i].astype(float) / f * f.mean()
        I = (I - I.mean()) * win
        L = gaussian_filter(np.log(np.abs(np.fft.fftshift(np.fft.fft2(I))) + 1e-6), 2.0)
        # nominal guess (z=98, offset (0,3) + die along rows ~1 mm)
        n0 = ((row - 18)*PITCH + 4.0) / 98 / lam / df; n1 = (cc - 15)*PITCH / 98 / lam / df
        c0, c1, rb = grid(L, n0, n1, [rb0], half=round(0.45*rb0), step=1.0)
        c0, c1, rb = grid(L, c0, c1, rb0*np.linspace(0.90, 1.12, 23), half=3, step=0.5)
        c0, c1, rb = grid(L, c0, c1, rb + np.arange(-0.6, 0.61, 0.15), half=0.75, step=0.125)
        if (c0-n0)**2 + (c1-n1)**2 > (c0+n0)**2 + (c1+n1)**2: c0, c1 = -c0, -c1
        rows.append(dict(led=[row, cc], mean=float(means[i]), c0=float(c0), c1=float(c1), rb=float(rb)))
        print(col, (row, cc), "c=(%.2f,%.2f) rb=%.2f (nom %.2f)" % (c0, c1, rb, rb0), flush=True)
    # lattice fit: c0 = a0 + s*row, c1 = a1 + s*col  (common s)
    A, b = [], []
    for r in rows:
        A.append([1, 0, r["led"][0]]); b.append(r["c0"])
        A.append([0, 1, r["led"][1]]); b.append(r["c1"])
    A, b = np.array(A, float), np.array(b)
    p, *_ = np.linalg.lstsq(A, b, rcond=None)
    resid = b - A @ p; dof = len(b) - 3
    cov = np.linalg.inv(A.T @ A) * (resid @ resid / max(dof, 1))
    s, ss = p[2], np.sqrt(cov[2, 2])
    rbm = np.mean([r["rb"] for r in rows]); rbs = np.std([r["rb"] for r in rows], ddof=1) / np.sqrt(len(rows))
    z = PITCH * N * PX / (lam * s); sz = z * ss / s
    NA = rbm * lam / (N * PX); sNA = NA * rbs / rbm
    ratio = s / rbm
    res[col] = dict(leds=rows, step_bins=s, step_se=ss, resid_rms_bins=float(np.sqrt(np.mean(resid**2))),
                    rb_bins=rbm, rb_se=rbs, rb_nominal=rb0,
                    z_mm_if_dx128=z, z_se=sz, NA_if_dx128=NA, NA_se=sNA,
                    zNA_from_ratio_mm=PITCH / ratio, zNA_se=PITCH/ratio*np.hypot(ss/s, rbs/rbm))
    print(col, json.dumps({k: v for k, v in res[col].items() if k != "leds"}, indent=1), flush=True)
json.dump(res, open(OUT + "paso_espectral.json", "w"), indent=1)
