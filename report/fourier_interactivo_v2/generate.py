"""Standalone FPM teaching data. Run with Python, NumPy and Pillow."""
from pathlib import Path
import base64
import io
import json
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
N = 128
Y, X = np.mgrid[:N, :N]
U, V = X - N // 2, Y - N // 2
F = lambda a: np.fft.fftshift(np.fft.fft2(a, norm='ortho'))
INV = lambda a: np.fft.ifft2(np.fft.ifftshift(a), norm='ortho')
LEDS = sorted([(x, y) for y in range(-3, 4) for x in range(-3, 4)],
              key=lambda p: (p[0]**2 + p[1]**2, np.arctan2(p[1], p[0])))
MASKS = [((U + x*10)**2 + (V + y*10)**2 <= 18**2) for x, y in LEDS]
SELECTED = [LEDS.index(p) for p in [(0, 0), (1, 0), (2, 1)]]


def png(a, limit=1, kind='gray'):
    t = np.clip(a / max(limit, 1e-12), -1 if kind == 'signed' else 0, 1)
    if kind == 'phase':
        t = np.stack([.12+.82*t, .16+.65*t, .32+.15*t], -1)
    elif kind == 'signed':
        t = t[..., None]
        neutral = np.array([.08, .12, .19])
        t = neutral + np.maximum(t, 0)*(np.array([1, .55, .32])-neutral) + np.maximum(-t, 0)*(np.array([.25, .65, 1])-neutral)
    image = Image.fromarray(np.uint8(np.clip(t, 0, 1)*255))
    buf = io.BytesIO()
    image.save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


def gradient(s, mask, intensity):
    z = INV(s * mask)
    residual = abs(z) - np.sqrt(intensity)
    g = mask * F(residual*z/np.maximum(abs(z), 1e-12))
    return float(np.sum(residual**2)), g, z, residual


def object_images(s, offset=0):
    o = INV(s) * np.exp(-1j*offset)
    # Signed phase exposes small negative updates instead of hiding them.
    return dict(amp=png(abs(o)), phase=png(np.angle(o), 1.5, 'signed'))


def assert_gradient(s, mask, intensity):
    rng = np.random.default_rng(7)
    probe = s + .01*(rng.normal(size=s.shape)+1j*rng.normal(size=s.shape))
    d = rng.normal(size=s.shape)+1j*rng.normal(size=s.shape)
    d /= np.linalg.norm(d)
    _, g, _, _ = gradient(probe, mask, intensity)
    h = 1e-5
    numerical = (gradient(probe+h*d, mask, intensity)[0]-gradient(probe-h*d, mask, intensity)[0])/(2*h)
    assert np.isclose(numerical, 2*np.real(np.vdot(g, d)), rtol=1e-5, atol=1e-7)


im = Image.new('L', (N, N), 220)
draw = ImageDraw.Draw(im)
draw.text((48, 52), 'FPM', fill=50, stroke_width=1)
for k in range(7):
    draw.rectangle((20+4*k, 22, 21+4*k, 43), fill=65)
    draw.rectangle((78, 75+4*k, 106, 76+4*k), fill=75)
draw.ellipse((20, 77, 49, 106), outline=70, width=2)
amplitude = np.asarray(im)/255
phase = .85*np.exp(-((U-20)**2+(V+26)**2)/220) + .6*np.exp(-((U+28)**2+(V-24)**2)/140)
phase += .25*(1+np.cos(2*np.pi*10*X/N))*np.exp(-(U**2+V**2)/700)

