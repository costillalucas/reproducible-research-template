import numpy as np, glob
from PIL import Image
from scipy import ndimage as ndi
B='/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-11-20.2048ms-red.a'
def L(root,r,c):
    t=glob.glob(f'{root}/fila{r}_col{c}_colorr/*ms')[0]; tn=t.split('/')[-1]; ms=float(tn[:-2])
    I=np.mean([np.array(Image.open(f),float) for f in glob.glob(t+'/*.tif*')],0)
    d=np.mean([np.array(Image.open(f),float) for f in glob.glob(f'{root}-dark/fila17_col15_colorr/{tn}/*.tif*')],0)
    return ndi.uniform_filter((I-d)/ms,15)
import sys
for root in [B]+sys.argv[1:]:
    c0=L(root,17,15); out=[]
    for (r,c) in [(15,15),(19,15),(17,13),(17,17),(16,15),(18,15)]:
        q=L(root,r,c)/c0
        prof=q[:,560] if c==15 else q[560,:]
        out.append(f'({r},{c}) q[borde0]={prof[5]:.2f} q[centro]={prof[560]:.2f} q[borde1119]={prof[-6]:.2f}')
    print(root.split('/')[-1]); print('\n'.join(out))
