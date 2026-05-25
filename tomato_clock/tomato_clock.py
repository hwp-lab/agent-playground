import tkinter as tk
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

# ── Deep Focus 色号字典 ──────────────────────────
COLORS = {
    "bg_deep":           "#1a1a1c",   # 窗口/卡片背景（最深）
    "bg_card":           "#242429",   # 容器、按钮背景（次级）
    "bg_hover":          "#2e2e35",   # hover 微抬
    "track":             "#3a3a42",   # 环形进度背景轨道
    "text_primary":      "#ebebf0",   # 标题、计时数字
    "text_secondary":    "#9a9aa6",   # 状态标签、辅助文字
    "text_disabled":     "#5a5a66",   # 禁用态文字
    "work":              "#f08c4b",   # 暖橙 —— 专注
    "work_deep":         "#d97430",   # 工作模式 hover
    "short_break":       "#5ec4a3",   # 薄荷绿 —— 短休
    "short_break_deep":  "#3daa87",   # 短休 hover
    "long_break":        "#9b8ec4",   # 薰衣草紫 —— 长休
    "long_break_deep":   "#7b6ea8",   # 长休 hover
    "danger":            "#e0556a",   # 取消 / 重置 hover
    "success":           "#5ec4a3",   # 保存按钮
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

    # ── UI 构建 ────────────────────────────────────

    def _build_ui(self):
        self.root.title("番茄钟 · Deep Focus")
        self.root.configure(bg=COLORS["bg_deep"])
        self.root.resizable(False, False)

        main = tk.Frame(self.root, bg=COLORS["bg_deep"], padx=32, pady=24)
        main.pack()

        # ── 模式指示器：三个圆点 ──
        indicator_frame = tk.Frame(main, bg=COLORS["bg_deep"])
        indicator_frame.pack(pady=(0, 10))

        self.mode_dot_work = tk.Label(
            indicator_frame, text="●", font=("", 7),
            fg=COLORS["work"], bg=COLORS["bg_deep"])
        self.mode_dot_work.pack(side="left", padx=(0, 3))
        tk.Label(indicator_frame, text="专注", font=("Microsoft YaHei", 9),
                 fg=COLORS["text_secondary"], bg=COLORS["bg_deep"]).pack(
                     side="left", padx=(0, 16))

        self.mode_dot_short = tk.Label(
            indicator_frame, text="○", font=("", 7),
            fg=COLORS["text_disabled"], bg=COLORS["bg_deep"])
        self.mode_dot_short.pack(side="left", padx=(0, 3))
        tk.Label(indicator_frame, text="短休", font=("Microsoft YaHei", 9),
                 fg=COLORS["text_secondary"], bg=COLORS["bg_deep"]).pack(
                     side="left", padx=(0, 16))

        self.mode_dot_long = tk.Label(
            indicator_frame, text="○", font=("", 7),
            fg=COLORS["text_disabled"], bg=COLORS["bg_deep"])
        self.mode_dot_long.pack(side="left", padx=(0, 3))
        tk.Label(indicator_frame, text="长休", font=("Microsoft YaHei", 9),
                 fg=COLORS["text_secondary"], bg=COLORS["bg_deep"]).pack(side="left")

        # ── 环形进度 + 中央时间 ──
        ring_size = 250
        self.canvas = tk.Canvas(
            main, width=ring_size, height=ring_size,
            bg=COLORS["bg_deep"], highlightthickness=0)
        self.canvas.pack(pady=(4, 6))

        # 环形背景轨道
        margin = 28
        self.canvas.create_arc(
            margin, margin, ring_size - margin, ring_size - margin,
            outline=COLORS["track"], width=10, style="arc",
            start=90, extent=-359.99, tags="track")

        # 环形进度弧
        self.canvas.create_arc(
            margin, margin, ring_size - margin, ring_size - margin,
            outline=COLORS["work"], width=10, style="arc",
            start=90, extent=-359.99, tags="progress")

        # 中央时间数字
        cx, cy = ring_size // 2, ring_size // 2
        self.canvas.create_text(
            cx, cy - 8, text="25:00",
            font=("Consolas", 42, "bold"),
            fill=COLORS["text_primary"], tags="time_text")

        # 状态小字
        self.canvas.create_text(
            cx, cy + 30, text="准备开始",
            font=("Microsoft YaHei", 10),
            fill=COLORS["text_secondary"], tags="status_text")

        # ── 按钮区 ──
        btn_frame = tk.Frame(main, bg=COLORS["bg_deep"])
        btn_frame.pack(pady=(14, 0))

        btn_cfg = {
            "font": ("Microsoft YaHei", 10),
            "width": 7, "relief": "flat", "cursor": "hand2",
            "borderwidth": 0, "padx": 2, "pady": 6,
        }

        self.start_btn = tk.Button(
            btn_frame, text="开始", command=self.start,
            bg=COLORS["work"], fg="#ffffff",
            activebackground=COLORS["work_deep"],
            activeforeground="#ffffff", **btn_cfg)
        self.start_btn.pack(side="left", padx=3)

        self.pause_btn = tk.Button(
            btn_frame, text="暂停", command=self.pause,
            bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
            activebackground=COLORS["bg_hover"],
            activeforeground=COLORS["text_primary"],
            state="disabled", **btn_cfg)
        self.pause_btn.pack(side="left", padx=3)

        self.reset_btn = tk.Button(
            btn_frame, text="重置", command=self.reset,
            bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
            activebackground=COLORS["danger"],
            activeforeground="#ffffff", **btn_cfg)
        self.reset_btn.pack(side="left", padx=3)

        # ── 底部：番茄计数 + 齿轮 ──
        bottom = tk.Frame(main, bg=COLORS["bg_deep"])
        bottom.pack(fill="x", pady=(20, 0))

        self.counter_label = tk.Label(
            bottom, text="已完成 0 个番茄",
            font=("Microsoft YaHei", 9),
            fg=COLORS["text_secondary"], bg=COLORS["bg_deep"])
        self.counter_label.pack(side="left")

        self.settings_btn = tk.Label(
            bottom, text="⚙", font=("", 14),
            fg=COLORS["text_disabled"], bg=COLORS["bg_deep"],
            cursor="hand2")
        self.settings_btn.pack(side="right")
        self.settings_btn.bind("<Button-1>", lambda e: self._open_settings())
        self.settings_btn.bind("<Enter>",
            lambda e: self.settings_btn.config(fg=COLORS["text_secondary"]))
        self.settings_btn.bind("<Leave>",
            lambda e: self.settings_btn.config(fg=COLORS["text_disabled"]))

        # 居中窗口
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"+{x}+{y}")

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── 状态刷新 ──────────────────────────────────

    def _update_display(self):
        total = self._get_total_duration()
        extent = -(self.current_time / total) * 360 if total > 0 else 0

        color = COLORS[self.mode]
        self.canvas.itemconfig("progress", outline=color, extent=extent)
        self.canvas.itemconfig("time_text", text=format_time(self.current_time), fill=color)

        # 状态小字
        mode_names = {"work": "专注中", "short_break": "短休息", "long_break": "长休息"}
        if self.state == "idle":
            status = "准备开始" if self.mode == "work" else "准备休息"
        elif self.state == "paused":
            status = "已暂停"
        else:
            status = mode_names[self.mode]
        self.canvas.itemconfig("status_text", text=status)

        # 模式圆点
        dot_map = {
            "work":         (self.mode_dot_work,   COLORS["work"]),
            "short_break":  (self.mode_dot_short,  COLORS["short_break"]),
            "long_break":   (self.mode_dot_long,   COLORS["long_break"]),
        }
        for m, (dot, c) in dot_map.items():
            if m == self.mode:
                dot.config(text="●", fg=c)
            else:
                dot.config(text="○", fg=COLORS["text_disabled"])

        # 番茄计数
        self.counter_label.config(text=f"已完成 {self.tomato_count} 个番茄")

        # 开始按钮颜色跟随模式
        self.start_btn.config(bg=color, activebackground=COLORS.get(f"{self.mode}_deep", color))

    def _get_total_duration(self):
        return {
            "work": self.work_duration,
            "short_break": self.short_break,
            "long_break": self.long_break,
        }[self.mode]

    def _set_button_state(self, running):
        if running:
            self.start_btn.config(state="disabled", text="运行中")
            self.pause_btn.config(state="normal")
            self.settings_btn.config(fg=COLORS["track"])
        else:
            self.start_btn.config(state="normal", text="开始")
            self.pause_btn.config(state="disabled")
            self.settings_btn.config(fg=COLORS["text_disabled"])

    # ── 计时控制 ──────────────────────────────────

    def start(self):
        if self.state in ("idle", "paused"):
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
        self.root.after(100, lambda: self._show_notification(msg))

    def _play_sound(self):
        for _ in range(3):
            winsound.Beep(800, 200)
            winsound.Sleep(100)
        winsound.Beep(1000, 400)

    def _show_notification(self, msg):
        popup = tk.Toplevel(self.root)
        popup.title("")
        popup.configure(bg=COLORS["bg_deep"])
        popup.resizable(False, False)
        popup.transient(self.root)
        popup.grab_set()
        popup.overrideredirect(True)

        # 卡片容器
        card = tk.Frame(popup, bg=COLORS["bg_card"], padx=1, pady=1)
        card.pack()

        inner = tk.Frame(card, bg=COLORS["bg_deep"], padx=28, pady=18)
        inner.pack()

        # 顶部 accent 色条
        accent_bar = tk.Frame(inner, bg=COLORS[self.mode], height=3)
        accent_bar.pack(fill="x", pady=(0, 12))

        tk.Label(
            inner, text=msg,
            font=("Microsoft YaHei", 11),
            fg=COLORS["text_primary"], bg=COLORS["bg_deep"],
            wraplength=260,
        ).pack(pady=(0, 12))

        dismiss_btn = tk.Label(
            inner, text="知道了",
            font=("Microsoft YaHei", 10),
            fg=COLORS[self.mode], bg=COLORS["bg_deep"],
            cursor="hand2", padx=16, pady=4,
        )
        dismiss_btn.pack()
        dismiss_btn.bind("<Button-1>", lambda e: popup.destroy())
        dismiss_btn.bind("<Enter>", lambda e: dismiss_btn.config(fg="#ffffff"))
        dismiss_btn.bind("<Leave>", lambda e: dismiss_btn.config(fg=COLORS[self.mode]))

        # 居中于主窗口
        popup.update_idletasks()
        pw = popup.winfo_width()
        ph = popup.winfo_height()
        rx = self.root.winfo_rootx()
        ry = self.root.winfo_rooty()
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        x = rx + (rw - pw) // 2
        y = ry + (rh - ph) // 2
        popup.geometry(f"+{x}+{y}")

        # 3 秒后自动关闭
        popup.after(3000, popup.destroy)

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


