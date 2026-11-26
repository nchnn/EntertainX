# Music Streaming Providers and Reverse Engineering Specification

This document details how to resolve, decrypt, and stream music sources reverse-engineered from Auris and BitChord. It covers lossless FLAC streaming, high-bitrate AAC CDN resolution via DES decryption, community proxy instances, YouTube Music fallback, and synchronized lyrics resolution (syllable-level, line-level, and plain text).

---

## 1. Request Guardrails and Anti-Bot Bypass

Public and reverse-engineered music APIs enforce bot prevention and rate limits. The following rules are required for all requests:

### Cloudflare Bot Protection (Monochrome / Lucida / Tidal Instances)
- **Trigger**: Default HTTP client headers (e.g. Python `urllib/3.x`, `requests/2.x`, Go `net/http`).
- **Action**: Responds with `HTTP 403 Forbidden` or `HTTP 503 Service Unavailable`.
- **Bypass**: Always provide a browser-grade or mobile application `User-Agent` header:
  `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36`

### JioSaavn Geo-Restricted CDN Filtering
- **Trigger**: Requests arriving from non-Indian IP ranges for regional licenses.
- **Action**: Returns empty results or downgrades CDN stream bitrates to 48/96 kbps.
- **Bypass**: Inject Indian gateway IP headers and adult/explicit content cookies:
  ```http
  X-Forwarded-For: 49.36.0.1
  X-Real-IP: 49.36.0.1
  Cookie: explicit_content=1
  ```

---

## 2. Music Source Hierarchy and Resolution Ladder

Auris organizes sources into a strict resolution ladder to ensure bit-perfect audio when available, falling back smoothly when instances are down or unindexed:

```
[Search Query / Track Metadata]
               │
               ▼
   [Tier 1: Hi-Res Lossless FLAC] ──(24-bit / 44.1-96 kHz direct stream)
               │ (if missed or down)
               ▼
   [Tier 2: Tidal Hi-Fi Instances] ──(16-bit / 44.1 kHz FLAC via community pools)
               │ (if missed or down)
               ▼
   [Tier 3: JioSaavn Direct CDN] ──(320 kbps AAC via DES-decrypted URLs)
               │ (if missed or disabled)
               ▼
   [Tier 4: YouTube Music Fallback] ──(160 kbps Opus / 256 kbps AAC)
```

---

## 3. Direct Hi-Res Lossless FLAC (Monochrome Tracks Protocol)

Direct FLAC streaming without authentication, accounts, or manifest tokens.

### Endpoints
- **Search**: `GET https://tracks.monochrome.st/search/tracks?q={query}&limit={limit}`
- **Stream**: `GET https://tracks.monochrome.st/track/{id}`
- **Required Header**: `User-Agent: Mozilla/5.0 ...`

### Search Response Payload
```json
{
  "tracks": [
    {
      "id": "154014286732070912",
      "title": "Blinding Lights",
      "artistNames": ["The Weeknd"],
      "albumTitle": "After Hours",
      "duration": 200040,
      "artwork": "https://resources.tidal.com/images/...",
      "explicit": false,
      "playable": true
    }
  ]
}
```

### Stream Characteristics
- **Content-Type**: `application/octet-stream`
- **File Format**: Native FLAC starting with 4-byte magic marker `fLaC` (`0x66 0x4C 0x61 0x43`).
- **HTTP 206 Seeking**: Fully supports `Range: bytes=start-end`. Audio players can seek instantly without buffering the entire file.
- **Audio Specs**: 24-bit or 16-bit PCM, 44.1 kHz to 96 kHz Stereo, typically 900 kbps to 1700 kbps true bitrate.

### Fake FLAC Detection
To prevent lossy audio packaged in a FLAC container from playing as lossless:
$$\text{Calculated Bitrate (kbps)} = \frac{\text{Content-Length (bytes)} \times 8}{\text{Duration (seconds)} \times 1000}$$
If the calculated bitrate is under 300 kbps for a track over 60 seconds, reject the stream and drop to the next provider.

