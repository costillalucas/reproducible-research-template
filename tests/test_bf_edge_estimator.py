"""Ground-truth tests for the J2 bright-field geometry estimators
(results/esferas_2026-07-08/geometria/).

These estimators produce the number the whole J2 argument rests on -- the
bright-field cutoff radius R_BF in LED steps -- so the claim that they are
unbiased, and in particular the claim that R_BF is free of the pixel size, is
tested here against synthetic data with a KNOWN answer rather than asserted in
a docstring.
"""
import importlib.util
import os
import sys

import numpy as np
import pytest

GEO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "results", "esferas_2026-07-08", "geometria")


def _load(name):
    path = os.path.join(GEO, name + ".py")
    if not os.path.exists(path):
        pytest.skip(f"{path} not present")
    if GEO not in sys.path:
        sys.path.insert(0, GEO)
    spec = importlib.util.spec_from_file_location("j2_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def edge():
    return _load("10_bf_edge")


@pytest.fixture(scope="module")
def circles():
    return _load("12_edge_circles")


# --------------------------------------------------------------- helpers ---
def synth(edge, c0=15.12, r0=18.22, px_per_step=1550.0, R_BF=1.70, w_steps=0.02,
          rot_deg=0.0, amp=210.0, noise=1.4, seed=0, nblk=56, block=20, frame=1120):
    """Synthetic block stack from the same forward model, with known R_BF."""
    th = np.radians(rot_deg)
    M = px_per_step * np.array([[-np.cos(th), np.sin(th)],
                                [-np.sin(th), -np.cos(th)]])
    rho0 = R_BF * px_per_step
    w = max(w_steps * px_per_step, 1.0)
    k = (np.arange(nblk) + 0.5) * block - frame / 2.0
    u, v = np.meshgrid(k, k)
    u, v = u.ravel(), v.ravel()
    leds = [(r, c) for r in range(17, 21) for c in range(13, 18)]
    dC = np.array([c for _, c in leds], float)
    dR = np.array([r for r, _ in leds], float)
    p = [c0, r0, M[0, 0], M[0, 1], M[1, 0], M[1, 1], rho0, w]
    g, _ = edge.model_g(p, u, v, dC, dR)
    rng = np.random.default_rng(seed)
    A = amp * (1.0 + 0.05 * rng.standard_normal(len(dC)))
    Y = A[:, None] * g + rng.normal(0.0, noise, g.shape)
    return u, v, Y, dC, dR, p


# ------------------------------------------------------------------ tests ---
def test_edge_fit_recovers_known_R_BF(edge):
    """The headline estimator is unbiased on data it did not generate itself."""
    u, v, Y, dC, dR, p_true = synth(edge, R_BF=1.70, px_per_step=1550.0)
    b = edge.fit(u, v, Y, dC, dR, starts=[[15.0, 18.0, -1500.0, 0.0, 0.0,
                                           -1500.0, 2600.0, 40.0]])
    d = edge.derived(b.x)
    assert d["R_BF"] == pytest.approx(1.70, abs=0.02)
    assert d["px_per_step"] == pytest.approx(1550.0, rel=0.02)
    assert d["c0"] == pytest.approx(15.12, abs=0.02)
    assert d["r0"] == pytest.approx(18.22, abs=0.02)


def test_R_BF_is_free_of_the_pixel_scale(edge):
    """The central claim of J2: R_BF is a ratio of two lengths measured on the
    same pixel grid, so halving px_sample (doubling px per LED step) must not
    move it.  If this failed, R_BF would smuggle in px_sample and could not be
    combined with an independent magnification constraint."""
    got = []
    for pps in (900.0, 1800.0):
        u, v, Y, dC, dR, _ = synth(edge, R_BF=1.62, px_per_step=pps, seed=3)
        b = edge.fit(u, v, Y, dC, dR,
                     starts=[[15.0, 18.0, -pps * 0.9, 0.0, 0.0, -pps * 0.9,
                              1.5 * pps, 0.05 * pps]])
        got.append(edge.derived(b.x)["R_BF"])
    assert got[0] == pytest.approx(1.62, abs=0.03)
    assert got[1] == pytest.approx(1.62, abs=0.03)
    assert abs(got[0] - got[1]) < 0.03


@pytest.mark.xfail(strict=True, reason=(
    "The edge fit does not estimate the array rotation: from a start with M = "
    "diag(-pps, -pps) it returns rot_deg = 180.000 exactly, for an injected rotation of "
    "3 deg (truth -177) and also of 10 deg (truth -170). The reported rotation is the "
    "starting value, not a measurement, so J2's 180.00/179.87/180.00 deg on the real "
    "capture must not be read as a measured array rotation. R_BF is unaffected -- see "
    "test_R_BF_survives_an_unrecovered_rotation below -- and the "
    "--led-center-offset-mm sign convention does not depend on this fit "
    "(results/esferas_2026-07-08/geometria/18_sign_convention_checks.py derives it "
    "algebraically from led_array.py instead). NOTE the convention: derived()['rot_deg'] "
    "is the ABSOLUTE angle including the 180 deg flip that synth() builds in, so an "
    "injected rot_deg of 3 must be compared against -177, not against 3."))
def test_edge_fit_recovers_array_rotation(edge):
    u, v, Y, dC, dR, p_true = synth(edge, rot_deg=3.0, seed=5)
    b = edge.fit(u, v, Y, dC, dR, starts=[[15.0, 18.0, -1550.0, 0.0, 0.0,
                                           -1550.0, 2635.0, 31.0]])
    truth = edge.derived(p_true)["rot_deg"]
    assert truth == pytest.approx(-177.0, abs=0.01)
    assert edge.derived(b.x)["rot_deg"] == pytest.approx(truth, abs=0.5)


@pytest.mark.parametrize("rot_deg", [3.0, 10.0])
def test_R_BF_survives_an_unrecovered_rotation(edge, rot_deg):
    """R_BF = rho0 / sqrt(|det M|) is rotation-invariant by construction, so the
    headline number stays right even where the rotation above is not recovered.
    This is what lets J2 quote R_BF while disowning its own rotation output."""
    u, v, Y, dC, dR, _ = synth(edge, R_BF=1.70, rot_deg=rot_deg, seed=5)
    b = edge.fit(u, v, Y, dC, dR, starts=[[15.0, 18.0, -1550.0, 0.0, 0.0,
                                           -1550.0, 2635.0, 31.0]])
    assert edge.derived(b.x)["R_BF"] == pytest.approx(1.70, abs=0.02)


def test_half_fill_radius_matches_the_cutoff(edge):
    """The model-free cross-check must agree with the truth: a disc edge through
    the frame centre gives fill = 0.5, so the half-fill LED radius IS R_BF."""
    u, v, Y, dC, dR, _ = synth(edge, R_BF=1.70, px_per_step=1550.0, amp=230.0,
                               w_steps=0.01, seed=7)
    fill = (Y > edge.BRIGHT_HALF).mean(1)
    sel = np.stack([(dR - 11).astype(int), (dC - 9).astype(int)], 1)
    hf = edge.half_fill_radius(sel, fill, 18.22, 15.12)
    assert hf == pytest.approx(1.70, abs=0.06)


def test_edge_profile_is_half_at_the_cutoff(edge):
    """rho0 is defined as the HALF-max radius for both profile shapes; the two
    radius definitions in play (half-max vs outermost-lit) must not be mixed."""
    assert edge.profile(np.array([0.0]))[0] == pytest.approx(0.5, abs=1e-12)
    assert edge.profile(np.array([0.0]), kind="logistic")[0] == pytest.approx(0.5, abs=1e-12)
    assert edge.profile(np.array([-4.0]))[0] > 0.99
    assert edge.profile(np.array([4.0]))[0] < 0.01


def test_circle_fit_recovers_a_known_arc(circles):
    """Only a 24-degree arc is visible inside the sensor at the real radius, so
    the circle fit is tested on an arc, not on a full circle."""
    rng = np.random.default_rng(1)
    r, cx, cy = 2650.0, -300.0, 420.0
    th = np.linspace(np.radians(-12), np.radians(12), 600)
    x = cx + r * np.cos(th) + rng.normal(0, 1.5, th.size)
    y = cy + r * np.sin(th) + rng.normal(0, 1.5, th.size)
    fx, fy, fr, rms = circles.circle_fit(x, y)
    assert fr == pytest.approx(r, rel=0.05)
    assert rms < 4.0


def test_lattice_fit_recovers_M_and_centre(circles):
    M = np.array([[-1550.0, 80.0], [-80.0, -1550.0]])
    t = np.array([234.0, -117.0])
    C = np.array([13, 14, 15, 16, 17, 14, 15, 16], float)
    R = np.array([17, 17, 18, 18, 19, 20, 20, 19], float)
    cx = M[0, 0] * C + M[0, 1] * R + t[0]
    cy = M[1, 0] * C + M[1, 1] * R + t[1]
    Mf, tf, rms = circles.lattice_fit(C, R, cx, cy)
    assert rms < 1e-6
    assert np.allclose(Mf, M, rtol=1e-6, atol=1e-6)
    assert np.allclose(tf, t, atol=1e-6)


def test_edge_points_rejects_a_dark_frame(circles, monkeypatch):
    """The failure path: a frame with no bright region must return no contour
    rather than a spurious circle.  157 of the 169 LEDs are exactly this."""
    monkeypatch.setattr(circles, "frame",
                        lambda ch, r, c, subset="1ms":
                        np.full((circles.FRAME, circles.FRAME), 187, np.uint16))
    x, y, hi = circles.edge_points("red", 7, 6)
    assert x is None and y is None
    assert hi < 40.0
