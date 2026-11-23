# unit and headless integration tests for the vektor python runtime

import math
from pathlib import Path

import pygame
import pytest

import library
from library import (
    Simulation,
    orbit,
    particle_group,
    planet,
    random,
    rings,
    satellite,
    simulate,
    star,
)
from library.core.constants import (
    CAMERA_DOLLY_SPEED,
    CAMERA_MOUSE_SENSITIVITY,
    CAMERA_PAN_SPEED,
    CAMERA_PITCH_MAX,
    CAMERA_PITCH_MIN,
    CAMERA_Z_MAX,
    CAMERA_Z_MIN,
    DEFAULT_CAMERA_PITCH,
    DEFAULT_CAMERA_POSITION,
    DEFAULT_FOCAL_LENGTH,
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    NEAR_CLIP_Z,
)
from library.entities import RandomRegion
from library.rendering import (
    Camera3D,
    ParticleRenderer,
    crisp_dot_radius,
    depth_shaded_color,
    mix_rgb,
    normalize_color,
    normalize_vec3,
)


def test_subpackage_modularity_and_public_exports() -> None:
    # verify exact nine public exports and modular subpackage structure
    expected = {
        "Simulation",
        "planet",
        "star",
        "satellite",
        "particle_group",
        "rings",
        "orbit",
        "random",
        "simulate",
    }
    assert set(library.__all__) == expected
    for symbol in expected:
        assert hasattr(library, symbol)

    library_dir = Path(library.__file__).resolve().parent
    root_py_files = sorted(p.name for p in library_dir.glob("*.py"))
    assert root_py_files == ["__init__.py"]
    for subpkg in ("core", "rendering", "entities", "environment"):
        assert (library_dir / subpkg / "__init__.py").is_file()


def test_library_source_purity() -> None:
    # verify absence of legacy symbols and external or meta terms across library
    forbidden_parts = [
        ("su", "n("),
        ("Sun", "Simulation"),
        ("Sun", "Particle"),
        ("Magnetic", "Field"),
        ("Magnetic", "Particle"),
        ("Radiation", "Particle"),
        ("earth", "Center"),
        ("sun", "Center"),
        ("x", "ray"),
        ("y", "ray"),
        ("No ", "Man's Sky"),
        ("no ", "man's sky"),
        ("magnetic", "FieldsSimulation"),
        ("AGENTS", ".md"),
        (".age", "nts"),
        ("sw", "arm"),
        ("wor", "ker"),
        ("phase", "-2"),
        ("phase", " 2"),
    ]
    forbidden_tokens = ["".join(parts) for parts in forbidden_parts]
    library_dir = Path(library.__file__).resolve().parent
    for py_file in sorted(library_dir.rglob("*.py")):
        source = py_file.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            assert token not in source, (
                f"forbidden token {token!r} found in {py_file.relative_to(library_dir)}"
            )
    assert not hasattr(library, "".join(("su", "n")))


def test_projection_math_and_color_helpers() -> None:
    # verify 2d vector promotion, 3d preservation, color mixing, and crisp radii
    assert normalize_vec3([10, 20]) == [10.0, 20.0, 0.0]
    assert normalize_vec3([10, 20], default_z=-5.0) == [10.0, 20.0, -5.0]
    assert normalize_vec3([1, 2, 3]) == [1.0, 2.0, 3.0]

    with pytest.raises(ValueError):
        normalize_vec3([1.0])
    with pytest.raises(ValueError):
        normalize_vec3([1.0, 2.0, 3.0, 4.0])

    assert normalize_color([-10, 128.9, 300]) == (0, 128, 255)
    assert mix_rgb((0, 100, 200), (100, 200, 0), 0.5) == (50.0, 150.0, 100.0)
    assert crisp_dot_radius(1.0, 0.63) == 1
    assert crisp_dot_radius(2.5, 4.0) == 3

    shaded = depth_shaded_color(
        (100, 200, 250),
        (200, 100, 50),
        variation=0.5,
        scale=0.5,
        luminosity=1.0,
    )
    assert all(0 <= c <= 255 for c in shaded)
    assert shaded == (88, 88, 88)


