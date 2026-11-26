"""Central audio playback engine and queue manager for EntertainX Music."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from api.tasks import run_async
from ui.components.music.models import LyricLine, Track

if TYPE_CHECKING:
    from api.music import MusicClient

_INSTANCE: AudioEngine | None = None


def get_audio_engine() -> AudioEngine:
    """Return the global AudioEngine singleton instance."""
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = AudioEngine()
    return _INSTANCE


class AudioEngine(QObject):
    """Audio playback manager coordinating QMediaPlayer, queue state, and lyrics."""

    track_changed = Signal(object)  # Track or None
    playback_state_changed = Signal(bool)  # is_playing
    position_changed = Signal(int)  # position_ms
    duration_changed = Signal(int)  # duration_ms
    queue_updated = Signal()
    volume_changed = Signal(float)  # 0.0 to 1.0
    lyrics_loaded = Signal(list)  # list[LyricLine]
    error_occurred = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._player = QMediaPlayer(self)
        self._audio = QAudioOutput(self)
        self._player.setAudioOutput(self._audio)
        self._audio.setVolume(0.85)

        self._queue: list[Track] = []
        self._current_index: int = -1
        self._is_shuffle: bool = False
        self._is_repeat: bool = False
        self._current_lyrics: list[LyricLine] = []
        self._client: MusicClient | None = None

        # Wire Qt multimedia signals
        self._player.playbackStateChanged.connect(self._on_playback_state_changed)
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.mediaStatusChanged.connect(self._on_media_status_changed)
        self._player.errorOccurred.connect(self._on_player_error)

    def set_client(self, client: MusicClient) -> None:
        self._client = client

    # ── State Accessors ─────────────────────────────────────────────────────
    @property
    def current_track(self) -> Track | None:
        if 0 <= self._current_index < len(self._queue):
            return self._queue[self._current_index]
        return None

    @property
    def current_lyrics(self) -> list[LyricLine]:
        return self._current_lyrics

    @property
    def queue(self) -> list[Track]:
        return list(self._queue)

    @property
    def current_index(self) -> int:
        return self._current_index

    @property
    def is_playing(self) -> bool:
        return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    @property
    def position_ms(self) -> int:
        return int(self._player.position())

    @property
    def duration_ms(self) -> int:
        dur = int(self._player.duration())
        if dur > 0:
            return dur
        cur = self.current_track
        return cur.duration_ms if cur else 180_000

    @property
    def volume(self) -> float:
        return float(self._audio.volume())

    @property
    def is_shuffle(self) -> bool:
        return self._is_shuffle

    @property
    def is_repeat(self) -> bool:
        return self._is_repeat

    # ── Playback Controls ───────────────────────────────────────────────────
    def play_track(self, track: Track) -> None:
        """Play a single track immediately, inserting it into the queue if absent."""
        found_idx = -1
        for i, q_track in enumerate(self._queue):
            if q_track.id == track.id:
                found_idx = i
                break

        if found_idx >= 0:
            self._current_index = found_idx
        else:
            if self._current_index >= 0:
                self._queue.insert(self._current_index + 1, track)
                self._current_index += 1
            else:
                self._queue.append(track)
                self._current_index = 0
            self.queue_updated.emit()

        self._start_current_track()

    def play_queue(self, tracks: list[Track], start_index: int = 0) -> None:
        """Replace the queue with a list of tracks and start at start_index."""
        if not tracks:
            return
        self._queue = list(tracks)
        self._current_index = max(0, min(start_index, len(self._queue) - 1))
        self.queue_updated.emit()
        self._start_current_track()

    def add_to_queue(self, track: Track) -> None:
        """Append a track to the end of the upcoming queue."""
        self._queue.append(track)
        self.queue_updated.emit()
        if self._current_index < 0:
            self._current_index = 0
            self._start_current_track()

    def remove_from_queue(self, index: int) -> None:
        """Remove a track by queue index."""
        if 0 <= index < len(self._queue):
            self._queue.pop(index)
            if index < self._current_index:
                self._current_index -= 1
            elif index == self._current_index:
                if self._current_index < len(self._queue):
                    self._start_current_track()
                elif self._queue:
                    self._current_index = 0
                    self._start_current_track()
                else:
                    self.stop()
            self.queue_updated.emit()

    def clear_queue(self) -> None:
        """Clear all queued items and stop playback."""
        self.stop()
        self._queue.clear()
        self._current_index = -1
        self._current_lyrics = []
        self.queue_updated.emit()
        self.track_changed.emit(None)
        self.lyrics_loaded.emit([])

    def _start_current_track(self) -> None:
        track = self.current_track
        if not track or not track.stream_url:
            return

        self._player.stop()
        self._player.setSource(QUrl(track.stream_url))
        self._player.play()
        self.track_changed.emit(track)
        self._fetch_lyrics_for(track)

    def pause(self) -> None:
        self._player.pause()

    def resume(self) -> None:
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
            self._player.play()
        elif self.current_track:
            self._start_current_track()

    def toggle_play_pause(self) -> None:
        if self.is_playing:
            self.pause()
        else:
            self.resume()

    def stop(self) -> None:
        self._player.stop()

    def seek(self, position_ms: int) -> None:
        self._player.setPosition(max(0, position_ms))

    def set_volume(self, vol: float) -> None:
        clamped = max(0.0, min(1.0, float(vol)))
        self._audio.setVolume(clamped)
        self.volume_changed.emit(clamped)

    def toggle_shuffle(self) -> bool:
        self._is_shuffle = not self._is_shuffle
        return self._is_shuffle

    def toggle_repeat(self) -> bool:
        self._is_repeat = not self._is_repeat
        return self._is_repeat

    def next_track(self) -> None:
        """Skip to the next track in the queue."""
        if not self._queue:
            return
        if self._is_repeat and self._current_index >= 0:
            self.seek(0)
            self._player.play()
            return

        if self._is_shuffle and len(self._queue) > 1:
            indices = [i for i in range(len(self._queue)) if i != self._current_index]
            self._current_index = random.choice(indices)
        else:
            if self._current_index + 1 < len(self._queue):
                self._current_index += 1
            else:
                self._current_index = 0  # loop back to start

        self._start_current_track()

    def previous_track(self) -> None:
        """Go to the previous track or restart current track if past 3 seconds."""
        if not self._queue:
            return
        if self._player.position() > 3000:
            self.seek(0)
            return

        if self._current_index > 0:
            self._current_index -= 1
        else:
            self._current_index = len(self._queue) - 1

        self._start_current_track()

    # ── Lyrics Loader ───────────────────────────────────────────────────────
    def _fetch_lyrics_for(self, track: Track) -> None:
        self._current_lyrics = []
        if self._client is None:
            from api.music import MusicClient
            self._client = MusicClient()

        def fetch() -> list[LyricLine]:
            assert self._client is not None
            dur_sec = track.duration_ms // 1000 if track.duration_ms > 0 else None
            return self._client.get_lyrics(track.title, track.artist, dur_sec)

        def on_done(lyrics: list[LyricLine]) -> None:
            # Check if this track is still the currently playing track
            if self.current_track and self.current_track.id == track.id:
                self._current_lyrics = lyrics
                self.lyrics_loaded.emit(lyrics)

        run_async(fetch, on_done=on_done, owner=self)

    # ── Signal Relays ───────────────────────────────────────────────────────
    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        is_playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.playback_state_changed.emit(is_playing)

    def _on_position_changed(self, pos: int) -> None:
        self.position_changed.emit(pos)

    def _on_duration_changed(self, dur: int) -> None:
        self.duration_changed.emit(dur)

    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.next_track()

    def _on_player_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        self.error_occurred.emit(f"Playback error: {error_string}")
