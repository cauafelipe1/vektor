# per-particle back-to-front painter algorithm renderer

from operator import itemgetter

import pygame

_DEPTH_KEY = itemgetter(0)


class ParticleRenderer:
    # collects projected 3d particles and draws them sorted by camera depth

    def __init__(self) -> None:
        self._queue: list[tuple[float, int, int, int, tuple[int, int, int]]] = []

    def clear(self) -> None:
        # discard any queued particles from previous frames
        self._queue.clear()

    def emit(
        self,
        z_cam: float,
        x_2d: int,
        y_2d: int,
        radius_2d: int,
        rgb: tuple[int, int, int],
        width: int,
        height: int,
    ) -> None:
        # enqueue a visible projected particle keyed by negated camera depth
        if x_2d < -6 or x_2d > width + 6 or y_2d < -6 or y_2d > height + 6:
            return
        self._queue.append((-float(z_cam), int(x_2d), int(y_2d), int(radius_2d), rgb))

    def flush(self, screen: pygame.Surface) -> int:
        # sort back-to-front and render crisp 1px and 2..3px particles
        self._queue.sort(key=_DEPTH_KEY)
        draw_circle = pygame.draw.circle
        fill_rect = screen.fill
        drawn = len(self._queue)
        for _, x_2d, y_2d, radius_2d, rgb in self._queue:
            if radius_2d <= 1:
                fill_rect(rgb, (x_2d, y_2d, 1, 1))
            else:
                draw_circle(screen, rgb, (x_2d, y_2d), radius_2d)
        self._queue.clear()
        return drawn
