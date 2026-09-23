"""Experiment behind the "defocus-pair residual" TIE-continuation diagnostic in
docs/roadmap_agentic_multispectral_pipeline.md milestone 12 (negative result).
Run from the repo root: python3 scripts/explore_tie_continuation_diagnostic.py (~5 min).
For 6 objects, tracks true phase correlation vs. the residual between the
current FPM estimate's predicted +/-30um defocus pair and the measured pair,
at k = 0/5/10/20/40 FPM iterations after a TIE-informed start. AMP[0] switches
between the full-field and the phase-only (measured on-axis amplitude) variant:
edit it in the loop to reproduce either. Not part of the provenance pipeline."""
import sys, numpy as np
sys.path.insert(0,"src"); sys.path.insert(0,"tests")
from ptyco_full_simulator import config, forward_model, led_array, optics, reconstruction, propagation as prop
from ptyco_full_simulator.optics import circular_pupil
from test_tie_informed_initialization import _tie_informed_initial_object
crop=32; D=30.0
setup=config.default_setup(channel="green",grid_size=9,objective="2_5x_na007",resolution_px=(crop,crop))
factor=optics.upsampling_factor(setup); hp=optics.actual_hr_pixel_size_um(setup,factor); hs=optics.hr_shape((crop,crop),factor)
lp=setup.lr_pixel_size_um; na=setup.objective.na; wl=setup.wavelength_um
grid=led_array.build_led_grid(setup.led_array,wl)
pupil=circular_pupil((crop,crop),lp,na,wl)
h,w=hs; y,x=np.mgrid[0:h,0:w].astype(float); yc,xc=y/h-0.5,x/w-0.5
def make_obj(a_low,a_high,f_high,contrast,seed):
    amp=(1-contrast)+contrast*np.exp(-((xc-0.1)**2+(yc+0.05)**2)/(2*0.08**2))
    amp=amp+0.3*contrast*np.exp(-((xc+0.15)**2+(yc-0.1)**2)/(2*0.05**2)); amp=np.clip(amp,0.05,1)
    ph=a_low*np.sin(2*np.pi*xc+seed)+a_high*np.sin(2*np.pi*f_high*xc+seed)*np.cos(2*np.pi*yc*(1+seed%3))
    return amp*np.exp(1j*ph),ph
AMP=[None]
def lr_pair(obj):
    spec=np.fft.fftshift(np.fft.fft2(obj)); ys=slice(h//2-crop//2,h//2+crop//2); xs=slice(w//2-crop//2,w//2+crop//2)
    f=np.fft.ifft2(np.fft.ifftshift(spec[ys,xs]*pupil))*(crop*crop)/(h*w)
    if AMP[0] is not None: f=AMP[0]*np.exp(1j*np.angle(f))   # phase-only variant: measured on-axis amplitude
    return [np.abs(prop.angular_spectrum_propagate(f,d,lp,wl))**2 for d in (D,-D)]
def diag(obj,meas):
    p=lr_pair(obj)
    g=sum(np.sum(a*b) for a,b in zip(p,meas))/max(sum(np.sum(a*a) for a in p),1e-30)  # best global intensity gain
    return float(np.sqrt(sum(np.sum((g*a-b)**2) for a,b in zip(p,meas))/sum(np.sum(b**2) for b in meas)))
def pc(o,ph):
    a=np.angle(o); return float(np.corrcoef((a-a.mean()).ravel(),(ph-ph.mean()).ravel())[0,1])
objs=[(0.3,0.15,6,0.6,0),(0.3,0.15,6,0.3,1),(0.2,0.25,8,0.5,2),(0.4,0.1,4,0.4,3),(0.15,0.3,10,0.6,4),(0.3,0.2,6,0.15,5)]
ks=[0,5,10,20,40]
summ=[]
for i,p in enumerate(objs):
    obj,ph=make_obj(*p)
    lr=forward_model.simulate_lr_stack(obj,hp,grid,(crop,crop),lp,na,wl)
    AMP[0]=None; meas=lr_pair(obj)
    c=grid[0]; AMP[0]=np.sqrt(np.clip(lr[(c['row'],c['col'])],0,None))
    init,tie=_tie_informed_initial_object(obj,grid,lr,hp,wl,factor,D)
    rows=[]
    for k in ks:
        o=init if k==0 else reconstruction.reconstruct(lr,grid,hp,lp,na,wl,factor,iterations=k,initial_object=init)["object"]
        rows.append((k,pc(o,ph),diag(o,meas)))
    corr=[r[1] for r in rows]; dg=[r[2] for r in rows]
    best_by_diag=rows[int(np.argmin(dg))]; oracle=rows[int(np.argmax(corr))]
    print(f"obj{i} {p}: "+" ".join(f"k{k}:{c:.3f}/{d:.3f}" for k,c,d in rows))
    print(f"   diag-picked k={best_by_diag[0]} corr {best_by_diag[1]:.3f} | TIE-only {corr[0]:.3f} | full40 {corr[-1]:.3f} | oracle k={oracle[0]} {oracle[1]:.3f} | spearman(diag,corr)={np.corrcoef(np.argsort(np.argsort(dg)),np.argsort(np.argsort(corr)))[0,1]:+.2f}")
    summ.append((best_by_diag[1],corr[0],corr[-1],oracle[1]))
s=np.array(summ); print("MEAN diag-picked %.3f | TIE-only %.3f | full40 %.3f | oracle %.3f"%tuple(s.mean(0)))