samples = {}
for name, a, p in [('amplitud', amplitude, np.zeros_like(phase)),
                   ('fase', np.ones_like(amplitude)*.86, phase),
                   ('mixta', amplitude, phase)]:
    obj = a*np.exp(1j*p)
    spectrum = F(obj)
    intensities = [abs(INV(spectrum*m))**2 for m in MASKS]
    peak = max(i.max() for i in intensities)
    initial = F(np.sqrt(intensities[0]).astype(complex))
    assert_gradient(initial, MASKS[SELECTED[2]], intensities[SELECTED[2]])
    normalizer = sum(i.sum() for i in intensities)
    display_spectrum_limit = np.log1p(abs(spectrum)).max()
    corrections = []
    for j in SELECTED:
        before_loss, g, z, residual = gradient(initial, MASKS[j], intensities[j])
        updated = initial - .3*g
        after_loss = gradient(updated, MASKS[j], intensities[j])[0]
        assert after_loss <= before_loss + 1e-10
        assert np.all((updated-initial)[~MASKS[j]] == 0)
        comparisons = []
        for k in SELECTED:
            lb, _, zb, _ = gradient(initial, MASKS[k], intensities[k])
            la, _, za, _ = gradient(updated, MASKS[k], intensities[k])
            # Shared display gain for all three states of this LED, never independent gains.
            paired_peak = max(float(intensities[k].max()), float((abs(zb)**2).max()), float((abs(za)**2).max()))
            comparisons.append(dict(measured=png(intensities[k], paired_peak), before=png(abs(zb)**2, paired_peak),
                                    after=png(abs(za)**2, paired_peak), lossBefore=lb/float(intensities[k].sum()),
                                    lossAfter=la/float(intensities[k].sum())))
        corrections.append(dict(led=j, before=object_images(initial), after=object_images(updated),
                                predicted=png(abs(z)**2, peak), residual=png(residual, .25, 'signed'),
                                correction=png(abs(.3*g), float(abs(.3*g).max())),
                                spectrumBefore=png(np.log1p(abs(initial)), display_spectrum_limit),
                                spectrumAfter=png(np.log1p(abs(updated)), display_spectrum_limit),
                                comparisons=comparisons))
    estimate = initial.copy()
    recon = []
    for epoch in range(31):
        loss = sum(gradient(estimate, m, i)[0] for m, i in zip(MASKS, intensities))/normalizer
        offset = np.angle(np.vdot(obj, INV(estimate)))
        recon.append(dict(object_images(estimate, offset), loss=float(loss)))
        if epoch < 30:
            step = .8*(1-np.exp(-.3*(epoch+1)))
            for m, i in zip(MASKS, intensities):
                estimate -= step*gradient(estimate, m, i)[1]
    assert np.isfinite([r['loss'] for r in recon]).all()
    assert recon[-1]['loss'] < recon[0]['loss']
    # Same amplitude, toggle only phase. Shared intensity scale across both states and all LEDs.
    zero_phase_spectrum = F(a.astype(complex))
    off_images = [abs(INV(zero_phase_spectrum*MASKS[j]))**2 for j in SELECTED]
    clues_peak = max(peak, max(i.max() for i in off_images))
    samples[name] = dict(truth=dict(amp=png(a), phase=png(p, 1.5, 'signed')),
        initial=object_images(initial), spectrum=png(np.log1p(abs(spectrum)), display_spectrum_limit),
        captures=[png(i, peak) for i in intensities], enhanced=[png(i, float(i.max())) for i in intensities],
        corrections=corrections, recon=recon,
        phaseOff=[png(i, clues_peak) for i in off_images],
        phaseOn=[png(intensities[j], clues_peak) for j in SELECTED])
    print(f'{name}: relative amplitude residual {np.sqrt(recon[0]["loss"]):.4f} -> {np.sqrt(recon[-1]["loss"]):.4f}')

# Fourier intuition: a DC term and two exactly located frequency peaks.
gratings = []
for label, fx, fy in [('Gruesas', 6, 0), ('Finas', 26, 0), ('Horizontales', 0, 26), ('Diagonales', 18, 18)]:
    a = .65 + .25*np.cos(2*np.pi*(fx*X+fy*Y)/N)
    spec = F(a)
    frames = []
    for radius in [10, 18, 30]:
        pupil = U**2+V**2 <= radius**2
        intensity = abs(INV(spec*pupil))**2
        frames.append(png(intensity))
    gratings.append(dict(label=label, fx=fx, fy=fy, object=png(a),
                         spectrum=png(np.log1p(abs(spec)), np.log1p(abs(spec)).max()), captures=frames))
# Angle demonstration: central misses ±26, q=(-10,0) admits DC and +26.
a = .65 + .25*np.cos(2*np.pi*26*X/N)
spec = F(a)
angle_images = []
for q in [0, -10]:
    m = (U+q)**2+V**2 <= 18**2
    intensity = abs(INV(spec*m))**2
    angle_images.append(png(intensity))
assert np.std(abs(INV(spec*(U**2+V**2<=18**2)))**2) < 1e-12
assert np.std(abs(INV(spec*((U-10)**2+V**2<=18**2)))**2) > .01

# Exact discrete overlap used by the displayed forward model.
overlap = []
base = MASKS[SELECTED[1]]
for other in [(0,0),(-3,0)]:
    j = LEDS.index(other)
    overlap.append(dict(led=j, fraction=float(np.sum(base&MASKS[j])/np.sum(base))))
assert overlap[0]['fraction'] > 0 and overlap[1]['fraction'] == 0
payload = dict(leds=LEDS, selected=SELECTED, samples=samples, gratings=gratings,
               angleImages=angle_images, overlap=overlap)
serialized = json.dumps(payload, separators=(',', ':'), allow_nan=False)
html = (ROOT/'template.html').read_text().replace('__DATA__', serialized)
(ROOT/'index.html').write_text(html)
print(f'Wrote independent V2: {len(html)/1024:.0f} KiB; gradient, support, descent, overlap and angular-detail checks passed.')