### Python Implementation
```python
import json
import urllib.request

MONOCHROME_BASE = "https://tracks.monochrome.st"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
}

def search_monochrome(query: str, limit: int = 10) -> list[dict]:
    query_encoded = urllib.parse.quote(query)
    url = f"{MONOCHROME_BASE}/search/tracks?q={query_encoded}&limit={limit}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    
    results = []
    for t in data.get("tracks", []):
        if not t.get("playable", True) or not t.get("id"):
            continue
        results.append({
            "id": str(t["id"]),
            "title": t.get("title", "Unknown"),
            "artist": ", ".join(t.get("artistNames", [])) or "Unknown Artist",
            "album": t.get("albumTitle") or t.get("releaseTitle"),
            "duration_sec": (t.get("duration", 0) + 500) // 1000 if t.get("duration", 0) > 10000 else t.get("duration", 0),
            "artwork_url": t.get("artwork"),
            "stream_url": f"{MONOCHROME_BASE}/track/{t['id']}",
            "quality": "LOSSLESS"
        })
    return results
```

---

## 4. Tidal Hi-Fi Community Instances

Tidal Hi-Fi community proxy instances act as relays to Tidal's catalog and CDNs without exposing user credentials.

### Remote Instance Registry
Instances rot as upstream rate limits shift. Auris fetches a dynamic instance list from:
`https://raw.githubusercontent.com/OreoMuncher45/BitChord/main/tidal-instances.json`

### Bundled Fallback Pool
1. `https://tracks.monochrome.st` (Tracks protocol, direct FLAC)
2. `https://api.monochrome.tf` (Hi-Fi v2 protocol)
3. `https://wolf.qqdl.site` (Lucida / QQDL)
4. `https://maus.qqdl.site` (Lucida / QQDL)
5. `https://vogel.qqdl.site` (Lucida / QQDL)
6. `https://katze.qqdl.site` (Lucida / QQDL)
7. `https://hund.qqdl.site` (Lucida / QQDL)
8. `https://tidal.kinoplus.online` (Kinoplus)

### Protocol Variations

#### Protocol A: Tracks Protocol (Modern)
- **Search**: `GET {base}/search/tracks?q={query}&limit={limit}`
- **Stream**: `GET {base}/track/{id}` (Path IS the audio stream).

#### Protocol B: Hi-Fi v2 / Binimum Protocol (Legacy)
- **Search**: `GET {base}/search/?s={query}&limit={limit}`
- **Stream Request**: `GET {base}/track/?id={id}&quality=LOSSLESS`
- **Response**:
  ```json
  {
    "data": {
      "audioQuality": "LOSSLESS",
      "manifest": "<Base64 encoded JSON>"
    }
  }
  ```
- **Manifest Decoding**:
  Decoded Base64 string contains:
  ```json
  {
    "mimeType": "audio/flac",
    "codecs": "flac",
    "encryptionType": "NONE",
    "urls": [
      "https://sp-pr-cf.audio.tidal.com/media/..."
    ]
  }
  ```
  Extract `urls[0]` to stream directly from Tidal's Cloudflare/Fastly CDN edge.

---

## 5. JioSaavn Direct 320 kbps Streaming (DES Decrypted)

JioSaavn hosts standard and high-bitrate AAC music files accessible through a reversed internal endpoint.

### Endpoints and Parameters
- **Base URL**: `https://www.jiosaavn.com/api.php`
- **Search Call**:
  - `__call`: `search.getResults`
  - `_format`: `json`
  - `_marker`: `0`
  - `api_version`: `4`
  - `ctx`: `android`
  - `q`: `{query}`
  - `p`: `1`
  - `n`: `10`
- **Detail Call (Optional)**:
  - `__call`: `song.getDetails`
  - `pids`: `{saavn_song_id}`

### Cipher Algorithm and Key
- **Cipher**: DES (Data Encryption Standard)
- **Mode**: ECB (Electronic Codebook)
- **Padding**: PKCS5Padding / PKCS7Padding
- **Secret Key (8 bytes UTF-8)**: `38346591`

### 320 kbps CDN URL Rewriting Rule
1. Decrypting `more_info.encrypted_media_url` outputs the default 96 kbps or 160 kbps CDN link:
   `https://aac.saavncdn.com/871/c2febd353f3a076a406fa37510f31f9f_96.mp4`
2. Inspect `more_info["320kbps"]`.
3. If `"true"`, apply regex string substitution:
   - Target pattern: `_(48|96|160|320)\.(mp4|aac|mp3)(?=[?#]|$)`
   - Replacement: `_320.\2`
4. The rewritten URL points to the 320 kbps AAC stream:
   `https://aac.saavncdn.com/871/c2febd353f3a076a406fa37510f31f9f_320.mp4`

