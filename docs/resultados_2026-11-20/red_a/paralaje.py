import numpy as np, glob
from PIL import Image
from scipy import ndimage as ndi
B='/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-11-20.2048ms-red.a'
def L(root,r,c):
    t=glob.glob(f'{root}/fila{r}_col{c}_colorr/*ms')[0]; tn=t.split('/')[-1]
    I=np.mean([np.array(Image.open(f),float) for f in glob.glob(t+'/*.tif*')],0)
    d=np.mean([np.array(Image.open(f),float) for f in glob.glob(f'{root}-dark/fila17_col15_colorr/{tn}/*.tif*')],0)
    return I-d
def Q(r,c): return L(B,r,c)/L(B+'-sinmuestra',r,c)
def shift(a,b):
    a=a-a.mean(); b=b-b.mean()
    F=np.fft.fft2(a)*np.conj(np.fft.fft2(b)); cc=np.real(np.fft.ifft2(F/(np.abs(F)+1e-9)))
    cc=ndi.gaussian_filter(np.fft.fftshift(cc),1); i=np.unravel_index(cc.argmax(),cc.shape); m=np.array(cc.shape)//2
    return (i[0]-m[0],i[1]-m[1]), round(float(cc.max()),3)
q0=Q(17,15)
regiones={'disco grande (fila~430,col~640)':(360,500,570,710),'2 discos centro (fila~550,col~430-560)':(470,630,360,620),
          'estrellas arriba-der (fila 80-280,col 780-1100)':(60,300,780,1100),'estrellas+disco abajo-der (fila 700-800,col 800-900)':(690,810,790,910)}
for led in [(16,15),(18,15),(17,14),(17,16)]:
    q=Q(*led); print('LED',led)
    for n,(r0,r1,c0,c1) in regiones.items():
        print('   ',n,'desplazamiento (filas,col) px:',*shift(q0[r0:r1,c0:c1],q[r0:r1,c0:c1]))
