"""Unified in-app trailer playback engine, countdown controller, and viewport seam.

All YouTube key validation, embed HTML/JS presets (``hover``, ``modal``,
``simple``), ``postMessage`` bridging, mute/watchlist state sync, and lazy
``QWebEngineView`` initialization live behind :class:`TrailerPlayer`.
"""

from __future__ import annotations

import html as html_lib
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, Protocol

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from theme import theme_manager as theme

BASE_URL = "https://entertainx.local/"
COUNTDOWN_MS = 600
COUNTDOWN_STEP_MS = 30

PlayerMode = Literal["hover", "modal", "simple"]
_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{6,20}$")

SVG_MUTED = (
    '<svg id="icon-muted" viewBox="0 0 24 24">'
    '<path d="M11 4.702a.705.705 0 0 0-1.203-.498L6.413 7.587A1.4 1.4 0 0 1 5.416 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384A.705.705 0 0 0 11 19.298z"/>'
    '<path d="m16.5 14.5 5-5"/><path d="m16.5 9.5 5 5"/>'
    '</svg>'
)

SVG_SOUND = (
    '<svg id="icon-sound" viewBox="0 0 24 24">'
    '<path d="M11 4.702a.705.705 0 0 0-1.203-.498L6.413 7.587A1.4 1.4 0 0 1 5.416 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384A.705.705 0 0 0 11 19.298z"/>'
    '<path d="M16 9a5 5 0 0 1 0 6"/><path d="M19.364 18.364a9 9 0 0 0 0-12.728"/>'
    '</svg>'
)

SVG_CLOSE = (
    '<svg viewBox="0 0 24 24">'
    '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>'
    '</svg>'
)

SVG_PLUS = (
    '<svg viewBox="0 0 24 24">'
    '<line x1="12" y1="5" x2="12" y2="19"/>'
    '<line x1="5" y1="12" x2="19" y2="12"/>'
    '</svg>'
)

SVG_CHECK = (
    '<svg viewBox="0 0 24 24">'
    '<polyline points="20 6 9 17 4 12"/>'
    '</svg>'
)


@dataclass(frozen=True)
class TrailerSpec:
    """Inputs required to render and start a trailer playback session."""

    key: str
    title: str = ""
    logo_url: str = ""
    backdrop_url: str = ""
    muted: bool = False
    in_watchlist: bool = False
    show_close: bool = False


class ViewportAdapter(Protocol):
    """Seam between :class:`TrailerPlayer` and the underlying web runtime."""

    title_changed: Signal
    load_finished: Signal

    def set_html(self, html: str, base_url: str) -> None: ...
    def clear(self) -> None: ...
    def run_javascript(self, script: str) -> None: ...
    def set_visible(self, visible: bool) -> None: ...
    def set_geometry(self, x: int, y: int, width: int, height: int) -> None: ...
    def widget(self) -> QWidget | None: ...


ViewportFactory = Callable[[QWidget], ViewportAdapter]


class WebEngineViewport(QObject):
    """Production viewport adapter backed lazily by ``QWebEngineView``."""

    title_changed = Signal(str)
    load_finished = Signal(bool)

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        from PySide6.QtWebEngineCore import QWebEngineSettings
        from PySide6.QtWebEngineWidgets import QWebEngineView

        self._view = QWebEngineView(parent)
        self._view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False
        )
        self._view.titleChanged.connect(self.title_changed.emit)
        self._view.loadFinished.connect(self.load_finished.emit)
        self._view.hide()

    def set_html(self, html: str, base_url: str) -> None:
        self._view.setHtml(html, QUrl(base_url))

    def clear(self) -> None:
        self._view.setHtml("")

    def run_javascript(self, script: str) -> None:
        self._view.page().runJavaScript(script)

    def set_visible(self, visible: bool) -> None:
        self._view.setVisible(visible)
        if visible:
            self._view.raise_()

    def set_geometry(self, x: int, y: int, width: int, height: int) -> None:
        self._view.setGeometry(x, y, width, height)

    def widget(self) -> QWidget:
        return self._view


