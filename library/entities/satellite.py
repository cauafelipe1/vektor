# compact 3d point-cloud satellite able to track a moving parent body

from typing import TYPE_CHECKING

from ..core.constants import COLOR_SATELLITE_SILVER
from ..rendering.camera import Camera3D
from ..rendering.renderer import ParticleRenderer
from .base import PointCloudSphere, register_entity
from .orbit import Orbit

if TYPE_CHECKING:
    from .planet import Planet
    from .star import Star


class Satellite(PointCloudSphere):
    # compact 3d point-cloud moon able to track a moving parent body

    render_layer: int = 40

    def __init__(self) -> None:
        super().__init__(
            mass=7.342e22,
            radius=8.0,
            position=[960.0, 360.0, 0.0],
            velocity=[0.0, 0.0, 0.0],
            color=COLOR_SATELLITE_SILVER,
            particle_count=65,
            spin_speed=0.02,
            luminosity=1.0,
            secondary_color=None,
            color_variation=0.7,
        )
        self.parent: "Planet | Star | None" = None
        self.orbit: Orbit | None = None

    def initialize(self) -> None:
        super().initialize()
        if self.orbit is not None and self.parent is not None:
            self.orbit.center = list(self.parent.position)

    def update(self, dt: float, sim: object) -> None:
        if not self._initialized:
            self.initialize()
        dt_scale = float(getattr(sim, "dt_scale", 1.0))
        if self.orbit is not None:
            self.orbit.step_frame(int(getattr(sim, "frame_count", 0)), dt_scale)
            if self.parent is not None:
                self.orbit.center = list(self.parent.position)
                self._position = self.orbit.sample_at(
                    self.orbit.angle,
                    center_override=self.parent.position,
                )
            else:
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
        self._render_points(renderer, camera, sim)


def satellite() -> Satellite:
    # instantiate and auto-register a 3d satellite body
    entity = Satellite()
    register_entity(entity)
    return entity
