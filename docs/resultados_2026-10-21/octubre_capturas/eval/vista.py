"""vista.py -- fase/amplitud del full a la época EP (m2_red) junto al BF crudo, y R de entrenamiento por anillo vs 28/09b rojo_final.
Uso: python3 vista.py EP -> figs/vista_eEP.png"""
import json, os, sys, numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import comun as C
ep = int(sys.argv[1]); H = C.HERE
o = np.load(f'{C.OC}/out/rojo_final/{C.DS}/real_A+init_z98.0_full/obj_e{ep:03d}.npy').astype(complex)
F, geo, D = C.load()
def rings(p):
    for l in open(p):
        r = json.loads(l)
        if r['epoch'] == ep:
            b = {}
            for k, v in r['per_led'].items():
                if v[3]: b.setdefault(int(v[2]), []).append(v[0])
            return {q: float(np.mean(x)) for q, x in sorted(b.items())}
a = rings(f'{C.OC}/out/rojo_final/{C.DS}/real_A+init_z98.0_full/metrics.jsonl')
b = rings(f'{C.RES}/offset_color_2026-10-02/out/rojo_final/b_red/real_A+init_z98.0_full/metrics.jsonl')
print('R train por anillo', C.DS, {q: round(v, 3) for q, v in a.items()}); print('28b', {q: round(v, 3) for q, v in b.items()})
fig, ax = plt.subplots(1, 3, figsize=(15, 5))
raw = D['I'][(17, 15)]; ax[0].imshow(raw, cmap='gray'); ax[0].set_title('BF crudo (17,15)')
ax[1].imshow(np.abs(o), cmap='gray'); ax[1].set_title(f'amplitud e{ep}')
p = C.rel_phase(o); ax[2].imshow(p, cmap='twilight', vmin=-np.percentile(np.abs(p), 99.5), vmax=np.percentile(np.abs(p), 99.5)); ax[2].set_title(f'fase relativa e{ep}')
for x in ax: x.set_xticks([]); x.set_yticks([])
fig.tight_layout(); fig.savefig(f'{H}/../figs/vista_{C.DS}_e{ep}.png', dpi=60)
json.dump(dict(R_train_anillo=a, R_train_anillo_28b=b), open(f'{H}/vista_{C.DS}_e{ep}.json', 'w'), indent=1)
