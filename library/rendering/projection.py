# pure 3d geometry, rotation, spherical sampling, and depth shading helpers

import math
import random as py_random
from collections.abc import Sequence


def normalize_vec3(value: Sequence[float], default_z: float = 0.0) -> list[float]:
    # promote 2d vectors to 3d and convert elements to floats
    if not isinstance(value, (list, tuple)):
        raise ValueError("vector must be a list or tuple of length 2 or 3")
    if len(value) == 2:
        return [float(value[0]), float(value[1]), float(default_z)]
    if len(value) == 3:
        return [float(value[0]), float(value[1]), float(value[2])]
    raise ValueError(f"expected 2d or 3d vector, got length {len(value)}")


def normalize_color(color: Sequence[float]) -> tuple[int, int, int]:
    # clamp an rgb sequence into valid 0..255 integer channels
    if not isinstance(color, (list, tuple)) or len(color) != 3:
        raise ValueError("color must be a 3-element rgb sequence")
    return (
        min(255, max(0, int(color[0]))),
        min(255, max(0, int(color[1]))),
        min(255, max(0, int(color[2]))),
    )


def mix_rgb(
    color_a: Sequence[float],
    color_b: Sequence[float],
    factor: float,
) -> tuple[float, float, float]:
    # linearly interpolate between two rgb triples with clamped factor
    t = min(1.0, max(0.0, float(factor)))
    inv = 1.0 - t
    return (
        float(color_a[0]) * inv + float(color_b[0]) * t,
        float(color_a[1]) * inv + float(color_b[1]) * t,
        float(color_a[2]) * inv + float(color_b[2]) * t,
    )


def rotate_point_x(vec3: Sequence[float], angle: float) -> list[float]:
    # rotate a 3d vector around the x axis
    x, y, z = float(vec3[0]), float(vec3[1]), float(vec3[2])
    if angle == 0.0:
        return [x, y, z]
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    return [x, y * cos_a - z * sin_a, y * sin_a + z * cos_a]


def rotate_point_y(vec3: Sequence[float], angle: float) -> list[float]:
    # rotate a 3d vector around the y axis
    x, y, z = float(vec3[0]), float(vec3[1]), float(vec3[2])
    if angle == 0.0:
        return [x, y, z]
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    return [x * cos_a + z * sin_a, y, -x * sin_a + z * cos_a]


def rotate_point_z(vec3: Sequence[float], angle: float) -> list[float]:
    # rotate a 3d vector around the z axis
    x, y, z = float(vec3[0]), float(vec3[1]), float(vec3[2])
    if angle == 0.0:
        return [x, y, z]
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    return [x * cos_a - y * sin_a, x * sin_a + y * cos_a, z]


def rotate_vec3(
    vec3: Sequence[float],
    yaw: float,
    pitch: float,
    roll: float,
) -> list[float]:
    # apply yaw (y), pitch (x), and roll (z) euler rotations
    x, y, z = float(vec3[0]), float(vec3[1]), float(vec3[2])
    if yaw == 0.0 and pitch == 0.0 and roll == 0.0:
        return [x, y, z]
    if yaw != 0.0:
        cos_y = math.cos(yaw)
        sin_y = math.sin(yaw)
        x, z = x * cos_y + z * sin_y, -x * sin_y + z * cos_y
    if pitch != 0.0:
        cos_p = math.cos(pitch)
        sin_p = math.sin(pitch)
        y, z = y * cos_p - z * sin_p, y * sin_p + z * cos_p
    if roll != 0.0:
        cos_r = math.cos(roll)
        sin_r = math.sin(roll)
        x, y = x * cos_r - y * sin_r, x * sin_r + y * cos_r
    return [x, y, z]


def spherical_to_cartesian(radius: float, theta: float, phi: float) -> list[float]:
    # convert spherical angles into 3d cartesian coordinates
    sin_phi = math.sin(phi)
    return [
        radius * sin_phi * math.cos(theta),
        radius * sin_phi * math.sin(theta),
        radius * math.cos(phi),
    ]


def generate_sphere_angles(count: int) -> list[tuple[float, float]]:
    # sample uniform points on a unit sphere using inverse cosine latitude
    n = max(0, int(count))
    two_pi = 2.0 * math.pi
    return [
        (py_random.uniform(0.0, two_pi), math.acos(py_random.uniform(-1.0, 1.0)))
        for _ in range(n)
    ]


def crisp_dot_radius(base_dot: float, scale: float) -> int:
    # map perspective scale to crisp 1..3 pixel particle radii
    return max(1, min(3, int(round(base_dot * max(0.7, scale * 1.15)))))


def depth_shaded_color(
    base_rgb: Sequence[float],
    rich_rgb: Sequence[float],
    variation: float,
    scale: float,
    luminosity: float = 1.0,
) -> tuple[int, int, int]:
    # blend multi-tone particle rgb and apply bounded perspective brightness
    r, g, b = mix_rgb(base_rgb, rich_rgb, variation)
    brightness = min(1.18, max(0.28, scale * 1.18 * luminosity))
    return (
        min(255, max(0, int(r * brightness))),
        min(255, max(0, int(g * brightness))),
        min(255, max(0, int(b * brightness))),
    )
