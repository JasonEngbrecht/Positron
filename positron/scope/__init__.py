"""Scope communication and acquisition modules."""

from .connection import (
    ScopeConnection,
    ScopeInfo,
    detect_and_connect,
    disconnect,
    is_connected,
    get_scope_info,
    get_connection,
)

__all__ = [
    "ScopeConnection",
    "ScopeInfo",
    "detect_and_connect",
    "disconnect",
    "is_connected",
    "get_scope_info",
    "get_connection",
]
