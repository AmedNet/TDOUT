import ipaddress
import platform
import re
import socket
import subprocess
from tkinter import messagebox

import customtkinter as ctk


class IPRangeGenerator:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.window = ctk.CTk()
        self.window.title("IP名单生成器")
        self.window.geometry("500x500")  # 稍微增加高度以容纳新功能

        self.setup_ui()

    def setup_ui(self):
        # 辅助工具：快速创建框架并返回，减少重复代码
        def _f(master, **kw):
            f = ctk.CTkFrame(master, **kw)
            f.pack(fill="x", padx=10, pady=5)
            return f

        # 1. 主体结构
        main = ctk.CTkFrame(self.window)
        main.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(main, text="IP地址范围生成器", font=("Microsoft YaHei", 24, "bold")).pack(pady=10)

        # 2. 本机信息区 (紧凑排版)
        ip_f = _f(main)
        ctk.CTkLabel(ip_f, text="本机网络信息:", font=("Microsoft YaHei", 13, "bold")).pack(side="left", padx=10)
        self.refresh_btn = ctk.CTkButton(ip_f, text="刷新", command=self.refresh_network_info, width=60, height=24)
        self.refresh_btn.pack(side="right", padx=10)
        self.network_interfaces_text = ctk.CTkTextbox(main, height=70, font=("Consolas", 10))
        self.network_interfaces_text.pack(fill="x", padx=10, pady=(0, 5))

        # 3. 自动填充与输入区
        self.auto_fill_frame = _f(main, fg_color="transparent")
        ctk.CTkLabel(self.auto_fill_frame, text="快速填充:", font=("Microsoft YaHei", 11)).pack(side="left")

        in_f = _f(main)
        # 第一行：目标网段 + 生成按钮
        r1 = ctk.CTkFrame(in_f, fg_color="transparent")
        r1.pack(fill="x", pady=2)
        ctk.CTkLabel(r1, text="目标网段:", width=60).pack(side="left")
        self.network_entry = ctk.CTkEntry(r1, placeholder_text="192.168.1.0/24", height=28)
        self.network_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.generate_btn = ctk.CTkButton(r1, text="生成列表", command=self.generate_custom_range, width=80)
        self.generate_btn.pack(side="right")

        # 第二行：排除地址
        r2 = ctk.CTkFrame(in_f, fg_color="transparent")
        r2.pack(fill="x", pady=2)
        ctk.CTkLabel(r2, text="排除地址:", width=60).pack(side="left")
        self.exclude_entry = ctk.CTkEntry(r2, placeholder_text="排除项(如.5, .10-20)", height=28)
        self.exclude_entry.pack(side="left", fill="x", expand=True, padx=5)

        # 4. 选项区 (单行整合)
        opt_f = _f(main, fg_color="transparent")
        self.exclude_gateway_var = ctk.BooleanVar(value=True)
        self.include_network_broadcast_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(opt_f, text="排除网关", variable=self.exclude_gateway_var, font=("MS", 11)).pack(side="left")
        ctk.CTkCheckBox(opt_f, text="含网络/广播", variable=self.include_network_broadcast_var, font=("MS", 11)).pack(
            side="left", padx=10)
        ctk.CTkLabel(opt_f, text="分隔:").pack(side="left")
        self.sep_var = ctk.StringVar(value="换行")
        self.sep_menu = ctk.CTkOptionMenu(opt_f, values=["换行", "逗号", "空格", "分号", "Tab"], variable=self.sep_var,
                                          width=70)
        self.sep_menu.pack(side="left", padx=5)

        # 5. 结果区
        res_f = ctk.CTkFrame(main)
        res_f.pack(fill="both", expand=True, padx=10, pady=5)

        # 结果头部按钮横向排列
        hdr = ctk.CTkFrame(res_f, fg_color="transparent")
        hdr.pack(fill="x", padx=5, pady=5)
        self.ip_count_label = ctk.CTkLabel(hdr, text="", font=("MS", 11))
        self.ip_count_label.pack(side="left")

        # 按钮组：使用循环生成减少代码
        btns = [("清空", self.clear_result, "gray"), ("导出", self.export_to_file, "green"),
                ("仅IP", self.copy_only_ips, "orange"), ("复制全部", self.copy_to_clipboard, "#1f538d")]
        for txt, cmd, clr in btns:
            b = ctk.CTkButton(hdr, text=txt, command=cmd, width=60, height=24, fg_color=clr)
            b.pack(side="right", padx=2)
            if txt == "复制全部": self.copy_btn = b  # 绑定引用

        self.result_text = ctk.CTkTextbox(res_f, font=("Consolas", 11), wrap="none")
        self.result_text.pack(fill="both", expand=True, padx=5, pady=5)

        self.status_bar = ctk.CTkLabel(main, text="就绪", font=("MS", 10), text_color="gray")
        self.status_bar.pack(side="bottom")
        self.refresh_network_info()

    # --- [核心逻辑] 解析排除的IP ---
    def get_excluded_ips(self):
        exclude_str = self.exclude_entry.get().strip()
        if not exclude_str:
            return set()

        excluded = set()
        # 兼容中文逗号、英文逗号和空格
        parts = re.split(r'[，,\s]+', exclude_str)
        for part in parts:
            try:
                if '-' in part:
                    start_ip, end_part = part.split('-')
                    if end_part.isdigit():
                        base = '.'.join(start_ip.split('.')[:3])
                        end_ip = f"{base}.{end_part}"
                    else:
                        end_ip = end_part

                    start = ipaddress.ip_address(start_ip.strip())
                    end = ipaddress.ip_address(end_ip.strip())
                    for ip_int in range(int(start), int(end) + 1):
                        excluded.add(str(ipaddress.ip_address(ip_int)))
                else:
                    excluded.add(str(ipaddress.ip_address(part.strip())))
            except:
                continue
        return excluded

    # --- [核心逻辑] 获取分隔符 ---
    def get_sep_char(self):
        mapping = {"换行": "\n", "逗号": ", ", "空格": " ", "分号": "; ", "Tab": "\t"}
        return mapping.get(self.sep_var.get(), "\n")

    # --- [全量保留并修复] 原始生成逻辑 ---
    def generate_custom_range(self):
        input_str = self.network_entry.get().strip()
        if not input_str:
            messagebox.showwarning("输入错误", "请输入网段地址")
            return

        try:
            result = self.parse_input_range(input_str)
            all_ips = []

            # 解析网段
            if isinstance(result, list):
                for network in result:
                    if self.include_network_broadcast_var.get():
                        all_ips.extend([str(ip) for ip in network])
                    else:
                        all_ips.extend([str(ip) for ip in network.hosts()])
            else:
                if result.num_addresses > 65536:
                    if not messagebox.askyesno("确认", f"网段包含 {result.num_addresses} 个地址，是否继续？"):
                        return
                if self.include_network_broadcast_var.get():
                    all_ips = [str(ip) for ip in result]
                else:
                    all_ips = [str(ip) for ip in result.hosts()]

            # 执行排除逻辑
            exclude_set = self.get_excluded_ips()
            if self.exclude_gateway_var.get():
                gw = self.get_default_gateway()
                if gw: exclude_set.add(gw)

            final_ips = [ip for ip in all_ips if ip not in exclude_set]

            if not final_ips:
                messagebox.showinfo("提示", "没有找到有效的IP地址")
                return

            # 更新UI
            self.result_text.delete("1.0", "end")
            sep = self.get_sep_char()

            # 记录汇总信息
            summary = f"输入: {input_str}\n生成的IP数量: {len(final_ips)} 个\n"
            summary += "=" * 50 + "\nIP地址列表:\n\n"

            # 性能优化：如果IP太多，只预览前/后100个，但导出和复制是全量的
            if len(final_ips) <= 500:
                self.result_text.insert("1.0", summary + sep.join(final_ips))
            else:
                preview = sep.join(
                    final_ips[:100]) + f"\n\n... (中间省略 {len(final_ips) - 200} 个) ...\n\n" + sep.join(
                    final_ips[-100:])
                self.result_text.insert("1.0", summary + preview)

            # 存储完整数据用于后续复制
            self.full_ip_list = final_ips

            self.ip_count_label.configure(text=f"共 {len(final_ips)} 个IP", text_color="light green")
            self.copy_btn.configure(state="normal")
            self.status_bar.configure(text=f"生成成功: {len(final_ips)} 个", text_color="#2E8B57")

        except Exception as e:
            messagebox.showerror("错误", f"发生错误: {str(e)}")

    # --- 以下是完全搬运你原始 IP.py 的所有底层函数，确保功能一致性 ---

    def parse_input_range(self, input_str):
        input_str = input_str.strip()
        if '/' in input_str:
            return ipaddress.ip_network(input_str, strict=False)
        if '-' in input_str:
            parts = input_str.split('-')
            start_ip = parts[0].strip()
            end_part = parts[1].strip()
            if end_part.isdigit():
                base_ip = '.'.join(start_ip.split('.')[:3])
                end_ip = f"{base_ip}.{end_part}"
            else:
                end_ip = end_part
            start = ipaddress.ip_address(start_ip)
            end = ipaddress.ip_address(end_ip)
            if start > end: start, end = end, start
            return list(ipaddress.summarize_address_range(start, end))
        raise ValueError("格式错误")

    def get_default_gateway(self):
        system = platform.system()
        try:
            if system == "Windows":
                result = subprocess.run(['ipconfig'], capture_output=True, text=True, encoding='gbk')
                for line in result.stdout.split('\n'):
                    if '默认网关' in line or 'Default Gateway' in line:
                        ip_match = re.search(r'\d+\.\d+\.\d+\.\d+', line)
                        if ip_match: return ip_match.group(0)
            return None
        except:
            return None

    def refresh_network_info(self):
        self.status_bar.configure(text="正在刷新...", text_color="yellow")
        # 这里复用了你原始的获取系统信息逻辑
        try:
            hostname = socket.gethostname()
            all_ips = list(set([info[4][0] for info in socket.getaddrinfo(hostname, None) if ':' not in info[4][0]]))
            display_text = f"主机名: {hostname}\n" + "-" * 40 + "\n"
            for ip in all_ips:
                if not ip.startswith("127."):
                    display_text += f"🟢 IP: {ip}\n"
            self.network_interfaces_text.configure(state="normal")
            self.network_interfaces_text.delete("1.0", "end")
            self.network_interfaces_text.insert("1.0", display_text)
            self.network_interfaces_text.configure(state="disabled")
            self.status_bar.configure(text="网络信息已刷新", text_color="light green")
            # 自动生成快速填充按钮
            self.create_auto_fill_buttons(all_ips[0] if all_ips else None)
        except:
            self.status_bar.configure(text="刷新失败", text_color="red")

    def create_auto_fill_buttons(self, base_ip):
        for widget in self.auto_fill_frame.winfo_children():
            if "快速填充" not in str(widget): widget.destroy()
        if base_ip:
            prefix = '.'.join(base_ip.split('.')[:3])
            btn = ctk.CTkButton(self.auto_fill_frame, text=f"{prefix}.0/24",
                                command=lambda: self.auto_fill_entry(f"{prefix}.0/24"), height=28, width=100)
            btn.pack(side="left", padx=5)

    def auto_fill_entry(self, value):
        self.network_entry.delete(0, "end")
        self.network_entry.insert(0, value)

    def copy_to_clipboard(self):
        text = self.result_text.get("1.0", "end-1c")
        self.window.clipboard_clear()
        self.window.clipboard_append(text)
        self.status_bar.configure(text="已复制完整结果", text_color="#4169E1")

    def copy_only_ips(self):
        if hasattr(self, 'full_ip_list'):
            sep = self.get_sep_char()
            self.window.clipboard_clear()
            self.window.clipboard_append(sep.join(self.full_ip_list))
            self.status_bar.configure(text="仅复制IP地址成功", text_color="#4169E1")

    def export_to_file(self):
        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(defaultextension=".txt")
        if file_path and hasattr(self, 'full_ip_list'):
            sep = self.get_sep_char()
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(sep.join(self.full_ip_list))
            messagebox.showinfo("成功", "导出成功")

    def clear_result(self):
        self.result_text.delete("1.0", "end")
        self.ip_count_label.configure(text="")
        self.copy_btn.configure(state="disabled")

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    app = IPRangeGenerator()
    app.run()