def test_camera3d_z_preservation_projection_clipping_and_modifiers() -> None:
    # verify camera defaults, 2d z-preservation, project_depth, and clipping
    cam = Camera3D()
    assert cam.position == DEFAULT_CAMERA_POSITION
    assert math.isclose(cam.pitch, DEFAULT_CAMERA_PITCH)

    # verify assigning a 2d vector preserves existing z depth (-1080.0)
    cam.position = [100, -50]
    assert cam.position == [100.0, -50.0, -1080.0]

    # verify simulation camera_position and euler properties forward cleanly
    sim = Simulation()
    sim.camera_position = [40, -20]
    assert sim.camera_position == [40.0, -20.0, -1080.0]
    sim.camera_yaw = 0.15
    sim.camera_pitch = 0.3
    sim.camera_roll = -0.05
    assert math.isclose(sim.camera.yaw, 0.15)
    assert math.isclose(sim.camera.pitch, 0.3)
    assert math.isclose(sim.camera.roll, -0.05)

    # verify scene center projects cleanly with project_depth and project
    base_cam = Camera3D(pitch=0.0)
    depth_proj = base_cam.project_depth([640.0, 360.0, 0.0], DEFAULT_WIDTH, DEFAULT_HEIGHT)
    assert depth_proj is not None
    x_2d, y_2d, scale, z_cam = depth_proj
    assert x_2d == 640
    assert y_2d == 360
    assert math.isclose(z_cam, 1080.0, rel_tol=1e-6)
    assert math.isclose(scale, DEFAULT_FOCAL_LENGTH / 1080.0, rel_tol=1e-6)
    assert base_cam.project([640.0, 360.0, 0.0], DEFAULT_WIDTH, DEFAULT_HEIGHT) == (
        x_2d,
        y_2d,
        scale,
    )

    # verify clipping for points at or behind near plane (z_cam <= NEAR_CLIP_Z)
    clip_z = -1080.0 + NEAR_CLIP_Z
    assert base_cam.project_depth([640.0, 360.0, clip_z], DEFAULT_WIDTH, DEFAULT_HEIGHT) is None
    assert base_cam.project_depth([640.0, 360.0, -1200.0], DEFAULT_WIDTH, DEFAULT_HEIGHT) is None

    # verify euler orientation shifts projected screen coordinates
    rot_cam = Camera3D(yaw=0.4, pitch=0.25, roll=0.1)
    rot_proj = rot_cam.project_depth([860.0, 410.0, 80.0], DEFAULT_WIDTH, DEFAULT_HEIGHT)
    flat_proj = base_cam.project_depth([860.0, 410.0, 80.0], DEFAULT_WIDTH, DEFAULT_HEIGHT)
    assert rot_proj is not None and flat_proj is not None
    assert (rot_proj[0], rot_proj[1]) != (flat_proj[0], flat_proj[1])

    # verify local offset projection helper
    local_proj = base_cam.project_point([100.0, -50.0, 0.0], [640.0, 360.0])
    assert local_proj is not None
    assert local_proj[0] > 640 and local_proj[1] < 360
    assert base_cam.project_point([0.0, 0.0, -1080.0], [640.0, 360.0]) is None

    # verify spatial modifiers execute sequentially
    warped = base_cam.apply_spatial_modifiers(
        [10.0, 20.0, 30.0],
        modifiers=[
            lambda p: [p[0] + 5.0, p[1], p[2]],
            lambda p: [p[0], p[1] * 2.0, p[2] - 10.0],
        ],
    )
    assert warped == [15.0, 40.0, 20.0]


