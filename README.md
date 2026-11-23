# Vektor

**Vektor** is a source-to-source compiler (transpiler) and 3D space simulation runtime for the `.vk` domain-specific language (DSL). It compiles `.vk` scripts through a C11 Flex/Bison front-end and decoupled AST back-end into clean Python 3 code executed on a modular Pygame-CE 3D particle renderer.

## Compilation and Execution Pipeline

```text
source.vk
  │
  ▼
Flex Lexer (compiler/src/frontend/lexer.l)
  │  tokenizes literals, identifiers, operators; strips % comments; tracks yylineno
  ▼
Bison LALR(1) Parser (compiler/src/frontend/parser.y)
  │  validates grammar with declarative precedence (0 conflicts) and builds the AST
  ▼
C11 AST (compiler/include/ast.h, compiler/src/ir/ast.c)
  │  structured intermediate representation supporting --dump-ast viewer / text dump
  ▼
Python 3 Codegen (compiler/include/codegen.h, compiler/src/backend/codegen.c)
  │  emits Python 3 source into output/<name>.py (header injection, ^ -> **, 0-based indexing)
  ▼
Pygame-CE 3D Particle Runtime (library/)
     runs the 60 FPS simulation with decoupled Camera3D projection and per-particle Z-sorting
```

## Repository Structure

```text
vektor/
├── compiler/
│   ├── Makefile                # builds compiler/vektor into build/ intermediates
│   ├── include/
│   │   ├── ast.h               # ast node types, constructors, ast_dump, ast_dump_json, ast_free
│   │   └── codegen.h           # python emitter interface
│   └── src/
│       ├── frontend/
│       │   ├── lexer.l         # flex lexical analyzer
│       │   └── parser.y        # bison lalr(1) grammar
│       ├── ir/
│       │   └── ast.c           # ast construction, dumping, and recursive cleanup
│       ├── backend/
│       │   └── codegen.c       # ast traversal and python 3 emission
│       └── cli/
│           └── main.c          # cli driver, ast viewer launcher, and uv runtime launcher
├── tools/
│   └── ast_viewer/             # interactive pygame ast tree viewer (zoom/pan; separate from simulation)
├── library/
│   ├── __init__.py             # public dsl exports (9 symbols)
│   ├── core/
│   │   ├── constants.py        # 1280x720 defaults, camera defaults, cosmic palettes
│   │   └── simulation.py       # simulation state, 60 fps loop, hud, simulate()
│   ├── rendering/
│   │   ├── camera.py           # decoupled camera3d with euler orientation and projection
│   │   ├── projection.py       # 3d math, rotations, spherical sampling, depth shading
│   │   └── renderer.py         # particle renderer with per-particle painter z-sorting
│   ├── entities/
│   │   ├── base.py             # celestial entity and point-cloud sphere bases
│   │   ├── star.py             # star entity and star() factory
│   │   ├── planet.py           # planet entity and planet() factory
│   │   ├── satellite.py        # satellite entity and satellite() factory
│   │   ├── rings.py            # rings entity and rings() factory
│   │   ├── orbit.py            # orbit entity and orbit() factory
│   │   ├── particle_group.py   # particle group entity and particle_group() factory
│   │   └── random_region.py    # random region and random() helper
│   └── environment/
│       └── starfield.py        # multi-depth twinkling 3d background starfield
├── examples/
│   ├── solar_system.vk         # multi-planet 3d solar system with asteroid belt and rings
│   └── deep_space_orbit.vk     # tilted exoplanet orbit inside a volumetric 3d nebula
├── tests/
│   ├── test_compiler.py        # lexer, parser, ast dump, and codegen tests
│   ├── test_runtime.py         # 3d camera, z-sorting renderer, and entity tests
│   └── test_e2e.py             # end-to-end headless compilation and simulation tests
├── output/                     # generated python scripts (ignored by git)
└── pyproject.toml              # python >= 3.13 project and uv dependencies
```

## Prerequisites and Installation

### Requirements
- `gcc` (C11 support)
- `flex`
- `bison` (GNU Bison)
- `uv`
- Python `>= 3.13`

### Build and Environment Setup

```bash
# build the C compiler binary (compiler/vektor)
make -C compiler

# install Python runtime and dev dependencies
uv sync
```

## Usage and CLI Options

Compile and run a `.vk` simulation directly:

```bash
./compiler/vektor examples/solar_system.vk
./compiler/vektor examples/deep_space_orbit.vk
```

### CLI Options

```text
vektor [--emit-only] [--dump-ast] [--dump-ast-text] [-o <output.py>] [-h|--help] <input.vk>
```

