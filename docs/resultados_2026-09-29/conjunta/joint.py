"""joint.py -- reconstruccion conjunta de los tres colores con UN espesor compartido.

Modelo (docs/plan_reconstruccion_conjunta_2026-09-29.md):

    O_c(x) = g_c * a_c(x) * exp( i * kappa_c * t(x) ),    kappa_c = 2*pi*dn(lam_c)/lam_c
    dn(lam) = A + B / lam^2

    t(x)   espesor compartido (um), la incognita principal
    a_c(x) amplitud: A1 = una por color, A2 = una sola compartida
    g_c    ganancia escalar real por color
    B      dispersion: D1 = fija, D2 = ajustada

Costo:  f = sum_c sum_k sum_p  m_ckp * ( |psi_ckp| - sqrt(I_ckp) )^2      (todos los LEDs con peso 1)
    psi_ck = ifft2( ifftshift( recorte_k( fftshift(fft2(O_c)) ) * P_c ) )   (el modelo de fpm_red.predict)

Gradientes analiticos (Wirtinger). Con Omega_c = df/dO_c* (el adjunto exacto del modelo directo):
    df/dt(x)   = -2 * sum_c kappa_c * Im[ conj(Omega_c) O_c ]
    df/da_c(x) =  2 * g_c * Re[ conj(Omega_c) exp(i kappa_c t) ]
    df/dg_c    =  2 * sum_x a_c * Re[ conj(Omega_c) exp(i kappa_c t) ]
    df/dB      = -2 * sum_c (2*pi/lam_c^3) * sum_x t * Im[ conj(Omega_c) O_c ]
`gradcheck(seed=0)` los compara contra diferencias centrales en un problema de 64 px HR, 9 LEDs y
3 colores (derivada direccional por grupo + coordenadas sueltas) y devuelve el error relativo maximo.

El adjunto se acumula EN FRECUENCIA (una sola FFT de 1600 px por color y por epoca, no una por LED):
Omega_c = H^2 * ifft2( ifftshift( sum_k embed_k( fftshift(fft2(G_k))/N_lr * conj(P) ) ) ).

Simetrias que el codigo usa y verifica:
  - t tiene una libertad aditiva EXACTA: t -> t + t0 multiplica cada O_c por exp(i kappa_c t0), una fase
    global por color, que no cambia |psi|. Por eso sum_x df/dt = 0 (por color). Lo chequea `test_gauge`.
  - g_c entra linealmente en |psi|, asi que su minimo es cerrado: g <- g * sum(m|psi|y)/sum(m|psi|^2).
    El solver lo usa (`g_exacto=True`) en lugar de dar pasos de Adam sobre g.

Uso:
    python3 joint.py gradcheck
    python3 joint.py correr --variante A1_D1 --epocas 80 --nombre A1_D1
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

os.environ.setdefault("OMP_NUM_THREADS", "1")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import comun as C  # noqa: E402

from ptyco_full_simulator.optics import circular_pupil  # noqa: E402
from ptyco_full_simulator.spectral_ops import led_crop_window  # noqa: E402

fft2, ifft2 = np.fft.fft2, np.fft.ifft2
fftshift, ifftshift = np.fft.fftshift, np.fft.ifftshift


# ---------------------------------------------------------------- el problema

class Problema:
    """Las fotos y la geometria de los tres colores, ya en la grilla comun.

    colores : lista de nombres
    lam     : {color: um}
    y       : {color: (nk, ly, lx) float32}   sqrt de la intensidad medida (recortada a >= 0)
    mask    : {color: (nk, ly, lx) bool} o None (simulacion: no hay saturacion)
    win     : {color: [ (slice, slice) ]}     ventana de cada LED en el espectro de H x H
    P       : {color: (ly, lx) complex}       pupila circular NA/lam
    """

    def __init__(self, colores, lam, y, win, P, H, mask=None, A=C.A_DN):
        self.colores, self.lam, self.y, self.win, self.P = colores, lam, y, win, P
        self.H, self.mask, self.A = H, mask, A
        self.lr_shape = y[colores[0]][0].shape
        self.n_lr = int(np.prod(self.lr_shape))
        self.n_H = H * H

    def kappa(self, c, B):
        return 2 * np.pi * (self.A + B / self.lam[c] ** 2) / self.lam[c]

    def dkappa_dB(self, c):
        return 2 * np.pi / self.lam[c] ** 3


def problema_sim(colores=C.COLORES, geo_name="z98", subconjunto=None, z_mm=C.Z_MM):
    """Arma el Problema con las fotos simuladas `datos_<geo>_<color>.npz`.

    `subconjunto`: None = los 225 LEDs; 'half0'/'half1' = la mitad del damero (fila+col)%2.
    """
    y, win, P, lam = {}, {}, {}, {}
    for c in colores:
        g = C.geometry(c, z_mm)
        d = C.cargar_sim(c, geo_name)
        keys = d["keys"]
        idx = list(range(len(keys)))
        if subconjunto in ("half0", "half1"):
            h = int(subconjunto[-1])
            idx = [i for i in idx if (keys[i][0] + keys[i][1]) % 2 == h]
        y[c] = np.sqrt(np.clip(d["I"][idx].astype(np.float32), 0, None))
        win[c] = [led_crop_window((C.H, C.H), g["hrpx"], (C.LR, C.LR), *g["fxy"][keys[i]]) for i in idx]
        P[c] = C.pupil(c, g).astype(complex)
        lam[c] = g["lam"]
    return Problema(list(colores), lam, y, win, P, C.H)


# ------------------------------------------------------- modelo directo/adjunto

def _fwd_adj(O, win, P, y, mask, n_lr, n_H, quiere_grad=True, s_led=None):
    """Una pasada por todos los LEDs de un color.

    `s_led`: ganancia por LED (None = todas 1, el costo literal del plan). El residuo es
    r_k = m_k (s_k |psi_k| - y_k); devuelve tambien los acumuladores del minimo exacto de s_k y de g_c.

    Devuelve (costo, Omega = df/dO*, s_ay, s_aa, g_s_led, grad_s_led).
    """
    spec = fftshift(fft2(O))
    E = np.zeros_like(spec) if quiere_grad else None
    costo = s_ay = s_aa = 0.0
    nk = len(win)
    g_s = np.ones(nk)
    gr_s = np.zeros(nk)
    for i, (ys, xs) in enumerate(win):
        ps = spec[ys, xs] * P
        psi = ifft2(ifftshift(ps))
        amp = np.abs(psi)
        yk = y[i].astype(float)
        sk = 1.0 if s_led is None else float(s_led[i])
        if mask is not None:
            mk = mask[i]
            ay = float(np.sum(amp[mk] * yk[mk])); aa = float(np.sum(amp[mk] ** 2))
            r = (sk * amp - yk) * mk
        else:
            ay = float(np.sum(amp * yk)); aa = float(np.sum(amp * amp))
            r = sk * amp - yk
        s_ay += sk * ay; s_aa += sk * sk * aa
        g_s[i] = (ay / aa) if aa > 0 else sk
        costo += float(np.sum(r * r))
        gr_s[i] = 2.0 * float(np.sum(r * amp))
        if quiere_grad:
            G = r * sk * psi / np.maximum(amp, 1e-300)
            E[ys, xs] += fftshift(fft2(G)) / n_lr * np.conj(P)
    Om = n_H * ifft2(ifftshift(E)) if quiere_grad else None
    return costo, Om, s_ay, s_aa, g_s, gr_s


def campos(prob, par, variante_A):
    """{color: O_c} a partir de los parametros."""
    O, fase = {}, {}
    for ic, c in enumerate(prob.colores):
        kap = prob.kappa(c, par["B"])
        ph = np.exp(1j * kap * par["t"])
        a = par["a"][ic if variante_A == "A1" else 0]
        fase[c] = ph
        O[c] = par["g"][ic] * a * ph
    return O, fase


def costo_grad(prob, par, variante_A="A1", quiere_grad=True):
    """Costo total y gradientes analiticos.

    par = {"t","a"(lista),"g"(3),"B", opcional "s"({color: (nk,)} ganancia por LED)}.
    Devuelve (costo, grad) con grad["t"], ["a"], ["g"], ["B"], ["s"] y ademas
      grad["_g_exacto"] : la ganancia por color que minimiza exactamente el costo (todo lo demas fijo);
      grad["_s_exacto"] : idem por LED.
    """
    t, B, g = par["t"], par["B"], np.asarray(par["g"], float)
    s_led = par.get("s")
    nA = len(par["a"])
    total = 0.0
    gt = np.zeros_like(t) if quiere_grad else None
    ga = [np.zeros_like(t) for _ in range(nA)] if quiere_grad else None
    gg = np.zeros(len(prob.colores)) if quiere_grad else None
    gs = {}
    gB = 0.0
    g_ex = np.zeros(len(prob.colores))
    s_ex = {}
    for ic, c in enumerate(prob.colores):
        kap = prob.kappa(c, B)
        ph = np.exp(1j * kap * t)
        a = par["a"][ic if variante_A == "A1" else 0]
        O = g[ic] * a * ph
        costo, Om, s_ay, s_aa, g_s, gr_s = _fwd_adj(
            O, prob.win[c], prob.P[c], prob.y[c],
            None if prob.mask is None else prob.mask[c],
            prob.n_lr, prob.n_H, quiere_grad, None if s_led is None else s_led[c])
        total += costo
        g_ex[ic] = g[ic] * (s_ay / s_aa) if s_aa > 0 else g[ic]
        s_ex[c] = g_s if s_led is None else g_s * 1.0
        gs[c] = gr_s
        if not quiere_grad:
            continue
        co = np.conj(Om)
        im = np.imag(co * O)                    # Im[ conj(Omega) O ]
        gt -= 2.0 * kap * im
        gB -= 2.0 * prob.dkappa_dB(c) * float(np.sum(t * im))
        re = np.real(co * ph)                   # Re[ conj(Omega) exp(i kappa t) ]
        ga[ic if variante_A == "A1" else 0] += 2.0 * g[ic] * re
        gg[ic] = 2.0 * float(np.sum(a * re))
    if quiere_grad:
        grad = {"t": gt, "a": ga, "g": gg, "B": gB, "s": gs, "_g_exacto": g_ex, "_s_exacto": s_ex}
    else:
        grad = {"_g_exacto": g_ex, "_s_exacto": s_ex, "s": gs}
    return total, grad


# ------------------------------------------------------------------ gradcheck

def _problema_chico(seed=0, n_lr=16, factor=4, n_leds=9):
    """Problema sintetico chico que usa EL MISMO codigo de ventanas y pupila que el grande."""
    rng = np.random.default_rng(seed)
    H = n_lr * factor                      # 64
    hrpx = C.LRPX / factor                 # 0.32 um
    fx_ax = fftshift(np.fft.fftfreq(H, hrpx))
    bins = [H // 2 - 8, H // 2, H // 2 + 8]
    colores = list(C.COLORES)
    lam = {c: C.LAM[c] for c in colores}
    win, P = {}, {}
    for c in colores:
        win[c] = [led_crop_window((H, H), hrpx, (n_lr, n_lr), fx_ax[bx], fx_ax[by])
                  for by in bins for bx in bins][:n_leds]
        P[c] = circular_pupil((n_lr, n_lr), C.LRPX, C.NA, lam[c]).astype(complex)
    # objeto "verdadero" -> fotos; despues los parametros arrancan en otro lado (residuo no nulo)
    t_v = rng.uniform(0.0, 3.0, (H, H))
    a_v = {c: rng.uniform(0.7, 1.0, (H, H)) for c in colores}
    g_v = {c: float(rng.uniform(0.8, 1.2)) for c in colores}
    s_v = {c: rng.uniform(0.2, 1.0, n_leds) for c in colores}   # ganancia por LED (como sim.py)
    B_v = 0.002
    y, mask = {}, {}
    prob0 = Problema(colores, lam, {c: np.zeros((n_leds, n_lr, n_lr), np.float32) for c in colores},
                     win, P, H)
    for c in colores:
        kap = 2 * np.pi * (C.A_DN + B_v / lam[c] ** 2) / lam[c]
        O = g_v[c] * a_v[c] * np.exp(1j * kap * t_v)
        spec = fftshift(fft2(O))
        ims = []
        for (ys, xs) in win[c]:
            psi = ifft2(ifftshift(spec[ys, xs] * P[c]))
            ims.append((s_v[c][len(ims)] * np.abs(psi)) ** 2 * (1.0 + 0.05 * rng.standard_normal((n_lr, n_lr))))
        y[c] = np.sqrt(np.clip(np.array(ims), 0, None)).astype(np.float32)
        mask[c] = rng.random((n_leds, n_lr, n_lr)) > 0.1     # ~10 % de pixeles apagados
    prob = Problema(colores, lam, y, win, P, H, mask=mask)
    par = {"t": rng.uniform(0.0, 3.0, (H, H)),
           "a": [rng.uniform(0.7, 1.0, (H, H)) for _ in colores],
           "g": np.array([rng.uniform(0.8, 1.2) for _ in colores]),
           "B": 0.001,
           "s": {c: rng.uniform(0.2, 1.0, n_leds) for c in colores}}
    return prob, par


def _aplanar(par, variante_A):
    return dict(t=par["t"], a=par["a"], g=np.asarray(par["g"], float), B=float(par["B"]))


def _f(prob, par, variante_A):
    return costo_grad(prob, par, variante_A, quiere_grad=False)[0]


def _copiar(par):
    d = {"t": par["t"].copy(), "a": [x.copy() for x in par["a"]],
         "g": np.asarray(par["g"], float).copy(), "B": float(par["B"])}
    if par.get("s") is not None:
        d["s"] = {c: np.asarray(v, float).copy() for c, v in par["s"].items()}
    return d


def _fd(f, h):
    """Diferencia central de 4to orden: [-f(2h) + 8f(h) - 8f(-h) + f(-2h)] / (12h).

    Con el paso h afinado (ver `_H_FD`) el error queda ~1e-9 relativo, tres ordenes por debajo
    del umbral de 1e-5 que pide la aceptacion: el margen no depende de elegir bien h por suerte.
    """
    return (-f(2 * h) + 8 * f(h) - 8 * f(-h) + f(-2 * h)) / (12 * h)


_H_FD = {"t": 1e-3, "a": 1e-3, "g": 1e-4, "B": 1e-6, "s": 1e-5}


def gradcheck(seed=0, variante_A="A1", detalle=False):
    """Error relativo maximo entre el gradiente analitico y diferencias centrales.

    Cubre los cuatro grupos (t, a_c, g_c, B) con:
      - una derivada direccional por grupo (direccion aleatoria unitaria sobre TODO el grupo),
        que mezcla todas las coordenadas del grupo y no puede pasar por casualidad;
      - coordenadas sueltas (4 de t, 4 de a_red, cada g_c, B).
    Problema: 64 px HR (16 px de camara x factor 4), 9 LEDs, 3 colores, ~10 % de pixeles
    enmascarados, con las MISMAS funciones de ventana y pupila que la corrida grande.
    """
    prob, par = _problema_chico(seed)
    rng = np.random.default_rng(seed + 1000)
    _, gr = costo_grad(prob, par, variante_A, quiere_grad=True)
    filas = []

    def rel(an, fd):
        d = max(abs(an), abs(fd))
        return abs(an - fd) / d if d > 0 else 0.0

    def agregar(nombre, an, mv, h):
        fd = _fd(lambda s: _f(prob, mv(s), variante_A), h)
        filas.append((nombre, float(an), float(fd), rel(an, fd)))

    # --- derivadas direccionales, una por grupo
    v = rng.standard_normal(par["t"].shape); v /= np.linalg.norm(v)
    agregar("direccional[t]", np.sum(gr["t"] * v),
            lambda s, v=v: dict(_copiar(par), t=par["t"] + s * v), _H_FD["t"])

    vs = [rng.standard_normal(x.shape) for x in par["a"]]
    nrm = np.sqrt(sum(float(np.sum(x * x)) for x in vs))
    vs = [x / nrm for x in vs]
    agregar("direccional[a]", sum(np.sum(gr["a"][i] * vs[i]) for i in range(len(vs))),
            lambda s, vs=vs: dict(_copiar(par), a=[a + s * w for a, w in zip(par["a"], vs)]),
            _H_FD["a"])

    vg = rng.standard_normal(len(par["g"])); vg /= np.linalg.norm(vg)
    agregar("direccional[g]", np.sum(gr["g"] * vg),
            lambda s, vg=vg: dict(_copiar(par), g=np.asarray(par["g"], float) + s * vg), _H_FD["g"])

    agregar("direccional[B]", gr["B"],
            lambda s: dict(_copiar(par), B=float(par["B"]) + s), _H_FD["B"])

    # --- coordenadas sueltas
    idx = [tuple(int(q) for q in rng.integers(0, par["t"].shape[0], 2)) for _ in range(4)]

    def mv_campo(campo, ic, i, j):
        def f(s):
            p = _copiar(par)
            if campo == "t":
                p["t"][i, j] += s
            else:
                p["a"][ic][i, j] += s
            return p
        return f

    for (i, j) in idx:
        agregar(f"t[{i},{j}]", gr["t"][i, j], mv_campo("t", 0, i, j), _H_FD["t"])
    for (i, j) in idx:
        agregar(f"a_red[{i},{j}]", gr["a"][0][i, j], mv_campo("a", 0, i, j), _H_FD["a"])
    for ic in range(len(par["g"])):
        def mvg(s, ic=ic):
            p = _copiar(par); p["g"][ic] += s; return p
        agregar(f"g[{ic}]", gr["g"][ic], mvg, _H_FD["g"])

    def mvB(s):
        p = _copiar(par); p["B"] += s; return p
    agregar("B", gr["B"], mvB, _H_FD["B"])

    # --- quinto grupo: ganancia por LED (extension al costo del plan, ver la cabecera del modulo)
    if par.get("s") is not None:
        cred = prob.colores[0]
        vsl = rng.standard_normal(len(par["s"][cred])); vsl /= np.linalg.norm(vsl)
        agregar("direccional[s_led]", np.sum(gr["s"][cred] * vsl),
                lambda q, vsl=vsl: dict(_copiar(par),
                                        s={c: (v + q * vsl if c == cred else v)
                                           for c, v in par["s"].items()}), _H_FD["s"])
        for kk in (0, 4):
            def mvs(q, kk=kk, cred=cred):
                p = _copiar(par); p["s"][cred][kk] += q; return p
            agregar(f"s_led[{cred},{kk}]", gr["s"][cred][kk], mvs, _H_FD["s"])

    err = max(f[3] for f in filas)
    if detalle:
        for n, an, fd, r in filas:
            print(f"{n:22s} analitico={an: .10e}  dif.centrales={fd: .10e}  rel={r:.3e}")
    return float(err)


def test_gauge(seed=0):
    """La libertad aditiva de t: sum_x df/dt debe ser 0 por color (fase global). Error relativo."""
    prob, par = _problema_chico(seed)
    peor = 0.0
    for ic, c in enumerate(prob.colores):
        p1 = Problema([c], {c: prob.lam[c]}, {c: prob.y[c]}, {c: prob.win[c]}, {c: prob.P[c]},
                      prob.H, mask={c: prob.mask[c]})
        pp = {"t": par["t"], "a": [par["a"][ic]], "g": np.array([par["g"][ic]]), "B": par["B"]}
        _, gr = costo_grad(p1, pp, "A1", True)
        s, esc = float(np.sum(gr["t"])), float(np.sum(np.abs(gr["t"])))
        peor = max(peor, abs(s) / esc)
    return peor


# ------------------------------------------------- leer un resultado guardado

def cargar_resultado(path):
    """Devuelve (par, extra) de un .npz escrito por correr_sim.guardar()."""
    d = np.load(path, allow_pickle=False)
    par = {"t": d["t"].astype(float),
           "a": [d[f"a{i}"].astype(float) for i in range(int(d["na"]))],
           "g": np.asarray(d["g"], float), "B": float(d["B"])}
    extra = json.loads(str(d["extra"]))
    extra["hist"] = [float(x) for x in d["hist"]]
    return par, extra


def campos_de(path, A=C.A_DN):
    """{color: O_c} en la grilla comun, reconstruidos del .npz guardado.

    Es lo que consumen S2 (fase por color) y S3 (FRC entre mitades): no hace falta guardar los
    campos complejos, alcanza con (t, a, g, B) y el modelo.
    """
    par, extra = cargar_resultado(path)
    O = {}
    for ic, c in enumerate(C.COLORES):
        kap = 2 * np.pi * (A + par["B"] / C.LAM[c] ** 2) / C.LAM[c]
        a = par["a"][ic if len(par["a"]) > 1 else 0]
        O[c] = par["g"][ic] * a * np.exp(1j * kap * par["t"])
    return O, par, extra


# --------------------------------------------------------------------- solver

def _adam(estado, clave, grad, lr, paso, b1=0.9, b2=0.999, eps=1e-8):
    m = estado.setdefault("m_" + clave, np.zeros_like(grad))
    v = estado.setdefault("v_" + clave, np.zeros_like(grad))
    m *= b1; m += (1 - b1) * grad
    v *= b2; v += (1 - b2) * grad * grad
    mh = m / (1 - b1 ** paso)
    vh = v / (1 - b2 ** paso)
    return -lr * mh / (np.sqrt(vh) + eps)


def resolver(prob, par0, variante_A="A1", B_libre=False, B_rango=(-0.005, 0.005),
             epocas=80, lr_t=0.05, lr_a=0.01, lr_B=2e-4, lr_g=1e-3, g_exacto=True, s_exacto=True,
             a_rango=(0.0, 2.0), log=None, estado_path=None, guardar_cada=5, etiqueta=""):
    """Adam de lote completo sobre (t, a) [+ B si D2]; g_c por minimo exacto cada epoca.

    Reanudable: si `estado_path` existe, retoma desde ahi.
    """
    par = _copiar(par0)
    est = {"paso": 0, "hist": []}
    if estado_path and os.path.exists(estado_path):
        d = np.load(estado_path, allow_pickle=True)
        par = {"t": d["t"], "a": [d[f"a{i}"] for i in range(int(d["na"]))],
               "g": d["g"], "B": float(d["B"])}
        if "s_colores" in d.files:
            par["s"] = {str(c): d[f"s_{c}"] for c in d["s_colores"]}
        est = {"paso": int(d["paso"]), "hist": list(d["hist"])}
        for k in d.files:
            if k.startswith(("m_", "v_")):
                est[k] = d[k]
        _bitacora(log, f"reanudado en la epoca {est['paso']} desde {os.path.basename(estado_path)}")

    def guardar():
        if not estado_path:
            return
        d = {"t": par["t"], "na": len(par["a"]), "g": np.asarray(par["g"], float), "B": par["B"],
             "paso": est["paso"], "hist": np.array(est["hist"], float)}
        for i, a in enumerate(par["a"]):
            d[f"a{i}"] = a
        if par.get("s") is not None:
            d["s_colores"] = np.array(list(par["s"].keys()))
            for c, v in par["s"].items():
                d[f"s_{c}"] = v
        for k, v in est.items():
            if k.startswith(("m_", "v_")):
                d[k] = v
        np.savez(estado_path + ".tmp.npz", **d)
        os.replace(estado_path + ".tmp.npz", estado_path)

    t0 = time.time()
    while est["paso"] < epocas:
        est["paso"] += 1
        costo, gr = costo_grad(prob, par, variante_A, quiere_grad=True)
        par["t"] = par["t"] + _adam(est, "t", gr["t"], lr_t, est["paso"])
        for i in range(len(par["a"])):
            par["a"][i] = np.clip(par["a"][i] + _adam(est, f"a{i}", gr["a"][i], lr_a, est["paso"]),
                                  *a_rango)
        if B_libre:
            par["B"] = float(np.clip(par["B"] + float(_adam(est, "B", np.array(gr["B"]), lr_B,
                                                            est["paso"])), *B_rango))
        if s_exacto and par.get("s") is not None:
            # con ganancia por LED, g_c es REDUNDANTE (s_ck la absorbe): reajustar las dos a la vez
            # con los acumuladores de la misma pasada reescala dos veces y empeora el costo.
            par["s"] = {c: gr["_s_exacto"][c] for c in prob.colores}
        elif g_exacto:
            par["g"] = gr["_g_exacto"]
        else:
            par["g"] = par["g"] + _adam(est, "g", gr["g"], lr_g, est["paso"])
        est["hist"].append(costo)
        _bitacora(log, f"{etiqueta} epoca {est['paso']:3d}/{epocas} costo={costo:.8e} "
                       f"B={par['B']:.6f} g={np.array2string(np.asarray(par['g']), precision=4)} "
                       f"t_med={float(np.mean(par['t'])):.4f} ({time.time() - t0:.1f}s)")
        if est["paso"] % guardar_cada == 0:
            guardar()
    guardar()
    return par, est


def _bitacora(path, msg):
    linea = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(linea, flush=True)
    if path:
        with open(path, "a") as fh:
            fh.write(linea + "\n")
            fh.flush()


# ----------------------------------------------------------------------- main

def _cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("accion", choices=["gradcheck", "correr"])
    ap.add_argument("--variante", default="A1_D1")
    ap.add_argument("--epocas", type=int, default=80)
    ap.add_argument("--lr_t", type=float, default=0.05)
    ap.add_argument("--lr_a", type=float, default=0.01)
    ap.add_argument("--nombre", default=None)
    ap.add_argument("--subconjunto", default=None)
    ap.add_argument("--init", default="cadena")
    a = ap.parse_args()
    if a.accion == "gradcheck":
        print("gradcheck =", gradcheck(0, detalle=True))
        print("gauge     =", test_gauge(0))
        return
    import correr_sim
    correr_sim.main(a)


if __name__ == "__main__":
    _cli()
