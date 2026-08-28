# -*- coding: utf-8 -*-
"""
20以内加减法小游戏 - 美化版
- 圆角按钮 + hover/pressed 反馈
- 护眼淡米黄背景
- 大字号圆润题目字体
- Canvas 进度条 + 倒计时闪烁
- 答对/答错音效反馈
- 答对3种特效轮流:全屏彩带 / 星星爆发 / 大对勾弹跳
- 答错3种特效轮流:题目摇头 / 哭脸气泡 / 红框抖动
- 难度模式切换(10以内 / 20以内 / 进位加法 / 退位减法)
- 错题回顾弹窗
"""

import math
import random
import sys
import time
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox
import winsound


# ---------------- 全局配置 ----------------
TOTAL_QUESTIONS = 10
SECONDS_PER_QUESTION = 15
SCORE_CORRECT = 10
SCORE_BONUS_MAX = 5

# 配色(护眼暖色调)
C_BG = "#FFF8E7"           # 淡米黄背景
C_CARD = "#FFFFFF"
C_ALT = "#F5EFD8"          # 隔行底色
C_TEXT = "#37474F"
C_SUBTEXT = "#78909C"
C_ACCENT = "#FF8C42"       # 主橙
C_ACCENT_HOVER = "#FF7A2E"
C_ACCENT_PRESSED = "#E6691C"
C_GREEN = "#4CAF50"
C_GREEN_HOVER = "#43A047"
C_GREEN_PRESSED = "#388E3C"
C_BLUE = "#5C6BC0"
C_BLUE_HOVER = "#3F51B5"
C_BLUE_PRESSED = "#303F9F"
C_RED = "#F44336"
C_PROGRESS_BG = "#E8E0CC"
C_PROGRESS_FILL = "#5C6BC0"
C_PROGRESS_WARN = "#F44336"
C_TRANSPARENT = "#FF00FF"     # overlay 透明色(必须选不常用颜色)
C_BUBBLE_BG = "#FFFFFF"

# 难度模式
# type: any=普通加减法, carry_add=进位加法, borrow_sub=退位减法
MODES = {
    "10以内加减法":   {"max": 10, "type": "any"},
    "20以内加减法":   {"max": 20, "type": "any"},
    "20以内进位加法": {"max": 20, "type": "carry_add"},
    "20以内退位减法": {"max": 20, "type": "borrow_sub"},
}
DEFAULT_MODE = "20以内加减法"


# ---------------- 字体选取 ----------------
def pick_font(candidates, fallback="TkDefaultFont"):
    try:
        avail = set(tkfont.families())
        for c in candidates:
            if c in avail:
                return c
    except Exception:
        pass
    return fallback


FONT_NUM = pick_font(["Comic Sans MS", "Segoe UI", "Microsoft YaHei UI"])
FONT_UI = pick_font(["Microsoft YaHei UI", "Segoe UI"])


# ---------------- 音效(异步线程,避免阻塞 UI) ----------------
def _beep_async(*pairs):
    def _t():
        for freq, dur in pairs:
            try:
                winsound.Beep(freq, dur)
            except Exception:
                pass
    threading.Thread(target=_t, daemon=True).start()


def sound_correct():
    _beep_async((880, 90), (1175, 120))


def sound_wrong():
    _beep_async((330, 150), (247, 200))


