import glob,numpy as np,tifffile
from scipy.ndimage import gaussian_filter
B='/home/chanoscopio/Documents/AleYLu/imagenes_tomadas/2026-11-06-'
def img(z):
    f=sorted(glob.glob(B+z+'/fila17_col15_colorr/18ms/*.tiff'))[0]
    return tifffile.imread(f).astype(float)
F=img('sinmuestra'); 
Z=['a.1','a.2','b','c','d','e','f']
N={}
for z in Z:
    r=img(z)/F; r=r-gaussian_filter(r,20); N[z]=r[60:-60,60:-60]
    print(z,'contraste sd(I/F, pasa-alto)=%.4f'%N[z].std())
print('corr entre zonas (pasa-alto):')
print('      '+' '.join(f'{z:>6}' for z in Z))
for a in Z:
    print(f'{a:>5} '+' '.join(f'{np.corrcoef(N[a].ravel(),N[b].ravel())[0,1]:6.2f}' for b in Z))
