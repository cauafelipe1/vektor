# pygame window for browsing a laid-out ast tree with zoom and pan

from __future__ import annotations

import argparse
import json
import os
import sys

import pygame

from tools.ast_viewer.layout import (
    LayoutNode,
    display_label,
    iter_layout_nodes,
    layout_bounds,
    layout_tree,
)
from tools.ast_viewer.model import AstTreeNode, load_ast_json


WINDOW_SIZE = (1280, 720)
BG_COLOR = (18, 22, 28)
NODE_FILL = (36, 48, 64)
NODE_BORDER = (120, 170, 220)
EDGE_COLOR = (90, 110, 140)
TEXT_COLOR = (230, 235, 240)
HINT_COLOR = (150, 160, 175)
ROOT_FILL = (48, 72, 56)
BOX_PAD_X = 14
BOX_PAD_Y = 8


def _read_max_frames() -> int | None:
    # optional headless smoke: exit after n frames when VEKTOR_MAX_FRAMES is set
    raw = os.environ.get("VEKTOR_MAX_FRAMES")
    if raw is None or raw.strip() == "":
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value >= 0 else None


def _draw_tree(
    surface: pygame.Surface,
    font: pygame.font.Font,
    root: LayoutNode,
    offset_x: float,
    offset_y: float,
    scale: float,
) -> None:
    # draw edges using layout centers, then boxes sized from rendered text
    for node in iter_layout_nodes(root):
        parent_cx = offset_x + (node.x + node.width / 2.0) * scale
        parent_by = offset_y + (node.y + node.height) * scale
        for child in node.children:
            child_cx = offset_x + (child.x + child.width / 2.0) * scale
            child_ty = offset_y + child.y * scale
            pygame.draw.aaline(
                surface,
                EDGE_COLOR,
                (int(parent_cx), int(parent_by)),
                (int(child_cx), int(child_ty)),
                max(1, int(1.5 * scale)),
            )

    for node in iter_layout_nodes(root):
        label = display_label(node.tree)
        text_surf = font.render(label, True, TEXT_COLOR)
        text_w = text_surf.get_width()
        text_h = text_surf.get_height()

        # box follows the exact text rect, then scales with the camera
        box_w = (text_w + BOX_PAD_X * 2) * scale
        box_h = (text_h + BOX_PAD_Y * 2) * scale
        center_x = offset_x + (node.x + node.width / 2.0) * scale
        center_y = offset_y + (node.y + node.height / 2.0) * scale
        rect = pygame.Rect(0, 0, max(1, int(box_w)), max(1, int(box_h)))
        rect.center = (int(center_x), int(center_y))

        fill = ROOT_FILL if node.tree.type_name == "PROGRAM" else NODE_FILL
        pygame.draw.rect(surface, fill, rect, border_radius=max(2, int(4 * scale)))
        pygame.draw.rect(
            surface,
            NODE_BORDER,
            rect,
            width=max(1, int(1.5 * scale)),
            border_radius=max(2, int(4 * scale)),
        )

        # skip labels when zoomed out too far to remain readable
        if scale < 0.35:
            continue
        if abs(scale - 1.0) > 0.05:
            tw = max(1, int(text_w * scale))
            th = max(1, int(text_h * scale))
            text_surf = pygame.transform.smoothscale(text_surf, (tw, th))
        text_rect = text_surf.get_rect(center=rect.center)
        surface.blit(text_surf, text_rect)


def run_viewer(root: AstTreeNode) -> int:
    # open an interactive window for the given ast tree; return process exit code
    pygame.init()
    pygame.display.set_caption("Vektor AST")
    screen = pygame.display.set_mode(WINDOW_SIZE)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("dejavusans", 16)
    hint_font = pygame.font.SysFont("dejavusans", 14)

    def size_fn(text: str) -> tuple[float, float]:
        # pygame font.size returns the pixel rect the label will occupy
        w, h = font.size(text)
        return float(w), float(h)

    layout = layout_tree(root, size_fn)
    min_x, min_y, max_x, max_y = layout_bounds(layout)
    tree_w = max(1.0, max_x - min_x)
    tree_h = max(1.0, max_y - min_y)

    # initial fit with padding
    pad = 80.0
    scale = min(
        (WINDOW_SIZE[0] - pad * 2) / tree_w,
        (WINDOW_SIZE[1] - pad * 2) / tree_h,
        1.25,
    )
    scale = max(0.12, scale)
    offset_x = (WINDOW_SIZE[0] - tree_w * scale) / 2.0 - min_x * scale
    offset_y = max(24.0, (WINDOW_SIZE[1] - tree_h * scale) / 2.0 - min_y * scale)

    dragging = False
    last_mouse = (0, 0)
    max_frames = _read_max_frames()
    frame_count = 0
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button in (1, 2):
                    dragging = True
                    last_mouse = event.pos
                elif event.button == 4:
                    mx, my = event.pos
                    old = scale
                    scale = min(4.0, scale * 1.12)
                    offset_x = mx - (mx - offset_x) * (scale / old)
                    offset_y = my - (my - offset_y) * (scale / old)
                elif event.button == 5:
                    mx, my = event.pos
                    old = scale
                    scale = max(0.08, scale / 1.12)
                    offset_x = mx - (mx - offset_x) * (scale / old)
                    offset_y = my - (my - offset_y) * (scale / old)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button in (1, 2):
                    dragging = False
            elif event.type == pygame.MOUSEMOTION and dragging:
                mx, my = event.pos
                dx = mx - last_mouse[0]
                dy = my - last_mouse[1]
                offset_x += dx
                offset_y += dy
                last_mouse = (mx, my)
            elif event.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                old = scale
                factor = 1.12 if event.y > 0 else (1.0 / 1.12)
                scale = min(4.0, max(0.08, scale * factor))
                offset_x = mx - (mx - offset_x) * (scale / old)
                offset_y = my - (my - offset_y) * (scale / old)

        screen.fill(BG_COLOR)
        _draw_tree(screen, font, layout, offset_x, offset_y, scale)

        hint = hint_font.render(
            "scroll: zoom  |  drag: pan  |  esc/q: quit",
            True,
            HINT_COLOR,
        )
        screen.blit(hint, (12, WINDOW_SIZE[1] - 28))

        pygame.display.flip()
        clock.tick(60)

        frame_count += 1
        if max_frames is not None and frame_count >= max_frames:
            running = False

    pygame.quit()
    return 0


def main(argv: list[str] | None = None) -> int:
    # cli entry used by __main__
    parser = argparse.ArgumentParser(description="interactive vektor ast viewer")
    parser.add_argument("--json", required=True, help="path to ast json from the compiler")
    args = parser.parse_args(argv)
    try:
        tree = load_ast_json(args.json)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[Vektor AST Viewer] failed to load json: {exc}", file=sys.stderr)
        return 1
    return run_viewer(tree)
