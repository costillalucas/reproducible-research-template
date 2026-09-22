"""tests/test_real_capture_index_base.py -- row/col index-base fix for
real lab captures whose row and column numbering don't share one base
(e.g. rows 13-21, columns 11-19 for the same 9x9 on-axis-centered scan),
and for the `fila<R>_col<C>.tiff` filename spelling seen on the lab's own
2025-12-12 capture (this project's docstrings/tests otherwise assume
`fila<R>_columna<C>.tiff`).

Motivating real case (see docs/roadmap_agentic_multispectral_pipeline.md):
on that capture, the on-axis LED (row=17, col=15) was confirmed
independently via the lab's own per-LED exposure-time metadata -- the
shortest-exposure LEDs (brightest, closest to on-axis, least angular
falloff) are exactly row in {16,17,18}, col==15, centered at (17, 15).
`LEDArrayConfig.center_index` (a single shared value) can't express that
row base (13) and col base (11) differ by 2 while both still center on
(17, 15); `center_row`/`center_col` can.
"""
import os
import sys

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ptyco_full_simulator import config, io_utils, led_array  # noqa: E402


def _write_tiff(path, value=1.0, shape=(4, 4)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.full(shape, value, dtype=np.float32), mode="F").save(path)


# ---------------------------------------------------------------------------
# config.LEDArrayConfig: center_row/center_col vs. the old shared center_index
# ---------------------------------------------------------------------------

def test_symmetric_index_base_matches_old_center_index_behavior():
    """Only `index_base` set (no row/col override) -- center_row and
    center_col must both equal the pre-existing center_index, so every
    caller that never heard of row/col bases keeps working unchanged."""
    cfg = config.LEDArrayConfig(grid_size=9, index_base=1)
    assert cfg.center_row == cfg.center_index
    assert cfg.center_col == cfg.center_index
    assert cfg.row_base == cfg.col_base == 1


def test_asymmetric_index_base_centers_on_the_confirmed_real_on_axis_led():
    """grid_size=9, row_index_base=13, col_index_base=11 -- the real
    2025-12-12 capture's shape. The on-axis LED must land at (17, 15),
    independently confirmed via the lab's exposure-time metadata."""
    cfg = config.LEDArrayConfig(grid_size=9, row_index_base=13, col_index_base=11)
    assert cfg.center_row == 17.0
    assert cfg.center_col == 15.0
    dx, dy = led_array.led_position_mm(17, 15, cfg)
    assert dx == 0.0
    assert dy == 0.0


def test_row_index_base_alone_falls_back_to_index_base_for_columns():
    cfg = config.LEDArrayConfig(grid_size=9, index_base=1, row_index_base=13)
    assert cfg.row_base == 13
    assert cfg.col_base == 1  # falls back to index_base, not row_index_base
    assert cfg.center_row == 17.0
    assert cfg.center_col == 5.0


def test_default_setup_propagates_row_col_index_base():
    setup = config.default_setup(
        channel="green", grid_size=9, row_index_base=13, col_index_base=11,
    )
    assert setup.led_array.row_base == 13
    assert setup.led_array.col_base == 11
    assert setup.led_array.center_row == 17.0
    assert setup.led_array.center_col == 15.0


# ---------------------------------------------------------------------------
# led_array.build_led_grid / max_illumination_na with asymmetric bases
# ---------------------------------------------------------------------------

def test_build_led_grid_spans_the_asymmetric_row_col_ranges():
    cfg = config.LEDArrayConfig(grid_size=9, row_index_base=13, col_index_base=11)
    grid = led_array.build_led_grid(cfg, wavelength_um=0.53)

    assert len(grid) == 81
    rows = {e["row"] for e in grid}
    cols = {e["col"] for e in grid}
    assert rows == set(range(13, 22))
    assert cols == set(range(11, 20))

    # sorted by radial distance from the on-axis LED, so it comes first
    assert grid[0]["row"] == 17
    assert grid[0]["col"] == 15
    assert grid[0]["radial_mm"] == 0.0
    assert all(grid[i]["radial_mm"] <= grid[i + 1]["radial_mm"] for i in range(len(grid) - 1))


def test_max_illumination_na_uses_the_asymmetric_corner():
    """Regression guard: max_illumination_na used to compute a single
    `hi = index_base + grid_size - 1` and reuse it for both row and col,
    which for asymmetric bases would point at the wrong (non-existent)
    corner LED. It must now use (row_base + grid_size - 1, col_base +
    grid_size - 1)."""
    cfg_sym = config.LEDArrayConfig(grid_size=9, index_base=5)
    cfg_asym = config.LEDArrayConfig(grid_size=9, row_index_base=13, col_index_base=11)
    # same physical corner offset from center in both cases (row/col span
    # the same 9-wide range relative to their own base), so the resulting
    # max NA must be identical -- only the labeling of rows/cols changed.
    assert led_array.max_illumination_na(cfg_sym) == led_array.max_illumination_na(cfg_asym)