### Python Resolver Implementation
```python
import base64
import json
import re
import urllib.parse
import urllib.request
from Crypto.Cipher import DES

JIOSAAVN_API = "https://www.jiosaavn.com/api.php"
DES_KEY = b"38346591"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "X-Forwarded-For": "49.36.0.1",
    "X-Real-IP": "49.36.0.1",
    "Cookie": "explicit_content=1"
}

def unpad_pkcs5(data: bytes) -> bytes:
    pad_len = data[-1]
    if pad_len < 1 or pad_len > 8:
        return data
    return data[:-pad_len]

def decrypt_jiosaavn_url(encrypted_b64: str) -> str:
    if not encrypted_b64:
        return ""
    cipher = DES.new(DES_KEY, DES.MODE_ECB)
    raw_ciphertext = base64.b64decode(encrypted_b64)
    decrypted = cipher.decrypt(raw_ciphertext)
    return unpad_pkcs5(decrypted).decode("utf-8").strip()

def search_jiosaavn(query: str, limit: int = 10) -> list[dict]:
    params = {
        "__call": "search.getResults",
        "_format": "json",
        "_marker": "0",
        "api_version": "4",
        "ctx": "android",
        "q": query,
        "p": "1",
        "n": str(limit)
    }
    url = f"{JIOSAAVN_API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    results = []
    for item in data.get("results", []):
        more = item.get("more_info", {})
        enc_url = more.get("encrypted_media_url")
        if not enc_url:
            continue
        
        raw_stream_url = decrypt_jiosaavn_url(enc_url)
        supports_320 = str(more.get("320kbps", "")).lower() == "true"
        
        if supports_320:
            final_stream_url = re.sub(r"_(48|96|160|320)\.(mp4|aac|mp3)(?=[?#]|$)", r"_320.\2", raw_stream_url)
            kbps = 320
        else:
            final_stream_url = raw_stream_url
            kbps = 160

        primary_artists = [a.get("name") for a in more.get("artistMap", {}).get("primary_artists", [])]
        artist_name = ", ".join(primary_artists) if primary_artists else "Unknown Artist"

        results.append({
            "id": item.get("id"),
            "title": item.get("title", "").replace("&quot;", '"').replace("&#039;", "'"),
            "artist": artist_name,
            "album": more.get("album"),
            "duration_sec": int(more.get("duration", 0)),
            "artwork_url": item.get("image", "").replace("150x150", "500x500").replace("http://", "https://"),
            "stream_url": final_stream_url,
            "kbps": kbps,
            "quality": "320KBPS" if supports_320 else "160KBPS"
        })
    return results
```

---

## 6. YouTube Music Fallback (InnerTube Client Emulation)

YouTube Music serves as the universal fallback catalogue when specialized lossless or high-rate CDNs lack rare recordings.

### Mechanics
- **Client Identifiers**: `WEB_REMIX` (YouTube Music Web), `ANDROID_MUSIC`, or `TVHTML5`.
- **Cipher & Signature Deobfuscation**: YouTube streams use rolling JavaScript player signatures. Auris uses `InnerTubeX` with cached preprocessed EJS player scripts and BotGuard PoToken (Proof of Origin) generated from WebView.
- **Python Integration**: In Python, use `ytmusicapi` for searching and `yt-dlp` / `innertube` for extracting the progressive Opus (`itag 251`, ~160 kbps) or AAC (`itag 140`, ~128-256 kbps) audio URL:

```python
import subprocess
import json

def get_youtube_music_stream(video_id: str) -> str | None:
    cmd = [
        "yt-dlp",
        "--get-url",
        "-f", "bestaudio[ext=webm]/bestaudio",
        f"https://music.youtube.com/watch?v=video_id"
    ]
    try:
        output = subprocess.check_output(cmd, text=True, timeout=15)
        return output.strip().splitlines()[0]
    except Exception:
        return None
```

---

## 7. Custom HTTP Addon Protocol (Stremio-Compatible)

Auris supports arbitrary user-defined HTTP addons communicating through three lightweight REST calls.

### Endpoints
1. `GET {base}/manifest.json`
   ```json
   {
     "id": "org.example.lossless",
     "name": "Custom FLAC Provider",
     "version": "1.0.0",
     "resources": ["search", "stream"],
     "allowDownloads": true
   }
   ```
2. `GET {base}/search?q={query}&quality={LOSSLESS|HIGH|LOW}`
   ```json
   {
     "tracks": [
       {
         "id": "track_12345",
         "title": "Song Title",
         "artist": "Artist Name",
         "album": "Album Name",
         "duration": 210.5,
         "artworkURL": "https://...",
         "format": "flac",
         "streamURL": null
       }
     ]
   }
   ```
