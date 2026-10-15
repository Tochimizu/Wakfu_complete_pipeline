import pyautogui
import keyboard
import time
import os
from pynput import mouse

# === NEW: concurrency + timing helpers ===
from threading import Lock, Timer

from PIL import Image

#############___________________Initialisation________________________#############
# Initialize global variables
tag = 0

# Create a translation dictionary for specific characters (e.g., AZERTY → digits)
translation_dict = {
    'à': '0',
    'ç': '9',
    '!': '8',
    'è': '7',
    '§': '6',
    '(': '5',
    "'": '4',
    '"': '3',
    'é': '2',
    '&': '1'
}

# Action collection state
key_sequence = []            # order-preserving list of unique components (max 2)
captured_keys = set()        # uniqueness within the current action
last_screenshot_time = None  # time of the last screenshot

# === NEW: action collector config ===
seq_lock = Lock()
action_timer = None
ACTION_TIMEOUT_SEC = 0.25  # brief window to complete combos

# Allowed components and actions
DIGITS = {str(d) for d in range(0, 10)}  # '0'..'9' (we'll allow combos only for 1..9)

# CHANGED: include "space" so it’s actually captured
ALLOWED_COMPONENTS = {'ctrl', 'shift', 'space'} | DIGITS  # what keyboard inputs we consider

# Singles allowed (keep '4' per your spec; add 'rightClick' via mouse)
ALLOWED_SINGLES = {str(d) for d in range(0, 10)} | {"space"}

# All ctrl/shift with digits 1..9 (order-agnostic)
ALLOWED_PAIRS_UNORDERED = {
    frozenset((mod, str(d)))
    for mod in ('ctrl', 'shift')
    for d in range(1, 10)
}

#############______________________Helpers____________________________#############
def _normalize_key(k: str) -> str:
    """Normalize raw key names to our vocabulary."""
    k = k.lower()
    # Apply AZERTY/symbol digit translations first
    if k in translation_dict:
        k = translation_dict[k]

    # Normalize modifiers/variants
    if k in ('maj', 'left shift', 'right shift', 'shift_l', 'shift_r'):
        k = 'shift'
    if k in ('left ctrl', 'right ctrl', 'ctrl_l', 'ctrl_r', 'control'):
        k = 'ctrl'
    # ⬇️ NEW: normalize space variants defensively
    if k in ('spacebar', ' '):
        k = 'space'

    return k

def reset_buffers():
    """Clear current action buffer."""
    global key_sequence, captured_keys
    key_sequence = []
    captured_keys = set()

def _cancel_timer():
    """Stop any pending finalize timer."""
    global action_timer
    if action_timer is not None:
        action_timer.cancel()
        action_timer = None

def _schedule_finalize():
    """(Re)start a short timer to auto-finalize single-key actions."""
    global action_timer
    _cancel_timer()
    action_timer = Timer(ACTION_TIMEOUT_SEC, finalize_action)
    action_timer.start()

def finalize_action():
    """Validate current buffer (max 2). If allowed, take screenshot; then reset."""
    with seq_lock:
        seq_snapshot = key_sequence[:2]  # hard cap and capture atomically

    if not seq_snapshot:
        return

    # Normalize a copy for matching
    norm = [_normalize_key(x) for x in seq_snapshot]
    allowed = False

    if len(norm) == 1:
        allowed = norm[0] in ALLOWED_SINGLES
    elif len(norm) == 2:
        allowed = frozenset(norm) in ALLOWED_PAIRS_UNORDERED

    if allowed:
        # Pass the snapshot to avoid races with concurrent resets
        take_screenshot_and_save(seq_snapshot, does_screen=does_screen)

    with seq_lock:
        reset_buffers()
    _cancel_timer()

#############______________________Listeners___________________________#############
# Keyboard: only buffer keys we care about; never screenshot here directly
def capture_key_event(e):
    global key_sequence, captured_keys

    key = _normalize_key(e.name)
    # Ignore anything outside our vocabulary
    if key not in ALLOWED_COMPONENTS:
        return

    with seq_lock:
        # If already have 2 inputs, ignore further keys until finalize/reset
        if len(key_sequence) >= 2:
            return
        # Uniqueness within action
        if key not in captured_keys:
            captured_keys.add(key)
            key_sequence.append(key)
            # If we just completed a pair, finalize immediately
            if len(key_sequence) == 2:
                # finalize outside the lock
                pass
            else:
                # For singles, start/refresh the short finalize timer
                _schedule_finalize()

    # If we reached 2, finalize now (outside lock)
    with seq_lock:
        should_finalize_now = (len(key_sequence) == 2)
    if should_finalize_now:
        _cancel_timer()
        finalize_action()