def test_camera3d_keyboard_pan_dolly_and_z_clamp() -> None:
    # verify wasd/arrows/space/shift pan xy and dolly z with clamps
    cam = Camera3D(pitch=0.0)
    base_z = cam.position[2]

    cam.apply_keyboard_motion({pygame.K_d: True}, dt_scale=1.0)
    assert cam.position == [CAMERA_PAN_SPEED, 0.0, base_z]

    cam.apply_keyboard_motion({pygame.K_LEFT: True}, dt_scale=1.0)
    assert cam.position == [0.0, 0.0, base_z]

    cam.apply_keyboard_motion({pygame.K_SPACE: True}, dt_scale=2.0)
    assert cam.position == [0.0, -CAMERA_PAN_SPEED * 2.0, base_z]

    cam.apply_keyboard_motion({pygame.K_LSHIFT: True}, dt_scale=2.0)
    assert cam.position == [0.0, 0.0, base_z]

    cam.apply_keyboard_motion({pygame.K_w: True}, dt_scale=1.0)
    assert math.isclose(cam.position[2], base_z + CAMERA_DOLLY_SPEED)
    assert cam.position[0] == 0.0 and cam.position[1] == 0.0

    cam.apply_keyboard_motion({pygame.K_DOWN: True}, dt_scale=1.0)
    assert math.isclose(cam.position[2], base_z)

    # verify yaw-relative pan: 180 deg yaw reverses world-x strafe for a/d
    cam.yaw = math.pi
    cam.position = [0.0, 0.0, base_z]
    cam._pivot_z = 0.0
    cam.apply_keyboard_motion({pygame.K_d: True}, dt_scale=1.0)
    assert math.isclose(cam.position[0], -CAMERA_PAN_SPEED, abs_tol=1e-9)
    assert math.isclose(cam.position[1], 0.0, abs_tol=1e-9)
    assert math.isclose(cam.position[2], base_z, abs_tol=1e-9)
    assert math.isclose(cam._pivot_z, 0.0, abs_tol=1e-9)

    # verify 90 deg yaw strafes via pivot z (not viewing distance) and moves camera-x
    cam.yaw = math.pi / 2.0
    cam.position = [0.0, 0.0, base_z]
    cam._pivot_z = 0.0
    center = [640.0, 360.0, 0.0]
    before = cam.world_to_camera(center, DEFAULT_WIDTH, DEFAULT_HEIGHT)
    cam.apply_keyboard_motion({pygame.K_d: True}, dt_scale=1.0)
    after = cam.world_to_camera(center, DEFAULT_WIDTH, DEFAULT_HEIGHT)
    assert math.isclose(cam.position[0], 0.0, abs_tol=1e-9)
    assert math.isclose(cam.position[1], 0.0, abs_tol=1e-9)
    assert math.isclose(cam.position[2], base_z, abs_tol=1e-9)
    assert math.isclose(cam._pivot_z, -CAMERA_PAN_SPEED, abs_tol=1e-9)
    assert after[0] < before[0]
    assert math.isclose(after[1], before[1], abs_tol=1e-6)

    # verify dolly clamp keeps camera safely beyond near clip depth
    cam.translate(0.0, 0.0, 10_000.0)
    assert cam.position[2] == CAMERA_Z_MAX
    cam.translate(0.0, 0.0, -10_000.0)
    assert cam.position[2] == CAMERA_Z_MIN

    # verify 2d position assignment still preserves dolly z after motion
    cam.position = [25, -10]
    assert cam.position == [25.0, -10.0, CAMERA_Z_MIN]


def test_camera3d_mouse_orbit_and_pitch_clamp() -> None:
    # verify mouse drag orbits yaw/pitch and pitch stays within clamp range
    cam = Camera3D(yaw=0.0, pitch=0.0)
    cam.apply_mouse_motion(40.0, -20.0)
    assert math.isclose(cam.yaw, 40.0 * CAMERA_MOUSE_SENSITIVITY)
    assert math.isclose(cam.pitch, 20.0 * CAMERA_MOUSE_SENSITIVITY)

    cam.rotate(0.0, 10.0)
    assert cam.pitch == CAMERA_PITCH_MAX
    cam.rotate(0.0, -10.0)
    assert cam.pitch == CAMERA_PITCH_MIN

    # verify position is untouched by orientation-only mouse orbit
    assert cam.position == DEFAULT_CAMERA_POSITION


