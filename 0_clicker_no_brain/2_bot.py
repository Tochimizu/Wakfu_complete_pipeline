from src import *
import io

# Focus game window
game_window = gw.getWindowsWithTitle('Notico - WAKFU')[0]
game_window.activate()

filename = "action.txt"
filename = "steps_Bilbiza/1_new_Bilbi_run.txt"
filename = "temp.txt"
# Read robustly: allow UTF-16 and strip NULs downstream anyway
try_encodings = ('utf-8-sig', 'utf-16', 'cp1252')
actions = None
for enc in try_encodings:
    try:
        with open(filename, 'r', encoding=enc) as f:
            actions = f.readlines()
        break
    except Exception:
        continue
if actions is None:
    # last-resort: binary then decode ignoring errors
    with open(filename, 'rb') as f:
        data = f.read().replace(b'\x00', b'')
    actions = data.decode('utf-8', errors='ignore').splitlines(True)

for i in range(25):

    bonus_delay = 0.25  # adjust for lag
    #bonus_delay = 0.45  # adjust for lag
    
    
    run_bot(actions, bonus_delay)
    now = datetime.now()
    print(f"{now.strftime('%H:%M:%S')} # Just finish the run : {i}")
    time.sleep(9)
    if False:
        take_screenshot(i)
