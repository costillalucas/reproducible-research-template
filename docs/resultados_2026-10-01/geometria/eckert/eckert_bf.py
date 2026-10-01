"""Eckert 2018 BF self-calibration (fixed radius) on capture 28/09b, R/G/B. Read-only on code/data."""
import sys, os, json
import numpy as np
sys.path.insert(0, '/home/chanoscopio/Documents/LucasC/code/códigos_by_codex/paper_2018_autocalibracion')
import campo_claro as cb
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__))
CAP = '/home/chanoscopio/Documents/LucasC/reproducible-research-template/results/captura_2026-09-28b'
LAM = dict(red=0.63, green=0.53, blue=0.47); NA = 0.07; PX = 1.28; Z = 98.; PITCH = 6.; OFF = (0., 3.)
CROP = int(sys.argv[1]) if len(sys.argv) > 1 else 400
HW = float(sys.argv[2]) if len(sys.argv) > 2 else 12.

def nominal_sin(r, c, z=Z):
    dx = (c - 15) * PITCH + OFF[0]; dy = (r - 18) * PITCH + OFF[1]
    d = np.sqrt(dx*dx + dy*dy + z*z); return np.array([dx/d, dy/d])

cand = [(r, c) for r in range(15, 21) for c in range(12, 19)]
out = {}; allsrc = []; alltgt = []; tags = []
for col in ['red', 'green', 'blue']:
    d = np.load(f'{CAP}/{col}/prep.npz'); keys = [tuple(int(v) for v in k) for k in d['keys']]
    idx = [keys.index(k) for k in cand]
    S = d['S'][idx].astype(float)
    n0 = S.shape[1]; o = (n0 - CROP)//2
    S = np.clip(S[:, o:o+CROP, o:o+CROP], 0, None)
    fov = CROP * PX; R = NA / LAM[col] * fov; s2b = fov / LAM[col]   # sin -> bins
    proc, bf = cb.preprocess(S, R, 2.)
    nom = np.array([nominal_sin(*k) for k in cand])
    exp_b = nom * s2b
    ids = [i for i in range(len(cand)) if bf[i]]
    res = {}
    for i in ids:
        w, bnd = cb.locate(proc[i], S[i], exp_b[i], R, 2., HW)
        # pick the conjugate (+/-) closest to nominal (|FFT| centrosymmetric)
        if np.linalg.norm(-w - exp_b[i]) < np.linalg.norm(w - exp_b[i]): w = -w
        # mirror test: edge score at nominal vs x-mirrored nominal
        e_n = cb.edge_scores(proc[i], exp_b[i][None], R)[0][0]
        e_m = cb.edge_scores(proc[i], (exp_b[i]*[-1, 1])[None], R)[0][0]
        res[cand[i]] = dict(meas_sin=(w/s2b).tolist(), nom_sin=nom[i].tolist(), boundary=bool(bnd),
                            d_sin=((w/s2b)-nom[i]).tolist(), d_mm=(((w/s2b)-nom[i])*Z).tolist(),
                            edge_nom=float(e_n), edge_mirror=float(e_m), S_mean=float(S[i].mean()))
        allsrc.append(nom[i]); alltgt.append(w/s2b); tags.append(col)
    out[col] = dict(radius_bins=R, bf=[list(k) for k in cand if bf[cand.index(k)]], leds={f'{k[0]},{k[1]}': v for k, v in res.items()})
    # figure for one BF LED (17,14) if BF else first
    k = (17, 14) if (17, 14) in res else list(res)[0]; i = cand.index(k)
    fig, ax = plt.subplots(figsize=(5, 5)); h = CROP//2
    ax.imshow(proc[i], cmap='gray', extent=[-h, h, h, -h], vmin=np.percentile(proc[i], 1), vmax=np.percentile(proc[i], 99.5))
    t = np.linspace(0, 2*np.pi, 300)
    for c0, colr in ((exp_b[i], 'w'), (np.array(res[k]['meas_sin'])*s2b, 'r')):
        for sg in (1, -1):
            ax.plot(sg*c0[0] + R*np.cos(t), sg*c0[1] + R*np.sin(t), colr, lw=0.8, ls='-' if sg == 1 else ':')
    ax.set_title(f'{col} LED {k}: nominal (white) vs measured (red)'); ax.set_xlabel('kx bin (col)'); ax.set_ylabel('ky bin (row)')
    fig.savefig(f'{HERE}/spec_{col}_{k[0]}_{k[1]}_crop{CROP}.png', dpi=120); plt.close(fig)

def fit(src, tgt):
    src = np.asarray(src); tgt = np.asarray(tgt)
    p = cb.fit_similarity(src, tgt); r = cb.transform(src, p) - tgt
    a, b, tx, ty = p; s = np.hypot(a, b); rot = np.degrees(np.arctan2(b, a))
    x, y = src.T; D = np.zeros((2*len(x), 4))
    D[0::2] = np.column_stack((x, -y, np.ones(len(x)), np.zeros(len(x)))); D[1::2] = np.column_stack((y, x, np.zeros(len(x)), np.ones(len(x))))
    dof = max(2*len(x) - 4, 1); s2 = (r**2).sum()/dof; cov = s2*np.linalg.inv(D.T@D); se = np.sqrt(np.diag(cov))
    # pure-translation-only fit for comparison
    tr = (tgt - src).mean(0); rt = tgt - src - tr
    return dict(n=len(x), scale=s, scale_se=float(np.hypot(se[0], se[1])), z_mm=Z/s, rot_deg=rot,
                rot_se_deg=float(np.degrees(se[1]/s)), t_sin=[tx, ty], t_se=[se[2], se[3]], t_mm=[tx*Z, ty*Z],
                rms_resid_sin=float(np.sqrt((r**2).sum(1).mean())), rms_identity_sin=float(np.sqrt(((tgt-src)**2).sum(1).mean())),
                translation_only=dict(t_sin=tr.tolist(), t_mm=(tr*Z).tolist(), rms=float(np.sqrt((rt**2).sum(1).mean()))))
fits = {}
for col in ['red', 'green', 'blue']:
    m = [i for i, t in enumerate(tags) if t == col]
    if len(m) >= 3: fits[col] = fit(np.array(allsrc)[m], np.array(alltgt)[m])
fits['joint'] = fit(allsrc, alltgt)
out['fits'] = fits; out['crop'] = CROP; out['halfwidth'] = HW
json.dump(out, open(f'{HERE}/eckert_crop{CROP}.json', 'w'), indent=1, default=float)
for col in ['red', 'green', 'blue']:
    print(col, 'R=%.1f' % out[col]['radius_bins'], 'BF', out[col]['bf'])
    for k, v in out[col]['leds'].items():
        print('  ', k, 'meas', np.round(v['meas_sin'], 4), 'nom', np.round(v['nom_sin'], 4), 'dmm', np.round(v['d_mm'], 2), 'bnd', v['boundary'], 'edge n/m %.3g %.3g' % (v['edge_nom'], v['edge_mirror']))
for k, f in fits.items():
    print(k, {a: (np.round(b, 4) if not isinstance(b, dict) else {c: np.round(e, 4) for c, e in b.items()}) for a, b in f.items()})
