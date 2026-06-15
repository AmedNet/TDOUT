# subwindow_panel.py
import ctypes
import os
import queue
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from ctypes import wintypes

import customtkinter as ctk
import requests
import win32con
import win32gui

from combat import NSudo, WindowsClean, Hook
from modules import Freeze
from modules.Download import open_download
from modules.tools import get_mythware_password_from_regedit

#颜色
COLOR_RED = "\033[31m"
COLOR_GREEN = "\033[32m"
COLOR_YELLOW = "\033[33m"
COLOR_CYAN = "\033[36m"
COLOR_RESET = "\033[0m"

#下载路径
APPpath = os.path.expandvars("%USERPROFILE%\\AppData\\LocalLow")
# 下载链接
CLASH_URL = "https://github.com/clash-verge-rev/clash-verge-rev/releases/download/v2.4.7/Clash.Verge_2.4.7_x64-setup.exe"
QBT_URL = "https://github.com/c0re100/qBittorrent-Enhanced-Edition/releases/download/release-5.1.3.10/qbittorrent_enhanced_5.1.3.10_x64_setup.exe"
BATTLE = "https://downloader.battlenet.com.cn/download/installer/win/1.0.62/Battle.net-Setup-CN.exe"
DDNET = "https://ddnet.org/downloads/DDNet-19.8-win64.zip"
CF = "http://dldir1.qq.com/tgc/wegame/miniloader/WeGameMiniLoader.CF.6.9.8.1742.2022023092201.exe"
steam="https://media.st.dl.eccdnx.com/client/installer/SteamSetup.exe"
UUG="https://api.nrd.nie.163.com/api/v1/release/dl/1?channel=91vip"
def restart_explorer():
    # 先结束 explorer.exe 进程，再重新启动它
    subprocess.run(["taskkill", "/f", "/im", "explorer.exe"])
    subprocess.Popen(["explorer.exe"])

def run_exe_as_admin(exe_path: str) -> bool:
    """
    以管理员身份运行可执行文件
    :param exe_path: 可执行文件路径
    :return: 成功返回 True，否则 False
    """
    class SHELLEXECUTEINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("fMask", wintypes.ULONG),
            ("hwnd", wintypes.HWND),
            ("lpVerb", wintypes.LPCSTR),
            ("lpFile", wintypes.LPCSTR),
            ("lpParameters", wintypes.LPCSTR),
            ("lpDirectory", wintypes.LPCSTR),
            ("nShow", wintypes.INT),
            ("hInstApp", wintypes.HINSTANCE),
            ("lpIDList", wintypes.LPVOID),
            ("lpClass", wintypes.LPCSTR),
            ("hKeyClass", wintypes.HKEY),
            ("dwHotKey", wintypes.DWORD),
            ("hIcon", wintypes.HANDLE),
            ("hProcess", wintypes.HANDLE),
        ]

    sei = SHELLEXECUTEINFO()
    sei.cbSize = ctypes.sizeof(SHELLEXECUTEINFO)
    sei.fMask = 0x00000040  # SEE_MASK_NOCLOSEPROCESS
    sei.lpVerb = b"runas"  # 以管理员身份运行
    sei.lpFile = exe_path.encode("utf-8")
    sei.lpParameters = None
    sei.nShow = 1
    sei.hwnd = None
    sei.hInstApp = None
    sei.lpIDList = None
    sei.lpClass = None
    sei.hKeyClass = None
    sei.dwHotKey = 0
    sei.hIcon = None
    sei.hProcess = None

    try:
        success = ctypes.windll.shell32.ShellExecuteExA(ctypes.byref(sei))
        if not success:
            err = ctypes.get_last_error()
            print(f"以管理员身份运行失败，错误码: {err}")
            return False
        return True
    except Exception as e:
        print(f"run_exe_as_admin 异常: {e}")
        return False

