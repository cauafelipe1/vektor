# decoupled 3d camera and perspective projection pipeline

from collections.abc import Callable, Iterable, Sequence

from ..core.constants import (
    DEFAULT_CAMERA_PITCH,
    DEFAULT_CAMERA_POSITION,
    DEFAULT_FOCAL_LENGTH,
    DEFAULT_HEIGHT,
    DEFAULT_VISION_RATIO,
    DEFAULT_WIDTH,
    NEAR_CLIP_Z,
)
from .projection import normalize_vec3, rotate_vec3


class Camera3D:
    # decoupled 3d camera supporting euler orientation and spatial modifiers

    def __init__(
        self,
        position: Sequence[float] | None = None,
        yaw: float = 0.0,
        pitch: float = DEFAULT_CAMERA_PITCH,
        roll: float = 0.0,
        focal_length: float = DEFAULT_FOCAL_LENGTH,
        vision_ratio: float = DEFAULT_VISION_RATIO,
    ) -> None:
        self._position: list[float] = normalize_vec3(
            DEFAULT_CAMERA_POSITION if position is None else position,
            default_z=DEFAULT_CAMERA_POSITION[2],
        )
        self.yaw: float = float(yaw)
        self.pitch: float = float(pitch)
        self.roll: float = float(roll)
        self.focal_length: float = float(focal_length)
        self.vision_ratio: float = float(vision_ratio)

    @property
    def position(self) -> list[float]:
        return self._position

    @position.setter
    def position(self, value: Sequence[float]) -> None:
        # preserve existing camera depth z when assigning a 2d vector
        self._position = normalize_vec3(value, default_z=self._position[2])

    def world_to_camera(
        self,
        world_pos: Sequence[float],
        viewport_width: float = DEFAULT_WIDTH,
        viewport_height: float = DEFAULT_HEIGHT,
    ) -> list[float]:
        # transform world coordinates into camera space orbiting the scene center
        wx, wy, wz = normalize_vec3(world_pos)
        ox = wx - viewport_width / 2.0 - self._position[0]
        oy = wy - viewport_height / 2.0 - self._position[1]
        oz = wz
        rx, ry, rz = rotate_vec3([ox, oy, oz], -self.yaw, -self.pitch, -self.roll)
        cz = rz - self._position[2]
        return [rx, ry, cz]

    def project_depth(
        self,
        world_pos: Sequence[float],
        viewport_width: float = DEFAULT_WIDTH,
        viewport_height: float = DEFAULT_HEIGHT,
    ) -> tuple[int, int, float, float] | None:
        # project a 3d world point returning screen position, scale, and camera z
        cx, cy, cz = self.world_to_camera(world_pos, viewport_width, viewport_height)
        if cz <= NEAR_CLIP_Z:
            return None
        scale = self.focal_length / cz
        x_2d = int(viewport_width / 2.0 + cx * scale)
        y_2d = int(viewport_height / 2.0 + cy * scale)
        return (x_2d, y_2d, scale, cz)

    def project(
        self,
        world_pos: Sequence[float],
        viewport_width: float = DEFAULT_WIDTH,
        viewport_height: float = DEFAULT_HEIGHT,
    ) -> tuple[int, int, float] | None:
        # project a 3d world coordinate onto the 2d viewport with near-plane clipping
        projected = self.project_depth(world_pos, viewport_width, viewport_height)
        if projected is None:
            return None
        x_2d, y_2d, scale, _ = projected
        return (x_2d, y_2d, scale)

    def project_point(
        self,
        local_offset: Sequence[float],
        anchor_2d: Sequence[float],
    ) -> tuple[int, int, float] | None:
        # project a local 3d offset around a 2d screen anchor
        vx, vy, vz = rotate_vec3(
            normalize_vec3(local_offset),
            -self.yaw,
            -self.pitch,
            -self.roll,
        )
        depth = vz + self.vision_ratio
        if depth <= NEAR_CLIP_Z:
            return None
        scale = self.focal_length / depth
        x_2d = int(anchor_2d[0] + vx * scale)
        y_2d = int(anchor_2d[1] + vy * scale)
        return (x_2d, y_2d, scale)

    def apply_spatial_modifiers(
        self,
        world_pos: Sequence[float],
        modifiers: Iterable[Callable[[list[float]], Sequence[float]]] | None = None,
    ) -> list[float]:
        # pass world position through registered spatial field modifiers
        pos = normalize_vec3(world_pos)
        if not modifiers:
            return pos
        for modifier in modifiers:
            pos = normalize_vec3(modifier(pos))
        return pos