def test_particle_renderer_back_to_front_sorting() -> None:
    # verify painter algorithm draws farthest z_cam first so nearest overwrites
    surface = pygame.Surface((100, 100))
    surface.fill((0, 0, 0))
    renderer = ParticleRenderer()

    near_rgb = (240, 60, 60)
    far_rgb = (40, 120, 240)

    # emit near particle before far particle at identical screen coordinates
    renderer.emit(z_cam=450.0, x_2d=50, y_2d=50, radius_2d=1, rgb=near_rgb, width=100, height=100)
    renderer.emit(z_cam=1250.0, x_2d=50, y_2d=50, radius_2d=1, rgb=far_rgb, width=100, height=100)
    # emit out-of-bounds particle that should be culled
    renderer.emit(z_cam=600.0, x_2d=-20, y_2d=50, radius_2d=1, rgb=(255, 255, 255), width=100, height=100)
    # emit 2px circle particle at separate coordinate
    renderer.emit(z_cam=700.0, x_2d=20, y_2d=20, radius_2d=2, rgb=(90, 220, 140), width=100, height=100)

    drawn = renderer.flush(surface)
    assert drawn == 3
    assert surface.get_at((50, 50))[:3] == near_rgb
    assert surface.get_at((20, 20))[:3] == (90, 220, 140)


def test_random_overload_and_zero_based_region_mutation() -> None:
    # verify scalar random returns float inside range
    scalar = random(5.0, 10.0)
    assert isinstance(scalar, float)
    assert 5.0 <= scalar <= 10.0

    # verify vector random returns mutable 0-based random region
    region = random([0, 10], [100, 200])
    assert isinstance(region, RandomRegion)
    assert region[0] == 0.0
    assert region[1] == 10.0
    assert region.low == [0.0, 10.0, 0.0]
    assert region.high == [100.0, 200.0, 0.0]

    # mutate x coordinate using native 0-based indexing and verify bound shift
    region[0] = region[0] + 20
    assert region[0] == 20.0
    assert region.low[0] == 20.0
    assert region.high[0] == 120.0

    for _ in range(50):
        sample = region.sample_point()
        assert 20.0 <= sample[0] <= 120.0
        assert 10.0 <= sample[1] <= 200.0