class FakeViewport(QObject):
    """In-memory viewport adapter for deterministic unit tests without Chromium."""

    title_changed = Signal(str)
    load_finished = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.html = ""
        self.base_url = ""
        self.js_calls: list[str] = []
        self.visible = False
        self.geometry = (0, 0, 0, 0)
        self.load_count = 0
        self.clear_count = 0

    def set_html(self, html: str, base_url: str) -> None:
        self.html = html
        self.base_url = base_url
        self.load_count += 1

    def clear(self) -> None:
        self.html = ""
        self.clear_count += 1

    def run_javascript(self, script: str) -> None:
        self.js_calls.append(script)

    def set_visible(self, visible: bool) -> None:
        self.visible = visible

    def set_geometry(self, x: int, y: int, width: int, height: int) -> None:
        self.geometry = (x, y, width, height)

    def widget(self) -> QWidget | None:
        return None

    def emit_title(self, title: str) -> None:
        self.title_changed.emit(title)

    def emit_load_finished(self, ok: bool) -> None:
        self.load_finished.emit(ok)


class CountdownController(QObject):
    """Drives the hover-intent autoplay countdown and reports normalized progress."""

    progressed = Signal(float)
    completed = Signal()

    def __init__(
        self,
        duration_ms: int = COUNTDOWN_MS,
        step_ms: int = COUNTDOWN_STEP_MS,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._duration_ms = max(1, int(duration_ms))
        self._step_ms = max(1, int(step_ms))
        self._active = False
        self._remaining_ms = self._duration_ms
        self._progress = 0.0

        self._timer = QTimer(self)
        self._timer.setInterval(self._step_ms)
        self._timer.timeout.connect(self.tick)

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def progress(self) -> float:
        return self._progress

    def start(self) -> None:
        self._active = True
        self._remaining_ms = self._duration_ms
        self._progress = 0.0
        self._timer.start()
        self.progressed.emit(0.0)

    def stop(self) -> None:
        was_active = self._active or self._progress > 0.0
        self._timer.stop()
        self._active = False
        self._remaining_ms = self._duration_ms
        self._progress = 0.0
        if was_active:
            self.progressed.emit(0.0)

    def tick(self) -> None:
        if not self._active:
            return
        self._remaining_ms -= self._step_ms
        self._progress = min(
            1.0,
            1.0 - max(0, self._remaining_ms) / float(self._duration_ms),
        )
        if self._remaining_ms <= 0:
            self._timer.stop()
            self._active = False
            self._progress = 1.0
            self.progressed.emit(1.0)
            self.completed.emit()
            return
        self.progressed.emit(self._progress)


def is_valid_youtube_key(key: str) -> bool:
    return bool(_KEY_PATTERN.match(key))


def _hex_to_rgb(hex_code: str) -> tuple[int, int, int]:
    h = hex_code.lstrip("#")
    if len(h) == 6:
        try:
            return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        except ValueError:
            pass
    return (24, 24, 24)


def _youtube_embed_url(key: str, *, muted: bool, interactive: bool) -> str:
    if interactive:
        return (
            f"https://www.youtube-nocookie.com/embed/{key}"
            "?autoplay=1&rel=0&modestbranding=1&playsinline=1"
        )
    mute_flag = 1 if muted else 0
    return (
        f"https://www.youtube-nocookie.com/embed/{key}"
        f"?autoplay=1&mute={mute_flag}&enablejsapi=1&origin=https://entertainx.local"
        "&controls=0&color=white&modestbranding=0&rel=0&playsinline=1&loop=1"
        "&disablekb=1&fs=0&iv_load_policy=3&cc_load_policy=0&start=20&vq=hd1080"
    )




def _logo_markup(logo_url: str, title: str, fallback_class: str) -> str:
    safe_title = html_lib.escape(title, quote=True)
    safe_logo = html_lib.escape(logo_url, quote=True) if logo_url else ""
    if safe_logo:
        return (
            f'<img id="logo-img" class="logo-img" src="{safe_logo}" alt="{safe_title}" '
            'onload="onLogoLoaded()" onerror="onLogoFailed()">'
            f'<span id="title-fallback" class="{fallback_class}" style="display:none;">{safe_title}</span>'
        )
    return f'<span id="title-fallback" class="{fallback_class}">{safe_title}</span>'


def _shared_bridge_js(*, start_ring_on_play: bool, loop_on_end: bool) -> str:
    ring_hook = "startCountdownRing();" if start_ring_on_play else ""
    loop_hook = (
        "postPlayerCmd('seekTo', [0, true]); postPlayerCmd('playVideo', []);"
        if loop_on_end
        else "sendAction('ended');"
    )
    return f"""
function onLogoLoaded() {{
  const f = document.getElementById('title-fallback');
  if (f) f.style.display = 'none';
}}
function onLogoFailed() {{
  const img = document.getElementById('logo-img');
  if (img) img.style.display = 'none';
  const f = document.getElementById('title-fallback');
  if (f) f.style.display = 'block';
}}
function postPlayerCmd(func, args = []) {{
  const frame = document.getElementById('yt-player');
  if (frame && frame.contentWindow) {{
    frame.contentWindow.postMessage(JSON.stringify({{
      event: 'command',
      func: func,
      args: args
    }}), '*');
  }}
}}
function sendAction(name) {{
  document.title = 'action:' + name;
  if (window.parent && window.parent !== window) {{
    window.parent.postMessage({{ type: 'entertainx_action', action: name }}, '*');
  }}
}}
window.addEventListener('message', (event) => {{
  let data = event.data;
  if (typeof data === 'string') {{
    try {{ data = JSON.parse(data); }} catch (e) {{ return; }}
  }}
  if (data && (data.event === 'onStateChange' || data.event === 'infoDelivery')) {{
    const state = data.info?.playerState ?? data.info;
    if (state === 1) {{
      const frame = document.getElementById('yt-player');
      if (frame) frame.style.opacity = '1';
      postPlayerCmd('unloadModule', ['captions']);
      postPlayerCmd('unloadModule', ['cc']);
      if (!isMuted) {{
        postPlayerCmd('unMute');
        postPlayerCmd('setVolume', [100]);
      }}
      {ring_hook}
    }} else if (state === 0) {{
      {loop_hook}
    }}
  }}
  if (data && data.event === 'onError') {{
    sendAction('error');
  }}
}});
setInterval(() => {{
  const frame = document.getElementById('yt-player');
  if (frame && frame.contentWindow) {{
    frame.contentWindow.postMessage(JSON.stringify({{ event: 'listening' }}), '*');
  }}
}}, 500);
"""


def _render_simple_html(spec: TrailerSpec) -> str:
    embed_url = _youtube_embed_url(spec.key, muted=False, interactive=True)
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='referrer' content='strict-origin-when-cross-origin'>"
        "<style>html,body{margin:0;height:100%;background:#000;overflow:hidden}"
        "iframe{border:0;width:100%;height:100%}</style></head><body>"
        f"<iframe src='{embed_url}' "
        "referrerpolicy='strict-origin-when-cross-origin' "
        "allow='autoplay; encrypted-media; picture-in-picture; fullscreen' "
        "allowfullscreen></iframe></body></html>"
    )


