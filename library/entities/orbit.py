# 3d tilted elliptical orbital trajectory with optional dotted trail

import math
from collections.abc import Sequence

from ..core.constants import COLOR_ORBIT_BLUE
from ..rendering.camera import Camera3D
from ..rendering.projection import (
    depth_shaded_color,
    normalize_color,
    normalize_vec3,
    rotate_point_x,
)
from ..rendering.renderer import ParticleRenderer
from .base import CelestialEntity, register_entity


class Orbit(CelestialEntity):
    # 3d tilted elliptical orbital trajectory with depth-sorted trail markers

    render_layer: int = 10

    def __init__(self) -> None:
        super().__init__()
        self._center: list[float] = [640.0, 360.0, 0.0]
        self.radius: float = 270.0
        self.eccentricity: float = 0.0
        self.inclination: float = 0.1
        self.speed: float = 0.008
        self._color: list[int] = list(COLOR_ORBIT_BLUE)
        self.show_trail: bool = True
        self.angle: float = 0.0
        self._last_step_frame: int = -1

    @property
    def center(self) -> list[float]:
        return self._center

    @center.setter
    def center(self, value: Sequence[float]) -> None:
        self._center = normalize_vec3(value)

    @property
    def color(self) -> list[int]:
        return self._color

    @color.setter
    def color(self, value: Sequence[float]) -> None:
        self._color = list(normalize_color(value))

    def step_frame(self, frame_index: int, dt_scale: float = 1.0) -> None:
        # advance orbital phase at most once per simulation frame
        if frame_index != self._last_step_frame:
            step = float(self.speed) * float(dt_scale)
            self.angle = (self.angle + step) % (2.0 * math.pi)
            self._last_step_frame = frame_index

    def sample_at(
        self,
        angle: float,
        center_override: Sequence[float] | None = None,
    ) -> list[float]:
        # evaluate a 3d point along the tilted elliptical orbit
        cx, cy, cz = normalize_vec3(
            self._center if center_override is None else center_override
        )
        ecc = min(0.95, max(0.0, float(self.eccentricity)))
        semi_major = float(self.radius)
        semi_minor = semi_major * math.sqrt(max(0.05, 1.0 - ecc * ecc))
        local = [semi_major * math.cos(angle), 0.0, semi_minor * math.sin(angle)]
        tilted = rotate_point_x(local, float(self.inclination))
        return [cx + tilted[0], cy + tilted[1], cz + tilted[2]]

    def update(self, dt: float, sim: object) -> None:
        if not self._initialized:
            self.initialize()
        dt_scale = float(getattr(sim, "dt_scale", 1.0))
        self.step_frame(int(getattr(sim, "frame_count", 0)), dt_scale)

    def render(
        self,
        renderer: ParticleRenderer,
        camera: Camera3D,
        sim: object,
    ) -> None:
        if not self._initialized:
            self.initialize()
        if not self.show_trail:
            return
        base_rgb = normalize_color(self._color)
        width = int(sim.width)
        height = int(sim.height)
        modifiers = sim.spatial_modifiers
        steps = 128
        step_angle = (2.0 * math.pi) / steps
        for idx in range(steps):
            world_pt = self.sample_at(idx * step_angle)
            if modifiers:
                world_pt = camera.apply_spatial_modifiers(world_pt, modifiers)
            projected = camera.project_depth(world_pt, width, height)
            if projected is None:
                continue
            x_2d, y_2d, scale, z_cam = projected
            rgb = depth_shaded_color(base_rgb, base_rgb, 0.0, scale, 0.65)
            renderer.emit(z_cam, x_2d, y_2d, 1, rgb, width, height)


def orbit() -> Orbit:
    # instantiate and auto-register a 3d elliptical orbit
    entity = Orbit()
    register_entity(entity)
    return entity
