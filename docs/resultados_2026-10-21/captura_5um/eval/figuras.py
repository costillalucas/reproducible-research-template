"""figuras.py -- figs/recon_r21_vs_m2.png (BF crudo, fase y amplitud de la reconstrucción full e160, recorte central de 100 µm, r21 vs
m2) y figs/heldout_anillos.png (R held-out por anillo con piso de ruido, e40, r21 / m2 / 28b; panel 2: control de offset en r21)."""
import json, os, sys
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__)); FIG = os.path.join(HERE, '..', 'figs')
import comun as C

rows = []
for ds, var, root in (('r21_red', 'rojo_centrado', C.OC), ('m2_red', 'rojo_final', C.OCO)):
    os.environ['DS'] = ds; C.DS = ds
    F, R = C.IR._load(ds); D = F.load_real()
    o = np.load(os.path.join(root, 'out', var, ds, 'real_A+init_z98.0_full', 'obj_e160.npy')).astype(complex)
    raw = np.sqrt(np.clip(D['I'][(17, 15)], 0, None)); f = o.shape[0] // raw.shape[0]
    rows.append((ds, np.real(F.fourier_upsample(raw, f)), C.rel_phase(o), np.abs(o)))
    sys.modules.pop('fpm_red', None); sys.path.remove(C.IR.DATASETS[ds][0])
n = int(100 / 0.43); c0 = 600 - n // 2
fig, ax = plt.subplots(2, 3, figsize=(12, 8.4))
for i, (ds, raw, ph, am) in enumerate(rows):
    for j, (im, tt, cm) in enumerate(((raw, 'BF (17,15) crudo (amplitud)', 'gray'), (ph, 'fase rel. (rad), e160', 'twilight'), (am, 'amplitud, e160', 'gray'))):
        x = im[c0:c0 + n, c0:c0 + n]; lo, hi = np.percentile(x, [1, 99.5])
        a = ax[i, j]; h = a.imshow(x, cmap=cm, vmin=lo, vmax=hi, extent=(0, 100, 100, 0)); a.set_title(f'{ds}: {tt}', fontsize=9)
        a.set_xlabel('µm'); plt.colorbar(h, ax=a, fraction=0.046)
plt.tight_layout(); plt.savefig(os.path.join(FIG, 'recon_r21_vs_m2.png'), dpi=110); plt.close()

H = json.load(open(os.path.join(HERE, 'heldout_anillos.json')))
fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
for nm, col in (('r21 centrado', 'C0'), ('m2 (16/10)', 'C1'), ('28/09b', 'C2')):
    k = f'{nm} e40'
    if k not in H:
        continue
    a = H[k]['anillos']; q = sorted(map(int, a))
    ax[0].plot(q, [a[str(x)]['R'] for x in q], 'o-', color=col, label=f'{nm}: C1 {H[k]["C1_media"]:.3f}')
    ax[0].plot(q, [a[str(x)]['piso'] for x in q], '--', color=col, lw=1)
ax[0].set_xlabel('anillo (pasos de LED desde el eje)'); ax[0].set_ylabel('R held-out (mediana); -- piso de ruido'); ax[0].legend(fontsize=8)
ax[0].set_title('held-out por anillo, 40 épocas', fontsize=10)
off = [(-0.6, 'r21 off -0.6'), (0.085, 'r21 centrado'), (0.6, 'r21 off +0.6'), (1.06, 'r21 off +1.06')]
pts = [(o, H[f'{n} e40']['C1_media'], H[f'{n} e40']['C1_sd']) for o, n in off if f'{n} e40' in H]
if pts:
    pts = np.array(pts); ax[1].errorbar(pts[:, 0], pts[:, 1], pts[:, 2], fmt='o-')
ax[1].set_xlabel('offset total del eje en filas (mm)'); ax[1].set_ylabel('C1 (R held-out medio, 5 folds)'); ax[1].set_title('r21: control de centrado (40 épocas)', fontsize=10)
plt.tight_layout(); plt.savefig(os.path.join(FIG, 'heldout_anillos.png'), dpi=110); plt.close()
print('ok')
