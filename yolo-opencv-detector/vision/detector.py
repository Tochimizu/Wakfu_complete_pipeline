"""
Clean YOLOv4-tiny detector wrapper.

Extracted and cleaned from the original notebooks.
This version has **no side effects** (no imshow, no image mutation for display).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

import cv2 as cv
import numpy as np

from .types import Detection, FrameDetections


class YoloDetector:
    """
    YOLOv4-tiny object detector for Wakfu (or any game).

    Example:
        detector = YoloDetector(
            cfg_path="yolov4-tiny/yolov4-tiny-custom.cfg",
            weights_path="yolov4-tiny-custom_last.weights",
            names_path="yolov4-tiny/obj.names",
        )
        dets = detector.detect(screenshot)
    """

    def __init__(
        self,
        cfg_path: str | Path,
        weights_path: str | Path,
        names_path: str | Path,
        input_size: tuple[int, int] = (416, 416),
        conf_threshold: float = 0.5,
        nms_threshold: float = 0.4,
    ):
        self.cfg_path = Path(cfg_path)
        self.weights_path = Path(weights_path)
        self.names_path = Path(names_path)
        self.input_size = input_size
        self.conf_threshold = conf_threshold
        self.nms_threshold = nms_threshold

        self.net: Optional[cv.dnn.Net] = None
        self.ln: list[str] = []
        self.classes: dict[int, str] = {}

        self._load_model()

    def _load_model(self) -> None:
        if not self.cfg_path.exists():
            raise FileNotFoundError(f"Config not found: {self.cfg_path}")
        if not self.weights_path.exists():
            raise FileNotFoundError(f"Weights not found: {self.weights_path}")

        self.net = cv.dnn.readNetFromDarknet(str(self.cfg_path), str(self.weights_path))
        self.net.setPreferableBackend(cv.dnn.DNN_BACKEND_OPENCV)
        # You can switch to DNN_BACKEND_CUDA + DNN_TARGET_CUDA if you have GPU

        layer_names = self.net.getLayerNames()
        unconnected = self.net.getUnconnectedOutLayers()
        self.ln = [layer_names[i - 1] for i in unconnected]

        # Load class names
        with open(self.names_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                self.classes[i] = line.strip()

    def detect(self, img: np.ndarray) -> FrameDetections:
        """
        Run detection on a BGR image (from WindowCapture or elsewhere).

        Args:
            img: BGR image, shape (H, W, 3)

        Returns:
            FrameDetections with clean Detection objects (no drawing performed).
        """
        if self.net is None:
            raise RuntimeError("Model not loaded")

        h, w = img.shape[:2]

        blob = cv.dnn.blobFromImage(
            img, 1 / 255.0, self.input_size, swapRB=True, crop=False
        )
        self.net.setInput(blob)
        outputs = self.net.forward(self.ln)
        outputs = np.vstack(outputs)

        detections = self._parse_outputs(outputs, w, h)

        return FrameDetections(
            detections=detections,
            window_width=w,
            window_height=h,
        )

    def _parse_outputs(
        self, outputs: np.ndarray, img_w: int, img_h: int
    ) -> list[Detection]:
        boxes: list[list[int]] = []
        confidences: list[float] = []
        class_ids: list[int] = []

        for output in outputs:
            scores = output[5:]
            class_id = int(np.argmax(scores))
            confidence = float(scores[class_id])

            if confidence > self.conf_threshold:
                # YOLO returns center_x, center_y, w, h normalized to [0,1]
                x, y, bw, bh = output[:4] * np.array([img_w, img_h, img_w, img_h])
                x1 = int(x - bw / 2)
                y1 = int(y - bh / 2)
                boxes.append([x1, y1, int(bw), int(bh)])
                confidences.append(confidence)
                class_ids.append(class_id)

        if not boxes:
            return []

        indices = cv.dnn.NMSBoxes(
            boxes, confidences, self.conf_threshold, self.nms_threshold
        )

        results: list[Detection] = []
        for i in indices.flatten():
            x, y, bw, bh = boxes[i]
            results.append(
                Detection(
                    x=x,
                    y=y,
                    w=bw,
                    h=bh,
                    class_id=class_ids[i],
                    class_name=self.classes.get(class_ids[i], f"class_{class_ids[i]}"),
                    confidence=confidences[i],
                )
            )
        return results

    @property
    def num_classes(self) -> int:
        return len(self.classes)