def test_entities_rings_gap_particle_modes_and_dt_scale() -> None:
    # verify entity factories, rings gap exclusion, particle modes, and dt_scale
    sim = Simulation()
    s = star()
    p = planet()
    r = rings()
    o = orbit()
    sat = satellite()
    pg_cloud = particle_group()

    assert len(sim.entities) == 6
    for entity in (s, p, r, o, sat, pg_cloud):
        assert entity in sim.entities

    # verify star corona generation
    s.particle_count = 90
    s.corona_count = 30
    s.initialize()
    assert len(s._angles) == 90
    assert len(s._corona_angles) == 30

    # verify 2d normalization and 0-based z mutation
    p.position = [400, 250]
    assert p.position == [400.0, 250.0, 0.0]
    p.position[2] = -35
    assert p.position[2] == -35.0
    p.polar_caps = True
    p.secondary_color = [30, 122, 198]

    # verify planet.rings auto-binds rings.target and ring gap excludes particles
    r.inner_radius = 50.0
    r.outer_radius = 100.0
    r.gap_inner = 70.0
    r.gap_outer = 80.0
    r.particle_count = 300
    p.rings = r
    assert r.target is p
    r.initialize()
    assert len(r._polar_points) == 300
    for rad, _ in r._polar_points:
        assert 50.0 <= rad <= 100.0
        assert not (70.0 < rad < 80.0)

    # verify dt_scale proportionally scales orbital advancement
    o.radius = 50.0
    o.speed = 0.1
    sat.parent = p
    sat.orbit = o
    sat.initialize()
    p.position = [600.0, 320.0, 10.0]
    sim.dt_scale = 2.0
    sim.frame_count = 1
    sat.update(0.032, sim)
    assert math.isclose(o.angle, 0.2, rel_tol=1e-6)
    assert o.center == [600.0, 320.0, 10.0]
    assert math.isclose(math.dist(sat.position, p.position), 50.0, rel_tol=1e-4)

    # verify particle group cloud mode preserves random region bounds
    region = random([10, 20], [110, 120])
    region[0] = region[0] + 20
    pg_cloud.mode = "cloud"
    pg_cloud.count = 40
    pg_cloud.position = region
    pg_cloud.initialize()
    assert isinstance(pg_cloud.position, RandomRegion)
    assert len(pg_cloud._particles) == 40
    for pt in pg_cloud._particles:
        assert 30.0 <= pt[0] <= 130.0
        assert 20.0 <= pt[1] <= 120.0

    # verify particle group belt mode generates toroidal ring around center
    pg_belt = particle_group()
    pg_belt.mode = "belt"
    pg_belt.center = [640, 360, 0]
    pg_belt.inner_radius = 350.0
    pg_belt.outer_radius = 400.0
    pg_belt.thickness = 24.0
    pg_belt.count = 80
    pg_belt.angular_speed = 0.05
    pg_belt.initialize()
    assert len(pg_belt._particles) == 80
    before_x = pg_belt._particles[0][0]
    for pt in pg_belt._particles:
        radial = math.hypot(pt[0] - 640.0, pt[2] - 0.0)
        assert 350.0 - 1e-6 <= radial <= 400.0 + 1e-6
        assert abs(pt[1] - 360.0) <= 12.0 + 1e-6
    pg_belt.update(0.016, sim)
    assert pg_belt._particles[0][0] != before_x

    # verify particle group nebula mode respects shifted random region and shimmers
    nebula_region = random([100, 80, 120], [500, 380, 320])
    nebula_region[0] = nebula_region[0] + 20
    pg_nebula = particle_group()
    pg_nebula.mode = "nebula"
    pg_nebula.count = 60
    pg_nebula.position = nebula_region
    pg_nebula.initialize()
    assert len(pg_nebula._particles) == 60
    for pt in pg_nebula._particles:
        assert 120.0 <= pt[0] <= 520.0
        assert 80.0 <= pt[1] <= 380.0
        assert 120.0 <= pt[2] <= 320.0
    phase_before = pg_nebula._phases[0]
    pg_nebula.update(0.016, sim)
    assert pg_nebula._phases[0] > phase_before


def test_headless_simulation_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    # verify full pygame loop runs headlessly across all primitives and exits cleanly
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("VEKTOR_MAX_FRAMES", "5")

    sim = Simulation()
    sim.name = "headless smoke"
    sim.duration = 10.0
    sim.width = 640
    sim.height = 360
    sim.star_count = 40
    sim.camera_position = [0.0, 0.0, -960.0]
    sim.camera_pitch = 0.22
    sim.spatial_modifiers.append(lambda pt: [pt[0], pt[1], pt[2]])

    primary = star()
    primary.particle_count = 120
    primary.corona_count = 30
    primary.radius = 55
    primary.position = [320, 180]

    world_orbit = orbit()
    world_orbit.center = primary.position
    world_orbit.radius = 150

    world = planet()
    world.particle_count = 80
    world.radius = 24
    world.polar_caps = True
    world.orbit = world_orbit

    world_rings = rings()
    world_rings.inner_radius = 36
    world_rings.outer_radius = 58
    world_rings.gap_inner = 46
    world_rings.gap_outer = 49
    world_rings.particle_count = 60
    world.rings = world_rings

    moon_orbit = orbit()
    moon_orbit.radius = 48
    moon_orbit.show_trail = False

    moon = satellite()
    moon.particle_count = 30
    moon.parent = world
    moon.orbit = moon_orbit

    belt = particle_group()
    belt.mode = "belt"
    belt.center = primary.position
    belt.inner_radius = 190
    belt.outer_radius = 220
    belt.count = 40

    nebula = particle_group()
    nebula.mode = "nebula"
    nebula.count = 40
    nebula.position = random([40, 40, 80], [600, 320, 260])
    nebula.position[0] = nebula.position[0] + 20

    simulate(sim.duration)
    assert sim.frame_count == 5

    # verify simulate(sim) and simulate() call conventions
    simulate(sim)
    assert sim.frame_count == 5

    simulate()
    assert sim.frame_count == 5
