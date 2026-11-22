# automated compiler transpilation, ast dump, and cli tests for the vektor c transpiler

import ast
from pathlib import Path
import runpy
import subprocess

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
COMPILER_BIN = REPO_ROOT / "compiler" / "vektor"
SOLAR_SYSTEM_VK = REPO_ROOT / "examples" / "solar_system.vk"
MANDATORY_PREAMBLE = (
    "from library import Simulation, planet, star, satellite, particle_group, "
    "rings, orbit, random, simulate\n\n"
    "sim = Simulation()\n"
)

GOLDEN_SNIPPET_VK = (
    "% deterministic golden snippet\n"
    'sim.name = "Solar System";\n'
    "sim.duration = 120;\n"
    "sim.gravity = 9.81;\n"
    "primary_star = star();\n"
    "primary_star.mass = 1.989e30;\n"
    "primary_star.radius = 68;\n"
    "primary_star.position = [640, 360, 0];\n"
    "earth = planet();\n"
    "earth.mass = 5.972e24;\n"
    "earth.radius = 26;\n"
    "earth.position = [910, 360, 0];\n"
    "earth_rings = rings();\n"
    "earth_rings.inner_radius = 56;\n"
    "earth_rings.outer_radius = 98;\n"
    "earth.rings = earth_rings;\n"
    "dust = particle_group();\n"
    "dust.count = 360;\n"
    "dust.mass = 0.5;\n"
    "dust.position = random([0, 0], [1280, 720]);\n"
    "dust.total_mass = dust.count * dust.mass;\n"
    "dust.position[0] = dust.position[0] + 20;\n"
    "simulate(sim.duration);\n"
)

GOLDEN_SNIPPET_PY = (
    MANDATORY_PREAMBLE
    + 'sim.name = "Solar System"\n'
    + "sim.duration = 120\n"
    + "sim.gravity = 9.81\n"
    + "primary_star = star()\n"
    + "primary_star.mass = 1.989e30\n"
    + "primary_star.radius = 68\n"
    + "primary_star.position = [640, 360, 0]\n"
    + "earth = planet()\n"
    + "earth.mass = 5.972e24\n"
    + "earth.radius = 26\n"
    + "earth.position = [910, 360, 0]\n"
    + "earth_rings = rings()\n"
    + "earth_rings.inner_radius = 56\n"
    + "earth_rings.outer_radius = 98\n"
    + "earth.rings = earth_rings\n"
    + "dust = particle_group()\n"
    + "dust.count = 360\n"
    + "dust.mass = 0.5\n"
    + "dust.position = random([0, 0], [1280, 720])\n"
    + "dust.total_mass = dust.count * dust.mass\n"
    + "dust.position[0] = dust.position[0] + 20\n"
    + "simulate(sim.duration)\n"
)


