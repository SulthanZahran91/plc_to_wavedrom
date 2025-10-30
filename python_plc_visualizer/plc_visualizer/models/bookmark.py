"""Time bookmark data model for navigation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TimeBookmark:
    """Represents a timestamped bookmark for quick navigation.
    
    Attributes:
        timestamp: The time this bookmark points to
        label: User-friendly label for the bookmark
        description: Optional longer description
        created_at: When this bookmark was created
    """
    timestamp: datetime
    label: str
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def __lt__(self, other: TimeBookmark) -> bool:
        """Compare bookmarks by timestamp for sorting."""
        return self.timestamp < other.timestamp

    def __str__(self) -> str:
        """String representation."""
        return f"{self.label} @ {self.timestamp.strftime('%H:%M:%S.%f')[:-3]}"

