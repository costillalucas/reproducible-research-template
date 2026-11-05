"""resumen.py -- junta resultados/res_*.json en resumen.json + tabla (markdown, a stdout) y hace fig_sim_borde.png."""
import os
import sys
import glob
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(BASE, 'resultados')
CMM, PITCH = 0.001696, 6.0
ERF_POR_LOG = 4 / np.sqrt(2 * np.pi) * np.sqrt(2)   # w_erf = 2.257·escala logística (misma pendiente en el centro)

rs = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(RES, 'res_*.json')))]
casos = sorted({(r['nombre'], r['NA'], r['z'], r['w']) for r in rs}, key=lambda c: (c[0][0], c[3]))


def ms(v):
    v = np.array(v, float)
    return float(v.mean()), (float(v.std(ddof=1)) if v.size > 1 else float('nan')), v.tolist()


tab = []
for (nom, NA, z, w) in casos:
    rr = [r for r in rs if r['nombre'] == nom]
    fila = dict(caso=nom, NA=NA, z=z, w=w, NAz=NA * z, n=len(rr),
                R_borde_verdad=z * NA / np.sqrt(1 - NA ** 2) / PITCH, sat=float(np.mean([r['frac_sat'] for r in rr])))
    for etq in ('ruido', 'sin_ruido'):
        for m in ('esp_nt', 'esp_pw', 'esp_nt_ancho'):
            for c in ('NAz_fila', 'NAz_col', 'NAz_media', 'NA_radio', 's_row', 's_col', 'rb_bins'):
                fila[f'{etq}.{m}.{c}'] = ms([r[etq][m][c] for r in rr])
            fila[f'{etq}.{m}.toca_borde'] = any(r[etq][m]['toca_borde'] for r in rr)
        for e in ('a', 'b'):
            fila[f'{etq}.borde_{e}.NAz'] = ms([r[etq]['borde'][e]['NAz'] for r in rr])
            fila[f'{etq}.borde_{e}.w_px'] = ms([r[etq]['borde'][e]['w_px'] for r in rr])
            fila[f'{etq}.borde_{e}.w_NA'] = ms([r[etq]['borde'][e]['w_px'] * CMM / z for r in rr])
            fila[f'{etq}.borde_{e}.eje'] = np.mean([r[etq]['borde'][e]['eje'] for r in rr], 0).tolist()
    tab.append(fila)
json.dump(tab, open(os.path.join(RES, 'resumen.json'), 'w'), indent=1)


def f(x, d=2):
    m, s, _ = x
    return f'{m:.{d}f}' + ('' if np.isnan(s) else f' ± {s:.{d}f}')


print('| verdad NA·z | w verdad | esp. filas | esp. cols | esp. media | esp. media (onda plana) | radio esp. NA | borde (a) NA·z | borde (a) w px (NA) | borde (b) NA·z | n |')
print('|---|---|---|---|---|---|---|---|---|---|---|')
for t in tab:
    k = 'ruido'
    print(f"| {t['NAz']:.3f} | {t['w']:.3f} | {f(t[k + '.esp_nt.NAz_fila'])} | {f(t[k + '.esp_nt.NAz_col'])} | "
          f"{f(t[k + '.esp_nt.NAz_media'])} | {f(t[k + '.esp_pw.NAz_media'])} | {f(t[k + '.esp_nt.NA_radio'], 4)} | "
          f"{f(t[k + '.borde_a.NAz'])} | {t[k + '.borde_a.w_px'][0]:.0f} ({t[k + '.borde_a.w_NA'][0]:.4f}) | "
          f"{f(t[k + '.borde_b.NAz'])} | {t['n']} |")
