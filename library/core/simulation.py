# simulation state manager, 60 fps pygame loop, and simulate entry point

import os
import time
from collections.abc import Callable, Sequence

import pygame

from ..environment.starfield import Starfield
from ..rendering.camera import Camera3D
from ..rendering.renderer import ParticleRenderer
from .constants import (
    COLOR_HUD_TEXT,
    COLOR_VOID,
    DEFAULT_DURATION,
    DEFAULT_FPS,
    DEFAULT_GRAVITY,
    DEFAULT_HEIGHT,
    DEFAULT_SIM_NAME,
    DEFAULT_STAR_COUNT,
    DEFAULT_WIDTH,
)


class Simulation:
    # global simulation context owning the 3d camera and registered entities

    _active: "Simulation | None" = None

    def __init__(self) -> None:
        Simulation._active = self
        self.name: str = DEFAULT_SIM_NAME
        self.duration: float = DEFAULT_DURATION
        self.gravity: float = DEFAULT_GRAVITY
        self.width: int = DEFAULT_WIDTH
        self.height: int = DEFAULT_HEIGHT
        self.star_count: int = DEFAULT_STAR_COUNT
        self.camera: Camera3D = Camera3D()
        self.spatial_modifiers: list[Callable[[list[float]], Sequence[float]]] = []
        self.entities: list[object] = []
        self.frame_count: int = 0
        self.dt_scale: float = 1.0

    @classmethod
    def get_active(cls) -> "Simulation":
        # return the active simulation or lazily create one
        if cls._active is None:
            return cls()
        return cls._active

    @property
    def camera_position(self) -> list[float]:
        return self.camera.position

    @camera_position.setter
    def camera_position(self, value: Sequence[float]) -> None:
        self.camera.position = value

    @property
    def camera_yaw(self) -> float:
        return self.camera.yaw

    @camera_yaw.setter
    def camera_yaw(self, value: float) -> None:
        self.camera.yaw = float(value)

    @property
    def camera_pitch(self) -> float:
        return self.camera.pitch

    @camera_pitch.setter
    def camera_pitch(self, value: float) -> None:
        self.camera.pitch = float(value)

    @property
    def camera_roll(self) -> float:
        return self.camera.roll

    @camera_roll.setter
    def camera_roll(self, value: float) -> None:
        self.camera.roll = float(value)

    def register(self, entity: object) -> None:
        # register an entity once in the simulation update/render list
        if entity not in self.entities:
            self.entities.append(entity)

    def _read_max_frames(self) -> int | None:
        # inspect optional frame cap environment variable for headless tests
        raw = os.environ.get("VEKTOR_MAX_FRAMES", "").strip()
        if not raw:
            return None
        try:
            value = int(raw)
        except ValueError:
            return None
        return max(1, value)

    def run(self) -> None:
        # initialize pygame window and execute the 60 fps space simulation loop
        width = max(1, int(self.width))
        height = max(1, int(self.height))
        max_frames = self._read_max_frames()

        pygame.init()
        try:
            screen = pygame.display.set_mode((width, height))
            pygame.display.set_caption(str(self.name))
            clock = pygame.time.Clock()
            screen.fill(COLOR_VOID)

            hud_font = pygame.font.SysFont("sans", 18)
            if hud_font is None:
                hud_font = pygame.font.Font(None, 22)

            starfield = Starfield(int(self.star_count), width, height)
            renderer = ParticleRenderer()
            for entity in self.entities:
                entity.initialize()

            self.frame_count = 0
            start_time = time.monotonic()
            running = True

            while running:
                dt = clock.tick(DEFAULT_FPS) / 1000.0
                self.dt_scale = min(0.05, dt) * float(DEFAULT_FPS)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        running = False

                if not running:
                    break

                screen.fill(COLOR_VOID)
                starfield.update(dt, self.dt_scale)
                starfield.draw(screen, self.camera, width, height)

                ordered_entities = sorted(
                    self.entities,
                    key=lambda item: getattr(item, "render_layer", 30),
                )
                for entity in ordered_entities:
                    entity.update(dt, self)

                renderer.clear()
                for entity in ordered_entities:
                    render_fn = getattr(entity, "render", None)
                    if callable(render_fn):
                        render_fn(renderer, self.camera, self)
                    else:
                        entity.draw(screen, self.camera, self)
                renderer.flush(screen)

                label = hud_font.render(str(self.name), True, COLOR_HUD_TEXT)
                screen.blit(label, (20, max(0, height - 35)))

                pygame.display.flip()
                self.frame_count += 1

                elapsed = time.monotonic() - start_time
                if max_frames is not None and self.frame_count >= max_frames:
                    running = False
                elif self.duration is not None and float(self.duration) > 0.0:
                    if elapsed >= float(self.duration):
                        running = False
        finally:
            pygame.quit()


def simulate(target: Simulation | int | float | None = None) -> None:
    # launch the active or specified simulation with optional duration override
    if isinstance(target, Simulation):
        target.run()
        return
    active = Simulation.get_active()
    if isinstance(target, (int, float)) and not isinstance(target, bool):
        active.duration = float(target)
    active.run()
