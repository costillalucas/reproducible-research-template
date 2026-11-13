"""sim_1bf_rescate.py -- rescate del 1 BF atacando la fase del DC / la inicializacion (simulacion, 12/11).
Uso: python sim_1bf_rescate.py   (semillas fijas; agrega filas a runs.jsonl).  Luego: python figs.py
Importa SIN modificar ../sim_1bf_diag/sim_1bf_diag.py (solver ePIE, diagnostico) y ../sim_z_1bf/sim_z_1bf.py.
Un proceso, complex64, LR 64.
"""
import json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "sim_1bf_diag"))
import sim_1bf_diag as D                              # noqa: E402
S, B, F, HR, C = D.S, D.B, D.F, D.HR, D.C
f2, if2 = D.f2, D.if2
T0 = time.time()
C0 = (0, 0)
TH = np.arange(24) * 2 * np.pi / 24
c0 = HR // 2


class Datos:
    def __init__(self, I, g, keys):
        self.I, self.g, self.keys = I, g, keys
        self.W, self.P, self.tg = {}, {}, {}
        N = np.zeros((HR, HR), np.float32)
        for k in set(keys):
            w, fx, fy = S.win(g, k, HR)
            self.W[k] = w; self.P[k] = (np.hypot(S.xx - fx, S.yy - fy) <= S.R).astype(np.float32)
            self.tg[k] = np.sqrt(np.clip(I[k], 0, None)); N[w] += self.P[k]
        self.sup = N > 0
        self.norm = sum(float(np.sum(t ** 2)) for t in self.tg.values())

    def costo(self, spec):
        """Residuo de amplitud relativo sobre todos los LEDs, y el del BF solo."""
        c = 0.0
        for k in self.tg:
            r = float(np.sum((self.tg[k] - np.abs(if2(spec[self.W[k]] * self.P[k]))) ** 2))
            c += r
            if k == C0:
                cb = r / float(np.sum(self.tg[k] ** 2))
        return c / self.norm, cb

    def init(self):
        return (f2(np.kron(self.tg[C0], np.ones((F, F), np.float32)).astype(C)) / F ** 2).astype(C)

    def solve(self, **kw):
        return f2(D.solve(self.I, self.g, self.keys, **kw)).astype(C)


def rot(spec, th):
    s = spec.copy(); s[c0, c0] *= np.exp(1j * th); return s


def signo(spec, sg, sup):
    """Prior de signo: fase respecto del fondo forzada a ser >= 0 (sg=+1) o <= 0 (sg=-1); amplitud intacta."""
    o = if2(spec); ref = np.exp(-1j * np.angle(o.mean()))
    ph = np.angle(o * ref)
    ph = np.where(sg * ph < 0, 0.0, ph)
    return (f2(np.abs(o) * np.exp(1j * ph) / ref) * sup).astype(C)


def log(row):
    row["t"] = round(time.time() - T0, 1)
    with open(os.path.join(HERE, "runs.jsonl"), "a") as f:
        f.write(json.dumps(row) + "\n")
    print(row["z"], row["obj"], row["seed"], row["var"], "costo %.5f bf %.5f ph %.3f th_dc %.2f t=%s" % (
        row["costo"], row["costo_bf"], row["ph_esf"], row["theta_dc"], row["t"]), flush=True)


def caso(z, io, seed, obj):
    spec_t, truth, mask = obj
    g = S.geom(z)
    keys = S.KEYS if z < 85.5 else B.solo_central(g)
    In, _ = S.add_noise(S.forward(spec_t, g), g, z, np.random.default_rng(1000 + seed))
    d = Datos(In, g, keys)
    ref_t = np.exp(-1j * np.angle(np.mean(truth[~mask])))
    sg_v = float(np.sign(np.mean(np.angle(truth[mask] * ref_t))))            # signo verdadero de la fase de las esferas

    def ev(var, spec, **extra):
        o = if2(spec); m = S.metrics(o, truth, mask); c, cb = d.costo(spec)
        _, th, _ = D.two_const(o, truth, D.DC)
        A = np.abs(if2(spec[d.W[C0]] * d.P[C0]))
        row = dict(z=z, obj=io, seed=seed, var=var, costo=c, costo_bf=cb, err=m["err"], ph_esf=m["ph_esf"],
                   theta_dc=th, s_bf=float(np.sum(d.tg[C0] * A) / np.sum(A * A)), signo_verdad=sg_v, **extra)
        log(row); return row

    def barrido(spec):
        cs, ps = [], []
        for th in TH:
            s = rot(spec, th); c, _ = d.costo(s)
            cs.append(c); ps.append(S.metrics(if2(s), truth, mask)["ph_esf"])
        return cs, ps

    # referencias: base (minimo falso) e init = verdad (minimo correcto), con barrido de theta sobre cada una
    sb = d.solve(); cs, ps = barrido(sb)
    ev("base", sb, sweep_c=cs, sweep_ph=ps)
    sv = d.solve(spec0=f2(truth / F ** 2)); cv, pv = barrido(sv)
    ev("ini_verdad", sv, sweep_c=cv, sweep_ph=pv)
    # 1. barrido post-hoc: mejor theta por costo, sin y con refinado (20 epocas mas); 2 rondas
    s1 = rot(sb, TH[int(np.argmin(cs))])
    ev("barrido", s1, theta_sel=float(TH[int(np.argmin(cs))]))
    s2 = d.solve(spec0=s1); ev("barrido+refina", s2)
    c2, _ = barrido(s2); s3 = d.solve(spec0=rot(s2, TH[int(np.argmin(c2))]))
    ev("barrido+refina_x2", s3, theta_sel=float(TH[int(np.argmin(c2))]))
    # 2. multi-inicio: DC del init rotado theta0
    s0 = d.init()
    for th0 in (0.0, np.pi / 2, np.pi, 3 * np.pi / 2):
        if th0 == 0.0:
            ev("ini_th0_0.00", sb, th0=0.0); continue
        ev("ini_th0_%.2f" % th0, d.solve(spec0=rot(s0, th0)), th0=float(th0))
    # 3. prior de signo (correcto e incorrecto), aplicado tras cada epoca; 4. ganancia libre del BF
    for nom, sg in (("signo_ok", sg_v), ("signo_mal", -sg_v)):
        s = None
        for it in range(20):
            s = signo(d.solve(spec0=s, its=1, step=0.3, ramp=False), sg, d.sup)
        ev(nom, s)
        ev(nom + "+libre10", d.solve(spec0=s, its=10))                       # se suelta el prior 10 epocas
    I2 = dict(In); s = None; gan = 1.0
    for it in range(20):
        s = f2(D.solve(I2, g, keys, spec0=s, its=1, step=0.3, ramp=False)).astype(C)
        A = np.abs(if2(s[d.W[C0]] * d.P[C0])); t = np.sqrt(np.clip(I2[C0], 0, None))
        sk = float(np.sum(t * A) / np.sum(t * t)); gan *= sk
        I2[C0] = In[C0] * np.float32(gan ** 2)                               # s_k: escala del BF ajustada al modelo
    ev("ganancia_bf", s, ganancia=gan)


def main():
    objs = {}
    for z, io, seed in [(73.0, 0, 0), (73.0, 1, 0), (103.0, 0, 0), (103.0, 1, 0), (73.0, 0, 1), (73.0, 1, 1),
                        (103.0, 0, 1), (103.0, 1, 1)]:
        if io not in objs:
            objs[io] = S.make_object(io)
        caso(z, io, seed, objs[io])


if __name__ == "__main__":
    main()