def _render_hover_html(spec: TrailerSpec) -> str:
    embed_url = _youtube_embed_url(spec.key, muted=spec.muted, interactive=False)
    safe_backdrop = html_lib.escape(spec.backdrop_url, quote=True) if spec.backdrop_url else ""
    backdrop_markup = (
        f'<img id="backdrop" class="backdrop-img" src="{safe_backdrop}" alt="" onerror="this.style.opacity=\'0\';">'
        if safe_backdrop
        else ""
    )
    close_btn_html = (
        f'<button id="close-btn" class="close-btn" title="Close" onclick="sendAction(\'close\')">{SVG_CLOSE}</button>'
        if spec.show_close
        else ""
    )
    logo_markup = _logo_markup(spec.logo_url, spec.title, "title-fallback")

    bg_card = theme.BG_CARD
    r, g, b = _hex_to_rgb(bg_card)
    bg_card_rgb = f"{r}, {g}, {b}"
    primary_color = theme.PRIMARY
    elevated_color = theme.BG_ELEVATED
    initial_audio_svg = SVG_MUTED if spec.muted else SVG_SOUND

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="referrer" content="strict-origin-when-cross-origin">
<title>Trailer Preview</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{
  width: 100%; height: 100%;
  background: {bg_card};
  color: #fff;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  overflow: hidden;
  border-radius: 8px 8px 0 0;
}}
.media-viewport {{
  position: relative; width: 100%; height: 100%;
  background: radial-gradient(circle at 60% 40%, {elevated_color} 0%, {bg_card} 100%);
  overflow: hidden; border-radius: 8px 8px 0 0;
}}
.backdrop-img {{
  position: absolute; inset: 0; width: 100%; height: 100%;
  object-fit: cover; transition: opacity 0.4s ease; z-index: 1;
}}
.iframe-wrapper {{
  position: absolute; inset: 0; width: 100%; height: 100%;
  overflow: hidden; pointer-events: none; z-index: 2;
}}
.iframe-wrapper iframe {{
  position: absolute; inset: 0; width: 100%; height: 100%;
  transform: scale(1.5); transform-origin: center center;
  border: 0; opacity: 0; transition: opacity 0.5s ease-out; pointer-events: none;
}}
.scrim-overlay {{
    position: absolute;
    inset: 0;
    background:
        linear-gradient(
            to top,
            #18181b 0%,
            rgba(24, 24, 27, 0.95) 12%,
            rgba(24, 24, 27, 0.75) 30%,
            rgba(24, 24, 27, 0.35) 52%,
            transparent 85%
        ),
        rgba(24, 24, 27, 0.16);
    pointer-events: none;
    z-index: 3;
}}
.click-shield {{
  position: absolute; inset: 0; z-index: 4; cursor: pointer; pointer-events: auto; background: transparent;
}}
.media-header {{
  position: absolute; top: 12px; left: 14px; right: 14px;
  display: flex; justify-content: space-between; align-items: flex-start; z-index: 6; pointer-events: none;
}}
.logo-box {{ max-width: 180px; max-height: 48px; display: flex; align-items: center; }}
.logo-box img {{ max-width: 100%; max-height: 46px; object-fit: contain; filter: drop-shadow(0 2px 8px rgba(0,0,0,0.95)); }}
.logo-box .title-fallback {{
  font-size: 16px; font-weight: 800; color: #fff; letter-spacing: -0.3px;
  text-shadow: 0 2px 6px rgba(0, 0, 0, 0.95); text-transform: uppercase;
}}
.controls-wrap {{ display: flex; align-items: center; gap: 8px; pointer-events: auto; }}
.audio-btn-wrapper {{ position: relative; width: 34px; height: 34px; pointer-events: auto; }}
.audio-btn-wrapper svg.countdown-ring {{
  position: absolute; inset: 0; width: 34px; height: 34px;
  transform: rotate(-90deg); pointer-events: none; opacity: 0; transition: opacity 0.3s ease;
}}
.audio-btn-wrapper circle.bg-circle {{ stroke: rgba(0, 0, 0, 0.45); stroke-width: 2; fill: none; }}
.audio-btn-wrapper circle.progress-circle {{
  stroke: {primary_color}; stroke-width: 2; stroke-dasharray: 94.2; stroke-dashoffset: 0;
  stroke-linecap: round; fill: none; transition: stroke-dashoffset 0.05s linear;
}}
.audio-btn, .close-btn {{
  border-radius: 50%; background: rgba(18, 18, 22, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.25); color: #fff;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: background 0.2s, transform 0.15s; outline: none;
}}
.audio-btn {{ position: absolute; inset: 2px; width: 30px; height: 30px; }}
.close-btn {{ width: 30px; height: 30px; }}
.audio-btn:hover, .close-btn:hover {{ background: rgba(35, 35, 42, 0.95); transform: scale(1.05); }}
.audio-btn svg, .close-btn svg {{
  width: 15px; height: 15px; fill: none; stroke: currentColor;
  stroke-width: 2; stroke-linecap: round; stroke-linejoin: round;
}}
</style>
</head>
<body>
<div class="media-viewport">
  {backdrop_markup}
  <div class="iframe-wrapper">
    <iframe id="yt-player" src="{embed_url}" allow="autoplay; encrypted-media"></iframe>
  </div>
  <div class="scrim-overlay"></div>
  <div class="click-shield" onclick="sendAction('details')"></div>
  <div class="media-header">
    <div id="logo-container" class="logo-box">{logo_markup}</div>
    <div class="controls-wrap">
      <div class="audio-btn-wrapper">
        <svg id="countdown-svg" class="countdown-ring" viewBox="0 0 34 34">
          <circle class="bg-circle" cx="17" cy="17" r="15"></circle>
          <circle id="ring-progress" class="progress-circle" cx="17" cy="17" r="15"></circle>
        </svg>
        <button id="audio-toggle" class="audio-btn" title="Toggle audio" onclick="handleAudioToggle()">
          {initial_audio_svg}
        </button>
      </div>
      {close_btn_html}
    </div>
  </div>
