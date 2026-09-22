"""config.py -- physical/geometric setup of the FPM microscope.

Values here come from the real lab setup (see references/bibliography.yaml
for the papers that ground the algorithm, and references/README.md for
how to cite them). Everything is a plain dataclass so a script can
override a field for a specific run without editing this file.
"""
from __future__ import annotations

from dataclasses import dataclass

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
    """

    grid_size: int  # e.g. 9 or 31; must be odd so there's a true center LED
    pitch_mm: float = 6.0
    z_distance_mm: float = 70.0  # array-to-sample distance; easy to retune
    index_base: int = 1
    row_index_base: int | None = None
    col_index_base: int | None = None

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


#: Named presets for the two objectives currently in the lab.
OBJECTIVES = {
    "current": ObjectiveConfig(na=0.07, magnification=2.5, name="current"),
    "future": ObjectiveConfig(na=0.10, magnification=2.0, name="future"),
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


def default_setup(channel: str, grid_size: int, objective: str = "current",
                   resolution_px: tuple[int, int] = (200, 200),
                   row_index_base: int | None = None,
                   col_index_base: int | None = None) -> SetupConfig:
    """Convenience builder for the lab's actual hardware, current values."""
    return SetupConfig(
        led_array=LEDArrayConfig(grid_size=grid_size, row_index_base=row_index_base,
                                  col_index_base=col_index_base),
        objective=OBJECTIVES[objective],
        sensor=SensorConfig(resolution_px=resolution_px),
        channel=channel,
    )
