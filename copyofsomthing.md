# Streaming Providers and Reverse Engineering Specification

This document details how 1Flex resolves video streaming sources, its provider architecture, anti-debugging mechanisms, and the complete cipher required to decrypt direct HLS (.m3u8) playback URLs for movies and TV shows.

---

## 1. Anti-Debugging and Bot Detection

The site uses `disable-devtool` inside `app/layout-*.js`.

- **Trigger**: Opening browser DevTools or attaching Chrome DevTools Protocol (CDP).
- **Action**: Redirects immediately to `https://www.youtube.com/watch?v=jy4qYmf3TxA`.
- **Bypass**: Query internal Next.js endpoints, static bundles, or backend APIs directly using HTTP clients with a browser `User-Agent` and appropriate `Referer` headers.

---

## 2. Dynamic Provider Registry

The web player queries a central registry for its embed servers:

- **Endpoint**: `GET https://api.viduki.net/embed_providers?site=1flex`
- **Required Headers**:
  - `Referer: https://www.1flex.org/`
  - `Origin: https://www.1flex.org`

### Available Embed Providers

| ID               | Name        | Movie URL Template                                 | TV URL Template                                         |
| ---------------- | ----------- | -------------------------------------------------- | ------------------------------------------------------- |
| `MAIN_1`         | Viduki      | `https://www.viduki.net/1/movie/{id}?color=FF0000` | `https://www.viduki.net/1/tv/{id}/{s}/{e}?color=FF0000` |
| `MAIN_2`         | Vidy        | `https://vidy.st/movie/{id}?color=FF0000`          | `https://vidy.st/tv/{id}/{s}/{e}?color=FF0000`          |
| `MAIN_3`         | VidFast     | `https://vidfast.pro/movie/{id}?autoPlay=true`     | `https://vidfast.pro/tv/{id}/{s}/{e}?autoPlay=true`     |
| `MAIN_4`         | VidLink     | `https://vidlink.pro/movie/{id}?player=jw`         | `https://vidlink.pro/tv/{id}/{s}/{e}?player=jw`         |
| `MAIN_5`         | VidRock     | `https://vidrock.to/movie/{id}?autoplay=true`      | `https://vidrock.to/tv/{id}/{s}/{e}?autoplay=true`      |
| `MAIN_6`         | VidZee      | `https://player.vidzee.wtf/embed/movie/{id}`       | `https://player.vidzee.wtf/embed/tv/{id}/{s}/{e}`       |
| `MULTILANGUAGE`  | Viduki ML   | `https://www.viduki.net/2/movie/{id}`              | `https://www.viduki.net/2/tv/{id}/{s}/{e}`              |
| `PREMIUM_EMBEDS` | Viduki Prem | `https://www.viduki.net/4/movie/{id}`              | `https://www.viduki.net/4/tv/{id}/{s}/{e}`              |

`{id}` is the TMDB ID, `{s}` is season number, and `{e}` is episode number.

---

## 3. Direct HLS Playback Extraction (VidRock API)

The `VidRock` provider exposes an API that returns encrypted streaming URLs for various CDN mirrors (Nova, Atlas, Orion, Lyra, Elara, Vega, etc.).

### Endpoints

- **Movie**: `GET https://vidrock.to/api/movie/{tmdb_id}` (Mirror: `https://vidrock.net/api/movie/{tmdb_id}`)
- **TV Show**: `GET https://vidrock.to/api/tv/{tmdb_id}/{season}/{episode}`
- **Required Header**: `Referer: https://vidrock.to/`

### Response Payload Structure

```json
{
  "Nova": {
    "url": "X00Y4G_F9X94a1gYBSn3r88M6s2lTuUHNYzqyzNqJn15...",
    "type": "hls",
    "language": "English",
    "flag": "us"
  },
  "Atlas": {
    "url": "GTxOcxudAGra_M5wJt-vhMVijk_kNLPnt22G4fg0hqs8...",
    "type": "hls",
    "language": "English",
    "flag": "us"
  }
}
```

---

## 4. AES-GCM Decryption Algorithm

Extracted from `vidrock.to/assets/index-*.js`:

- **Cipher Algorithm**: AES-GCM (256-bit)
- **Key (Hex)**: `7f3e9c2a8b5d1f4e6a9c3b7d2e5f8a1c4b6d9e2f5a8c1b4d7e9f2a5c8b1d4e7f`
- **Encoding**: Base64URL
- **Binary Layout**:
  - Bytes `0` to `11` (12 bytes): Initialization Vector (IV / Nonce)
  - Bytes `12` to end: Ciphertext concatenated with 16-byte authentication tag
  - Decrypted result: UTF-8 string containing the direct `.m3u8` playlist URL

