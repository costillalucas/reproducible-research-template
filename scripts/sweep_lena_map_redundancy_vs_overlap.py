"""Separate data redundancy (LED count) from adjacent-LED overlap at a FIXED
96x96 HR canvas, Lena(amplitude)+Map(phase), green, 32px crops, phase max
0.3pi, Poisson noise, Adam gradient descent with the amplitude loss (100
iterations; no Wirtinger flow here, to save time). All arms are subsets of
the 21x21 grid (48 mm span, pitch 2.4 mm) or the uniform 9x9/15x15/21x21
grids over the same 48 mm; LED k snapped to a spectrum bin.
  U9/U15/U21 : uniform grid over 48 mm (count and overlap move together)
  R81/R225   : random subset (centre kept) of the 21x21 grid, same count as
               U9/U15 but a different local-spacing distribution
  C9/C15     : central 9x9 / 15x15 of the 21x21 grid: SAME overlap as U21,
               fewer LEDs, but a smaller synthetic aperture (canvas stays 96)
Reports the phase/amplitude correlation against the full truth and against
the truth low-passed to each arm's synthetic-aperture cutoff (NA_obj + max
LED NA), plus the median nearest-neighbour LED spacing in pupil radii and
the corresponding adjacent-pupil overlap. Run from the repo root:
python3 scripts/sweep_lena_map_redundancy_vs_overlap.py out.json [peak] (~15 min
on 2 cores). Not part of the provenance pipeline."""
import os
os.environ["OMP_NUM_THREADS"]="1"; os.environ["OPENBLAS_NUM_THREADS"]="1"; os.environ["MKL_NUM_THREADS"]="1"
import sys, json, time, dataclasses, numpy as np
from multiprocessing import Pool
sys.path.insert(0,"src")
from ptyco_full_simulator import config, forward_model, led_array, metrics, optics, joint_calibration as jc
from ptyco_full_simulator.test_objects import lena_map_object
CROP=32; PHASE_MAX=0.3*np.pi; SPAN_MM=48.0
ARMS={"U9":(9,"uniform"),"R81":(21,"random81"),"C9":(21,"crop9"),
      "U15":(15,"uniform"),"R225":(21,"random225"),"C15":(21,"crop15"),"U21":(21,"uniform")}
def select(grid,mode,rng):
    if mode=="uniform": return grid
    c=grid[0]  # centre LED (sorted by radius)
    if mode.startswith("random"):
        n=int(mode[6:]); idx=rng.choice(np.arange(1,len(grid)),n-1,replace=False)
        sub=[grid[0]]+[grid[i] for i in idx]
        return sorted(sub,key=lambda e:e["radial_mm"])
    m=int(mode[4:])//2
    return [e for e in grid if abs(e["row"]-c["row"])<=m and abs(e["col"]-c["col"])<=m]
def overlap_stats(grid,dk,R):
    p=np.array([[e["fx"],e["fy"]] for e in grid]); d=np.hypot(*(p[:,None]-p[None]).transpose(2,0,1)); np.fill_diagonal(d,np.inf)
    x=min(np.median(d.min(1))/(2*R),1.0)
    return float(np.median(d.min(1))/R), float((2/np.pi)*(np.arccos(x)-x*np.sqrt(1-x*x)))
def lowpass(obj,cut_bins):
    ky=np.fft.fftshift(np.fft.fftfreq(obj.shape[0]))*obj.shape[0]; kx=np.fft.fftshift(np.fft.fftfreq(obj.shape[1]))*obj.shape[1]
    m=np.hypot(*np.meshgrid(kx,ky))<=cut_bins
    return np.fft.ifft2(np.fft.ifftshift(np.fft.fftshift(np.fft.fft2(obj))*m))
def job(a):
    arm,peak,seed=a; grid_size,mode=ARMS[arm]; t=time.time()
    setup=config.default_setup(channel="green",grid_size=grid_size,objective="2_5x_na007",resolution_px=(CROP,CROP))
    setup=dataclasses.replace(setup,led_array=config.LEDArrayConfig(grid_size=grid_size,pitch_mm=SPAN_MM/(grid_size-1)))
    factor=optics.upsampling_factor(setup); hp=optics.actual_hr_pixel_size_um(setup,factor); hs=optics.hr_shape((CROP,CROP),factor)
    truth,_=lena_map_object(hs,phase_max_rad=PHASE_MAX); dk=1/(hs[1]*hp)
    grid=led_array.build_led_grid(setup.led_array,setup.wavelength_um)
    grid=select(grid,mode,np.random.default_rng(1000+seed))
    grid=[{**e,"fx":round(e["fx"]/dk)*dk,"fy":round(e["fy"]/dk)*dk} for e in grid]
    lp,na,wl=setup.lr_pixel_size_um,setup.objective.na,setup.wavelength_um
    R=na/wl; cut=(R+max(np.hypot(e["fx"],e["fy"]) for e in grid))/dk
    nn,ov=overlap_stats(grid,dk,R)
    raw=forward_model.simulate_lr_stack(truth,hp,grid,(CROP,CROP),lp,na,wl,peak_photon_count=peak,rng=np.random.default_rng(seed))
    scale=(hs[0]*hs[1])/(CROP*CROP); meas={k:v/scale**2 for k,v in raw.items()}
    init=jc.initial_object_from_center_led(meas[(grid[0]["row"],grid[0]["col"])],hs)
    gd=jc.reconstruct_and_calibrate(meas,grid,hs,hp,(CROP,CROP),lp,na,wl,init,n_iterations=100,calibrate_leds=False,loss="amplitude")["object"]
    full=metrics.compare_to_ground_truth(gd,truth); bl=metrics.compare_to_ground_truth(gd,lowpass(truth,cut))
    return {"arm":arm,"n_leds":len(grid),"hr":list(hs),"redundancy":len(grid)*CROP*CROP/(hs[0]*hs[1]),"peak":peak,"seed":seed,
            "nn_spacing_pupil_radii":nn,"adjacent_overlap":ov,"cutoff_bins":float(cut),
            "phase":full["phase_correlation"],"amp":full["amplitude_correlation"],
            "phase_bandlimited":bl["phase_correlation"],"amp_bandlimited":bl["amplitude_correlation"],"secs":time.time()-t}
if __name__=="__main__":
    peak=float(sys.argv[2]) if len(sys.argv)>2 else 1000.0
    jobs=[(arm,peak,s) for arm in ("U21","U15","R225","C15","U9","R81","C9") for s in range(3)]
    with Pool(2) as pool: res=pool.map(job,jobs,chunksize=1)
    json.dump(res,open(sys.argv[1],"w"))
    for arm in ARMS:
        r=[x for x in res if x["arm"]==arm]
        print(arm,r[0]["n_leds"],"nn=%.2fR ov=%.2f"%(r[0]["nn_spacing_pupil_radii"],r[0]["adjacent_overlap"]),
              "phase %.3f bl %.3f amp %.3f"%tuple(np.mean([x[k] for x in r]) for k in ("phase","phase_bandlimited","amp")))
