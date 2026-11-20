import numpy as np, glob
from PIL import Image
B='/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-11-20.2048ms-red.a'
r0,r1,c0,c1=285,685,344,744
def L(root,r,c):
    t=glob.glob(f'{root}/fila{r}_col{c}_colorr/*ms')[0]; tn=t.split('/')[-1]; ms=float(tn[:-2])
    I=np.mean([np.array(Image.open(f),float) for f in glob.glob(t+'/*.tif*')],0)
    d=np.mean([np.array(Image.open(f),float) for f in glob.glob(f'{root}-dark/fila17_col15_colorr/{tn}/*.tif*')],0)
    return ((I-d)/ms)[r0:r1,c0:c1]
sc=L(B,17,15); fc=L(B+'-sinmuestra',17,15)
print('LED   dist  muestra: med p5 p95 | flat: med p5 p95   (cociente LED/LED central, recorte 400)')
for r in range(13,22):
  for c in range(11,20):
    d=np.hypot(r-17,c-15)
    if d<1.2 or d>3.3: continue
    qs=L(B,r,c)/sc; qf=L(B+'-sinmuestra',r,c)/fc
    a=np.percentile(qs,[50,5,95]); b=np.percentile(qf,[50,5,95])
    flag=' <-- distinto' if abs(a[0]-b[0])>0.1 or abs(a[1]-b[1])>0.1 or abs(a[2]-b[2])>0.1 else ''
    print(f'({r},{c}) {d:.2f}  {a[0]:.2f} {a[1]:.2f} {a[2]:.2f} | {b[0]:.2f} {b[1]:.2f} {b[2]:.2f}{flag}')
