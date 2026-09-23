"""config.py -- physical/geometric setup of the FPM microscope.

Values here come from the real lab setup (see references/bibliography.yaml
for the papers that ground the algorithm, and references/README.md for
how to cite them). Everything is a plain dataclass so a script can
override a field for a specific run without editing this file.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

#: nm, one entry per LED color. The array is a sequential-RGB LED grid:
#: each grid position is captured once per color, one channel reconstructed
#: at a time for now (see notebook.md -- combining all 3 channels into one
#: solid reconstruction is a later goal, not implemented yet).
CHANNEL_WAVELENGTH_NM = {
    "red": 630.0,
    "green": 530.0,
    "blue": 470.0,
}


@dataclass(frozen=True)
class LEDArrayConfig:
    """Geometry of the LED illumination array.

    Rows/columns are 1-indexed, matching the lab's own filaR_columnaC
    convention. The array is square (grid_size x grid_size) and centered
    on the optical axis: for odd grid_size, the center LED is exactly
    at row = col = (grid_size + 1) / 2 -- in this config's own index_base.

    Rows and columns don't have to share the same starting number: the
    lab's own numbering can put e.g. rows 13-21 and columns 11-19 for the
    same 9x9 on-axis-centered scan (confirmed on the 2025-12-12 capture by
    cross-referencing the shortest-exposure LEDs, which are the brightest
    because they're closest to the optical axis). Pass `row_index_base`/
    `col_index_base` for that case; either left as None falls back to the
    shared `index_base` (the common, symmetric case).

    `z_distance_mm` defaults to 70.0, the simulator's nominal geometry that
    every synthetic result recorded so far uses. The real lab array sits at
    REAL_CAPTURE_Z_DISTANCE_MM (76 mm, confirmed by the user 2026-09-23);
    the real-data entry points default to that instead.

    `center_offset_mm = (dx, dy)` is where the array's nominal center LED
    (`center_row`, `center_col`) actually sits relative to the optical
    axis, in mm: dx along columns (x), dy along rows (y), same axes and
    signs as `led_array.led_position_mm`. Default (0, 0) is the perfectly
    aligned array; the lab isn't sure theirs is (see roadmap 6.8).
    """

    grid_size: int  # e.g. 9 or 31; must be odd so there's a true center LED
    pitch_mm: float = 6.0
    z_distance_mm: float = 70.0  # array-to-sample distance; easy to retune
    index_base: int = 1
    row_index_base: int | None = None
    col_index_base: int | None = None
    center_offset_mm: tuple[float, float] = (0.0, 0.0)

    def __post_init__(self):
        if self.grid_size % 2 == 0:
            raise ValueError(
                f"grid_size must be odd so a center LED exists, got {self.grid_size}"
            )

    @property
    def row_base(self) -> int:
        return self.index_base if self.row_index_base is None else self.row_index_base

    @property
    def col_base(self) -> int:
        return self.index_base if self.col_index_base is None else self.col_index_base

    @property
    def center_index(self) -> float:
        """Row/column of the on-axis LED, in this config's own index_base.
        Only meaningful when row and col share one index_base -- use
        `center_row`/`center_col` otherwise."""
        return self.index_base + (self.grid_size - 1) / 2.0

    @property
    def center_row(self) -> float:
        return self.row_base + (self.grid_size - 1) / 2.0

    @property
    def center_col(self) -> float:
        return self.col_base + (self.grid_size - 1) / 2.0


@dataclass(frozen=True)
class ObjectiveConfig:
    """One objective/imaging-path preset: numerical aperture + magnification."""

    na: float
    magnification: float
    name: str = ""


_OBJ_2X_NA010 = ObjectiveConfig(na=0.10, magnification=2.0, name="2x_na010")
_OBJ_2_5X_NA007 = ObjectiveConfig(na=0.07, magnification=2.5, name="2_5x_na007")

#: mm, array-to-sample distance of the real lab setup (confirmed by the
#: user 2026-09-23; LEDArrayConfig's own default, 70 mm, is the simulator's
#: nominal geometry and stays pinned for synthetic reproducibility).
REAL_CAPTURE_Z_DISTANCE_MM = 76.0

#: Default objective preset: the one the lab's real captures are taken
#: with (confirmed by the user 2026-09-23 for the 2025-12-12 capture).
DEFAULT_OBJECTIVE = "2x_na010"

#: Named presets for the two objectives in the lab, keyed by what they are.
#:
#: "current" and "future" are DEPRECATED aliases kept only so existing
#: scripts / result metadata / CLI invocations keep working:
#: "current" -> "2_5x_na007", "future" -> "2x_na010". They were misleading:
#: the real 2025-12-12 capture was taken with the 2x/0.10 ("future")
#: objective, but "current" (2.5x/0.07) was the default, so every real-data
#: run before 2026-09-23 silently used the wrong magnification AND NA.
#: Synthetic results recorded before then used "current" == "2_5x_na007"
#: and pin it explicitly so their numbers don't change.
OBJECTIVES = {
    "2x_na010": _OBJ_2X_NA010,
    "2_5x_na007": _OBJ_2_5X_NA007,
    "current": _OBJ_2_5X_NA007,  # deprecated alias
    "future": _OBJ_2X_NA010,  # deprecated alias
}


@dataclass(frozen=True)
class SensorConfig:
    pixel_size_um: float = 3.2
    # Raw capture is 1120x1120; often cropped to 400x400 or 200x200 for
    # memory/speed while testing -- pass the actual (h, w) you captured.
    resolution_px: tuple[int, int] = (1120, 1120)


@dataclass(frozen=True)
class SetupConfig:
    """Everything the forward model / reconstruction needs for one run."""

    led_array: LEDArrayConfig
    objective: ObjectiveConfig
    sensor: SensorConfig
    channel: str  # one of CHANNEL_WAVELENGTH_NM's keys

    @property
    def wavelength_nm(self) -> float:
        return CHANNEL_WAVELENGTH_NM[self.channel]

    @property
    def wavelength_um(self) -> float:
        return self.wavelength_nm / 1000.0

    @property
    def lr_pixel_size_um(self) -> float:
        """Camera pixel size projected back onto the sample plane."""
        return self.sensor.pixel_size_um / self.objective.magnification


def default_setup(channel: str, grid_size: int, objective: str = DEFAULT_OBJECTIVE,
                   resolution_px: tuple[int, int] = (200, 200),
                   row_index_base: int | None = None,
                   col_index_base: int | None = None,
                   z_distance_mm: float | None = None,
                   led_center_offset_mm: tuple[float, float] = (0.0, 0.0),
                   na: float | None = None,
                   magnification: float | None = None) -> SetupConfig:
    """Convenience builder for the lab's actual hardware, current values.

    `objective` defaults to DEFAULT_OBJECTIVE ("2x_na010", the one real
    captures use); synthetic experiments that must reproduce numbers
    recorded before 2026-09-23 pass "2_5x_na007" explicitly.

    `z_distance_mm=None` keeps LEDArrayConfig's nominal 70 mm (what every
    synthetic caller relies on); real-data entry points pass
    REAL_CAPTURE_Z_DISTANCE_MM. `na` / `magnification`, if given, override
    the preset's value (e.g. to try a measured effective 1.83x / NA 0.11
    without inventing a preset); the objective's name then gets a
    "+override" suffix so it can't be mistaken for the plain preset.
    """
    led_kwargs = {} if z_distance_mm is None else {"z_distance_mm": float(z_distance_mm)}
    objective_cfg = OBJECTIVES[objective]
    if na is not None or magnification is not None:
        objective_cfg = replace(
            objective_cfg,
            na=objective_cfg.na if na is None else float(na),
            magnification=objective_cfg.magnification if magnification is None else float(magnification),
            name=f"{objective}+override",
        )
    return SetupConfig(
        led_array=LEDArrayConfig(grid_size=grid_size, row_index_base=row_index_base,
                                  col_index_base=col_index_base,
                                  center_offset_mm=(float(led_center_offset_mm[0]),
                                                    float(led_center_offset_mm[1])),
                                  **led_kwargs),
        objective=objective_cfg,
        sensor=SensorConfig(resolution_px=resolution_px),
        channel=channel,
    )


def setup_geometry_summary(setup: SetupConfig) -> dict:
    """The effective optical/LED geometry a run actually used, as plain
    JSON-able values -- written into each real-data pipeline's metrics
    so a result can't be separated from the geometry that produced it.
    """
    return {
        "na": setup.objective.na,
        "magnification": setup.objective.magnification,
        "objective_name": setup.objective.name,
        "lr_pixel_um": setup.lr_pixel_size_um,
        "z_distance_mm": setup.led_array.z_distance_mm,
        "pitch_mm": setup.led_array.pitch_mm,
        "led_center_offset_mm": list(setup.led_array.center_offset_mm),
    }
