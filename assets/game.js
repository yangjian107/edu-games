/* ============ 儿童启蒙小游戏 - 共享游戏框架 ============ */
/* 所有变量封装在 IIFE 中,不污染全局作用域 */
(function() {
"use strict";

// ---- 工具函数 ----
const $ = (id) => document.getElementById(id);
function randInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}
function randFloat(min, max) {
  return Math.random() * (max - min) + min;
}

// ---- 共享配色 ----
const THEME = {
  confetti: ["#FF5252", "#FFD740", "#40C4FF", "#69F0AE",
             "#B388FF", "#FF8A80", "#FFB74D", "#7C4DFF"],
  star: ["#FFD700", "#FFEB3B", "#FFA726", "#FFCA28"],
  green: "#4CAF50",
  red: "#F44336",
  blue: "#5C6BC0",
  orange: "#FF8C42",
  bg: "#FFF8E7",
};

// ---- 音效系统 ----
const AudioSystem = {
  ctx: null,
  ensure() {
    if (!this.ctx) {
      try { this.ctx = new (window.AudioContext || window.webkitAudioContext)(); }
      catch (e) { this.ctx = null; }
    }
    if (this.ctx && this.ctx.state === "suspended") {
      this.ctx.resume().catch(() => {});
    }
  },
  beep(freq, duration) {
    if (!this.ctx) return;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = "sine";
    osc.frequency.value = freq;
    gain.gain.value = 0.18;
    osc.connect(gain);
    gain.connect(this.ctx.destination);
    const now = this.ctx.currentTime;
    gain.gain.setValueAtTime(0.18, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + duration / 1000);
    osc.start(now);
    osc.stop(now + duration / 1000);
  },
  correct() {
    this.ensure();
    this.beep(880, 100);
    setTimeout(() => this.beep(1175, 120), 100);
  },
  wrong() {
    this.ensure();
    this.beep(330, 150);
    setTimeout(() => this.beep(247, 200), 170);
  },
  click() {
    this.ensure();
    this.beep(600, 60);
  },
};

// ---- 特效系统 ----
const FxSystem = {
  canvas: null,
  ctx: null,
  rafId: null,
  particles: [],
  correctIdx: 0,
  wrongIdx: 0,
  bubbleSlot: null,
  checkSlot: null,
  questionEl: null,
  answerEl: null,
  _gameOver: false,

  init(questionEl, answerEl) {
    this.questionEl = questionEl;
    this.answerEl = answerEl;
    this.bubbleSlot = document.createElement("div");
    this.bubbleSlot.style.cssText = "position:fixed;inset:0;pointer-events:none;z-index:950;";
    document.body.appendChild(this.bubbleSlot);
    this.checkSlot = document.createElement("div");
    this.checkSlot.style.cssText = "position:fixed;inset:0;pointer-events:none;z-index:950;";
    document.body.appendChild(this.checkSlot);
  },

  _ensureCanvas() {
    if (!this.canvas) {
      this.canvas = document.createElement("canvas");
      this.canvas.id = "fxCanvas";
      this.canvas.style.cssText = "position:fixed;inset:0;width:100vw;height:100vh;pointer-events:none;z-index:900;display:none;";
      document.body.appendChild(this.canvas);
      this.ctx = this.canvas.getContext("2d");
    }
    this.canvas.width = window.innerWidth;
    this.canvas.height = window.innerHeight;
    this.canvas.style.display = "block";
  },

  _clearCanvas() {
    this.particles = [];
    if (this.rafId) { cancelAnimationFrame(this.rafId); this.rafId = null; }
    if (this.canvas && this.ctx) {
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      this.canvas.style.display = "none";
    }
  },

  clearAll() {
    this._clearCanvas();
    if (this.bubbleSlot) this.bubbleSlot.innerHTML = "";
    if (this.checkSlot) this.checkSlot.innerHTML = "";
    if (this.questionEl) this.questionEl.classList.remove("shake");
    if (this.answerEl) {
      this.answerEl.classList.remove("shake-small", "green", "red");
    }
  },

  resetIdx() {
    this.correctIdx = 0;
    this.wrongIdx = 0;
    this.clearAll();
  },

  triggerCorrect() {
    this.clearAll();
    const kind = this.correctIdx % 3;
    this.correctIdx++;
    if (kind === 0) this._confetti();
    else if (kind === 1) this._starBurst();
    else this._bigCheck();
  },

  triggerWrong() {
    this.clearAll();
    const kind = this.wrongIdx % 3;
    this.wrongIdx++;
    if (kind === 0) this._shakeQuestion();
    else if (kind === 1) this._cryBubble();
    else this._redShakeEntry();
  },

  // --- 答对 A: 全屏彩带 ---
  _confetti() {
    this._ensureCanvas();
    const w = this.canvas.width, h = this.canvas.height;
    this.particles = [];
    for (let i = 0; i < 90; i++) {
      const sw = randFloat(5, 9);
      const sh = sw * randFloat(1.2, 1.8);
      this.particles.push({
        x: Math.random() * w,
        y: -Math.random() * 30 - 3,
        vx: randFloat(-2.5, 2.5),
        vy: randFloat(2, 5),
        sw, sh,
        color: THEME.confetti[Math.floor(Math.random() * THEME.confetti.length)],
        life: randInt(80, 140),
      });
    }
    const maxFrames = 1800 / 20;
    let frame = 0;
    const self = this;
    function step() {
      self.ctx.clearRect(0, 0, w, h);
      self.particles = self.particles.filter(p => {
        p.life--;
        p.vy += 0.18;
        p.x += p.vx;
        p.y += p.vy;
        if (p.y > h + 30 || p.life <= 0) return false;
        self.ctx.fillStyle = p.color;
        self.ctx.fillRect(p.x, p.y, p.sw, p.sh);
        return true;
      });
      frame++;
      if (self.particles.length > 0 && frame < maxFrames) {
        self.rafId = requestAnimationFrame(step);
      } else {
        self._clearCanvas();
      }
    }
    this.rafId = requestAnimationFrame(step);
  },

  // --- 答对 B: 星星爆发 ---
  _starBurst() {
    this._ensureCanvas();
    const w = this.canvas.width, h = this.canvas.height;
    let cx = w / 2, cy = h / 2;
    if (this.questionEl) {
      const rect = this.questionEl.getBoundingClientRect();
      cx = rect.left + rect.width / 2;
      cy = rect.top + rect.height / 2;
    }
    this.particles = [];
    const n = 36;
    for (let i = 0; i < n; i++) {
      const angle = (2 * Math.PI * i / n) + randFloat(-0.1, 0.1);
      const speed = randFloat(3, 7);
      this.particles.push({
        x: cx, y: cy,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        color: THEME.star[Math.floor(Math.random() * THEME.star.length)],
        size: randFloat(12, 22),
        life: randInt(45, 70),
      });
    }
    const maxFrames = 1300 / 16;
    let frame = 0;
    const self = this;
    function step() {
      self.ctx.clearRect(0, 0, w, h);
      self.particles = self.particles.filter(p => {
        p.life--;
        p.vy += 0.08;
        p.vx *= 0.98;
        p.x += p.vx;
        p.y += p.vy;
        if (p.life <= 0) return false;
        self.ctx.font = `bold ${p.size}px "Microsoft YaHei UI", sans-serif`;
        self.ctx.fillStyle = p.color;
        self.ctx.textAlign = "center";
        self.ctx.textBaseline = "middle";
        self.ctx.fillText("★", p.x, p.y);
        return true;
      });
      frame++;
      if (self.particles.length > 0 && frame < maxFrames) {
        self.rafId = requestAnimationFrame(step);
      } else {
        self._clearCanvas();
      }
    }
    this.rafId = requestAnimationFrame(step);
  },

  // --- 答对 C: 大对勾弹跳 ---
  _bigCheck() {
    if (this.answerEl) this.answerEl.classList.add("green");
    const el = document.createElement("div");
    el.className = "big-check";
    el.textContent = "✔";
    this.checkSlot.appendChild(el);
    const self = this;
    setTimeout(() => {
      el.remove();
      if (self.answerEl && !self._gameOver) {
        self.answerEl.classList.remove("green");
      }
    }, 800);
  },

  setGameOver(v) { this._gameOver = v; },

  // --- 答错 A: 题目摇头 ---
  _shakeQuestion() {
    if (this.questionEl) {
      this.questionEl.classList.add("shake");
      setTimeout(() => this.questionEl.classList.remove("shake"), 600);
    }
  },

  // --- 答错 B: 哭脸气泡 ---
  _cryBubble() {
    if (!this.answerEl) return;
    const rect = this.answerEl.getBoundingClientRect();
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = "T_T";
    bubble.style.left = (rect.left + rect.width / 2) + "px";
    bubble.style.top = (rect.top - 8) + "px";
    this.bubbleSlot.appendChild(bubble);
    setTimeout(() => bubble.remove(), 1000);
  },

  // --- 答错 C: 输入框变红 + 抖动 ---
  _redShakeEntry() {
    if (!this.answerEl) return;
    this.answerEl.classList.add("red");
    this.answerEl.classList.add("shake-small");
    const self = this;
    setTimeout(() => {
      self.answerEl.classList.remove("shake-small");
      if (!self._gameOver) self.answerEl.classList.remove("red");
    }, 600);
  },
};

// ---- 计时器/进度条 ----
const TimerSystem = {
  timerId: null,
  onTick: null,
  onTimeout: null,
  duration: 15,
  remaining: 15,
  running: false,
  paused: false,
  _startTime: 0,

  start(duration, onTick, onTimeout) {
    this.duration = duration;
    this.remaining = duration;
    this.onTick = onTick;
    this.onTimeout = onTimeout;
    this.running = true;
    this.paused = false;
    this._startTime = Date.now();
    this._tick();
  },

  pause() {
    if (this.running && !this.paused) {
      this.paused = true;
      if (this.timerId) { clearTimeout(this.timerId); this.timerId = null; }
    }
  },

  resume() {
    if (this.running && this.paused) {
      this.paused = false;
      this._startTime = Date.now() - (this.duration - this.remaining) * 1000;
      this._tick();
    }
  },

  stop() {
    this.running = false;
    this.paused = false;
    if (this.timerId) { clearTimeout(this.timerId); this.timerId = null; }
  },

  _tick() {
    if (!this.running || this.paused) return;
    const elapsed = (Date.now() - this._startTime) / 1000;
    const left = Math.max(0, this.duration - elapsed);
    this.remaining = left;
    if (this.onTick) this.onTick(left);
    if (left <= 0) {
      this.running = false;
      if (this.onTimeout) this.onTimeout();
      return;
    }
    this.timerId = setTimeout(() => this._tick(), 150);
  },
};

// ---- 错题弹窗 ----
const ModalSystem = {
  mask: null,
  titleEl: null,
  listEl: null,

  init(mask, titleEl, listEl, closeBtn) {
    this.mask = mask;
    this.titleEl = titleEl;
    this.listEl = listEl;
    if (closeBtn) closeBtn.addEventListener("click", () => this.hide());
    if (mask) mask.addEventListener("click", (e) => {
      if (e.target === mask) this.hide();
    });
  },

  showWrong(wrongList, emptyMsg) {
    emptyMsg = emptyMsg || "本局没有错题,继续保持!";
    if (!wrongList || wrongList.length === 0) {
      alert(emptyMsg);
      return;
    }
    if (!this.mask) return;
    this.titleEl.textContent = "错题回顾  (共 " + wrongList.length + " 题)";
    this.listEl.innerHTML = "";
    wrongList.forEach((item, i) => {
      const div = document.createElement("div");
      div.className = "modal-item";
      const userStr = item.user === null ? "(未作答)" : String(item.user);
      const qText = item.q || item.question || "";
      div.innerHTML =
        '<div class="modal-item-q">' + (i + 1) + '.  ' + qText + '</div>' +
        '<div class="modal-item-a">你的答案: ' + userStr + '    正确: ' + item.correct + '</div>';
      this.listEl.appendChild(div);
    });
    this.mask.classList.add("show");
  },

  hide() {
    if (this.mask) this.mask.classList.remove("show");
  },
};

// ---- 事件绑定(全局) ----
function bindGlobalEvents() {
  // 首次交互解锁音频
  document.addEventListener("click", () => AudioSystem.ensure(), { once: false });
  document.addEventListener("touchstart", () => AudioSystem.ensure(), { passive: true });
  // 阻止移动端双指缩放
  document.addEventListener("gesturestart", (e) => e.preventDefault());
}

// 导出到 window
window.GameLib = {
  $: $,
  randInt: randInt,
  randFloat: randFloat,
  THEME: THEME,
  AudioSystem: AudioSystem,
  FxSystem: FxSystem,
  TimerSystem: TimerSystem,
  ModalSystem: ModalSystem,
  bindGlobalEvents: bindGlobalEvents,
};

})();
