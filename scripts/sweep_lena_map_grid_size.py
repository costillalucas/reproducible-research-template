"""Does more data (bigger LED grid) rescue reconstruction of a detailed
real-image object (Lena amplitude + Map phase, src/ptyco_full_simulator/
test_objects.py)? Wirtinger flow (200 epochs) vs Adam gradient descent with
the amplitude loss (100 iterations), green channel, 32px crops, objective
"current", LED k rounded to a spectrum bin. Run from the repo root:
python3 scripts/sweep_lena_map_grid_size.py out.json   (several minutes;
the 21x21 jobs dominate). Not part of the provenance pipeline."""
import os
os.environ["OMP_NUM_THREADS"]="1"; os.environ["OPENBLAS_NUM_THREADS"]="1"; os.environ["MKL_NUM_THREADS"]="1"
import sys, json, time, numpy as np
from multiprocessing import Pool
sys.path.insert(0,"src")
from ptyco_full_simulator import config, forward_model, led_array, metrics, optics, reconstruction, joint_calibration as jc
from ptyco_full_simulator.test_objects import lena_map_object
CROP=32; PHASE_MAX=0.3*np.pi
def job(a):
    grid_size,peak,seed=a
    t=time.time()
    setup=config.default_setup(channel="green",grid_size=grid_size,objective="2_5x_na007",resolution_px=(CROP,CROP))
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
    a,b=f(wf),f(gd)
    return {"grid":grid_size,"n_leds":len(grid),"hr":list(hs),"peak":peak,"seed":seed,
            "wf_phase":a["phase_correlation"],"wf_amp":a["amplitude_correlation"],
            "gd_phase":b["phase_correlation"],"gd_amp":b["amplitude_correlation"],"secs":time.time()-t}
if __name__=="__main__":
    jobs=[(21,None,0),(21,20.0,0),(21,20.0,1)]+[(15,None,0)]+[(15,20.0,s) for s in range(4)]+[(9,None,0)]+[(9,20.0,s) for s in range(4)]
    with Pool(os.cpu_count()) as pool: res=pool.map(job,jobs,chunksize=1)
    json.dump(res,open(sys.argv[1],"w"))
