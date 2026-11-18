"""na_pupila.py -- 18/11/2026. NA del objetivo desde el radio del disco BF en la FFT del LED del eje (17,15).

Mismo método que lote_2026-11-13/pupila/forma_pupila.py (borde = máxima pendiente negativa del perfil polar de
log|FFT|, 36 sectores, círculo ajustado, 3x3 teselas). Esta medición NO depende de z: el radio en px de Fourier es
NA/λ · n · Δx (Δx = 1.29 µm/px en la muestra, regla 16/10).

El método tiene sesgo (pendiente máxima ≠ borde exacto) → se calibra con imágenes simuladas con pupila circular de
NA conocida: NA_medida = interpolación de R_real en la curva R_sim(NA).

Sin flat a z 143.5 todavía → I = (muestra - oscuro) sin dividir. Control: 2026-11-13 con y sin flat (mismo campo)
dice cuánto cambia el radio por no dividir.
"""
import importlib.util, json, os, sys
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    'fp', '/home/chanoscopio/Documents/AleYLu/reconstrucciones/lote_2026-11-13/pupila/forma_pupila.py')
fp = importlib.util.module_from_spec(spec); spec.loader.exec_module(fp)
D = fp.I_DIR


def leer(carpeta, t):
    fp.T = t
    return fp.leer(carpeta)


def img(campo, t, flat=None, t_flat=None):
    s = leer(f'{D}/{campo}', t) - leer(f'{D}/{campo}-dark', t)
    if flat is None:
        return s / s.mean()
    f = leer(f'{D}/{flat}', t_flat) - leer(f'{D}/{flat}-dark', t_flat)
    return s / np.maximum(f, 1.0)


def radio(im):
    r = fp.analizar(im)
    Rs = np.array([r[(i, j)]['R'] for i in range(3) for j in range(3)])
    return Rs.mean(), Rs.std() / 3.0, Rs           # media de 9 teselas, error estándar


casos = {
    '13/11 con flat (z~100)': img('2026-11-13', '18ms', '2026-11-13.fondo', '18ms'),
    '13/11 sin flat (z~100)': img('2026-11-13', '18ms'),
    '18/11 1025 sin flat (z 143.5)': img('2026-11-18.1025ms', '41ms'),
    '18/11 2048 sin flat (z 143.5)': img('2026-11-18.2048ms', '41ms'),
}
res = {}
for k, im in casos.items():
    m, e, Rs = radio(im)
    res[k] = dict(R=m, err=Rs.std() / 3, teselas=Rs.round(1).tolist())
    print(f'{k:32s} R = {m:.2f} ± {e:.2f} px   teselas {np.round(Rs, 1)}', flush=True)

# curva de calibración R_sim(NA): pupila circular dura, 3 semillas por NA
nas = [0.064, 0.068, 0.072, 0.076, 0.080]
cal = []
for na in nas:
    fp.NA = na
    rs = [radio(fp.simular(s))[0] for s in range(3)]
    cal.append(np.mean(rs))
    print(f'sim NA {na:.3f}: R = {np.mean(rs):.2f} px (sd {np.std(rs):.2f}; nominal {na / fp.LAM * 373 * fp.DX:.2f})', flush=True)
cal = np.array(cal)
for k in res:
    na = float(np.interp(res[k]['R'], cal, nas))
    e = res[k]['err'] * (nas[-1] - nas[0]) / (cal[-1] - cal[0])
    res[k].update(NA_lam063=na, NA_err=e, NA_sobre_lambda=na / 0.63, NA_lam0617=na / 0.63 * 0.617)
    print(f'{k:32s} NA/λ = {na / 0.63:.4f} µm⁻¹ → NA {na:.4f} ± {e:.4f} (λ 0.630) | {na / 0.63 * 0.617:.4f} (λ 0.617)')
json.dump(dict(casos=res, cal=dict(na=nas, R=cal.tolist())), open(f'{AQUI}/na_pupila.json', 'w'), indent=1)
