"""Shared locale-template analysis and rendering."""

from .placeholders import placeholder_indices, title_template
from .render import render_template

__all__ = ["placeholder_indices", "render_template", "title_template"]
