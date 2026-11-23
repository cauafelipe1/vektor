# top-down tree layout: measure subtree widths with font metrics, center children

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from tools.ast_viewer.model import AstTreeNode


@dataclass
class LayoutNode:
    """a tree node with computed screen-space geometry."""

    tree: AstTreeNode
    x: float
    y: float
    width: float
    height: float
    children: list[LayoutNode]


# horizontal gap between sibling subtrees and vertical gap between levels
H_GAP = 28.0
V_GAP = 64.0
BOX_PAD_X = 14.0
BOX_PAD_Y = 8.0

SizeFn = Callable[[str], tuple[float, float]]


def display_label(node: AstTreeNode) -> str:
    # same label used for measuring boxes and for drawing
    label = node.label
    if node.lineno > 0 and node.type_name in {"ASSIGN", "EXPR_STMT"}:
        return f"{label}  L{node.lineno}"
    return label


def _box_size(size_fn: SizeFn, label: str) -> tuple[float, float]:
    # pad around the exact text metrics from the font
    text_w, text_h = size_fn(label)
    return text_w + BOX_PAD_X * 2, text_h + BOX_PAD_Y * 2


def _measure(node: AstTreeNode, size_fn: SizeFn) -> tuple[float, float, float]:
    # return (subtree_width, box_width, box_height) for this node
    box_w, box_h = _box_size(size_fn, display_label(node))
    if not node.children:
        return box_w, box_w, box_h
    child_widths = [_measure(child, size_fn)[0] for child in node.children]
    children_span = sum(child_widths) + H_GAP * (len(child_widths) - 1)
    return max(box_w, children_span), box_w, box_h


def _place(node: AstTreeNode, left: float, top: float, size_fn: SizeFn) -> LayoutNode:
    # assign positions so children are centered under the parent
    subtree_w, box_w, box_h = _measure(node, size_fn)
    center_x = left + subtree_w / 2.0
    x = center_x - box_w / 2.0
    y = top

    child_layouts: list[LayoutNode] = []
    if node.children:
        child_spans = [_measure(c, size_fn)[0] for c in node.children]
        children_span = sum(child_spans) + H_GAP * (len(child_spans) - 1)
        child_left = left + (subtree_w - children_span) / 2.0
        cursor = child_left
        for child, child_span in zip(node.children, child_spans, strict=True):
            child_layouts.append(_place(child, cursor, top + box_h + V_GAP, size_fn))
            cursor += child_span + H_GAP

    return LayoutNode(
        tree=node,
        x=x,
        y=y,
        width=box_w,
        height=box_h,
        children=child_layouts,
    )


def layout_tree(root: AstTreeNode, size_fn: SizeFn) -> LayoutNode:
    # produce a fully positioned layout tree rooted at (0, 0)
    return _place(root, 0.0, 0.0, size_fn)


def iter_layout_nodes(node: LayoutNode):
    # depth-first walk of layout nodes
    yield node
    for child in node.children:
        yield from iter_layout_nodes(child)


def layout_bounds(root: LayoutNode) -> tuple[float, float, float, float]:
    # return (min_x, min_y, max_x, max_y) covering all boxes
    min_x = root.x
    min_y = root.y
    max_x = root.x + root.width
    max_y = root.y + root.height
    for node in iter_layout_nodes(root):
        min_x = min(min_x, node.x)
        min_y = min(min_y, node.y)
        max_x = max(max_x, node.x + node.width)
        max_y = max(max_y, node.y + node.height)
    return min_x, min_y, max_x, max_y
