"""Ajuste de la frontera |sin|=NA en los flats sin muestra: borde de Fresnel (escala sqrt(lz/2)) * disco de diametro d."""
import json, os, numpy as np
from scipy.special import fresnel
from scipy.optimize import least_squares
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__))
D = np.load(f'{HERE}/flats_bin8.npz'); cand = [tuple(k) for k in D['cand']]
Z, NA, P, PX = 98.0, 0.07, 6.0, 1.28 * 8 / 1000     # mm
R0 = Z * np.tan(np.arcsin(NA))
LAM = dict(red=630e-6, green=530e-6, blue=470e-6)
n = D['red'].shape[1]; ax_ = (np.arange(n) - n / 2 + 0.5) * PX
Y, X = np.meshgrid(ax_, ax_, indexing='ij')           # Y = eje 0 (filas LED), X = eje 1 (columnas LED)
LEDS = [(17, 14), (17, 16), (18, 14), (18, 16), (16, 15)]
sg = np.arange(-3, 3, 0.001)
def perfil(lam, d):
    v = sg * np.sqrt(2 / (lam * Z)); S, C = fresnel(v)
    I = ((C + .5) ** 2 + (S + .5) ** 2) / 2
    d = min(d, 1.5)
    if d > 0.002:
        u = np.arange(-d / 2, d / 2 + 1e-9, 0.001); k = np.sqrt(np.clip(1 - (2 * u / d) ** 2, 0, None)); k /= k.sum()
        I = np.convolve(np.pad(I, len(k), mode='edge'), k, mode='same')[len(k):-len(k)]
    return I
def ancho1090(I):
    m = (sg > -1.5) & (sg < 1.5); s, i = sg[m], I[m]
    return float(np.interp(.9, np.maximum.accumulate(i), s) - np.interp(.1, np.maximum.accumulate(i), s))
def nom(k): return np.array([(k[1] - 15) * P, (k[0] - 17.5) * P])  # (x, y) mm
def modelo_basis(L, R, lam, d):
    s = R - np.hypot(X - L[0], Y - L[1]); pr = np.interp(s, sg, perfil(lam, d))
    return np.stack([pr, pr * X, pr * Y, np.ones_like(X)], -1).reshape(-1, 4)
def res_led(img, L, R, lam, d):
    A = modelo_basis(L, R, lam, d); y = img.ravel(); c, *_ = np.linalg.lstsq(A, y, rcond=None)
    return (A @ c - y) / img.max(), c
