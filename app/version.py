"""Single source of truth for the application version.

Everything else (config, health endpoint, OpenAPI metadata, Docker labels)
imports ``__version__`` from here so the number can never drift.
"""

from __future__ import annotations

__version__ = "3.0.0"
