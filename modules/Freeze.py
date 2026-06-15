import os
import threading

import customtkinter as ctk
import psutil
import win32con
import win32gui
import win32ui
from PIL import Image


class FreezeWindow(ctk.CTkToplevel):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)

        # 窗口基础设置
        self.title("Freeze Pro")
        self.geometry("680x650")
        self.minsize(650, 650)

        self.attributes("-topmost", True) #权威置顶

        # 数据控制
        self.full_process_data = []
        self.selected_pids = set()
        self.icon_cache = {}

        # 【核心：防止图片报错的关键列表】
        self._current_page_icons = []

        # 分页与定时器
        self.current_page = 0
        self.page_size = 40
        self.refresh_timer = None
        self.default_icon = self.get_default_icon()

        # 初始化UI
        self.setup_ui()

        # 拦截关闭协议，清理定时器
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 初始扫描
        self.trigger_full_scan()

    def get_default_icon(self):
        # 创建一个空图标作为占位符
        img = Image.new('RGBA', (32, 32), (80, 80, 80, 255))
        return ctk.CTkImage(img, size=(20, 20))

    def setup_ui(self):
        # 配置网格权重：侧边栏固定，主区拉伸
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- 1. 左侧侧边栏 (更窄、更硬朗) ---
        self.sidebar = ctk.CTkFrame(self, width=160, corner_radius=0, border_width=1, border_color="#333")
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # 标题紧凑化
        ctk.CTkLabel(self.sidebar, text="FREEZER", font=("Impact", 24), text_color="#E74C3C").pack(pady=(20, 0))
        ctk.CTkLabel(self.sidebar, text="PRO VERSION", font=("Arial", 10, "bold"), text_color="#888").pack(pady=(0, 20))

        # 刷新控制组
        refresh_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        refresh_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(refresh_frame, text="刷新间隔:", font=("Microsoft YaHei", 11)).pack(anchor="w")
        self.speed_menu = ctk.CTkOptionMenu(
            refresh_frame, values=["手动", "2s", "5s"], height=28, corner_radius=4,
            command=self.change_refresh_speed
        )
        self.speed_menu.pack(fill="x", pady=5)
        self.speed_menu.set("手动")

        # --- 侧边栏：强制结束区 ---
        kill_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        kill_frame.pack(fill="x", padx=10, pady=(20, 0))

        ctk.CTkLabel(kill_frame, text="系统级操作", font=("Microsoft YaHei", 11, "bold"), text_color="#E74C3C").pack(
            anchor="w")

        self.btn_system_kill = ctk.CTkButton(
            kill_frame,
            text="⚡ 强制杀进程",
            fg_color="#FF0000",
            hover_color="#000000",
            height=35,
            corner_radius=4,
            command=self.execute_taskkill_system  # 绑定下面的系统调用方法
        )
        self.btn_system_kill.pack(fill="x", pady=5)

        # 底部计数器
        self.status_label = ctk.CTkLabel(self.sidebar, text="Selected: 0", font=("Consolas", 12))
        self.status_label.pack(side="bottom", pady=20)

        # --- 2. 主内容区 ---
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=10, pady=(10, 0))
        self.main_area.grid_columnconfigure(0, weight=1)
        self.main_area.grid_rowconfigure(2, weight=1)  # 滚动区权重最大

        # A. 顶部工具栏 (整合搜索)
        self.top_bar = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        # 搜索组合框
        search_box = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        search_box.pack(side="left", fill="x", expand=True)

        self.search_entry = ctk.CTkEntry(search_box, placeholder_text="搜索进程名...", height=30, corner_radius=2)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=2)

        self.pid_search_entry = ctk.CTkEntry(search_box, placeholder_text="PID", width=60, height=30, corner_radius=2)
        self.pid_search_entry.pack(side="left", padx=2)

        ctk.CTkButton(self.top_bar, text="刷新", width=60, height=30, corner_radius=2,
                      command=self.trigger_full_scan).pack(side="left", padx=2)
        ctk.CTkButton(self.top_bar, text="清空", width=60, height=30, corner_radius=2,
                      fg_color="#3D3D3D", command=self.deselect_all).pack(side="right", padx=2)

        # B. 紧凑表头 (减少高度，深浅色区分)
        self.header = ctk.CTkFrame(self.main_area, fg_color="#252525", height=30, corner_radius=0)
        self.header.grid(row=1, column=0, sticky="ew")
        self.header.grid_propagate(False)

        headers = [("选", 40), ("图标", 45), ("PID", 70), ("状态", 75), ("进程名称", 200)]
        for i, (text, w) in enumerate(headers):
            lbl = ctk.CTkLabel(self.header, text=text, width=w, font=("Microsoft YaHei", 11, "bold"),
                               text_color="#AAA", anchor="center" if i < 2 else "w")
            lbl.grid(row=0, column=i, padx=2, pady=2)

        # C. 滚动容器 (背景调深，强化对比)
        self.scroll_frame = ctk.CTkScrollableFrame(self.main_area, fg_color="#121212", corner_radius=0)
        self.scroll_frame.grid(row=2, column=0, sticky="nsew")

        # D. 分页跳转栏 (高度压缩)
        self.pager = ctk.CTkFrame(self.main_area, fg_color="transparent", height=40)
        self.pager.grid(row=3, column=0, pady=5)

        self.prev_btn = ctk.CTkButton(self.pager, text="<", width=30, height=26, corner_radius=2,
                                      command=self.prev_page)
        self.prev_btn.pack(side="left", padx=2)

        self.page_info = ctk.CTkLabel(self.pager, text="1 / 1", width=60, font=("Consolas", 11))
        self.page_info.pack(side="left", padx=5)

        self.next_btn = ctk.CTkButton(self.pager, text=">", width=30, height=26, corner_radius=2,
                                      command=self.next_page)
        self.next_btn.pack(side="left", padx=2)

        # 跳转区紧凑化
        self.jump_entry = ctk.CTkEntry(self.pager, width=40, height=26, corner_radius=2, placeholder_text="页")
        self.jump_entry.pack(side="left", padx=(10, 2))
        self.jump_entry.bind("<Return>", lambda e: self.jump_to_page())
        ctk.CTkButton(self.pager, text="GO", width=35, height=26, corner_radius=2, command=self.jump_to_page).pack(
            side="left")

        # --- 3. 底部操作栏 (强对比色，高度适中) ---
        self.bottom_bar = ctk.CTkFrame(self, height=60, fg_color="#1A1A1A", corner_radius=0, border_width=1,
                                       border_color="#333")
        self.bottom_bar.grid(row=1, column=1, sticky="ew")
        self.bottom_bar.grid_propagate(False)

        # 使用两个醒目的功能按钮
        btn_freeze = ctk.CTkButton(self.bottom_bar, text="❄️ 批量冻结", fg_color="#0089FF", hover_color="#1A00FF",
                                   font=("Microsoft YaHei", 13, "bold"), corner_radius=4,
                                   command=lambda: self.batch_operate("suspend"))
        btn_freeze.pack(side="left", expand=True, padx=(20, 10), pady=12, fill="both")

        btn_resume = ctk.CTkButton(self.bottom_bar, text="🔥 批量恢复", fg_color="#FF9A00", hover_color="#A66400",
                                   font=("Microsoft YaHei", 13, "bold"), corner_radius=4,
                                   command=lambda: self.batch_operate("resume"))
        btn_resume.pack(side="left", expand=True, padx=(10, 20), pady=12, fill="both")

    def execute_taskkill_system(self):
        """模拟管理员 PowerShell 执行 taskkill /f"""
        import subprocess

        targets = list(self.selected_pids)
        if not targets:
            return

        # 遍历选中的 PID 并强制结束
        for pid in targets:
            try:
                # /f 强制, /t 包含子进程, /pid 指定进程号
                # shell=True 确保在系统 shell 环境下执行，创建窗口隐藏
                cmd = f"taskkill /f /t /pid {pid}"
                subprocess.run(
                    ["cmd", "/c", cmd],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            except Exception as e:
                print(f"执行失败: {e}")

        # 清理状态并刷新
        self.selected_pids.clear()
        self.status_label.configure(text="选中: 0")
        self.trigger_full_scan()

    def get_icon(self, path):
        if not path or not os.path.exists(path): return self.default_icon
        if path in self.icon_cache: return self.icon_cache[path]
        try:
            large, _ = win32gui.ExtractIconEx(path, 0)
            if large:
                hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
                hbmp = win32ui.CreateBitmap()
                hbmp.CreateCompatibleBitmap(hdc, 32, 32)
                mdc = hdc.CreateCompatibleDC()
                mdc.SelectObject(hbmp)
                win32gui.DrawIconEx(mdc.GetHandleOutput(), 0, 0, large[0], 32, 32, 0, None, win32con.DI_NORMAL)
                bmpinfo = hbmp.GetInfo();
                bmpstr = hbmp.GetBitmapBits(True)
                img = Image.frombuffer('RGBA', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRA', 0, 1)
                win32gui.DestroyIcon(large[0])
                ctk_img = ctk.CTkImage(img, size=(20, 20))
                self.icon_cache[path] = ctk_img
                return ctk_img
        except:
            pass
        return self.default_icon

    def trigger_full_scan(self):
        threading.Thread(target=self._scan_thread, daemon=True).start()

    def _scan_thread(self):
        name_q = self.search_entry.get().lower()
        pid_q = self.pid_search_entry.get().strip()
        temp = []
        for proc in psutil.process_iter(['pid', 'name', 'exe', 'status']):
            try:
                p = proc.info
                if pid_q and str(p['pid']) != pid_q: continue
                if name_q and name_q not in p['name'].lower(): continue
                temp.append(p)
            except:
                continue
        self.full_process_data = temp
        self.after(0, self.render_current_page)

    def render_current_page(self):
        # 释放上一页图片的强引用
        for child in self.scroll_frame.winfo_children():
            child.destroy()
        self._current_page_icons.clear()

        start = self.current_page * self.page_size
        end = start + self.page_size
        page_data = self.full_process_data[start:end]
        total_p = max(1, (len(self.full_process_data) + self.page_size - 1) // self.page_size)

        self.page_info.configure(text=f"{self.current_page + 1} / {total_p} 页 (共{len(self.full_process_data)}条)")

        for p in page_data:
            row = ctk.CTkFrame(self.scroll_frame, fg_color="transparent", height=35)
            row.pack(fill="x", pady=1)
            row.grid_columnconfigure(4, weight=1)
            row.grid_propagate(False)

            cb = ctk.CTkCheckBox(row, text="", width=40, command=lambda pid=p['pid']: self.toggle_selection(pid))
            if p['pid'] in self.selected_pids: cb.select()
            cb.grid(row=0, column=0, padx=5)

            # 获取并存储图标引用
            icon = self.get_icon(p['exe'])
            self._current_page_icons.append(icon)

            img_lbl = ctk.CTkLabel(row, text="", image=icon, width=50)
            img_lbl.grid(row=0, column=1)
            img_lbl._image_ref = icon  # 第三重保护

            ctk.CTkLabel(row, text=str(p['pid']), width=80, anchor="w", font=("Consolas", 12)).grid(row=0, column=2,
                                                                                                    padx=5)
            is_stop = p['status'] == 'stopped'
            ctk.CTkLabel(row, text="冻结" if is_stop else "运行", text_color="#FF4B4B" if is_stop else "#00FF7F",
                         width=80, anchor="w").grid(row=0, column=3)
            ctk.CTkLabel(row, text=p['name'], anchor="w", font=("Segoe UI", 12)).grid(row=0, column=4, padx=10,
                                                                                      sticky="ew")

    def jump_to_page(self):
        try:
            val = int(self.jump_entry.get()) - 1
            max_p = (len(self.full_process_data) + self.page_size - 1) // self.page_size
            if 0 <= val < max_p:
                self.current_page = val
                self.render_current_page()
        except:
            pass

    def change_refresh_speed(self, choice):
        if self.refresh_timer: self.after_cancel(self.refresh_timer)
        if choice == "手动": return
        self.auto_refresh_loop(int(choice.replace("s", "")) * 1000)

    def auto_refresh_loop(self, ms):
        self.trigger_full_scan()
        self.refresh_timer = self.after(ms, lambda: self.auto_refresh_loop(ms))

    def toggle_selection(self, pid):
        if pid in self.selected_pids:
            self.selected_pids.remove(pid)
        else:
            self.selected_pids.add(pid)
        self.status_label.configure(text=f"选中: {len(self.selected_pids)}")

    def deselect_all(self):
        self.selected_pids.clear()
        self.status_label.configure(text="选中: 0")
        self.render_current_page()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.render_current_page()

    def next_page(self):
        if (self.current_page + 1) * self.page_size < len(self.full_process_data):
            self.current_page += 1
            self.render_current_page()

    def batch_operate(self, action):
        def run():
            for pid in list(self.selected_pids):
                try:
                    p = psutil.Process(pid)
                    if action == "suspend":
                        p.suspend()
                    else:
                        p.resume()
                except:
                    pass
            self.after(0, self.trigger_full_scan)

        threading.Thread(target=run, daemon=True).start()

    def on_closing(self):
        if self.refresh_timer:
            self.after_cancel(self.refresh_timer)
        self.destroy()


# --- 主程序集成调用示例 ---
def open_Freeze():
    # 自动查找是否存在实例，防止重复打开多个窗口
    if not hasattr(open_Freeze, "instance") or not open_Freeze.instance.winfo_exists():
        open_Freeze.instance = FreezeWindow()
    open_Freeze.instance.deiconify()  # 如果最小化了则还原
    open_Freeze.instance.focus()


# --- 调试与独立运行逻辑 ---

if __name__ == "__main__":
    # 1. 初始化 ctk 主实例 (单独启动时必须有 root)
    root = ctk.CTk()
    root.title("调试模式 - 主窗口")

    # 2. 为了美观，我们可以隐藏掉这个调试用的主窗口
    # 或者让它变小，只作为一个后台存在
    root.geometry("200x100")
    ctk.CTkLabel(root, text="调试模式运行中\n子窗口已弹出").pack(expand=True)

    # 3. 实例化你的进程管理器
    # 此时 master 指向 root
    app = FreezeWindow(master=root)


    # 4. 确保关闭子窗口时，主调试进程也退出
    def on_debug_close():
        app.on_closing()
        root.quit()
        root.destroy()


    app.protocol("WM_DELETE_WINDOW", on_debug_close)

    # 5. 进入事件循环
    root.mainloop()