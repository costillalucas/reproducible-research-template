import numpy as np, json, sys
from scipy.ndimage import gaussian_filter, map_coordinates
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
R = "/home/chanoscopio/Documents/LucasC/reproducible-research-template/results/captura_2026-09-28b/"
OUT = "/home/chanoscopio/Documents/LucasC/reproducible-research-template/results/geometria_2026-10-01/independiente/"
NA, PX, N, Z, PITCH = 0.07, 1.28, 400, 98.0, 6.0
LAMS = {"red":0.63,"red_foco_green":0.63,"red_foco_blue":0.63}
df = 1.0 / (N * PX)

def nominal(row, col):
    dx = (col - 15) * PITCH + 0.0; dy = (row - 18) * PITCH + 3.0
    D = np.sqrt(dx*dx + dy*dy + Z*Z); return dx / D, dy / D   # (sin_x, sin_y)

win = np.outer(np.hanning(N), np.hanning(N))
TH = np.linspace(0, 2*np.pi, 360, endpoint=False)

DD = 4.0
def score(L, c0, c1, rb, d=None):
    d = DD if d is None else d
    s = []
    for sg in (1, -1):
        p0, p1 = sg*c0 + rb*np.sin(TH), sg*c1 + rb*np.cos(TH)
        # keep only arc points outside the partner circle (where an edge exists)
        keep = np.hypot(p0 + sg*c0, p1 + sg*c1) > rb + d
        if keep.sum() < 20: return -1e9
        inn = map_coordinates(L, [N//2 + sg*c0 + (rb-d)*np.sin(TH[keep]), N//2 + sg*c1 + (rb-d)*np.cos(TH[keep])], order=1)
        out = map_coordinates(L, [N//2 + sg*c0 + (rb+d)*np.sin(TH[keep]), N//2 + sg*c1 + (rb+d)*np.cos(TH[keep])], order=1)
        s.append(inn - out)
    return float(np.mean(np.concatenate(s)))

def fit(L, rb, g0, g1, half=14, step=0.5):
    a = np.arange(-half, half + 1e-9, step)
    S = np.array([[score(L, g0+u, g1+v, rb) for v in a] for u in a])
    i, j = np.unravel_index(np.argmax(S), S.shape)
    def par(m, c, p):
        den = m - 2*c + p; return 0.0 if den == 0 else 0.5*(m - p)/den
    di = par(S[i-1, j], S[i, j], S[i+1, j]) if 0 < i < len(a)-1 else 0
    dj = par(S[i, j-1], S[i, j], S[i, j+1]) if 0 < j < len(a)-1 else 0
    edge = i in (0, len(a)-1) or j in (0, len(a)-1)
    return g0 + a[i] + di*step, g1 + a[j] + dj*step, S, edge

res = {}
for col_name, lam in LAMS.items():
    d = np.load(R + col_name + "/prep.npz")
    keys = [tuple(int(v) for v in k) for k in d["keys"]]
    S, F = d["S"], d["F"]
    means = np.array([S[i].mean() for i in range(len(keys))])
    order = np.argsort(means)[::-1]
    print(col_name, "top10 means:", [(keys[i], round(float(means[i]), 2)) for i in order[:10]])
    bf = [order[i] for i in range(6)]
    rb = NA / lam / df
    res[col_name] = []
    fig, axs = plt.subplots(2, 3, figsize=(13, 9))
    for ax, i in zip(axs.flat, sorted(bf, key=lambda i: keys[i])):
        f = F[i].astype(float); I = S[i].astype(float) / f * f.mean()
        I = (I - I.mean()) * win
        L = gaussian_filter(np.log(np.abs(np.fft.fftshift(np.fft.fft2(I))) + 1e-6), 2.0)
        sx, sy = nominal(*keys[i])
        # hypothesis: axis0 (rows) <-> y, axis1 (cols) <-> x
        n0, n1 = sy/lam/df, sx/lam/df
        # global coarse search over whole BF range for robustness, then local refine
        c0, c1, _, e1 = fit(L, rb, n0, n1, half=round(0.45*rb), step=1.0)
        m0, m1, Sg, edge = fit(L, rb, c0, c1, half=4, step=0.25)
        # resolve the +-k ambiguity with nominal
        if (m0-n0)**2 + (m1-n1)**2 > (m0+n0)**2 + (m1+n1)**2: m0, m1 = -m0, -m1
        msx, msy = m1*df*lam/NA*NA, m0*df*lam
        res[col_name].append(dict(led=keys[i], mean=float(means[i]), nom_sx=sx, nom_sy=sy,
                                  meas_sx=float(m1*df*lam), meas_sy=float(m0*df*lam), edge=bool(edge or e1)))
        h = 110
        ax.imshow(L[N//2-h:N//2+h, N//2-h:N//2+h], cmap="gray", extent=[-h-.5, h-.5, h-.5, -h-.5])
        for sg in (1, -1):
            ax.add_patch(plt.Circle((sg*n1, sg*n0), rb, fill=False, color="w", lw=1))
            ax.add_patch(plt.Circle((sg*m1, sg*m0), rb, fill=False, color="r", lw=1, ls="--"))
        ax.set_title(f"LED {keys[i]}  nom(sx,sy)=({sx/NA:.3f},{sy/NA:.3f})NA\nmed=({m1*df*lam/NA:.3f},{m0*df*lam/NA:.3f})NA", fontsize=9)
        ax.set_xlabel("kx bin (eje 1)"); ax.set_ylabel("ky bin (eje 0)")
    fig.suptitle(f"{col_name} λ={lam} µm: log|FFT| BF, blanco=nominal, rojo=ajuste (r=NA/λ fijo)")
    fig.tight_layout(); fig.savefig(OUT + f"fft_{col_name}.png", dpi=90); plt.close(fig)
json.dump(res, open(OUT + "medidas_foco.json", "w"), indent=1, default=str)
for c, rows in res.items():
    print("==", c)
    for r in rows:
        print(r["led"], "nom %.4f %.4f  med %.4f %.4f  edge=%s" % (r["nom_sx"]/NA, r["nom_sy"]/NA, r["meas_sx"]/NA, r["meas_sy"]/NA, r["edge"]))
    dx = np.mean([r["meas_sx"]-r["nom_sx"] for r in rows]); dy = np.mean([r["meas_sy"]-r["nom_sy"] for r in rows])
    sdx = np.std([r["meas_sx"]-r["nom_sx"] for r in rows]); sdy = np.std([r["meas_sy"]-r["nom_sy"] for r in rows])
    print("mean offset NA: (%.4f, %.4f) sd (%.4f,%.4f) ; mm: (%.2f, %.2f)" % (dx/NA, dy/NA, sdx/NA, sdy/NA, Z*dx, Z*dy))
