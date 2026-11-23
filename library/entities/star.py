# luminous 3d point-cloud star with multi-tone surface turbulence and corona

import math
import random as py_random

from ..core.constants import (
    COLOR_STAR_AMBER,
    COLOR_STAR_CORE,
    COLOR_STAR_EMBER,
    COLOR_SUPERNOVA_FLASH,
    COLOR_SUPERNOVA_REMNANT,
    DEFAULT_SUPERNOVA_BURST_COUNT,
    SUPERNOVA_BURST_DURATION,
    SUPERNOVA_UNSTABLE_DURATION,
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
        # schedule collapse at age seconds; negative disables timed supernova
        self.collapse_at: float = -1.0
        self.go_supernova: bool = False
        self.burst_count: int = DEFAULT_SUPERNOVA_BURST_COUNT
        self.remnant: str = "nebula"
        self.phase: str = "stable"
        self._life_time: float = 0.0
        self._phase_time: float = 0.0
        self._angles: list[list[float]] = []
        self._drifts: list[tuple[float, float]] = []
        self._surface_tones: list[float] = []
        self._surface_dots: list[float] = []
        self._corona_angles: list[list[float]] = []
        self._corona_radii: list[float] = []
        self._corona_drifts: list[tuple[float, float]] = []
        self._corona_tones: list[float] = []
        self._burst_particles: list[list[float]] = []

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
        self._burst_particles = []
        if self.phase not in {"stable", "unstable", "burst", "remnant"}:
            self.phase = "stable"
        self._initialized = True

    def _enter_phase(self, phase: str) -> None:
        # switch supernova lifecycle phase and reset phase-local timer
        self.phase = phase
        self._phase_time = 0.0

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

    def _spawn_burst(self) -> None:
        # seed an expanding radial debris shell for the burst phase
        count = max(0, int(self.burst_count))
        pairs = generate_sphere_angles(count)
        radius = max(1.0, float(self.radius))
        px, py, pz = self._position
        self._burst_particles = []
        for theta, phi in pairs:
            dx, dy, dz = spherical_to_cartesian(1.0, theta, phi)
            speed = py_random.uniform(2.8, 7.5)
            shell = radius * py_random.uniform(0.85, 1.15)
            self._burst_particles.append(
                [
                    px + dx * shell,
                    py + dy * shell,
                    pz + dz * shell,
                    dx * speed,
                    dy * speed,
                    dz * speed,
                    py_random.random(),
                    py_random.uniform(0.9, 1.6),
                ]
            )

    def _advance_lifecycle(self, dt: float) -> None:
        # progress stable -> unstable -> burst -> remnant from age and flags
        self._life_time += float(dt)
        self._phase_time += float(dt)

        if self.phase == "stable":
            timed = float(self.collapse_at) >= 0.0 and self._life_time >= float(
                self.collapse_at
            )
            if bool(self.go_supernova) or timed:
                self.go_supernova = False
                self._enter_phase("unstable")
            return

        if self.phase == "unstable":
            if self._phase_time >= SUPERNOVA_UNSTABLE_DURATION:
                self._spawn_burst()
                self._enter_phase("burst")
            return

        if self.phase == "burst":
            if self._phase_time >= SUPERNOVA_BURST_DURATION:
                remnant = str(self.remnant).strip().lower()
                if remnant in {"", "none", "false", "0"}:
                    self._burst_particles = []
                    self._enter_phase("remnant")
                else:
                    self._enter_phase("remnant")

    def _update_burst_particles(self, dt_scale: float) -> None:
        # integrate burst debris outward; slow drift once in remnant
        drag = 0.985 if self.phase == "burst" else 0.992
        step = float(dt_scale)
        for particle in self._burst_particles:
            particle[0] += particle[3] * step
            particle[1] += particle[4] * step
            particle[2] += particle[5] * step
            particle[3] *= drag
            particle[4] *= drag
            particle[5] *= drag

    def update(self, dt: float, sim: object) -> None:
        if not self._initialized:
            self.initialize()
        dt_scale = float(getattr(sim, "dt_scale", 1.0))
        self._advance_lifecycle(float(dt))

        turb = float(self.turbulence) * dt_scale
        if self.phase == "unstable":
            # ramp surface chaos as the star becomes unstable
            progress = min(1.0, self._phase_time / SUPERNOVA_UNSTABLE_DURATION)
            turb *= 1.0 + 7.0 * progress
        elif self.phase in {"burst", "remnant"}:
            turb *= 0.15

        if self.phase in {"stable", "unstable"}:
            self._step_angle_pool(self._angles, self._drifts, turb)
            self._step_angle_pool(self._corona_angles, self._corona_drifts, turb * 0.5)

        if self.phase in {"burst", "remnant"} and self._burst_particles:
            self._update_burst_particles(dt_scale)

    def _render_burst_cloud(
        self,
        renderer: ParticleRenderer,
        camera: Camera3D,
        sim: object,
        modifiers: object,
        width: int,
        height: int,
        flash_rgb: tuple[int, int, int],
        remnant_rgb: tuple[int, int, int],
        luminosity: float,
    ) -> None:
        # emit expanding or remnant debris into the painter queue
        variation_strength = min(1.0, max(0.0, float(self.color_variation)))
        for particle in self._burst_particles:
            world_pt = [particle[0], particle[1], particle[2]]
            if modifiers:
                world_pt = camera.apply_spatial_modifiers(world_pt, modifiers)
            projected = camera.project_depth(world_pt, width, height)
            if projected is None:
                continue
            x_2d, y_2d, scale, z_cam = projected
            tone = particle[6]
            if self.phase == "burst":
                rgb = depth_shaded_color(
                    flash_rgb,
                    remnant_rgb,
                    tone * variation_strength,
                    scale,
                    luminosity,
                )
            else:
                rgb = depth_shaded_color(
                    remnant_rgb,
                    flash_rgb,
                    0.25 * variation_strength,
                    scale,
                    luminosity * 0.55,
                )
            radius_2d = crisp_dot_radius(particle[7], scale)
            renderer.emit(z_cam, x_2d, y_2d, radius_2d, rgb, width, height)

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
        flash_rgb = COLOR_SUPERNOVA_FLASH
        remnant_rgb = COLOR_SUPERNOVA_REMNANT
        variation_strength = min(1.0, max(0.0, float(self.color_variation)))
        width = int(sim.width)
        height = int(sim.height)
        modifiers = sim.spatial_modifiers
        lum = float(self.luminosity)

        unstable_progress = 0.0
        if self.phase == "unstable":
            unstable_progress = min(1.0, self._phase_time / SUPERNOVA_UNSTABLE_DURATION)
            lum *= 1.0 + 1.8 * unstable_progress
            radius *= 1.0 + 0.35 * unstable_progress
        elif self.phase == "burst":
            # core collapses while the flash shell expands
            burst_progress = min(1.0, self._phase_time / SUPERNOVA_BURST_DURATION)
            lum *= max(0.15, 2.4 * (1.0 - burst_progress))
            radius *= max(0.05, 1.0 - 0.95 * burst_progress)
        elif self.phase == "remnant":
            # core is gone; only remnant debris remains when configured
            if self._burst_particles:
                self._render_burst_cloud(
                    renderer,
                    camera,
                    sim,
                    modifiers,
                    width,
                    height,
                    flash_rgb,
                    remnant_rgb,
                    max(0.2, lum * 0.35),
                )
            return

        if self.phase in {"stable", "unstable", "burst"} and radius > 0.5:
            corona_scale = 1.0 + 0.85 * unstable_progress
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
                if self.phase == "burst":
                    rgb = depth_shaded_color(
                        flash_rgb,
                        ember_rgb,
                        variation_strength,
                        scale,
                        lum * 1.3,
                    )
                elif tone < 0.35:
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
                    ember_weight = min(
                        1.0,
                        ember_weight + 0.55 * unstable_progress * variation_strength,
                    )
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
                halo_r = radius * self._corona_radii[idx] * corona_scale
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
                    base_rgb if self.phase != "burst" else flash_rgb,
                    ember_rgb,
                    (0.45 + 0.55 * tone) * variation_strength,
                    scale,
                    lum * (0.72 + 0.5 * unstable_progress),
                )
                radius_2d = crisp_dot_radius(0.9, scale)
                renderer.emit(z_cam, x_2d, y_2d, radius_2d, rgb, width, height)

        if self.phase in {"burst", "remnant"} and self._burst_particles:
            self._render_burst_cloud(
                renderer,
                camera,
                sim,
                modifiers,
                width,
                height,
                flash_rgb,
                remnant_rgb,
                lum if self.phase == "burst" else max(0.2, lum * 0.35),
            )


def star() -> Star:
    # instantiate and auto-register a luminous 3d star
    entity = Star()
    register_entity(entity)
    return entity