print()
print('Sin ruido (media de muestras):')
print('| caso | esp. filas | esp. cols | radio NA | s_fila bins | s_col bins | borde (a) | w(a) px | borde (b) | toca borde rango |')
print('|---|---|---|---|---|---|---|---|---|---|')
for t in tab:
    k = 'sin_ruido'
    print(f"| {t['caso']} | {f(t[k + '.esp_nt.NAz_fila'])} | {f(t[k + '.esp_nt.NAz_col'])} | {f(t[k + '.esp_nt.NA_radio'], 4)} | "
          f"{f(t[k + '.esp_nt.s_row'], 1)} | {f(t[k + '.esp_nt.s_col'], 1)} | {f(t[k + '.borde_a.NAz'])} | "
          f"{t[k + '.borde_a.w_px'][0]:.0f} | {f(t[k + '.borde_b.NAz'])} | {t['ruido.esp_nt.toca_borde']}/{t['ruido.esp_nt_ancho.toca_borde']} |")

# ---------------------------------------------------------------- figura
C = dict(fila='#2a78d6', col='#eb6834', a='#1baf7a', b='#eda100', ink='#52514e')
verd = sorted({t['NAz'] for t in tab})
fig, axs = plt.subplots(1, len(verd), figsize=(5.4 * len(verd), 4.6), sharey=True, sharex=True, squeeze=False)
for ax, v in zip(axs[0], verd):
    tt = [t for t in tab if abs(t['NAz'] - v) < 1e-9]
    w = np.array([t['w'] for t in tt]) * 1000
    for key, lab, col, dx, mk in (('ruido.esp_nt.NAz_fila', 'espectral, filas', C['fila'], -0.15, 'o'),
                                  ('ruido.esp_nt.NAz_col', 'espectral, cols', C['col'], -0.05, 'o'),
                                  ('ruido.borde_a.NAz', 'borde (a)', C['a'], 0.05, 's'),
                                  ('ruido.borde_b.NAz', 'borde (b)', C['b'], 0.15, 's')):
        m = np.array([t[key][0] for t in tt]); s = np.array([t[key][1] for t in tt])
        ax.errorbar(w + dx, m, yerr=np.nan_to_num(s), fmt=mk + '-', color=col, ms=6, lw=1.5, capsize=3, label=lab)
    dg = []
    for t in tt:
        fj = os.path.join(RES, f"diag_rb0_{t['caso']}.json")
        if os.path.exists(fj):
            q = json.load(open(fj))['etapa1_radio']; dg.append((t['w'] * 1000, 0.5 * (q['NAz_fila'] + q['NAz_col'])))
    if dg:
        dg = np.array(dg)
        ax.plot(dg[:, 0], dg[:, 1], 'o--', color='#6250d6', mfc='none', ms=8, lw=1.2,
                label='espectral, radio libre en etapa 1\n(media filas/cols, solo semilla 0)')
    ax.axhline(v, color='0.2', lw=1, ls='--', label='verdad NA·z')
    ax.axhspan(7.40, 7.47, color=C['a'], alpha=0.12, lw=0, label='real 03/11: borde (a)/(b)')
    ax.axhline(6.97, color=C['fila'], lw=0.8, ls=':', label='real 03/11: espectral filas (original)')
    ax.axhline(6.71, color=C['col'], lw=0.8, ls=':', label='real 03/11: espectral cols (original)')
    ax.axhline(6.97, color='#6250d6', lw=0.8, ls='-.', label='real 03/11: espectral radio libre (7.01/6.94)')
    ax.set_xlim(-0.6, 8.6)
    ax.set_title(f'verdad NA·z = {v:.3f} mm', fontsize=10)
    ax.set_xlabel('ancho erf verdadero w (×10⁻³ NA)')
    ax.grid(alpha=0.25, lw=0.5)
    for sp in ('top', 'right'):
        ax.spines[sp].set_visible(False)
axs[0][0].set_ylabel('NA·z medido (mm)')
axs[0][-1].legend(fontsize=7.5, loc='upper left', bbox_to_anchor=(1.01, 1.0), frameon=False)
fig.suptitle('Simulación: NA·z medido por cada método vs ancho del borde de pupila (media ± sd de 3 muestras con ruido)',
             fontsize=10)
fig.tight_layout()
fig.savefig(os.path.join(BASE, 'fig_sim_borde.png'), dpi=140)
print('figura ok')
