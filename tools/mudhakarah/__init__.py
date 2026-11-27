"""Mudhakarah build tooling (Phase 1 Architecture Specification).

The package is imported by tools/build.py. It never writes content,
configuration, the ID lock or templates; only the writer stage writes the
generated page to its published path.
"""

TOOL_VERSION = "1.1.0"