# ── 设置弹窗 ──────────────────────────────────


class SettingsDialog:
    def __init__(self, clock):
        self.clock = clock
        self.result = dict(clock.settings)

        self.win = tk.Toplevel(clock.root)
        self.win.title("设置")
        self.win.configure(bg=COLORS["bg_deep"])
        self.win.resizable(False, False)
        self.win.transient(clock.root)
        self.win.grab_set()

        frame = tk.Frame(self.win, bg=COLORS["bg_deep"], padx=30, pady=20)
        frame.pack()

        tk.Label(frame, text="偏好设置", font=("Microsoft YaHei", 14, "bold"),
                 fg=COLORS["text_primary"], bg=COLORS["bg_deep"]).pack(pady=(0, 16))

        rows = [
            ("专注时长 (分钟):", "work_duration"),
            ("短休息时长 (分钟):", "short_break"),
            ("长休息时长 (分钟):", "long_break"),
            ("长休息间隔 (个番茄):", "long_break_interval"),
        ]

        entries = {}
        vars_data = {}
        for label_text, key in rows:
            row_frame = tk.Frame(frame, bg=COLORS["bg_deep"])
            row_frame.pack(pady=4, fill="x")

            tk.Label(row_frame, text=label_text, font=("Microsoft YaHei", 11),
                     fg=COLORS["text_secondary"], bg=COLORS["bg_deep"],
                     width=18, anchor="e").pack(side="left", padx=(0, 8))

            var = tk.StringVar(value=str(self.result[key]))
            vars_data[key] = var
            entry = tk.Entry(row_frame, textvariable=var, font=("Microsoft YaHei", 11),
                             width=8, justify="center",
                             bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                             insertbackground=COLORS["text_primary"],
                             relief="flat", borderwidth=4)
            entry.pack(side="left")
            entries[key] = entry

        btn_frame = tk.Frame(frame, bg=COLORS["bg_deep"])
        btn_frame.pack(pady=(18, 0))

        tk.Button(btn_frame, text="取消", command=self.win.destroy,
                  font=("Microsoft YaHei", 10), width=8, relief="flat",
                  bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                  activebackground=COLORS["danger"],
                  activeforeground="#ffffff", cursor="hand2",
                  borderwidth=0, padx=2, pady=6).pack(side="left", padx=4)

        tk.Button(btn_frame, text="保存", command=lambda: self._save(vars_data),
                  font=("Microsoft YaHei", 10), width=8, relief="flat",
                  bg=COLORS["success"], fg="#ffffff",
                  activebackground=COLORS["short_break_deep"],
                  activeforeground="#ffffff", cursor="hand2",
                  borderwidth=0, padx=2, pady=6).pack(side="left", padx=4)

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
                val = max(1, min(val, 120))
                self.result[key] = val
            except ValueError:
                pass
        self.clock.apply_settings(self.result)
        self.win.destroy()


def main():
    root = tk.Tk()
    TomatoClock(root)
    root.mainloop()


if __name__ == "__main__":
    main()
