# multi-depth 3d twinkling pinpoint starfield background

import math
import random as py_random

import pygame

from ..core.constants import STARFIELD_PALETTE
from ..rendering.camera import Camera3D
from ..rendering.projection import rotate_point_z


class Starfield:
    # distant 3d pinpoint star layer with gentle z-axis rotation and twinkle

    def __init__(self, count: int, width: int, height: int) -> None:
        self.count: int = max(0, int(count))
        self.width: int = max(1, int(width))
        self.height: int = max(1, int(height))
        self._stars: list[dict[str, object]] = []
        self._populate()

    def _populate(self) -> None:
        # distribute distant stars across a wide 3d background frustum
        half_w = self.width * 2.0
        half_h = self.height * 2.0
        two_pi = 2.0 * math.pi
        for _ in range(self.count):
            self._stars.append(
                {
                    "offset": [
                        py_random.uniform(-half_w, half_w),
                        py_random.uniform(-half_h, half_h),
                        py_random.uniform(260.0, 1450.0),
                    ],
                    "phase": py_random.uniform(0.0, two_pi),
                    "twinkle_speed": py_random.uniform(0.015, 0.06),
                    "base_brightness": py_random.uniform(0.45, 0.95),
                    "color": py_random.choice(STARFIELD_PALETTE),
                }
            )

    def update(self, dt: float, dt_scale: float = 1.0) -> None:
        # gently rotate background stars around z and advance twinkle phases
        scale = float(dt_scale)
        angle = 0.00025 * scale
        for entry in self._stars:
            entry["offset"] = rotate_point_z(entry["offset"], angle)
            entry["phase"] = float(entry["phase"]) + float(entry["twinkle_speed"]) * scale

    def draw(
        self,
        screen: pygame.Surface,
        camera: Camera3D,
        width: int,
        height: int,
    ) -> None:
        # project and draw crisp 1px background stars with sinusoidal twinkle
        half_w = width / 2.0
        half_h = height / 2.0
        fill_rect = screen.fill
        for entry in self._stars:
            ox, oy, oz = entry["offset"]
            projected = camera.project(
                [half_w + ox, half_h + oy, oz],
                width,
                height,
            )
            if projected is None:
                continue
            x_2d, y_2d, scale = projected
            if x_2d < 0 or x_2d >= width or y_2d < 0 or y_2d >= height:
                continue
            twinkle = 0.55 + 0.45 * math.sin(float(entry["phase"]))
            base_lum = float(entry["base_brightness"])
            brightness = min(1.0, max(0.18, twinkle * base_lum * (0.55 + scale)))
            base_r, base_g, base_b = entry["color"]
            rgb = (
                min(255, max(0, int(base_r * brightness))),
                min(255, max(0, int(base_g * brightness))),
                min(255, max(0, int(base_b * brightness))),
            )
            fill_rect(rgb, (x_2d, y_2d, 1, 1))
