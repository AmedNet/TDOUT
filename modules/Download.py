import customtkinter as ctk
import threading
import queue
import requests
import os
import time
from concurrent.futures import ThreadPoolExecutor

# 喵~ 帮主人把字节转换成好看的单位
def format_size(size):
    if size < 1024:
        return f"{size} B"
    elif size < 1024 ** 2:
        return f"{size / 1024:.2f} KB"
    elif size < 1024 ** 3:
        return f"{size / (1024 ** 2):.2f} MB"
    else:
        return f"{size / (1024 ** 3):.2f} GB"


class MeowDownloader(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("多线程下载器")
        self.geometry("750x600")

        self.APPpath = os.getcwd()
        self.stop_event = threading.Event()

        # 喵~ 顶部的输入区
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.pack(fill="x", padx=20, pady=10)

        self.url_label = ctk.CTkLabel(self.input_frame, text="下载链接:")
        self.url_label.pack(side="left", padx=5)
        self.url_entry = ctk.CTkEntry(self.input_frame, width=500)
        self.url_entry.pack(side="left", padx=5)

        self.thread_label = ctk.CTkLabel(self.input_frame, text="线程:")
        self.thread_label.pack(side="left", padx=5)
        self.thread_entry = ctk.CTkEntry(self.input_frame, width=50)
        self.thread_entry.insert(0, "64")  # 喵~ 默认8线程演示比较好看哦
        self.thread_entry.pack(side="left", padx=5)

        self.start_btn = ctk.CTkButton(self.input_frame, text="开始下载", width=80, command=self.start_download)
        self.start_btn.pack(side="left", padx=10)

        # 喵~ 总体进度区
        self.info_frame = ctk.CTkFrame(self)
        self.info_frame.pack(fill="x", padx=20, pady=5)

        self.main_progress = ctk.CTkProgressBar(self.info_frame)
        self.main_progress.pack(fill="x", padx=15, pady=(15, 5))
        self.main_progress.set(0)

        self.status_label = ctk.CTkLabel(self.info_frame, text="等待主人下达任务喵~")
        self.status_label.pack(pady=5)

        # 喵~ 详细的分段网格区 (可滚动哦)
        self.threads_frame = ctk.CTkScrollableFrame(self, label_text="各线程下载详情")
        self.threads_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.error_label = ctk.CTkLabel(self, text="", text_color="red")

        self.thread_ui_elements = []  # 喵~ 这里用来保存每个小线程的UI引用
        self.download_speed = 0
        self.last_time = time.time()
        self.last_downloaded = 0

    def start_download(self):
        url = self.url_entry.get()
        if not url:
            self.error_label.configure(text="主人忘记填链接啦！")
            self.error_label.pack(pady=5)
            return

        self.start_btn.configure(state="disabled")
        # 喵~ 启动新线程去执行，不让界面卡顿
        threading.Thread(target=self._download_file, args=(url,), daemon=True).start()

    def _download_file(self, url: str):
        self.error_label.pack_forget()
        if not hasattr(self, 'stop_event'):
            self.stop_event = threading.Event()
        self.stop_event.clear()

        try:
            if not os.path.isdir(self.APPpath):
                raise FileNotFoundError(f"目录不存在: {self.APPpath}")

            local_filename = os.path.join(self.APPpath, os.path.basename(url))

            head = requests.head(url)
            total_length = int(head.headers.get('content-length', 0))

            if total_length == 0:
                raise Exception("无法获取文件大小或文件为空")

            try:
                thread_count = int(self.thread_entry.get())
            except ValueError:
                thread_count = 8

            chunk_size = total_length // thread_count

            with open(local_filename, 'wb') as f:
                f.seek(total_length - 1)
                f.write(b'\0')

            self.main_progress.set(0)
            progress_queue = queue.Queue()

            # 喵~ 动态清空并生成每个线程的UI网格
            for widget in self.threads_frame.winfo_children():
                widget.destroy()
            self.thread_ui_elements.clear()

            # 喵~ 双列排布，好看又紧凑
            for i in range(thread_count):
                frame = ctk.CTkFrame(self.threads_frame)
                frame.grid(row=i // 2, column=i % 2, padx=10, pady=5, sticky="ew")
                self.threads_frame.grid_columnconfigure(0, weight=1)
                self.threads_frame.grid_columnconfigure(1, weight=1)

                lbl = ctk.CTkLabel(frame, text=f"线程 {i + 1}: 0%")
                lbl.pack(side="left", padx=10)
                pb = ctk.CTkProgressBar(frame, width=120)
                pb.set(0)
                pb.pack(side="right", padx=10)

                self.thread_ui_elements.append({
                    "label": lbl,
                    "progress": pb,
                    "downloaded": 0,
                    "total": chunk_size if i < thread_count - 1 else total_length - i * chunk_size
                })

            def download_range(thread_index, start, end, file_path):
                headers = {'Range': f'bytes={start}-{end}'}
                try:
                    with requests.get(url, headers=headers, stream=True) as r:
                        with open(file_path, 'rb+') as f:
                            f.seek(start)
                            for chunk in r.iter_content(chunk_size=8192):
                                if self.stop_event.is_set():
                                    break
                                if chunk:
                                    f.write(chunk)
                                    # 喵~ 把线程编号和下载大小一起发出去
                                    progress_queue.put((thread_index, len(chunk)))
                except Exception as e:
                    print(f"线程 {thread_index} 发生错误: {e}")

            self.downloaded_bytes = 0
            self.last_time = time.time()
            self.last_downloaded = 0

            def update_progress():
                if not self.main_progress.winfo_exists() or self.stop_event.is_set():
                    return

                try:
                    # 喵~ 拼命从队列里拿出所有分块数据
                    while True:
                        t_index, chunk_len = progress_queue.get_nowait()
                        self.downloaded_bytes += chunk_len
                        self.thread_ui_elements[t_index]["downloaded"] += chunk_len
                except queue.Empty:
                    pass

                # 喵~ 计算总速度（每0.5秒刷新一次速度，避免闪烁哦）
                current_time = time.time()
                time_diff = current_time - self.last_time
                if time_diff >= 0.5:
                    speed = (self.downloaded_bytes - self.last_downloaded) / time_diff
                    self.download_speed = speed
                    self.last_downloaded = self.downloaded_bytes
                    self.last_time = current_time

                    # 喵~ 更新UI的文字和主进度条
                    percent = (self.downloaded_bytes / total_length) * 100
                    status_text = f"总进度: {percent:.1f}%  |  已下载: {format_size(self.downloaded_bytes)} / {format_size(total_length)}  |  速度: {format_size(self.download_speed)}/s"
                    self.status_label.configure(text=status_text)

                    # 喵~ 刷新各个小线程网格里的UI
                    for i, t_info in enumerate(self.thread_ui_elements):
                        t_percent = t_info["downloaded"] / t_info["total"] if t_info["total"] > 0 else 1
                        t_info["label"].configure(text=f"线程 {i + 1}: {t_percent * 100:.1f}%")
                        t_info["progress"].set(t_percent)

                if self.downloaded_bytes < total_length:
                    self.main_progress.set(self.downloaded_bytes / total_length)
                    self.main_progress.after(100, update_progress)
                else:
                    self.main_progress.set(1.0)
                    self.status_label.configure(text=f"下载完成喵！总大小: {format_size(total_length)}")
                    for t_info in self.thread_ui_elements:
                        t_info["progress"].set(1.0)
                        t_info["label"].configure(text=f"线程完成: 100%")
                    self.start_btn.configure(state="normal")
                    print(f"下载完成: {local_filename}")

            self.main_progress.after(100, update_progress)

            def start_download_threads():
                with ThreadPoolExecutor(max_workers=thread_count) as executor:
                    for i in range(thread_count):
                        start = i * chunk_size
                        end = (i + 1) * chunk_size - 1 if i < thread_count - 1 else total_length - 1
                        executor.submit(download_range, i, start, end, local_filename)

            threading.Thread(target=start_download_threads, daemon=True).start()

        except Exception as e:
            error_msg = f"下载失败: {e}"
            self.error_label.configure(text=error_msg)
            self.error_label.pack(pady=5)
            self.start_btn.configure(state="normal")

def open_download():
    app = MeowDownloader()
    app.mainloop()

if __name__ == "__main__":
    open_download()