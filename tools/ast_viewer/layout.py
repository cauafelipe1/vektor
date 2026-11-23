# top-down tree layout: measure subtree widths, then assign centered x/y positions

from __future__ import annotations

from dataclasses import dataclass

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
# minimum box size; actual width grows with label length at layout time via char estimate
CHAR_WIDTH = 8.5
BOX_PAD_X = 16.0
BOX_HEIGHT = 32.0


def _box_width(label: str) -> float:
    # estimate node box width from label length
    return max(72.0, len(label) * CHAR_WIDTH + BOX_PAD_X * 2)


def _measure(node: AstTreeNode) -> tuple[float, float]:
    # return (subtree_width, box_width) for this node
    box_w = _box_width(node.label)
    if not node.children:
        return box_w, box_w
    child_widths = [_measure(child)[0] for child in node.children]
    children_span = sum(child_widths) + H_GAP * (len(child_widths) - 1)
    return max(box_w, children_span), box_w


def _place(node: AstTreeNode, left: float, top: float) -> LayoutNode:
    # assign positions so children are centered under the parent
    subtree_w, box_w = _measure(node)
    box_h = BOX_HEIGHT
    center_x = left + subtree_w / 2.0
    x = center_x - box_w / 2.0
    y = top

    child_layouts: list[LayoutNode] = []
    if node.children:
        child_left = left + (subtree_w - (
            sum(_measure(c)[0] for c in node.children)
            + H_GAP * (len(node.children) - 1)
        )) / 2.0
        cursor = child_left
        for child in node.children:
            child_span, _ = _measure(child)
            child_layouts.append(_place(child, cursor, top + box_h + V_GAP))
            cursor += child_span + H_GAP

    return LayoutNode(
        tree=node,
        x=x,
        y=y,
        width=box_w,
        height=box_h,
        children=child_layouts,
    )


def layout_tree(root: AstTreeNode) -> LayoutNode:
    # produce a fully positioned layout tree rooted at (0, 0)
    return _place(root, 0.0, 0.0)


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
