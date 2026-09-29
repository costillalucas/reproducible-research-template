"""Acceptance gate for the joint 3-colour reconstruction job (docs/plan_reconstruccion_conjunta_2026-09-29.md).

It checks that the deliverables EXIST and are well-formed, not that the method succeeds: a clean negative result
(criteria that fail, with the reason written down) is an acceptable outcome. Hash-pinned: the job cannot edit it.
"""
import importlib.util
import json
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "results", "conjunta_2026-09-30")


def _joint():
    p = os.path.join(D, "joint.py")
    assert os.path.exists(p), "results/conjunta_2026-09-30/joint.py missing"
    s = importlib.util.spec_from_file_location("joint", p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def test_gradient_matches_finite_differences():
    err = _joint().gradcheck(seed=0)
    assert err < 1e-5, f"relative gradient error {err}"


def _res():
    p = os.path.join(D, "resultados.json")
    assert os.path.exists(p), "results/conjunta_2026-09-30/resultados.json missing"
    return json.load(open(p))


@pytest.mark.parametrize("key", ["S1", "S2", "S3"])
def test_simulation_criteria_reported(key):
    c = _res()["sim"][key]
    assert isinstance(c["valor"], (int, float)) and isinstance(c["referencia"], (int, float)) and isinstance(c["pasa"], bool)


def test_dispersion_recovery_reported():
    r = _res()["sim"]["B_ajustado"]
    assert isinstance(r, (int, float))


def test_real_data_reported_or_skipped_with_reason():
    r = _res()["real"]
    if "omitido" in r:
        assert isinstance(r["omitido"], str) and len(r["omitido"]) > 20
    else:
        for key in ("R1", "R2"):
            assert isinstance(r[key]["pasa"], bool)
        assert r["variante_elegida"] in {"A1_D1", "A1_D2", "A2_D1", "A2_D2"}


def test_report_exists():
    p = os.path.join(D, "INFORME.md")
    assert os.path.exists(p) and os.path.getsize(p) > 1500
