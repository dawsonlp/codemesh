"""Backward compatibility alias forwarding semantic_engine -> codemesh."""

from codemesh import *  # noqa: F401, F403
import codemesh as _codemesh

__all__ = _codemesh.__all__