def run_cmd_as_system(cmd: str) -> bool:
    """
    以提升/系统权限运行 cmd（使用 ShellExecuteExA runas）
    注意：这个函数使用 ShellExecuteExA + "runas"，通常会弹出 UAC 提升对话框，可能不是 Windows NT System 帐户。
    :param cmd: 要执行的 CMD 命令字符串
    :return: 成功返回 True，否则 False
    """
    class SHELLEXECUTEINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("fMask", wintypes.ULONG),
            ("hwnd", wintypes.HWND),
            ("lpVerb", wintypes.LPCSTR),
            ("lpFile", wintypes.LPCSTR),
            ("lpParameters", wintypes.LPCSTR),
            ("lpDirectory", wintypes.LPCSTR),
            ("nShow", wintypes.INT),
            ("hInstApp", wintypes.HINSTANCE),
            ("lpIDList", wintypes.LPVOID),
            ("lpClass", wintypes.LPCSTR),
            ("hKeyClass", wintypes.HKEY),
            ("dwHotKey", wintypes.DWORD),
            ("hIcon", wintypes.HANDLE),
            ("hProcess", wintypes.HANDLE),
        ]

    sei = SHELLEXECUTEINFO()
    sei.cbSize = ctypes.sizeof(SHELLEXECUTEINFO)
    sei.fMask = 0x00000040  # SEE_MASK_NOCLOSEPROCESS
    sei.lpVerb = b"runas"
    sei.lpFile = b"cmd.exe"
    sei.lpParameters = f"/k {cmd}".encode("utf-8")
    sei.nShow = 1
    sei.hwnd = None
    sei.hInstApp = None
    sei.lpIDList = None
    sei.lpClass = None
    sei.hKeyClass = None
    sei.dwHotKey = 0
    sei.hIcon = None
    sei.hProcess = None

    try:
        success = ctypes.windll.shell32.ShellExecuteExA(ctypes.byref(sei))
        if not success:
            # 获取错误码（如果可用）
            err = ctypes.get_last_error()
            print(f"ShellExecuteExA 失败，错误码: {err}")
            return False

        # 等待进程结束
        if sei.hProcess:
            ctypes.windll.kernel32.WaitForSingleObject(sei.hProcess, -1)
            ctypes.windll.kernel32.CloseHandle(sei.hProcess)
        return True
    except Exception as e:
        print(f"run_cmd_as_system 异常: {e}")
        return False
