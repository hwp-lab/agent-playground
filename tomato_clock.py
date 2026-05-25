import tkinter as tk
from tkinter import ttk
import json
import os
import winsound
import threading

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

DEFAULT_SETTINGS = {
    "work_duration": 25,
    "short_break": 5,
    "long_break": 15,
    "long_break_interval": 4,
}

# 配色方案
COLORS = {
    "work": "#e74c3c",
    "short_break": "#2ecc71",
    "long_break": "#3498db",
    "bg": "#fafafa",
    "text": "#2c3e50",
    "btn_bg": "#ecf0f1",
    "btn_fg": "#2c3e50",
    "counter_bg": "#f0f0f0",
}


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key in DEFAULT_SETTINGS:
                if key not in data:
                    data[key] = DEFAULT_SETTINGS[key]
            return data
        except (json.JSONDecodeError, IOError):
            return dict(DEFAULT_SETTINGS)
    return dict(DEFAULT_SETTINGS)


def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)


def format_time(seconds):
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"


class TomatoClock:
    def __init__(self, root):
        self.root = root
        self.settings = load_settings()

        self.work_duration = self.settings["work_duration"] * 60
        self.short_break = self.settings["short_break"] * 60
        self.long_break = self.settings["long_break"] * 60
        self.long_break_interval = self.settings["long_break_interval"]

        self.current_time = self.work_duration
        self.tomato_count = 0
        self.mode = "work"
        self.state = "idle"
        self.after_id = None

        self._build_ui()
        self._update_display()

    def _build_ui(self):
        self.root.title("番茄钟")
        self.root.configure(bg=COLORS["bg"])
        self.root.resizable(False, False)

        # 主容器
        main = tk.Frame(self.root, bg=COLORS["bg"], padx=40, pady=30)
        main.pack()

        # 标题
        title = tk.Label(
            main,
            text="番茄钟",
            font=("Microsoft YaHei", 18, "bold"),
            fg=COLORS["text"],
            bg=COLORS["bg"],
        )
        title.pack(pady=(0, 20))

        # 计时显示
        self.time_label = tk.Label(
            main,
            text="25:00",
            font=("Consolas", 56, "bold"),
            fg=COLORS["work"],
            bg=COLORS["bg"],
        )
        self.time_label.pack()

        # 模式标签
        self.mode_label = tk.Label(
            main,
            text="准备开始",
            font=("Microsoft YaHei", 12),
            fg=COLORS["text"],
            bg=COLORS["bg"],
        )
        self.mode_label.pack(pady=(4, 24))

        # 按钮区
        btn_frame = tk.Frame(main, bg=COLORS["bg"])
        btn_frame.pack()

        self.start_btn = tk.Button(
            btn_frame,
            text="开始",
            font=("Microsoft YaHei", 11),
            width=8,
            command=self.start,
            bg="#2ecc71",
            fg="white",
            activebackground="#27ae60",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
        )
        self.start_btn.pack(side="left", padx=4)

        self.pause_btn = tk.Button(
            btn_frame,
            text="暂停",
            font=("Microsoft YaHei", 11),
            width=8,
            command=self.pause,
            bg="#f39c12",
            fg="white",
            activebackground="#e67e22",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            state="disabled",
        )
        self.pause_btn.pack(side="left", padx=4)

        self.reset_btn = tk.Button(
            btn_frame,
            text="重置",
            font=("Microsoft YaHei", 11),
            width=8,
            command=self.reset,
            bg="#95a5a6",
            fg="white",
            activebackground="#7f8c8d",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
        )
        self.reset_btn.pack(side="left", padx=4)

        # 进度条
        self.progress = ttk.Progressbar(
            main,
            length=280,
            mode="determinate",
            style="TProgressbar",
        )
        self.progress["maximum"] = self.work_duration
        self.progress["value"] = self.work_duration
        self.progress.pack(pady=(20, 4))

        # 番茄计数
        counter_frame = tk.Frame(main, bg=COLORS["counter_bg"])
        counter_frame.pack(pady=(12, 12))

        self.counter_label = tk.Label(
            counter_frame,
            text="已完成: 0 个番茄",
            font=("Microsoft YaHei", 11),
            fg=COLORS["text"],
            bg=COLORS["counter_bg"],
            padx=20,
            pady=6,
        )
        self.counter_label.pack()

        # 设置按钮
        self.settings_btn = tk.Button(
            main,
            text="设置",
            font=("Microsoft YaHei", 10),
            width=6,
            command=self._open_settings,
            bg=COLORS["btn_bg"],
            fg=COLORS["btn_fg"],
            relief="flat",
            cursor="hand2",
        )
        self.settings_btn.pack()

        # 居中窗口
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"+{x}+{y}")

        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _update_display(self):
        self.time_label.config(text=format_time(self.current_time))
        self.progress["maximum"] = self._get_total_duration()
        self.progress["value"] = self._get_total_duration() - self.current_time

        color = COLORS[self.mode]
        self.time_label.config(fg=color)

        mode_names = {"work": "专注中...", "short_break": "短休息中...", "long_break": "长休息中..."}

        if self.state == "idle":
            if self.mode == "work":
                self.mode_label.config(text="准备开始")
            else:
                self.mode_label.config(text="准备休息")
        elif self.state == "paused":
            self.mode_label.config(text="已暂停")
        else:
            self.mode_label.config(text=mode_names[self.mode])

        self.counter_label.config(text=f"已完成: {self.tomato_count} 个番茄")

    def _get_total_duration(self):
        durations = {
            "work": self.work_duration,
            "short_break": self.short_break,
            "long_break": self.long_break,
        }
        return durations[self.mode]

    def _set_button_state(self, running):
        if running:
            self.start_btn.config(state="disabled")
            self.pause_btn.config(state="normal")
            self.settings_btn.config(state="disabled")
        else:
            self.start_btn.config(state="normal")
            self.pause_btn.config(state="disabled")
            self.settings_btn.config(state="normal")

    def start(self):
        if self.state == "idle":
            self._set_button_state(True)
            self.state = "running"
            self._tick()
        elif self.state == "paused":
            self._set_button_state(True)
            self.state = "running"
            self._tick()

    def pause(self):
        if self.state == "running":
            self.state = "paused"
            if self.after_id:
                self.root.after_cancel(self.after_id)
                self.after_id = None
            self._set_button_state(False)
            self._update_display()

    def reset(self):
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.state = "idle"
        self.mode = "work"
        self.current_time = self.work_duration
        self._set_button_state(False)
        self._update_display()

    def _tick(self):
        if self.state != "running":
            return

        if self.current_time > 0:
            self.current_time -= 1
            self._update_display()
            self.after_id = self.root.after(1000, self._tick)
        else:
            self._on_timer_end()

    def _on_timer_end(self):
        self.after_id = None
        self.state = "idle"

        if self.mode == "work":
            self.tomato_count += 1
            self._update_display()

            if self.tomato_count % self.long_break_interval == 0:
                self.mode = "long_break"
                self.current_time = self.long_break
            else:
                self.mode = "short_break"
                self.current_time = self.short_break
        else:
            self.mode = "work"
            self.current_time = self.work_duration

        self._set_button_state(False)
        self._update_display()
        self._notify()

    def _notify(self):
        threading.Thread(target=self._play_sound, daemon=True).start()

        msg = "专注时间结束，休息一下吧！" if self.mode != "work" else "休息时间结束，开始新的番茄吧！"
        self.root.after(100, lambda: tk.messagebox.showinfo("番茄钟提醒", msg))

    def _play_sound(self):
        for _ in range(3):
            winsound.Beep(800, 200)
            winsound.Sleep(100)
        winsound.Beep(1000, 400)

    def _open_settings(self):
        SettingsDialog(self)

    def _on_close(self):
        if self.after_id:
            self.root.after_cancel(self.after_id)
        self.root.destroy()

    def apply_settings(self, new_settings):
        self.settings = new_settings
        self.work_duration = new_settings["work_duration"] * 60
        self.short_break = new_settings["short_break"] * 60
        self.long_break = new_settings["long_break"] * 60
        self.long_break_interval = new_settings["long_break_interval"]
        save_settings(new_settings)

        self.state = "idle"
        self.mode = "work"
        self.current_time = self.work_duration
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self._set_button_state(False)
        self._update_display()