</div>
<script>
let isMuted = {'true' if spec.muted else 'false'};
let countdownActive = false;
let countdownTimer = null;
const COUNTDOWN_TOTAL_MS = 6000;
let countdownRemainingMs = COUNTDOWN_TOTAL_MS;
const TICK_INTERVAL_MS = 50;
const CIRCLE_CIRCUMFERENCE = 94.2;

const countdownSvg = document.getElementById('countdown-svg');
const ringProgress = document.getElementById('ring-progress');
const audioToggle = document.getElementById('audio-toggle');
const svgMutedStr = `{SVG_MUTED}`;
const svgSoundStr = `{SVG_SOUND}`;

{_shared_bridge_js(start_ring_on_play=True, loop_on_end=True)}

function startCountdownRing() {{
  countdownActive = true;
  countdownRemainingMs = COUNTDOWN_TOTAL_MS;
  if (countdownSvg) countdownSvg.style.opacity = '1';
  updateRingUI();
  countdownTimer = setInterval(() => {{
    countdownRemainingMs -= TICK_INTERVAL_MS;
    if (countdownRemainingMs <= 0) {{
      stopCountdownRing(true);
    }} else {{
      updateRingUI();
    }}
  }}, TICK_INTERVAL_MS);
}}

function updateRingUI() {{
  if (!ringProgress) return;
  const progressRatio = Math.max(0, countdownRemainingMs / COUNTDOWN_TOTAL_MS);
  ringProgress.style.strokeDashoffset = CIRCLE_CIRCUMFERENCE * (1 - progressRatio);
}}

