# 标准库导入（按功能分组，排序）
import ctypes
import os
import random
import subprocess
import sys
import threading
import time
import webbrowser
from ctypes import wintypes
from pathlib import Path

import pystray

from combat.UDP import UDP_Attack
from modules.Download import open_download
from modules.F1 import HOTKEY_MANUAL, MANUAL_CONTENT
from modules.IP import IPRangeGenerator

# Windows API 相关（单独分组，明确平台相关性）
if os.name == 'nt':
    import ctypes.wintypes
    from ctypes import windll, byref, create_unicode_buffer
    from ctypes.wintypes import HWND, DWORD, LPVOID, HANDLE
    import win32con
    import win32gui
    import win32process

import customtkinter as ctk
import keyboard
from winotify import Notification, audio  # 用于发送系统通知

# 本地模块导入
from modules import tools, clean, eeg, Freeze
from modules.lan_transfer_chat import LanChatWindow
from modules.subwindow_panel import SubWindow


def run_as_admin():
    """如果当前用户不是管理员，则以管理员权限重新运行自身"""
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except:
        is_admin = False

    if not is_admin:
        # 重新以管理员权限启动
        script = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
        params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)
        sys.exit(0)

GetLastError = ctypes.windll.kernel32.GetLastError
GetLastError.restype = wintypes.DWORD

# --- New Imports for System Tray Feature ---
try:
    from PIL import Image, ImageDraw, ImageTk, ImageFont  # ImageTk 用于窗口图标
    TRAY_ENABLED = True
except ImportError:
    TRAY_ENABLED = False
    print("警告: 无法导入 pystray 或 PIL 库。系统托盘功能将禁用。请确保已安装: pip install pystray Pillow")
    # 在实际运行环境中，这个警告只会出现在控制台

# --- 全局常量和配置 ---
# 热键：Ctrl + Alt + L (L for Launch/Lock) - 用于模式切换和最小化/恢复窗口
HOTKEY_SWITCH1 = '<Control-Alt-l>'
HOTKEY_SWITCH2 = '<Control-Alt-L>'
# 热键：Alt + BackSpace - 用于清除控制台日志
HOTKEY_CLEAR = '<Alt-BackSpace>'
DECOY_ACTIONS = {
    "CDR修复":"#4169E1",
    "Flash修复":"#4169E1",
    "Photoshop修复":"#4169E1",
    "系统卡死修复": "#4169E1",
    "网络丢包检测与修复": "#4169E1",
    "DLL 丢失修复": "#4169E1",
}
# 目标目录: 用户文件夹下的 AppData\LocalLow (用于 '=]' 功能)
TARGET_APPDATA_DIR = os.path.join(os.path.expanduser('~'), 'AppData', 'LocalLow')
EXE_CLEAR = "Window2Clear_v0.2.0.exe"

