"""
Event Bus for Applyr AI job application platform.

This module provides a centralized event system for communication between
services and agents in the Applyr platform.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Callable, Optional
from enum import Enum
from core.models import PipelineEvent

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Event type enum."""
    RESUME_UPLOADED = "resume_uploaded"
    RESUME_PARSED = "resume_parsed"
    RESUME_VALIDATION_FAILED = "resume_validation_failed"
    PROFILE_CREATED = "profile_created"
    SEARCH_STARTED = "search_started"
    JOBS_FOUND = "jobs_found"
    JOB_DISCOVERED = "job_discovered"
    COMPANY_EXTRACTED = "company_extracted"
    COMPANY_ENRICHED = "company_enriched"
    RECRUITER_DISCOVERED = "recruiter_discovered"
    EMAIL_GENERATED = "email_generated"
    APPLICATION_SUBMITTED = "application_submitted"
    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_COMPLETED = "pipeline_completed"
    PIPELINE_ERROR = "pipeline_error"
    PIPELINE_TIMEOUT = "pipeline_timeout"


class EventBus:
    """Event bus for managing events in the Applyr platform."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.subscribers: Dict[str, List[Callable]] = {}
        self.event_history: List[PipelineEvent] = []

    def publish(self, event_type: str, data: Dict[str, Any], source: str, run_id: str) -> None:
        """
        Publish an event to the event bus.

        Args:
            event_type: Type of event
            data: Event data
            source: Source of the event
            run_id: Pipeline run ID
        """
        event = PipelineEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            run_id=run_id,
            data=data,
            source=source,
        )

        # Add to event history
        self.event_history.append(event)

        # Notify subscribers
        self._notify_subscribers(event)

        self.logger.info(f"Event published: {event_type} from {source} (run_id: {run_id})")

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """
        Subscribe to an event type.

        Args:
            event_type: Type of event to subscribe to
            callback: Callback function to call when event is published
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []

        self.subscribers[event_type].append(callback)
        self.logger.info(f"Subscribed to event: {event_type}")

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """
        Unsubscribe from an event type.

        Args:
            event_type: Type of event to unsubscribe from
            callback: Callback function to remove
        """
        if event_type in self.subscribers:
            try:
                self.subscribers[event_type].remove(callback)
                self.logger.info(f"Unsubscribed from event: {event_type}")
            except ValueError:
                pass

    def get_events_for_run(self, run_id: str) -> List[PipelineEvent]:
        """
        Get all events for a specific run.

        Args:
            run_id: Pipeline run ID

        Returns:
            List of events for the specified run
        """
        return [event for event in self.event_history if event.run_id == run_id]

    def get_events_by_type(self, event_type: str) -> List[PipelineEvent]:
        """
        Get all events of a specific type.

        Args:
            event_type: Type of event

        Returns:
            List of events of the specified type
        """
        return [event for event in self.event_history if event.event_type == event_type]

    def _notify_subscribers(self, event: PipelineEvent) -> None:
        """
        Notify all subscribers of an event.

        Args:
            event: Event to notify subscribers about
        """
        if event.event_type in self.subscribers:
            for callback in self.subscribers[event.event_type]:
                try:
                    callback(event)
                except Exception as e:
                    self.logger.error(f"Error notifying subscriber: {e}")

    def clear_history(self) -> None:
        """Clear event history."""
        self.event_history = []
        self.logger.info("Event history cleared")

    def get_event_count(self) -> int:
        """
        Get the number of events in history.

        Returns:
            Number of events
        """
        return len(self.event_history)


# Singleton instance
_event_bus = None


def get_event_bus() -> EventBus:
    """Get the singleton EventBus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus