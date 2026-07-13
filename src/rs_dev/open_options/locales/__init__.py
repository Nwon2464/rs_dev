"""Locale catalog generation."""

from .japanese import build_japanese_catalog
from .korean import build_korean_catalog

__all__ = ["build_japanese_catalog", "build_korean_catalog"]
