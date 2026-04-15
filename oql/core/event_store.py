# oql/oql/core/event_store.py
"""
EventStore re-exported from oqlos.shared.event_store.
oqlos is the authoritative source; this module exists for backward compatibility.

Usage:
    from oql.core.event_store import DslEventStore

    store = DslEventStore()                          # in-memory
    store = DslEventStore(persist_path="events.json") # with persistence
"""

from oqlos.shared.event_store import EventStore as DslEventStore  # noqa: F401

__all__ = ["DslEventStore"]
