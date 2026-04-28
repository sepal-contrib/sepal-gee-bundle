"""Bundle-local UI helpers shared across apps.

These are Solara/ipyvuetify components that need state or browser I/O,
so they cannot live in `apps/_commons/` (which is reserved for pure
constants and pure functions).
"""

from .about_dialog import AboutOnceDialog
from .local_storage import LocalStorageBridge

__all__ = ["AboutOnceDialog", "LocalStorageBridge"]
