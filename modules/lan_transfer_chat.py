# lan_transfer_chat.py
import json
import os
import socket
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
from winotify import Notification

# --- 配置 ---
DEFAULT_PORT = 14514
RECV_SAVE_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "LanReceived")  # 保存目录
CHAT_LOG_PATH = os.path.join(os.path.expanduser("~"), "LanChat_history.txt")


# --- App ---
class LanChatWindow(ctk.CTkToplevel):  # ✅ 改成 CTkToplevel
    def __init__(self, master=None):
        super().__init__(master)
        ctk.set_appearance_mode("dark")          # 全局深色主题
        ctk.set_default_color_theme("dark-blue") # 蓝色系按钮风格
        self.title("Lan_Chat")
        self.geometry("820x580")
        self.resizable(True, True)
        self._file_accept_flag = None

        # 用户昵称
        self.user_nickname = ""  # 默认昵称

        # 网络
        self.local_ip = self.get_local_ip()
        self.local_port = DEFAULT_PORT
        self.server_socket = None
        self.server_running = False

        # 连接上下文字典：key=conn socket, value={'leftover': b'', 'addr': (ip,port)}
        self.client_contexts = {}

        # 发送文件状态
        self.sending = False

        # UI
        self.setup_ui()

        # 启动服务器线程
        self.start_server_thread()
        self.load_chat_history()
        self.display_system_message(f"本机IP: {self.local_ip}, 监听端口: {self.local_port}")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------- UI ----------
    def setup_ui(self):
        # --- 整体布局配置 ---
        # 聊天区占权重 1，配置区固定宽度
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- 左侧：聊天记录区域 (保持原逻辑) ---
        left_container = ctk.CTkFrame(self, fg_color="transparent")
        left_container.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)

        # 标题紧凑化
        header = ctk.CTkLabel(left_container, text="信息日志", font=ctk.CTkFont(size=13, weight="bold"), anchor="w")
        header.pack(fill="x", pady=(0, 5))

        # 聊天文本框 (完全保留你的配置)
        self.chat_text = tk.Text(
            left_container,
            wrap="word",
            state="disabled",
            height=1,  # 依靠 pack fill expand 撑开
            bg="#101010",
            fg="#E0E0E0",
            insertbackground="white",
            relief="flat",
            bd=8,
            font=("Consolas", 12)  # 稍微调小一点，显得更精致
        )
        self.chat_text.pack(fill="both", expand=True)

        # 保留你的所有 Tag 配置
        self.chat_text.tag_configure("me", foreground="#4da6ff", font=("Consolas", 12, "bold"))
        self.chat_text.tag_configure("peer", foreground="#00ff88", font=("Consolas", 12))
        self.chat_text.tag_configure("sys", foreground="#aaaaaa", font=("Consolas", 11, "italic"))
        self.chat_text.tag_configure("sent_ok", foreground="#ffffff", font=("Consolas", 12, "bold"))

        # 输入区 (紧凑单行)
        bottom_frame = ctk.CTkFrame(left_container, fg_color="transparent")
        bottom_frame.pack(fill="x", pady=(8, 0))

        self.message_input = ctk.CTkEntry(bottom_frame, placeholder_text="输入消息...", height=35, corner_radius=4)
        self.message_input.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.message_input.bind("<Return>", lambda e: self.send_data())

        send_btn = ctk.CTkButton(bottom_frame, text="发送", width=80, height=35, corner_radius=4,
                                 command=self.send_data)
        send_btn.pack(side="left")

        # --- 右侧：配置与操作区域 (压缩宽度与间距) ---
        right = ctk.CTkScrollableFrame(self, width=260, label_text="控制面板", corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)

        # 1. 目标设置区
        ctk.CTkLabel(right, text="网络设置", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="nw")

        # 目标 IP
        ip_frame = ctk.CTkFrame(right, fg_color="transparent")
        ip_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(ip_frame, text="IP:", width=40, anchor="w").pack(side="left")
        self.target_ip_entry = ctk.CTkEntry(ip_frame, height=28)
        self.target_ip_entry.pack(side="left", fill="x", expand=True)
        self.target_ip_entry.insert(0, "192.168.")

        # 目标端口
        port_frame = ctk.CTkFrame(right, fg_color="transparent")
        port_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(port_frame, text="Port:", width=40, anchor="w").pack(side="left")
        self.target_port_entry = ctk.CTkEntry(port_frame, height=28)
        self.target_port_entry.pack(side="left", fill="x", expand=True)
        self.target_port_entry.insert(0, str(DEFAULT_PORT))

        # 本机端口控制
        myport_frame = ctk.CTkFrame(right, fg_color="transparent")
        myport_frame.pack(fill="x", pady=(10, 2))
        ctk.CTkLabel(myport_frame, text="监听:", width=40, anchor="w").pack(side="left")
        self.local_port_entry = ctk.CTkEntry(myport_frame, height=28)
        self.local_port_entry.pack(side="left", fill="x", expand=True)
        self.local_port_entry.insert(0, str(DEFAULT_PORT))

        apply_port_btn = ctk.CTkButton(right, text="应用端口", height=24, command=self.apply_local_port)
        apply_port_btn.pack(fill="x", pady=4)

        # 2. 昵称设置区
        nickname_frame = ctk.CTkFrame(right, fg_color="#2B2B2B", corner_radius=4)
        nickname_frame.pack(fill="x", pady=10, padx=2)

        row_nick = ctk.CTkFrame(nickname_frame, fg_color="transparent")
        row_nick.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(row_nick, text="昵称:").pack(side="left", padx=5)
        self.nickname_entry = ctk.CTkEntry(row_nick, height=24)
        self.nickname_entry.pack(side="left", fill="x", expand=True)
        self.nickname_entry.insert(0, self.user_nickname)

        set_nickname_btn = ctk.CTkButton(nickname_frame, text="更新昵称", height=24, command=self.set_nickname)
        set_nickname_btn.pack(fill="x", padx=5, pady=(0, 5))

        # 3. 文件传输区
        ctk.CTkLabel(right, text="文件传输", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="nw", pady=(10, 2))

        file_info_frame = ctk.CTkFrame(right, fg_color="#2B2B2B", corner_radius=4)
        file_info_frame.pack(fill="x", pady=2)
        self.selected_file_lbl = ctk.CTkLabel(file_info_frame, text="未选择文件", font=ctk.CTkFont(size=11),
                                              wraplength=220)
        self.selected_file_lbl.pack(pady=4)

        btn_row = ctk.CTkFrame(right, fg_color="transparent")
        btn_row.pack(fill="x", pady=4)
        choose_btn = ctk.CTkButton(btn_row, text="选择", width=115, height=28, command=self.select_file)
        choose_btn.pack(side="left")
        send_file_btn = ctk.CTkButton(btn_row, text="发送", width=115, height=28, command=self.send_selected_file)
        send_file_btn.pack(side="right")

        self.progress = ctk.CTkProgressBar(right, height=6)
        self.progress.set(0.0)
        self.progress.pack(fill="x", pady=8)

        # 4. 保存目录与清除
        self.save_dir_lbl = ctk.CTkLabel(right, text=f"保存至: {RECV_SAVE_DIR}", font=ctk.CTkFont(size=10),
                                         text_color="#888888", wraplength=240)
        self.save_dir_lbl.pack(pady=2)

        choose_save_btn = ctk.CTkButton(right, text="修改目录", height=22, fg_color="transparent", border_width=1,
                                        command=self.change_save_dir)
        choose_save_btn.pack(fill="x", pady=2)

        clear_log_btn = ctk.CTkButton(right, text="清除记录", height=22, fg_color="#442222", hover_color="#662222",
                                      command=self.clear_chat_log)
        clear_log_btn.pack(fill="x", pady=(20, 5))

        # 5. 底部状态
        self.server_status_lbl = ctk.CTkLabel(right, text="服务器：未启动", text_color="#aaaaaa")
        self.server_status_lbl.pack(pady=2)
        stop_btn = ctk.CTkButton(right, text="重启服务器", height=30, command=self.restart_server)
        stop_btn.pack(fill="x")

    # ---------- 显示并写日志 ----------
    def _append_chat(self, text: str, tag: str = "sys", write_log: bool = True, newline: bool = True):
        """内部：向 Text 添加一行或一段，并追加到磁盘日志"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        # 完整的文本内容
        display_text = f"[{timestamp}] {text}"
        # 仅在需要时加上换行符
        full_text = display_text + ("\n" if newline else "")

        def _do():
            self.chat_text.configure(state="normal")
            self.chat_text.insert("end", full_text, tag)
            self.chat_text.see("end")
            self.chat_text.configure(state="disabled")

        self.after(0, _do)

        # 追加到文件（仅在需要记录时）
        if write_log:
            try:
                # 写入日志文件时，总是需要换行，确保日志文件格式正确
                log_entry = display_text + "\n"
                with open(CHAT_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(log_entry)
            except Exception:
                pass

    def display_system_message(self, msg: str):
        self._append_chat(msg, tag="sys")

    def display_peer_message(self, peer_nick: str, msg: str, peer_ip: str):
        self._append_chat(f"{peer_nick} ({peer_ip}): {msg}", tag="peer")

    def display_my_message(self, msg: str):
        self._append_chat(f"{self.user_nickname} (⭐): {msg}", tag="me", newline=False)


    def update_send_status(self, is_success: bool = True, target_ip: str = ""):
        """
        在最近一条"我"发送的消息末尾添加发送状态标记，并在之后添加换行。
        """
        if not self.check_alive():
            return

        # 标记内容
        status_text = " [√]" if is_success else f" [×] (to {target_ip})"  # 失败时可以更详细
        tag = "sent_ok" if is_success else "sys"

        # 确保失败时，也加上换行符
        full_status_text = status_text + "\n"

        def _do_update():
            self.chat_text.configure(state="normal")

            # 直接在末尾插入状态标记和换行符
            # 因为 display_my_message 已经阻止了换行，所以现在 'end' 就在消息文本后
            self.chat_text.insert("end", full_status_text, tag)

            # 滚动到底部
            self.chat_text.see("end")
            self.chat_text.configure(state="disabled")

        self.after(0, _do_update)

    # ---------- 昵称设置 ----------
    def set_nickname(self):
        new_nick = self.nickname_entry.get().strip()
        if new_nick:
            self.user_nickname = new_nick
            self.display_system_message(f"✅ 昵称已设置为: {self.user_nickname}")
        else:
            self.display_system_message("❌ 昵称不能为空！")

    # ---------- 本机IP ----------
    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    # ---------- GUI 存在性检查 (新增) ----------
    def check_alive(self):
        """检查 Tkinter 窗口是否仍然存在"""
        try:
            # 尝试执行一个简单的 Tcl 命令来检查 widget 是否活着
            self.winfo_exists()
            return True
        except Exception:
            return False

    # ---------- 服务器 ----------
    def start_server_thread(self):
        t = threading.Thread(target=self.start_server, daemon=True)
        t.start()

    def start_server(self):
        """启动局域网服务器监听"""
        try:
            # 若服务器已在运行，先关闭旧 socket
            self.server_running = False
            try:
                if self.server_socket:
                    try:
                        self.server_socket.close()
                    except:
                        pass
            except:
                pass

            # 创建新的 socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(("", self.local_port))
            self.server_socket.listen(5)
            self.server_running = True

            self.after(0, lambda: self.server_status_lbl.configure(text=f"服务器：运行中 ({self.local_port})"))
            self.display_system_message("✅ 服务器启动，等待连接...")

            # 保存每个连接的上下文（防止动态属性报错）
            self.client_contexts = {}

            while self.server_running:
                try:
                    conn, addr = self.server_socket.accept()
                except OSError:
                    break
                except Exception as e:
                    self.display_system_message(f"服务器 accept 错误: {e}")
                    break

                # 初始化该连接的上下文（缓冲区）
                self.client_contexts[conn] = {"leftover": b"", "addr": addr}

                # 启动线程处理客户端连接
                threading.Thread(
                    target=self.handle_client_connection,
                    args=(conn,),
                    daemon=True
                ).start()

        except Exception as e:
            self.display_system_message(f"❌ 服务器错误: {e}")
        finally:
            self.server_running = False
            try:
                self.after(0, lambda: self.server_status_lbl.configure(text="服务器：已停止"))
            except:
                pass

    def stop_server(self):
        self.server_running = False
        try:
            if self.server_socket:
                self.server_socket.close()
        except:
            pass

    def restart_server(self):
        # 更新端口为输入框的值
        try:
            port = int(self.local_port_entry.get())
            self.local_port = port
        except:
            self.display_system_message("端口格式错误，使用当前端口。")
        # 重启服务器线程
        self.stop_server()
        time.sleep(0.15)
        self.start_server_thread()
        self.display_system_message(f"服务器在端口 {self.local_port} 重启中...")

    def apply_local_port(self):
        """应用监听端口并重启服务器"""
        try:
            port = int(self.local_port_entry.get())
            self.local_port = port
            self.restart_server()
            self.display_system_message(f"监听端口已修改为 {self.local_port} 并重启服务器。")
        except Exception:
            self.display_system_message("❌ 端口格式无效，请输入整数。")

    # ---------- 处理连接并解析 header 协议 ----------
    def handle_client_connection(self, conn):
        """处理单个客户端连接（支持 header JSON + \\n\\n + payload 格式）"""
        ctx = self.client_contexts.get(conn, {"leftover": b"", "addr": ("?", 0)})
        addr = ctx["addr"]
        buffer = ctx.get("leftover", b"")

        try:
            while True:
                try:
                    data = conn.recv(65536)
                except Exception:
                    break
                if not data:
                    break
                buffer += data

                # 可能包含多条消息，循环解析
                while True:
                    idx = buffer.find(b"\n\n")
                    if idx == -1:
                        break  # header 不完整，等待更多数据

                    header_bytes = buffer[:idx]
                    try:
                        header = json.loads(header_bytes.decode("utf-8"))
                    except Exception:
                        # 无法解析 header：当作普通文本消息
                        text = buffer.decode("utf-8", errors="ignore")
                        self.after(0, lambda t=text, a=addr: self.display_peer_message(a[0], t))
                        buffer = b""
                        break

                    # 去掉 header + 分隔符
                    buffer = buffer[idx + 2:]
                    typ = header.get("type")
                    length = int(header.get("length", 0))

                    # ⚠️ 特殊控制类型无需等待 payload
                    control_types = {"file_request", "file_accept", "file_reject"}
                    if typ not in control_types and len(buffer) < length:
                        ctx["leftover"] = header_bytes + b"\n\n" + buffer
                        self.client_contexts[conn] = ctx
                        buffer = ctx["leftover"]
                        break

                    # payload 已完整在 buffer 里
                    payload = buffer[:length]
                    buffer = buffer[length:]

                    # ---------- 消息类型分支 ----------
                    if typ == "chat":
                        try:
                            text = payload.decode("utf-8", errors="replace")

                            # 支持 "昵称|:|消息" 协议
                            if "|:|" in text:
                                peer_nick, msg_content = text.split("|:|", 1)
                            else:
                                peer_nick, msg_content = addr[0], text

                            # 更新聊天窗口
                            self.after(0, lambda n=peer_nick, t=msg_content, a=addr:
                            self.display_peer_message(n, t, a[0]))

                            # ✅ 替换后的系统通知代码：
                            threading.Thread(
                                target=lambda n=peer_nick, m=msg_content:
                                Notification(
                                    app_id="WPS",  # Windows 10/11 必需的唯一 ID
                                    title=f"WPS更新失败！",
                                    duration="short",
                                    # icon="path/to/your/icon.png" # 可选：添加图标路径
                                ).show(),
                                daemon=True
                            ).start()

                        except Exception as e:
                            self.after(0, lambda: self.display_system_message(f"[{addr[0]}] 聊天消息解析出错: {e}"))

                    elif typ == "file_request":
                        filename = header.get("filename", "unknown")
                        length = header.get("length", 0)

                        # 弹出确认框（主线程中执行）
                        def ask_permission():
                            res = messagebox.askyesno(
                                "文件接收请求",
                                f"来自 {addr[0]} 的文件请求：\n\n文件名: {filename}\n大小: {length} 字节\n\n是否接受？"
                            )
                            if res:
                                ack = {"type": "file_accept"}
                                self._send_header_only(addr[0], self.local_port, ack)
                                self.display_system_message(f"✅ 已同意接收来自 {addr[0]} 的文件：{filename}")
                            else:
                                nack = {"type": "file_reject"}
                                self._send_header_only(addr[0], self.local_port, nack)
                                self.display_system_message(f"❌ 已拒绝来自 {addr[0]} 的文件：{filename}")

                        self.after(0, ask_permission)

                    elif typ == "file_accept":
                        # 对方同意发送
                        self._file_accept_flag = "accept"

                    elif typ == "file_reject":
                        # 对方拒绝发送
                        self._file_accept_flag = "reject"

                    elif typ == "file":
                        filename = header.get("filename", "unknown")
                        safe_name = os.path.basename(filename)
                        os.makedirs(RECV_SAVE_DIR, exist_ok=True)
                        target_path = os.path.join(RECV_SAVE_DIR, safe_name)
                        try:
                            with open(target_path, "wb") as f:
                                f.write(payload)
                            self.after(0, lambda p=target_path, fn=safe_name, a=addr:
                            self.display_system_message(
                                f"💾 [来自 {a[0]}] 接收文件成功: {fn}\n保存路径: {p}"
                            ))
                        except Exception as e:
                            self.after(0, lambda: self.display_system_message(
                                f"[{addr[0]}] 保存文件出错: {e}"
                            ))

                    else:
                        self.after(0, lambda: self.display_system_message(
                            f"[{addr[0]}] 未知消息类型: {typ}"
                        ))

                # end inner while

            # 保存残余
            ctx["leftover"] = buffer
            self.client_contexts[conn] = ctx

        except Exception as e:
            self.after(0, lambda: self.display_system_message(f"[{addr[0]}] 处理错误: {e}"))

        finally:
            try:
                conn.close()
            except:
                pass
            if conn in self.client_contexts:
                del self.client_contexts[conn]

    # ---------- 发送聊天消息 ----------
    def send_data(self):
        target_ips_str = self.target_ip_entry.get().strip()

        try:
            target_port = int(self.target_port_entry.get().strip())
        except:
            self.display_system_message("端口格式错误")
            return

        message = self.message_input.get().strip()

        if not target_ips_str or not message:
            self.display_system_message("请输入目标 IP 与消息")
            return

        # 1. 解析多个目标 IP
        target_ips = [ip.strip() for ip in target_ips_str.split(',') if ip.strip()]

        if not target_ips:
            self.display_system_message("请输入有效的目标 IP 地址")
            return

        # 先显示"我"的消息到聊天框（只显示一次）
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        display_text = f"[{timestamp}] {self.user_nickname} (⭐): {message} "

        # 直接插入到聊天框，但不换行（等待状态标记）
        def _do_display():
            self.chat_text.configure(state="normal")
            self.chat_text.insert("end", display_text, "me")
            self.chat_text.see("end")
            self.chat_text.configure(state="disabled")

        self.after(0, _do_display)

        # 写入日志（完整消息，包含换行）
        try:
            log_entry = display_text + "\n"
            with open(CHAT_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception:
            pass

        # 2. 对每个目标 IP 启动一个发送线程
        for ip in target_ips:
            threading.Thread(target=self._perform_send_chat, args=(ip, target_port, message, display_text),
                             daemon=True).start()

        self.message_input.delete(0, "end")

    def _perform_send_chat(self, ip, port, text, display_text):
        """发送聊天消息到单个目标"""
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(8)
            client.connect((ip, port))
            full_message = f"{self.user_nickname}|:|{text}"
            data_bytes = full_message.encode('utf-8')
            header = {"type": "chat", "length": len(data_bytes)}
            header_bytes = (json.dumps(header) + "\n\n").encode('utf-8')
            client.sendall(header_bytes)
            client.sendall(data_bytes)

            # 成功发送，在对应位置添加状态标记
            if self.check_alive():
                self.after(0, lambda ip=ip: self._add_send_status_marker(ip, is_success=True))
        except Exception as e:
            if self.check_alive():
                # 失败时也需要显示状态标记
                self.after(0, lambda ip=ip, e=e: self._add_send_status_marker(ip, is_success=False, error=e))
        finally:
            try:
                client.close()
            except:
                pass

    def _add_send_status_marker(self, ip, is_success=True, error=None):
        """在消息末尾添加发送状态标记"""
        if not self.check_alive():
            return

        def _do_update():
            try:
                self.chat_text.configure(state="normal")

                # 获取当前光标位置
                current_pos = self.chat_text.index("end-1c")

                # 查找最近一个"⭐"的位置（我们消息的标识）
                # 从当前位置向前搜索
                start_idx = self.chat_text.search("⭐", current_pos, backwards=True, nocase=True)

                if start_idx:
                    # 找到消息开始位置，现在找到该行结束位置
                    line_end = self.chat_text.index(f"{start_idx} lineend")

                    # 检查这行是否已经有状态标记
                    line_text = self.chat_text.get(start_idx, line_end)

                    # 如果已经有状态标记（包含[√]或[×]），则不添加
                    if "[√]" in line_text or "[×]" in line_text:
                        self.chat_text.configure(state="disabled")
                        return

                    # 添加状态标记
                    status_text = f"[√]" if is_success else f"[×]"

                    # 如果失败且有错误信息，可以显示更详细
                    if not is_success and error:
                        status_text = f"[×] ({str(error)[:50]})"

                    # 在行尾添加状态标记
                    self.chat_text.insert(line_end, status_text, "sent_ok" if is_success else "sys")

                    # 在状态标记后添加换行符
                    self.chat_text.insert("end", "\n")

                self.chat_text.see("end")
                self.chat_text.configure(state="disabled")
            except Exception as e:
                # 如果发生错误，至少确保换行
                self.chat_text.insert("end", "\n")
                self.chat_text.configure(state="disabled")

        self.after(0, _do_update)

    # ---------- 文件发送 ----------
    def select_file(self):
        path = filedialog.askopenfilename()
        if path:
            self.selected_file = path
            self.selected_file_lbl.configure(text=path)
        else:
            self.selected_file = None
            self.selected_file_lbl.configure(text="未选择文件")

    def send_selected_file(self):
        if getattr(self, "sending", False):
            self.display_system_message("当前有文件传输进行中，请稍后")
            return
        if not getattr(self, "selected_file", None):
            self.display_system_message("请先选择文件")
            return
        target_ips_str = self.target_ip_entry.get().strip()
        try:
            target_port = int(self.target_port_entry.get().strip())
        except:
            self.display_system_message("端口格式错误")
            return
        target_ips = [ip.strip() for ip in target_ips_str.split(',') if ip.strip()]
        if not target_ips:
            self.display_system_message("请输入有效的目标 IP 地址")
            return
        for ip in target_ips:
            threading.Thread(target=self._perform_file_send, args=(ip, target_port, self.selected_file),
                             daemon=True).start()

    def _perform_file_send(self, ip, port, filepath):
        self.sending = True
        client = None
        try:
            filesize = os.path.getsize(filepath)
            filename = os.path.basename(filepath)

            # 1. 发送请求
            req_header = {"type": "file_request", "filename": filename, "length": filesize}
            self._send_header_only(ip, port, req_header)

            # 2. 等待确认 (保持原逻辑)
            start_wait = time.time()
            while getattr(self, "_file_accept_flag", None) is None:
                if (time.time() - start_wait) > 15:
                    self.display_system_message("❌ 对方未响应，取消发送。")
                    return
                time.sleep(0.1)

            if self._file_accept_flag == "reject":
                self._file_accept_flag = None
                self.display_system_message("❌ 对方拒绝接收。")
                return
            self._file_accept_flag = None

            # 3. 流式发送
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(20)
            client.connect((ip, port))

            header = {"type": "file", "filename": filename, "length": filesize}
            client.sendall((json.dumps(header) + "\n\n").encode('utf-8'))

            sent = 0
            last_update_time = 0  # 用于 UI 节流

            with open(filepath, "rb") as f:
                while True:
                    chunk = f.read(128 * 1024)  # 增加到 128KB 提高吞吐量
                    if not chunk:
                        break
                    client.sendall(chunk)
                    sent += len(chunk)

                    # --- UI 节流：每 0.1 秒或完成时更新一次进度条 ---
                    curr_time = time.time()
                    if curr_time - last_update_time > 0.1 or sent == filesize:
                        frac = sent / filesize if filesize > 0 else 1.0
                        if self.check_alive():
                            self.after(0, lambda v=frac: self.progress.set(v))
                        last_update_time = curr_time

            if self.check_alive():
                self.after(0, lambda: self.display_system_message(f"✅ 文件发送成功: {filename}"))

        except Exception as e:
            if self.check_alive():
                self.after(0, lambda: self.display_system_message(f"❌ 发送失败: {e}"))
        finally:
            if client: client.close()
            self.sending = False
            if self.check_alive():
                self.after(500, lambda: self.progress.set(0.0))

    def _send_header_only(self, ip, port, header_dict):
        """发送仅包含 header 的控制消息"""
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((ip, port))
            header_bytes = (json.dumps(header_dict) + "\n\n").encode("utf-8")
            client.sendall(header_bytes)
        except Exception as e:
            self.display_system_message(f"发送控制消息失败: {e}")
        finally:
            try:
                client.close()
            except:
                pass

    # ---------- 保存目录 ----------
    def change_save_dir(self):
        d = filedialog.askdirectory(initialdir=os.path.expanduser("~"))
        if d:
            global RECV_SAVE_DIR
            RECV_SAVE_DIR = d
            self.save_dir_lbl.configure(text=f"保存目录:\n{RECV_SAVE_DIR}")

    # ---------- 聊天记录清理 ----------
    def clear_chat_log(self):
        # 清空界面文本
        def _do_clear():
            self.chat_text.configure(state="normal")
            self.chat_text.delete("1.0", "end")
            self.chat_text.configure(state="disabled")
        self.after(0, _do_clear)
        # 删除磁盘日志
        try:
            if os.path.exists(CHAT_LOG_PATH):
                os.remove(CHAT_LOG_PATH)
            self.display_system_message("聊天记录已清除")
        except Exception as e:
            self.display_system_message(f"清除聊天记录失败: {e}")

    def on_close(self):
        """关闭窗口时仅隐藏，不停止服务器"""
        try:
            self.withdraw()  # 隐藏窗口
            self.display_system_message("窗口已隐藏，后台仍在运行接收消息。")
        except Exception as e:
            print(f"on_close 错误: {e}")

    def reopen(self):
        """重新显示聊天窗口，并恢复聊天记录"""
        self.deiconify()  # 显示窗口
        self.load_chat_history()
        self.display_system_message("窗口已恢复。")

    def load_chat_history(self):
        """从日志文件读取聊天记录"""
        if not os.path.exists(CHAT_LOG_PATH):
            return
        try:
            with open(CHAT_LOG_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
            self.chat_text.configure(state="normal")
            self.chat_text.delete("1.0", "end")
            for line in lines[-500:]:  # 限制最多加载 500 条，避免太多
                if "⭐" in line:
                    tag = "me"
                elif "] 接收" in line or "): " in line:
                    tag = "peer"
                else:
                    tag = "sys"
                self.chat_text.insert("end", line, tag)
            self.chat_text.configure(state="disabled")
            self.chat_text.see("end")
        except Exception as e:
            self.display_system_message(f"加载聊天记录失败: {e}")

# ---------- Main (for standalone testing) ----------
if __name__ == "__main__":
    os.makedirs(RECV_SAVE_DIR, exist_ok=True)
    # ensure log file exists
    try:
        open(CHAT_LOG_PATH, "a", encoding="utf-8").close()
    except:
        pass

    root = ctk.CTk()  # minimal root to host Toplevel if run standalone
    root.withdraw()
    win = LanChatWindow(master=root)
    win.mainloop()