# ---------------- 圆角矩形辅助 ----------------
def _round_rect(canvas, x1, y1, x2, y2, r, fill):
    """在 canvas 上绘制圆角矩形"""
    w = x2 - x1
    h = y2 - y1
    if w <= 0 or h <= 0:
        return
    r = max(0, min(r, h // 2, w // 2))
    if r <= 0:
        canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline="")
        return
    canvas.create_rectangle(x1 + r, y1, x2 - r, y2, fill=fill, outline="")
    canvas.create_rectangle(x1, y1 + r, x2, y2 - r, fill=fill, outline="")
    canvas.create_oval(x1, y1, x1 + 2 * r, y1 + 2 * r, fill=fill, outline="")
    canvas.create_oval(x2 - 2 * r, y1, x2, y1 + 2 * r, fill=fill, outline="")
    canvas.create_oval(x1, y2 - 2 * r, x1 + 2 * r, y2, fill=fill, outline="")
    canvas.create_oval(x2 - 2 * r, y2 - 2 * r, x2, y2, fill=fill, outline="")


# ---------------- 圆角按钮 ----------------
class RoundButton(tk.Canvas):
    """圆角矩形按钮,支持 hover / pressed 颜色变化"""

    def __init__(self, parent, text, command,
                 bg=C_ACCENT, fg="white",
                 hover_bg=C_ACCENT_HOVER, pressed_bg=C_ACCENT_PRESSED,
                 width=160, height=48, font=None, radius=22):
        super().__init__(parent, width=width, height=height,
                         bd=0, highlightthickness=0,
                         bg=parent.cget("bg"))
        self._cmd = command
        self._text = text
        self._bg = bg
        self._hover_bg = hover_bg
        self._pressed_bg = pressed_bg
        self._fg = fg
        # 注意:不能用 self._w / self._h,会覆盖 tkinter 内部 widget path
        self._bw = width
        self._bh = height
        self._br = radius
        self._font = font or (FONT_UI, 13, "bold")
        self._state = "normal"
        self._cur_color = bg
        self._draw(bg)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _draw(self, color):
        self.delete("all")
        _round_rect(self, 0, 0, self._bw, self._bh, self._br, color)
        self.create_text(self._bw / 2, self._bh / 2, text=self._text,
                         fill=self._fg, font=self._font)
        self._cur_color = color

    def _on_enter(self, _):
        if self._state == "normal":
            self._draw(self._hover_bg)
            self.config(cursor="hand2")

    def _on_leave(self, _):
        if self._state == "normal":
            self._draw(self._bg)

    def _on_press(self, _):
        self._state = "pressed"
        self._draw(self._pressed_bg)

    def _on_release(self, _):
        self._state = "normal"
        self._draw(self._hover_bg)
        if self._cmd:
            self._cmd()


# ---------------- 进度条 ----------------
class ProgressBar(tk.Canvas):
    """圆角进度条"""

    def __init__(self, parent, width, height=12,
                 bg=C_PROGRESS_BG, fill=C_PROGRESS_FILL, warn=C_PROGRESS_WARN):
        super().__init__(parent, width=width, height=height,
                         bd=0, highlightthickness=0,
                         bg=parent.cget("bg"))
        # 注意:不能用 self._w / self._h,会覆盖 tkinter 内部 widget path
        self._pw = width
        self._ph = height
        self._bg = bg
        self._fill = fill
        self._warn = warn
        self.update_ratio(1.0)

    def update_ratio(self, ratio, warn=False):
        self.delete("all")
        # 背景条
        _round_rect(self, 0, 0, self._pw, self._ph, self._ph // 2, self._bg)
        # 前景条
        fw = max(self._ph, int(self._pw * max(0, min(1, ratio))))
        color = self._warn if warn else self._fill
        _round_rect(self, 0, 0, fw, self._ph, self._ph // 2, color)


# ---------------- 特效系统 ----------------
class Effects:
    """答对/答错特效管理器

    用透明 Toplevel 作为 overlay,在其 Canvas 上绘制粒子/形状。
    答对三种特效轮流:全屏彩带 / 星星爆发 / 大对勾弹跳
    答错三种特效轮流:题目摇头 / 哭脸气泡 / 红框抖动
    """

    PALETTE_CONFETTI = ["#FF5252", "#FFD740", "#40C4FF", "#69F0AE",
                         "#B388FF", "#FF8A80", "#FFB74D", "#7C4DFF"]
    PALETTE_STAR = ["#FFD700", "#FFEB3B", "#FFA726", "#FFCA28"]

    def __init__(self, game):
        self.game = game
        self.root = game.root
        self._fx_win = None
        self._fx_canvas = None
        self._particles = []
        self._anim_jobs = []
        self._correct_idx = 0
        self._wrong_idx = 0

    # ---------- overlay 管理 ----------
    def _ensure_overlay(self):
        if self._fx_win is None:
            self._fx_win = tk.Toplevel(self.root)
            self._fx_win.wm_overrideredirect(True)
            try:
                self._fx_win.attributes("-transparentcolor", C_TRANSPARENT)
            except Exception:
                pass
            self._fx_win.config(bg=C_TRANSPARENT)
            self._fx_win.attributes("-topmost", True)
            self._fx_canvas = tk.Canvas(
                self._fx_win, bg=C_TRANSPARENT,
                highlightthickness=0, bd=0
            )
            self._fx_canvas.pack(fill="both", expand=True)
        self.root.update_idletasks()
        x = self.root.winfo_rootx()
        y = self.root.winfo_rooty()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        self._fx_win.geometry(f"{w}x{h}+{x}+{y}")
        self._fx_win.deiconify()
        self._fx_win.lift()
        self._fx_canvas.configure(width=w, height=h)
        self._fx_canvas.delete("all")
        return self._fx_canvas, w, h

    def _hide_overlay(self):
        if self._fx_win is not None:
            try:
                self._fx_win.withdraw()
            except Exception:
                pass

    def _cancel_anim(self):
        for j in self._anim_jobs:
            try:
                self.root.after_cancel(j)
            except Exception:
                pass
        self._anim_jobs = []
        self._particles = []

    def _schedule(self, ms, fn):
        j = self.root.after(ms, fn)
        self._anim_jobs.append(j)
        return j

    def _force_hide(self):
        if self._fx_canvas is not None:
            try:
                self._fx_canvas.delete("all")
            except Exception:
                pass
        self._particles = []
        self._hide_overlay()

    def cleanup(self):
        self._cancel_anim()
        if self._fx_win is not None:
            try:
                self._fx_win.destroy()
            except Exception:
                pass
            self._fx_win = None
            self._fx_canvas = None

    def reset(self):
        """新一局重置特效轮换计数"""
        self._correct_idx = 0
        self._wrong_idx = 0
        self._cancel_anim()
        self._hide_overlay()

    # ---------- 触发入口 ----------
    def trigger_correct(self):
        self._cancel_anim()
        kind = self._correct_idx % 3
        self._correct_idx += 1
        if kind == 0:
            self._confetti()
        elif kind == 1:
            self._star_burst()
        else:
            self._big_check()

    def trigger_wrong(self):
        self._cancel_anim()
        kind = self._wrong_idx % 3
        self._wrong_idx += 1
        if kind == 0:
            self._shake_label()
        elif kind == 1:
            self._cry_bubble()
        else:
            self._red_shake_entry()

    # ---------- 答对 A: 全屏彩带 ----------
    def _confetti(self):
        canvas, w, h = self._ensure_overlay()
        particles = []
        for _ in range(90):
            x = random.uniform(0, w)
            y = random.uniform(-30, -3)
            vx = random.uniform(-2.5, 2.5)
            vy = random.uniform(2, 5)
            color = random.choice(self.PALETTE_CONFETTI)
            sw = random.uniform(5, 9)
            sh = sw * random.uniform(1.2, 1.8)
            life = random.randint(80, 140)
            cid = canvas.create_rectangle(
                x, y, x + sw, y + sh, fill=color, outline=""
            )
            particles.append({
                "x": x, "y": y, "vx": vx, "vy": vy,
                "sw": sw, "sh": sh, "life": life, "cid": cid
            })
        self._particles = particles

        def step():
            alive = []
            for p in self._particles:
                p["life"] -= 1
                p["vy"] += 0.18
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                if p["y"] > h + 30 or p["life"] <= 0:
                    try:
                        canvas.delete(p["cid"])
                    except Exception:
                        pass
                    continue
                try:
                    canvas.coords(p["cid"], p["x"], p["y"],
                                  p["x"] + p["sw"], p["y"] + p["sh"])
                except Exception:
                    pass
                alive.append(p)
            self._particles = alive
            if alive:
                self._schedule(20, step)
            else:
                self._schedule(200, self._hide_overlay)

        self._schedule(20, step)
        self._schedule(1800, self._force_hide)

    # ---------- 答对 B: 星星爆发 ----------
    def _star_burst(self):
        canvas, w, h = self._ensure_overlay()
        self.root.update_idletasks()
        try:
            ql = self.game.question_label
            cx = ql.winfo_rootx() - self.root.winfo_rootx() + ql.winfo_width() // 2
            cy = ql.winfo_rooty() - self.root.winfo_rooty() + ql.winfo_height() // 2
        except Exception:
            cx, cy = w // 2, h // 2

        particles = []
        n = 36
        for i in range(n):
            angle = (2 * math.pi) * i / n + random.uniform(-0.1, 0.1)
            speed = random.uniform(3, 7)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            color = random.choice(self.PALETTE_STAR)
            r = random.uniform(4, 8)
            life = random.randint(45, 70)
            cid = canvas.create_text(
                cx, cy, text="★", fill=color,
                font=(FONT_UI, int(r * 3), "bold")
            )
            particles.append({
                "x": float(cx), "y": float(cy), "vx": vx, "vy": vy,
                "life": life, "cid": cid
            })
        self._particles = particles

        def step():
            alive = []
            for p in self._particles:
                p["life"] -= 1
                p["vy"] += 0.08
                p["vx"] *= 0.98
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                if p["life"] <= 0:
                    try:
                        canvas.delete(p["cid"])
                    except Exception:
                        pass
                    continue
                try:
                    canvas.coords(p["cid"], p["x"], p["y"])
                except Exception:
                    pass
                alive.append(p)
            self._particles = alive
            if alive:
                self._schedule(25, step)
            else:
                self._schedule(200, self._hide_overlay)

        self._schedule(25, step)
        self._schedule(1300, self._force_hide)

    # ---------- 答对 C: 大对勾弹跳 ----------
    def _big_check(self):
        canvas, w, h = self._ensure_overlay()
        cx, cy = w // 2, h // 2
        cid = canvas.create_text(
            cx, cy, text="✔", fill=C_GREEN,
            font=(FONT_UI, 30, "bold")
        )
        # 输入框边框变绿
        try:
            self.game.entry.config(
                highlightcolor=C_GREEN, highlightbackground=C_GREEN
            )
        except Exception:
            pass
        # 字号序列模拟弹跳缩放
        sizes = [30, 70, 120, 85, 110, 95, 110]

        def step(i=0):
            if i >= len(sizes):
                try:
                    canvas.delete(cid)
                except Exception:
                    pass
                self._schedule(100, self._restore_entry_border)
                self._schedule(200, self._hide_overlay)
                return
            try:
                canvas.itemconfig(cid, font=(FONT_UI, sizes[i], "bold"))
            except Exception:
                pass
            self._schedule(90, lambda: step(i + 1))

        step(0)

    def _restore_entry_border(self):
        try:
            self.game.entry.config(
                highlightcolor=C_ACCENT,
                highlightbackground=C_PROGRESS_BG
            )
        except Exception:
            pass

    # ---------- 答错 A: 题目摇头(红框套住题目大幅左右晃) ----------
    def _shake_label(self):
        canvas, w, h = self._ensure_overlay()
        self.root.update_idletasks()
        try:
            ql = self.game.question_label
            lx = ql.winfo_rootx() - self.root.winfo_rootx()
            ly = ql.winfo_rooty() - self.root.winfo_rooty()
            lw = ql.winfo_width()
            lh = ql.winfo_height()
        except Exception:
            lx, ly, lw, lh = 50, h // 2 - 30, w - 100, 60

        pad = 16
        cid = canvas.create_rectangle(
            lx - pad, ly - pad, lx + lw + pad, ly + lh + pad,
            outline=C_RED, width=4
        )
        offsets = [0, -18, 0, 16, 0, -12, 0, 10, 0, -6, 0, 4, 0]

        def step(i=0):
            if i >= len(offsets):
                try:
                    canvas.delete(cid)
                except Exception:
                    pass
                self._schedule(150, self._hide_overlay)
                return
            dx = offsets[i]
            try:
                canvas.coords(
                    cid, lx - pad + dx, ly - pad,
                    lx + lw + pad + dx, ly + lh + pad
                )
            except Exception:
                pass
            self._schedule(55, lambda: step(i + 1))

        step(0)

    # ---------- 答错 B: 哭脸气泡 ----------
    def _cry_bubble(self):
        canvas, w, h = self._ensure_overlay()
        self.root.update_idletasks()
        try:
            e = self.game.entry
            ex = e.winfo_rootx() - self.root.winfo_rootx()
            ey = e.winfo_rooty() - self.root.winfo_rooty()
            ew = e.winfo_width()
            eh = e.winfo_height()
        except Exception:
            ex, ey, ew, eh = w // 2 - 40, h // 2 - 20, 80, 30

        cx = ex + ew // 2
        cy = ey - 36
        bw, bh = 84, 42
        bx = cx - bw // 2
        by = cy - bh // 2
        bid = canvas.create_oval(
            bx, by, bx + bw, by + bh,
            fill=C_BUBBLE_BG, outline=C_RED, width=2
        )
        # 气泡尾巴
        tail = canvas.create_polygon(
            cx - 6, by + bh - 2, cx + 6, by + bh - 2, cx, by + bh + 8,
            fill=C_BUBBLE_BG, outline=C_RED, width=2
        )
        tid = canvas.create_text(
            cx, cy, text="T_T", fill=C_RED,
            font=(FONT_UI, 16, "bold")
        )

        def remove():
            try:
                canvas.delete(bid)
                canvas.delete(tail)
                canvas.delete(tid)
            except Exception:
                pass
            self._schedule(50, self._hide_overlay)

        self._schedule(1000, remove)
        self._schedule(1400, self._force_hide)

    # ---------- 答错 C: 输入框变红 + 小抖 ----------
    def _red_shake_entry(self):
        canvas, w, h = self._ensure_overlay()
        self.root.update_idletasks()
        try:
            e = self.game.entry
            ex = e.winfo_rootx() - self.root.winfo_rootx()
            ey = e.winfo_rooty() - self.root.winfo_rooty()
            ew = e.winfo_width()
            eh = e.winfo_height()
        except Exception:
            ex, ey, ew, eh = w // 2 - 50, h // 2 - 15, 100, 30

        # 改 entry 边框红
        try:
            self.game.entry.config(
                highlightcolor=C_RED, highlightbackground=C_RED
            )
        except Exception:
            pass

        pad = 6
        cid = canvas.create_rectangle(
            ex - pad, ey - pad, ex + ew + pad, ey + eh + pad,
            outline=C_RED, width=3
        )
        offsets = [0, -8, 0, 6, 0, -5, 0, 4, 0, -3, 0]

        def step(i=0):
            if i >= len(offsets):
                try:
                    canvas.delete(cid)
                except Exception:
                    pass
                self._schedule(100, self._restore_entry_border)
                self._schedule(200, self._hide_overlay)
                return
            dx = offsets[i]
            try:
                canvas.coords(
                    cid, ex - pad + dx, ey - pad,
                    ex + ew + pad + dx, ey + eh + pad
                )
            except Exception:
                pass
            self._schedule(50, lambda: step(i + 1))

        step(0)


# ---------------- 游戏主体 ----------------
class Game:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("20以内加减法")
        self.root.resizable(False, False)
        self.root.configure(bg=C_BG)
        self._center_window(520, 600)

        # 设置 Combobox 下拉样式
        self.root.option_add("*TCombobox*Listbox*font", (FONT_UI, 11))
        self.root.option_add("*TCombobox*Listbox*selectBackground", C_ACCENT)
        self.root.option_add("*TCombobox*Listbox*selectForeground", "white")
        self.root.option_add("*TCombobox*Listbox*background", C_CARD)
        self.root.option_add("*TCombobox*Listbox*foreground", C_TEXT)

        # 游戏状态
        self.mode_name = DEFAULT_MODE
        self.question_index = 0
        self.score = 0
        self.start_time = 0.0
        self.remaining = float(SECONDS_PER_QUESTION)
        self.timer_job = None
        self.current_answer = 0
        self.current_q_text = ""
        self.game_over = False
        self.wrong_questions = []
        self._awaiting_next = False

        self._build_ui()
        self.fx = Effects(self)
        self._new_round()

    # ---------- 窗口居中 ----------
    def _center_window(self, w: int, h: int):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ---------- 界面构建 ----------
    def _build_ui(self):
        # 顶部:难度选择(左) + 得分(右)
        top = tk.Frame(self.root, bg=C_BG)
        top.pack(fill="x", padx=24, pady=(20, 4))

        self.mode_var = tk.StringVar(value=self.mode_name)
        self.mode_cb = ttk.Combobox(
            top, textvariable=self.mode_var, values=list(MODES.keys()),
            state="readonly", width=14, font=(FONT_UI, 11)
        )
        self.mode_cb.bind("<<ComboboxSelected>>", self._on_mode_change)
        self.mode_cb.pack(side="left")

        self.score_label = tk.Label(
            top, text="得分: 0", bg=C_BG, fg=C_TEXT,
            font=(FONT_UI, 13, "bold")
        )
        self.score_label.pack(side="right")

        # 进度信息行
        info = tk.Frame(self.root, bg=C_BG)
        info.pack(fill="x", padx=24, pady=(8, 2))
        self.progress_label = tk.Label(
            info, text=f"题目 1 / {TOTAL_QUESTIONS}",
            bg=C_BG, fg=C_SUBTEXT, font=(FONT_UI, 11)
        )
        self.progress_label.pack(side="left")
        self.time_label = tk.Label(
            info, text=f"剩余: {SECONDS_PER_QUESTION}s",
            bg=C_BG, fg=C_BLUE, font=(FONT_UI, 12, "bold")
        )
        self.time_label.pack(side="right")

        # 进度条
        pb_wrap = tk.Frame(self.root, bg=C_BG)
        pb_wrap.pack(fill="x", padx=24, pady=(4, 24))
        self.progress_bar = ProgressBar(pb_wrap, width=472, height=12)
        self.progress_bar.pack()

        # 题目(大字号圆润字体)
        self.question_label = tk.Label(
            self.root, text="", bg=C_BG, fg=C_TEXT,
            font=(FONT_NUM, 48, "bold")
        )
        self.question_label.pack(pady=(6, 30))

        # 输入框(无边框,聚焦时彩色高亮边)
        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(
            self.root, textvariable=self.entry_var,
            font=(FONT_NUM, 28), justify="center",
            width=10, bd=8, relief="flat",
            highlightthickness=2,
            highlightbackground=C_PROGRESS_BG,
            highlightcolor=C_ACCENT
        )
        self.entry.pack(pady=(0, 24))
        self.entry.bind("<Return>", lambda _: self._submit())
        self.entry.bind("<KeyPress>", self._on_keypress)
        self.entry.focus_set()

        # 提交按钮(圆角 + hover/pressed)
        self.submit_btn = RoundButton(
            self.root, "提  交", self._submit,
            bg=C_ACCENT, hover_bg=C_ACCENT_HOVER, pressed_bg=C_ACCENT_PRESSED,
            width=200, height=50, radius=25
        )
        self.submit_btn.pack(pady=(0, 20))

        # 反馈区
        self.feedback_label = tk.Label(
            self.root, text="", bg=C_BG, fg=C_TEXT,
            font=(FONT_UI, 15, "bold")
        )
        self.feedback_label.pack()

        # 底部按钮区(结束时显示)
        self.bottom_frame = tk.Frame(self.root, bg=C_BG)
        self.restart_btn = RoundButton(
            self.bottom_frame, "再来一局", self._restart,
            bg=C_GREEN, hover_bg=C_GREEN_HOVER, pressed_bg=C_GREEN_PRESSED,
            width=150, height=46, radius=23
        )
        self.review_btn = RoundButton(
            self.bottom_frame, "查看错题", self._show_wrong,
            bg=C_BLUE, hover_bg=C_BLUE_HOVER, pressed_bg=C_BLUE_PRESSED,
            width=150, height=46, radius=23
        )

    # ---------- 输入过滤 ----------
    def _on_keypress(self, e):
        # 仅允许数字 / 退格 / 删除 / 回车
        if e.keysym in ("Return", "BackSpace", "Delete", "Left", "Right"):
            return
        if not e.char.isdigit():
            return "break"

    # ---------- 难度切换 ----------
    def _on_mode_change(self, _=None):
        new_mode = self.mode_var.get()
        if new_mode == self.mode_name:
            return
        self.mode_name = new_mode
        self._restart()

    # ---------- 题目生成 ----------
    def _gen_question(self):
        cfg = MODES[self.mode_name]
        max_n = cfg["max"]
        t = cfg["type"]
        if t == "any":
            op = random.choice(["+", "-"])
            if op == "+":
                a = random.randint(0, max_n)
                b = random.randint(0, max_n - a)
                ans = a + b
            else:
                a = random.randint(0, max_n)
                b = random.randint(0, a)
                ans = a - b
        elif t == "carry_add":
            # 进位加法:a,b 都是 1..9 且 a+b>=10
            a = random.randint(1, 9)
            b = random.randint(10 - a, 9)
            ans = a + b
            op = "+"
        else:  # borrow_sub
            # 退位减法:十几减一个个位数字,个位不够减
            x = random.randint(1, 8)
            a = 10 + x
            b = random.randint(x + 1, 9)
            ans = a - b
            op = "-"
        return f"{a} {op} {b} = ?", ans

    # ---------- 一局开始 ----------
    def _new_round(self):
        self.question_index = 0
        self.score = 0
        self.wrong_questions = []
        self.game_over = False
        self._awaiting_next = False
        try:
            self.fx.reset()
        except Exception:
            pass
        self.bottom_frame.pack_forget()
        self.restart_btn.pack_forget()
        self.review_btn.pack_forget()
        self.submit_btn.pack(pady=(0, 20))
        self.entry.config(state="normal")
        self._update_score()
        self._next_question()

    # ---------- 出下一题 ----------
    def _next_question(self):
        if self.question_index >= TOTAL_QUESTIONS:
            self._finish()
            return
        self.question_index += 1
        self.progress_label.config(
            text=f"题目 {self.question_index} / {TOTAL_QUESTIONS}"
        )
        self.feedback_label.config(text="", fg=C_TEXT)

        q, ans = self._gen_question()
        self.current_q_text = q
        self.current_answer = ans
        self.question_label.config(text=q)

        self.entry_var.set("")
        self.entry.config(state="normal")
        self.entry.focus_set()  # 自动聚焦

        self.remaining = float(SECONDS_PER_QUESTION)
        self.start_time = time.time()
        self._update_time_label()
        self.time_label.config(fg=C_BLUE)
        self.progress_bar.update_ratio(1.0)
        self._tick()

    # ---------- 倒计时主循环 ----------
    def _tick(self):
        if self.game_over or self._awaiting_next:
            return
        elapsed = time.time() - self.start_time
        left = max(0.0, SECONDS_PER_QUESTION - elapsed)
        self.remaining = left
        ratio = left / SECONDS_PER_QUESTION
        self.progress_bar.update_ratio(ratio, warn=(left <= 5))
        self._update_time_label()
        if left <= 0:
            self._timeout()
            return
        # 少于 5 秒:数字红色闪烁
        if left <= 5:
            cur = self.time_label.cget("fg")
            new = C_BG if cur == C_RED else C_RED
            self.time_label.config(fg=new)
        self.timer_job = self.root.after(150, self._tick)

    def _update_time_label(self):
        self.time_label.config(text=f"剩余: {int(self.remaining)}s")

    def _update_score(self):
        self.score_label.config(text=f"得分: {self.score}")

    def _cancel_timers(self):
        if self.timer_job is not None:
            try:
                self.root.after_cancel(self.timer_job)
            except Exception:
                pass
            self.timer_job = None

    # ---------- 提交答案 ----------
    def _submit(self):
        if self.game_over or self._awaiting_next:
            return
        raw = self.entry_var.get().strip()
        if raw == "":
            self.feedback_label.config(text="请输入答案", fg=C_RED)
            self.entry.focus_set()
            return
        try:
            user_ans = int(raw)
        except ValueError:
            self.feedback_label.config(text="请输入整数", fg=C_RED)
            return

        self._cancel_timers()
        self._awaiting_next = True

        if user_ans == self.current_answer:
            bonus = 0
            if self.remaining > 0:
                bonus = int(round(SCORE_BONUS_MAX * (self.remaining / SECONDS_PER_QUESTION)))
                bonus = max(0, min(SCORE_BONUS_MAX, bonus))
            got = SCORE_CORRECT + bonus
            self.score += got
            self.feedback_label.config(
                text=f"✅  正确!  +{got} 分", fg=C_GREEN
            )
            sound_correct()
            try:
                self.fx.trigger_correct()
            except Exception:
                pass
        else:
            self.feedback_label.config(
                text=f"❌  错误!  正确答案:{self.current_answer}",
                fg=C_RED
            )
            self.wrong_questions.append({
                "q": self.current_q_text,
                "user": user_ans,
                "correct": self.current_answer
            })
            sound_wrong()
            try:
                self.fx.trigger_wrong()
            except Exception:
                pass

        self._update_score()
        self.entry.config(state="disabled")
        self.root.after(1500, self._resume_next)

    def _resume_next(self):
        self._awaiting_next = False
        self._next_question()

    # ---------- 超时 ----------
    def _timeout(self):
        if self.game_over or self._awaiting_next:
            return
        self._cancel_timers()
        self._awaiting_next = True
        self.feedback_label.config(
            text=f"⏰  超时!  正确答案:{self.current_answer}",
            fg=C_RED
        )
        self.wrong_questions.append({
            "q": self.current_q_text,
            "user": None,
            "correct": self.current_answer
        })
        sound_wrong()
        try:
            self.fx.trigger_wrong()
        except Exception:
            pass
        self.entry.config(state="disabled")
        self.root.after(1800, self._resume_next)

    # ---------- 全部完成 ----------
    def _finish(self):
        self.game_over = True
        self._cancel_timers()
        full = TOTAL_QUESTIONS * SCORE_CORRECT
        percent = int(self.score / full * 100) if full else 0
        if percent >= 90:
            comment = "太棒了!"
        elif percent >= 60:
            comment = "不错,继续努力!"
        else:
            comment = "加油,多练习会更好!"

        self.question_label.config(text="练习结束")
        self.feedback_label.config(
            text=f"总分 {self.score} / {full}    {comment}",
            fg=C_TEXT
        )
        self.time_label.config(text="剩余: 0s", fg=C_SUBTEXT)
        self.progress_bar.update_ratio(0)
        self.entry.config(state="disabled")
        self.submit_btn.pack_forget()
        self.bottom_frame.pack(pady=(8, 0))
        self.restart_btn.pack(side="left", padx=10)
        if self.wrong_questions:
            self.review_btn.pack(side="left", padx=10)

    # ---------- 错题回顾 ----------
    def _show_wrong(self):
        if not self.wrong_questions:
            messagebox.showinfo("错题回顾", "本局没有错题,继续保持!")
            return
        win = tk.Toplevel(self.root)
        win.title("错题回顾")
        win.configure(bg=C_BG)
        win.resizable(False, False)

        tk.Label(
            win, text=f"错题回顾  (共 {len(self.wrong_questions)} 题)",
            bg=C_BG, fg=C_TEXT, font=(FONT_UI, 15, "bold")
        ).pack(pady=(18, 12))

        container = tk.Frame(win, bg=C_BG)
        container.pack(padx=22, pady=(0, 14))
        for i, item in enumerate(self.wrong_questions, 1):
            row_bg = C_CARD if i % 2 == 1 else C_ALT
            row = tk.Frame(container, bg=row_bg)
            row.pack(fill="x", ipadx=12, ipady=6)
            tk.Label(
                row, text=f"{i}.  {item['q']}",
                bg=row_bg, fg=C_TEXT, font=(FONT_UI, 13, "bold")
            ).pack(anchor="w")
            user_str = str(item["user"]) if item["user"] is not None else "(未作答)"
            tk.Label(
                row, text=f"      你的答案: {user_str}    正确: {item['correct']}",
                bg=row_bg, fg=C_RED,
                font=(FONT_UI, 11)
            ).pack(anchor="w", pady=(2, 0))

        tk.Button(
            win, text="关 闭", command=win.destroy,
            bg=C_SUBTEXT, fg="white", bd=0,
            font=(FONT_UI, 12, "bold"),
            width=12, height=1, cursor="hand2",
            activebackground="#546E7A", activeforeground="white"
        ).pack(pady=(0, 18))

        win.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w = max(win.winfo_width(), 360)
        h = win.winfo_height()
        win.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        win.transient(self.root)
        win.grab_set()
        win.focus_set()

    # ---------- 再来一局 ----------
    def _restart(self):
        self._new_round()


def main():
    root = tk.Tk()
    game = Game(root)

    def on_closing():
        try:
            game.fx.cleanup()
        except Exception:
            pass
        try:
            root.destroy()
        except Exception:
            pass
        sys.exit(0)

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