class SubWindow:

    def __init__(self, master, APPpath=None):
        self.master = master
        if APPpath is None:
            APPpath = os.path.expandvars(r"%USERPROFILE%\AppData\LocalLow")
        self.APPpath = APPpath
        self._subwindow = None
        self.progressbar = None
        self.taskbar_hidden = False  # 跟踪任务栏状态

    def open(self):
        if self._subwindow and self._subwindow.winfo_exists():
            self._subwindow.lift()
            self._subwindow.focus_force()
            return

        SUBW_W, SUBW_H = 200, 200
        self._subwindow = ctk.CTkToplevel(self.master)
        self._subwindow.title("Schweizer")

        screen_w = self.master.winfo_screenwidth()
        screen_h = self.master.winfo_screenheight()
        x = (screen_w // 2) - (SUBW_W // 2)
        y = (screen_h // 2) - (SUBW_H // 2)
        self._subwindow.geometry(f"{SUBW_W}x{SUBW_H}+{x}+{y}")

        self._subwindow.resizable(True, True)
        self._subwindow.minsize(320, 300)
        self._subwindow.attributes("-topmost", 1)

        tabs = ctk.CTkTabview(self._subwindow)
        tabs.pack(padx=10, pady=10, fill="both", expand=True)


        for name in ["Combat", "Auto", "Web"]:
            tabs.add(name)

        # Combat 页面 - 滚动容器
        combat_scroll = ctk.CTkScrollableFrame(tabs.tab("Combat"))
        combat_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(combat_scroll, text="对抗页面", font=ctk.CTkFont(size=15)).pack(pady=8)

        hide_button = ctk.CTkButton(
            combat_scroll,
            text="🛡️ 隐藏/显示任务栏",  # 更新文本更清晰
            font=ctk.CTkFont(size=16, weight="bold"),  # 增大字体并加粗
            fg_color="#000080",  # 深蓝色
            hover_color="#191970",  # 午夜蓝
            text_color="#FFFFFF",  # 白色文字
            border_width=2,  # 添加边框
            border_color="#4169E1",  # 皇家蓝边框
            corner_radius=12,  # 圆角
            height=45,  # 增加高度
            width=220,  # 增加宽度
            command=lambda: threading.Thread(
                target=self.toggle_taskbar,
                daemon=True
            ).start()
        )
        hide_button.pack(pady=15, padx=10)  # 增加内边距

        deploy_button = ctk.CTkButton(
            combat_scroll,
            text="🛠️ 部署NSudo",
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#2E8B57",  # 海洋绿 (更有“部署”和“成功”的感觉)
            hover_color="#1E6B47",
            text_color="#FFFFFF",
            border_width=2,
            border_color="#3CB371",
            corner_radius=12,
            height=45,
            width=220,
            # 使用 lambda 在后台线程中调用保存并打开的函数，避免界面卡死
            command=lambda: threading.Thread(
                target=lambda: NSudo.save_base64_and_open(NSudo.sample_base64, "NSudo.exe"),
                daemon=True
            ).start()
        )
        deploy_button.pack(pady=15, padx=10)

        deploy_button = ctk.CTkButton(
            combat_scroll,
            text="🛠️ 部署Window2Clear",
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#436452",  # 海洋绿 (更有“部署”和“成功”的感觉)
            hover_color="#1B3F2E",
            text_color="#FFFFFF",
            border_width=2,
            border_color="#3CB371",
            corner_radius=12,
            height=45,
            width=220,
            # 使用 lambda 在后台线程中调用保存并打开的函数，避免界面卡死
            command=lambda: threading.Thread(
                target=lambda: NSudo.save_base64_and_open(WindowsClean.Windows_clean_base64, "Window2Clear.exe"),
                daemon=True
            ).start()
        )

        deploy_button.pack(pady=15, padx=10)
        Freeze_button = ctk.CTkButton(
            combat_scroll,
            text="🧊 冻结管理器",
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#2E778D",
            hover_color="#1E2B6C",
            text_color="#FFFFFF",
            border_width=2,
            border_color="#3D94B3",
            corner_radius=12,
            height=45,
            width=220,
            # 使用 lambda 在后台线程中调用保存并打开的函数，避免界面卡死
            command=lambda: threading.Thread(
                target=lambda: Freeze.open_Freeze(),
                daemon=True
            ).start()
        )
        Freeze_button.pack(pady=15, padx=10)

        DLL_button = ctk.CTkButton(
            combat_scroll,
            text="💉 极域钩子",
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#8D2E2E",
            hover_color="#6C481E",
            text_color="#FFFFFF",
            border_width=2,
            border_color="#B33D3D",
            corner_radius=12,
            height=45,
            width=220,
            # 使用 lambda 在后台线程中调用保存并打开的函数，避免界面卡死
            command=lambda: threading.Thread(
                target=lambda: Hook.open_hook(),
                daemon=True
            ).start()
        )
        DLL_button.pack(pady=15, padx=10)

        mouse_button = ctk.CTkButton(
            combat_scroll,
            text="🗝️ 获取密码",
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#996633",
            hover_color="#666600",
            text_color="#FFFF00",
            border_width=2,
            border_color="#CCCC33",
            corner_radius=12,
            height=45,
            width=220,
            # 使用 lambda 在后台线程中调用保存并打开的函数，避免界面卡死
            command=lambda: threading.Thread(
                target=lambda: self.show_selectable_alert(),
                daemon=True
            ).start()
        )
        mouse_button.pack(pady=15, padx=10)

        # Auto 页面 - 滚动容器
        auto_scroll = ctk.CTkScrollableFrame(tabs.tab("Auto"))
        auto_scroll.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(auto_scroll, text="用于放一些自动执行的功能", font=ctk.CTkFont(size=15)).pack(pady=10)

        # 错误信息 Label，默认隐藏
        self.error_label = ctk.CTkLabel(auto_scroll, text="", text_color="red", font=ctk.CTkFont(size=13))
        self.error_label.pack(padx=10, pady=(10, 0))
        self.error_label.pack_forget()

        # 下载进度条，默认隐藏
        self.progressbar = ctk.CTkProgressBar(auto_scroll)
        self.progressbar.pack(padx=20, pady=(5, 10), fill="x")
        self.progressbar.set(0)
        self.progressbar.pack_forget()

        ctk.CTkButton(
            auto_scroll,
            text="📁 程序目录",
            width=240,
            height=42,
            fg_color="#4CAF50",
            hover_color="#388E3C",
            corner_radius=10,
            command=self._open_local_low
        ).pack(pady=10)

        # --- Clash 下载按钮 (更新 command) ---
        ctk.CTkButton(
            auto_scroll,
            text="⬇️ 下载 Clash",
            width=240,
            height=42,
            fg_color="#2196F3",
            hover_color="#1769AA",
            corner_radius=10,
            command=lambda: threading.Thread(target=self._download_file, args=(CLASH_URL,)).start()
            # <--- 调用 _download_file
        ).pack(pady=10)

        ctk.CTkButton(
            auto_scroll,
            text="⬇️ 下载 UU远程",
            width=240,
            height=42,
            fg_color="#27C8F5",
            hover_color="#005A73",
            corner_radius=10,
            command=lambda: threading.Thread(target=self._download_file, args=(UUG,)).start()
            # <--- 调用 _download_file
        ).pack(pady=10)

        # --- [新增] qBittorrent 下载按钮 ---
        ctk.CTkButton(
            auto_scroll,
            text="⬇️ 下载 qBittorrent",
            width=240,
            height=42,
            fg_color="#33A650",  # 使用新的颜色区分
            hover_color="#288F44",
            corner_radius=10,
            command=lambda: threading.Thread(target=self._download_file, args=(QBT_URL,)).start()
            # <--- 调用 _download_file
        ).pack(pady=10)

        ctk.CTkButton(
            auto_scroll,
            text="⬇️ 下载 DDNET",
            width=240,
            height=42,
            fg_color="#FE9900",
            hover_color="#D78100",
            corner_radius=10,
            command=lambda: threading.Thread(target=self._download_file, args=(DDNET,)).start()
            # <--- 调用 _download_file
        ).pack(pady=10)

        ctk.CTkButton(
            auto_scroll,
            text="⬇️ 下载 steam",
            width=240,
            height=42,
            fg_color="#435980",
            hover_color="#2F3C51",
            corner_radius=10,
            command=lambda: threading.Thread(target=self._download_file, args=(steam,)).start()
            # <--- 调用 _download_file
        ).pack(pady=10)

        ctk.CTkButton(
            auto_scroll,
            text="⬇️ 下载 CF",
            width=240,
            height=42,
            fg_color="#FF4500",
            hover_color="#C93500",
            corner_radius=10,
            command=lambda: threading.Thread(target=self._download_file, args=(CF,)).start()
            # <--- 调用 _download_file
        ).pack(pady=10)

        ctk.CTkButton(
            auto_scroll,
            text="⬇️ 下载 守望先锋",
            width=240,
            height=42,
            fg_color="#9CDCDF",
            hover_color="#1769AA",
            corner_radius=10,
            command=lambda: threading.Thread(target=self._download_file, args=(BATTLE,)).start()
            # <--- 调用 _download_file
        ).pack(pady=10)

        restart_btn = ctk.CTkButton(
            auto_scroll,
            text="🔄 重启资源管理器",
            width=240,
            height=42,
            fg_color="#FF5722",
            hover_color="#E64A19",
            corner_radius=10,
            command=lambda: threading.Thread(target=restart_explorer).start()
        )
        restart_btn.pack(pady=10)

        # 原来的 System CMD 按钮（可选保留）
        black_btn = ctk.CTkButton(
            auto_scroll,
            text="🛡️System CMD",
            width=240,
            height=42,
            fg_color="#000000",
            border_color="#FFFFFF",
            border_width=1.5,
            text_color="#FFFFFF",
            hover_color="#333333",
            corner_radius=10,
            command=lambda: threading.Thread(
                target=lambda: self._run_cmd_and_log("whoami && systeminfo | findstr /i \"操作系统版本\"")
            ).start()
        )
        black_btn.pack(pady=10)

        # 新的多线程下载器按钮
        downloader_btn = ctk.CTkButton(
            auto_scroll,
            text="⬇️ 多线程下载器",
            width=240,
            height=42,
            fg_color="#2E8B57",
            border_color="#3CB371",
            border_width=1.5,
            text_color="#FFFFFF",
            hover_color="#1E6B47",
            corner_radius=10,
            command=lambda: threading.Thread(
                target=self.open_downloader,
                daemon=True
            ).start()
        )
        downloader_btn.pack(pady=10)

        # Web 页面 - 滚动容器
        web_scroll = ctk.CTkScrollableFrame(tabs.tab("Web"))
        web_scroll.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(web_scroll, text="快捷打开一些网页", font=ctk.CTkFont(size=15)).pack(pady=10)

        buttons = [
            ("BiliBili", "https://www.bilibili.com/"),
            ("抖音", "https://www.douyin.com/"),
            ("UU远程", "https://uuyc.163.com/"),
            ("4399", "https://www.4399.com/"),
            ("扫雷", "https://www.minesweeper.cn/"),
            ("minecraft(PCL)", "https://ltcat.lanzouv.com/b0aj6gsid"),
            ("FNFgames", "https://www.play-games.com/fnf-games.html"),
            ("OSU", "https://osu.ppy.sh/"),
            ("Sparebeat", "https://sparebeat.com/"),
            ("hackergame", "https://byrut.org"),
            ("DDNet", "https://ddnet.org/"),
            ("IDM(885w)", "https://www.lanzoux.com/iHddG332n7sh"),
            ("51", "https://wikipedia4.ftzkrqf.cc/"),
            ("IKUUU", "https://ikuuu.nl/"),
            ("Free SSR", "https://shadowsocksr.org/free-node/"),
            ("Everything", "https://www.lanzouo.com/b573047"),
            ("网站导航", "https://lkssite.vip/"),
        ]

        import webbrowser
        for name, url in buttons:
            ctk.CTkButton(
                web_scroll,
                text=name,
                fg_color="#4CAF50",
                hover_color="#388E3C",
                command=lambda link=url: webbrowser.open(link)
            ).pack(padx=10, pady=5, fill="x")

        self._subwindow.update_idletasks()
        width, height = self._subwindow.winfo_width(), self._subwindow.winfo_height()
        self._subwindow.geometry(f"{width}x{height}+20+20")
        self._subwindow.focus_force()

    def _run_cmd_and_log(self, cmd: str):
        """在后台以提升权限运行 cmd，并把结果写到程序日志里（通过 self._log_output）。"""
        try:
            self._log_output(f"准备执行命令: {cmd}", prefix=COLOR_YELLOW)
        except Exception:
            print(f"准备执行命令: {cmd}")

        try:
            ok = run_cmd_as_system(cmd)
            if ok:
                try:
                    self._log_output("命令执行完成（可能已弹出提升窗口）。", prefix=COLOR_GREEN)
                except Exception:
                    print("命令执行完成（可能已弹出提升窗口）。")
            else:
                try:
                    self._log_output("命令执行失败。", prefix=COLOR_RED)
                except Exception:
                    print("命令执行失败。")
        except Exception as e:
            try:
                self._log_output(f"执行命令时异常: {e}", prefix=COLOR_RED)
            except Exception:
                print(f"执行命令时异常: {e}")

    def _open_local_low(self):
        path = os.path.expandvars(r"%USERPROFILE%\AppData\LocalLow")
        if os.path.exists(path):
            subprocess.Popen(f'explorer "{path}"')
        else:
            print(f"目录不存在: {path}")

    def _download_file(self, url: str):
        self.error_label.pack_forget()
        if not hasattr(self, 'stop_event'):
            self.stop_event = threading.Event()
        self.stop_event.clear()

        try:
            if not os.path.isdir(self.APPpath):
                raise FileNotFoundError(f"目录不存在: {self.APPpath}")

            # ========== 关键修改：处理重定向，获取真实下载地址和正确文件大小 ==========
            session = requests.Session()
            session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
            head_resp = session.head(url, allow_redirects=True, timeout=30)
            final_url = head_resp.url  # 最终下载地址
            total_length = int(head_resp.headers.get('content-length', 0))

            if total_length == 0:
                # 降级：用 GET 流式获取大小
                resp = session.get(final_url, stream=True, allow_redirects=True)
                total_length = int(resp.headers.get('content-length', 0))
                resp.close()
                if total_length == 0:
                    raise Exception("无法获取文件大小或文件为空")

            # 获取文件名（优先从 Content-Disposition 提取）
            content_disposition = head_resp.headers.get('content-disposition', '')
            if 'filename=' in content_disposition:
                import re
                match = re.search(r'filename[=*]?["\']?([^"\';]+)', content_disposition)
                if match:
                    filename = match.group(1)
                else:
                    filename = os.path.basename(final_url)
            else:
                filename = os.path.basename(final_url)
            filename = filename.replace('/', '_').replace('\\', '_')
            local_filename = os.path.join(self.APPpath, filename)

            # ========== 以下保持你的原始多线程写入逻辑，只替换 url 为 final_url，并添加完整性校验 ==========
            thread_count = 48  # 原为64，可适当降低避免网络压力
            chunk_size = total_length // thread_count
            # 预分配文件空间
            with open(local_filename, 'wb') as f:
                f.seek(total_length - 1)
                f.write(b'\0')

            self.progressbar.pack()
            self.progressbar.set(0)

            progress_queue = queue.Queue()
            self.downloaded_bytes = 0

            def download_range(start, end, file_path):
                headers = {'Range': f'bytes={start}-{end}'}
                # 使用 session 和 final_url
                with session.get(final_url, headers=headers, stream=True, timeout=30) as r:
                    r.raise_for_status()
                    with open(file_path, 'rb+') as f:
                        f.seek(start)
                        for chunk in r.iter_content(chunk_size=8192):
                            if self.stop_event.is_set():
                                break
                            if chunk:
                                f.write(chunk)
                                progress_queue.put(len(chunk))

            def update_progress():
                if not self.progressbar.winfo_exists() or self.stop_event.is_set():
                    return
                try:
                    while True:
                        self.downloaded_bytes += progress_queue.get_nowait()
                except queue.Empty:
                    pass

                if self.downloaded_bytes < total_length:
                    self.progressbar.set(self.downloaded_bytes / total_length)
                    self.progressbar.after(100, update_progress)
                else:
                    self.progressbar.set(1.0)
                    # 下载完成后校验文件大小
                    actual_size = os.path.getsize(local_filename)
                    if actual_size != total_length:
                        raise Exception(f"文件大小不匹配: 预期{total_length}, 实际{actual_size}")
                    print(f"下载完成: {local_filename}")
                    run_exe_as_admin(local_filename)

            self.progressbar.after(100, update_progress)

            def start_download():
                with ThreadPoolExecutor(max_workers=thread_count) as executor:
                    for i in range(thread_count):
                        start = i * chunk_size
                        end = (i + 1) * chunk_size - 1 if i < thread_count - 1 else total_length - 1
                        executor.submit(download_range, start, end, local_filename)

            threading.Thread(target=start_download, daemon=True).start()

        except Exception as e:
            error_msg = f"下载失败: {e}"
            self.error_label.configure(text=error_msg)
            self.error_label.pack()
            self.progressbar.pack_forget()
            # 清理不完整的文件
            if os.path.exists(local_filename):
                os.remove(local_filename)

    def toggle_taskbar(self):
        """切换任务栏显示状态"""
        try:
            if not self.taskbar_hidden:
                self.hide_taskbar()
            else:
                self.show_taskbar()

        except Exception as e:
            print(f"操作任务栏时出错: {e}")

    def hide_taskbar(self):
        """隐藏任务栏和相关组件"""
        try:
            # 隐藏主任务栏
            taskbar = win32gui.FindWindow("Shell_TrayWnd", None)
            if taskbar:
                win32gui.ShowWindow(taskbar, win32con.SW_HIDE)

            # 隐藏开始按钮（可选）
            self.hide_start_button()

            # 隐藏系统托盘（可选）
            self.hide_system_tray()

            self.taskbar_hidden = True
            print("任务栏已隐藏")

        except Exception as e:
            print(f"隐藏任务栏失败: {e}")

    def show_taskbar(self):
        """显示任务栏和相关组件"""
        try:
            # 显示主任务栏
            taskbar = win32gui.FindWindow("Shell_TrayWnd", None)
            if taskbar:
                win32gui.ShowWindow(taskbar, win32con.SW_SHOW)

            # 显示开始按钮（如果之前隐藏了）
            self.show_start_button()

            # 显示系统托盘（如果之前隐藏了）
            self.show_system_tray()

            self.taskbar_hidden = False
            print("任务栏已显示")

        except Exception as e:
            print(f"显示任务栏失败: {e}")

    def hide_start_button(self):
        """隐藏开始按钮"""
        try:
            start_button = win32gui.FindWindow("Button", "Start")
            if start_button:
                win32gui.ShowWindow(start_button, win32con.SW_HIDE)
        except:
            pass

    def show_start_button(self):
        """显示开始按钮"""
        try:
            start_button = win32gui.FindWindow("Button", "Start")
            if start_button:
                win32gui.ShowWindow(start_button, win32con.SW_SHOW)
        except:
            pass

    def hide_system_tray(self):
        """隐藏系统托盘"""
        try:
            tray = win32gui.FindWindow("TrayNotifyWnd", None)
            if tray:
                win32gui.ShowWindow(tray, win32con.SW_HIDE)
        except:
            pass

    def show_system_tray(self):
        """显示系统托盘"""
        try:
            tray = win32gui.FindWindow("TrayNotifyWnd", None)
            if tray:
                win32gui.ShowWindow(tray, win32con.SW_SHOW)
        except:
            pass

    def show_selectable_alert(self):
        """优化版：更大更舒展的可选择提示窗"""
        import tkinter
        root = tkinter.Toplevel()
        root.title("已经尝试获取密码")
        # 增加宽度到 500，视觉上更稳重
        root.geometry("500x350")
        root.resizable(False, False)
        root.configure(bg='white')  # 背景设为白色更现代

        # 获取密码函数
        get_mythware_password_from_regedit()

        # 主容器：增加 padding 创造“呼吸感”
        main_container = tkinter.Frame(root, bg='white', padx=20, pady=20)
        main_container.pack(fill=tkinter.BOTH, expand=True)

        # 标题（可选，增加层次感）
        title_label = tkinter.Label(
            main_container,
            text="提示：",
            font=("微软雅黑", 12, "bold"),
            bg='white',
            fg='#333333'
        )
        title_label.pack(anchor='w', pady=(0, 10))

        # 文本容器
        text_frame = tkinter.Frame(main_container, bg='#f8f9fa', bd=1, relief=tkinter.SOLID)
        text_frame.pack(fill=tkinter.BOTH, expand=True)

        scrollbar = tkinter.Scrollbar(text_frame)
        scrollbar.pack(side=tkinter.RIGHT, fill=tkinter.Y)

        # 增大字号到 11，增加 spacing3 (段后距)
        text_box = tkinter.Text(
            text_frame,
            wrap=tkinter.WORD,
            font=("微软雅黑", 11),
            bg='#f8f9fa',
            fg='#444444',
            relief=tkinter.FLAT,
            padx=10,
            pady=10,
            spacing3=8,  # 行间距优化
            yscrollcommand=scrollbar.set,
            selectbackground='#0078d7',
            selectforeground='white'
        )

        message = (
            "尝试获取到的密码已保存为: Student_Pwd_key.txt\n"
            "存放位置: AppData\\Local\\Temp\n"
            "请使用记事本打开该文件\n\n"
            "如果密码不对或没有(旧版极域)：\n"
            "1. 在regedit(注册表)中搜索 Student 关键词查找\n"
            "2. 使用极域超级密码：mythware_super_password"
        )

        text_box.insert("1.0", message)
        text_box.config(state='disabled')
        text_box.pack(side=tkinter.LEFT, fill=tkinter.BOTH, expand=True)
        scrollbar.config(command=text_box.yview)

        # 底部按钮区域
        btn_frame = tkinter.Frame(root, bg='#f0f0f0', pady=10) # 浅色底色区分功能区
        btn_frame.pack(fill=tkinter.X, side=tkinter.BOTTOM)

        tkinter.Button(
            btn_frame,
            text="确认并关闭",
            font=("微软雅黑", 10),
            command=root.destroy,
            width=12,
            bg='white',
            cursor="hand2"
        ).pack()

        # 居中算法
        root.update_idletasks()
        x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
        y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
        root.geometry(f'+{x}+{y}')

        return root

    def open_downloader(self):
        open_download()