# Mouse: allow only rightClick as a single action; ignore leftClick entirely
def on_click(x, y, button, pressed):
    if not pressed:
        return

    # If a single key is pending (e.g., '3'), finalize it immediately
    with seq_lock:
        pending_single = (len(key_sequence) == 1)
    if pending_single:
        _cancel_timer()
        finalize_action()  # saves the pending '3' (or 'space'), resets buffers

    # Now handle the click as a single action, as before
    if button == mouse.Button.right:
        with seq_lock:
            captured_keys.add("rightClick")
            key_sequence.append("rightClick")
        _cancel_timer()
        take_screenshot_and_save(['rightClick'], does_screen=does_screen)
        with seq_lock:
            reset_buffers()
        return

    if button == mouse.Button.left:
        with seq_lock:
            captured_keys.add("leftClick")
            key_sequence.append("leftClick")
        _cancel_timer()
        take_screenshot_and_save(['leftClick'], does_screen=does_screen)
        with seq_lock:
            reset_buffers()
        return

#############______________________Screenshot__________________________#############
def take_screenshot_and_save(seq=None, does_screen=True):
    """
    Take a screenshot and save it.
    seq: the specific sequence (max 2) that triggered the shot; if None, uses current key_sequence.
    """
    global tag, last_screenshot_time

    # Use provided snapshot (preferred) or a safe in-lock copy
    if seq is None:
        with seq_lock:
            seq = key_sequence[:2]

    # Get current cursor position
    x, y = pyautogui.position()

    # Join the key sequence to form part of the filename
    key_sequence_str = ' '.join(seq)

    # Get the current time and calculate the delay since the last screenshot
    current_time = time.time()
    delay = 0 if last_screenshot_time is None else round(current_time - last_screenshot_time, 2)
    last_screenshot_time = current_time  # Update the last screenshot time

    # Create a filename using the key sequence, position, iteration count, and delay
    name = f"{tag:04d}_{key_sequence_str}_{x}_{y}_{delay}.png"
    print(name, flush=True)  # ensure it appears immediately
    filename = f"img/{name}"
    tag += 1  # Increment the global 'tag' variable

    if does_screen:
        #take_screen(filename)
        take_low_quality_screen(filename)

def take_screen(filename):
    # Take a screenshot and save it with the generated filename
        screenshot = pyautogui.screenshot()

        # Ensure the directory exists
        os.makedirs("img", exist_ok=True)

        # Save the screenshot
        screenshot.save(filename)
def take_low_quality_screen(filename):
    # Take the screenshot (PIL Image)
    screenshot = pyautogui.screenshot()

    # Optional but highly recommended for speed: downscale
    # Example: half resolution (change 0.5 to whatever you need)
    scale = 0.5
    new_size = (int(screenshot.width * scale), int(screenshot.height * scale))
    screenshot = screenshot.resize(new_size, Image.Resampling.LANCZOS)  # or Image.BILINEAR for even more speed

    # Ensure the directory exists (move this outside the function if you call it often)
    os.makedirs("img", exist_ok=True)

    # Change extension to .jpg and save with reduced quality
    filename = filename.replace(".png", ".jpg")   # or just build the name with .jpg from the start
    # Convert to RGB (JPEG does not support alpha/transparency)
    if screenshot.mode in ("RGBA", "P"):
        screenshot = screenshot.convert("RGB")

    # quality=50–70 is a good speed/size trade-off (lower = faster + smaller)
    screenshot.save(filename, "JPEG", quality=60, optimize=True)


#############___________________RUN________________________#############
does_screen = False

# Set up keyboard listener for capturing key presses
keyboard.on_press(capture_key_event)

# Set up mouse listener
mouse_listener = mouse.Listener(on_click=on_click)
mouse_listener.start()

# Keep the script running
keyboard.wait('f')  # Press 'f' to exit
