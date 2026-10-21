"""montaje.py -- BF (17,15) cuadro completo y DF (20,15) / (21,17) (recorte 400, bin 4) de cada set, más 28/09b. figs/montaje_sets.png"""
import glob, os, numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__)); RES = os.path.abspath(os.path.join(HERE, '..', '..'))
S = sorted(os.path.basename(p)[:-4] for p in glob.glob(f'{HERE}/2026-*.npz') if 'oscura' not in p and 'sinluz' not in p)
fig, axs = plt.subplots(len(S) + 1, 3, figsize=(9, 3 * (len(S) + 1)))
for row, s in zip(axs, S):
    d = np.load(f'{HERE}/{s}.npz'); keys = [tuple(k) for k in d['keys']]
    nm = [n for n in d.files if n.startswith('full_17_15_')][0]; bf = d[nm]
    row[0].imshow(bf, cmap='gray', vmin=np.percentile(bf, 1), vmax=np.percentile(bf, 99.5)); row[0].set_title(f'{s}\nBF (17,15) completo', fontsize=8)
    row[0].add_patch(plt.Rectangle((360, 360), 400, 400, fill=False, ec='y'))
    for a, k in zip(row[1:], [(20, 15), (21, 17)]):
        im = d['sm'][keys.index(k)]; a.imshow(im, cmap='gray', vmin=np.percentile(im, 1), vmax=np.percentile(im, 99.5))
        a.set_title(f'DF {k} t={d["t"][keys.index(k)]} ms, media {im.mean():.0f}', fontsize=8)
pz = np.load(f'{RES}/captura_2026-09-28b/red/prep.npz'); pk = [tuple(map(int, k)) for k in pz['keys']]
for a, k in zip(axs[-1], [(17, 15), (20, 15), (21, 17)]):
    im = pz['S'][pk.index(k)].astype(float); a.imshow(im, cmap='gray', vmin=np.percentile(im, 1), vmax=np.percentile(im, 99.5)); a.set_title(f'28/09b rojo {k} (recorte 400, c/ms)', fontsize=8)
for a in axs.flat: a.set_xticks([]); a.set_yticks([])
fig.tight_layout(); fig.savefig(f'{HERE}/../figs/montaje_sets.png', dpi=60)
