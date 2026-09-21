"""tests/test_test_objects.py -- src/ptyco_full_simulator/test_objects.py
(Lena amplitude + Map phase). Skipped when the images (kept outside the
repo) aren't at PTYCO_DATA_SOURCE / the default path.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ptyco_full_simulator import test_objects  # noqa: E402

_DIR = os.environ.get("PTYCO_DATA_SOURCE", test_objects.DEFAULT_DATA_DIR)
pytestmark = pytest.mark.skipif(not os.path.exists(os.path.join(_DIR, "Lena_512.png")),
                                reason="Lena/Map images not available on this machine")


def test_lena_map_object_has_requested_shape_amplitude_and_phase_ranges():
    obj, phase = test_objects.lena_map_object((48, 64), phase_max_rad=0.5, min_amplitude=0.2)
    assert obj.shape == phase.shape == (48, 64)
    assert np.abs(obj).min() == pytest.approx(0.2, abs=1e-9)
    assert np.abs(obj).max() == pytest.approx(1.0, abs=1e-9)
    assert phase.min() == pytest.approx(0.0, abs=1e-9)
    assert phase.max() == pytest.approx(0.5, abs=1e-9)
    assert np.allclose(np.angle(obj), phase)  # phase < pi, so no wrapping
