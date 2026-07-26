"""
Jarvis OS — FastAPI Dependencies.

Provides shared dependencies like the global Brain instance,
avoiding circular imports between app.py and routes.
"""

from __future__ import annotations

from jarvis.brain.jarvis_brain import JarvisBrain

# Global brain instance (lives for the server's lifetime)
_brain: JarvisBrain | None = None

def get_brain() -> JarvisBrain:
    """Return the global brain instance."""
    if _brain is None:
        raise RuntimeError("Jarvis brain not initialized — server not started?")
    return _brain

def set_brain(brain_instance: JarvisBrain) -> None:
    """Set the global brain instance."""
    global _brain
    _brain = brain_instance