| Option | Description |
| :--- | :--- |
| `--emit-only` | Transpile the `.vk` input into Python without launching the simulation runtime. |
| `--dump-ast` | Open an interactive Pygame AST tree viewer (zoom/pan). When used alone, exits without writing `.py` or launching the simulation. Combined with `--emit-only`/`-o`, prints the textual AST to `stdout` then continues. |
| `--dump-ast-text` | Print the parsed Abstract Syntax Tree to `stdout` (useful for CI/scripts). When used alone, exits without writing `.py`. |
| `-o <output.py>` | Write the generated Python script to an explicit path instead of `output/<stem>.py`. |
| `-h`, `--help` | Display usage instructions and exit. |

Examples:

```bash
# open the interactive AST viewer (scroll to zoom, drag to pan)
./compiler/vektor --dump-ast examples/solar_system.vk

# print the textual AST without generating Python or opening a window
./compiler/vektor --dump-ast-text examples/solar_system.vk

# emit Python code only
./compiler/vektor --emit-only -o output/solar_system.py examples/solar_system.vk
```

## Vektor DSL Reference (`.vk`)

### Syntax Highlights
- **Comments:** Single-line comments begin with `%` and extend to the end of the line.
- **Statements:** Every statement terminates with `;`.
- **Literals:** Integers, decimals, scientific notation (`5.972e24`), double-quoted strings, and lowercase booleans (`true`, `false`).
- **Vectors and Indexing:** Square-bracket vectors (`[x, y]` or `[x, y, z]`) use **native 0-based indexing** (`vec[0]`, `vec[1]`, `vec[2]`).
- **Operators:** Arithmetic (`+`, `-`, `*`, `/`), right-associative exponentiation (`^`, higher precedence than unary `-`), and relational comparisons (`<`, `>`, `<=`, `>=`, `==`, `!=`).

### Example Script

```matlab
% configure global simulation state and 3d camera
sim.name = "Orbital Demo";
sim.duration = 60;
sim.camera_position = [0, 0, -1080];
sim.camera_pitch = 0.22;

% create a primary star and an orbiting ringed planet
central_star = star();
central_star.position = [640, 360, 0];
central_star.radius = 68;

world = planet();
world.radius = 32;
world.polar_caps = true;

world_orbit = orbit();
world_orbit.center = [640, 360, 0];
world_orbit.radius = 16 ^ 2 + 14;
world_orbit.inclination = 0.15;
world.orbit = world_orbit;

world_rings = rings();
world_rings.inner_radius = 48;
world_rings.outer_radius = 84;
world_rings.gap_inner = 64;
world_rings.gap_outer = 69;
world.rings = world_rings;

% launch simulation
simulate(sim.duration);
```

### Built-in Primitives

| Primitive | Key Configurable Attributes |
| :--- | :--- |
| `sim` | Pre-initialized `Simulation` instance: `name`, `duration`, `gravity`, `width` (`1280`), `height` (`720`), `star_count`, `camera_position`, `camera_yaw`, `camera_pitch`, `camera_roll`. |
| `star()` | Luminous 3D point-cloud star with outer corona: `mass`, `radius`, `position`, `color`, `secondary_color`, `color_variation`, `particle_count`, `corona_count`, `turbulence`, `luminosity`. |
| `planet()` | Rotating 3D point-cloud planet: `mass`, `radius`, `position`, `velocity`, `color`, `secondary_color`, `color_variation`, `polar_caps`, `particle_count`, `spin_speed`, `rings`, `orbit`. |
| `satellite()` | Compact moon/satellite body: `mass`, `radius`, `position`, `color`, `secondary_color`, `color_variation`, `particle_count`, `spin_speed`, `parent`, `orbit`. |
| `rings()` | Tilted 3D concentric particle rings with optional gap: `inner_radius`, `outer_radius`, `gap_inner`, `gap_outer`, `tilt`, `color`, `secondary_color`, `color_variation`, `particle_count`, `spin_speed`, `position`, `target`. |
| `orbit()` | 3D elliptical trajectory and optional dotted trail: `center`, `radius`, `eccentricity`, `inclination`, `speed`, `color`, `show_trail`. |
| `particle_group()` | 3D particle system supporting `"cloud"`, `"belt"`, and `"nebula"` modes: `mode`, `count`, `mass`, `total_mass`, `position`, `center`, `velocity`, `color`, `secondary_color`, `color_variation`, `spread`, `inner_radius`, `outer_radius`, `thickness`, `angular_speed`. |
| `random(low, high)` | Uniform float between scalars, or a mutable 0-based `RandomRegion` bounding box when given 2D/3D vectors. |
| `simulate(target)` | Launches the 60 FPS simulation window; accepts a duration (`sim.duration`), a `Simulation` instance (`sim`), or no arguments. |

## Running Tests

Run the full compiler, runtime, and headless end-to-end test suite via `uv` and `pytest`:

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run pytest -v
```
