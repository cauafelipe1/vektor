# luminous 3d point-cloud star with multi-tone surface turbulence and corona

import math
import random as py_random

from ..core.constants import (
    COLOR_STAR_AMBER,
    COLOR_STAR_CORE,
    COLOR_STAR_EMBER,
)
from ..rendering.camera import Camera3D
from ..rendering.projection import (
    crisp_dot_radius,
    depth_shaded_color,
    generate_sphere_angles,
    normalize_color,
    spherical_to_cartesian,
)
from ..rendering.renderer import ParticleRenderer
from .base import PointCloudSphere, register_entity


class Star(PointCloudSphere):
    # luminous 3d point-cloud star with incandescent shimmer and outer corona

    render_layer: int = 20

    def __init__(self) -> None:
        super().__init__(
            mass=1.989e30,
            radius=68.0,
            position=[640.0, 360.0, 0.0],
            velocity=[0.0, 0.0, 0.0],
            color=COLOR_STAR_AMBER,
            particle_count=750,
            spin_speed=0.0,
            luminosity=1.2,
            secondary_color=None,
            color_variation=0.8,
        )
        self.corona_count: int = 110
        self.turbulence: float = 0.007
        self._angles: list[list[float]] = []
        self._drifts: list[tuple[float, float]] = []
        self._surface_tones: list[float] = []
        self._surface_dots: list[float] = []
        self._corona_angles: list[list[float]] = []
        self._corona_radii: list[float] = []
        self._corona_drifts: list[tuple[float, float]] = []
        self._corona_tones: list[float] = []

    def initialize(self) -> None:
        # sample turbulent surface angles and outer corona halo particles
        pairs = generate_sphere_angles(int(self.particle_count))
        self._angles = [[theta, phi] for theta, phi in pairs]
        self._drifts = [
            (py_random.uniform(-1.0, 1.0), py_random.uniform(-1.0, 1.0))
            for _ in range(len(self._angles))
        ]
        self._surface_tones = [py_random.random() for _ in range(len(self._angles))]
        self._surface_dots = [
            py_random.uniform(1.0, 1.5) for _ in range(len(self._angles))
        ]

        corona_pairs = generate_sphere_angles(max(0, int(self.corona_count)))
        self._corona_angles = [[theta, phi] for theta, phi in corona_pairs]
        self._corona_radii = [
            py_random.uniform(1.04, 1.25) for _ in range(len(self._corona_angles))
        ]
        self._corona_drifts = [
            (py_random.uniform(-0.6, 0.6), py_random.uniform(-0.6, 0.6))
            for _ in range(len(self._corona_angles))
        ]
        self._corona_tones = [
            py_random.random() for _ in range(len(self._corona_angles))
        ]
        self._initialized = True

    def _step_angle_pool(
        self,
        angles: list[list[float]],
        drifts: list[tuple[float, float]],
        step_size: float,
    ) -> None:
        # advance spherical particle angles smoothly while bouncing off poles
        two_pi = 2.0 * math.pi
        phi_min = 0.02
        phi_max = math.pi - 0.02
        for idx, pair in enumerate(angles):
            dtheta, dphi = drifts[idx]
            pair[0] = (pair[0] + dtheta * step_size) % two_pi
            next_phi = pair[1] + dphi * step_size
            if next_phi < phi_min or next_phi > phi_max:
                drifts[idx] = (dtheta, -dphi)
                next_phi = min(phi_max, max(phi_min, next_phi))
            pair[1] = next_phi

    def update(self, dt: float, sim: object) -> None:
        if not self._initialized:
            self.initialize()
        dt_scale = float(getattr(sim, "dt_scale", 1.0))
        turb = float(self.turbulence) * dt_scale
        self._step_angle_pool(self._angles, self._drifts, turb)
        self._step_angle_pool(self._corona_angles, self._corona_drifts, turb * 0.5)

    def render(
        self,
        renderer: ParticleRenderer,
        camera: Camera3D,
        sim: object,
    ) -> None:
        if not self._initialized:
            self.initialize()
        px, py, pz = self._position
        radius = float(self.radius)
        base_rgb = normalize_color(self._color)
        ember_rgb = (
            normalize_color(self._secondary_color)
            if self._secondary_color is not None
            else COLOR_STAR_EMBER
        )
        variation_strength = min(1.0, max(0.0, float(self.color_variation)))
        width = int(sim.width)
        height = int(sim.height)
        modifiers = sim.spatial_modifiers
        lum = float(self.luminosity)

        for idx, (theta, phi) in enumerate(self._angles):
            lx, ly, lz = spherical_to_cartesian(radius, theta, phi)
            world_pt = [px + lx, py + ly, pz + lz]
            if modifiers:
                world_pt = camera.apply_spatial_modifiers(world_pt, modifiers)
            projected = camera.project_depth(world_pt, width, height)
            if projected is None:
                continue
            x_2d, y_2d, scale, z_cam = projected
            tone = self._surface_tones[idx]
            if tone < 0.35:
                core_weight = (1.0 - tone / 0.35) * variation_strength
                rgb = depth_shaded_color(
                    base_rgb,
                    COLOR_STAR_CORE,
                    core_weight,
                    scale,
                    lum * 1.1,
                )
            else:
                ember_weight = ((tone - 0.35) / 0.65) * variation_strength
                rgb = depth_shaded_color(
                    base_rgb,
                    ember_rgb,
                    ember_weight,
                    scale,
                    lum,
                )
            radius_2d = crisp_dot_radius(self._surface_dots[idx], scale)
            renderer.emit(z_cam, x_2d, y_2d, radius_2d, rgb, width, height)

        for idx, (theta, phi) in enumerate(self._corona_angles):
            halo_r = radius * self._corona_radii[idx]
            lx, ly, lz = spherical_to_cartesian(halo_r, theta, phi)
            world_pt = [px + lx, py + ly, pz + lz]
            if modifiers:
                world_pt = camera.apply_spatial_modifiers(world_pt, modifiers)
            projected = camera.project_depth(world_pt, width, height)
            if projected is None:
                continue
            x_2d, y_2d, scale, z_cam = projected
            tone = self._corona_tones[idx]
            rgb = depth_shaded_color(
                base_rgb,
                ember_rgb,
                (0.45 + 0.55 * tone) * variation_strength,
                scale,
                lum * 0.72,
            )
            radius_2d = crisp_dot_radius(0.9, scale)
            renderer.emit(z_cam, x_2d, y_2d, radius_2d, rgb, width, height)


def star() -> Star:
    # instantiate and auto-register a luminous 3d star
    entity = Star()
    register_entity(entity)
    return entity