function stopCountdownRing(autoUnmute = false) {{
  if (countdownTimer) {{
    clearInterval(countdownTimer);
    countdownTimer = null;
  }}
  countdownActive = false;
  if (countdownSvg) countdownSvg.style.opacity = '0';
  if (autoUnmute) setMuteState(false, true);
}}

function handleAudioToggle() {{
  if (countdownActive) stopCountdownRing(false);
  setMuteState(!isMuted, true);
}}

function setMuteState(muted, notifyHost = false) {{
  isMuted = !!muted;
  if (isMuted) {{
    postPlayerCmd('mute');
    if (audioToggle) {{
      audioToggle.innerHTML = svgMutedStr;
      audioToggle.setAttribute('title', 'Unmute trailer');
    }}
  }} else {{
    postPlayerCmd('unMute');
    postPlayerCmd('setVolume', [100]);
    if (audioToggle) {{
      audioToggle.innerHTML = svgSoundStr;
      audioToggle.setAttribute('title', 'Mute trailer');
    }}
  }}
  if (notifyHost) sendAction(isMuted ? 'muted' : 'unmuted');
}}

function toggleMute() {{
  handleAudioToggle();
}}
</script>
</body>
</html>"""


def _render_modal_html(spec: TrailerSpec) -> str:
    embed_url = _youtube_embed_url(spec.key, muted=spec.muted, interactive=False)
    logo_markup = _logo_markup(spec.logo_url, spec.title, "logo-text")
    initial_icon = SVG_MUTED if spec.muted else SVG_SOUND
    initial_list_svg = SVG_CHECK if spec.in_watchlist else SVG_PLUS

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="referrer" content="strict-origin-when-cross-origin">
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{
  width: 100%; height: 100%; background: #18181b; overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  border-radius: 16px 16px 0 0;
}}
#modal-player-wrap {{
  position: relative; width: 100%; height: 100%;
  overflow: hidden; pointer-events: none;
  border-radius: 16px 16px 0 0;
  background: radial-gradient(circle at 50% 50%, #252732 0%, #101114 100%);
}}
iframe {{
  position: absolute; top: 50%; left: 50%; width: 100%; height: 180%;
  transform: translate(-50%, -50%) scale(1.35);
  border: 0; opacity: 0; transition: opacity 0.45s ease-out; pointer-events: none;
}}

.modal-scrim {{
    position: absolute;
    inset: 0;
    z-index: 5;
    pointer-events: none;

    /* Cinematic video fade */
    background:
        linear-gradient(
            to top,
            #18181b 0%,
            rgba(24, 24, 27, 0.95) 12%,
            rgba(24, 24, 27, 0.75) 28%,
            rgba(24, 24, 27, 0.35) 48%,
            rgba(24, 24, 27, 0.10) 68%,
            transparent 85%
        ),
        rgba(24, 24, 27, 0.16);
}}

.click-shield {{
  position: absolute; inset: 0; z-index: 8; pointer-events: auto; background: transparent; cursor: default;
}}
.overlay {{ position: absolute; inset: 0; pointer-events: none; z-index: 10; }}
.top-controls {{
  position: absolute; top: 18px; right: 20px; z-index: 12;
  display: flex; align-items: center; gap: 10px; pointer-events: auto;
}}
.bottom-left-panel {{
  position: absolute; bottom: 24px; left: 36px; z-index: 12;
  display: flex; flex-direction: column; gap: 16px; pointer-events: none;
}}
.logo-box {{ max-width: 380px; max-height: 80px; display: flex; align-items: flex-end; }}
.logo-img {{ max-width: 100%; max-height: 80px; object-fit: contain; filter: drop-shadow(0 3px 12px rgba(0,0,0,0.95)); }}
.logo-text {{
  color: #fff; font-size: 28px; font-weight: 800; letter-spacing: -0.5px;
  text-shadow: 0 3px 10px rgba(0, 0, 0, 0.95); line-height: 1.15; text-transform: uppercase;
}}
.action-buttons-row {{ display: flex; align-items: center; gap: 12px; pointer-events: auto; }}
.modal-play-btn {{
  height: 44px; padding: 0 28px; border-radius: 6px;
  background: #ffffff; color: #000000; border: none; font-size: 16px; font-weight: 700;
  display: flex; align-items: center; gap: 10px; cursor: pointer;
  transition: background 0.2s, transform 0.15s; outline: none;
}}
.modal-play-btn:hover {{ background: rgba(255, 255, 255, 0.85); transform: scale(1.03); }}
.modal-play-btn svg {{ width: 18px; height: 18px; fill: currentColor; }}
.modal-circle-btn {{
  width: 44px; height: 44px; border-radius: 50%;
  background: rgba(30, 31, 38, 0.7); border: 1.5px solid rgba(255, 255, 255, 0.35);
  color: #ffffff; display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: background 0.2s, border-color 0.2s, transform 0.15s; outline: none;
}}
.modal-circle-btn:hover {{ background: rgba(45, 47, 56, 0.9); border-color: #ffffff; transform: scale(1.06); }}
.modal-circle-btn svg {{
  width: 20px; height: 20px; fill: none; stroke: currentColor; stroke-width: 2;
  stroke-linecap: round; stroke-linejoin: round;
}}
.bottom-right-panel {{
  position: absolute; bottom: 24px; right: 32px; z-index: 12; display: flex; align-items: center; pointer-events: auto;
}}
</style>
</head>
<body>
<div id="modal-player-wrap">
  <iframe id="yt-player"
    src="{embed_url}"
    referrerpolicy="strict-origin-when-cross-origin"
    allow="autoplay; encrypted-media"
    allowfullscreen></iframe>
  <div class="modal-scrim"></div>
  <div class="click-shield"></div>
</div>
<div class="overlay">
  <div class="top-controls">
    <button class="modal-circle-btn" title="Close" onclick="sendAction('close')">
      {SVG_CLOSE}
    </button>
  </div>
  <div class="bottom-left-panel">
    <div class="logo-box">{logo_markup}</div>
    <div class="action-buttons-row">
      <button class="modal-play-btn" title="Play movie" onclick="sendAction('play')">
        <svg viewBox="0 0 24 24"><polygon points="6 3 20 12 6 21 6 3"/></svg>
        <span>Play</span>
      </button>
      <button id="modal-list-btn" class="modal-circle-btn" title="{'In My List' if spec.in_watchlist else 'Add to My List'}" onclick="toggleWatchlist()">
        {initial_list_svg}
      </button>
    </div>
  </div>
  <div class="bottom-right-panel">
    <button id="mute-btn" class="modal-circle-btn" title="Toggle audio" onclick="toggleMute()">
      {initial_icon}
    </button>
  </div>
</div>
<script>
let isMuted = {'true' if spec.muted else 'false'};
let inWatchlist = {'true' if spec.in_watchlist else 'false'};
const svgMuted = `{SVG_MUTED}`;
const svgSound = `{SVG_SOUND}`;
const svgPlus = `{SVG_PLUS}`;
const svgCheck = `{SVG_CHECK}`;

{_shared_bridge_js(start_ring_on_play=False, loop_on_end=True)}

function setMuteState(muted, notifyHost = false) {{
  isMuted = !!muted;
  postPlayerCmd(isMuted ? 'mute' : 'unMute', []);
  if (!isMuted) postPlayerCmd('setVolume', [100]);
  const btn = document.getElementById('mute-btn');
  if (btn) {{
    btn.innerHTML = isMuted ? svgMuted : svgSound;
    btn.setAttribute('title', isMuted ? 'Unmute' : 'Mute');
  }}
  if (notifyHost) sendAction(isMuted ? 'muted' : 'unmuted');
}}

function toggleMute() {{
  setMuteState(!isMuted, true);
}}

function setWatchlistState(active) {{
  inWatchlist = !!active;
  const btn = document.getElementById('modal-list-btn');
  if (btn) {{
    btn.innerHTML = inWatchlist ? svgCheck : svgPlus;
    btn.setAttribute('title', inWatchlist ? 'In My List' : 'Add to My List');
  }}
}}

function toggleWatchlist() {{
  setWatchlistState(!inWatchlist);
  sendAction('watchlist');
}}
</script>
</body>
</html>"""


