# load compiler-emitted ast json into a simple tree of display nodes

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


@dataclass
class AstTreeNode:
    """one display node in the interactive ast tree."""

    type_name: str
    label: str
    lineno: int
    children: list[AstTreeNode] = field(default_factory=list)


def _parse_node(payload: dict[str, Any]) -> AstTreeNode:
    # convert one json object into an AstTreeNode recursively
    children_raw = payload.get("children", [])
    if not isinstance(children_raw, list):
        children_raw = []
    children = [
        _parse_node(child)
        for child in children_raw
        if isinstance(child, dict)
    ]
    return AstTreeNode(
        type_name=str(payload.get("type", "UNKNOWN")),
        label=str(payload.get("label", payload.get("type", "UNKNOWN"))),
        lineno=int(payload.get("lineno", 0) or 0),
        children=children,
    )


def load_ast_json(path: str | Path) -> AstTreeNode:
    # read a json file produced by ast_dump_json and return the root node
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("ast json root must be an object")
    return _parse_node(data)
