# shared base protocols and spherical point-cloud helpers for celestial entities

import math
import random as py_random
from collections.abc import Sequence

import pygame

from ..rendering.camera import Camera3D
from ..rendering.projection import (
    crisp_dot_radius,
    depth_shaded_color,
    generate_sphere_angles,
    normalize_color,
    normalize_vec3,
    spherical_to_cartesian,
)
from ..rendering.renderer import ParticleRenderer


def register_entity(entity: "CelestialEntity") -> None:
    # register a newly created entity with the active simulation
    from ..core.simulation import Simulation

    Simulation.get_active().register(entity)


class CelestialEntity:
    # uniform lifecycle protocol shared by all 3d simulation entities

    render_layer: int = 30

    def __init__(self) -> None:
        self._initialized: bool = False

    def initialize(self) -> None:
        # prepare internal point clouds after dsl configuration finishes
        self._initialized = True

    def update(self, dt: float, sim: object) -> None:
        # advance entity physics and animations by one simulation step
        if not self._initialized:
            self.initialize()

    def render(
        self,
        renderer: ParticleRenderer,
        camera: Camera3D,
        sim: object,
    ) -> None:
        # emit projected 3d particles into the depth-sorted painter renderer
        if not self._initialized:
            self.initialize()

    def draw(self, screen: pygame.Surface, camera: Camera3D, sim: object) -> None:
        # compatibility helper rendering a single entity through a local painter queue
        renderer = ParticleRenderer()
        self.render(renderer, camera, sim)
        renderer.flush(screen)


class PointCloudSphere(CelestialEntity):
    # shared 3d spherical point-cloud base for stars, planets, and satellites

    def __init__(
        self,
        mass: float,
        radius: float,
        position: Sequence[float],
        velocity: Sequence[float],
        color: Sequence[int],
        particle_count: int,
        spin_speed: float,
        luminosity: float = 1.0,
        secondary_color: Sequence[int] | None = None,
        color_variation: float = 0.8,
    ) -> None:
        super().__init__()
        self.mass: float = float(mass)
        self.radius: float = float(radius)
        self._position: list[float] = normalize_vec3(position)
        self._velocity: list[float] = normalize_vec3(velocity)
        self._color: list[int] = list(normalize_color(color))
        self._secondary_color: list[int] | None = (
            None if secondary_color is None else list(normalize_color(secondary_color))
        )
        self.color_variation: float = float(color_variation)
        self.particle_count: int = int(particle_count)
        self.spin_speed: float = float(spin_speed)
        self.luminosity: float = float(luminosity)
        self._local_points: list[list[float]] = []
        self._tones: list[float] = []
        self._dot_sizes: list[float] = []

    @property
    def position(self) -> list[float]:
        return self._position

    @position.setter
    def position(self, value: Sequence[float]) -> None:
        self._position = normalize_vec3(value)

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

    def _derive_rich_color(
        self,
        base_rgb: tuple[int, int, int],
    ) -> tuple[int, int, int]:
        # derive a secondary shade when no explicit secondary color is configured
        if self._secondary_color is not None:
            return normalize_color(self._secondary_color)
        return (
            min(255, int(base_rgb[0] * 0.62 + 48)),
            min(255, int(base_rgb[1] * 0.72 + 42)),
            min(255, int(base_rgb[2] * 0.85 + 36)),
        )

    def initialize(self) -> None:
        # generate spherical surface points and stochastic shading weights
        angles = generate_sphere_angles(int(self.particle_count))
        radius = float(self.radius)
        self._local_points = [
            spherical_to_cartesian(radius, theta, phi) for theta, phi in angles
        ]
        self._tones = [py_random.random() for _ in range(len(self._local_points))]
        self._dot_sizes = [
            py_random.uniform(0.95, 1.45) for _ in range(len(self._local_points))
        ]
        self._initialized = True

    def _spin_points(self, dt_scale: float = 1.0) -> None:
        # rotate spherical surface points around the local y axis
        angle = float(self.spin_speed) * float(dt_scale)
        if angle == 0.0:
            return
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        for point in self._local_points:
            x, z = point[0], point[2]
            point[0] = x * cos_a + z * sin_a
            point[2] = -x * sin_a + z * cos_a

    def _render_points(
        self,
        renderer: ParticleRenderer,
        camera: Camera3D,
        sim: object,
        polar_caps: bool = False,
    ) -> None:
        # project and emit depth-sorted surface particles with multi-tone shading
        px, py, pz = self._position
        base_rgb = normalize_color(self._color)
        rich_rgb = self._derive_rich_color(base_rgb)
        has_explicit_secondary = self._secondary_color is not None
        variation_strength = min(1.0, max(0.0, float(self.color_variation)))
        radius = max(1e-6, float(self.radius))
        width = int(sim.width)
        height = int(sim.height)
        modifiers = sim.spatial_modifiers
        lum = float(self.luminosity)
        polar_rgb = (232, 244, 255)

        for idx, (lx, ly, lz) in enumerate(self._local_points):
            world_pt = [px + lx, py + ly, pz + lz]
            if modifiers:
                world_pt = camera.apply_spatial_modifiers(world_pt, modifiers)
            projected = camera.project_depth(world_pt, width, height)
            if projected is None:
                continue
            x_2d, y_2d, scale, z_cam = projected
            tone = self._tones[idx]
            lat_ratio = abs(ly) / radius
            if polar_caps and lat_ratio > 0.74:
                cap_blend = min(1.0, (lat_ratio - 0.74) / 0.22)
                rgb = depth_shaded_color(
                    base_rgb,
                    polar_rgb,
                    cap_blend * (0.65 + 0.35 * tone),
                    scale,
                    lum * 1.06,
                )
            else:
                if has_explicit_secondary:
                    band = 0.5 + 0.5 * math.sin((ly / radius) * 5.0)
                    mix_weight = (0.6 * band + 0.4 * tone) * variation_strength
                else:
                    mix_weight = tone * variation_strength
                rgb = depth_shaded_color(base_rgb, rich_rgb, mix_weight, scale, lum)
            radius_2d = crisp_dot_radius(self._dot_sizes[idx], scale)
            renderer.emit(z_cam, x_2d, y_2d, radius_2d, rgb, width, height)