3. `GET {base}/stream/{id}?quality={LOSSLESS|HIGH|LOW}`
   ```json
   {
     "url": "https://cdn.example.com/audio/track_12345.flac",
     "format": "flac",
     "codec": "flac",
     "quality": "LOSSLESS",
     "bitDepth": 24,
     "sampleRate": 96000
   }
   ```

---

## 8. Desktop Playback Pipeline (PySide6 / Qt Integration)

Desktop applications built with PySide6 (`QtMultimedia`) or `python-mpv` stream these endpoints directly.

### Recommended Playback Backend
1. **`python-mpv` (Recommended for Audiophile / Hi-Res)**:
   - Native bit-perfect playback up to 192 kHz / 32-bit float PCM.
   - Built-in FFmpeg engine handles FLAC, ALAC, Opus, AAC inside MP4, and WebM seamlessly.
   - Built-in HTTP 206 range streaming with configurable cache buffer (`demuxer-max-bytes=32M`).
   - Custom HTTP headers can be attached per stream (`ytdl-format`, `http-header-fields`).

2. **PySide6 `QMediaPlayer` + `QAudioOutput`**:
   - Native Qt integration with zero external C dynamic library dependencies.
   - Connect directly to the HTTP URL:
   ```python
   from PySide6.QtCore import QUrl
   from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

   class AudioEngine:
       def __init__(self):
           self.player = QMediaPlayer()
           self.audio_output = QAudioOutput()
           self.player.setAudioOutput(self.audio_output)
           self.audio_output.setVolume(1.0)

       def play_stream(self, url: str):
           self.player.setSource(QUrl(url))
           self.player.play()
   ```

---

## 9. Music Provider Comparison Matrix

| Provider | Audio Codec | Bitrate / Quality | Container | Auth / Account | Seeking Support | Geo-Restricted |
|---|---|---|---|---|---|---|
| **Monochrome Tracks** | FLAC | 24-bit / 44.1 - 96 kHz (~1600 kbps) | `.flac` | None (Public) | HTTP 206 (Instant) | No |
| **Tidal Community (Hi-Fi v2)** | FLAC | 16-bit / 44.1 kHz (1411 kbps) | `.flac` | Instance Relay | HTTP 206 (Instant) | No |
| **JioSaavn 320k** | AAC | 320 kbps CBR | `.mp4` / `.aac` | DES Decryption | HTTP 206 (Instant) | Bypass with Indian IP header |
| **JioSaavn 160k** | AAC | 160 kbps CBR | `.mp4` / `.aac` | DES Decryption | HTTP 206 (Instant) | Bypass with Indian IP header |
| **YouTube Music** | Opus / AAC | ~160 kbps VBR | `.webm` / `.m4a` | PoToken / Cipher | HTTP 206 (Chunked) | No |

---

## 10. Synchronized Lyrics and Captions Resolution

Auris features a dedicated lyrics engine (`LyricsRepository`) that resolves time-synced captions using a prioritised multi-provider race.

### Why Multiple Providers Are Used
1. **Timing Resolution Differences**:
   - **Word/Syllable-Synced**: Timestamps each individual syllable or word for smooth karaoke singing animations.
   - **Line-Synced**: Timestamps full sentences/lines using `[mm:ss.xx]` tags.
   - **Plain Text**: Raw lyrics text with no timing data, used as a last resort.
2. **Catalog Coverage**:
   - Apple Music/TTML sources excel at Western pop and major studio releases.
   - LRCLIB and KuGou cover Asian, regional, and indie releases that major streaming labels miss.
   - YouTube Transcripts match live cuts, acoustic sessions, and YouTube remixes exactly.
3. **Instance Redundancy**: Community mirrors frequently rot or suffer temporary rate-limiting. A tiered fallback chain prevents the player from displaying blank lyrics.

```
[Now Playing Track: Title + Artist + Duration + ISRC]
                          │
                          ▼
            [Lyrics Priority Resolution Chain]
                          │
  ┌───────────────────────┼─────────────────────────┐
  │                       │                         │
  ▼                       ▼                         ▼
[Tier 1: Word-Synced]   [Tier 2: Line-Synced]     [Tier 3: Plain Fallback]
  • lrc.red (ISRC TTML)   • LRCLIB (api/get)        • YouTube Music Tab
  • BiniLyrics            • YouTube Transcripts     • Genius Scraper
  • BetterLyrics          • KuGou
```

