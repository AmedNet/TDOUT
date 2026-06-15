import os
import subprocess
import threading
import tkinter as tk
import urllib.request
from tkinter import messagebox

import customtkinter as ctk


class CompactExeRunner(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("EXE批量运行工具")
        self.geometry("600x500")  # 稍微增大窗口以容纳新功能

        # 默认配置
        self.default_folder_name = "banchen_123-limbuscompany"
        self.exe_files = []
        self.running_processes = []

        # 初始化UI组件
        self.initialize_variables()
        # 创建界面
        self.setup_ui()
        # 自动扫描
        self.scan_for_exe_files()

    def initialize_variables(self):
        """初始化UI变量"""
        # 延迟变量
        self.delay_var = tk.BooleanVar(value=True)
        # 管理员权限变量
        self.admin_var = tk.BooleanVar(value=False)
        # 磁盘选择变量
        self.disk_vars = {}

    def setup_ui(self):
        """创建紧凑的界面布局"""
        # 使用网格布局更紧凑
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ========== 标题 ==========
        title_label = ctk.CTkLabel(
            self,
            text="EXE批量运行工具",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.grid(row=0, column=0, pady=(10, 5), sticky="w", padx=15)

        # ========== 设置区域 ==========
        settings_frame = ctk.CTkFrame(self, height=40)
        settings_frame.grid(row=1, column=0, padx=15, pady=(0, 5), sticky="ew")
        settings_frame.grid_propagate(False)
        settings_frame.grid_columnconfigure(1, weight=1)

        # 文件夹设置
        folder_label = ctk.CTkLabel(
            settings_frame,
            text="目标文件夹:",
            font=ctk.CTkFont(size=12)
        )
        folder_label.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="w")

        self.folder_entry = ctk.CTkEntry(
            settings_frame,
            placeholder_text="输入文件夹名称",
            width=180
        )
        self.folder_entry.insert(0, self.default_folder_name)
        self.folder_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        # 扫描按钮
        self.scan_button = ctk.CTkButton(
            settings_frame,
            text="扫描",
            command=self.scan_for_exe_files,
            width=60
        )
        self.scan_button.grid(row=0, column=2, padx=(5, 10), pady=10)

        # ========== 磁盘选择区域 ==========
        self.disk_frame = ctk.CTkFrame(self)
        self.disk_frame.grid(row=2, column=0, padx=15, pady=(0, 5), sticky="nsew")

        self.setup_disk_selection()
        self.setup_tools_section()
        self.setup_exe_list_section()

        # ========== 选项区域 ==========
        options_frame = ctk.CTkFrame(self)
        options_frame.grid(row=3, column=0, padx=15, pady=(0, 5), sticky="ew")
        options_frame.grid_columnconfigure(1, weight=1)

        # 延迟选项
        delay_check = ctk.CTkCheckBox(
            options_frame,
            text="延迟启动:",
            variable=self.delay_var,
            onvalue=True,
            offvalue=False
        )
        delay_check.grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")

        self.delay_entry = ctk.CTkEntry(
            options_frame,
            width=60
        )
        self.delay_entry.insert(0, "1")
        self.delay_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        delay_unit = ctk.CTkLabel(
            options_frame,
            text="秒",
            font=ctk.CTkFont(size=12)
        )
        delay_unit.grid(row=0, column=2, padx=(0, 10), pady=5, sticky="w")

        # 管理员权限选项
        admin_check = ctk.CTkCheckBox(
            options_frame,
            text="管理员权限",
            variable=self.admin_var,
            onvalue=True,
            offvalue=False
        )
        admin_check.grid(row=0, column=3, padx=(20, 5), pady=5, sticky="w")

        # ========== 状态和执行区域 ==========
        action_frame = ctk.CTkFrame(self)
        action_frame.grid(row=4, column=0, padx=15, pady=(0, 5), sticky="ew")

        # 状态标签
        self.status_label = ctk.CTkLabel(
            action_frame,
            text="就绪",
            text_color="green",
            font=ctk.CTkFont(size=11)
        )
        self.status_label.pack(side="left", padx=(10, 20), pady=5)

        # 执行按钮
        self.execute_button = ctk.CTkButton(
            action_frame,
            text="执行选中的EXE文件",
            command=self.execute_selected_exes,
            width=150,
            height=32
        )
        self.execute_button.pack(side="right", padx=(0, 10), pady=5)

    def setup_disk_selection(self):
        """设置磁盘选择区域"""
        # 磁盘标签和按钮
        disk_header = ctk.CTkFrame(self.disk_frame, height=30)
        disk_header.pack(fill="x", padx=5, pady=(5, 0))
        disk_header.grid_propagate(False)

        disk_label = ctk.CTkLabel(
            disk_header,
            text="搜索磁盘:",
            font=ctk.CTkFont(size=12)
        )
        disk_label.grid(row=0, column=0, padx=(10, 20), pady=5, sticky="w")

        # 获取磁盘
        self.disks = self.get_available_disks()

        # 磁盘选择按钮（紧凑布局）
        disk_buttons_frame = ctk.CTkFrame(disk_header)
        disk_buttons_frame.grid(row=0, column=1, sticky="w")

        for i, disk in enumerate(self.disks):
            var = tk.BooleanVar(value=True)
            self.disk_vars[disk] = var

            checkbox = ctk.CTkCheckBox(
                disk_buttons_frame,
                text=f"{disk}:",
                variable=var,
                onvalue=True,
                offvalue=False,
                width=50
            )
            checkbox.grid(row=0, column=i, padx=2)

        # 全选/取消按钮
        select_all_btn = ctk.CTkButton(
            disk_header,
            text="全选",
            command=self.select_all_disks,
            width=50,
            height=20,
            font=ctk.CTkFont(size=10)
        )
        select_all_btn.grid(row=0, column=2, padx=(20, 5), sticky="e")

        deselect_all_btn = ctk.CTkButton(
            disk_header,
            text="取消",
            command=self.deselect_all_disks,
            width=50,
            height=20,
            font=ctk.CTkFont(size=10)
        )
        deselect_all_btn.grid(row=0, column=3, padx=(0, 10), sticky="e")

    def setup_tools_section(self):
        """设置工具按钮区域"""
        tools_frame = ctk.CTkFrame(self.disk_frame)
        tools_frame.pack(fill="x", padx=5, pady=5)

        # 汉化工具按钮
        self.chinese_tool_button = ctk.CTkButton(
            tools_frame,
            text="汉化工具",
            command=self.download_chinese_tool,
            width=100,
            height=28,
            fg_color="#2AA876",
            hover_color="#207A55"
        )
        self.chinese_tool_button.pack(side="left", padx=(5, 10), pady=5)

        # 创建软连接按钮
        self.create_symlink_button = ctk.CTkButton(
            tools_frame,
            text="创建软连接",
            command=self.create_symlinks,
            width=100,
            height=28,
            fg_color="#8A2BE2",
            hover_color="#6A1BBF"
        )
        self.create_symlink_button.pack(side="left", padx=(0, 10), pady=5)

        # 工具状态标签
        self.tools_status_label = ctk.CTkLabel(
            tools_frame,
            text="就绪",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        )
        self.tools_status_label.pack(side="left", padx=(10, 5), pady=5)

    def setup_exe_list_section(self):
        """设置EXE文件列表区域"""
        list_container = ctk.CTkFrame(self.disk_frame)
        list_container.pack(fill="both", expand=True, padx=5, pady=5)

        list_label = ctk.CTkLabel(
            list_container,
            text="找到的EXE文件:",
            font=ctk.CTkFont(size=12)
        )
        list_label.pack(anchor="w", padx=5, pady=(5, 0))

        # EXE文件滚动列表
        self.exe_list_frame = ctk.CTkScrollableFrame(
            list_container,
            height=120
        )
        self.exe_list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # 文件列表控制按钮
        list_control_frame = ctk.CTkFrame(list_container, height=30)
        list_control_frame.pack(fill="x", padx=5, pady=(0, 5))
        list_control_frame.grid_propagate(False)

        self.select_all_exe_btn = ctk.CTkButton(
            list_control_frame,
            text="全选",
            command=self.select_all_exes,
            width=60,
            height=20,
            font=ctk.CTkFont(size=10)
        )
        self.select_all_exe_btn.grid(row=0, column=0, padx=(10, 5), pady=5)

        self.deselect_all_exe_btn = ctk.CTkButton(
            list_control_frame,
            text="取消",
            command=self.deselect_all_exes,
            width=60,
            height=20,
            font=ctk.CTkFont(size=10)
        )
        self.deselect_all_exe_btn.grid(row=0, column=1, padx=5, pady=5)

        # 文件计数标签
        self.file_count_label = ctk.CTkLabel(
            list_control_frame,
            text="找到 0 个文件",
            text_color="gray"
        )
        self.file_count_label.grid(row=0, column=2, padx=(20, 10), pady=5, sticky="e")

    # ========== 汉化工具下载功能 ==========
    def download_chinese_tool(self):
        """下载汉化工具"""
        self.chinese_tool_button.configure(state="disabled", text="下载中...")
        self.tools_status_label.configure(text="开始下载汉化工具...", text_color="yellow")

        threading.Thread(target=self._download_chinese_tool_thread, daemon=True).start()

    def _download_chinese_tool_thread(self):
        """下载汉化工具的线程"""
        download_url = "https://download.zeroasso.top/files/LLC_MOD_Toolbox_Installer.exe"

        try:
            appdata_path = os.getenv("APPDATA")
            if not appdata_path:
                raise Exception("无法获取 APPDATA 环境变量")

            target_dir = os.path.join(os.path.dirname(appdata_path), "LocalLow")
            os.makedirs(target_dir, exist_ok=True)

            target_path = os.path.join(target_dir, "LLC_MOD_Toolbox_Installer.exe")

            self.after(0, lambda: self.tools_status_label.configure(
                text=f"下载到: {target_path}",
                text_color="yellow"
            ))

            urllib.request.urlretrieve(download_url, target_path)

            self.after(0, lambda: self._chinese_tool_download_complete(True, target_path))

        except Exception as e:
            error_msg = f"下载失败: {str(e)}"
            self.after(0, lambda: self._chinese_tool_download_complete(False, error_msg))

    def _chinese_tool_download_complete(self, success, info):
        """汉化工具下载完成"""
        self.chinese_tool_button.configure(state="normal", text="汉化工具")

        if success:
            self.tools_status_label.configure(
                text=f"汉化工具下载成功",
                text_color="green"
            )
            if messagebox.askyesno("下载完成", "汉化工具下载完成！是否要立即运行？"):
                try:
                    subprocess.Popen(info, shell=True)
                except Exception as e:
                    messagebox.showerror("运行错误", f"无法运行程序: {e}")
        else:
            self.tools_status_label.configure(
                text=f"汉化工具下载失败",
                text_color="red"
            )
            messagebox.showerror("下载错误", f"汉化工具下载失败: {info}")

    # ========== 创建软连接功能 ==========
    def create_symlinks(self):
        """创建软连接"""
        # 首先需要找到目标文件夹
        target_folder = self._find_target_folder()
        if not target_folder:
            messagebox.showwarning("未找到目标",
                                   f"未找到名为 '{self.folder_entry.get()}' 的文件夹。请先扫描确认文件夹存在。")
            return

        # 确认是否要创建软连接
        confirm_msg = f"将为以下路径创建软连接:\n\n"
        confirm_msg += f"目标文件夹: {target_folder}\n\n"
        confirm_msg += f"这将创建两个软连接到 {os.path.expanduser('~')}\\AppData\\LocalLow\\\n\n"
        confirm_msg += "是否继续？"

        if not messagebox.askyesno("确认创建软连接", confirm_msg):
            return

        # 在新线程中创建软连接
        self.create_symlink_button.configure(state="disabled", text="创建中...")
        self.tools_status_label.configure(text="正在创建软连接...", text_color="yellow")

        threading.Thread(target=self._create_symlinks_thread, args=(target_folder,), daemon=True).start()

    def _find_target_folder(self):
        """查找目标文件夹"""
        folder_name = self.folder_entry.get().strip() or self.default_folder_name
        selected_disks = [disk for disk, var in self.disk_vars.items() if var.get()]

        # 在选中的磁盘中搜索文件夹
        for disk in selected_disks:
            disk_path = f"{disk}:\\"

            # 检查常见位置
            search_paths = [
                os.path.join(disk_path, folder_name),
                os.path.join(disk_path, "Program Files", folder_name),
                os.path.join(disk_path, "Program Files (x86)", folder_name),
                os.path.join(disk_path, "Users", "Public", folder_name),
                os.path.join(disk_path, folder_name.split('_')[0], folder_name) if '_' in folder_name else "",
            ]

            for path in search_paths:
                if path and os.path.exists(path) and os.path.isdir(path):
                    return path

        return None

    def _create_symlinks_thread(self, target_folder):
        """创建软连接的线程"""
        try:
            # 获取当前用户名对应的LocalLow路径
            username = os.getlogin()
            local_low_base = f"C:\\Users\\{username}\\AppData\\LocalLow"

            # 要创建的软连接目标
            symlink_targets = [
                ("ProjectMoon", "ProjectMoon"),
                ("Unity", "Unity")
            ]

            results = []

            for source_name, target_name in symlink_targets:
                # 源路径：目标文件夹下的对应目录
                source_path = os.path.join(target_folder, source_name)

                # 如果源目录不存在，尝试创建
                if not os.path.exists(source_path):
                    try:
                        os.makedirs(source_path, exist_ok=True)
                        created = True
                    except:
                        created = False
                    if created:
                        results.append(f"创建目录: {source_path}")

                # 目标路径：LocalLow下的对应目录
                target_path = os.path.join(local_low_base, target_name)

                # 如果目标已存在，先尝试删除（询问用户？）
                if os.path.exists(target_path):
                    try:
                        if os.path.islink(target_path):
                            os.unlink(target_path)  # 删除现有的软连接
                        elif os.path.isdir(target_path):
                            # 如果是目录，不能简单删除，需要用户确认
                            self.after(0, lambda t=target_path: self._ask_replace_directory(t))
                            continue
                    except Exception as e:
                        results.append(f"无法删除现有目标 {target_name}: {str(e)}")
                        continue

                # 创建软连接
                try:
                    # 使用mklink命令创建目录软连接
                    cmd = f'mklink /D "{target_path}" "{source_path}"'

                    # 以管理员权限运行（可能需要）
                    CREATE_NO_WINDOW = 0x08000000
                    result = subprocess.run(
                        cmd,
                        shell=True,
                        capture_output=True,
                        text=True,
                        creationflags=CREATE_NO_WINDOW
                    )

                    if result.returncode == 0:
                        results.append(f"成功创建 {target_name} 软连接")
                    else:
                        # 如果mklink失败，尝试使用Python的symlink（可能需要管理员权限）
                        try:
                            if hasattr(os, 'symlink'):
                                os.symlink(source_path, target_path, target_is_directory=True)
                                results.append(f"成功创建 {target_name} 软连接 (Python)")
                            else:
                                results.append(f"创建 {target_name} 失败: {result.stderr}")
                        except Exception as e:
                            results.append(f"创建 {target_name} 失败: {str(e)}")

                except Exception as e:
                    results.append(f"创建 {target_name} 时出错: {str(e)}")

            # 更新状态
            self.after(0, lambda: self._symlinks_complete(results, target_folder))

        except Exception as e:
            error_msg = f"创建软连接失败: {str(e)}"
            self.after(0, lambda: self._symlinks_complete([error_msg], None))

    def _ask_replace_directory(self, target_path):
        """询问是否替换现有目录"""
        response = messagebox.askyesno(
            "目录已存在",
            f"目录 {target_path} 已存在。是否删除并替换为软连接？\n\n注意：删除目录将丢失其中的所有文件！"
        )

        if response:
            try:
                import shutil
                shutil.rmtree(target_path)
                self.tools_status_label.configure(
                    text=f"已删除现有目录: {os.path.basename(target_path)}",
                    text_color="orange"
                )
            except Exception as e:
                messagebox.showerror("删除失败", f"无法删除目录: {str(e)}")

    def _symlinks_complete(self, results, target_folder):
        """软连接创建完成"""
        self.create_symlink_button.configure(state="normal", text="创建软连接")

        if target_folder and any("成功" in result for result in results):
            success_results = [r for r in results if "成功" in r]

            summary = f"软连接创建完成！\n\n"
            summary += f"目标文件夹: {target_folder}\n\n"
            summary += "结果:\n"
            for result in results:
                summary += f"• {result}\n"

            self.tools_status_label.configure(text="软连接创建成功", text_color="green")

            # 显示详细结果
            messagebox.showinfo("软连接创建完成", summary)

            # 显示创建的软连接信息
            username = os.getlogin()
            info_msg = f"创建的软连接位于:\n"
            info_msg += f"C:\\Users\\{username}\\AppData\\LocalLow\\ProjectMoon\n"
            info_msg += f"  → 指向 → {target_folder}\\ProjectMoon\n\n"
            info_msg += f"C:\\Users\\{username}\\AppData\\LocalLow\\Unity\n"
            info_msg += f"  → 指向 → {target_folder}\\Unity"

            messagebox.showinfo("软连接信息", info_msg)
        else:
            self.tools_status_label.configure(text="软连接创建失败", text_color="red")

            error_summary = "软连接创建失败:\n\n"
            for result in results:
                error_summary += f"• {result}\n"

            messagebox.showerror("创建失败", error_summary)

    # ========== 原有核心功能方法 ==========
    def get_available_disks(self):
        """获取所有可用的磁盘"""
        disks = []
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            disk_path = f"{letter}:\\"
            if os.path.exists(disk_path):
                disks.append(letter)
        return disks[:8]  # 限制显示前8个磁盘以保持紧凑

    def select_all_disks(self):
        """选择所有磁盘"""
        for var in self.disk_vars.values():
            var.set(True)

    def deselect_all_disks(self):
        """取消选择所有磁盘"""
        for var in self.disk_vars.values():
            var.set(False)

    def scan_for_exe_files(self):
        """扫描exe文件"""
        self.scan_button.configure(state="disabled", text="扫描中...")
        self.execute_button.configure(state="disabled")

        # 清空列表
        for widget in self.exe_list_frame.winfo_children():
            widget.destroy()

        self.exe_files = []
        folder_name = self.folder_entry.get().strip() or self.default_folder_name

        # 获取选中的磁盘
        selected_disks = [disk for disk, var in self.disk_vars.items() if var.get()]

        if not selected_disks:
            self.status_label.configure(text="请选择至少一个磁盘", text_color="red")
            self.scan_button.configure(state="normal", text="扫描")
            self.execute_button.configure(state="normal")
            return

        self.status_label.configure(text="正在扫描...", text_color="yellow")
        self.file_count_label.configure(text="扫描中...")

        # 在新线程中扫描
        threading.Thread(
            target=self._scan_thread,
            args=(folder_name, selected_disks),
            daemon=True
        ).start()

    def _scan_thread(self, folder_name, selected_disks):
        """扫描线程"""
        found_files = []

        for disk in selected_disks:
            disk_path = f"{disk}:\\"

            # 快速扫描方法：检查常见位置
            search_paths = [
                os.path.join(disk_path, folder_name),
                os.path.join(disk_path, "Program Files", folder_name),
                os.path.join(disk_path, "Program Files (x86)", folder_name),
                os.path.join(disk_path, "Users", "Public", folder_name),
            ]

            for target_path in search_paths:
                if os.path.exists(target_path) and os.path.isdir(target_path):
                    self._search_exe_in_folder(target_path, found_files, disk)

        # 更新UI
        self.after(0, self._update_exe_list, found_files)

    def _search_exe_in_folder(self, folder_path, found_files, disk):
        """在文件夹中搜索exe文件"""
        try:
            for item in os.listdir(folder_path):
                if item.lower().endswith('.exe'):
                    item_path = os.path.join(folder_path, item)
                    found_files.append({
                        'path': item_path,
                        'name': item,
                        'disk': disk,
                        'var': tk.BooleanVar(value=True)
                    })
        except:
            pass

    def _update_exe_list(self, found_files):
        """更新EXE文件列表"""
        self.exe_files = found_files

        # 启用按钮
        self.scan_button.configure(state="normal", text="扫描")
        self.execute_button.configure(state="normal")

        # 清空列表
        for widget in self.exe_list_frame.winfo_children():
            widget.destroy()

        if not self.exe_files:
            no_files_label = ctk.CTkLabel(
                self.exe_list_frame,
                text="未找到EXE文件",
                text_color="gray"
            )
            no_files_label.pack(pady=10)
            self.status_label.configure(
                text=f"未找到'{self.folder_entry.get()}'中的EXE文件",
                text_color="orange"
            )
            self.file_count_label.configure(text="找到 0 个文件")
        else:
            # 显示文件列表（最多显示10个，超过显示更多提示）
            max_display = 10
            for i, exe_info in enumerate(self.exe_files[:max_display]):
                checkbox = ctk.CTkCheckBox(
                    self.exe_list_frame,
                    text=f"{exe_info['name']} ({exe_info['disk']}:)",
                    variable=exe_info['var'],
                    onvalue=True,
                    offvalue=False
                )
                checkbox.pack(anchor="w", padx=5, pady=1)

            # 如果文件太多，显示提示
            if len(self.exe_files) > max_display:
                more_label = ctk.CTkLabel(
                    self.exe_list_frame,
                    text=f"... 还有 {len(self.exe_files) - max_display} 个文件",
                    text_color="gray",
                    font=ctk.CTkFont(size=10)
                )
                more_label.pack(pady=2)

            self.status_label.configure(
                text=f"找到 {len(self.exe_files)} 个EXE文件",
                text_color="green"
            )
            self.file_count_label.configure(text=f"找到 {len(self.exe_files)} 个文件")

    def select_all_exes(self):
        """选择所有EXE文件"""
        for exe_info in self.exe_files:
            exe_info['var'].set(True)

    def deselect_all_exes(self):
        """取消选择所有EXE文件"""
        for exe_info in self.exe_files:
            exe_info['var'].set(False)

    def execute_selected_exes(self):
        """执行选中的EXE文件"""
        selected_exes = [exe for exe in self.exe_files if exe['var'].get()]

        if not selected_exes:
            messagebox.showwarning("警告", "请至少选择一个EXE文件")
            return

        if not messagebox.askyesno("确认", f"确定要运行 {len(selected_exes)} 个EXE文件吗？"):
            return

        # 禁用按钮
        self.execute_button.configure(state="disabled")
        self.scan_button.configure(state="disabled")
        self.status_label.configure(text="正在启动程序...", text_color="yellow")

        # 在新线程中执行
        threading.Thread(
            target=self._execute_thread,
            args=(selected_exes,),
            daemon=True
        ).start()

    def _execute_thread(self, selected_exes):
        """执行线程"""
        delay_enabled = self.delay_var.get()
        try:
            delay_seconds = max(0.5, float(self.delay_entry.get()))
        except:
            delay_seconds = 1.0

        run_as_admin = self.admin_var.get()

        success_count = 0

        for i, exe_info in enumerate(selected_exes):
            try:
                # 延迟启动
                if delay_enabled and i > 0:
                    import time
                    time.sleep(delay_seconds)

                exe_path = exe_info['path']

                if run_as_admin:
                    # 尝试管理员权限
                    try:
                        import ctypes
                        ctypes.windll.shell32.ShellExecuteW(
                            None, "runas", exe_path, None, None, 1
                        )
                        success_count += 1
                        status_msg = f"✓ {exe_info['name']}"
                    except:
                        status_msg = f"✗ {exe_info['name']} (权限失败)"
                else:
                    # 普通执行
                    subprocess.Popen(exe_path, shell=True)
                    success_count += 1
                    status_msg = f"✓ {exe_info['name']}"

                # 更新状态
                self.after(0, self._update_status_progress, i + 1, len(selected_exes), status_msg)

            except Exception as e:
                status_msg = f"✗ {exe_info['name']} (错误)"
                self.after(0, self._update_status_progress, i + 1, len(selected_exes), status_msg)

        # 完成
        self.after(0, self._execution_complete, success_count, len(selected_exes))

    def _update_status_progress(self, current, total, message):
        """更新进度状态"""
        progress = f"({current}/{total})"
        self.status_label.configure(
            text=f"{progress} {message}",
            text_color="yellow"
        )

    def _execution_complete(self, success, total):
        """执行完成"""
        self.execute_button.configure(state="normal")
        self.scan_button.configure(state="normal")

        if success == total:
            self.status_label.configure(
                text=f"完成！成功启动 {success}/{total} 个程序",
                text_color="green"
            )
        elif success > 0:
            self.status_label.configure(
                text=f"完成！成功 {success}/{total}，失败 {total - success}",
                text_color="orange"
            )
        else:
            self.status_label.configure(
                text=f"所有 {total} 个程序启动失败",
                text_color="red"
            )


def maineeg():
    app = CompactExeRunner()
    app.mainloop()


if __name__ == "__main__":
    maineeg()