"""montaje2.py -- BF (17,15) recorte 400 (resolución completa) y DF (20,15) (bin 4) de los sets de muestra candidatos. figs/montaje_bf400.png"""
import os, numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__)); RES = os.path.abspath(os.path.join(HERE, '..', '..'))
S = ['2026-10-09-d', '2026-10-09-e', '2026-10-09-muestra', '2026-10-16-a', '2026-10-16-muestra2', '2026-10-20-muestra']
fig, axs = plt.subplots(2, 4, figsize=(16, 8))
for a, s in zip(axs.flat, S):
    d = np.load(f'{HERE}/{s}.npz'); nm = [n for n in d.files if n.startswith('full_17_15_')][0]; bf = d[nm][360:760, 360:760]
    a.imshow(bf, cmap='gray', vmin=np.percentile(bf, 0.5), vmax=np.percentile(bf, 99.5)); a.set_title(s, fontsize=9)
pz = np.load(f'{RES}/captura_2026-09-28b/red/prep.npz'); pk = [tuple(map(int, k)) for k in pz['keys']]
im = pz['S'][pk.index((17, 15))].astype(float); axs.flat[6].imshow(im, cmap='gray', vmin=np.percentile(im, .5), vmax=np.percentile(im, 99.5)); axs.flat[6].set_title('28/09b rojo')
d = np.load(f'{HERE}/2026-10-20-luzsinmuestra.npz'); bf = d['full_17_15_5'][360:760, 360:760]
axs.flat[7].imshow(bf, cmap='gray', vmin=np.percentile(bf, 0.5), vmax=np.percentile(bf, 99.5)); axs.flat[7].set_title('2026-10-20-luzsinmuestra')
for a in axs.flat: a.set_xticks([]); a.set_yticks([])
fig.tight_layout(); fig.savefig(f'{HERE}/../figs/montaje_bf400.png', dpi=55)
