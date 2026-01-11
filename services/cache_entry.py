from typing import Any
from datetime import datetime
from dataclasses import dataclass

@dataclass
class CacheEntry:
    """Complete cache entry with data and metadata for persistence."""
    ticker: str
    # Metadata
    retrieval_time: datetime
    # Data
    data: Any