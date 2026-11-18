(() => {
  "use strict";
  if (window.__minaChristmasBrowserEffects) return;
  window.__minaChristmasBrowserEffects = true;

  const DEFAULTS = {
    snow: true,
    edgeSnow: true,
    santa: true,
    snowman: true,
    cursor: true,
    clickSound: false,
    typingSound: false,
    deleteSound: false,
    clickVolume: 0.22,
    typingVolume: 0.16,
    deleteVolume: 0.22,
    reducedMotion: false
  };

  let settings = { ...DEFAULTS };
  let audioContext = null;
  let canvas, ctx, host, sleigh, snowman, frameId = 0;
  let flakes = [];
  let width = 0, height = 0, dpr = 1;
  let lastFrame = 0;
  let lastKeySound = 0;
  let lastSnowmanWave = 0;
  let sleighTimer = 0;
  let isDisposed = false;

  const cursorSvg = '<svg xmlns="http://www.w3.org/2000/svg" width="36" height="42" viewBox="0 0 36 42"><path d="M5 3 L7 34 L15 26 L21 39 L27 36 L20 23 L32 22 Z" fill="#ffffff" stroke="#182638" stroke-width="2" stroke-linejoin="round"/><path d="M7 8 C8 1 14 -1 19 4 L25 10 L17 13 Z" fill="#d92332" stroke="#7f101c" stroke-width="1.5"/><circle cx="7" cy="7" r="4" fill="#fff"/></svg>';
  const cursorUrl = 'url("data:image/svg+xml,' + encodeURIComponent(cursorSvg) + '") 4 3, auto';

  function makeLayer() {
    host = document.createElement("div");
    host.id = "mina-christmas-browser-layer";
    host.style.cssText = "position:fixed!important;inset:0!important;width:100vw!important;height:100vh!important;z-index:2147483647!important;pointer-events:none!important;overflow:hidden!important;contain:strict!important;";
    const shadow = host.attachShadow({ mode: "open" });
    const style = document.createElement("style");
    style.textContent = `
      :host { all: initial; }
      canvas, .sleigh, .snowman { pointer-events:none!important; }
      canvas { position:fixed; inset:0; width:100%; height:100%; }
      .sleigh { position:fixed; top:22px; left:-180px; font:48px/1 "Segoe UI Emoji",sans-serif; white-space:nowrap; opacity:0; filter:drop-shadow(0 2px 7px #75cfff); will-change:transform; }
      .sleigh.go { opacity:1; animation:mina-sleigh-pass 17s linear forwards; }
      @keyframes mina-sleigh-pass { from { transform:translate3d(-180px,0,0) rotate(-3deg); } 35% { transform:translate3d(35vw,20px,0) rotate(1deg); } 70% { transform:translate3d(75vw,-5px,0) rotate(-1deg); } to { transform:translate3d(calc(100vw + 220px),16px,0) rotate(2deg); } }
      .snowman { position:fixed; left:18px; bottom:17px; font:46px/1 "Segoe UI Emoji",sans-serif; opacity:.7; filter:drop-shadow(0 2px 5px #8fd8ff); transform-origin:50% 100%; animation:mina-snowman-bob 3.8s ease-in-out infinite; pointer-events:none; }
      .snowman.wave { animation:mina-snowman-wave .72s ease-in-out 2; }
      @keyframes mina-snowman-bob { 0%,100% { transform:translateY(0) rotate(-2deg); } 50% { transform:translateY(-5px) rotate(2deg); } }
      @keyframes mina-snowman-wave { 0%,100% { transform:rotate(0) translateY(0); } 25% { transform:rotate(-12deg) translateY(-7px); } 75% { transform:rotate(12deg) translateY(-7px); } }
      @media (prefers-reduced-motion: reduce) { .sleigh,.snowman { animation:none!important; } }
    `;
    canvas = document.createElement("canvas");
    canvas.setAttribute("aria-hidden", "true");
    ctx = canvas.getContext("2d", { alpha: true, desynchronized: true });
    sleigh = document.createElement("div");
    sleigh.className = "sleigh";
    sleigh.textContent = "🎅 🛷";
    snowman = document.createElement("div");
    snowman.className = "snowman";
    snowman.textContent = "☃️";
    shadow.append(style, canvas, sleigh, snowman);
    (document.documentElement || document.body).appendChild(host);
    resize();
    scheduleSleigh();
  }

  function resize() {
    if (!canvas) return;
    width = Math.max(1, window.innerWidth);
    height = Math.max(1, window.innerHeight);
    dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const count = settings.reducedMotion ? 20 : Math.max(36, Math.min(95, Math.round(width * height / 17000)));
    flakes = Array.from({ length: count }, () => newFlake(true));
  }

  function newFlake(randomY) {
    return {
      x: Math.random() * width,
      y: randomY ? Math.random() * height : -8,
      r: 1 + Math.random() * 2.6,
      vy: .45 + Math.random() * 1.25,
      vx: -.28 + Math.random() * .56,
      phase: Math.random() * Math.PI * 2,
      alpha: .28 + Math.random() * .55
    };
  }

  function drawEdges(time) {
    if (!settings.edgeSnow) return;
    ctx.save();
    ctx.globalAlpha = .58;
    ctx.fillStyle = "#eaf7ff";
    ctx.beginPath();
    ctx.moveTo(0, 0);
    for (let y = 0; y <= height; y += 40) {
      ctx.lineTo(5 + Math.sin(y * .021 + time * .0003) * 3, y);
    }
    ctx.lineTo(0, height);
    ctx.closePath();
    ctx.fill();
    ctx.beginPath();
    ctx.moveTo(width, 0);
    for (let y = 0; y <= height; y += 40) {
      ctx.lineTo(width - 5 + Math.sin(y * .019 - time * .00025) * 3, y);
    }
    ctx.lineTo(width, height);
    ctx.closePath();
    ctx.fill();
    ctx.globalAlpha = .44;
    ctx.fillRect(0, 0, width, 3);
    ctx.fillRect(0, height - 4, width, 4);
    ctx.restore();
  }

  function animate(time) {
    if (isDisposed) return;
    frameId = requestAnimationFrame(animate);
    if (document.visibilityState !== "visible" || document.fullscreenElement) {
      ctx.clearRect(0, 0, width, height);
      if (sleigh) sleigh.style.display = "none";
      if (snowman) snowman.style.display = "none";
      lastFrame = time;
      return;
    }
    if (time - lastFrame < 28) return;
    lastFrame = time;
    ctx.clearRect(0, 0, width, height);
    if (settings.snow) {
      for (const flake of flakes) {
        flake.phase += .012;
        flake.x += flake.vx + Math.sin(flake.phase) * .28;
        flake.y += flake.vy;
        if (flake.y > height + 5) Object.assign(flake, newFlake(false));
        if (flake.x < -5) flake.x = width + 5;
        if (flake.x > width + 5) flake.x = -5;
        ctx.globalAlpha = flake.alpha;
        ctx.fillStyle = "#ffffff";
        ctx.beginPath();
        ctx.arc(flake.x, flake.y, flake.r, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
      drawEdges(time);
    }
    sleigh.style.display = settings.santa ? "block" : "none";
    snowman.style.display = settings.snowman && settings.snow ? "block" : "none";
    const custom = settings.cursor ? cursorUrl : "auto";
    if (document.documentElement) {
      document.documentElement.style.setProperty("--mina-winter-cursor", custom);
    }
  }

  function scheduleSleigh() {
    clearTimeout(sleighTimer);
    if (!sleigh || !settings.santa || document.visibilityState !== "visible") return;
    sleigh.classList.remove("go");
    void sleigh.offsetWidth;
    sleigh.classList.add("go");
    sleighTimer = window.setTimeout(() => {
      sleigh.classList.remove("go");
      scheduleSleigh();
    }, 52000 + Math.random() * 30000);
  }

  function playSound(kind) {
    const enabled = kind === "click" ? settings.clickSound :
                    kind === "typing" ? settings.typingSound : settings.deleteSound;
    const volumeKey = kind === "click" ? "clickVolume" : kind === "typing" ? "typingVolume" : "deleteVolume";
    const volume = Number(settings[volumeKey] ?? 0.2);
    if (!enabled || volume <= 0) return;
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      if (!audioContext) audioContext = new AudioCtx();
      if (audioContext.state === "suspended") audioContext.resume();
      const now = audioContext.currentTime;
      const oscillator = audioContext.createOscillator();
      const gain = audioContext.createGain();
      const tones = kind === "click" ? [220, 150] :
                    kind === "delete" ? [940, 620] : [1320];
      oscillator.type = kind === "typing" ? "square" : "sine";
      oscillator.frequency.setValueAtTime(tones[0], now);
      if (tones.length > 1) oscillator.frequency.exponentialRampToValueAtTime(tones[1], now + .075);
      gain.gain.setValueAtTime(Math.max(.0001, volume * .16), now);
      gain.gain.exponentialRampToValueAtTime(.0001, now + (kind === "delete" ? .10 : .045));
      oscillator.connect(gain);
      gain.connect(audioContext.destination);
      oscillator.start(now);
      oscillator.stop(now + .11);
    } catch (_) {
      // Audio is an optional decoration; page interaction always continues.
    }
  }

  document.addEventListener("pointerdown", () => playSound("click"), { capture: true, passive: true });
  document.addEventListener("keydown", (event) => {
    // Classify the physical key only. Never inspect input values or record typed text.
    const code = event.code || "";
    const now = performance.now();
    if (code === "Backspace" || code === "Delete") {
      if (now - lastKeySound > 55) playSound("delete");
      lastKeySound = now;
    } else if ((code.startsWith("Key") || code.startsWith("Digit") ||
                code.startsWith("Numpad") || ["Space", "Enter", "Tab", "Minus", "Equal",
                "BracketLeft", "BracketRight", "Backslash", "Semicolon", "Quote",
                "Comma", "Period", "Slash", "Backquote"].includes(code)) &&
                now - lastKeySound > 28) {
      playSound("typing");
      lastKeySound = now;
    }
  }, { capture: true, passive: true });

  document.addEventListener("mousemove", (event) => {
    if (!snowman || snowman.style.display === "none") return;
    const rect = snowman.getBoundingClientRect();
    const near = event.clientX >= rect.left - 12 && event.clientX <= rect.right + 12 &&
                 event.clientY >= rect.top - 12 && event.clientY <= rect.bottom + 12;
    if (near && performance.now() - lastSnowmanWave > 1500) {
      lastSnowmanWave = performance.now();
      snowman.classList.remove("wave");
      void snowman.offsetWidth;
      snowman.classList.add("wave");
    }
  }, { passive: true });

  function applyCursor() {
    if (!document.documentElement) return;
    if (settings.cursor) {
      const css = cursorUrl;
      document.documentElement.style.setProperty("--mina-winter-cursor", css);
      const styleId = "mina-christmas-cursor-style";
      let cursorStyle = document.getElementById(styleId);
      if (!cursorStyle) {
        cursorStyle = document.createElement("style");
        cursorStyle.id = styleId;
        (document.head || document.documentElement).appendChild(cursorStyle);
      }
      cursorStyle.textContent = `
        html, body, body *:not(input):not(textarea):not([contenteditable="true"]) {
          cursor: var(--mina-winter-cursor) !important;
        }
        a, button, [role="button"], input[type="button"], input[type="submit"] {
          cursor: var(--mina-winter-cursor) !important;
        }
      `;
    } else {
      document.documentElement.style.removeProperty("--mina-winter-cursor");
      document.getElementById("mina-christmas-cursor-style")?.remove();
    }
  }

  function update(next) {
    settings = { ...settings, ...next };
    if (host) {
      host.style.display = "block";
      if (!settings.santa) sleigh.classList.remove("go");
      else scheduleSleigh();
      applyCursor();
    }
  }

  makeLayer();
  applyCursor();
  frameId = requestAnimationFrame(animate);

  if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.sync) {
    chrome.storage.sync.get(DEFAULTS, update);
    chrome.storage.onChanged.addListener((changes, area) => {
      if (area !== "sync") return;
      const next = {};
      for (const key of Object.keys(DEFAULTS)) {
        if (changes[key]) next[key] = changes[key].newValue;
      }
      update(next);
    });
  }

  window.addEventListener("resize", resize, { passive: true });
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && settings.santa) scheduleSleigh();
  }, { passive: true });

  window.addEventListener("pagehide", () => {
    isDisposed = true;
    cancelAnimationFrame(frameId);
    clearTimeout(sleighTimer);
    host?.remove();
    document.getElementById("mina-christmas-cursor-style")?.remove();
    document.documentElement?.style.removeProperty("--mina-winter-cursor");
    try { audioContext?.close(); } catch (_) {}
  }, { once: true });
})();