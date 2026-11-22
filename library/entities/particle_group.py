# 3d particle group supporting cloud, toroidal asteroid belt, and nebula modes

import math
import random as py_random
from collections.abc import Sequence

from ..core.constants import (
    COLOR_NEBULA_MAGENTA,
    COLOR_PARTICLE_DUST,
)
from ..rendering.camera import Camera3D
from ..rendering.projection import (
    crisp_dot_radius,
    depth_shaded_color,
    normalize_color,
    normalize_vec3,
)
from ..rendering.renderer import ParticleRenderer
from .base import CelestialEntity, register_entity
from .random_region import RandomRegion


class ParticleGroup(CelestialEntity):
    # 3d particle ensemble rendered in cloud, belt, or volumetric nebula mode

    render_layer: int = 50

    def __init__(self) -> None:
        super().__init__()
        self.count: int = 360
        self.mass: float = 0.5
        self.total_mass: float = 0.0
        self.mode: str = "cloud"
        self._position: list[float] | RandomRegion = [0.0, 0.0, 0.0]
        self._center: list[float] = [640.0, 360.0, 0.0]
        self._velocity: list[float] = [0.0, 0.0, 0.0]
        self._color: list[int] = list(COLOR_PARTICLE_DUST)
        self._secondary_color: list[int] | None = None
        self.color_variation: float = 0.8
        self.spread: float = 1.0
        self.inner_radius: float = 355.0
        self.outer_radius: float = 405.0
        self.thickness: float = 28.0
        self.angular_speed: float = 0.002
        self._particles: list[list[float]] = []
        self._tones: list[float] = []
        self._phases: list[float] = []
        self._dot_sizes: list[float] = []
        self._nebula_pivot: list[float] = [640.0, 360.0, 0.0]

    @property
    def position(self) -> list[float] | RandomRegion:
        return self._position

    @position.setter
    def position(self, value: Sequence[float] | RandomRegion) -> None:
        # preserve random regions while normalizing plain 2d/3d vectors
        if isinstance(value, RandomRegion):
            self._position = value
        else:
            self._position = normalize_vec3(value)

    @property
    def center(self) -> list[float]:
        return self._center

    @center.setter
    def center(self, value: Sequence[float]) -> None:
        self._center = normalize_vec3(value)

    @property
    def velocity(self) -> list[float]:
        return self._velocity

    @velocity.setter
    def velocity(self, value: Sequence[float]) -> None:
        self._velocity = normalize_vec3(value)

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

    def _init_belt(self, total: int) -> None:
        # distribute particles across a 3d toroidal ring around center
        cx, cy, cz = self._center
        inner = float(self.inner_radius)
        outer = float(self.outer_radius)
        low_r, high_r = (inner, outer) if inner <= outer else (outer, inner)
        half_thick = max(0.0, float(self.thickness)) * 0.5
        two_pi = 2.0 * math.pi
        for _ in range(total):
            r = py_random.uniform(low_r, high_r)
            theta = py_random.uniform(0.0, two_pi)
            dy = py_random.uniform(-half_thick, half_thick)
            self._particles.append(
                [cx + r * math.cos(theta), cy + dy, cz + r * math.sin(theta)]
            )

    def _init_nebula(self, total: int, spread: float) -> None:
        # generate multi-lobed volumetric 3d cosmic filament clusters
        lobe_count = 5
        lobes: list[list[float]] = []
        if isinstance(self._position, RandomRegion):
            lo_x, lo_y, lo_z = self._position.low
            hi_x, hi_y, hi_z = self._position.high
            has_z_span = abs(hi_z - lo_z) > 1e-6
            z_lo = lo_z if has_z_span else lo_z - 140.0 * spread
            z_hi = hi_z if has_z_span else hi_z + 140.0 * spread
            self._nebula_pivot = [
                (lo_x + hi_x) * 0.5,
                (lo_y + hi_y) * 0.5,
                (z_lo + z_hi) * 0.5,
            ]
            span_x = max(10.0, hi_x - lo_x)
            span_y = max(10.0, hi_y - lo_y)
            span_z = max(10.0, z_hi - z_lo)
            for _ in range(lobe_count):
                lobes.append(
                    [
                        py_random.uniform(lo_x + span_x * 0.15, hi_x - span_x * 0.15),
                        py_random.uniform(lo_y + span_y * 0.15, hi_y - span_y * 0.15),
                        py_random.uniform(z_lo + span_z * 0.15, z_hi - span_z * 0.15),
                    ]
                )
            sig_x = span_x * 0.16 * spread
            sig_y = span_y * 0.16 * spread
            sig_z = span_z * 0.18 * spread
            for idx in range(total):
                lx, ly, lz = lobes[idx % lobe_count]
                px = min(hi_x, max(lo_x, py_random.gauss(lx, sig_x)))
                py = min(hi_y, max(lo_y, py_random.gauss(ly, sig_y)))
                pz = min(z_hi, max(z_lo, py_random.gauss(lz, sig_z)))
                self._particles.append([px, py, pz])
        else:
            cx, cy, cz = self._position
            self._nebula_pivot = [cx, cy, cz]
            radius = 95.0 * spread
            for _ in range(lobe_count):
                lobes.append(
                    [
                        cx + py_random.uniform(-radius, radius),
                        cy + py_random.uniform(-radius * 0.65, radius * 0.65),
                        cz + py_random.uniform(-radius, radius),
                    ]
                )
            sigma = 45.0 * spread
            for idx in range(total):
                lx, ly, lz = lobes[idx % lobe_count]
                self._particles.append(
                    [
                        py_random.gauss(lx, sigma),
                        py_random.gauss(ly, sigma * 0.75),
                        py_random.gauss(lz, sigma),
                    ]
                )

    def _init_cloud(self, total: int, spread: float) -> None:
        # spawn particles from random region bounds or gaussian cluster
        if isinstance(self._position, RandomRegion):
            has_z_span = abs(self._position.high[2] - self._position.low[2]) > 1e-6
            z_span = 120.0 * spread
            for _ in range(total):
                pt = self._position.sample_point()
                if not has_z_span:
                    pt[2] = py_random.uniform(-z_span, z_span)
                self._particles.append(pt)
        else:
            cx, cy, cz = self._position
            sigma = 25.0 * spread
            for _ in range(total):
                self._particles.append(
                    [
                        py_random.gauss(cx, sigma),
                        py_random.gauss(cy, sigma),
                        py_random.gauss(cz, sigma),
                    ]
                )

    def initialize(self) -> None:
        # initialize particle coordinates, tone weights, and shimmer phases
        total = max(0, int(self.count))
        spread = max(0.01, float(self.spread))
        mode = str(self.mode).strip().lower()
        self._particles = []
        if mode == "belt":
            self._init_belt(total)
        elif mode == "nebula":
            self._init_nebula(total, spread)
        else:
            self._init_cloud(total, spread)

        two_pi = 2.0 * math.pi
        self._tones = [py_random.random() for _ in range(len(self._particles))]
        self._phases = [
            py_random.uniform(0.0, two_pi) for _ in range(len(self._particles))
        ]
        self._dot_sizes = [
            py_random.uniform(0.85, 1.35) for _ in range(len(self._particles))
        ]
        self._initialized = True

    def _rotate_around_y(self, pivot: Sequence[float], angle: float) -> None:
        # rotate all particles around a 3d pivot about the vertical y axis
        if angle == 0.0:
            return
        px, _, pz = float(pivot[0]), float(pivot[1]), float(pivot[2])
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        for particle in self._particles:
            dx = particle[0] - px
            dz = particle[2] - pz
            particle[0] = px + dx * cos_a + dz * sin_a
            particle[2] = pz - dx * sin_a + dz * cos_a

    def update(self, dt: float, sim: object) -> None:
        if not self._initialized:
            self.initialize()
        dt_scale = float(getattr(sim, "dt_scale", 1.0))
        mode = str(self.mode).strip().lower()
        if mode == "belt":
            self._rotate_around_y(self._center, float(self.angular_speed) * dt_scale)
            return
        if mode == "nebula":
            self._rotate_around_y(
                self._nebula_pivot,
                float(self.angular_speed) * dt_scale,
            )
            phase_step = 0.025 * dt_scale
            for idx in range(len(self._phases)):
                self._phases[idx] += phase_step
            return

        vx = self._velocity[0] * dt_scale
        vy = self._velocity[1] * dt_scale
        vz = self._velocity[2] * dt_scale
        if vx == 0.0 and vy == 0.0 and vz == 0.0:
            return
        width = float(sim.width)
        height = float(sim.height)
        for particle in self._particles:
            particle[0] += vx
            particle[1] += vy
            particle[2] += vz
            if width > 0.0:
                if particle[0] > width:
                    particle[0] -= width
                elif particle[0] < 0.0:
                    particle[0] += width
            if height > 0.0:
                if particle[1] > height:
                    particle[1] -= height
                elif particle[1] < 0.0:
                    particle[1] += height
            if particle[2] > 320.0:
                particle[2] -= 640.0
            elif particle[2] < -320.0:
                particle[2] += 640.0

    def render(
        self,
        renderer: ParticleRenderer,
        camera: Camera3D,
        sim: object,
    ) -> None:
        if not self._initialized:
            self.initialize()
        mode = str(self.mode).strip().lower()
        base_rgb = normalize_color(self._color)
        if self._secondary_color is not None:
            rich_rgb = normalize_color(self._secondary_color)
        elif mode == "nebula":
            rich_rgb = COLOR_NEBULA_MAGENTA
        else:
            rich_rgb = (
                min(255, int(base_rgb[0] * 0.65 + 45)),
                min(255, int(base_rgb[1] * 0.72 + 40)),
                min(255, int(base_rgb[2] * 0.85 + 35)),
            )
        variation_strength = min(1.0, max(0.0, float(self.color_variation)))
        width = int(sim.width)
        height = int(sim.height)
        modifiers = sim.spatial_modifiers

        for idx, particle in enumerate(self._particles):
            world_pt = particle
            if modifiers:
                world_pt = camera.apply_spatial_modifiers(particle, modifiers)
            projected = camera.project_depth(world_pt, width, height)
            if projected is None:
                continue
            x_2d, y_2d, scale, z_cam = projected
            tone = self._tones[idx]
            if mode == "nebula":
                shimmer = 0.68 + 0.32 * math.sin(self._phases[idx])
                rgb = depth_shaded_color(
                    base_rgb,
                    rich_rgb,
                    tone * variation_strength,
                    scale,
                    0.95 * shimmer,
                )
                radius_2d = crisp_dot_radius(self._dot_sizes[idx] * 0.9, scale)
            elif mode == "belt":
                rgb = depth_shaded_color(
                    base_rgb,
                    rich_rgb,
                    tone * variation_strength,
                    scale,
                    0.88,
                )
                radius_2d = crisp_dot_radius(0.95, scale)
            else:
                rgb = depth_shaded_color(
                    base_rgb,
                    rich_rgb,
                    tone * variation_strength,
                    scale,
                    0.92,
                )
                radius_2d = crisp_dot_radius(self._dot_sizes[idx], scale)
            renderer.emit(z_cam, x_2d, y_2d, radius_2d, rgb, width, height)


def particle_group() -> ParticleGroup:
    # instantiate and auto-register a 3d particle group
    entity = ParticleGroup()
    register_entity(entity)
    return entity