# --- 资源释放函数 (用于 PyInstaller 单文件模式) ---
def is_packed():
    """检查程序是否以 PyInstaller 打包模式运行。"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def extract_dll_resource(resource_name):
    """将 DLL 资源文件从打包的 EXE 中释放到 TEMP 目录，并返回其完整路径。"""
    temp_dir = os.getenv("TEMP")
    target_path = os.path.join(temp_dir, resource_name)

    if is_packed():
        source_path = os.path.join(sys._MEIPASS, resource_name)
        try:
            if not os.path.exists(source_path):
                print(f"警告: 打包资源未找到: {resource_name}")
                return target_path

            if os.path.exists(target_path) and os.path.getsize(target_path) == os.path.getsize(source_path):
                return target_path

            with open(source_path, "rb") as source, open(target_path, "wb") as target:
                target.write(source.read())
            return target_path

        except Exception as e:
            print(f"严重错误: 无法释放资源 {resource_name}: {e}")
            return target_path

    else:
        return target_path

# --- 核心 DLL 路径和释放及内阁头像 ---
DLL_HIDER_NAME = "NTDHider32.dll"
DLL_SHOWER_NAME = "NTDShower32.dll"
Banchen123_NAME= "Banchen123.ico"
Banchen123 = extract_dll_resource(Banchen123_NAME)
DLL_HIDER = extract_dll_resource(DLL_HIDER_NAME)
DLL_SHOWER = extract_dll_resource(DLL_SHOWER_NAME)

#ico
Banchen123_image = Image.open(Banchen123)

# --- WINDOWS API 导入和常量 (用于窗口操作和注入) ---
if os.name == 'nt':
    import ctypes
    from ctypes import windll, byref, create_unicode_buffer, wintypes
    from ctypes.wintypes import HWND, DWORD, LPVOID, HANDLE

    # 导入所需的类型和常量
    LRESULT = ctypes.c_longlong
    WM_SETICON = 0x0080
    ICON_BIG = 1
    ICON_SMALL = 0
    IDI_APPLICATION = 32512
    PROCESS_ALL_ACCESS = 0x1F0FFF
    MEM_COMMIT = 0x00001000
    PAGE_READWRITE = 0x0004
    LPTHREAD_START_ROUTINE = ctypes.c_void_p
    SIZE_T = ctypes.c_size_t  # 修复: 确保大小类型为 64 位兼容
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_NOZORDER = 0x0004
    SWP_TOPMOST = 0x0008

    # 修复：定义正确的 WNDENUMPROC 类型 (BOOL, HWND, LPARAM)
    WNDENUMPROC_TYPE = ctypes.WINFUNCTYPE(wintypes.BOOL, HWND, wintypes.LPARAM)

    subprocess.DETACHED_PROCESS = 0x00000008
    subprocess.CREATE_NEW_PROCESS_GROUP = 0x00000200

    # 加载系统库
    kernel32 = windll.kernel32
    user32 = windll.user32

    # API 签名设置 (只列出核心签名，确保 LoadLibraryA 可用)
    GetForegroundWindow = user32.GetForegroundWindow
    user32.GetWindowThreadProcessId.argtypes = [HWND, ctypes.POINTER(DWORD)]
    SetWindowPos = user32.SetWindowPos
    SetWindowPos.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,ctypes.c_uint]
    kernel32.OpenProcess.restype = HANDLE

    # --- 修复溢出错误的 Argtypes 明确定义 ---
    # VirtualAllocEx
    kernel32.VirtualAllocEx.argtypes = [HANDLE, LPVOID, SIZE_T, DWORD, DWORD]
    kernel32.VirtualAllocEx.restype = LPVOID

    # WriteProcessMemory (Argument 2 lpBaseAddress 是指针，需要 64 位兼容)
    kernel32.WriteProcessMemory.argtypes = [
        HANDLE,  # hProcess
        LPVOID,  # lpBaseAddress (Argument 2)
        LPVOID,  # lpBuffer (bytes buffer)
        SIZE_T,  # nSize
        ctypes.POINTER(SIZE_T)  # lpNumberOfBytesWritten
    ]
    kernel32.WriteProcessMemory.restype = wintypes.BOOL

    # CreateRemoteThread
    kernel32.CreateRemoteThread.argtypes = [
        HANDLE,  # hProcess
        LPVOID,  # lpThreadAttributes (None)
        SIZE_T,  # dwStackSize (0)
        LPTHREAD_START_ROUTINE,  # lpStartAddress (pLoadLibraryA)
        LPVOID,  # lpParameter (lpBuffer)
        DWORD,  # dwCreationFlags (0)
        LPVOID  # lpThreadId (None)
    ]
    kernel32.CreateRemoteThread.restype = HANDLE
    # --- 修复结束 ---

    pLoadLibraryA = None
    try:
        LoadLibraryA_func = kernel32.LoadLibraryA
        pLoadLibraryA = ctypes.cast(LoadLibraryA_func, ctypes.c_void_p).value
    except Exception as e:
        print(f"错误: 绑定 LoadLibraryA 失败: {e}")
        pLoadLibraryA = None

    WDA_ACTION_HIDE = 1
    WDA_ACTION_SHOW = 0

# --- ANSI 颜色代码 (用于日志显示) ---
COLOR_GREEN = "[√] "
COLOR_RED = "[X] "
COLOR_YELLOW = "[→] "
COLOR_CYAN = "--- "
COLOR_RESET = ""

def start_unlock_daemon(keyword: str = "屏幕", interval: float = 1.0):
    """
    后台线程：检测到窗口标题包含 keyword 时，持续执行键盘+鼠标解禁。
    :param keyword: 窗口标题关键字，默认 '屏幕广播'
    :param interval: 检查间隔（秒）
    """
    def loop_unlock():
        print(f"[解禁守护] 已启动，监控窗口关键字：{keyword}")
        while True:
            time.sleep(5)
            hwnds = tools.find_window_by_title(keyword)
            if hwnds:
                try:
                    tools.wake_keyboard()
                    tools.unlock_mouse()
                    # 可选：只打印一次或节流打印
                    print(f"[解禁守护] 检测到 '{keyword}'，已执行解禁。")
                except Exception as e:
                    print(f"[解禁守护] 失败: {e}")
    t = threading.Thread(target=loop_unlock, daemon=True)
    t.start()
    return t  # 若需手动管理线程，可接收返回值

# --- 屏幕解控常量和 API 定义 ---
BROADCAST_TITLE_SNIPPET = "屏幕"  #仅包含
EnumChildProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

# --- 2. 核心解冻回调函数（Windows API 强制要求） ---
def unfreeze_child_window_proc(hwndChild, lParam):
    """
    EnumChildWindows 的回调函数，用于启用子控件。
    """
    try:
        win32gui.EnableWindow(hwndChild, True)
        current_style = win32gui.GetWindowLong(hwndChild, win32con.GWL_STYLE)
        if current_style & win32con.WS_DISABLED:
            new_style = current_style & (~win32con.WS_DISABLED)
            win32gui.SetWindowLong(hwndChild, win32con.GWL_STYLE, new_style)
    except Exception:
        pass
    return True

stop_event = threading.Event()
# --- 3. 后台循环函数（线程执行的目标） ---
def run_periodic_unfreeze_in_background():
    print("--- 极域广播解冻后台线程已启动 (每 3 秒执行一次) ---")
    target_hwnd = 0
    while not stop_event.is_set():
        try:
            # A. 查找广播窗口
            # 定义一个内部查找回调函数
            def find_parent_window(hwnd, extra):
                nonlocal target_hwnd
                try:
                    title = win32gui.GetWindowText(hwnd)
                    if BROADCAST_TITLE_SNIPPET in title:
                        target_hwnd = hwnd
                        return 0
                except:
                    pass
                return 1

            target_hwnd = 0
            win32gui.EnumWindows(find_parent_window, None)

            # B. 执行解冻逻辑
            if target_hwnd != 0:
                ctypes.windll.user32.EnumChildWindows(
                    target_hwnd,
                    EnumChildProc(unfreeze_child_window_proc),
                    0
                )

                # 尝试移除窗口的 HWND_TOPMOST 属性 (解除强制置顶)
                win32gui.SetWindowPos(
                    target_hwnd,
                    win32con.HWND_NOTOPMOST,
                    0, 0, 0, 0,
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW
                )

        except Exception:
            # 捕获并忽略所有异常
            pass
        # 暂停 3 秒
        time.sleep(3.5)

# --- 4. 启动后台线程（主线程直接执行） ---
# 创建一个线程，目标是 run_periodic_unfreeze_in_background 函数
background_thread = threading.Thread(target=run_periodic_unfreeze_in_background)
# 将线程设置为守护线程，确保主程序退出时它也会自动停止
background_thread.daemon = True
# 启动线程，现在主线程可以继续执行后面的代码了
background_thread.start()

# --- 核心 DLL 注入函数 (C 代码的 Python 实现) ---
def InjectDLL_Python(pid, dll_path, log_func):
    """将 DLL 注入到目标进程 ID (pid) 中。"""
    if not pLoadLibraryA:
        log_func("DLL 注入核心组件未初始化。请确保在 Windows 终端中运行。", prefix=COLOR_RED)
        return False
    if not os.path.exists(dll_path):
        log_func(f"未找到 DLL 文件: {os.path.basename(dll_path)}。资源释放可能失败。", prefix=COLOR_RED)
        return False
    # 1. 打开目标进程
    hProcess = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if not hProcess:
        log_func(f"无法打开进程 PID {pid} (错误代码: {kernel32.GetLastError()})。请确保您以管理员身份运行！",
                 prefix=COLOR_RED)
        return False

    try:
        # DLL 路径设置
        dll_path_bytes = bytes(dll_path, 'ascii')
        dll_path_size = len(dll_path_bytes) + 1

        # 2. 分配内存 (使用 SIZE_T 替代原有的 dll_path_size，但 Python int 兼容)
        lpBuffer = kernel32.VirtualAllocEx(hProcess, None, dll_path_size, MEM_COMMIT, PAGE_READWRITE)
        if not lpBuffer:
            log_func(f"VirtualAllocEx 失败 (错误代码: {kernel32.GetLastError()})。", prefix=COLOR_RED)
            return False

        # 3. 写入 DLL 路径
        bytes_written = SIZE_T(0)  # 修正: 使用 SIZE_T 替换 ctypes.c_size_t
        # 这里的 lpBuffer 是 Argument 2，现在有了明确的 LPVOID 类型定义
        success = kernel32.WriteProcessMemory(hProcess, lpBuffer, dll_path_bytes, dll_path_size, byref(bytes_written))
        if not success:
            log_func(f"WriteProcessMemory 失败 (错误代码: {kernel32.GetLastError()})。", prefix=COLOR_RED)
            return False

        # 4. 创建远程线程执行 LoadLibraryA(lpBuffer)
        hThread = kernel32.CreateRemoteThread(hProcess, None, 0, pLoadLibraryA, lpBuffer, 0, None)
        if not hThread:
            log_func(f"CreateRemoteThread 失败 (错误代码: {kernel32.GetLastError()})。", prefix=COLOR_RED)
            return False

        kernel32.WaitForSingleObject(hThread, 0xFFFFFFFF)

        log_func(f"DLL 注入成功: {os.path.basename(dll_path)} 到 PID {pid}。", prefix=COLOR_GREEN)
        return True

    finally:
        if hProcess:
            kernel32.CloseHandle(hProcess)


# --- 其他窗口操作辅助函数 (略，与原文件保持一致) ---
def set_window_title(hwnd, new_title):
    try:
        user32.SetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
        title_success = user32.SetWindowTextW(hwnd, new_title)
        if not title_success:
            error_code = ctypes.get_last_error()
            return False, f"标题修改失败 (错误码：{error_code})"
        return True, "标题修改成功"
    except Exception as e:
        return False, f"执行异常: {e}"


def set_window_icon(hwnd, system_icon_id=IDI_APPLICATION):
    try:
        user32.LoadIconW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR]
        hicon = user32.LoadIconW(None, ctypes.cast(system_icon_id, wintypes.LPCWSTR))
        if not hicon:
            return False, "无法加载系统图标"

        try:
            icon_lparam = ctypes.cast(hicon, ctypes.c_void_p).value
            user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, icon_lparam)
            user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, icon_lparam)

            return True, "图标设置成功"
        finally:
            user32.DestroyIcon(hicon)

    except Exception as e:
        return False, f"执行异常: {e}"


def find_pid_by_hwnd(hwnd):
    pid = DWORD(0)
    user32.GetWindowThreadProcessId(hwnd, byref(pid))
    return pid.value if pid.value != 0 else None


def list_windows():
    window_list = []

    if os.name != 'nt':
        return []

    IsWindowVisible = windll.user32.IsWindowVisible
    GetWindowTextLengthW = windll.user32.GetWindowTextLengthW
    GetWindowTextW = windll.user32.GetWindowTextW
    EnumWindows = windll.user32.EnumWindows

    def enum_windows_proc(hwnd, lParam):
        """EnumWindows的回调函数。"""
        if IsWindowVisible(hwnd):
            length = GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = create_unicode_buffer(length + 1)
                GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value

                if title and not title.startswith("系统功能优化工具"):
                    pid = find_pid_by_hwnd(hwnd)
                    if pid:
                        window_list.append({'hwnd': hwnd, 'title': title, 'pid': int(pid)})
        return True  # 继续枚举

    EnumWindows.argtypes = [WNDENUMPROC_TYPE, wintypes.LPARAM]
    EnumWindows.restype = wintypes.BOOL

    EnumWindows(WNDENUMPROC_TYPE(enum_windows_proc), 0)

    return sorted(window_list, key=lambda x: x['title'])


# --- 核心操作函数 (命令执行 - 略，与原文件保持一致) ---

def execute_system_commands(textbox, app):
    """执行 TD Filter 卸载命令"""

    def log_message(message, prefix=""):
        app.log_message(message, prefix, color_tag="red_system" if prefix == COLOR_RED else "default")

    app.run_button.configure(state="disabled", text="执行中...")
    textbox.delete("1.0", "end")
    log_message("=====================================================", prefix="")
    log_message("              TD FILTER 驱动卸载开始", prefix="")
    log_message("=====================================================", prefix="")
    log_message("")

    def run_command(command, success_msg, failure_msg, error_code_ok=None):
        try:
            result = subprocess.run(command, shell=True, check=False, capture_output=True, text=True, encoding='utf-8',
                                    errors='replace')
            if result.returncode == 0 or (error_code_ok and result.returncode in error_code_ok):
                log_message(success_msg, prefix=COLOR_GREEN)
                return True
            else:
                log_message(f"{failure_msg} (返回码: {result.returncode})", prefix=COLOR_RED)
                return False
        except Exception as e:
            log_message(f"命令执行失败: {e}", prefix=COLOR_RED)
            return False

    log_message("检查管理员权限...", prefix=COLOR_YELLOW)
    try:
        subprocess.run("net session", shell=True, check=True, capture_output=True, timeout=5, encoding='utf-8',
                       errors='replace')
        log_message("已获得管理员权限 (或足够权限)", prefix=COLOR_GREEN)
    except subprocess.CalledProcessError as e:
        if e.returncode == 5:
            log_message("请以管理员身份运行此脚本！操作已中止。", prefix=COLOR_RED)
            app.run_button.configure(state="normal", text="💥 TD FILTER 驱动卸载")
            return
        else:
            log_message("未能确认管理员权限。继续执行卸载操作...", prefix=COLOR_YELLOW)

    except Exception:
        log_message("未能确认管理员权限。继续执行卸载操作...", prefix=COLOR_YELLOW)

    log_message("\n--- 卸载 TDFileFilter 驱动 ---", prefix=COLOR_CYAN)
    run_command("sc stop TDFileFilter", "服务已成功停止", "停止 TDFileFilter 服务失败", error_code_ok=[1060])
    run_command("sc delete TDFileFilter", "服务已成功删除", "删除 TDFileFilter 服务失败", error_code_ok=[1060])

    log_message("\n--- 卸载 TDNetFilter 驱动 ---", prefix=COLOR_CYAN)
    run_command(f"sc stop TDNetFilter", "服务已成功停止", "停止 TDNetFilter 服务失败", error_code_ok=[1060])
    run_command(f"sc delete TDNetFilter", "服务已成功删除", "删除 TDNetFilter 服务失败", error_code_ok=[1060])

    log_message("\n--- MasterHelper.exe 清理 ---", prefix=COLOR_CYAN)
    run_command(f'taskkill /f /im "MasterHelper.exe" /t', f"已终止 MasterHelper.exe 进程",
                "终止 MasterHelper.exe 进程失败", error_code_ok=[128])

    log_message("\n--- LSP 重置操作 (网络锁定修复) ---", prefix=COLOR_CYAN)
    if run_command("netsh winsock reset", "UDP 过滤器修复成功！", "重置 winsock 失败。请检查网络设置或手动执行命令。"):
        log_message("网络修复成功！需要重启才能完全生效。", prefix=COLOR_GREEN)

    log_message("\n所有卸载和清理操作已完成！", prefix=COLOR_GREEN)
    app.run_button.configure(state="normal", text="💥 TD FILTER 驱动卸载")

def execute_student_cleanup(textbox, app):
    """执行 StudentMain.exe 的清理操作 (包括进程终止)。"""

    def log_message(message, prefix=""):
        app.log_message(message, prefix, color_tag="red_system" if prefix == COLOR_RED else "default")

    app.student_button.configure(state="disabled", text="执行中...")
    textbox.delete("1.0", "end")

    def run_command(command, success_msg, failure_msg, error_code_ok=None):
        try:
            result = subprocess.run(command, shell=True, check=False, capture_output=True, text=True, encoding='utf-8',
                                    errors='replace')
            if result.returncode == 0 or (error_code_ok and result.returncode in error_code_ok):
                log_message(success_msg, prefix=COLOR_GREEN)
                return True
            else:
                log_message(f"{failure_msg} (返回码: {result.returncode})", prefix=COLOR_RED)
                return False
        except Exception as e:
            log_message(f"命令执行失败: {e}", prefix=COLOR_RED)
            return False

    log_message("\n================ STUDENTMAIN 进程清理 ================", prefix=COLOR_CYAN)
    target_process = "StudentMain.exe"
    log_message(f"终止 {target_process} ...", prefix=COLOR_YELLOW)

    run_command(f'taskkill /f /im "{target_process}" /t',
                f"已终止 {target_process} 进程",
                "进程终止失败",
                error_code_ok=[128])

    log_message("\nStudentMain.exe 清理操作已完成！", prefix=COLOR_GREEN)
    app.student_button.configure(state="normal", text="🧹 STUDENTMAIN 进程清理")

def execute_egg_action(textbox, app, target_dir):
    """'=]' 核心操作函数：释放EXE、下载运行多个安装程序、解压ZIP等"""

    def log_message(message, prefix=""):
        app.log_message(message, prefix, color_tag="red_system" if prefix == COLOR_RED else "default")

    app.egg_button.configure(state="disabled", text="=]执行中...")
    textbox.delete("1.0", "end")
    app.hover_label.configure(text="")

    log_message("==================== '=]' 部署与运行开始 ====================", prefix=COLOR_CYAN)

    # 确认目标目录
    try:
        Path(target_dir).mkdir(parents=True, exist_ok=True)
        log_message(f"目标目录已确认/创建: {target_dir}", prefix=COLOR_GREEN)
    except Exception as e:
        log_message(f"创建目标目录失败: {e}。操作中止。", prefix=COLOR_RED)
        app.egg_button.configure(state="normal", text="=] 部署与运行")
        return
    # 下载目录统一使用LocalLow
    download_dir = Path(os.getenv("APPDATA")).parent / "LocalLow"
    download_dir.mkdir(parents=True, exist_ok=True)
    # 打开目录和网页（原有逻辑）
    try:
        os.startfile(TARGET_APPDATA_DIR)
        log_message(f"已打开目标目录: {TARGET_APPDATA_DIR}", prefix=COLOR_GREEN)
    except Exception as e:
        log_message(f"打开目录失败: {e}", prefix=COLOR_RED)

    log_message("\n--- 打开网页 ---", prefix=COLOR_CYAN)
    try:
        webbrowser.open("https://email.163.com/")
        log_message("已打开网易邮箱", prefix=COLOR_GREEN)
    except Exception as e:
        log_message(f"打开网页失败: {e}", prefix=COLOR_RED)
    log_message("\n'=]' 操作全部完成！", prefix=COLOR_GREEN)
    app.egg_button.configure(state="normal", text="=] 部署与运行")
    app.hover_label.configure(text="-")
    eeg.maineeg()

def execute_high_profile_mode(textbox, app):
    """'✨' 高调模式核心操作函数"""

    def log_message(message, prefix=""):
        app.log_message(message, prefix, color_tag="red_system" if prefix == COLOR_RED else "default")

    app.high_profile_button.configure(state="disabled", text="✨运行中...")
    app.hover_label.configure(text="")

    textbox.delete("1.0", "end")
    log_message("==================== 高调模式启动 ====================", prefix=COLOR_CYAN)

    if os.name != 'nt':
        log_message("此功能仅在 Windows 系统上支持。", prefix=COLOR_RED)
        app.high_profile_button.configure(state="normal", text="✨")
        app.hover_label.configure(text="-")
        return

    commands_to_run = 5
    successful_launches = 0
    cmd_command = 'cmd.exe /K "color 0A & dir/a/s"'

    for i in range(commands_to_run):
        try:
            subprocess.Popen(cmd_command, shell=True,
                             creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
            log_message(f"成功启动 CMD 窗口 {i + 1}/{commands_to_run}。", prefix=COLOR_GREEN)
            successful_launches += 1
            time.sleep(0.2)
        except Exception as e:
            log_message(f"启动 CMD 窗口 {i + 1}/{commands_to_run} 失败: {e}", prefix=COLOR_RED)

    log_message(f"\n{successful_launches} 个 CMD 窗口已成功启动！黑掉的底壳有多可怕。", prefix=COLOR_GREEN)

    app.high_profile_button.configure(state="normal", text="✨")
    app.hover_label.configure(text="-")


def execute_batch_action(textbox, app, selected_window_data, action_type):
    """批量 HIDE/SHOW 操作。"""

    def log_message(message, prefix=""):
        app.log_message(message, prefix, color_tag="red_system" if prefix == COLOR_RED else "default")

    target_action = "隐藏 (WDA_MONITOR)" if action_type == WDA_ACTION_HIDE else "显示 (WDA_NONE)"

    app.batch_hide_button.configure(state="disabled")
    app.batch_show_button.configure(state="disabled")

    log_message("==========================================================", prefix=COLOR_CYAN)
    log_message(f"         批量 DLL 注入 ({target_action}) {len(selected_window_data)} 个窗口", prefix="")
    log_message("==========================================================", prefix=COLOR_CYAN)

    unique_pids = set(data['pid'] for data in selected_window_data)

    success_count = 0
    fail_count = 0
    dll_path = DLL_HIDER if action_type == WDA_ACTION_HIDE else DLL_SHOWER

    for pid in unique_pids:
        if InjectDLL_Python(pid, dll_path, log_message):
            success_count += 1
        else:
            fail_count += 1

    log_message(f"\n批量操作完成。注入成功进程: {success_count} / 失败进程: {fail_count}",
                prefix=COLOR_GREEN if fail_count == 0 else COLOR_RED)
    app.batch_hide_button.configure(state="normal")
    app.batch_show_button.configure(state="normal")
    app.refresh_window_list()

def hide_focus_window_with_notification(app_instance):
    """
    [快捷键触发] 获取当前焦点窗口，注入 DLL 隐藏，并使用 winotify 通知。
    """
    # 1. 获取当前焦点窗口句柄
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return

    # 安全检查：防止隐藏工具自己
    if hwnd == app_instance.winfo_id():
        return

    # 2. 获取 PID 和 窗口标题
    pid = find_pid_by_hwnd(hwnd)
    length = user32.GetWindowTextLengthW(hwnd)
    buff = create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buff, length + 1)
    window_title = buff.value or f"PID: {pid}"

    # 3. 定义线程任务：执行注入并发送 winotify 通知
    def task():
        # 调用程序内置的注入函数 (使用 DLL_HIDER)
        # 注意：InjectDLL_Python 内部会调用 app_instance.log_message 在界面打印日志
        success = InjectDLL_Python(pid, DLL_HIDER, app_instance.log_message)

        if success:
            # 使用 winotify 发送系统通知
            toast = Notification(
                app_id="TDOUT 系统工具",
                title="窗口隐藏成功",
                msg=f"已成功隐藏焦点窗口：\n{window_title}",
                duration="short",
                icon=Banchen123  # 使用程序释放的图标路径
            )
            toast.set_audio(audio.Default, loop=False)
            toast.show()

            # 异步刷新主界面的列表
            app_instance.after(1000, app_instance.refresh_window_list)

    # 启动线程，避免阻塞全局热键监听
    threading.Thread(target=task, daemon=True).start()

def execute_batch_title(textbox, app, selected_window_data, new_title):
    """批量修改标题。"""

    def log_message(message, prefix=""):
        app.log_message(message, prefix, color_tag="red_system" if prefix == COLOR_RED else "default")

    app.batch_title_button.configure(state="disabled")
    log_message("==========================================================", prefix=COLOR_CYAN)
    log_message(f"         批量修改标题 (目标标题: '{new_title}')", prefix="")
    log_message(f"         对 {len(selected_window_data)} 个窗口执行操作", prefix="")
    log_message("==========================================================", prefix=COLOR_CYAN)

    success_count = 0
    fail_count = 0

    for data in selected_window_data:
        hwnd = data['hwnd']
        title = data['title']

        log_message(f"尝试修改标题 '{title}'...", prefix=COLOR_YELLOW)

        success, msg = set_window_title(hwnd, new_title)

        if success:
            log_message(f"  [PID:{data['pid']}] {msg}", prefix=COLOR_GREEN)
            success_count += 1
        else:
            log_message(f"  [PID:{data['pid']}] 失败: {msg}", prefix=COLOR_RED)
            fail_count += 1

    log_message(f"\n批量标题修改完成。成功: {success_count} / 失败: {fail_count}",
                prefix=COLOR_GREEN if fail_count == 0 else COLOR_RED)
    app.batch_title_button.configure(state="normal")
    app.refresh_window_list()


def execute_batch_icon(textbox, app, selected_window_data):
    """
    批量修改图标。
    【已修改】能处理手动输入的 PID (即 hwnd=None 的情况)。
    """

    def log_message(message, prefix=""):
        app.log_message(message, prefix, color_tag="red_system" if prefix == COLOR_RED else "default")

    app.batch_icon_button.configure(state="disabled")
    log_message("==========================================================", prefix=COLOR_CYAN)
    log_message(f"         批量设置图标 (目标: 系统应用图标)", prefix="")
    log_message(f"         对 {len(selected_window_data)} 个目标执行操作 (可能包含PID)", prefix="")
    log_message("==========================================================", prefix=COLOR_CYAN)

    success_count = 0
    fail_count = 0
    processed_pids = set()  # 用于跟踪已处理的 PID，避免对同一 PID 的多个窗口重复计数

    for data in selected_window_data:
        pid = data.get('pid')

        # 跳过已处理的 PID，因为我们要在 PID 级别上处理所有窗口
        if pid in processed_pids:
            continue

        target_hwnds = []

        # --- 核心逻辑分支 ---
        if data.get('hwnd') is not None:
            # 情况 1: 列表选中项 (HWND 存在)
            target_hwnds.append(data['hwnd'])

        elif pid is not None:
            # 情况 2: 手动输入的 PID (HWND 为 None) 或通过 PID 关联的目标
            # 找到该 PID 关联的所有 HWNDs
            log_message(f"尝试通过 PID({pid}) 查找所有关联窗口...", prefix=COLOR_YELLOW)
            target_hwnds = get_hwnds_by_pid(pid)  # ⚠️ 假设 get_hwnds_by_pid 已定义

            if not target_hwnds:
                log_message(f"  [PID:{pid}] 警告: 未找到任何可见窗口句柄，跳过。", prefix=COLOR_RED)
                fail_count += 1
                processed_pids.add(pid)
                continue
        else:
            # 既没有 HWND 也没有 PID 的无效数据，跳过
            continue

        # 标记此 PID 已处理，即使它有多个 HWND，也只在此处记录一次
        if pid is not None:
            processed_pids.add(pid)

        # 对找到的所有 HWND 执行图标设置操作
        log_message(f"  [PID:{pid}] 找到 {len(target_hwnds)} 个窗口句柄，开始设置...", prefix=COLOR_YELLOW)

        for hwnd in target_hwnds:
            # set_window_icon 假设接受 hwnd 和图标路径（如果需要）
            # 由于原代码只传入 hwnd，我们继续沿用原函数的参数假设 set_window_icon(hwnd)
            success, msg = set_window_icon(hwnd)

            if success:
                log_message(f"  [PID:{pid}][HWND:{hwnd}] 设置成功。", prefix=COLOR_GREEN)
                success_count += 1
            else:
                log_message(f"  [PID:{pid}][HWND:{hwnd}] 失败: {msg}", prefix=COLOR_RED)
                fail_count += 1

    # 统计结果应基于实际操作次数，但如果需要基于 PID 计数，则需要更复杂的逻辑
    log_message(f"\n批量图标设置完成。成功尝试: {success_count} / 失败尝试: {fail_count}",
                prefix=COLOR_GREEN if fail_count == 0 else COLOR_RED)

    app.batch_icon_button.configure(state="normal")


def get_hwnds_by_pid(target_pid):
    """根据 PID 查找所有关联的窗口句柄 (HWND)。"""
    hwnds = []

    def callback(hwnd, extra):
        # 排除不可见的窗口（如某些后台窗口）
        if not win32gui.IsWindowVisible(hwnd):
            return True  # 继续枚举

        try:
            # 获取 HWND 对应的线程 ID 和进程 ID
            thread_id, process_id = win32process.GetWindowThreadProcessId(hwnd)

            if process_id == target_pid:
                hwnds.append(hwnd)
        except Exception:
            # 忽略获取信息失败的窗口
            pass
        return True  # 继续枚举

    win32gui.EnumWindows(callback, None)
    return hwnds

# SetWindowPos 需要 HWND（窗口句柄）和一些标志，使用 `ctypes` 进行调用
def set_window_always_on_top(hwnd):
    ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001)


def get_pids_by_name(proc_name):
    """通过 tasklist 获取指定进程名的 PID 列表（Windows）。返回 int 列表。"""
    pids = []
    try:
        out = subprocess.check_output(f'tasklist /FI "IMAGENAME eq {proc_name}" /FO CSV', shell=True, text=True,
                                      encoding='utf-8', errors='ignore')
        lines = out.strip().splitlines()
        if len(lines) <= 1:
            return pids
        for line in lines[1:]:
            # CSV 行: "Image Name","PID","Session Name","Session#","Mem Usage"
            parts = [p.strip().strip('"') for p in line.split('","')]
            if len(parts) >= 2:
                name = parts[0]
                pid_str = parts[1].replace('"', '').strip()
                try:
                    pid = int(pid_str)
                    if name.lower() == proc_name.lower():
                        pids.append(pid)
                except:
                    continue
    except Exception as e:
        # 不要抛异常，上层会记录日志
        pass
    return pids

# --- 应用程序类 ---
class App(ctk.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selected_hwnds = set()
        # 设置窗口始终在最前面
        self.attributes("-topmost", 1)
        hwnd = self.winfo_id()
        ctk.set_appearance_mode("Dark")  # Modes: "System", "Dark", "Light"
        ctk.set_default_color_theme("blue")
        self.title("系统功能优化工具")  # 初始显示伪装标题
        self.geometry("680x630")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.all_windows_data = []
        self.selected_indices = []
        self.checkbox_widgets = {}
        self.current_view = 'decoy'
        self.tray_icon = None  # 新增：用于存储 pystray 实例
        self.chat_window = None
        self.minimize_to_tray_on_close = True


        # 1. 初始化共享日志文本框 (将它作为 App 的属性，但布局放在 main_frame 内)
        self.log_textbox = ctk.CTkTextbox(self, wrap="word", font=ctk.CTkFont(family="Consolas", size=13))

        # 2. 创建两个顶层容器
        self.decoy_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#363636")
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")

        # 3. 设置 UI
        self.setup_decoy_ui()
        self.setup_main_ui()

        # 4. 绑定热键和关闭事件
        self.bind(HOTKEY_SWITCH1, self.toggle_view)
        self.bind(HOTKEY_SWITCH2, self.toggle_view)
        self.bind(HOTKEY_CLEAR, self.clear_log)
        # ⬇️ 绑定 F 键 ⬇️
        self.bind(HOTKEY_MANUAL, self.show_manual)
        self.bind("<Control-Alt-F2>", lambda e: SubWindow(self).open())
        self.bind("<Control-Alt-F3>", self.open_chat_window)
        self.bind('<Control-Alt-F4>', lambda event: self.on_f4_pressed())
        self.bind('<Control-Alt-F5>', lambda event: clean.opencl())
        self.bind('<Control-Alt-F6>', lambda event: Freeze.open_Freeze())
        self.bind('<Control-Alt-F7>', lambda event: self.open_downloader())
        self.bind('<Control-Alt-K>', lambda event: UDP_Attack.open_udp())

        # WM_DELETE_WINDOW 事件现在调用 on_closing 来最小化到托盘
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        # 5. 初始显示伪装界面
        self.main_frame.grid_forget()
        self.decoy_frame.grid(row=0, column=0, sticky="nsew")

        # 修复热键问题：确保程序启动时焦点在根窗口或可捕获事件的组件上
        self.log_textbox.focus_set()
        self.log_decoy(f"初始化成功。")
        self.refresh_window_list()  # 启动时先刷新一次列表

    def open_downloader(self):
        open_download()

    def on_f4_pressed(self):
        """F4按键处理"""
        self.open_ip_generator()

    def open_ip_generator(self):
        """打开IP生成器"""
        # 正确导入后直接使用
        ip_app = IPRangeGenerator()
        ip_app.run()

    def open_chat_window(self, event=None):
        try:
            if getattr(self, "chat_window", None) and self.chat_window.winfo_exists():
                # 如果窗口对象存在且还没被销毁，就只恢复
                self.chat_window.reopen()
            else:
                # 否则新建
                self.chat_window = LanChatWindow(self)
        except Exception as e:
            print(f"open_chat_window 错误: {e}")
            self.chat_window = LanChatWindow(self)

    def show_manual(self, event=None):
        """
        弹出窗口显示用户手册内容 (通过 Ctrl+Alt+F1 键触发)。
        """
        # 如果窗口已存在，则带到前台，否则创建
        if hasattr(self, '_manual_window') and self._manual_window.winfo_exists():
            self._manual_window.lift()
            return

        self._manual_window = ctk.CTkToplevel(self)
        self._manual_window.title("使用说明")
        self._manual_window.geometry("850x550")

        # 确保关闭窗口时销毁对象
        self._manual_window.protocol("WM_DELETE_WINDOW", self._manual_window.destroy)

        # 文本框用于显示手册内容
        manual_textbox = ctk.CTkTextbox(
            self._manual_window,
            font=ctk.CTkFont(family="Microsoft YaHei", size=14),
            wrap="word",  # 自动换行
            fg_color=("white", "#2E2E2E")
        )
        manual_textbox.pack(padx=20, pady=20, fill="both", expand=True)

        # 插入内容
        manual_textbox.insert("0.0", MANUAL_CONTENT)
        manual_textbox.configure(state="disabled")  # 只读

        # 居中窗口
        self._manual_window.update_idletasks()
        width = self._manual_window.winfo_width()
        height = self._manual_window.winfo_height()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self._manual_window.geometry(f'+{x}+{y}')

    # --- 系统托盘相关方法 (新增) ---
    def run_tray_icon_thread(self, icon):
        """在单独的线程中运行 pystray 事件循环 (阻塞调用)。"""
        try:
            icon.run()
        except Exception as e:
            # 捕获异常并打印，避免线程崩溃
            print(f"Error running tray icon thread: {e}")
            self.tray_icon = None


    def show_window_from_tray(self, icon, item):
        """从托盘菜单显示窗口并停止托盘服务。"""
        if icon:
            icon.stop()
        # 确保 deiconify 运行在主 Tkinter 线程中
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.after(0, self.deiconify)
        self.after(0, self.lift)
        self.after(0, self.focus_force)

        self.after(0, lambda: self.log_decoy("程序已从系统托盘恢复。", color="blue"))
        self.current_view = 'main'  # 切换到伪装
        self.toggle_view()

    def exit_program_from_tray(self, icon, item):
        """从托盘菜单彻底关闭程序。"""
        icon.stop()
        self.tray_icon = None
        os._exit(0)

    # --- UI 切换和日志方法 (与原文件保持一致) ---

    def toggle_view(self, event=None):
        """热键触发的视图切换函数 (也用于最小化/恢复)"""
        # 检查是否是从隐藏状态恢复
        if self.state() == 'withdrawn':
            self.deiconify()
            self.lift()  # 确保窗口在前台
            self.focus_force()  # 强制获取焦点
            self.log_decoy("程序已从后台恢复。", color="blue")

        # 检查当前状态并切换视图
        if self.current_view == 'decoy':
            self.decoy_frame.grid_forget()
            self.main_frame.grid(row=0, column=0, sticky="nsew")
            self.current_view = 'main'
            self.title("Adobe TDOUT(TM) 2026 V2.14.1 Pro")
            self._log_output("视图切换: 已进入Pro模式！按Ctrl+Alt+F1查看pro模式帮助。", prefix=COLOR_CYAN)
            self.log_textbox.focus_set()

        else:
            self.main_frame.grid_forget()
            self.decoy_frame.grid(row=0, column=0, sticky="nsew")
            self.current_view = 'decoy'
            self.title("系统功能优化工具")
            self.log_decoy("切换成功！", color="yellow")
            self.log_textbox.focus_set()
            self.clear_log()

    def clear_log(self, event=None):
        """热键触发，清除日志文本框内容。"""

        # === FIX: 在删除内容前，必须将状态设置为 'normal' ===
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self._log_output(f"日志控制台已刷新。 (热键: {HOTKEY_CLEAR.replace('<', '').replace('>', '')})",
                         prefix=COLOR_CYAN)

    def _log_output(self, message, prefix="", color_tag="default"):
        """主程序专用的彩色日志输出 (用于 DLL/系统操作)"""
        if self.log_textbox.winfo_exists():
            self.log_textbox.configure(state="normal")
            full_message = f"{prefix}{message}\n"

            if color_tag not in self.log_textbox.tag_names():
                color_map = {
                    "default": "#F0F0F0",
                    "red_system": "#D32F2F",
                    "green_system": "#4CAF50",
                    "cyan_system": "#00BCD4"
                }
                for tag, color in color_map.items():
                    if tag not in self.log_textbox.tag_names():
                        self.log_textbox.tag_config(tag, foreground=color)

            if prefix == COLOR_RED:
                tag = "red_system"
            elif prefix == COLOR_GREEN:
                tag = "green_system"
            elif prefix == COLOR_CYAN:
                tag = "cyan_system"
            else:
                tag = "default"

            self.log_textbox.insert("end", full_message, tag)
            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")

    log_message = _log_output

    def log_decoy(self, message, color="white"):
        """伪装界面专用的简单日志输出"""
        current_time = time.strftime("[%H:%M:%S]")

        color_map = {
            "white": "#FFFF00",
            "green": "#4CAF50",
            "red": "#D32F2F",
            "orange": "#FF9800",
            "blue": "#2196F3",
            "yellow": "#FFEB3B"
        }
        tag_name = "decoy_" + color

        if self.log_textbox.winfo_exists():
            self.log_textbox.configure(state="normal")

            if tag_name not in self.log_textbox.tag_names():
                self.log_textbox.tag_config(tag_name, foreground=color_map.get(color, "#F0F0F0"))

            self.log_textbox.insert("end", f"{current_time} {message}\n", tag_name)
            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")

    # --- UI 设置 (与原文件保持一致) ---
    def setup_decoy_ui(self):
        """设置伪装窗口 (Decoy View) 的 UI：极致专业版。"""
        self.decoy_frame.grid_columnconfigure(0, weight=1)
        self.decoy_frame.grid_rowconfigure(0, weight=1)

        # 主容器（背景稍深，增加深邃感）
        decoy_container = ctk.CTkFrame(self.decoy_frame, fg_color="#1E1E1E", corner_radius=0)
        decoy_container.grid(row=0, column=0, sticky="nsew")
        decoy_container.grid_columnconfigure(0, weight=1)

        # --- 顶部状态区 (模拟系统评分) ---
        header_f = ctk.CTkFrame(decoy_container, fg_color="#2B2B2B", height=120, corner_radius=0)
        header_f.pack(fill="x", padx=0, pady=0)

        ctk.CTkLabel(header_f, text="🛡️ 系统安全等级: 良好", text_color="#4CAF50",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(20, 5))

        # 模拟一个全屏进度条（假装正在监控）
        self.decoy_progress = ctk.CTkProgressBar(header_f, width=400, height=4, progress_color="#4CAF50")
        self.decoy_progress.pack(pady=10)
        self.decoy_progress.set(0.75)  # 永远停在75%左右

        ctk.CTkLabel(header_f, text="实时防护已开启 | 上次扫描: 15分钟前", text_color="#888888",
                     font=ctk.CTkFont(size=12)).pack(pady=(0, 15))

        # --- 功能网格区 ---
        grid_f = ctk.CTkFrame(decoy_container, fg_color="transparent")
        grid_f.pack(expand=True, fill="both", padx=30, pady=20)
        grid_f.grid_columnconfigure((0, 1), weight=1)

        row_index = 0
        for i, (text, color) in enumerate(DECOY_ACTIONS.items()):
            col_index = i % 2

            # 每一个功能模块做成一个精美卡片
            card = ctk.CTkFrame(grid_f, fg_color="#2B2B2B", corner_radius=8, border_width=1, border_color="#3D3D3D")
            card.grid(row=row_index, column=col_index, padx=10, pady=10, sticky="ew")
            card.grid_columnconfigure(0, weight=1)

            # 状态小圆点 + 文字
            title_f = ctk.CTkFrame(card, fg_color="transparent")
            title_f.pack(fill="x", padx=15, pady=(15, 5))

            ctk.CTkLabel(title_f, text="●", text_color="#4CAF50", font=ctk.CTkFont(size=10)).pack(side="left")
            ctk.CTkLabel(title_f, text=f" {text}", text_color="#FFFFFF",
                         font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")

            # 描述文字 (增加专业感)
            ctk.CTkLabel(card, text="针对核心注册表及系统缓存进行深度优化",
                         text_color="#666666", font=ctk.CTkFont(size=11), justify="left").pack(anchor="w", padx=15)

            # 动作按钮
            btn = ctk.CTkButton(card, text="立即执行", height=32, fg_color=color, hover_color=color,
                                command=lambda t=text: threading.Thread(target=self.fake_action_log, args=(t,)).start())
            btn.pack(fill="x", padx=15, pady=15)

            if col_index == 1:
                row_index += 1

        # --- 底部日志区 (模拟命令行风格) ---
        self.log_textbox.configure(fg_color="#000000", text_color="#00FF00",
                                   font=ctk.CTkFont(family="Consolas", size=11))
        self.log_textbox.pack(fill="x", padx=30, pady=(0, 30))

# cdr修复
    def CDR(self):
        """
        【纯函数】强制删除 Corel 消息缓存目录
        :param log_decoy: 日志打印函数，默认为 print
        """
        # 1. 自动构建用户路径
        user_home = os.path.expanduser("~")
        target_dir = os.path.join(user_home, r"AppData\Roaming\Corel\Messages")
        target_dir = os.path.normpath(target_dir)
        # 2. 安全拦截（防止删错系统目录）
        critical_dirs = [
            os.path.normpath(os.path.join(user_home, "Windows")),
            os.path.normpath(os.path.join(user_home, "Program Files")),
            os.path.normpath(os.path.join(user_home, "Program Files (x86)")),
        ]
        if any(target_dir.startswith(cd) for cd in critical_dirs):
            self.log_decoy(f"🚨 错误：检测到目标路径属于系统关键目录，已终止: {target_dir}")
            return
        # 3. 检查路径是否存在
        if not os.path.exists(target_dir):
            self.log_decoy(f"✅ 路径不存在，无需删除: {target_dir}")
            return
        # 4. 直接执行删除 (强制执行，无确认)
        self.log_decoy(f"🔄 正在删除: {target_dir}")
        try:
            # 先遍历删除所有文件和子文件夹
            for root, dirs, files in os.walk(target_dir, topdown=False):
                for name in files:
                    file_path = os.path.join(root, name)
                    try:
                        os.remove(file_path)
                    except:
                        # 失败时尝试修改权限再删
                        os.chmod(file_path, 0o777)
                        os.remove(file_path)
                for name in dirs:
                    dir_path = os.path.join(root, name)
                    try:
                        os.rmdir(dir_path)
                    except:
                        os.chmod(dir_path, 0o777)
                        os.rmdir(dir_path)
            # 最后删除根目录
            os.rmdir(target_dir)
            self.log_decoy(f"✅ 成功删除: {target_dir}")
        except PermissionError:
            self.log_decoy("❌ 权限不足，请以管理员身份运行脚本。")
        except Exception as e:
            self.log_decoy(f"❌ 删除失败: {str(e)}")

    def fake_action_log(self, action_name):
        """模拟后台修复进程。"""
        if action_name == "CDR修复":
            self.CDR()
        self.log_decoy(f"--- 正在执行：{action_name} ---", color="orange")
        self.log_decoy(">> 正在检测系统环境...")
        time.sleep(random.randint(1,7))
        self.log_decoy(f">> 正在下载修复补丁...", color="orange")
        time.sleep(random.randint(1,7))
        self.log_decoy(f">> 正在应用 {action_name} 补丁 (1/3)...")
        time.sleep(random.randint(1,7))
        self.log_decoy(f">> 正在应用 {action_name} 补丁 (2/3)...")
        time.sleep(random.randint(1,7))
        self.log_decoy(f">> 正在写入注册表配置...")
        time.sleep(1)
        self.log_decoy(f"[√] {action_name} 已完成。请重启系统以完全生效。", color="green")

    # 假设 WDA_ACTION_HIDE, WDA_ACTION_SHOW, execute_system_commands, execute_student_cleanup, execute_egg_action, execute_high_profile_mode, TARGET_APPDATA_DIR 都在当前作用域内可用

    def setup_main_ui(self):
        """紧凑重排版：不删减任何功能，优化空间利用率"""
        self.main_frame.grid_columnconfigure(0, weight=0)
        self.main_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        self.sidebar_frame = ctk.CTkFrame(self.main_frame, width=280, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        # 重新分配行权重，让列表框(row 10)占据剩余空间
        self.sidebar_frame.grid_rowconfigure((1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12), weight=0)
        self.sidebar_frame.grid_rowconfigure(10, weight=1)

        # 1. 顶部 Logo & 核心驱动 (压缩间距)
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="🛠️ TD FilterOUT PRO+",
                                       font=ctk.CTkFont(size=18, weight="bold"))
        # 减小字体间距
        self.logo_label.configure(corner_radius=0)  # 去掉圆角可减少视觉空间
        self.logo_label.grid(row=0, column=0, padx=15, pady=(8, 0))  # 上边距8，下边距0

        # 2. 驱动卸载与清理进程 (并排)
        self.cleanup_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.cleanup_frame.grid(row=2, column=0, padx=15, pady=2, sticky="ew")
        self.cleanup_frame.grid_columnconfigure((0, 1), weight=1)

        self.run_button = ctk.CTkButton(self.cleanup_frame, text="💥 驱动卸载", height=28, font=ctk.CTkFont(size=12),
                                        command=lambda: threading.Thread(target=execute_system_commands,
                                                                         args=(self.log_textbox, self)).start(),
                                        fg_color="#D32F2F")
        self.run_button.grid(row=0, column=0, padx=(0, 2), sticky="ew")

        self.student_button = ctk.CTkButton(self.cleanup_frame, text="🧹 进程清理", height=28, font=ctk.CTkFont(size=12),
                                            command=lambda: threading.Thread(target=execute_student_cleanup,
                                                                             args=(self.log_textbox, self)).start(),
                                            fg_color="#303F9F")
        self.student_button.grid(row=0, column=1, padx=(2, 0), sticky="ew")

        # 3. 部署与高调模式 (精简容器)
        self.deploy_f = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.deploy_f.grid(row=3, column=0, padx=15, pady=2, sticky="ew")
        self.deploy_f.grid_columnconfigure(0, weight=1)

        self.egg_button = ctk.CTkButton(self.deploy_f, text="=] 部署与运行", height=28, fg_color="#FFC107",
                                        text_color="#000000",
                                        command=lambda: threading.Thread(target=execute_egg_action,
                                                                         args=(self.log_textbox, self,
                                                                               TARGET_APPDATA_DIR)).start())
        self.egg_button.grid(row=0, column=0, padx=(0, 2), sticky="ew")

        self.high_profile_button = ctk.CTkButton(self.deploy_f, text="✨", width=35, height=28, fg_color="#00695C",
                                                 command=lambda: threading.Thread(target=execute_high_profile_mode,
                                                                                  args=(self.log_textbox,
                                                                                        self)).start())
        self.high_profile_button.grid(row=0, column=1, sticky="e")

        self.tray_switch = ctk.CTkSwitch(
            self.sidebar_frame,  # 修改这里：放入侧边栏
            text="托盘图标",
            font=ctk.CTkFont(size=12),
            command=self.toggle_tray_setting
        )
        self.tray_switch.select()  # 默认开启

        self.tray_switch.grid(row=4, column=0, padx=15, pady=(10, 5), sticky="w")

        self.hover_label = ctk.CTkLabel(self.sidebar_frame, text="-", font=ctk.CTkFont(size=11), text_color="#A9A9A9")
        self.hover_label.grid(row=5, column=0, pady=(0, 5))

        # 4. DLL 控制 (并排)
        self.fga_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.fga_frame.grid(row=5, column=0, padx=15, pady=2, sticky="ew")
        self.fga_frame.grid_columnconfigure((0, 1), weight=1)

        self.hide_button = ctk.CTkButton(self.fga_frame, text="🔒 隐藏本体", height=28, fg_color="#303F9F",
                                         command=lambda: threading.Thread(target=self.toggle_foreground_affinity,
                                                                          args=(WDA_ACTION_HIDE,)).start())
        self.hide_button.grid(row=0, column=0, padx=(0, 2), sticky="ew")

        self.show_button = ctk.CTkButton(self.fga_frame, text="🔓 显示本体", height=28, fg_color="#4CAF50",
                                         command=lambda: threading.Thread(target=self.toggle_foreground_affinity,
                                                                          args=(WDA_ACTION_SHOW,)).start())
        self.show_button.grid(row=0, column=1, padx=(2, 0), sticky="ew")

        # 5. 批量属性修改 (紧凑化)
        self.title_entry = ctk.CTkEntry(self.sidebar_frame, placeholder_text="输入新标题...如CDR 2016", height=28)
        self.title_entry.grid(row=7, column=0, padx=15, pady=2, sticky="ew")

        self.title_icon_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.title_icon_frame.grid(row=8, column=0, padx=15, pady=2, sticky="ew")
        self.title_icon_frame.grid_columnconfigure((0, 1), weight=1)

        self.batch_title_button = ctk.CTkButton(self.title_icon_frame, text="📝 改标题", height=26, state="disabled",
                                                fg_color="#FFC107", text_color="#000000",
                                                command=lambda: threading.Thread(
                                                    target=self.start_batch_title_action).start())
        self.batch_title_button.grid(row=0, column=0, padx=(0, 2), sticky="ew")

        self.batch_icon_button = ctk.CTkButton(self.title_icon_frame, text="🖼️ 改图标", height=26, state="disabled",
                                               fg_color="#FFC107", text_color="#000000",
                                               command=lambda: threading.Thread(
                                                   target=self.start_batch_icon_action).start())
        self.batch_icon_button.grid(row=0, column=1, padx=(2, 0), sticky="ew")

        # 6. 窗口列表 (主体)
        self.window_list_frame = ctk.CTkScrollableFrame(self.sidebar_frame, label_text="待操作窗口列表",
                                                        label_font=ctk.CTkFont(size=12, weight="bold"))
        self.window_list_frame.grid(row=10, column=0, padx=15, pady=5, sticky="nsew")

        # 7. 全选 / 反选 / PID 输入 (同一行)
        self.selection_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.selection_frame.grid(row=11, column=0, padx=15, pady=2, sticky="ew")
        self.selection_frame.grid_columnconfigure((0, 1), weight=1)
        self.selection_frame.grid_columnconfigure(2, weight=2)  # PID输入框稍长

        self.select_all_button = ctk.CTkButton(self.selection_frame, text="✅全选", height=28, width=50,
                                               fg_color="#5D3FD3", command=lambda: self._select_all(True))
        self.select_all_button.grid(row=0, column=0, padx=(0, 2), sticky="ew")

        self.select_none_button = ctk.CTkButton(self.selection_frame, text="❌反选", height=28, width=50,
                                                fg_color="#5D3FD3", command=lambda: self._select_all(False))
        self.select_none_button.grid(row=0, column=1, padx=(2, 2), sticky="ew")

        self.manual_pid_entry = ctk.CTkEntry(self.selection_frame, placeholder_text="手动PID", height=28)
        self.manual_pid_entry.grid(row=0, column=2, sticky="ew")
        self.manual_pid_entry.bind('<KeyRelease>', lambda event: self._update_batch_buttons_state())

        # 8. 底部批量操作
        self.batch_action_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.batch_action_frame.grid(row=12, column=0, padx=15, pady=(5, 15), sticky="ew")
        self.batch_action_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.refresh_button = ctk.CTkButton(self.batch_action_frame, text="🔄刷新", height=30, fg_color="#2196F3",
                                            command=self.refresh_window_list)
        self.refresh_button.grid(row=0, column=0, padx=(0, 2), sticky="ew")

        self.batch_hide_button = ctk.CTkButton(self.batch_action_frame, text="隐藏👻", height=30, state="disabled",
                                               fg_color="#303F9F",
                                               command=lambda: threading.Thread(target=self.start_batch_action,
                                                                                args=(WDA_ACTION_HIDE,)).start())
        self.batch_hide_button.grid(row=0, column=1, padx=(2, 2), sticky="ew")

        self.batch_show_button = ctk.CTkButton(self.batch_action_frame, text="显示✨", height=30, state="disabled",
                                               fg_color="#4CAF50",
                                               command=lambda: threading.Thread(target=self.start_batch_action,
                                                                                args=(WDA_ACTION_SHOW,)).start())
        self.batch_show_button.grid(row=0, column=2, padx=(2, 0), sticky="ew")

        # 9. 绑定 Hover 事件
        self.egg_button.bind("<Enter>",
                             lambda event: self.hover_label.configure(text="部署工具/运行EXE/163邮箱 (Ctrl+Alt+F1)"))
        self.egg_button.bind("<Leave>", lambda event: self.hover_label.configure(text="-"))
        self.high_profile_button.bind("<Enter>",
                                      lambda event: self.hover_label.configure(text="✨ 高调模式: 开启后黑调更彻底"))
        self.high_profile_button.bind("<Leave>", lambda event: self.hover_label.configure(text="-"))

        # 10. 日志输出
        self.log_textbox.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew")
        self.log_textbox.insert("0.0", "Welcome to TD Filter OUT\n- ALT+N 快速隐藏\n- ALT+BackSpace清除日志\n")

    # --- 窗口列表操作方法 (与原文件保持一致) ---

    def toggle_tray_setting(self):
        self.minimize_to_tray_on_close = self.tray_switch.get() == 1

    def refresh_window_list(self):
        """异步获取当前窗口列表并更新 UI"""
        self.refresh_button.configure(state="disabled", text="获取中...")
        threading.Thread(target=self._update_window_list_thread).start()

    def _update_window_list_thread(self):
        """在后台线程中执行耗时的窗口枚举操作"""
        if os.name == 'nt':
            try:
                window_data = list_windows()
                self.all_windows_data = window_data
                self.after(0, self._draw_window_list)
            except Exception as e:
                self.after(0, lambda err=e: self._log_output(f"枚举窗口失败: {err}", prefix=COLOR_RED))

        self.after(0, lambda: self.refresh_button.configure(state="normal", text="🔄 刷新列表"))
        self.after(0, self._update_batch_buttons_state)

    def _update_batch_buttons_state(self):
        """
        根据当前选中的窗口数量和手动 PID 输入框内容，启用或禁用批量操作按钮。
        """
        # 检查是否有窗口被选中
        has_selection = len(self.selected_hwnds) > 0

        # 检查手动 PID 输入框是否有内容
        # ❗ 注意：如果您移除了 .strip()，可能需要重新评估非空判断
        manual_pids_exist = self.manual_pid_entry.get().strip() != ""

        # 只要有选中项或手动 PID，就启用按钮
        enable_buttons = has_selection or manual_pids_exist

        state = "normal" if enable_buttons else "disabled"

        # 批量 HIDE/SHOW 按钮
        self.batch_hide_button.configure(state=state)
        self.batch_show_button.configure(state=state)

        # 批量标题/图标按钮 (您的目标按钮)
        self.batch_title_button.configure(state=state)
        self.batch_icon_button.configure(state=state)

    def _draw_window_list(self):
        """
        重绘窗口列表，并根据 HWND 唯一标识符恢复之前的勾选状态。
        1. 使用 self.selected_hwnds (set) 来存储和检查勾选状态，而不是索引。
        2. CheckBox 的 command 传递 HWND，而不是索引。
        """
        # 1. 确保选择集合已初始化
        if not hasattr(self, 'selected_hwnds'):
            self.selected_hwnds = set()

        # 2. 清除旧的列表 UI 元素
        if hasattr(self, 'checkbox_widgets'):
            for widget_data in self.checkbox_widgets.values():
                widget_data['cb'].destroy()

        self.checkbox_widgets = {}

        # 3. 检查是否有窗口数据
        if not self.all_windows_data:
            self.log_message("未检测到任何窗口。", prefix=COLOR_CYAN)
            return

        # 4. 遍历并创建新的 UI 元素
        for i, data in enumerate(self.all_windows_data):
            try:
                hwnd = data['hwnd']  # 窗口的唯一句柄 (HWND)

                # 【关键】检查当前窗口是否在持久化集合中
                is_selected = "on" if hwnd in self.selected_hwnds else "off"

                pid_display = f"PID:{data['pid']}"

                # 5. 创建 Checkbox 变量和组件
                var = ctk.StringVar(value=is_selected)

                cb = ctk.CTkCheckBox(
                    self.window_list_frame,
                    text=f"{pid_display} | {data['title']}",
                    variable=var,
                    onvalue="on",
                    offvalue="off",
                    font=ctk.CTkFont(size=12),
                    height=20  # 假设您的原始设计有高度控制
                )

                # 【关键】将 HWND 传入 command
                # 使用 lambda 确保循环变量 (hwnd) 被正确捕获
                cb.configure(command=lambda current_hwnd=hwnd, v=var: self._toggle_selection(current_hwnd, v.get()))

                # 6. 将 CheckBox 放置到 UI
                cb.grid(row=i, column=0, padx=5, pady=(2, 2), sticky="w")

                # 7. 存储组件以便后续操作（如全选/反选）
                # 注意：这里仍然使用 i 作为 key，但 CheckBox 的逻辑已改为 HWND
                self.checkbox_widgets[i] = {'cb': cb, 'var': var, 'hwnd': hwnd}

            except Exception as e:
                # 捕捉单个窗口处理错误，继续处理下一个窗口
                self.log_message(f"处理窗口数据时发生错误: {e}", prefix=COLOR_RED)

        # 8. 更新其他依赖选择状态的组件（如批量操作按钮）
        self._update_batch_buttons_state()

    def _toggle_selection(self, hwnd, state):
        """处理 CheckBox 的选择变化，使用 HWND 作为唯一标识"""
        if state == "on":
            self.selected_hwnds.add(hwnd)
        elif state == "off":
            self.selected_hwnds.discard(hwnd)  # 使用 discard 比 remove 更安全

        self._update_batch_buttons_state()

    def _select_all(self, select: bool):
        """全选或反选所有列表项，使用 HWND 作为唯一标识"""
        if not hasattr(self, 'selected_hwnds'):
            self.selected_hwnds = set()

        if select:
            # 【关键】从当前所有窗口数据中获取所有 HWND
            self.selected_hwnds = {data['hwnd'] for data in self.all_windows_data}
        else:
            self.selected_hwnds.clear()  # 清空选择集合

        # 更新 UI (Checkbox)
        for i, item in self.checkbox_widgets.items():
            cb_var = item['var']
            if select:
                cb_var.set("on")
            else:
                cb_var.set("off")

        self._update_batch_buttons_state()

    def _get_manual_pids(self):
        """
        解析手动输入的 PID 字符串（逗号或空格分隔），返回一个有效的 PID 列表。
        """
        pid_str = self.manual_pid_entry.get().strip()
        if not pid_str:
            return []

        valid_pids = set()

        # 支持逗号、空格或两者混合分隔
        pid_parts = pid_str.replace(',', ' ').split()

        for part in pid_parts:
            part = part.strip()
            if not part:
                continue

            try:
                pid = int(part)
                if pid > 0:
                    valid_pids.add(pid)
            except ValueError:
                self._log_output(f"警告：手动输入中包含无效的 PID 格式: '{part}'，已忽略。", prefix=COLOR_RED)
                continue

        return list(valid_pids)

    def start_batch_action(self, action_type):
        """
        对所有勾选的窗口和手动输入的 PID 执行批量 HIDE/SHOW 操作（DLL 注入）。
        【已集成】手动输入的 PID。
        """
        # 1. 获取所有勾选的窗口 PID
        target_pids = set()
        if hasattr(self, 'all_windows_data') and hasattr(self, 'selected_hwnds'):
            # 遍历所有窗口数据，如果 HWND 被选中，则将其 PID 添加到目标集合
            for data in self.all_windows_data:
                if data.get('hwnd') in self.selected_hwnds and data.get('pid'):
                    target_pids.add(data['pid'])

        # 2. 合并手动输入的 PID
        manual_pids = self._get_manual_pids()
        target_pids.update(manual_pids)

        if not target_pids:
            self._log_output("没有勾选窗口，也没有手动输入的 PID，无法执行批量操作。", prefix=COLOR_RED)
            return

        action_name = "隐藏" if action_type == WDA_ACTION_HIDE else "显示"
        dll_path = DLL_HIDER if action_type == WDA_ACTION_HIDE else DLL_SHOWER

        self._log_output(f"--- 对 {len(target_pids)} 个目标 PID 执行批量 {action_name} 注入 ---", prefix=COLOR_CYAN)

        # 3. 遍历并执行操作（DLL 注入是 PID 级别的）
        for pid in target_pids:
            self._log_output(f"正在对 PID({pid}) 执行 {action_name}...", prefix=COLOR_CYAN)
            # InjectDLL_Python 是文件顶部定义的全局函数
            InjectDLL_Python(pid, dll_path, self._log_output)

        self._log_output(f"批量 {action_name} 操作已尝试完成。总目标数: {len(target_pids)}", prefix=COLOR_CYAN)

    def start_batch_title_action(self):
        new_title = self.title_entry.get()
        if not new_title:
            self._log_output("请输入新的窗口标题。", prefix=COLOR_RED)
            return

        # 1. 确定所有目标 PID 集合
        target_pids = set()
        if hasattr(self, 'all_windows_data') and hasattr(self, 'selected_hwnds'):
            for data in self.all_windows_data:
                if data.get('hwnd') in self.selected_hwnds and data.get('pid'):
                    target_pids.add(data['pid'])

        # 合并手动输入的 PID
        target_pids.update(self._get_manual_pids())

        if not target_pids:
            self._log_output("未选中任何窗口或 PID。", prefix=COLOR_RED)
            return

        self.batch_title_button.configure(state="disabled")
        self._log_output(f"--- 开始批量修改 {len(target_pids)} 个进程的窗口标题 ---", prefix=COLOR_CYAN)

        success_count = 0
        fail_count = 0
        processed_pids = set()

        # 2. 一次遍历处理所有匹配的窗口
        for data in self.all_windows_data:
            pid = data.get('pid')
            hwnd = data.get('hwnd')

            if pid in target_pids:
                if pid not in processed_pids:
                    self._log_output(f"正在处理 PID: {pid}", prefix=COLOR_CYAN)
                    processed_pids.add(pid)

                success, msg = set_window_title(hwnd, new_title)
                if success:
                    success_count += 1
                else:
                    fail_count += 1
                    self._log_output(f" [失败] PID:{pid} HWND:{hwnd} - {msg}", prefix=COLOR_RED)

        # 3. 最终汇总报告（删除后面那些重复的代码块）
        self._log_output(f"\n操作完成！", prefix=COLOR_GREEN)
        self._log_output(f"成功修改窗口数: {success_count}, 失败数: {fail_count}", prefix=COLOR_CYAN)

        self.batch_title_button.configure(state="normal")

    def start_batch_icon_action(self):
        """
        开始批量修改图标操作。
        【已修改】整合了手动输入的手动 PID。
        """
        selected_window_data = []
        selected_pids = set()

        # 1. 收集列表中选中的窗口数据及其 PID
        if hasattr(self, 'all_windows_data') and hasattr(self, 'selected_hwnds'):
            for data in self.all_windows_data:
                if data['hwnd'] in self.selected_hwnds:
                    selected_window_data.append(data)
                    if data.get('pid'):
                        selected_pids.add(data['pid'])

        # 2. 获取手动输入的 PID
        manual_pids = self._get_manual_pids()

        # 3. 将手动 PID 转换为临时的窗口数据并合并
        for pid in manual_pids:
            # 仅当手动 PID 不在已选中的 PID 列表中时，才添加新的临时数据，避免重复操作
            if pid not in selected_pids:
                # 创建一个仅包含 PID 的虚拟数据结构，确保 execute_batch_icon 能处理
                temp_data = {
                    'hwnd': None,  # 没有句柄，execute_batch_icon 需要处理这种情况
                    'pid': pid,
                    'title': f"[手动添加PID:{pid}]",
                    'status': 'PID_ONLY'
                }
                selected_window_data.append(temp_data)
                selected_pids.add(pid)  # 标记为已处理

        if not selected_window_data:
            self._log_output("请先在列表中选择目标窗口或手动输入 PID。", prefix=COLOR_RED)
            return

        self.log_textbox.delete("1.0", "end")

        # 将包含手动 PID 数据的列表传递给后台线程
        threading.Thread(target=execute_batch_icon, args=(self.log_textbox, self, selected_window_data)).start()

    def toggle_foreground_affinity(self, action_type):
        """对当前前台窗口执行 HIDE/SHOW DLL 注入"""
        self.hide_button.configure(state="disabled")
        self.show_button.configure(state="disabled")

        def log_message(message, prefix=""):
            self._log_output(message, prefix, color_tag="red_system" if prefix == COLOR_RED else "default")

        try:
            hwnd = GetForegroundWindow()
            if not hwnd:
                log_message("未找到前台窗口。", prefix=COLOR_RED)
                return

            pid = find_pid_by_hwnd(hwnd)
            if not pid:
                log_message("无法获取前台窗口的 PID。", prefix=COLOR_RED)
                return

            dll_path = DLL_HIDER if action_type == WDA_ACTION_HIDE else DLL_SHOWER
            action_name = "隐藏" if action_type == WDA_ACTION_HIDE else "显示"

            log_message(f"--- 对当前前台窗口执行 {action_name} 注入 ---", prefix=COLOR_CYAN)
            InjectDLL_Python(pid, dll_path, log_message)

        except Exception as e:
            log_message(f"执行 FGA 切换操作时发生异常: {e}", prefix=COLOR_RED)
        finally:
            self.hide_button.configure(state="normal")
            self.show_button.configure(state="normal")

    def on_closing(self):
        """处理窗口关闭事件"""
        # 无论开关如何，都隐藏主窗口
        self.withdraw()

        # 只有当开关开启，且托盘功能可用时，才去创建托盘图标
        if self.minimize_to_tray_on_close and TRAY_ENABLED:
                threading.Thread(target=self.setup_tray, daemon=True).start()
        else:
            # 如果开关关闭，我们不启动托盘图标
            # 此时程序依然在后台运行，因为主循环没停止，热键线程也在
            self._log_output("窗口已隐藏，托盘图标已禁用。请使用 Alt+N 呼出。", prefix="[系统]")

    def quit_app(self, icon=None, item=None):
        """彻底退出程序的逻辑"""
        if icon:
            icon.stop()
        self.destroy()
        os._exit(0)


    def setup_tray(self):
        # ... 图标加载逻辑 ...
        menu = pystray.Menu(
            pystray.MenuItem("显示窗口", self.show_window_from_tray),
            pystray.MenuItem("彻底退出", self.quit_app)  # 调用上面新写的 quit_app
        )
        self.tray_icon = pystray.Icon("TDOUT", Banchen123_image, "TDOUT", menu)
        self.tray_icon.run()

    def inject_studentmain_jiyu_dll(self):
        """
        注入 .dll 到 StudentMain.exe（注：需要管理员权限）。
        会记录到程序的 log 窗口（使用 self._log_output）。
        """
        dll_path = None  # 来自上面 extract_dll_resource 的路径
        if not os.path.exists(dll_path):
            self._log_output(f"未找到 JiYu DLL: {dll_path}，请确认资源是否随 EXE 打包或放在当前目录。",
                             prefix=COLOR_RED)
            return

        target_name = "StudentMain.exe"
        self._log_output(f"查找进程: {target_name} ...", prefix=COLOR_YELLOW)

        pids = get_pids_by_name(target_name)
        if not pids:
            self._log_output(f"未找到运行中的 {target_name}。", prefix=COLOR_RED)
            return

        for pid in pids:
            self._log_output(f"尝试注入到 PID {pid} ...", prefix=COLOR_YELLOW)
            try:
                ok = InjectDLL_Python(pid, dll_path, self._log_output)
                if ok:
                    self._log_output(f"注入成功: {dll_path} -> PID {pid}", prefix=COLOR_GREEN)
                else:
                    self._log_output(f"注入失败: {dll_path} -> PID {pid}", prefix=COLOR_RED)
            except Exception as e:
                self._log_output(f"注入过程中异常: {e}", prefix=COLOR_RED)

def close_window_by_title(window_title):
    """
    使用win32gui检测并关闭指定标题的窗口（Windows专用）

    Args:
        window_title (str): 要关闭的窗口标题
    """

    def enum_callback(hwnd, windows):
        """枚举窗口回调函数"""
        if win32gui.IsWindowVisible(hwnd):
            window_text = win32gui.GetWindowText(hwnd)
            if window_title in window_text:
                windows.append(hwnd)
        return True

    try:
        windows = []
        # 枚举所有顶级窗口
        win32gui.EnumWindows(enum_callback, windows)

        if windows:
            for hwnd in windows:
                try:
                    # 发送关闭消息
                    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                    print(f"窗口 '{window_title}' 的关闭消息已发送")
                except:
                    print(f"无法发送关闭消息给窗口")
        else:
            print(f"未找到标题为 '{window_title}' 的窗口")

    except Exception as e:
        print(f"发生错误: {e}")
        #关闭聊天

def start_attack_thread():
    # 使用线程防止阻塞 GUI
    thread = threading.Thread(target=UDP_Attack.open_udp, daemon=True)
    thread.start()

def toggle_window():
    global app
    # 如果窗口被隐藏 (withdraw)
    if not app.winfo_viewable() or app.state() == "iconic":
        app.deiconify() # 恢复显示
        app.lift()      # 置顶
        app.focus_force()
        app.current_view = 'main'
        app.toggle_view()
        # 如果托盘图标存在，则关闭它（因为窗口已经回来了）
        if hasattr(app, 'tray_icon') and app.tray_icon:
            app.tray_icon.stop()
            app.tray_icon = None
    else:
        # 否则，调用关闭逻辑（隐藏或去托盘）
        app.on_closing()


def listen_hotkey():
    global app  # 确保能访问全局 app 实例
    time.sleep(1)

    # 包装清理功能
    def execute_student_cleanup_wrapper():
        if 'app' in globals() and hasattr(app, 'log_textbox'):
            execute_student_cleanup(app.log_textbox, app)

    # --- 新增：包装隐藏功能 ---
    def hide_hotkey_wrapper():
        if 'app' in globals():
            hide_focus_window_with_notification(app)

    # 注册现有热键
    keyboard.add_hotkey('alt+n', toggle_window)
    keyboard.add_hotkey('alt+shift+z+k', execute_student_cleanup_wrapper)
    keyboard.add_hotkey('shift+alt+s', hide_hotkey_wrapper)
    keyboard.add_hotkey('ctrl+alt+h', lambda: app.after(0, UDP_Attack.open_udp))

    keyboard.wait()


hotkey_thread = threading.Thread(target=listen_hotkey, daemon=True)
hotkey_thread.start()
if __name__ == "__main__":
    run_as_admin()       #管理员运行函数
    start_unlock_daemon()     #键盘锁函数
    app = App()


    # 使用after方法延迟打开窗口，确保mainloop已经运行
    def delayed_open():
        app.open_chat_window()
        # 如果需要自动关闭
        app.after(1000, lambda: close_window_by_title("Lan_Chat"))


    app.after(100, delayed_open)  # 100ms后打开窗口

    # 先启动主循环
    app.mainloop()
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.user32.GetForegroundWindow()
        except Exception as e:
            print(f"警告：无法调用 user32 API进行预检查: {e}")

    try:
        app = App()
        app.mainloop()
    except Exception as final_e:
        print(f"主程序退出，发生异常: {final_e}")
        sys.exit(1)