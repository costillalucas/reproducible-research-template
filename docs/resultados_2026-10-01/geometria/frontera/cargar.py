"""Carga flats sin muestra (28/09b, organizado, cuadro completo 1120), resta oscuro, /t, binning 8 -> cache + montajes."""
import glob, os, numpy as np, tifffile as T
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
B = os.path.expanduser('~/Documents/AleYLu/imagenes_tomadas')
FL = f'{B}/2026-09-28.b_rgb_sin_muestra/organizado'; DK = f'{B}/2026-09-28.b_dark/fila18_col15_colorb'
PX, BIN = 1.28, 8
HERE = os.path.dirname(os.path.abspath(__file__))
dk = {}
def dark(t):
    if t not in dk:
        dk[t] = np.mean([T.imread(f).astype(float) for f in sorted(glob.glob(f'{DK}/{t}ms/imagen_frame_*.tiff'))], 0)
    return dk[t]
cand = [(r, c) for r in range(15, 21) for c in range(12, 19)]
out = {}
for col in ['red', 'green', 'blue']:
    imgs = []
    for k in cand:
        fs = [f for f in glob.glob(f'{FL}/{col}/*ms/fila{k[0]}_col{k[1]}.tiff')]
        t, f = max((int(os.path.basename(os.path.dirname(f))[:-2]), f) for f in fs)
        a = T.imread(f).astype(float) + 0.5          # organizado = floor(mean de 2)
        sat = (a >= 4094).mean()
        im = (a - dark(t)) / t
        im = im.reshape(1120 // BIN, BIN, 1120 // BIN, BIN).mean((1, 3))
        imgs.append(im); print(col, k, t, 'sat %.4f' % sat, 'mean %.2f' % im.mean())
    out[col] = np.array(imgs)
    fig, axs = plt.subplots(6, 7, figsize=(14, 12.5))
    for ax, k, im in zip(axs.flat, cand, out[col]):
        lo, hi = np.percentile(im, [1, 99.5])
        ax.imshow(im, cmap='gray', vmin=lo, vmax=hi); ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(f'({k[0]},{k[1]})  media {im.mean():.1f}', fontsize=8)
        n = im.shape[0]; L = 500 / (PX * BIN)
        ax.plot([n * .05, n * .05 + L], [n * .93] * 2, 'y-', lw=2)
    axs[0, 0].text(3, 120, '500 µm', color='y', fontsize=7)
    fig.suptitle(f'Flats sin muestra 28/09b, {dict(red="rojo",green="verde",blue="azul")[col]}: cuadro completo (1.43 mm), '
                 'oscuro restado, /t, escala propia por panel (filas 15–20, columnas 12–18)', fontsize=10)
    fig.tight_layout(); fig.savefig(f'{HERE}/montaje_{col}.png', dpi=80); plt.close(fig)
np.savez_compressed(f'{HERE}/flats_bin8.npz', cand=np.array(cand), **out)
