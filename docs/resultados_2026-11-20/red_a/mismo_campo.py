import numpy as np, glob
from PIL import Image
from scipy import ndimage as ndi
B='/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-11-20.2048ms-'
def L(root):
    t=glob.glob(f'{root}/fila17_col15_colorr/*ms')[0]
    I=np.mean([np.array(Image.open(f),float) for f in glob.glob(t+'/*.tif*')],0)
    return I/ndi.gaussian_filter(I,40)-1
a=L(B+'red.a'); b=L(B+'red.b-prueba-1405')
F=np.fft.fft2(a)*np.conj(np.fft.fft2(b)); c=np.real(np.fft.ifft2(F/np.abs(F)))
i=np.unravel_index(c.argmax(),c.shape); sh=[(x if x<s/2 else x-s) for x,s in zip(i,c.shape)]
print('desplazamiento red.a vs red.b (filas, cols) px:',sh,' pico de correlación:',round(c.max(),3),' (ruido ~',round(np.std(c),4),')')
cc=np.fft.fftshift(c); m=np.array(cc.shape)//2
cc[m[0]-3:m[0]+4,m[1]-3:m[1]+4]=0
for k in range(3):
    j=np.unravel_index(cc.argmax(),cc.shape); print('pico secundario',k,(j[0]-m[0],j[1]-m[1]),round(cc[j],4)); cc[j[0]-3:j[0]+4,j[1]-3:j[1]+4]=0
# also sample vs flat at 0 shift (dust only)
f=L(B+'red.a-sinmuestra'); print('corr a·flat (polvo fijo):',round(np.corrcoef(a.ravel(),f.ravel())[0,1],3),' a·b:',round(np.corrcoef(a.ravel(),b.ravel())[0,1],3),' b·flat:',round(np.corrcoef(b.ravel(),f.ravel())[0,1],3))