---

### Provider 1: lrc.red (Primary Word/Syllable-Level Provider)

The primary lead provider in Auris. Delivers Apple Music TTML (Timed Text Markup Language) documents with exact per-syllable timing markers.

#### Endpoints
- **Direct by ISRC (Fastest)**:
  `GET https://lrc.red/s/{ISRC}.ttml`
  *(Example: `https://lrc.red/s/USUG11904206.ttml`)*
- **Search by Metadata**:
  `GET https://lrc.red/search.json?q={title}+{artist}`

#### TTML Format Structure
Apple Music TTML uses XML with `<p>` lines containing timestamped `<span>` tokens:
```xml
<p begin="00:00:23.140" end="00:00:26.500">
  <span begin="00:00:23.140" end="00:00:23.500">I </span>
  <span begin="00:00:23.500" end="00:00:24.120">said, </span>
  <span begin="00:00:24.120" end="00:00:24.800">ooh, </span>
  <span begin="00:00:24.800" end="00:00:26.500">I'm blinded by the lights</span>
</p>
```

---

### Provider 2: BetterLyrics (Alternative Word-Synced Provider)

Backend powering the popular YouTube Music lyrics extension. Provides word-synced Apple Music timings without requiring API keys or user tokens.

#### Endpoints
- **Apple Timings**:
  `GET https://lyrics-api.boidu.dev/getLyrics?s={title}&a={artist}&d={duration_seconds}`
- **QQ Music Portato Timings (Asian/Karaoke)**:
  `GET https://lyrics-api.boidu.dev/qq/getLyrics?s={title}&a={artist}&d={duration_seconds}`

---

### Provider 3: LRCLIB (Standard Line-Synced Provider)

Free, community-driven, keyless lyrics database delivering standard `[mm:ss.xx]` line-synced LRC files. Highly stable and resilient.

#### Endpoints
- **Exact Match**:
  `GET https://lrclib.net/api/get?track_name={title}&artist_name={artist}&duration={duration_seconds}`
- **Fuzzy Search Fallback**:
  `GET https://lrclib.net/api/search?track_name={title}&artist_name={artist}`

#### Response Payload
```json
{
  "id": 142104,
  "trackName": "Blinding Lights",
  "artistName": "The Weeknd",
  "albumName": "After Hours",
  "duration": 200,
  "instrumental": false,
  "plainLyrics": "Yeah\nI've been tryna call...",
  "syncedLyrics": "[00:15.20] Yeah\n[00:23.14] I've been tryna call\n[00:26.85] I've been on my own for long enough..."
}
```

---

### Provider 4: YouTube Transcripts (Exact Video Alignment)

When a track is streamed directly from YouTube Music, its official captions or automatic speech recognition (ASR) transcripts can be extracted directly using the video ID.

#### InnerTube Transcript Endpoint
- **URL**: `POST https://music.youtube.com/youtubei/v1/get_transcript`
- **Payload**:
  ```json
  {
    "context": {
      "client": {
        "clientName": "WEB_REMIX",
        "clientVersion": "1.20241021.01.00"
      }
    },
    "params": "{transcript_params_from_next_endpoint}"
  }
  ```
- **Parsing**: Iterates over `transcriptCueRenderer` nodes:
  - `startOffsetMs`: Millisecond timestamp for the line.
  - `cue.simpleText`: Raw lyric text string.

---

### Python Unified Lyrics Resolver Implementation

This module queries `lrc.red` for word-synced TTML first, falls back to `LRCLIB` for line-synced LRC, parses timestamps into milliseconds, and formats lines for real-time playback synchronization.

