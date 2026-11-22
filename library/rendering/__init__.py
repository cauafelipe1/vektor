# rendering subpackage exports for camera, projection math, and painter renderer

from .camera import Camera3D
from .projection import (
    crisp_dot_radius,
    depth_shaded_color,
    generate_sphere_angles,
    mix_rgb,
    normalize_color,
    normalize_vec3,
    rotate_point_x,
    rotate_point_y,
    rotate_point_z,
    rotate_vec3,
    spherical_to_cartesian,
)
from .renderer import ParticleRenderer

__all__ = [
    "Camera3D",
    "ParticleRenderer",
    "crisp_dot_radius",
    "depth_shaded_color",
    "generate_sphere_angles",
    "mix_rgb",
    "normalize_color",
    "normalize_vec3",
    "rotate_point_x",
    "rotate_point_y",
    "rotate_point_z",
    "rotate_vec3",
    "spherical_to_cartesian",
]
