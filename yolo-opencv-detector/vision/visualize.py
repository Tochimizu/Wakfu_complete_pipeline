"""
Optional visualization helpers for YOLO detections.

These are intentionally separated from the pure Detector so that
production code (WorldBuilder sources) never accidentally opens GUI windows.
"""

from __future__ import annotations

import cv2 as cv
import numpy as np

from .types import Detection


# Default colors (expand as needed for your 16+ classes)
DEFAULT_COLORS = [
    (0, 0, 255), (0, 255, 0), (255, 0, 0),
    (255, 255, 0), (255, 0, 255), (0, 255, 255),
    (128, 0, 128), (0, 128, 128), (128, 128, 0),
]


def draw_detections(
    img: np.ndarray,
    detections: list[Detection],
    colors: list[tuple[int, int, int]] | None = None,
    thickness: int = 2,
) -> np.ndarray:
    """
    Draw bounding boxes and labels on a copy of the image.

    Returns a new image (does not mutate the input).
    """
    if colors is None:
        colors = DEFAULT_COLORS

    vis = img.copy()

    for det in detections:
        color = colors[det.class_id % len(colors)]

        cv.rectangle(
            vis,
            (det.x, det.y),
            (det.x + det.w, det.y + det.h),
            color,
            thickness,
        )
        label = f"{det.class_name} {det.confidence:.2f}"
        cv.putText(
            vis,
            label,
            (det.x, max(15, det.y - 8)),
            cv.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            1,
            cv.LINE_AA,
        )

    return vis


def show_detections(
    img: np.ndarray,
    detections: list[Detection],
    window_name: str = "Detections",
    wait_ms: int = 1,
) -> None:
    """
    Convenience function for debugging in notebooks or local dev.
    Opens an OpenCV window. Does NOT call waitKey itself.
    """
    vis = draw_detections(img, detections)
    cv.imshow(window_name, vis)