```python
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

HEADERS = {
    "User-Agent": "EntertainX/1.0 (https://github.com/EntertainX)"
}

def parse_lrc_timestamp(stamp: str) -> int:
    """Converts '[mm:ss.xx]' or '[mm:ss.xxx]' into integer milliseconds."""
    m = re.match(r"\[?(\d+):(\d+)(?:\.(\d+))?\]?", stamp)
    if not m:
        return 0
    minutes = int(m.group(1))
    seconds = int(m.group(2))
    frac_str = m.group(3) or "0"
    if len(frac_str) == 2:
        millis = int(frac_str) * 10
    else:
        millis = int(frac_str[:3].ljust(3, "0"))
    return (minutes * 60 + seconds) * 1000 + millis

def parse_ttml_time(time_str: str) -> int:
    """Converts TTML 'hh:mm:ss.sss' or 'mm:ss.sss' into milliseconds."""
    parts = time_str.split(":")
    if len(parts) == 3:
        h, m, s = parts
        total_sec = int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        total_sec = int(m) * 60 + float(s)
    else:
        total_sec = float(parts[0])
    return int(total_sec * 1000)

def fetch_lrclib(title: str, artist: str, duration_sec: int = 0) -> list[dict] | None:
    """Fetches line-synced lyrics from LRCLIB."""
    params = {"track_name": title, "artist_name": artist}
    if duration_sec > 0:
        params["duration"] = str(duration_sec)

    url = f"https://lrclib.net/api/get?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=HEADERS)
    
    body = None
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            body = data.get("syncedLyrics")
    except Exception:
        pass

    # Fallback to search if exact match missed
    if not body:
        search_params = {"track_name": title, "artist_name": artist}
        search_url = f"https://lrclib.net/api/search?{urllib.parse.urlencode(search_params)}"
        req_search = urllib.request.Request(search_url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req_search, timeout=6) as resp:
                hits = json.loads(resp.read().decode("utf-8"))
                for hit in hits:
                    if hit.get("syncedLyrics"):
                        body = hit["syncedLyrics"]
                        break
        except Exception:
            return None

    if not body:
        return None

    parsed_lines = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.match(r"^(\[\d+:\d+(?:\.\d+)?\])(.*)$", line)
        if match:
            time_ms = parse_lrc_timestamp(match.group(1))
            text = match.group(2).strip()
            parsed_lines.append({
                "time_ms": time_ms,
                "text": text,
                "type": "line"
            })
    return parsed_lines if parsed_lines else None

def fetch_lrc_red(isrc: str) -> list[dict] | None:
    """Fetches word/syllable-synced Apple TTML lyrics from lrc.red via ISRC."""
    if not isrc or not re.match(r"^[A-Z]{2}[A-Z0-9]{3}\d{7}$", isrc.strip()):
        return None

    url = f"https://lrc.red/s/{isrc.strip().upper()}.ttml"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            xml_text = resp.read().decode("utf-8")
    except Exception:
        return None

    try:
        root = ET.fromstring(xml_text)
        ns = {"tt": root.tag.split("}")[0].strip("{")} if "}" in root.tag else {}
        body = root.find("tt:body", ns) if ns else root.find("body")
        if body is None:
            return None

        parsed_lines = []
        for p in body.iterfind(".//tt:p", ns) if ns else body.iter("p"):
            begin_attr = p.attrib.get("begin")
            if not begin_attr:
                continue
            line_time_ms = parse_ttml_time(begin_attr)
            
            words = []
            for span in p.iterfind("tt:span", ns) if ns else p.iter("span"):
                span_begin = span.attrib.get("begin")
                span_end = span.attrib.get("end")
                span_text = span.text or ""
                if span_begin and span_text:
                    words.append({
                        "begin_ms": parse_ttml_time(span_begin),
                        "end_ms": parse_ttml_time(span_end) if span_end else 0,
                        "text": span_text
                    })

            line_text = "".join(p.itertext()).strip()
            parsed_lines.append({
                "time_ms": line_time_ms,
                "text": line_text,
                "words": words,
                "type": "word" if words else "line"
            })
        return parsed_lines if parsed_lines else None
    except Exception:
        return None

def resolve_lyrics(title: str, artist: str, duration_sec: int = 0, isrc: str = None) -> list[dict]:
    """Unified resolution ladder: tries word-synced TTML first, falls back to LRCLIB."""
    if isrc:
        ttml_result = fetch_lrc_red(isrc)
        if ttml_result:
            return ttml_result

    lrc_result = fetch_lrclib(title, artist, duration_sec)
    if lrc_result:
        return lrc_result

    return []
```

---

## 11. Complete Audio and Lyrics Desktop Integration Pipeline

Connecting playback and synchronized lyrics inside a PySide6 GUI:

```
[QMediaPlayer: stream_url]
         │
         ▼ (fires positionChanged(ms) every 50-100 ms)
[Playback Position: 00:23.140]
         │
         ▼
[Lyrics Controller] ──► Binary search for active line:
                         line.time_ms <= current_position < next_line.time_ms
         │
         ▼
[UI / QScrollArea]  ──► Auto-scroll to active line
                     ──► Apply theme accent color to current lyric
                     ──► Optional: Karaoke word glow if 'words' array exists
```
