# mutable 0-based 3d bounding region and overloaded random helper

import random as py_random
from collections.abc import Sequence

from ..rendering.projection import normalize_vec3


class RandomRegion(list):
    # 3d bounding region behaving as a mutable 0-based coordinate list

    def __init__(self, low: Sequence[float], high: Sequence[float]) -> None:
        norm_low = normalize_vec3(low)
        norm_high = normalize_vec3(high)
        super().__init__([norm_low[0], norm_low[1], norm_low[2]])
        self.low: list[float] = [norm_low[0], norm_low[1], norm_low[2]]
        self.high: list[float] = [norm_high[0], norm_high[1], norm_high[2]]

    def __setitem__(self, index: int | slice, value: object) -> None:
        # shift both stored coordinate and low/high bounds on 0-based mutation
        if isinstance(index, int):
            idx = index if index >= 0 else len(self) + index
            new_val = float(value)
            delta = new_val - float(self[idx])
            super().__setitem__(idx, new_val)
            self.low[idx] += delta
            self.high[idx] += delta
            return
        super().__setitem__(index, value)

    def sample_point(self) -> list[float]:
        # sample a uniform 3d point inside the shifted bounding box
        return [
            py_random.uniform(self.low[0], self.high[0]),
            py_random.uniform(self.low[1], self.high[1]),
            py_random.uniform(self.low[2], self.high[2]),
        ]


def random(
    low: float | Sequence[float],
    high: float | Sequence[float],
) -> float | RandomRegion:
    # return a scalar uniform sample or a mutable 3d random region
    if isinstance(low, (list, tuple)) and isinstance(high, (list, tuple)):
        return RandomRegion(low, high)
    return py_random.uniform(float(low), float(high))
