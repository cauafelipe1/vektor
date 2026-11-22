# tilted concentric 3d planetary ring system with optional division gap

import math
import random as py_random
from collections.abc import Sequence
from typing import TYPE_CHECKING

from ..core.constants import COLOR_RINGS_SANDSTONE
from ..rendering.camera import Camera3D
from ..rendering.projection import (
    crisp_dot_radius,
    depth_shaded_color,
    normalize_color,
    normalize_vec3,
    rotate_vec3,
)
from ..rendering.renderer import ParticleRenderer
from .base import CelestialEntity, register_entity

if TYPE_CHECKING:
    from .planet import Planet


class Rings(CelestialEntity):
    # tilted concentric 3d particle rings attachable to a planet

    render_layer: int = 35

    def __init__(self) -> None:
        super().__init__()
        self.inner_radius: float = 54.0
        self.outer_radius: float = 96.0
        self.gap_inner: float = 0.0
        self.gap_outer: float = 0.0
        self._tilt: list[float] = [0.42, 0.18, -0.08]
        self._color: list[int] = list(COLOR_RINGS_SANDSTONE)
        self._secondary_color: list[int] | None = None
        self.color_variation: float = 0.8
        self.particle_count: int = 450
        self._position: list[float] = [910.0, 360.0, 0.0]
        self.target: "Planet | None" = None
        self.spin_speed: float = 0.005
        self._spin_angle: float = 0.0
        self._polar_points: list[tuple[float, float]] = []
        self._tones: list[float] = []

    @property
    def tilt(self) -> list[float]:
        return self._tilt

    @tilt.setter
    def tilt(self, value: Sequence[float]) -> None:
        self._tilt = normalize_vec3(value)

    @property
    def position(self) -> list[float]:
        return self._position

    @position.setter
    def position(self, value: Sequence[float]) -> None:
        self._position = normalize_vec3(value)

    @property
    def color(self) -> list[int]:
        return self._color

    @color.setter
    def color(self, value: Sequence[float]) -> None:
        self._color = list(normalize_color(value))

    @property
    def secondary_color(self) -> list[int] | None:
        return self._secondary_color

    @secondary_color.setter
    def secondary_color(self, value: Sequence[float] | None) -> None:
        if value is None:
            self._secondary_color = None
        else:
            self._secondary_color = list(normalize_color(value))

    def _sample_radius(
        self,
        intervals: list[tuple[float, float]],
        total_width: float,
    ) -> float:
        # sample a radius uniformly across active ring intervals excluding any gap
        if len(intervals) == 1 or total_width <= 0.0:
            lo, hi = intervals[0]
            return py_random.uniform(lo, hi)
        pick = py_random.uniform(0.0, total_width)
        acc = 0.0
        for lo, hi in intervals:
            span = hi - lo
            if pick <= acc + span:
                return lo + (pick - acc)
            acc += span
        return intervals[-1][1]

    def initialize(self) -> None:
        # populate radial disc samples between inner and outer radii excluding gaps
        inner = float(self.inner_radius)
        outer = float(self.outer_radius)
        low_r, high_r = (inner, outer) if inner <= outer else (outer, inner)

        gap_lo = min(float(self.gap_inner), float(self.gap_outer))
        gap_hi = max(float(self.gap_inner), float(self.gap_outer))

        intervals: list[tuple[float, float]] = []
        if gap_hi > gap_lo and gap_lo < high_r and gap_hi > low_r:
            if gap_lo > low_r:
                intervals.append((low_r, min(high_r, gap_lo)))
            if gap_hi < high_r:
                intervals.append((max(low_r, gap_hi), high_r))
        if not intervals:
            intervals.append((low_r, high_r))

        total_width = sum(max(0.0, hi - lo) for lo, hi in intervals)
        radial_span = max(1e-6, high_r - low_r)
        two_pi = 2.0 * math.pi
        count = max(0, int(self.particle_count))

        self._polar_points = []
        self._tones = []
        for _ in range(count):
            radius = self._sample_radius(intervals, total_width)
            theta = py_random.uniform(0.0, two_pi)
            self._polar_points.append((radius, theta))
            radial_t = (radius - low_r) / radial_span
            tone = min(1.0, max(0.0, 0.65 * radial_t + 0.35 * py_random.random()))
            self._tones.append(tone)
        self._initialized = True

    def update(self, dt: float, sim: object) -> None:
        if not self._initialized:
            self.initialize()
        dt_scale = float(getattr(sim, "dt_scale", 1.0))
        step = float(self.spin_speed) * dt_scale
        self._spin_angle = (self._spin_angle + step) % (2.0 * math.pi)

    def render(
        self,
        renderer: ParticleRenderer,
        camera: Camera3D,
        sim: object,
    ) -> None:
        if not self._initialized:
            self.initialize()
        anchor = self.target.position if self.target is not None else self._position
        ax, ay, az = anchor
        rx, ry, rz = self._tilt
        base_rgb = normalize_color(self._color)
        if self._secondary_color is not None:
            rich_rgb = normalize_color(self._secondary_color)
        else:
            rich_rgb = (
                min(255, int(base_rgb[0] * 0.68 + 30)),
                min(255, int(base_rgb[1] * 0.68 + 30)),
                min(255, int(base_rgb[2] * 0.78 + 40)),
            )
        variation_strength = min(1.0, max(0.0, float(self.color_variation)))
        width = int(sim.width)
        height = int(sim.height)
        modifiers = sim.spatial_modifiers
        spin = self._spin_angle

        for idx, (radius, theta) in enumerate(self._polar_points):
            angle = theta + spin
            local = [radius * math.cos(angle), 0.0, radius * math.sin(angle)]
            tilted = rotate_vec3(local, ry, rx, rz)
            world_pt = [ax + tilted[0], ay + tilted[1], az + tilted[2]]
            if modifiers:
                world_pt = camera.apply_spatial_modifiers(world_pt, modifiers)
            projected = camera.project_depth(world_pt, width, height)
            if projected is None:
                continue
            x_2d, y_2d, scale, z_cam = projected
            rgb = depth_shaded_color(
                base_rgb,
                rich_rgb,
                self._tones[idx] * variation_strength,
                scale,
                0.96,
            )
            radius_2d = crisp_dot_radius(0.95, scale)
            renderer.emit(z_cam, x_2d, y_2d, radius_2d, rgb, width, height)


def rings() -> Rings:
    # instantiate and auto-register a 3d planetary ring system
    entity = Rings()
    register_entity(entity)
    return entity
