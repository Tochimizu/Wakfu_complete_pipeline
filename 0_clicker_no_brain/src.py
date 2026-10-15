import re
import pyautogui
import time
import pygetwindow as gw
import win32api
import win32con
import random
import os
from datetime import datetime

def take_screenshot(i):
    screenshot = pyautogui.screenshot()
    os.makedirs("temp_img", exist_ok=True)
    now = datetime.now()
    formatted_time = now.strftime("%H_%M_%S")
    screenshot.save(f"temp_img/run_n{i}__{formatted_time}.png")

def _clean_action_line(s: str) -> str:
    # remove NULs and whitespace; drop optional .png or png at end
    s = s.replace("\x00", "").strip()
    s = re.sub(r'\.?\s*png$', '', s, flags=re.IGNORECASE)
    return s

def press_win32_key(key):
    vk_codes = {'0':0x30,'1':0x31,'2':0x32,'3':0x33,'4':0x34,'5':0x35,'6':0x36,'7':0x37,'8':0x38,'9':0x39}
    if key in vk_codes:
        vk_code = vk_codes[key]
        win32api.keybd_event(vk_code, 0, 0, 0)
        time.sleep(0.05)
        win32api.keybd_event(vk_code, 0, win32con.KEYEVENTF_KEYUP, 0)

def perform_action(action_line, bonus_delay):
    try:
        line = _clean_action_line(action_line)
        parts = line.split("_")

        if len(parts) < 5:
            raise ValueError(f"Invalid action format: {line}")

        key_sequence = parts[1]
        x_str, y_str, delay_str = parts[2], parts[3], parts[4]

        # extra clean (handles any lingering non-digit like thin spaces)
        x = int(x_str.replace("\x00", "").strip())
        y = int(y_str.replace("\x00", "").strip())
        delay = float(delay_str.replace("\x00", "").strip())

        time.sleep(delay)
        pyautogui.moveTo(x, y,duration=0.05+random.randrange(3,7)/100)

        random_time = random.randrange(0, 50, 1) / 1000.0
        time.sleep(bonus_delay + random_time)

        key_parts = key_sequence.split()
        modifier_keys = ['ctrl', 'shift', 'alt', 'maj']
        keys_to_hold = [k for k in key_parts if k in modifier_keys]

        for k in keys_to_hold:
            pyautogui.keyDown('shift' if k == 'maj' else k)

        non_modifier_keys = [k for k in key_parts if k not in modifier_keys and "Click" not in k]
        for k in non_modifier_keys:
            if k.isdigit():
                press_win32_key(k)
            else:
                pyautogui.press(k)

        for k in keys_to_hold:
            pyautogui.keyUp('shift' if k == 'maj' else k)

        click_time = 0.07
        if "leftClick" in key_parts:
            pyautogui.mouseDown(x=x, y=y, button='left')
            time.sleep(click_time)
            pyautogui.mouseUp(x=x, y=y, button='left')
        elif "rightClick" in key_parts:
            pyautogui.mouseDown(x=x, y=y, button='right')
            time.sleep(click_time)
            pyautogui.mouseUp(x=x, y=y, button='right')

    except Exception as e:
        print(f"Error processing action: {e}")

# Main function to process multiple actions
def run_bot(action_list,bonus_delay):
    for action in action_list:
        perform_action(action,bonus_delay)

