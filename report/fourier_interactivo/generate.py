"""Generate embedded optical demo data; numpy + Pillow, no network required."""
from pathlib import Path
import base64, io, json
import numpy as np
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parent
N=128
y,x=np.mgrid[:N,:N]; u=x-N//2; v=y-N//2
im=Image.new('L',(N,N),220); d=ImageDraw.Draw(im)
d.text((43,51),'FPM',fill=45,stroke_width=1)
for k in range(7):
    d.rectangle((20+4*k,22,21+4*k,43),fill=65)
    d.rectangle((78,75+4*k,106,76+4*k),fill=75)
d.ellipse((20,77,49,106),outline=70,width=2)
a=np.asarray(im)/255
phase=0.85*np.exp(-((u-20)**2+(v+26)**2)/220)+0.6*np.exp(-((u+28)**2+(v-24)**2)/140)
obj=a*np.exp(1j*phase)
F=lambda z: np.fft.fftshift(np.fft.fft2(z,norm='ortho'))
Fi=lambda z: np.fft.ifft2(np.fft.ifftshift(z),norm='ortho')
S=F(obj)
leds=sorted([(cx,cy) for cy in range(-3,4) for cx in range(-3,4)],key=lambda p:(p[0]**2+p[1]**2,np.arctan2(p[1],p[0])))
masks=[((u+cx*10)**2+(v+cy*10)**2<=18**2) for cx,cy in leds]
fields=[Fi(S*m) for m in masks]; intens=[abs(z)**2 for z in fields]
def png(arr, vmax=1, color=False):
    t=np.clip(arr/vmax,0,1)
    if color:
        rgb=np.stack([0.12+0.82*t,0.16+0.65*t,0.32+0.15*t],-1)
        out=Image.fromarray(np.uint8(255*np.clip(rgb,0,1)))
    else: out=Image.fromarray(np.uint8(255*t))
    b=io.BytesIO();out.save(b,format='PNG');return 'data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()
def object_images(spectrum, phase_offset=None):
    rec=Fi(spectrum)
    # A common phase reference for each before/after pair: no artificial jump.
    if phase_offset is None:
        phase_offset=np.angle(np.vdot(obj,rec))
    rec=rec*np.exp(-1j*phase_offset)
    return {'amp':png(abs(rec)), 'phase':png(np.angle(rec),1,color=True)}

def signed_png(arr, limit):
    t=np.clip(arr/max(limit,1e-12),-1,1)[...,None]
    neutral=np.array([0.08,0.12,0.19])
    positive=np.array([1.0,0.55,0.32]); negative=np.array([0.25,0.65,1.0])
    rgb=neutral+np.maximum(t,0)*(positive-neutral)+np.maximum(-t,0)*(negative-neutral)
    b=io.BytesIO();Image.fromarray(np.uint8(255*rgb)).save(b,format='PNG')
    return 'data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()

def loss_and_gradient(spectrum, mask, measured):
    z=Fi(spectrum*mask)
    residual=abs(z)-np.sqrt(measured)
    # dL/dS*, L = sum (|z|-sqrt(I))^2. FFT is unitary here.
    gradient=mask*F(residual*z/np.maximum(abs(z),1e-12))
    return float(np.sum(residual**2)), gradient, z, residual

est=F(np.sqrt(intens[0]).astype(complex)); snapshots=[];errors=[]
# Three actual updates in each pass, sampled for a legible teaching sequence.
trace_leds=[leds.index(p) for p in [(0,0),(1,0),(2,1)]]
peak=max(I.max() for I in intens)
normalizer=sum(I.sum() for I in intens)
# Finite-difference validation of the complex gradient and adjoint convention.
rng=np.random.default_rng(42)
probe=est+0.01*(rng.normal(size=est.shape)+1j*rng.normal(size=est.shape))
direction=rng.normal(size=est.shape)+1j*rng.normal(size=est.shape)
direction/=np.linalg.norm(direction)
L,g,_,_=loss_and_gradient(probe,masks[trace_leds[-1]],intens[trace_leds[-1]])
h=1e-5
finite=(loss_and_gradient(probe+h*direction,masks[trace_leds[-1]],intens[trace_leds[-1]])[0]-loss_and_gradient(probe-h*direction,masks[trace_leds[-1]],intens[trace_leds[-1]])[0])/(2*h)
analytic=2*np.real(np.vdot(g,direction))
assert np.isclose(finite,analytic,rtol=1e-5,atol=1e-7),(finite,analytic)
for epoch in range(31):
    total=sum(np.sum((abs(Fi(est*m))-np.sqrt(I))**2) for m,I in zip(masks,intens))
    err=np.sqrt(total/normalizer)
    snapshots.append(dict(object_images(est),error=float(err),loss=float(total/normalizer)))
    errors.append(float(err))
    if epoch==30: break
    step=0.8*(1-np.exp(-0.3*(epoch+1)))
    for j,(m,I) in enumerate(zip(masks,intens)):
        local_loss,g,z,residual=loss_and_gradient(est,m,I)
        new_est=est-step*g
        if j in trace_leds:
            offset=np.angle(np.vdot(obj,Fi(est)))
            after_loss=loss_and_gradient(new_est,m,I)[0]
            assert after_loss<=local_loss+1e-10
            assert np.all((new_est-est)[~m]==0)
        est=new_est
# A single illustrative first update, selectable by LED, from the same initial guess.
guide=[]
initial=F(np.sqrt(intens[0]).astype(complex))
for j in trace_leds:
    local,g,z,residual=loss_and_gradient(initial,masks[j],intens[j])
    step=0.8*(1-np.exp(-0.3))
    updated=initial-step*g
    after_loss=loss_and_gradient(updated,masks[j],intens[j])[0]
    assert after_loss<=local+1e-10
    guide.append({'led':j,'before':object_images(initial,0),
        'after':object_images(updated,0),'predicted':png(abs(z)**2,peak),
        'residual':signed_png(residual,0.25),
        'gradient':png(abs(g),max(float(abs(g).max()),1e-12)),
        'spectrumBefore':png(np.log1p(abs(initial)),np.log1p(abs(initial)).max()),
        'spectrumAfter':png(np.log1p(abs(updated)),np.log1p(abs(initial)).max())})
data={'leds':leds,'captures':[png(I,peak) for I in intens],
    'enhanced':[png(I,I.max()) for I in intens], 'peaks':[float(I.max()) for I in intens],
    'spectrum':png(np.log1p(abs(S)),np.log1p(abs(S)).max()),
    'truth':{'amp':png(a),'phase':png(phase,1,True)},'recon':snapshots,'guide':guide}
assert len(leds)==49 and errors[-1]<errors[0]*0.5,errors
assert np.isfinite(errors).all()
html=(ROOT/'template.html').read_text().replace('__DATA__',json.dumps(data,separators=(',',':')))
(ROOT/'index.html').write_text(html)
print(f'49 capturas; error relativo de amplitudes {errors[0]:.4f} → {errors[-1]:.4f}; HTML {len(html)//1024} KiB')
