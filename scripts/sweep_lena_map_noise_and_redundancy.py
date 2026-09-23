"""Where does the Lena(amplitude)+Map(phase) phase become recoverable?
(A) photon-count sweep on the 9x9 grid; (B) higher data redundancy at a
FIXED HR canvas: denser LED grids spanning the same physical extent as the
9x9/6mm array (15x15 @ 48/14 mm, 21x21 @ 48/20 mm), so the synthetic
aperture -- hence the HR canvas -- stays 96x96 while LED count (redundancy
= LEDs * LR px / HR px) goes 9 -> 25 -> 49. Wirtinger flow (200 epochs) vs
Adam gradient descent with the amplitude loss (100 iterations), green, 32px
crops, phase max 0.3pi. Run from the repo root:
python3 scripts/sweep_lena_map_noise_and_redundancy.py out.json (~10+ min on 4
cores). Not part of the provenance pipeline."""
import os
os.environ["OMP_NUM_THREADS"]="1"; os.environ["OPENBLAS_NUM_THREADS"]="1"; os.environ["MKL_NUM_THREADS"]="1"
import sys, json, time, dataclasses, numpy as np
from multiprocessing import Pool
sys.path.insert(0,"src")
from ptyco_full_simulator import config, forward_model, led_array, metrics, optics, reconstruction, joint_calibration as jc
from ptyco_full_simulator.test_objects import lena_map_object
CROP=32; PHASE_MAX=0.3*np.pi; SPAN_MM=48.0
def job(a):
    exp,grid_size,peak,seed=a
    t=time.time()
    setup=config.default_setup(channel="green",grid_size=grid_size,objective="2_5x_na007",resolution_px=(CROP,CROP))
    setup=dataclasses.replace(setup,led_array=config.LEDArrayConfig(grid_size=grid_size,pitch_mm=SPAN_MM/(grid_size-1)))
    factor=optics.upsampling_factor(setup); hp=optics.actual_hr_pixel_size_um(setup,factor); hs=optics.hr_shape((CROP,CROP),factor)
    truth,_=lena_map_object(hs,phase_max_rad=PHASE_MAX); dk=1/(hs[1]*hp)
    grid=[{**e,"fx":round(e["fx"]/dk)*dk,"fy":round(e["fy"]/dk)*dk} for e in led_array.build_led_grid(setup.led_array,setup.wavelength_um)]
    lp,na,wl=setup.lr_pixel_size_um,setup.objective.na,setup.wavelength_um
    raw=forward_model.simulate_lr_stack(truth,hp,grid,(CROP,CROP),lp,na,wl,peak_photon_count=peak,rng=np.random.default_rng(seed))
    wf=reconstruction.reconstruct(raw,grid,hp,lp,na,wl,factor,iterations=200)["object"]
    scale=(hs[0]*hs[1])/(CROP*CROP); meas={k:v/scale**2 for k,v in raw.items()}
    init=jc.initial_object_from_center_led(meas[(grid[0]["row"],grid[0]["col"])],hs)
    gd=jc.reconstruct_and_calibrate(meas,grid,hs,hp,(CROP,CROP),lp,na,wl,init,n_iterations=100,calibrate_leds=False,loss="amplitude")["object"]
    f=lambda o:metrics.compare_to_ground_truth(o,truth)
    a_,b_=f(wf),f(gd)
    return {"exp":exp,"grid":grid_size,"n_leds":len(grid),"hr":list(hs),"redundancy":len(grid)*CROP*CROP/(hs[0]*hs[1]),
            "peak":peak,"seed":seed,"wf_phase":a_["phase_correlation"],"wf_amp":a_["amplitude_correlation"],
            "gd_phase":b_["phase_correlation"],"gd_amp":b_["amplitude_correlation"],"secs":time.time()-t}
if __name__=="__main__":
    jobs=[("A",9,pk,s) for pk in (100.0,1000.0,10000.0) for s in range(4)]
    jobs+=[("B",g,pk,s) for g in (15,21) for pk in (20.0,1000.0) for s in range(2)]
    with Pool(os.cpu_count()) as pool: res=pool.map(job,jobs,chunksize=1)
    json.dump(res,open(sys.argv[1],"w"))
