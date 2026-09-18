# ptyco-full-simulator

A multispectral (RGB) Fourier Ptychographic Microscopy pipeline: forward
model + Wirtinger flow reconstruction per channel
(`src/ptyco_full_simulator/`), registered onto one shared HR grid, coupled
via multi-wavelength phase unwrapping and a Cauchy dispersion fit, and
orchestrated by two Claude Code agents (reconstruction retry/accept, and
QC/confidence review). Full design and status:
`docs/roadmap_agentic_multispectral_pipeline.md`.

## Milestone 2: coupled multispectral reconstruction

On a synthetic 3-channel dispersion object, reconstructed through the
actual forward model and Wirtinger flow solver (not injected phase), the
milestone-2 coupled pipeline (shared HR grid → independent per-channel
reconstruction → piston removal → synthetic-wavelength unwrapping →
Cauchy dispersion fit) recovers the sample's thickness field with
correlation [srcnum:multispectral_thickness_correlation:0.88] to the true
field [src:multispectral_thickness_correlation].

On a larger, synthetic dispersion signal specifically constructed to
require real multi-wavelength unwrapping, the coupled pipeline's thickness
error is [srcnum:unwrapping_error_reduction_factor:183]x smaller than a
naive baseline that treats each channel's raw wrapped phase as
already-unwrapped optical path length [src:unwrapping_error_reduction_factor]
— evidence that the unwrapping/dispersion-fit step (milestone 2b) is
worth having, not just a coupling exercise.

## A real limitation of the baseline solver

The baseline Wirtinger flow reconstructor is far more sensitive to
amplitude contrast than previously documented: a uniform-amplitude (pure
phase) object reconstructs with phase correlation
[srcnum:phase_only_object_phase_correlation:-0.04]
[src:phase_only_object_phase_correlation] — worse than random — while the
identical phase field with just 5% amplitude contrast added reconstructs
with correlation [srcnum:five_percent_contrast_object_phase_correlation:0.65]
[src:five_percent_contrast_object_phase_correlation]. This matters because
this project's target samples (near-transparent biological specimens) are
exactly in the low-contrast regime where this baseline is weakest — see
`docs/roadmap_agentic_multispectral_pipeline.md` section 1, point 6.

## Fixing the low-contrast limitation: TIE-informed initialization

Initializing the solver with a Transport of Intensity Equation phase
estimate (`propagation.solve_tie`, from one extra simulated defocused
capture) instead of the default zero phase reliably escapes the
degenerate saddle point behind the limitation above. On a mixed
low/high-spatial-frequency phase object, phase correlation goes from
[srcnum:tie_informed_init_baseline_phase_correlation:0.31]
[src:tie_informed_init_baseline_phase_correlation] with the default
initialization to
[srcnum:tie_informed_init_phase_correlation:0.99]
[src:tie_informed_init_phase_correlation] with TIE-informed
initialization. Wired into both `pipelines/simulate_and_reconstruct.py`
(`--tie-defocus-um`) and `pipelines/reconstruct_multispectral_independent.py`
(per channel).

## Milestone 4: LED position self-calibration

Given a good object-spectrum estimate, the spectral-correlation LED
calibration (adapted from `eckert2018`) recovers a known injected
misalignment's scale factor to within
[srcnum:led_calibration_scale_recovery_error:0.0015]
[src:led_calibration_scale_recovery_error] of the true value — the core
calibration math works. It does **not**, however, reliably rescue a
reconstruction that is already badly corrupted by an uncorrected
misalignment (see `tests/test_led_calibration.py`'s documented negative
result) — the paper's own brightfield pre-calibration bootstrap stage,
not implemented here, is a real prerequisite for this to help on real
data, not an optional extra.

A plain least-squares fit of that calibration transform has no
resistance to a minority of badly miscorrected LEDs: with 10% of points
corrupted, its rotation error is
[srcnum:ransac_plain_fit_rotation_error_rad:0.18]
[src:ransac_plain_fit_rotation_error_rad] rad. `fit_similarity_transform_ransac`,
added to reject exactly this kind of outlier, recovers the true rotation
to within
[srcnum:ransac_robust_fit_rotation_error_rad:0.000000]
[src:ransac_robust_fit_rotation_error_rad] rad on the same corrupted data.

## Milestone 8: pupil recovery (EPRY) and a testbed-scale caveat

Adding EPRY pupil recovery (`ou2014`, `reconstruction.reconstruct`'s
`recover_pupil`) gives a real but modest improvement when a genuine
defocus aberration is present: assuming the ideal pupil, phase
correlation is [srcnum:epry_uncorrected_phase_correlation:0.69]
[src:epry_uncorrected_phase_correlation]; with EPRY on, it rises to
[srcnum:epry_corrected_phase_correlation:0.79]
[src:epry_corrected_phase_correlation]. The recovered pupil's phase
correlates [srcnum:epry_recovered_pupil_phase_correlation:0.65]
[src:epry_recovered_pupil_phase_correlation] with the true injected
aberration — confirming EPRY identifies the actual aberration, not just
"helps the object by coincidence".

However, on this project's small (9×9 LED, 12×12px) synthetic testbed,
turning EPRY on for a channel with **no** aberration present regresses an
already-well-converging reconstruction: phase correlation drops from
[srcnum:epry_small_scale_baseline_phase_correlation:0.95]
[src:epry_small_scale_baseline_phase_correlation] to
[srcnum:epry_small_scale_corrected_phase_correlation:0.53]
[src:epry_small_scale_corrected_phase_correlation] — `recover_pupil=True`
is **not** a safe default to enable unconditionally across all 3 RGB
channels in one run. Investigation ruled out "badly implemented" (EPRY
correctly recovers real aberrations above, and the literature's standard
fix for this kind of PIE-family instability barely changes the numbers)
in favor of "small-testbed/low-data-redundancy artifact": reproducing the
identical no-aberration scenario at a scale close to `ou2014`'s own real
demonstration (225 LEDs, 64×64px instead of 12×12px) makes the collapse
disappear — baseline
[srcnum:epry_paper_scale_baseline_phase_correlation:0.84]
[src:epry_paper_scale_baseline_phase_correlation] vs. EPRY
[srcnum:epry_paper_scale_corrected_phase_correlation:0.84]
[src:epry_paper_scale_corrected_phase_correlation], within a few percent.
This project's own real lab grids (81–441 LEDs) sit closer to the risky
small-scale end than to the paper's 225-image demo, so this caveat is
practically relevant, not just a synthetic-test artifact to dismiss.

## Correctness suite

[src:suite_coverage] — see `data/checks_results.json` for the full
pass/fail breakdown, including the negative control proving the
phase-only-object finding above is real (the check would fail if 5%
contrast did *not* score meaningfully better than uniform amplitude).
