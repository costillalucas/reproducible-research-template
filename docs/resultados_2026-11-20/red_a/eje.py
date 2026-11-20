import numpy as np, glob, sys
from PIL import Image
from scipy import ndimage as ndi
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
D=sys.argv[1]; out=sys.argv[2]
def load(p): return np.mean([np.array(Image.open(f),float) for f in sorted(glob.glob(p+'/*.tiff'))],0)
t=sorted(glob.glob(D+'/fila17_col15_colorr/*ms'))[0]; tn=t.split('/')[-1]
I=load(t); dk=load(D+'-dark/fila17_col15_colorr/'+tn) if glob.glob(D+'-dark/fila17_col15_colorr/'+tn) else np.zeros_like(I)
S=I-dk; print('exp',tn,'max raw',I.max(),'sat px',(I>=4095).sum(),'median',np.median(S))
bg=ndi.gaussian_filter(S,40); N=S/bg
print('contraste rms (sin flat, fondo suavizado):',N.std().round(4),' p1/p99:',np.percentile(N,[1,99]).round(3))
# particles: local deviation
d=ndi.gaussian_filter(N,2)-1
lab,n=ndi.label(np.abs(d)>0.04); sz=ndi.sum(np.ones_like(d),lab,range(1,n+1))
keep=[i+1 for i,s in enumerate(sz) if 20<s<3000]
cm=ndi.center_of_mass(np.abs(d),lab,keep); 
sgn=[np.sign(d[int(r),int(c)]) for r,c in cm]
print('objetos (|dev|>4%, 20-3000 px):',len(keep),' centro brillante:',sum(s>0 for s in sgn),' oscuro:',sum(s<0 for s in sgn))
c=np.array(N.shape)/2; dd=[np.hypot(r-c[0],c2-c[1]) for r,c2 in cm]
print('objetos dentro de 200 px del centro del ROI (recorte 400):',sum(x<200 for x in dd))
fig,ax=plt.subplots(1,2,figsize=(14,7))
ax[0].imshow(N,cmap='gray',vmin=np.percentile(N,1),vmax=np.percentile(N,99)); ax[0].set_title(f'LED eje {tn}, /fondo suavizado')
ax[0].add_patch(plt.Rectangle((c[1]-200,c[0]-200),400,400,fill=False,ec='r'))
z=N[int(c[0])-200:int(c[0])+200,int(c[1])-200:int(c[1])+200]
ax[1].imshow(z,cmap='gray',vmin=np.percentile(z,1),vmax=np.percentile(z,99)); ax[1].set_title('recorte central 400 px')
plt.tight_layout(); plt.savefig(out,dpi=90)
