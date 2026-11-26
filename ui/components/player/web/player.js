/* EntertainX player — stream resolution, HLS playback, and failover. */
(function () {
  "use strict";

  var $ = function (id) { return document.getElementById(id); };

  var state = {
    payload: null,
    servers: [],
    serverIndex: 0,
    candidates: [],
    candidateIndex: 0,
    season: 1,
    episode: 1,
    phase: "idle", // idle | resolving | buffering | switching | playing | error
    resolveTimer: 0,
    candidateTimer: 0,
    failToken: 0,
    idleTimer: 0,
    toastTimer: 0,
    dragging: false,
    ccIndex: 0,
    subtitleTracks: [],
    episodeCache: {},
    wired: false,
    settingsOpen: false,
  };

  var bridge = null;
  var hls = null;
  var video = null;
  var lastVolume = 1;
  var iconCache = new Map();
  var iconToken = new WeakMap();

  // ── Icons (Lucide assets served by the local proxy) ───────────────────────
  function loadIcon(name) {
    if (!iconCache.has(name)) {
      iconCache.set(
        name,
        fetch("/icons/" + name + ".svg")
          .then(function (response) { return response.ok ? response.text() : ""; })
          .catch(function () { return ""; })
      );
    }
    return iconCache.get(name);
  }

  function setIcon(element, name) {
    if (!element) return;
    var token = (iconToken.get(element) || 0) + 1;
    iconToken.set(element, token);
    element.dataset.icon = name;
    loadIcon(name).then(function (svg) {
      if (iconToken.get(element) === token && svg) element.innerHTML = svg;
    });
  }

  function hydrateIcons(root) {
    (root || document).querySelectorAll("[data-icon]").forEach(function (element) {
      setIcon(element, element.dataset.icon);
    });
  }

  // ── Small helpers ─────────────────────────────────────────────────────────
  function fmt(seconds) {
    if (!isFinite(seconds) || seconds < 0) return "0:00";
    seconds = Math.floor(seconds);
    var s = seconds % 60;
    var m = Math.floor(seconds / 60) % 60;
    var h = Math.floor(seconds / 3600);
    if (h > 0) {
      return h + ":" + String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0");
    }
    return m + ":" + String(s).padStart(2, "0");
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function currentServer() {
    return state.servers[state.serverIndex] || null;
  }

  function isPanelOpen() {
    return document.body.classList.contains("panel-open");
  }

  function setText(element, text) {
    if (element) element.textContent = text == null ? "" : String(text);
  }

  function showToast(message, duration) {
    var toast = $("toast");
    setText(toast, message);
    toast.classList.add("show");
    clearTimeout(state.toastTimer);
    state.toastTimer = setTimeout(function () {
      toast.classList.remove("show");
    }, duration || 2600);
  }

  function showLoading(message) {
    setText($("loading-text"), message || "Finding a stream\u2026");
    $("loading").hidden = false;
    $("error-state").hidden = true;
    document.body.classList.remove("idle");
  }

  function hideLoading() {
    $("loading").hidden = true;
  }

  function failAll() {
    cleanupPlayback();
    state.phase = "error";
    hideLoading();
    $("error-state").hidden = false;
    document.body.classList.remove("idle");
    setPlayIcon(false);
    if (bridge) bridge.reportPlaybackError("all", "every server failed");
  }

  // ── Playback lifecycle ────────────────────────────────────────────────────
  function cleanupPlayback() {
    state.failToken += 1;
    clearTimeout(state.resolveTimer);
    clearTimeout(state.candidateTimer);
    if (hls) {
      try { hls.destroy(); } catch (error) { /* already gone */ }
      hls = null;
    }
    state.subtitleTracks = [];
    state.ccIndex = 0;
    $("btn-cc").classList.remove("active");
    document.body.classList.remove("has-video");
    if (video) {
      try { video.pause(); } catch (error) { /* no source */ }
      video.removeAttribute("src");
      try { video.load(); } catch (error) { /* ignore */ }
    }
  }

  function startServer(index, options) {
    options = options || {};
    cleanupPlayback();
    if (index >= state.servers.length || index < 0) {
      failAll();
      return;
    }
    var server = state.servers[index];
    state.serverIndex = index;
    state.candidates = [];
    state.candidateIndex = 0;
    state.phase = "resolving";
    syncServerSelects();
    showLoading("Connecting to " + server.name + "\u2026");
    if (options.announce) showToast("Switching to " + server.name + "\u2026");
    if (!bridge) return;
    bridge.requestSource(
      server.id,
      state.payload.type,
      state.payload.tmdbId,
      state.season,
      state.episode
    );
    state.resolveTimer = setTimeout(function () {
      if (state.phase !== "resolving") return;
      console.warn("[player] " + server.name + " timed out while resolving");
      nextServer();
    }, 8000);
  }

  function nextServer() {
    state.phase = "switching";
    cleanupPlayback();
    var next = state.serverIndex + 1;
    if (next < state.servers.length) {
      startServer(next, { announce: true });
    } else {
      failAll();
    }
  }

  function onSourceReady(raw) {
    var data;
    try {
      data = JSON.parse(raw);
    } catch (error) {
      console.error("[player] bad source payload", error);
      return;
    }
    var server = currentServer();
    if (!server || data.serverId !== server.id || state.phase !== "resolving") return;
    clearTimeout(state.resolveTimer);
    state.candidates = Array.isArray(data.candidates) ? data.candidates : [];
    if (!state.candidates.length) {
      nextServer();
      return;
    }
    tryCandidate(0);
  }

  function onSourceFailed(serverId, message) {
    console.warn("[player] resolve failed for", serverId, "-", message);
    var server = currentServer();
    if (!server || serverId !== server.id || state.phase !== "resolving") return;
    clearTimeout(state.resolveTimer);
    nextServer();
  }

  function tryCandidate(index) {
    if (index >= state.candidates.length) {
      nextServer();
      return;
    }
    state.phase = "buffering";
    state.candidateIndex = index;
    var candidate = state.candidates[index];
    var server = currentServer();
    console.info(
      "[player] " + (server ? server.name : "?") + " \u2192 " + candidate.label +
      " (" + candidate.kind + ")"
    );
    showLoading("Starting stream\u2026");
    clearTimeout(state.candidateTimer);
    var token = ++state.failToken;
    state.candidateTimer = setTimeout(function () {
      if (token === state.failToken && state.phase === "buffering") {
        candidateFailed("timed out after 8s");
      }
    }, 8000);

    if (candidate.kind === "mp4" || !window.Hls || !window.Hls.isSupported()) {
      if (candidate.kind !== "mp4" && !window.Hls) {
        console.warn("[player] hls.js unavailable; trying native playback");
      }
      video.src = candidate.url;
      video.play().catch(function (error) {
        console.warn("[player] play() rejected", error);
      });
      return;
    }

    hls = new window.Hls({
      enableWorker: true,
      lowLatencyMode: false,
      backBufferLength: 30,
      maxBufferLength: 30,
      manifestLoadingTimeOut: 8000,
      levelLoadingTimeOut: 8000,
      fragLoadingTimeOut: 12000,
    });
    hls.attachMedia(video);
    hls.on(window.Hls.Events.MEDIA_ATTACHED, function () {
      if (hls) hls.loadSource(candidate.url);
    });
    hls.on(window.Hls.Events.MANIFEST_PARSED, function () {
      video.play().catch(function (error) {
        console.warn("[player] play() rejected", error);
      });
    });
    hls.on(window.Hls.Events.SUBTITLE_TRACKS_UPDATED, function (_event, data) {
      state.subtitleTracks = (data && data.subtitleTracks) || [];
      if (state.subtitleTracks.length) {
        hls.subtitleDisplay = true;
      }
    });
    hls.on(window.Hls.Events.ERROR, function (_event, data) {
      if (!data || !data.fatal) return;
      candidateFailed(data.type + " " + data.details);
    });
  }

  function candidateFailed(reason) {
    if (state.phase !== "buffering") return;
    console.warn("[player] candidate failed:", reason);
    state.phase = "switching";
    var next = state.candidateIndex + 1;
    cleanupPlayback();
    if (next < state.candidates.length) {
      tryCandidate(next);
    } else {
      nextServer();
    }
  }

  function onPlaying() {
    clearTimeout(state.candidateTimer);
    state.phase = "playing";
    document.body.classList.add("has-video");
    hideLoading();
    $("error-state").hidden = true;
    setPlayIcon(true);
    updateProgress();
    wake();
  }

  function togglePlay() {
    if (!video || !video.src) return;
    if (video.paused) {
      video.play().catch(function (error) {
        console.warn("[player] play() rejected", error);
      });
    } else {
      video.pause();
    }
  }

  function seekBy(delta) {
    if (!video || !isFinite(video.duration)) return;
    video.currentTime = clamp(video.currentTime + delta, 0, video.duration);
    updateProgress();
    wake();
  }

  function setPlayIcon(playing) {
    var button = $("btn-play");
    setIcon(button, playing ? "pause" : "play");
    button.setAttribute("aria-label", playing ? "Pause" : "Play");
    button.title = playing ? "Pause" : "Play";
  }

  // ── Progress bar ──────────────────────────────────────────────────────────
  function updateProgress() {
    var duration = video && isFinite(video.duration) ? video.duration : 0;
    var current = video ? video.currentTime : 0;
    var ratio = duration > 0 ? clamp(current / duration, 0, 1) : 0;
    $("played").style.width = (ratio * 100).toFixed(3) + "%";
    $("knob").style.left = (ratio * 100).toFixed(3) + "%";
    setText($("time-cur"), fmt(current));
    setText($("time-dur"), duration > 0 ? fmt(duration) : "0:00");
    $("progress").setAttribute("aria-valuenow", String(Math.round(ratio * 100)));
    $("progress").setAttribute(
      "aria-valuetext",
      fmt(current) + " of " + (duration > 0 ? fmt(duration) : "unknown")
    );
    updateBuffered();
  }

  function updateBuffered() {
    var duration = video && isFinite(video.duration) ? video.duration : 0;
    if (!duration || !video) {
      $("buffered").style.width = "0%";
      return;
    }
    var end = 0;
    for (var i = 0; i < video.buffered.length; i += 1) {
      if (video.buffered.start(i) <= video.currentTime + 0.5) {
        end = Math.max(end, video.buffered.end(i));
      }
    }
    $("buffered").style.width = ((end / duration) * 100).toFixed(3) + "%";
  }

  function seekFromPointer(clientX) {
    if (!video || !isFinite(video.duration) || video.duration <= 0) return;
    var rect = $("progress").getBoundingClientRect();
    var ratio = clamp((clientX - rect.left) / rect.width, 0, 1);
    video.currentTime = ratio * video.duration;
    updateProgress();
  }

  function wireProgress() {
    var progress = $("progress");
    progress.addEventListener("pointerdown", function (event) {
      state.dragging = true;
      progress.setPointerCapture(event.pointerId);
      seekFromPointer(event.clientX);
      wake();
    });
    progress.addEventListener("pointermove", function (event) {
      if (state.dragging) seekFromPointer(event.clientX);
    });
    progress.addEventListener("pointerup", function (event) {
      state.dragging = false;
      try { progress.releasePointerCapture(event.pointerId); } catch (error) { /* ignore */ }
    });
    progress.addEventListener("pointercancel", function () { state.dragging = false; });
    progress.addEventListener("keydown", function (event) {
      if (event.key === "ArrowLeft") { event.preventDefault(); seekBy(-10); }
      if (event.key === "ArrowRight") { event.preventDefault(); seekBy(10); }
      if (event.key === "Home") { event.preventDefault(); video.currentTime = 0; updateProgress(); }
      if (event.key === "End" && isFinite(video.duration)) {
        event.preventDefault();
        video.currentTime = video.duration;
        updateProgress();
      }
    });
  }

  // ── Volume ────────────────────────────────────────────────────────────────
  function updateVolumeUi() {
    var muted = video.muted || video.volume === 0;
    setIcon($("btn-mute"), muted ? "volume-x" : "volume-2");
    $("btn-mute").setAttribute("aria-label", muted ? "Unmute" : "Mute");
    $("btn-mute").title = muted ? "Unmute" : "Mute";
    $("volume").value = muted ? "0" : String(video.volume);
  }

  function toggleMute() {
    if (!video) return;
    video.muted = !video.muted;
    if (!video.muted && video.volume === 0) video.volume = lastVolume || 0.8;
    updateVolumeUi();
  }

  // ── Panel, subtitles, settings ────────────────────────────────────────────
  function setPanel(open) {
    document.body.classList.toggle("panel-open", open);
    $("side-panel").setAttribute("aria-hidden", String(!open));
    $("type-tab").setAttribute("aria-expanded", String(open));
    if (open) closeSettings();
    wake();
  }

  function closeSettings() {
    state.settingsOpen = false;
    $("settings-menu").hidden = true;
  }

  function openSettings() {
    state.settingsOpen = true;
    var menu = $("settings-menu");
    menu.hidden = false;
    var button = $("btn-settings").getBoundingClientRect();
    menu.style.right = Math.max(12, window.innerWidth - button.right) + "px";
    menu.style.bottom = (window.innerHeight - button.top + 10) + "px";
    wake();
  }

  function toggleSettings() {
    if (state.settingsOpen) closeSettings();
    else openSettings();
  }

  function cycleSubtitles() {
    var tracks = state.subtitleTracks || [];
    if (!tracks.length) {
      showToast("No subtitles available for this source.");
      return;
    }
    state.ccIndex = (state.ccIndex + 1) % (tracks.length + 1);
    if (hls) hls.subtitleTrack = state.ccIndex === 0 ? -1 : state.ccIndex - 1;
    $("btn-cc").classList.toggle("active", state.ccIndex > 0);
    if (state.ccIndex === 0) {
      showToast("Subtitles off");
    } else {
      var track = tracks[state.ccIndex - 1] || {};
      showToast("Subtitles: " + (track.name || track.lang || "track " + state.ccIndex));
    }
  }

  async function toggleFullscreen() {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
    } catch (error) {
      console.warn("[player] fullscreen unavailable", error);
      showToast("Fullscreen is not available right now.");
    }
  }

  async function togglePip() {
    if (!video) return;
    try {
      if (document.pictureInPictureElement) await document.exitPictureInPicture();
      else if (document.pictureInPictureEnabled) await video.requestPictureInPicture();
      else showToast("Picture-in-picture is not available.");
    } catch (error) {
      console.warn("[player] picture-in-picture failed", error);
      showToast("Picture-in-picture is not available.");
    }
  }

  function setSpeed(rate) {
    if (video) video.playbackRate = rate;
    document.querySelectorAll("#speed-grid button").forEach(function (button) {
      button.classList.toggle("active", Number(button.dataset.speed) === rate);
    });
  }

  // ── Auto-hide ─────────────────────────────────────────────────────────────
  function wake() {
    document.body.classList.remove("idle");
    clearTimeout(state.idleTimer);
    if (state.phase === "playing" && !isPanelOpen() && !state.settingsOpen) {
      state.idleTimer = setTimeout(function () {
        if (state.phase === "playing" && !isPanelOpen() && !state.settingsOpen) {
          document.body.classList.add("idle");
        }
      }, 3000);
    }
  }

  // ── Episodes ──────────────────────────────────────────────────────────────
  function renderSeasons() {
    var seasons = state.payload.seasons || [];
    var section = $("episodes-section");
    section.hidden = !seasons.length;
    if (!seasons.length) return;
    var select = $("season-select");
    select.replaceChildren();
    seasons.forEach(function (season) {
      var option = document.createElement("option");
      option.value = String(season.number);
      option.textContent = season.name || "Season " + season.number;
      select.append(option);
    });
    select.value = String(state.season);
  }

  function requestEpisodes() {
    if (!bridge || !state.payload || state.payload.type !== "tv") return;
    var season = state.season;
    if (state.episodeCache[season]) {
      renderEpisodes(season);
      return;
    }
    setText($("episode-list"), "Loading episodes\u2026");
    $("episode-list").classList.add("panel-empty");
    bridge.requestEpisodes(season);
  }

  function renderEpisodes(season) {
    var list = $("episode-list");
    var episodes = state.episodeCache[season];
    list.replaceChildren();
    list.classList.remove("panel-empty");
    if (!episodes) {
      setText(list, "Loading episodes\u2026");
      list.classList.add("panel-empty");
      return;
    }
    if (!episodes.length) {
      setText(list, "The episode list is unavailable right now.");
      list.classList.add("panel-empty");
      return;
    }
    episodes.forEach(function (episode) {
      var button = document.createElement("button");
      button.className = "episode" + (episode.number === state.episode ? " active" : "");
      button.type = "button";
      button.dataset.episode = String(episode.number);
      button.setAttribute(
        "aria-label",
        "Play season " + season + " episode " + episode.number + ": " + episode.name
      );

      var number = document.createElement("span");
      number.className = "ep-number";
      number.textContent = "E" + String(episode.number).padStart(2, "0");

      var body = document.createElement("span");
      body.className = "ep-body";
      var name = document.createElement("span");
      name.className = "ep-name";
      name.textContent = episode.name || "Episode " + episode.number;
      var meta = document.createElement("span");
      meta.className = "ep-meta";
      meta.textContent = episode.runtime ? episode.runtime + "m" : (episode.airDate || "");
      body.append(name);
      if (meta.textContent) body.append(meta);

      button.append(number, body);
      button.addEventListener("click", function () {
        selectEpisode(episode.number);
      });
      list.append(button);
    });
  }

  function onEpisodesReady(raw) {
    var data;
    try {
      data = JSON.parse(raw);
    } catch (error) {
      console.error("[player] bad episode payload", error);
      return;
    }
    state.episodeCache[data.season] = Array.isArray(data.episodes) ? data.episodes : [];
    if (data.season === state.season) renderEpisodes(data.season);
  }

  function selectEpisode(number) {
    state.episode = number;
    updateTopTitle();
    renderEpisodes(state.season);
    startServer(state.serverIndex, { announce: false });
  }

  // ── Rendering ─────────────────────────────────────────────────────────────
  function makeChip(text, iconName, className) {
    var chip = document.createElement("span");
    chip.className = "chip" + (className ? " " + className : "");
    if (iconName) {
      var icon = document.createElement("span");
      icon.dataset.icon = iconName;
      chip.append(icon);
    }
    chip.append(document.createTextNode(text));
    hydrateIcons(chip);
    return chip;
  }

  function renderChips(container, compact) {
    var payload = state.payload;
    container.replaceChildren();
    if (payload.certification) container.append(makeChip(payload.certification));
    if (payload.runtime) container.append(makeChip(payload.runtime, "clock"));
    if (payload.rating > 0) {
      container.append(makeChip(payload.rating.toFixed(1), "star", "rating"));
    }
  }

  function updateTopTitle() {
    var payload = state.payload;
    var text = payload.title;
    if (payload.type === "tv") {
      text += "  \u00b7  S" + state.season + " E" + state.episode;
    }
    setText($("top-title"), text);
  }

  function renderServerOptions() {
    ["server-select", "error-server"].forEach(function (id) {
      var select = $(id);
      select.replaceChildren();
      state.servers.forEach(function (server, index) {
        var option = document.createElement("option");
        option.value = String(index);
        option.textContent = server.name + (server.quality ? " \u00b7 " + server.quality : "");
        select.append(option);
      });
    });
    syncServerSelects();
  }

  function syncServerSelects() {
    ["server-select", "error-server"].forEach(function (id) {
      var select = $(id);
      if (select && select.value !== String(state.serverIndex)) {
        select.value = String(state.serverIndex);
      }
    });
  }

  function render() {
    var payload = state.payload;
    document.title = payload.title + " \u00b7 EntertainX";
    setText($("title"), payload.title);
    updateTopTitle();
    renderChips($("chips"), false);
    renderChips($("card-chips"), true);
    setText($("synopsis"), payload.synopsis || "");
    setText($("card-overview"), payload.synopsis || "");
    setText($("card-title"), payload.title);
    setText($("type-text"), payload.type === "tv" ? "TV" : "MOVIE");

    if (payload.tagline) {
      setText($("tagline"), payload.tagline);
      $("tagline").hidden = false;
    }

    var art = payload.backdrop || "";
    $("poster").style.backgroundImage = art ? 'url("' + art.replace(/"/g, "%22") + '")' : "none";
    var cardArt = $("card-art");
    if (art) {
      cardArt.src = art;
      cardArt.alt = payload.title + " artwork";
      cardArt.hidden = false;
    } else {
      cardArt.hidden = true;
    }

    renderServerOptions();
    renderSeasons();
    $("episodes-section").hidden = payload.type !== "tv" || !(payload.seasons || []).length;
  }

  // ── Wiring ────────────────────────────────────────────────────────────────
  function wire() {
    if (state.wired) return;
    state.wired = true;
    video = $("video");

    $("btn-back").addEventListener("click", function () {
      if (bridge) bridge.back();
    });
    $("btn-play").addEventListener("click", togglePlay);
    $("btn-rew").addEventListener("click", function () { seekBy(-10); });
    $("btn-fwd").addEventListener("click", function () { seekBy(10); });
    $("btn-mute").addEventListener("click", toggleMute);
    $("volume").addEventListener("input", function (event) {
      var value = Number(event.target.value);
      if (value > 0) lastVolume = value;
      video.volume = value;
      video.muted = value === 0;
      updateVolumeUi();
    });
    $("btn-cc").addEventListener("click", cycleSubtitles);
    $("btn-panel").addEventListener("click", function () { setPanel(!isPanelOpen()); });
    $("panel-close").addEventListener("click", function () { setPanel(false); });
    $("type-tab").addEventListener("click", function () { setPanel(!isPanelOpen()); });
    $("btn-settings").addEventListener("click", toggleSettings);
    $("btn-pip").addEventListener("click", togglePip);
    $("btn-fs").addEventListener("click", toggleFullscreen);
    $("btn-retry").addEventListener("click", function () {
      startServer(Number($("error-server").value) || 0, { announce: false });
    });

    $("server-select").addEventListener("change", function (event) {
      startServer(Number(event.target.value) || 0, { announce: false });
    });
    $("error-server").addEventListener("change", function (event) {
      syncServerSelects();
      if (event.target.value !== String(state.serverIndex)) {
        $("error-server").value = String(state.serverIndex);
      }
    });

    $("season-select").addEventListener("change", function (event) {
      state.season = Number(event.target.value) || 1;
      state.episode = 1;
      updateTopTitle();
      requestEpisodes();
    });

    var speeds = [0.5, 0.75, 1, 1.25, 1.5, 2];
    var grid = $("speed-grid");
    speeds.forEach(function (rate) {
      var button = document.createElement("button");
      button.type = "button";
      button.dataset.speed = String(rate);
      button.textContent = rate + "\u00d7";
      button.addEventListener("click", function () {
        setSpeed(rate);
        closeSettings();
        showToast("Playback speed " + rate + "\u00d7");
      });
      grid.append(button);
    });
    setSpeed(1);

    wireProgress();

    video.addEventListener("playing", onPlaying);
    video.addEventListener("pause", function () {
      setPlayIcon(false);
      wake();
    });
    video.addEventListener("timeupdate", updateProgress);
    video.addEventListener("progress", updateBuffered);
    video.addEventListener("durationchange", updateProgress);
    video.addEventListener("loadedmetadata", updateProgress);
    video.addEventListener("volumechange", updateVolumeUi);
    video.addEventListener("ended", function () {
      setPlayIcon(false);
      wake();
    });
    video.addEventListener("error", function () {
      if (state.phase === "buffering") candidateFailed("video element error");
    });
    video.addEventListener("click", togglePlay);
    video.addEventListener("dblclick", toggleFullscreen);

    document.addEventListener("mousemove", wake);
    document.addEventListener("pointerdown", wake);
    document.addEventListener("fullscreenchange", function () {
      setIcon($("btn-fs"), document.fullscreenElement ? "minimize" : "maximize");
      wake();
    });

    document.addEventListener("keydown", function (event) {
      var tag = (event.target && event.target.tagName) || "";
      if (tag === "SELECT" || tag === "INPUT" || tag === "TEXTAREA") return;

      switch (event.key) {
        case " ":
        case "k":
        case "K":
          event.preventDefault();
          togglePlay();
          break;
        case "ArrowLeft":
          event.preventDefault();
          seekBy(-10);
          break;
        case "ArrowRight":
          event.preventDefault();
          seekBy(10);
          break;
        case "ArrowUp":
          event.preventDefault();
          video.volume = clamp(video.volume + 0.05, 0, 1);
          video.muted = false;
          updateVolumeUi();
          showToast("Volume " + Math.round(video.volume * 100) + "%", 1200);
          break;
        case "ArrowDown":
          event.preventDefault();
          video.volume = clamp(video.volume - 0.05, 0, 1);
          video.muted = false;
          updateVolumeUi();
          showToast("Volume " + Math.round(video.volume * 100) + "%", 1200);
          break;
        case "f":
        case "F":
          event.preventDefault();
          toggleFullscreen();
          break;
        case "m":
        case "M":
          event.preventDefault();
          toggleMute();
          break;
        case "Escape":
          if (state.settingsOpen) {
            closeSettings();
          } else if (isPanelOpen()) {
            setPanel(false);
          } else if (!document.fullscreenElement && bridge) {
            bridge.back();
          }
          break;
        default:
          break;
      }
    });

    document.addEventListener("click", function (event) {
      if (state.settingsOpen && !event.target.closest("#settings-menu") &&
          !event.target.closest("#btn-settings")) {
        closeSettings();
      }
    });

    window.addEventListener("resize", function () {
      if (state.settingsOpen) closeSettings();
    });
  }

  // ── Init from Python ──────────────────────────────────────────────────────
  function init(payload) {
    if (state.payload) return;
    state.payload = payload;
    state.servers = payload.servers || [];
    state.season = payload.season || 1;
    state.episode = payload.episode || 1;
    wire();
    hydrateIcons();
    render();
    updateVolumeUi();
    setPlayIcon(false);
    if (payload.type === "tv") requestEpisodes();
    startServer(0, { announce: false });
  }

  function connectBridge() {
    if (typeof QWebChannel === "undefined" || !window.qt || !qt.webChannelTransport) {
      console.error("[player] QWebChannel is unavailable");
      setText($("loading-text"), "The player could not start. Please go back and try again.");
      return;
    }
    new QWebChannel(qt.webChannelTransport, function (channel) {
      bridge = channel.objects.bridge;
      if (!bridge) {
        console.error("[player] bridge object missing");
        return;
      }
      bridge.sourceReady.connect(onSourceReady);
      bridge.sourceFailed.connect(onSourceFailed);
      bridge.episodesReady.connect(onEpisodesReady);
      bridge.payload(function (raw) {
        try {
          init(JSON.parse(raw));
        } catch (error) {
          console.error("[player] could not start", error);
          setText($("loading-text"), "The player could not start. Please go back and try again.");
        }
      });
    });
  }

  window.EXPlayer = {
    init: init,
    onSourceReady: onSourceReady,
    onSourceFailed: onSourceFailed,
    onEpisodesReady: onEpisodesReady,
  };

  window.addEventListener("error", function (event) {
    console.error("[player] uncaught", event.message);
  });
  window.addEventListener("unhandledrejection", function (event) {
    console.error("[player] rejected", event.reason);
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", connectBridge);
  } else {
    connectBridge();
  }
})();
