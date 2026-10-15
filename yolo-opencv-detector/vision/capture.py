"""
Window capture for Wakfu (and similar games) using Win32.

This is the cleaned, production-ready version extracted from the notebooks.
It correctly captures only the client area and returns a clean BGR numpy array
suitable for YOLO / OpenCV processing.

IMPORTANT:
- This module is Windows-only (uses pywin32).
- Must be run on the machine where the game client ("Notico - WAKFU") is running.
"""

from __future__ import annotations

import ctypes
from typing import Optional, Tuple

import numpy as np

try:
    import win32con
    import win32gui
    import win32ui
except ImportError as e:
    raise ImportError(
        "pywin32 is required for WindowCapture. "
        "Install with: pip install pywin32"
    ) from e


class WindowCapture:
    """
    Captures screenshots of a specific Windows application window (client area only).

    Example:
        cap = WindowCapture("Notico - WAKFU")
        img = cap.get_screenshot()   # BGR numpy array, shape (H, W, 3)
    """

    def __init__(self, window_name: str):
        self.window_name = window_name
        self.hwnd: Optional[int] = None
        self.w: int = 0
        self.h: int = 0
        self.cropped_x: int = 0
        self.cropped_y: int = 0

        self._initialize()

    def _initialize(self) -> None:
        self.hwnd = win32gui.FindWindow(None, self.window_name)
        if not self.hwnd:
            raise RuntimeError(f"Window not found: {self.window_name!r}")

        # Make process DPI aware (important on high-DPI displays)
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

        # Get client area in screen coordinates
        left, top, right, bottom = win32gui.GetClientRect(self.hwnd)
        point_left_top = win32gui.ClientToScreen(self.hwnd, (left, top))
        point_right_bottom = win32gui.ClientToScreen(self.hwnd, (right, bottom))

        self.cropped_x = point_left_top[0]
        self.cropped_y = point_left_top[1]
        self.w = point_right_bottom[0] - point_left_top[0]
        self.h = point_right_bottom[1] - point_left_top[1]

        if self.w <= 0 or self.h <= 0:
            raise RuntimeError(f"Invalid client area size: {self.w}x{self.h}")

    def get_screenshot(self) -> np.ndarray:
        """
        Capture the current client area of the window.

        Returns:
            BGR numpy array of shape (height, width, 3), dtype=uint8, contiguous.
        """
        if self.hwnd is None:
            self._initialize()

        wDC = win32gui.GetWindowDC(self.hwnd)
        dcObj = win32ui.CreateDCFromHandle(wDC)
        cDC = dcObj.CreateCompatibleDC()

        dataBitMap = win32ui.CreateBitmap()
        dataBitMap.CreateCompatibleBitmap(dcObj, self.w, self.h)
        cDC.SelectObject(dataBitMap)

        cDC.BitBlt(
            (0, 0),
            (self.w, self.h),
            dcObj,
            (self.cropped_x, self.cropped_y),
            win32con.SRCCOPY,
        )

        signedIntsArray = dataBitMap.GetBitmapBits(True)
        img = np.frombuffer(signedIntsArray, dtype="uint8")
        img.shape = (self.h, self.w, 4)

        # Cleanup
        dcObj.DeleteDC()
        cDC.DeleteDC()
        win32gui.ReleaseDC(self.hwnd, wDC)
        win32gui.DeleteObject(dataBitMap.GetHandle())

        # Return BGR (drop alpha) as contiguous array for OpenCV / DNN
        return np.ascontiguousarray(img[..., :3])  # BGRA -> BGR

    def get_window_size(self) -> Tuple[int, int]:
        """Return (width, height) of the captured client area."""
        return self.w, self.h

    def __repr__(self) -> str:
        return f"<WindowCapture name={self.window_name!r} size={self.w}x{self.h}>"
