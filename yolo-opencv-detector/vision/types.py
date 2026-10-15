"""
Typed structures for the Wakfu YOLO vision pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Detection:
    """Clean detection result (replaces raw dicts from notebooks)."""
    x: int          # top-left x in screenshot client pixels
    y: int          # top-left y
    w: int
    h: int
    class_id: int
    class_name: str
    confidence: float = 0.0

    def center(self) -> tuple[int, int]:
        return self.x + self.w // 2, self.y + self.h // 2

    def to_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "w": self.w,
            "h": self.h,
            "class": self.class_id,
            "class_name": self.class_name,
            "confidence": self.confidence,
        }


@dataclass
class FrameDetections:
    """Result of running the detector on one screenshot."""
    detections: list[Detection]
    window_width: int
    window_height: int
    timestamp: Optional[float] = None  # unix time