### Python Resolver Implementation

```python
import base64
import json
import urllib.request
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

VIDROCK_KEY = bytes.fromhex("7f3e9c2a8b5d1f4e6a9c3b7d2e5f8a1c4b6d9e2f5a8c1b4d7e9f2a5c8b1d4e7f")
CIPHER = AESGCM(VIDROCK_KEY)

def decrypt_vidrock_url(cipher_b64: str) -> str | None:
    if not cipher_b64 or len(cipher_b64) < 28:
        return None
    # Base64URL padding correction
    s = cipher_b64.replace("-", "+").replace("_", "/")
    s += "=" * ((4 - len(s) % 4) % 4)
    raw = base64.b64decode(s)

    iv = raw[:12]
    ciphertext_and_tag = raw[12:]
    decrypted_bytes = CIPHER.decrypt(iv, ciphertext_and_tag, None)
    return decrypted_bytes.decode("utf-8")

def get_movie_streams(tmdb_id: int | str) -> list[dict]:
    url = f"https://vidrock.to/api/movie/{tmdb_id}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://vidrock.to/"
        }
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    streams = []
    for server_name, item in data.items():
        enc_url = item.get("url")
        if not enc_url:
            continue
        try:
            playback_url = decrypt_vidrock_url(enc_url)
            streams.append({
                "server": server_name,
                "type": item.get("type", "hls"),
                "language": item.get("language", "English"),
                "url": playback_url
            })
        except Exception:
            continue
    return streams
```

---

## 5. Stream Characteristics and Playback Notes

1. **HLS Playlists**:
   - Manifests return with `Content-Type: application/vnd.apple.mpegurl`.
   - Video segments are standard MPEG-TS or fragmented MP4 chunks. Some CDNs disguise segments using `.jpg` extensions (e.g. `s_0.jpg?t=...`) to avoid network filtering.
   - Playable directly in VLC, mpv, Qt Multimedia (`QMediaPlayer`), or browser video engines (`hls.js`).

2. **Subtitles**:
   - Subtitle service host: `https://sub.vdrk.site`

3. **Fallback Torrent Search**:
   - For titles without active direct CDN mirrors, the site falls back to querying Stremio-compatible torrent scrapers using IMDb IDs:
     - `https://torrentio.strem.fun`
     - `https://thepiratebay-plus.strem.fun`
     - `https://comet.feels.legal`

---

## 6. WatchFree Provider Registry

WatchFree (`https://watchfree.win/`) resolves playback via an embed player container controlled by `watch-controller.js` and `watch-servers.js`. It queries TMDB IDs for movies, and TMDB ID + Season + Episode for TV shows across 9 streaming servers.

### Available Embed Providers

| Provider ID  | Provider Name | Quality  | Movie Embed URL Template                       | TV Embed URL Template                                      | Characteristics                                                    |
| ------------ | ------------- | -------- | ---------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------ |
| `videasy`    | Videasy       | HD       | `https://player.videasy.ws/embed/movie/{id}`   | `https://player.videasy.ws/embed/tv/{id}/{s}/{e}`          | Default provider. Backed by VidSrc.sh with dynamic WASM decryptor. |
| `vixsrc`     | VixSrc        | HD       | `https://vixsrc.to/movie/{id}`                 | `https://vixsrc.to/tv/{id}/{s}/{e}`                        | Fastest direct HLS extraction provider. Multi-audio and subtitles. |
| `vidfast`    | VidFast       | HD       | `https://vidfast.me/movie/{id}`                | `https://vidfast.me/tv/{id}/{s}/{e}`                       | Fast CDN mirror of VidFast.                                        |
| `vidsrc`     | VidSrc        | HD       | `https://vidsrc.me/embed/movie/{id}`           | `https://vidsrc.me/embed/tv/{id}/{s}/{e}`                  | Mirror of Videasy / VidSrc.sh pipeline.                            |
| `vidlink`    | VidLink       | Standard | `https://vidlink.pro/movie/{id}`               | `https://vidlink.pro/tv/{id}/{s}/{e}`                      | Direct web player with JWPlayer engine.                            |
| `vidrock`    | VidRock       | HD       | `https://vidrock.to/movie/{id}`                | `https://vidrock.to/tv/{id}/{s}/{e}`                       | Embed player for VidRock CDN sources (see Section 3).              |
| `111movies`  | 111Movies     | HD       | `https://111movies.net/movie/{id}`             | `https://111movies.net/tv/{id}/{s}/{e}`                    | VidMario player with 8 server clusters (Pythagoras, Euler, Gauss). |
| `vidzee`     | Vidzee        | HD       | `https://player.vidzee.wtf/embed/movie/{id}`   | `https://player.vidzee.wtf/embed/tv/{id}/{s}/{e}`          | Clean iframe embed player.                                         |
| `superembed` | SuperEmbed    | HD       | `https://multiembed.mov/?video_id={id}&tmdb=1` | `https://multiembed.mov/?video_id={id}&tmdb=1&s={s}&e={e}` | MultiEmbed player gated by Cloudflare Turnstile.                   |

