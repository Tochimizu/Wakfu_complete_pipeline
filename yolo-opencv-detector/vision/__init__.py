"""
Clean, importable YOLO vision package for Wakfu automation.

Public API:
    from yolo_opencv_detector.vision import WindowCapture, YoloDetector, Detection
"""

from .capture import WindowCapture
from .detector import YoloDetector
from .types import Detection, FrameDetections
from .visualize import draw_detections, show_detections

__all__ = [
    "WindowCapture",
    "YoloDetector",
    "Detection",
    "FrameDetections",
    "draw_detections",
    "show_detections",
]