out = {}
for col in ['red', 'green', 'blue']:
    lam = LAM[col]; imgs = {k: D[col][cand.index(k)] for k in LEDS}
    o = dict(per_led={})
    for k in LEDS:
        img = imgs[k]
        f = lambda p: res_led(img, nom(k) + p[:2], R0, lam, abs(p[2]))[0]
        best = min((least_squares(f, [0, dy, d0], loss='soft_l1', f_scale=0.02, diff_step=1e-3)
                    for dy in (0.3, 1.0) for d0 in (0.1, 0.4)), key=lambda r: r.cost)
        L = nom(k) + best.x[:2]; dd = abs(best.x[2]); r_, c = res_led(img, L, R0, lam, dd)
        J = best.jac; cov = np.linalg.pinv(J.T @ J) * (r_ ** 2).mean()
        u = -L / np.linalg.norm(L)                                   # direccion opuesta al LED
        o['per_led'][f'{k}'] = dict(dx_mm=float(best.x[0]), dy_mm=float(best.x[1]), d_mm=dd, sig_d=float(np.sqrt(cov[2, 2])),
                                    frontera_desde_centro_um=float((R0 - np.linalg.norm(L)) * 1000),
                                    dir_unit=u.tolist(), ancho1090_um=ancho1090(perfil(lam, dd)) * 1000,
                                    contraste=float(c[0] / max(img.max(), 1e-9)), rms=float(np.sqrt((r_ ** 2).mean())))
    use = LEDS[:4]   # (16,15): frontera en el borde, ajuste individual no fiable
    for tag, freeR in (('conjunto_R_fijo', False), ('conjunto_R_libre', True)):
        def f(p):
            R = p[3] if freeR else R0
            return np.concatenate([res_led(imgs[k], nom(k) + p[:2], R, lam, abs(p[2]))[0] for k in use])
        r = least_squares(f, [0, 0.7, 0.2, R0], loss='soft_l1', f_scale=0.02, diff_step=1e-3)
        J = r.jac; cov = np.linalg.pinv(J.T @ J) * (r.fun ** 2).mean()
        o[tag] = dict(leds=[str(k) for k in use], dx_mm=float(r.x[0]), dy_mm=float(r.x[1]), d_mm=abs(float(r.x[2])),
                      R_mm=float(r.x[3] if freeR else R0), sig=np.sqrt(np.diag(cov)).tolist(),
                      ancho1090_um=ancho1090(perfil(lam, abs(r.x[2]))) * 1000, ancho1090_d0_um=ancho1090(perfil(lam, 0)) * 1000)
    out[col] = o
    # figura: datos, modelo, perfil radial
    fig, axs = plt.subplots(3, len(LEDS), figsize=(3.2 * len(LEDS), 9))
    J = out[col]['conjunto_R_libre']
    for i, k in enumerate(LEDS):
        img = imgs[k]; L = nom(k) + np.array([J['dx_mm'], J['dy_mm']])
        _, c = res_led(img, L, J['R_mm'], lam, J['d_mm']); mod = (modelo_basis(L, J['R_mm'], lam, J['d_mm']) @ c).reshape(n, n)
        ext = [ax_[0] * 1e3, ax_[-1] * 1e3, ax_[-1] * 1e3, ax_[0] * 1e3]
        axs[0, i].imshow(img, cmap='gray', extent=ext); axs[0, i].set_title(f'datos ({k[0]},{k[1]})', fontsize=9)
        axs[1, i].imshow(mod, cmap='gray', extent=ext); axs[1, i].set_title('modelo conjunto', fontsize=9)
        s = (J['R_mm'] - np.hypot(X - L[0], Y - L[1])) * 1e3
        axs[2, i].plot(s.ravel(), img.ravel() / c[0], ',', alpha=.3); axs[2, i].plot(s.ravel(), mod.ravel() / c[0], 'r,')
        axs[2, i].set_xlim(-600, 600); axs[2, i].set_xlabel('distancia a la frontera (µm, + = dentro)'); axs[2, i].set_ylim(-.2, 1.6)
        for a in axs[:2, i]: a.set_xlabel('x (µm)'); a.set_ylabel('y (µm)')
    fig.suptitle(f'{dict(red="Rojo",green="Verde",blue="Azul")[col]}: frontera |sinθ|=NA en flats sin muestra; '
                 f'Δx={J["dx_mm"]:+.3f} mm, Δy={J["dy_mm"]:+.3f} mm, R={J["R_mm"]:.3f} mm, d={J["d_mm"]*1e3:.0f} µm', fontsize=10)
    fig.tight_layout(); fig.savefig(f'{HERE}/ajuste_{col}.png', dpi=80); plt.close(fig)
json.dump(out, open(f'{HERE}/frontera.json', 'w'), indent=1)
for col in out:
    print(col)
    for k, v in out[col]['per_led'].items():
        print('  ', k, ' '.join(f'{a}={b:.3f}' if isinstance(b, float) else '' for a, b in v.items()))
    for t in ('conjunto_R_fijo', 'conjunto_R_libre'):
        v = out[col][t]; print('  ', t, v['leds'], 'dx %.3f dy %.3f d %.3f R %.3f' % (v['dx_mm'], v['dy_mm'], v['d_mm'], v['R_mm']),
                               'sig', np.round(v['sig'], 3), 'w1090 %.0f (d=0: %.0f) um' % (v['ancho1090_um'], v['ancho1090_d0_um']))