`{id}` is the TMDB ID, `{s}` is the season number, and `{e}` is the episode number.

### Python Embed URL Helper

```python
def get_watchfree_embed_url(provider: str, tmdb_id: int | str, season: int = None, episode: int = None) -> str:
    """
    Constructs an embed player URL for any WatchFree provider.
    """
    is_tv = season is not None and episode is not None
    templates = {
        "videasy": "https://player.videasy.ws/embed/tv/{id}/{s}/{e}" if is_tv else "https://player.videasy.ws/embed/movie/{id}",
        "vixsrc": "https://vixsrc.to/tv/{id}/{s}/{e}" if is_tv else "https://vixsrc.to/movie/{id}",
        "vidfast": "https://vidfast.me/tv/{id}/{s}/{e}" if is_tv else "https://vidfast.me/movie/{id}",
        "vidsrc": "https://vidsrc.me/embed/tv/{id}/{s}/{e}" if is_tv else "https://vidsrc.me/embed/movie/{id}",
        "vidlink": "https://vidlink.pro/tv/{id}/{s}/{e}" if is_tv else "https://vidlink.pro/movie/{id}",
        "vidrock": "https://vidrock.to/tv/{id}/{s}/{e}" if is_tv else "https://vidrock.to/movie/{id}",
        "111movies": "https://111movies.net/tv/{id}/{s}/{e}" if is_tv else "https://111movies.net/movie/{id}",
        "vidzee": "https://player.vidzee.wtf/embed/tv/{id}/{s}/{e}" if is_tv else "https://player.vidzee.wtf/embed/movie/{id}",
        "superembed": "https://multiembed.mov/?video_id={id}&tmdb=1&s={s}&e={e}" if is_tv else "https://multiembed.mov/?video_id={id}&tmdb=1",
    }
    tmpl = templates.get(provider.lower())
    if not tmpl:
        raise ValueError(f"Unknown provider '{provider}'. Available: {list(templates.keys())}")
    return tmpl.format(id=tmdb_id, s=season, e=episode)
```

---

## 7. Direct HLS Playback Extraction (VixSrc Resolver)

VixSrc exposes a lightweight API endpoint that resolves TMDB IDs into signed HLS Master Playlists (.m3u8). The resolved stream features multiple audio tracks (e.g. English, Italian), subtitle tracks (VTT), and adaptive bitrate video streams.

### Endpoints and Flow

1. **Movie Metadata Request**: `GET https://vixsrc.to/api/movie/{tmdb_id}`
2. **TV Metadata Request**: `GET https://vixsrc.to/api/tv/{tmdb_id}/{season}/{episode}`
   - **Required Headers**:
     - `Referer: https://vixsrc.to/movie/{tmdb_id}` (or `https://vixsrc.to/tv/{tmdb_id}/{season}/{episode}`)
     - `Origin: https://vixsrc.to`
3. **Response Payload**:
   ```json
   {
     "src": "/embed/{video_id}?token={token}&expires={expires}&lang=en&skin=vixsrc"
   }
   ```
4. **Embed Page Inspection**: `GET https://vixsrc.to{src}` returns HTML containing:
   ```javascript
   window.masterPlaylist = {
     params: { token: "{token}", expires: "{expires}", asn: "" },
     url: "https://vixsrc.to/playlist/{video_id}",
   };
   ```
5. **Direct Master Playlist**:
   `GET https://vixsrc.to/playlist/{video_id}?token={token}&expires={expires}`
   - Returns the active `#EXTM3U` manifest directly playable in `QMediaPlayer`, VLC, or `mpv`.

### Python Resolver Implementation

