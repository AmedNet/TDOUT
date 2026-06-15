# tools.py
import ctypes
import os
import subprocess
import winreg
from ctypes import wintypes

# === 兼容性修复：某些 Python 版本无 ULONG_PTR ===
if not hasattr(wintypes, "ULONG_PTR"):
    # 根据架构选择 32 / 64 位
    import struct
    if struct.calcsize("P") == 8:  # 64-bit
        wintypes.ULONG_PTR = ctypes.c_uint64
    else:
        wintypes.ULONG_PTR = ctypes.c_uint32

# Load Win32 DLLs
user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

# === 解键盘 ===
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.ULONG_PTR),
    ]

class INPUT(ctypes.Structure):
    class _I(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]
    _anonymous_ = ("i",)
    _fields_ = [("type", wintypes.DWORD), ("i", _I)]

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002

def wake_keyboard():
    """模拟按下并释放 Shift 键，常用于解除键盘锁或唤醒输入"""
    inputs = (INPUT * 2)()
    inputs[0].type = INPUT_KEYBOARD
    inputs[0].ki.wVk = 0x10  # VK_SHIFT
    inputs[0].ki.dwFlags = 0
    inputs[1].type = INPUT_KEYBOARD
    inputs[1].ki.wVk = 0x10
    inputs[1].ki.dwFlags = KEYEVENTF_KEYUP
    n = user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))
    if n != 2:
        raise ctypes.WinError(ctypes.get_last_error())

# === 解鼠标 ===
def unlock_mouse():
    """释放鼠标限制区域"""
    if not user32.ClipCursor(None):
        raise ctypes.WinError(ctypes.get_last_error())

# === 置顶 / 取消置顶窗口 ===
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2

def set_window_topmost(hwnd):
    user32.SetWindowPos(wintypes.HWND(hwnd), HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)

def clear_window_topmost(hwnd):
    user32.SetWindowPos(wintypes.HWND(hwnd), HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)

# === 注册表解密 ===
def get_mythware_password_from_regedit():
    # Initialize the registry keys and values
    registry_path1 = r"SOFTWARE\WOW6432Node\TopDomain\e-Learning Class\Student"
    registry_path2 = r"SOFTWARE\TopDomain\e-Learning Class\Student"
    key_name_1 = "Knock"
    key_name_2 = "knock1"

    # Attempt to open the registry keys
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_path1, 0,
                             winreg.KEY_QUERY_VALUE | winreg.KEY_WOW64_32KEY)
        key_exists = True
    except FileNotFoundError:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_path2, 0,
                                 winreg.KEY_QUERY_VALUE | winreg.KEY_WOW64_32KEY)
            key_exists = True
        except FileNotFoundError:
            print("Registry key not found")
            return

    # Try to fetch the value of "Knock" first, if not found, fetch "knock1"
    try:
        value, _ = winreg.QueryValueEx(key, key_name_1)
    except FileNotFoundError:
        try:
            value, _ = winreg.QueryValueEx(key, key_name_2)
            f = 0
        except FileNotFoundError:
            winreg.CloseKey(key)
            return

    # XOR Decryption of the value
    decrypted_value = bytearray(value)
    for i in range(0, len(decrypted_value), 4):
        decrypted_value[i] ^= 0x50 ^ 0x45
        decrypted_value[i + 1] ^= 0x43 ^ 0x4c
        decrypted_value[i + 2] ^= 0x4c ^ 0x43
        decrypted_value[i + 3] ^= 0x45 ^ 0x50

    # Extract the string from decrypted value (null-terminated)
    password = ""
    for i in range(0, len(decrypted_value), 2):
        if decrypted_value[i + 1] == 0:  # Null byte is encountered
            password += chr(decrypted_value[i])
        if decrypted_value[i] == 0:  # End of string (second null byte)
            break

    # Get the temp directory path and save the result to NTDPwd.key
    temp_dir = os.getenv("TEMP")
    file_path = os.path.join(temp_dir, "Student_Pwd_key.txt")
    with open(file_path, "w") as f:
        f.write(password)

    # Close the registry key
    winreg.CloseKey(key)
    print(f"Password saved to {file_path}")
    subprocess.run(['cmd', '/k', f'{file_path}'])

# === 判断窗口是否存在（通过标题或类名）===
def find_window_by_title(title_keyword: str):
    """返回包含特定标题的窗口句柄"""
    EnumWindows = user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    GetWindowText = user32.GetWindowTextW
    GetWindowTextLength = user32.GetWindowTextLengthW

    handles = []

    def callback(hwnd, lParam):
        length = GetWindowTextLength(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        GetWindowText(hwnd, buff, length + 1)
        if title_keyword.lower() in buff.value.lower():
            handles.append(hwnd)
        return True

    EnumWindows(EnumWindowsProc(callback), 0)
    return handles
