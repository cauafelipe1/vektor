# end-to-end headless cli integration tests for the full vektor pipeline

import os
from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parent.parent
COMPILER_BIN = REPO_ROOT / "compiler" / "vektor"
MANDATORY_PREAMBLE = (
    "from library import Simulation, planet, star, satellite, particle_group, "
    "rings, orbit, random, simulate\n\n"
    "sim = Simulation()\n"
)


def run_headless_cli(example_rel_path: str) -> subprocess.CompletedProcess[str]:
    # invoke ./compiler/vektor under dummy sdl drivers capped at 10 frames
    env = os.environ.copy()
    env["SDL_VIDEODRIVER"] = "dummy"
    env["SDL_AUDIODRIVER"] = "dummy"
    env["VEKTOR_MAX_FRAMES"] = "10"
    return subprocess.run(
        [str(COMPILER_BIN), example_rel_path],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_e2e_solar_system_headless() -> None:
    # verify full transpilation and headless pygame execution for solar_system.vk
    result = run_headless_cli("examples/solar_system.vk")
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"

    generated = REPO_ROOT / "output" / "solar_system.py"
    assert generated.is_file()
    content = generated.read_text(encoding="utf-8")
    assert content.startswith(MANDATORY_PREAMBLE)


def test_e2e_deep_space_orbit_headless() -> None:
    # verify full transpilation and headless pygame execution for deep_space_orbit.vk
    result = run_headless_cli("examples/deep_space_orbit.vk")
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"

    generated = REPO_ROOT / "output" / "deep_space_orbit.py"
    assert generated.is_file()
    content = generated.read_text(encoding="utf-8")
    assert content.startswith(MANDATORY_PREAMBLE)
