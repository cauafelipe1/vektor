# rotating 3d stippled point-cloud planet with optional rings and orbit

from typing import TYPE_CHECKING

from ..core.constants import COLOR_PLANET_CYAN
from ..rendering.camera import Camera3D
from ..rendering.renderer import ParticleRenderer
from .base import PointCloudSphere, register_entity
from .orbit import Orbit

if TYPE_CHECKING:
    from .rings import Rings


class Planet(PointCloudSphere):
    # rotating 3d point-cloud planet supporting polar caps, rings, and orbits

    render_layer: int = 30

    def __init__(self) -> None:
        super().__init__(
            mass=5.972e24,
            radius=28.0,
            position=[910.0, 360.0, 0.0],
            velocity=[0.0, 0.0, 0.0],
            color=COLOR_PLANET_CYAN,
            particle_count=300,
            spin_speed=0.012,
            luminosity=1.0,
            secondary_color=None,
            color_variation=0.8,
        )
        self.polar_caps: bool = False
        self._rings: "Rings | None" = None
        self.orbit: Orbit | None = None

    @property
    def rings(self) -> "Rings | None":
        return self._rings

    @rings.setter
    def rings(self, value: "Rings | None") -> None:
        # automatically bind ring target to this planet when attached
        self._rings = value
        if value is not None:
            value.target = self

    def update(self, dt: float, sim: object) -> None:
        if not self._initialized:
            self.initialize()
        dt_scale = float(getattr(sim, "dt_scale", 1.0))
        if self.orbit is not None:
            self.orbit.step_frame(int(getattr(sim, "frame_count", 0)), dt_scale)
            self._position = self.orbit.sample_at(self.orbit.angle)
        else:
            self._position[0] += self._velocity[0] * dt_scale
            self._position[1] += self._velocity[1] * dt_scale
            self._position[2] += self._velocity[2] * dt_scale
        self._spin_points(dt_scale)

    def render(
        self,
        renderer: ParticleRenderer,
        camera: Camera3D,
        sim: object,
    ) -> None:
        if not self._initialized:
            self.initialize()
        self._render_points(renderer, camera, sim, polar_caps=bool(self.polar_caps))


def planet() -> Planet:
    # instantiate and auto-register a 3d point-cloud planet
    entity = Planet()
    register_entity(entity)
    return entity
