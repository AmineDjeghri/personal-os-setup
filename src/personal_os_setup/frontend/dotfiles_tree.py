"""Group chezmoi-managed dotfiles into a nested tree for the "Sync dotfiles" tab.

`chezmoi_managed_paths()` returns a flat list of absolute file paths. This module
groups them by path segment (relative to a root, normally the user's home
directory) so the frontend can render a folder tree with per-folder cascading
selection instead of one long flat list.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class DotfileTreeNode(BaseModel):
    """A single node in the dotfiles tree.

    Leaf nodes (files) have `path` set; directory nodes have `path=None` and
    one or more `children`, keyed by path segment name.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    path: Path | None = None
    children: dict[str, "DotfileTreeNode"] = Field(default_factory=dict)

    @property
    def is_file(self) -> bool:
        """Whether this node represents a file rather than a directory."""
        return self.path is not None

    def all_file_paths(self) -> list[Path]:
        """Return every file path in this node's subtree.

        Returns:
            `[self.path]` if this node is a file, otherwise every file path
            found recursively under its children.
        """
        if self.path is not None:
            return [self.path]
        paths: list[Path] = []
        for child in self.children.values():
            paths.extend(child.all_file_paths())
        return paths


def build_dotfiles_tree(paths: list[Path], root: Path, root_label: str = "~") -> DotfileTreeNode:
    """Group flat absolute file paths into a nested tree relative to a root.

    Args:
        paths: Absolute file paths, e.g. from `chezmoi_managed_paths()`.
        root: The directory paths are grouped relative to (normally `Path.home()`).
        root_label: Display name for the tree's root node.

    Returns:
        The tree's root node; its children are the top-level path segments.
        Paths not under `root` (e.g. a different drive on Windows) fall back to
        being grouped by their full parts instead of raising.
    """
    tree = DotfileTreeNode(name=root_label)
    for p in paths:
        try:
            parts = p.relative_to(root).parts
        except ValueError:
            parts = p.parts
        node = tree
        for i, part in enumerate(parts):
            is_last_part = i == len(parts) - 1
            if part not in node.children:
                node.children[part] = DotfileTreeNode(name=part, path=p if is_last_part else None)
            node = node.children[part]
    return tree
