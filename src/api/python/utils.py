"""Shared utility functions for the API application."""

import logging
import os

from azure.monitor.events.extension import track_event

logger = logging.getLogger(__name__)


def track_event_if_configured(event_name: str, event_data: dict):
    """
    Track an event with Application Insights if configured.

    Args:
        event_name: The name of the event to track.
        event_data: The data to associate with the event.
    """
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if connection_string:
        track_event(event_name, event_data)