class SettingsDialog:
    def __init__(self, clock):
        self.clock = clock
        self.result = dict(clock.settings)

        self.win = tk.Toplevel(clock.root)
        self.win.title("设置")
        self.win.configure(bg=COLORS["bg"])
        self.win.resizable(False, False)
        self.win.transient(clock.root)
        self.win.grab_set()

        frame = tk.Frame(self.win, bg=COLORS["bg"], padx=30, pady=20)
        frame.pack()

        tk.Label(
            frame,
            text="番茄钟设置",
            font=("Microsoft YaHei", 14, "bold"),
            fg=COLORS["text"],
            bg=COLORS["bg"],
        ).pack(pady=(0, 16))

        vars_data = {}
        rows = [
            ("专注时长 (分钟):", "work_duration"),
            ("短休息时长 (分钟):", "short_break"),
            ("长休息时长 (分钟):", "long_break"),
            ("长休息间隔 (个番茄):", "long_break_interval"),
        ]

        entries = {}
        for label_text, key in rows:
            row_frame = tk.Frame(frame, bg=COLORS["bg"])
            row_frame.pack(pady=4, fill="x")

            tk.Label(
                row_frame,
                text=label_text,
                font=("Microsoft YaHei", 11),
                fg=COLORS["text"],
                bg=COLORS["bg"],
                width=18,
                anchor="e",
            ).pack(side="left", padx=(0, 8))

            var = tk.StringVar(value=str(self.result[key]))
            vars_data[key] = var
            entry = tk.Entry(
                row_frame,
                textvariable=var,
                font=("Microsoft YaHei", 11),
                width=8,
                justify="center",
            )
            entry.pack(side="left")
            entries[key] = entry

        btn_frame = tk.Frame(frame, bg=COLORS["bg"])
        btn_frame.pack(pady=(16, 0))

        tk.Button(
            btn_frame,
            text="保存",
            font=("Microsoft YaHei", 11),
            width=8,
            command=lambda: self._save(vars_data),
            bg="#2ecc71",
            fg="white",
            activebackground="#27ae60",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=4)

        tk.Button(
            btn_frame,
            text="取消",
            font=("Microsoft YaHei", 11),
            width=8,
            command=self.win.destroy,
            bg="#e74c3c",
            fg="white",
            activebackground="#c0392b",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
        ).pack(side="left", padx=4)

        self._center_window()
        entries["work_duration"].focus_set()

    def _center_window(self):
        self.win.update_idletasks()
        w = self.win.winfo_width()
        h = self.win.winfo_height()
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.win.geometry(f"+{x}+{y}")

    def _save(self, vars_data):
        for key in self.result:
            try:
                val = int(vars_data[key].get())
                if val < 1:
                    val = 1
                if val > 120:
                    val = 120
                self.result[key] = val
            except ValueError:
                pass  # 无效输入保持原值

        self.clock.apply_settings(self.result)
        self.win.destroy()


def main():
    root = tk.Tk()
    TomatoClock(root)
    root.mainloop()


if __name__ == "__main__":
    main()
