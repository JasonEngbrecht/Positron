"""
Event storage management for high-rate data acquisition.

Thread-safe storage for up to 10 million events with efficient
memory management and concurrent access support.
"""

import sys
from typing import List, Optional
from PySide6.QtCore import QMutex, QMutexLocker

from positron.processing.pulse import EventData


class EventStorage:
    """
    Thread-safe storage for event data.
    
    Supports concurrent access from acquisition thread (writes) and
    UI/analysis threads (reads). Uses Python list with mutex protection.
    
    Current implementation: ~750 bytes per event
    Default capacity: 1M events = ~700 MB memory
    
    Note: Future optimization to NumPy structured arrays could reduce
    memory to ~80 bytes/event, enabling 10M+ events in <1 GB.
    """
    
    def __init__(self, max_capacity: int = 1_000_000):
        """
        Initialize event storage.
        
        Args:
            max_capacity: Maximum number of events to store (default: 10 million)
        """
        self._events: List[EventData] = []
        self._mutex = QMutex()
        self._max_capacity = max_capacity
        self._event_id_counter = 0
    
    def add_event(self, event: EventData) -> bool:
        """
        Add a single event to storage.
        
        Args:
            event: EventData to store
            
        Returns:
            True if added successfully, False if storage is full
        """
        with QMutexLocker(self._mutex):
            if len(self._events) >= self._max_capacity:
                return False
            
            self._events.append(event)
            return True
    
    def add_events(self, events: List[EventData]) -> int:
        """
        Add multiple events to storage (batch operation).
        
        Args:
            events: List of EventData to store
            
        Returns:
            Number of events actually added (may be less if capacity reached)
        """
        with QMutexLocker(self._mutex):
            current_count = len(self._events)
            available_space = self._max_capacity - current_count
            
            if available_space <= 0:
                return 0
            
            # Add as many as we can
            num_to_add = min(len(events), available_space)
            self._events.extend(events[:num_to_add])
            
            return num_to_add
    
    def get_count(self) -> int:
        """
        Get current number of events stored.
        
        Returns:
            Event count
        """
        with QMutexLocker(self._mutex):
            return len(self._events)
    
    def get_events(self, start_idx: int = 0, end_idx: Optional[int] = None) -> List[EventData]:
        """
        Retrieve a slice of events.
        
        Args:
            start_idx: Starting index (inclusive)
            end_idx: Ending index (exclusive), None for all remaining
            
        Returns:
            List of EventData (copy)
        """
        with QMutexLocker(self._mutex):
            if end_idx is None:
                return self._events[start_idx:].copy()
            else:
                return self._events[start_idx:end_idx].copy()
    
    def get_all_events(self) -> List[EventData]:
        """
        Get a copy of all events.
        
        Returns:
            List of all EventData (copy)
        """
        with QMutexLocker(self._mutex):
            return self._events.copy()
    
    def clear(self) -> None:
        """
        Clear all stored events and reset counter.
        Used when Restart button is clicked.
        """
        with QMutexLocker(self._mutex):
            self._events.clear()
            self._event_id_counter = 0
    
    def is_full(self) -> bool:
        """
        Check if storage has reached maximum capacity.
        
        Returns:
            True if at capacity, False otherwise
        """
        with QMutexLocker(self._mutex):
            return len(self._events) >= self._max_capacity
    
    def get_available_space(self) -> int:
        """
        Get number of events that can still be stored.
        
        Returns:
            Available capacity
        """
        with QMutexLocker(self._mutex):
            return self._max_capacity - len(self._events)
    
    def get_memory_usage(self) -> float:
        """
        Estimate memory usage in megabytes.
        
        Rough estimate based on:
        - EventData structure: ~40 bytes per event
        - Python object overhead
        
        Returns:
            Estimated memory usage in MB
        """
        with QMutexLocker(self._mutex):
            count = len(self._events)
            
            # Estimate bytes per event
            # Each EventData has:
            # - event_id (int): 28 bytes
            # - timestamp (float): 24 bytes  
            # - channels dict: ~48 bytes + 4 * ChannelPulse
            # - Each ChannelPulse: 4 floats + 1 bool = ~100 bytes
            # Total: ~28 + 24 + 48 + 400 = ~500 bytes per event with overhead
            bytes_per_event = 500
            
            total_bytes = count * bytes_per_event
            total_mb = total_bytes / (1024 * 1024)
            
            return total_mb
    
    def get_next_event_id(self) -> int:
        """
        Get the next event ID and increment counter.
        Thread-safe.
        
        Returns:
            Next event ID
        """
        with QMutexLocker(self._mutex):
            event_id = self._event_id_counter
            self._event_id_counter += 1
            return event_id
    
    def get_max_capacity(self) -> int:
        """
        Get maximum storage capacity.
        
        Returns:
            Maximum number of events
        """
        return self._max_capacity
    
    def get_fill_percentage(self) -> float:
        """
        Get storage fill percentage.
        
        Returns:
            Fill percentage (0-100)
        """
        with QMutexLocker(self._mutex):
            if self._max_capacity == 0:
                return 100.0
            return (len(self._events) / self._max_capacity) * 100.0


# Global event storage instance
_global_storage: Optional[EventStorage] = None


def get_event_storage(max_capacity: int = 1_000_000) -> EventStorage:
    """
    Get or create the global event storage instance.
    
    Args:
        max_capacity: Maximum capacity (only used on first call)
        
    Returns:
        Global EventStorage instance
    """
    global _global_storage
    if _global_storage is None:
        _global_storage = EventStorage(max_capacity=max_capacity)
    return _global_storage


def reset_event_storage() -> None:
    """
    Reset the global event storage instance.
    Used primarily for testing or when changing capacity settings.
    """
    global _global_storage
    if _global_storage is not None:
        _global_storage.clear()