def run_compiler(args: list[str], cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    # invoke the compiled vektor binary in the specified working directory
    return subprocess.run(
        [str(COMPILER_BIN), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def test_solar_system_transpilation_invariants(tmp_path: Path) -> None:
    # verify examples/solar_system.vk emits valid, clean python with mandatory preamble
    out_file = tmp_path / "solar_system.py"
    result = run_compiler(["--emit-only", "-o", str(out_file), str(SOLAR_SYSTEM_VK)])
    assert result.returncode == 0, result.stderr

    emitted = out_file.read_text(encoding="utf-8")
    assert emitted.startswith(MANDATORY_PREAMBLE)
    assert "import pygame" not in emitted
    assert "belt.center[2] = 0\n" in emitted
    assert "- 1" not in emitted
    for line in emitted.splitlines():
        assert not line.rstrip().endswith(";")
    ast.parse(emitted)


def test_golden_deterministic_emission(tmp_path: Path) -> None:
    # verify exact byte-for-byte emission of scientific notation, calls, vectors, and indexing
    src_file = tmp_path / "golden.vk"
    out_file = tmp_path / "golden.py"
    src_file.write_text(GOLDEN_SNIPPET_VK, encoding="utf-8")

    result = run_compiler(["--emit-only", "-o", str(out_file), str(src_file)])
    assert result.returncode == 0, result.stderr

    emitted = out_file.read_text(encoding="utf-8")
    assert emitted == GOLDEN_SNIPPET_PY
    assert "import pygame" not in emitted
    for line in emitted.splitlines():
        assert not line.rstrip().endswith(";")
    ast.parse(emitted)


def test_dump_ast_standalone_without_output_or_runtime(tmp_path: Path) -> None:
    # verify standalone --dump-ast prints hierarchical ast nodes without emitting or running python
    result = run_compiler(["--dump-ast", str(SOLAR_SYSTEM_VK)], cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    for token in ("PROGRAM", "ASSIGN", "CALL", "ATTR", "VECTOR", "INDEX", "BINOP", "BOOL"):
        assert token in result.stdout
    assert not (tmp_path / "output").exists()


def test_dump_ast_combined_with_emit_only(tmp_path: Path) -> None:
    # verify --dump-ast combined with --emit-only -o prints ast and writes valid python output
    out_file = tmp_path / "dumped_solar.py"
    result = run_compiler(
        ["--dump-ast", "--emit-only", "-o", str(out_file), str(SOLAR_SYSTEM_VK)]
    )
    assert result.returncode == 0, result.stderr
    for token in ("PROGRAM", "ASSIGN", "CALL", "ATTR", "VECTOR"):
        assert token in result.stdout

    assert out_file.is_file()
    emitted = out_file.read_text(encoding="utf-8")
    assert emitted.startswith(MANDATORY_PREAMBLE)
    ast.parse(emitted)


def test_native_zero_based_indexing_parity(tmp_path: Path) -> None:
    # verify 0-based index access is emitted 1:1 without subtracting 1
    src_file = tmp_path / "indexing.vk"
    out_file = tmp_path / "indexing.py"
    src_file.write_text(
        "vec = [10, 20, 30];\n"
        "vec[0] = vec[0] + 5;\n"
        "first = vec[0];\n",
        encoding="utf-8",
    )

    result = run_compiler(["--emit-only", "-o", str(out_file), str(src_file)])
    assert result.returncode == 0, result.stderr

    emitted = out_file.read_text(encoding="utf-8")
    assert "vec[0] = vec[0] + 5\n" in emitted
    assert "first = vec[0]\n" in emitted
    assert "- 1" not in emitted

    ns = runpy.run_path(str(out_file))
    assert ns["vec"] == [15, 20, 30]
    assert ns["first"] == 15


def test_exponentiation_and_operator_precedence(tmp_path: Path) -> None:
    # verify right-associative ^ -> ** translation and unary minus precedence
    src_file = tmp_path / "precedence.vk"
    out_file = tmp_path / "precedence.py"
    src_file.write_text(
        "a = 2 ^ 3 ^ 2;\n"
        "b = -2 ^ 2;\n"
        "c = (-2) ^ 2;\n"
        "d = (2 ^ 3) ^ 2;\n"
        "e = 10 - 3 - 2;\n"
        "f = 10 - (3 - 2);\n",
        encoding="utf-8",
    )

    result = run_compiler(["--emit-only", "-o", str(out_file), str(src_file)])
    assert result.returncode == 0, result.stderr

    emitted = out_file.read_text(encoding="utf-8")
    assert "^" not in emitted
    assert "**" in emitted

    ns = runpy.run_path(str(out_file))
    assert ns["a"] == 512
    assert ns["b"] == -4
    assert ns["c"] == 4
    assert ns["d"] == 64
    assert ns["e"] == 5
    assert ns["f"] == 9


def test_booleans_empty_vectors_zero_arg_calls_and_relational_ops(tmp_path: Path) -> None:
    # verify boolean literals, empty vectors, zero-arg calls, and relational parenthesization
    src_file = tmp_path / "features.vk"
    out_file = tmp_path / "features.py"
    src_file.write_text(
        "flag_on = true;\n"
        "flag_off = false;\n"
        "empty_vec = [];\n"
        "obj = planet();\n"
        "lt_res = 1 < 2;\n"
        "gt_res = 3 > 2;\n"
        "le_res = 2 <= 2;\n"
        "ge_res = 3 >= 2;\n"
        "eq_res = 4 == 4;\n"
        "ne_res = 4 != 5;\n"
        "chained = 1 < 2 < 3;\n"
        "chained_false = 2 < 1 < 2;\n",
        encoding="utf-8",
    )

    result = run_compiler(["--emit-only", "-o", str(out_file), str(src_file)])
    assert result.returncode == 0, result.stderr

    emitted = out_file.read_text(encoding="utf-8")
    assert "flag_on = True\n" in emitted
    assert "flag_off = False\n" in emitted
    assert "empty_vec = []\n" in emitted
    assert "obj = planet()\n" in emitted
    assert "chained = (1 < 2) < 3\n" in emitted
    assert "chained_false = (2 < 1) < 2\n" in emitted

    ns = runpy.run_path(str(out_file))
    assert ns["flag_on"] is True
    assert ns["flag_off"] is False
    assert ns["empty_vec"] == []
    assert ns["obj"] is not None
    assert ns["lt_res"] is True
    assert ns["gt_res"] is True
    assert ns["le_res"] is True
    assert ns["ge_res"] is True
    assert ns["eq_res"] is True
    assert ns["ne_res"] is True
    assert ns["chained"] is True
    # verify left-associative (2 < 1) < 2 evaluates to (False < 2) == True, not python chained false
    assert ns["chained_false"] is True


def test_negative_syntax_error_reports_line_and_skips_output(tmp_path: Path) -> None:
    # verify missing semicolon reports line 2 syntax error without creating output file
    src_file = tmp_path / "bad_syntax.vk"
    out_file = tmp_path / "should_not_exist.py"
    src_file.write_text('sim.name = "bad"\nearth = planet();\n', encoding="utf-8")

    result = run_compiler(["--emit-only", "-o", str(out_file), str(src_file)])
    assert result.returncode != 0
    assert "[Vektor Syntax Error] Line 2:" in result.stderr
    assert not out_file.exists()


def test_negative_lexical_error_reports_line_and_skips_output(tmp_path: Path) -> None:
    # verify unexpected @ on line 3 reports lexical error without creating output file
    src_file = tmp_path / "bad_lex.vk"
    out_file = tmp_path / "should_not_exist_lex.py"
    src_file.write_text(
        'sim.name = "ok";\n'
        "earth = planet();\n"
        "earth.mass = @5;\n",
        encoding="utf-8",
    )

    result = run_compiler(["--emit-only", "-o", str(out_file), str(src_file)])
    assert result.returncode != 0
    assert "[Vektor Lexical Error] Line 3: unexpected character '@'" in result.stderr
    assert not out_file.exists()


def test_negative_unterminated_string_reports_line_and_skips_output(tmp_path: Path) -> None:
    # verify unterminated string literal reports line 1 lexical error without creating output file
    src_file = tmp_path / "unterminated.vk"
    out_file = tmp_path / "should_not_exist_str.py"
    src_file.write_text('sim.name = "unterminated\n', encoding="utf-8")

    result = run_compiler(["--emit-only", "-o", str(out_file), str(src_file)])
    assert result.returncode != 0
    assert "[Vektor Lexical Error] Line 1: unterminated string literal" in result.stderr
    assert not out_file.exists()


@pytest.mark.parametrize(
    "cli_args",
    [
        [],
        ["--emit-only"],
        ["--unknown-flag", "examples/solar_system.vk"],
        ["--emit-only", "-o"],
        ["--emit-only", "nonexistent_file_for_test.vk"],
    ],
)
def test_cli_argument_validation_errors(cli_args: list[str]) -> None:
    # verify invalid cli invocations fail cleanly with non-zero exit code
    result = run_compiler(cli_args)
    assert result.returncode != 0
    assert result.stderr.strip() != ""


def test_cli_help_flag() -> None:
    # verify -h and --help exit cleanly with usage text advertising --dump-ast
    for flag in ("-h", "--help"):
        result = run_compiler([flag])
        assert result.returncode == 0
        assert "usage:" in result.stdout
        assert "--dump-ast" in result.stdout
        assert "--emit-only" in result.stdout
