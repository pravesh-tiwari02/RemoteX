import ctypes
from ctypes import wintypes
import time
from PIL import ImageGrab

# Enable DPI Awareness
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    user32.SetProcessDPIAware()

# VK Codes
VK_BACK = 0x08
VK_TAB = 0x09
VK_RETURN = 0x0D
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12 # Alt
VK_PAUSE = 0x13
VK_CAPITAL = 0x14
VK_ESCAPE = 0x1B
VK_SPACE = 0x20
VK_PRIOR = 0x21 # Page Up
VK_NEXT = 0x22 # Page Down
VK_END = 0x23
VK_HOME = 0x24
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_INSERT = 0x2D
VK_DELETE = 0x2E
VK_LWIN = 0x5B
VK_RWIN = 0x5C

SPECIAL_KEYS = {
    "{BACKSPACE}": VK_BACK,
    "{TAB}": VK_TAB,
    "{ENTER}": VK_RETURN,
    "{SHIFT}": VK_SHIFT,
    "{CTRL}": VK_CONTROL,
    "{ALT}": VK_MENU,
    "{PAUSE}": VK_PAUSE,
    "{CAPSLOCK}": VK_CAPITAL,
    "{ESC}": VK_ESCAPE,
    "{SPACE}": VK_SPACE,
    "{PGUP}": VK_PRIOR,
    "{PGDN}": VK_NEXT,
    "{END}": VK_END,
    "{HOME}": VK_HOME,
    "{LEFT}": VK_LEFT,
    "{UP}": VK_UP,
    "{RIGHT}": VK_RIGHT,
    "{DOWN}": VK_DOWN,
    "{INSERT}": VK_INSERT,
    "{DELETE}": VK_DELETE,
    "{LWIN}": VK_LWIN,
    "{RWIN}": VK_RWIN,
}

def send_vk(vk, down):
    """Sends a virtual key event."""
    scan = user32.MapVirtualKeyW(vk, 0)
    flags = 0 if down else KEYEVENTF_KEYUP
    
    # Extended keys need the extended flag
    if vk in [VK_INSERT, VK_DELETE, VK_HOME, VK_END, VK_PRIOR, VK_NEXT, VK_LEFT, VK_UP, VK_RIGHT, VK_DOWN]:
        flags |= 0x0001 # KEYEVENTF_EXTENDEDKEY

    ki = KEYBDINPUT(vk, scan, flags, 0, None)
    inp = INPUT(INPUT_KEYBOARD, INPUT_UNION(ki=ki))
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

def simulate_special_key(key_tag):
    """Simulates a special key press (Down and Up)."""
    vk = SPECIAL_KEYS.get(key_tag.upper())
    if vk:
        send_vk(vk, True)
        send_vk(vk, False)

def simulate_text(text):
    """Parses text and simulates input, handling {KEY} tags."""
    i = 0
    while i < len(text):
        if text[i] == '{':
            end = text.find('}', i)
            if end != -1:
                tag = text[i:end+1]
                if tag.upper() in SPECIAL_KEYS:
                    simulate_special_key(tag)
                    i = end + 1
                    continue
        
        send_unicode_char(text[i])
        i += 1
