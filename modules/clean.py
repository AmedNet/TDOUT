import os
import platform
import sys
from datetime import datetime
from tkinter import messagebox, filedialog

import customtkinter as ctk

# 设置CustomTkinter外观
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class EmptyDirCleanerCTK:
    def __init__(self, root):
        self.root = root
        self.root.title("DS.Store")
        self.root.geometry("0x550")
        self.root.minsize(650, 450)

        # 初始化变量
        self.target_path = ctk.StringVar()
        self.scan_depth = ctk.IntVar(value=1)
        self.include_hidden_dirs = ctk.BooleanVar(value=False)  # 扫描隐藏目录
        self.include_hidden_files = ctk.BooleanVar(value=False)  # 扫描隐藏文件
        self.empty_dirs = []
        self.hidden_files = []  # 存储找到的隐藏文件
        self.all_selected = False
        self.current_view = "dirs"  # 当前视图：dirs(目录) 或 files(文件)

        # 主框架（减少外层间距）
        self.main_frame = ctk.CTkFrame(root, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=8, pady=8)

        # 构建紧凑布局（优化区域排列而非缩小控件）
        self.create_compact_layout()

    def create_compact_layout(self):
        """创建真正紧凑的布局 - 优化区域排列而非缩小控件"""
        # # 标题（适中字号，底部少量间距）
        # title_label = ctk.CTkLabel(
        #     self.main_frame,
        #     text="Clean Null.",
        #     font=ctk.CTkFont(size=18, weight="bold")
        # )
        # title_label.pack(pady=(0, 8))

        # ========== 第一行：路径选择 + 功能按钮（横向合并，紧凑排列） ==========
        top_row_frame = ctk.CTkFrame(self.main_frame)
        top_row_frame.pack(fill="x", pady=(0, 6))

        # 路径选择部分（占主要宽度）
        path_label = ctk.CTkLabel(top_row_frame, text="目标路径：", width=70)
        path_label.pack(side="left", padx=(8, 4), pady=6)

        path_entry = ctk.CTkEntry(
            top_row_frame,
            textvariable=self.target_path,
            width=0
        )
        path_entry.pack(side="left", padx=(0, 4), pady=6, fill="x", expand=True)

        browse_btn = ctk.CTkButton(
            top_row_frame,
            text="浏览",
            command=self.browse_path,
            width=80,
            height=28
        )
        browse_btn.pack(side="left", padx=(0, 8), pady=6)

        # 功能按钮组（和路径在同一行，节省纵向空间）
        btn_group = ctk.CTkFrame(top_row_frame, fg_color="transparent")
        btn_group.pack(side="left", pady=6)

        scan_btn = ctk.CTkButton(
            btn_group, text="扫描", command=self.scan_items,
            width=10, height=28, fg_color="#2ecc71", hover_color="#27ae60"
        )
        scan_btn.pack(side="left", padx=3)

        # 视图切换按钮
        self.view_btn = ctk.CTkButton(
            btn_group, text="查看隐藏文件", command=self.toggle_view,
            width=90, height=28, fg_color="#3498db", hover_color="#2980b9"
        )
        self.view_btn.pack(side="left", padx=3)

        self.select_btn = ctk.CTkButton(
            btn_group, text="全选", command=self.toggle_select_all,
            width=70, height=28, state="disabled"
        )
        self.select_btn.pack(side="left", padx=3)

        self.delete_btn = ctk.CTkButton(
            btn_group, text="删除选中", command=self.delete_selected_items,
            width=80, height=28, fg_color="#e74c3c", hover_color="#c0392b", state="disabled"
        )
        self.delete_btn.pack(side="left", padx=3)

        refresh_btn = ctk.CTkButton(
            btn_group, text="刷新", command=self.refresh_list,
            width=70, height=28
        )
        refresh_btn.pack(side="left", padx=3)

        # ========== 第二行：扫描设置（深度+隐藏开关，横向紧凑排列） ==========
        setting_frame = ctk.CTkFrame(self.main_frame)
        setting_frame.pack(fill="x", pady=(0, 6))

        depth_label = ctk.CTkLabel(setting_frame, text="扫描深度：", width=70)
        depth_label.pack(side="left", padx=(8, 4), pady=6)

        depth_slider = ctk.CTkSlider(
            setting_frame, from_=1, to=10, variable=self.scan_depth,
            command=self.update_depth_label, width=200, height=16
        )
        depth_slider.pack(side="left", padx=(0, 4), pady=6)

        self.depth_value_label = ctk.CTkLabel(setting_frame, text=f"{self.scan_depth.get()} 级", width=50)
        self.depth_value_label.pack(side="left", padx=(0, 15), pady=6)

        # 隐藏目录开关
        hidden_dir_switch = ctk.CTkSwitch(
            setting_frame,
            text="目录（.开头）",
            variable=self.include_hidden_dirs,
            width=0
        )
        hidden_dir_switch.pack(side="left", pady=6, padx=(0, 10))

        # 隐藏文件开关
        hidden_file_switch = ctk.CTkSwitch(
            setting_frame,
            text="文件（.开头）",
            variable=self.include_hidden_files,
            width=180
        )
        hidden_file_switch.pack(side="left", pady=6)

        # ========== 第三部分：列表区域（占满剩余空间） ==========
        list_frame = ctk.CTkFrame(self.main_frame)
        list_frame.pack(fill="both", expand=True, pady=(0, 6))

        self.list_title = ctk.CTkLabel(list_frame, text="空目录列表", font=ctk.CTkFont(weight="bold"))
        self.list_title.pack(padx=8, pady=(6, 2), anchor="w")

        self.listbox_frame = ctk.CTkScrollableFrame(list_frame)
        self.listbox_frame.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        self.checkbox_vars = {}

        # ========== 第四部分：日志区域（固定高度，紧凑显示） ==========
        log_frame = ctk.CTkFrame(self.main_frame)
        log_frame.pack(fill="x", pady=(0, 0))

        log_title = ctk.CTkLabel(log_frame, text="操作日志", font=ctk.CTkFont(weight="bold"))
        log_title.pack(padx=8, pady=(6, 2), anchor="w")

        self.log_text = ctk.CTkTextbox(log_frame, height=70, font=ctk.CTkFont(family="Consolas", size=10))
        self.log_text.pack(fill="x", padx=8, pady=(0, 6))

        self.add_log("工具已启动，等待操作...")

    def update_depth_label(self, value):
        """更新深度显示"""
        self.depth_value_label.configure(text=f"{int(value)} 级")

    def browse_path(self):
        """浏览选择路径"""
        initial_dir = "C:/" if platform.system() == "Windows" else os.path.expanduser("~")
        path = filedialog.askdirectory(title="选择清理路径", initialdir=initial_dir)
        if path:
            self.target_path.set(path)
            self.add_log(f"已选择路径: {path}")

    def is_hidden_item(self, item_name):
        """判断是否为.开头的隐藏项"""
        return item_name.startswith('.') and len(item_name) > 1

    def scan_items(self):
        """扫描空目录和/或隐藏文件"""
        target_path = self.target_path.get().strip()
        if not target_path:
            messagebox.showwarning("警告", "请选择目标路径！")
            return
        if not os.path.exists(target_path):
            messagebox.showerror("错误", "路径不存在！")
            return

        scan_depth = self.scan_depth.get()
        include_hidden_dirs = self.include_hidden_dirs.get()
        include_hidden_files = self.include_hidden_files.get()

        # 清空列表
        self.clear_item_list()
        self.empty_dirs.clear()
        self.hidden_files.clear()
        self.checkbox_vars.clear()

        # 构建日志信息
        scan_info = f"扫描{scan_depth}级"
        if include_hidden_dirs and include_hidden_files:
            scan_info += "空目录和隐藏文件"
        elif include_hidden_dirs:
            scan_info += "空目录（包含隐藏目录）"
        elif include_hidden_files:
            scan_info += "隐藏文件"
        else:
            scan_info += "空目录（排除隐藏项）"

        self.add_log(f"{scan_info}：{target_path}")

        try:
            if self.current_view == "dirs" or include_hidden_dirs:
                # 扫描空目录
                self.scan_dir_recursive(target_path, target_path, 1, scan_depth, include_hidden_dirs)

            if self.current_view == "files" or include_hidden_files:
                # 扫描隐藏文件
                self.scan_hidden_files_recursive(target_path, target_path, 1, scan_depth)

            # 更新按钮状态
            total_items = len(self.empty_dirs) + len(self.hidden_files)
            if total_items > 0:
                self.delete_btn.configure(state="normal")
                self.select_btn.configure(state="normal", text="全选")
                self.all_selected = False
                self.add_log(f"扫描完成，发现{len(self.empty_dirs)}个空目录，{len(self.hidden_files)}个隐藏文件")
            else:
                self.delete_btn.configure(state="disabled")
                self.select_btn.configure(state="disabled")
                self.add_log(f"扫描完成，无空目录和隐藏文件")

        except Exception as e:
            messagebox.showerror("错误", f"扫描失败：{str(e)}")
            self.add_log(f"扫描失败：{str(e)}")

    def scan_dir_recursive(self, root_path, current_path, current_depth, max_depth, include_hidden):
        """递归扫描空目录"""
        if current_depth > max_depth:
            return

        try:
            for item in os.listdir(current_path):
                if not include_hidden and self.is_hidden_item(item):
                    continue

                item_path = os.path.join(current_path, item)
                if os.path.isdir(item_path):
                    try:
                        dir_items = os.listdir(item_path)
                        if not include_hidden:
                            dir_items = [i for i in dir_items if not self.is_hidden_item(i)]
                        is_empty = len(dir_items) == 0
                    except:
                        is_empty = False

                    if is_empty:
                        self.empty_dirs.append(item_path)
                        if self.current_view == "dirs":
                            self.add_item_checkbox(item_path, is_dir=True)
                    else:
                        if current_depth < max_depth:
                            self.scan_dir_recursive(root_path, item_path, current_depth + 1, max_depth, include_hidden)
        except PermissionError:
            self.add_log(f"权限不足，跳过：{current_path}")
        except Exception as e:
            self.add_log(f"扫描目录出错 {current_path}：{str(e)}")

    def scan_hidden_files_recursive(self, root_path, current_path, current_depth, max_depth):
        """递归扫描.开头的隐藏文件"""
        if current_depth > max_depth:
            return

        try:
            for item in os.listdir(current_path):
                item_path = os.path.join(current_path, item)

                # 跳过目录（只扫描文件）
                if os.path.isdir(item_path):
                    # 如果是目录，递归继续扫描
                    if current_depth < max_depth:
                        self.scan_hidden_files_recursive(root_path, item_path, current_depth + 1, max_depth)
                    continue

                # 检查是否是.开头的隐藏文件
                if self.is_hidden_item(item):
                    self.hidden_files.append(item_path)
                    if self.current_view == "files":
                        self.add_item_checkbox(item_path, is_dir=False)

        except PermissionError:
            self.add_log(f"权限不足，跳过：{current_path}")
        except Exception as e:
            self.add_log(f"扫描文件出错 {current_path}：{str(e)}")

    def add_item_checkbox(self, item_path, is_dir=True):
        """添加目录/文件复选框"""
        var = ctk.BooleanVar(value=False)
        # 区分目录和文件的显示样式
        if is_dir:
            text = f"[目录] {item_path}"
            fg_color = "#3498db"  # 蓝色
        else:
            text = f"[文件] {item_path}"
            fg_color = "#e67e22"  # 橙色

        checkbox = ctk.CTkCheckBox(
            self.listbox_frame,
            text=text,
            variable=var,
            font=ctk.CTkFont(size=10),
            fg_color=fg_color
        )
        checkbox.pack(anchor="w", padx=2, pady=1)
        self.checkbox_vars[item_path] = (var, is_dir)

    def clear_item_list(self):
        """清空列表"""
        for widget in self.listbox_frame.winfo_children():
            widget.destroy()

    def toggle_view(self):
        """切换目录/文件视图"""
        if self.current_view == "dirs":
            self.current_view = "files"
            self.list_title.configure(text="隐藏文件列表")
            self.view_btn.configure(text="查看空目录")
        else:
            self.current_view = "dirs"
            self.list_title.configure(text="空目录列表")
            self.view_btn.configure(text="查看隐藏文件")

        # 重新扫描以更新列表
        if self.target_path.get().strip():
            self.scan_items()

    def toggle_select_all(self):
        """全选/反选切换"""
        self.all_selected = not self.all_selected
        self.select_btn.configure(text="反选" if self.all_selected else "全选")
        for (var, _) in self.checkbox_vars.values():
            var.set(self.all_selected)

    def delete_selected_items(self):
        """删除选中的目录/文件"""
        selected_items = [(path, is_dir) for path, (var, is_dir) in self.checkbox_vars.items() if var.get()]
        if not selected_items:
            messagebox.showwarning("警告", "请选择要删除的项目！")
            return

        # 统计选中的项目类型
        dir_count = sum(1 for _, is_dir in selected_items if is_dir)
        file_count = len(selected_items) - dir_count

        confirm_text = f"确认删除以下项目？\n此操作不可恢复！\n📁 目录：{dir_count} 个\n📄 文件：{file_count} 个"

        if not messagebox.askyesno("删除确认", confirm_text):
            self.add_log("用户取消删除操作")
            return

        self.add_log(f"开始删除{len(selected_items)}个项目（{dir_count}个目录，{file_count}个文件）...")
        deleted, failed = 0, 0

        for item_path, is_dir in selected_items:
            try:
                if is_dir:
                    # 删除目录
                    # 再次检查目录是否为空
                    dir_items = os.listdir(item_path)
                    if not self.include_hidden_dirs.get():
                        dir_items = [i for i in dir_items if not self.is_hidden_item(i)]

                    if len(dir_items) == 0:
                        os.rmdir(item_path)
                        self.add_log(f"✅ 已删除目录：{item_path}")
                        deleted += 1
                    else:
                        self.add_log(f"❌ 删除失败：目录非空 {item_path}")
                        failed += 1
                else:
                    # 删除文件
                    os.remove(item_path)
                    self.add_log(f"✅ 已删除文件：{item_path}")
                    deleted += 1

            except PermissionError:
                self.add_log(f"❌ 删除失败（权限不足）：{item_path}")
                failed += 1
            except OSError as e:
                self.add_log(f"❌ 删除失败（系统错误）：{item_path} - {str(e)}")
                failed += 1
            except Exception as e:
                self.add_log(f"❌ 删除失败：{item_path} - {str(e)}")
                failed += 1

        self.refresh_list()
        self.add_log(f"删除完成：成功{deleted}个，失败{failed}个")
        messagebox.showinfo(
            "删除完成",
            f"✅ 成功删除：{deleted} 个\n❌ 删除失败：{failed} 个\n📁 目录：{dir_count} 个（选中）\n📄 文件：{file_count} 个（选中）"
        )

    def refresh_list(self):
        """刷新列表"""
        self.add_log("刷新列表...")
        self.scan_items()

    def add_log(self, message):
        """添加操作日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}\n"
        self.log_text.insert("end", log_msg)
        self.log_text.see("end")
        self.log_text.update_idletasks()


def resource_path(relative_path):
    """打包后资源路径处理"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def opencl():
    if platform.system() == "Windows":
        try:
            from ctypes import windll

            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
    app = ctk.CTk()
    EmptyDirCleanerCTK(app)
    app.mainloop()
if __name__ == "__main__":
    opencl()  # 这样只有直接运行 clean.py 时才会启动