# ---------------------------------------------------------------------------
# io_utils.load_real_lr_stack: "col" vs "columna" filenames + asymmetric bases
# ---------------------------------------------------------------------------

def test_load_real_lr_stack_finds_columna_spelling(tmp_path):
    subdir = tmp_path / "green" / "3x3_recortada_4"
    for row in range(1, 4):
        for col in range(1, 4):
            _write_tiff(subdir / f"fila{row}_columna{col}.tiff", value=row * 10 + col)

    stack = io_utils.load_real_lr_stack(tmp_path, "green", grid_size=3, crop=4)
    assert len(stack) == 9
    assert stack[(1, 1)][0, 0] == 11.0


def test_load_real_lr_stack_finds_col_spelling(tmp_path):
    """The real lab's 2025-12-12 capture spells it `col`, not `columna`."""
    subdir = tmp_path / "green" / "3x3_recortada_4"
    for row in range(1, 4):
        for col in range(1, 4):
            _write_tiff(subdir / f"fila{row}_col{col}.tiff", value=row * 10 + col)

    stack = io_utils.load_real_lr_stack(tmp_path, "green", grid_size=3, crop=4)
    assert len(stack) == 9
    assert stack[(2, 3)][0, 0] == 23.0


def test_load_real_lr_stack_prefers_columna_when_both_exist(tmp_path):
    subdir = tmp_path / "green" / "3x3_recortada_4"
    for row in range(1, 4):
        for col in range(1, 4):
            _write_tiff(subdir / f"fila{row}_columna{col}.tiff", value=1.0)
            _write_tiff(subdir / f"fila{row}_col{col}.tiff", value=2.0)

    stack = io_utils.load_real_lr_stack(tmp_path, "green", grid_size=3, crop=4)
    assert stack[(1, 1)][0, 0] == 1.0


def test_load_real_lr_stack_with_asymmetric_row_col_bases(tmp_path):
    """Rows 13-21, cols 11-19 -- the real capture's own numbering."""
    subdir = tmp_path / "red" / "9x9_recortada_4"
    for row in range(13, 22):
        for col in range(11, 20):
            _write_tiff(subdir / f"fila{row}_col{col}.tiff", value=row * 100 + col)

    stack = io_utils.load_real_lr_stack(
        tmp_path, "red", grid_size=9, crop=4, row_index_base=13, col_index_base=11,
    )
    assert len(stack) == 81
    assert set(r for r, c in stack) == set(range(13, 22))
    assert set(c for r, c in stack) == set(range(11, 20))
    assert stack[(17, 15)][0, 0] == 1715.0


def test_load_real_lr_stack_asymmetric_bases_miss_with_wrong_symmetric_base(tmp_path):
    """Sanity check that the fix is actually load-bearing: without passing
    row/col bases, a single shared index_base=1 finds nothing under the
    real capture's 13-21 / 11-19 layout."""
    subdir = tmp_path / "red" / "9x9_recortada_4"
    for row in range(13, 22):
        for col in range(11, 20):
            _write_tiff(subdir / f"fila{row}_col{col}.tiff", value=1.0)

    with pytest.raises(FileNotFoundError):
        io_utils.load_real_lr_stack(tmp_path, "red", grid_size=9, crop=4, index_base=1)


# ---------------------------------------------------------------------------
# End-to-end regression: the exact real-world shape round-trips correctly
# ---------------------------------------------------------------------------

def test_real_world_shape_round_trips_from_default_setup_to_led_grid(tmp_path):
    """grid_size=9, row_index_base=13, col_index_base=11 (the real
    2025-12-12 capture) round-tripped through default_setup ->
    LEDArrayConfig -> build_led_grid must center on (17, 15), the on-axis
    LED independently confirmed via the lab's own exposure-time metadata.
    """
    setup = config.default_setup(
        channel="green", grid_size=9, row_index_base=13, col_index_base=11,
    )
    grid = led_array.build_led_grid(setup.led_array, setup.wavelength_um)
    on_axis = grid[0]
    assert (on_axis["row"], on_axis["col"]) == (17, 15)
    assert on_axis["radial_mm"] == 0.0
    assert len(grid) == 81