```python
import json
import re
import urllib.request

def resolve_vixsrc_stream(tmdb_id: int | str, season: int = None, episode: int = None) -> str | None:
    """
    Extracts direct HLS (.m3u8) master playlist URL from VixSrc.
    Compatible with movies and TV shows.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    if season is not None and episode is not None:
        api_url = f"https://vixsrc.to/api/tv/{tmdb_id}/{season}/{episode}"
        ref = f"https://vixsrc.to/tv/{tmdb_id}/{season}/{episode}"
    else:
        api_url = f"https://vixsrc.to/api/movie/{tmdb_id}"
        ref = f"https://vixsrc.to/movie/{tmdb_id}"

    try:
        # Step 1: Query API for embed endpoint
        req = urllib.request.Request(api_url, headers={**headers, "Referer": ref, "Origin": "https://vixsrc.to"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if "src" not in data:
            return None

        embed_url = "https://vixsrc.to" + data["src"]

        # Step 2: Fetch embed page to extract playlist signature
        req2 = urllib.request.Request(embed_url, headers={**headers, "Referer": ref})
        with urllib.request.urlopen(req2, timeout=10) as resp2:
            html = resp2.read().decode("utf-8")

        m = re.search(r"window\.masterPlaylist\s*=\s*(\{.*?\});", html, re.DOTALL)
        if not m:
            return None

        token_m = re.search(r"'token':\s*'([^']+)'", m.group(1))
        expires_m = re.search(r"'expires':\s*'([^']+)'", m.group(1))
        url_m = re.search(r"url:\s*'([^']+)'", m.group(1))

        if token_m and expires_m and url_m:
            token = token_m.group(1)
            expires = expires_m.group(1)
            base_playlist_url = url_m.group(1)
            return f"{base_playlist_url}?token={token}&expires={expires}"
    except Exception:
        return None

    return None
```

---

## 8. Direct HLS Playback Extraction (Videasy / VidSrc.sh WASM Decryption Protocol)

Videasy (`player.videasy.ws`) and VidSrc (`vidsrc.me`) share an encrypted backend powered by `vidsrc.sh` and dynamic WebAssembly decryption (`vsdec.js`).

### Architecture and Lifecycle

1. **Gate Token Generation**:
   `GET https://player.videasy.ws/vs_src.php?type=movie&id={tmdb_id}` (or `type=tv&id={tmdb_id}&season={s}&episode={e}`)
   - Returns: `{"src": "https://stellarconductornexus.com/embed/movie/{id}?vs={gate_token}"}`
2. **Metadata and Pool Discovery**:
   - Query metadata endpoint: `GET https://data.vidsrc.sh/api.php?type=movie&tmdb={id}`
   - Returns: `data.stream_urls_api_host` (e.g. `riverandreed.space`).
3. **Session Token Minting**:
   - Query inner player: `GET https://stellarconductornexus.com/embed/player/movie/{id}?vs={gate_token}`
   - Extracts single-use IP-bound `CONFIG.apiToken`.
   - Mint playback token: `GET https://{stream_urls_api_host}/generate.php?api_token={apiToken}` yields playback session token `tk`.
4. **Encrypted Stream URLs**:
   - `GET https://{stream_urls_api_host}/api.php?type=movie&tmdb={id}&stream_urls&api_token={apiToken}`
   - Returns payload containing:
     - `data.stream_urls`: Base64 ChaCha20 ciphertext (nonce + encrypted URLs).
     - `vs.wasm_url`: Dynamic WebAssembly compiler URL valid for a 5-minute window (`https://data.vidsrc.sh/wasm.php?w={w}`).
5. **WASM Decryption**:
   - WebAssembly module exports: `alloc(len)` and `decrypt(ptr, len)`.
   - The decrypted payload yields newline-delimited stream URLs (e.g. `https://{stream_urls_api_host}/pl/{hash}`).
6. **Master Playlist Request**:
   - Stamping the session token onto the playlist URL (`{stream_url}?token={tk}`) returns the live HLS `#EXTM3U` playlist.

---

## 9. WatchFree Internal Site APIs

For client applications indexing or searching catalog items:

- **Search Suggestions**: `GET https://watchfree.win/api/search?q={query}`
- **Popular Movies**: `GET https://watchfree.win/api/movies/popular`
- **TV Show Season Episodes**: `GET https://watchfree.win/api/tv/{tmdb_id}/season/{season_number}`
- **Active Viewer Count**: `GET https://watchfree.win/api/active-users`
