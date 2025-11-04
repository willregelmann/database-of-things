"""
Structured progress event system for curator agents.

Uses Pydantic models for type-safe event emission and monitoring.
"""

from datetime import datetime
from typing import Optional, Dict, Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# Event phase types
PhaseType = Literal[
    "planning",
    "fetching",
    "downloading",
    "processing",
    "validation",
    "uploading",
    "database",
    "memory",
    "complete",
    "error",
]


class ProgressEvent(BaseModel):
    """
    Base progress event model.

    All progress events share these common fields.
    """

    event_id: UUID = Field(default_factory=uuid4, description="Unique event identifier")
    run_id: str = Field(..., description="Curator run identifier")
    curator_id: str = Field(..., description="Curator identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    phase: PhaseType = Field(..., description="Current phase of operation")
    message: str = Field(..., description="Human-readable message")

    # Optional fields
    metrics: Optional[Dict[str, Any]] = Field(
        None, description="Quantitative metrics (counts, percentages, etc.)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional context data"
    )
    error: Optional[Dict[str, Any]] = Field(
        None, description="Error details if phase is 'error'"
    )


class PlanningEvent(ProgressEvent):
    """Event emitted during planning phase."""

    phase: Literal["planning"] = "planning"
    plan_steps: Optional[int] = Field(None, description="Number of planned steps")


class FetchingEvent(ProgressEvent):
    """Event emitted during API fetching phase."""

    phase: Literal["fetching"] = "fetching"
    url: Optional[str] = Field(None, description="URL being fetched")
    rate_limit_remaining: Optional[int] = Field(None, description="API rate limit remaining")


class DownloadingEvent(ProgressEvent):
    """Event emitted during image downloading phase."""

    phase: Literal["downloading"] = "downloading"
    total_items: Optional[int] = Field(None, description="Total items to download")
    completed_items: Optional[int] = Field(None, description="Items completed")
    failed_items: Optional[int] = Field(None, description="Items failed")


class ProcessingEvent(ProgressEvent):
    """Event emitted during data processing phase."""

    phase: Literal["processing"] = "processing"
    total_items: Optional[int] = Field(None, description="Total items to process")
    completed_items: Optional[int] = Field(None, description="Items completed")


class ValidationEvent(ProgressEvent):
    """Event emitted during validation phase."""

    phase: Literal["validation"] = "validation"
    validation_passed: Optional[bool] = Field(None, description="Validation result")
    validation_errors: Optional[list] = Field(None, description="Validation errors if any")


class UploadingEvent(ProgressEvent):
    """Event emitted during upload phase."""

    phase: Literal["uploading"] = "uploading"
    total_bytes: Optional[int] = Field(None, description="Total bytes to upload")
    uploaded_bytes: Optional[int] = Field(None, description="Bytes uploaded")


class DatabaseEvent(ProgressEvent):
    """Event emitted during database operations."""

    phase: Literal["database"] = "database"
    operation: Optional[str] = Field(None, description="Database operation type")
    entities_created: Optional[int] = Field(None, description="Entities created")
    relationships_created: Optional[int] = Field(None, description="Relationships created")


class MemoryEvent(ProgressEvent):
    """Event emitted during memory operations."""

    phase: Literal["memory"] = "memory"
    memory_count: Optional[int] = Field(None, description="Number of memories")
    memory_category: Optional[str] = Field(None, description="Memory category")


class CompleteEvent(ProgressEvent):
    """Event emitted when curator run completes successfully."""

    phase: Literal["complete"] = "complete"
    total_entities_created: Optional[int] = Field(None, description="Total entities created")
    total_relationships_created: Optional[int] = Field(
        None, description="Total relationships created"
    )
    total_images_processed: Optional[int] = Field(None, description="Total images processed")
    total_tokens_used: Optional[int] = Field(None, description="Total tokens used")
    duration_seconds: Optional[float] = Field(None, description="Total duration in seconds")


class ErrorEvent(ProgressEvent):
    """Event emitted when an error occurs."""

    phase: Literal["error"] = "error"
    error_type: str = Field(..., description="Error type/class")
    error_message: str = Field(..., description="Error message")
    error_traceback: Optional[str] = Field(None, description="Full traceback")
    recoverable: bool = Field(default=False, description="Whether error is recoverable")


class ProgressEmitter:
    """
    Progress event emitter.

    Emits structured events for monitoring and UI updates.
    """

    def __init__(self, run_id: str, curator_id: str):
        """
        Initialize progress emitter.

        Args:
            run_id: Curator run identifier
            curator_id: Curator identifier
        """
        self.run_id = run_id
        self.curator_id = curator_id
        self.events: list[ProgressEvent] = []

    def emit(self, event: ProgressEvent) -> None:
        """
        Emit a progress event.

        Args:
            event: Progress event to emit
        """
        # Set run_id and curator_id
        event.run_id = self.run_id
        event.curator_id = self.curator_id

        # Store event
        self.events.append(event)

        # Log to console (in production, send to monitoring system)
        self._log_event(event)

    def _log_event(self, event: ProgressEvent) -> None:
        """
        Log event to console.

        Args:
            event: Event to log
        """
        timestamp = event.timestamp.strftime("%H:%M:%S")
        phase_emoji = {
            "planning": "📋",
            "fetching": "🌐",
            "downloading": "⬇️",
            "processing": "⚙️",
            "validation": "✅",
            "uploading": "⬆️",
            "database": "💾",
            "memory": "🧠",
            "complete": "🎉",
            "error": "❌",
        }

        emoji = phase_emoji.get(event.phase, "📌")
        print(f"[{timestamp}] {emoji} {event.phase.upper()}: {event.message}")

        if event.metrics:
            print(f"  Metrics: {event.metrics}")

    def emit_planning(self, message: str, plan_steps: Optional[int] = None) -> None:
        """Emit planning event."""
        self.emit(PlanningEvent(message=message, plan_steps=plan_steps))

    def emit_fetching(
        self,
        message: str,
        url: Optional[str] = None,
        rate_limit_remaining: Optional[int] = None,
    ) -> None:
        """Emit fetching event."""
        self.emit(
            FetchingEvent(message=message, url=url, rate_limit_remaining=rate_limit_remaining)
        )

    def emit_downloading(
        self,
        message: str,
        total: Optional[int] = None,
        completed: Optional[int] = None,
        failed: Optional[int] = None,
    ) -> None:
        """Emit downloading event."""
        self.emit(
            DownloadingEvent(
                message=message,
                total_items=total,
                completed_items=completed,
                failed_items=failed,
            )
        )

    def emit_processing(
        self,
        message: str,
        total: Optional[int] = None,
        completed: Optional[int] = None,
    ) -> None:
        """Emit processing event."""
        self.emit(
            ProcessingEvent(message=message, total_items=total, completed_items=completed)
        )

    def emit_database(
        self,
        message: str,
        operation: Optional[str] = None,
        entities: Optional[int] = None,
        relationships: Optional[int] = None,
    ) -> None:
        """Emit database event."""
        self.emit(
            DatabaseEvent(
                message=message,
                operation=operation,
                entities_created=entities,
                relationships_created=relationships,
            )
        )

    def emit_complete(
        self,
        message: str,
        entities: Optional[int] = None,
        relationships: Optional[int] = None,
        images: Optional[int] = None,
        tokens: Optional[int] = None,
        duration: Optional[float] = None,
    ) -> None:
        """Emit completion event."""
        self.emit(
            CompleteEvent(
                message=message,
                total_entities_created=entities,
                total_relationships_created=relationships,
                total_images_processed=images,
                total_tokens_used=tokens,
                duration_seconds=duration,
            )
        )

    def emit_error(
        self,
        message: str,
        error_type: str,
        error_message: str,
        traceback: Optional[str] = None,
        recoverable: bool = False,
    ) -> None:
        """Emit error event."""
        self.emit(
            ErrorEvent(
                message=message,
                error_type=error_type,
                error_message=error_message,
                error_traceback=traceback,
                recoverable=recoverable,
            )
        )

    def get_events(self, phase: Optional[PhaseType] = None) -> list[ProgressEvent]:
        """
        Get all events, optionally filtered by phase.

        Args:
            phase: Optional phase filter

        Returns:
            List of events
        """
        if phase:
            return [e for e in self.events if e.phase == phase]
        return self.events