def render_trailer_html(mode: PlayerMode, spec: TrailerSpec) -> str:
    """Validate ``spec.key`` and render the HTML document for ``mode``."""
    if not is_valid_youtube_key(spec.key):
        raise ValueError("not a YouTube video id")
    if mode == "simple":
        return _render_simple_html(spec)
    if mode == "hover":
        return _render_hover_html(spec)
    if mode == "modal":
        return _render_modal_html(spec)
    raise ValueError(f"Unknown trailer player mode: {mode!r}")


class TrailerPlayer(QWidget):
    """Unified trailer playback module hiding WebEngine, presets, and action bridging."""

    action_triggered = Signal(str)
    playback_started = Signal()
    playback_stopped = Signal()
    load_finished = Signal(bool)
    load_failed = Signal(str)

    def __init__(
        self,
        mode: PlayerMode = "hover",
        viewport_factory: ViewportFactory | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._mode: PlayerMode = mode
        self._is_playing = False
        self._muted = False
        self._in_watchlist = False
        self._unavailable_reason = ""
        self._viewport: ViewportAdapter | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        factory = viewport_factory or WebEngineViewport
        try:
            self._viewport = factory(self)
        except ImportError:
            self._unavailable_reason = "Trailer playback needs PySide6-WebEngine."
        else:
            widget = self._viewport.widget()
            if widget is not None:
                layout.addWidget(widget)
            self._viewport.title_changed.connect(self._on_title_changed)
            self._viewport.load_finished.connect(self.load_finished.emit)

    @property
    def available(self) -> bool:
        return self._viewport is not None

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def is_muted(self) -> bool:
        return self._muted

    @property
    def viewport(self) -> ViewportAdapter | None:
        return self._viewport

    def load(self, spec: TrailerSpec) -> bool:
        """Validate ``spec``, render its preset HTML, and start playback."""
        if not is_valid_youtube_key(spec.key):
            self._is_playing = False
            self.load_failed.emit("This trailer link is not valid.")
            return False
        if self._viewport is None:
            self._is_playing = False
            self.load_failed.emit(
                self._unavailable_reason or "Trailer playback needs PySide6-WebEngine."
            )
            return False

        html = render_trailer_html(self._mode, spec)
        self._muted = spec.muted
        self._in_watchlist = spec.in_watchlist
        if self.width() > 0 and self.height() > 0:
            self._viewport.set_geometry(0, 0, self.width(), self.height())
        self._viewport.set_html(html, BASE_URL)
        self._viewport.set_visible(True)
        self._is_playing = True
        self.show()
        self.raise_()
        self.playback_started.emit()
        return True

    def stop(self) -> None:
        """Tear down active trailer playback and hide the viewport."""
        was_playing = self._is_playing
        self._is_playing = False
        if self._viewport is not None:
            self._viewport.clear()
            self._viewport.set_visible(False)
        self.hide()
        if was_playing:
            self.playback_stopped.emit()

    def set_muted(self, muted: bool) -> None:
        self._muted = bool(muted)
        if self._is_playing and self._viewport is not None:
            flag = "true" if self._muted else "false"
            self._viewport.run_javascript(
                f"if (typeof setMuteState === 'function') setMuteState({flag}, false);"
            )

    def toggle_mute(self) -> bool:
        self.set_muted(not self._muted)
        return self._muted

    def set_watchlist_state(self, in_watchlist: bool) -> None:
        self._in_watchlist = bool(in_watchlist)
        if self._is_playing and self._viewport is not None:
            flag = "true" if self._in_watchlist else "false"
            self._viewport.run_javascript(
                f"if (typeof setWatchlistState === 'function') setWatchlistState({flag});"
            )

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self._viewport is not None:
            self._viewport.set_geometry(0, 0, event.size().width(), event.size().height())

    def _on_title_changed(self, title: str) -> None:
        if not title.startswith("action:"):
            return
        action = title[len("action:") :].strip()
        if action in ("error", "ended"):
            self.stop()
            if action == "error":
                self.load_failed.emit(
                    "The trailer could not be loaded. Check your connection."
                )
            return
        if action == "muted":
            self._muted = True
        elif action == "unmuted":
            self._muted = False
        self.action_triggered.emit(action)
