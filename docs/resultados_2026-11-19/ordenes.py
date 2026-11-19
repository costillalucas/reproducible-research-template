import glob, re, numpy as np, tifffile
I='/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/'
def carga(d):
    out={}
    for f in glob.glob(d+'/fila*/*ms/*.tiff'):
        m=re.search(r'fila(\d+)_col(\d+)_color\w/(\d+)ms/',f); r,c,t=map(int,m.groups()); out.setdefault((r,c),{})[t]=f
    return out
def oscuro(d):
    o={}
    for f in glob.glob(d+'/fila*/*ms/*.tiff'):
        t=int(re.search(r'/(\d+)ms/',f).group(1)); o.setdefault(t,[]).append(tifffile.imread(f).astype(float))
    return {t:np.mean(v,0) for t,v in o.items()}
def cps(F,O,k,rec):
    t=max(F[k]); return (tifffile.imread(F[k][t]).astype(float)[rec]-O[t][rec])/t
casos={'rojo  (grilla.c)':(I+'2026-11-18.2048ms-grilla.c',I+'2026-11-18.2048ms-sinmuestra',(slice(319,719),slice(341,741)),[(r,c) for r in (8,9,25,26) for c in (14,15,16)]),
       'azul  (grilla.a)':(I+'2026-11-19.2048ms-grilla.a',I+'2026-11-19.2048ms-sinmuestra.azul.500',(slice(262,662),slice(365,765)),[(r,c) for r in (10,11,23,24) for c in (14,15,16)])}
for nom,(S,F,rec,lob) in casos.items():
    SM,FL,OS,OF=carga(S),carga(F),oscuro(S+'-dark'),oscuro(F+'-dark')
    q=lambda k: np.median(cps(SM,OS,k,rec))/np.median(cps(FL,OF,k,rec))
    c0=np.mean([q(k) for k in [(17,15),(16,15),(18,15),(17,14),(17,16)]])
    c1=[q(k) for k in lob]
    print(f'{nom}: |c0|² ≈ {c0:.3f}   |c1|² (lóbulo, 12 LEDs) ≈ {np.mean(c1):.3f} [{min(c1):.3f}–{max(c1):.3f}]   |c1|²/|c0|² = {np.mean(c1)/c0:.2f}   suma c0+2c1 = {c0+2*np.mean(c1):.2f}')
