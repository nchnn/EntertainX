# Streaming Providers

This document lists every video source used to resolve movies and TV shows: the 1Flex embed registry, VidRock, the WatchFree server list, VixSrc, and the Videasy / VidSrc pipeline, plus torrent fallbacks and the WatchFree catalog APIs.

`api/streaming.py` currently resolves playback through VidRock (Main 1) and VixSrc (Main 2). The player never talks to a third-party site itself; it receives a playable HLS or MP4 URL.

`{id}` is the TMDB id, `{s}` is the season number, and `{e}` is the episode number.

---

## 1. 1Flex Embed Registry

The web player queries a central registry for its embed servers:

- **Endpoint**: `GET https://api.viduki.net/embed_providers?site=1flex`
- **Required Headers**:
  - `Referer: https://www.1flex.org/`
  - `Origin: https://www.1flex.org`

| ID | Name | Movie URL Template | TV URL Template |
|---|---|---|---|
| `MAIN_1` | Viduki | `https://www.viduki.net/1/movie/{id}?color=FF0000` | `https://www.viduki.net/1/tv/{id}/{s}/{e}?color=FF0000` |
| `MAIN_2` | Vidy | `https://vidy.st/movie/{id}?color=FF0000` | `https://vidy.st/tv/{id}/{s}/{e}?color=FF0000` |
| `MAIN_3` | VidFast | `https://vidfast.pro/movie/{id}?autoPlay=true` | `https://vidfast.pro/tv/{id}/{s}/{e}?autoPlay=true` |
| `MAIN_4` | VidLink | `https://vidlink.pro/movie/{id}?player=jw` | `https://vidlink.pro/tv/{id}/{s}/{e}?player=jw` |
| `MAIN_5` | VidRock | `https://vidrock.to/movie/{id}?autoplay=true` | `https://vidrock.to/tv/{id}/{s}/{e}?autoplay=true` |
| `MAIN_6` | VidZee | `https://player.vidzee.wtf/embed/movie/{id}` | `https://player.vidzee.wtf/embed/tv/{id}/{s}/{e}` |
| `MULTILANGUAGE` | Viduki ML | `https://www.viduki.net/2/movie/{id}` | `https://www.viduki.net/2/tv/{id}/{s}/{e}` |
| `PREMIUM_EMBEDS` | Viduki Prem | `https://www.viduki.net/4/movie/{id}` | `https://www.viduki.net/4/tv/{id}/{s}/{e}` |

---

## 2. VidRock

VidRock returns encrypted streaming URLs for CDN mirrors (Nova, Atlas, Orion, Lyra, Elara, Vega, and others). This is Main 1 in `api/streaming.py`.

### Endpoints

- **Movie**: `GET https://vidrock.to/api/movie/{id}`
- **TV**: `GET https://vidrock.to/api/tv/{id}/{s}/{e}`
- **Mirror**: the same paths on `https://vidrock.net`
- **Headers**: `Referer: https://vidrock.to/` and `Origin: https://vidrock.to`

Try `vidrock.to` first. On HTTP 404 or a network error, retry the same path on `vidrock.net`.

### Response

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

Each `url` is Base64URL ciphertext. Decryption is AES-256-GCM, extracted from `vidrock.to/assets/index-*.js`:

- **Key (hex)**: `7f3e9c2a8b5d1f4e6a9c3b7d2e5f8a1c4b6d9e2f5a8c1b4d7e9f2a5c8b1d4e7f`
- **Bytes 0–11**: 12-byte nonce
- **Remainder**: ciphertext followed by a 16-byte authentication tag
- **Plaintext**: a UTF-8 `http` or `https` URL (`.m3u8` or `.mp4`)

Playback requests for these URLs send the same VidRock `Referer` and `Origin`. Several of these CDNs reject a `User-Agent`, so that header is omitted.

Before a mirror is offered to the player, an HLS URL is preflighted. The response must be under HTTP 400 and the body must start with `#EXTM3U`. MP4 URLs skip that check. Duplicate URLs are dropped.

### Resolver

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
            "Referer": "https://vidrock.to/",
        },
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
                "url": playback_url,
            })
        except Exception:
            continue
    return streams
```

The live implementation is `decrypt_vidrock_url` and `resolve_vidrock` in `api/streaming.py`. It also tries `https://vidrock.net` and omits `User-Agent` on CDN playback.

---

## 3. Playback Notes

1. **HLS playlists**
   - Manifests return with `Content-Type: application/vnd.apple.mpegurl`.
   - Segments are MPEG-TS or fragmented MP4. Some CDNs serve segments with a `.jpg` extension (for example `s_0.jpg?t=...`).
   - The in-app player consumes the resolved URL through `api/stream_proxy.py`. The same URL is playable in VLC, mpv, Qt Multimedia (`QMediaPlayer`), or `hls.js`.

2. **Subtitles**
   - Subtitle service host: `https://sub.vdrk.site`

3. **Torrent fallback**
   - When a title has no direct CDN mirror, fall back to Stremio-compatible torrent scrapers using the IMDb id:
     - `https://torrentio.strem.fun`
     - `https://comet.feels.legal`

---

## 4. WatchFree Provider Registry

WatchFree (`https://watchfree.win/`) resolves playback through `watch-controller.js` and `watch-servers.js`. Movies use the TMDB id. TV uses the TMDB id plus season and episode.

| Provider ID | Provider Name | Quality | Movie Embed URL Template | TV Embed URL Template | Characteristics |
|---|---|---|---|---|---|
| `videasy` | Videasy | HD | `https://player.videasy.ws/embed/movie/{id}` | `https://player.videasy.ws/embed/tv/{id}/{s}/{e}` | Default provider. Backed by VidSrc.sh with a dynamic WASM decryptor. |
| `vixsrc` | VixSrc | HD | `https://vixsrc.to/movie/{id}` | `https://vixsrc.to/tv/{id}/{s}/{e}` | Direct HLS extraction. Multi-audio and subtitles. |
| `vidfast` | VidFast | HD | `https://vidfast.me/movie/{id}` | `https://vidfast.me/tv/{id}/{s}/{e}` | Fast CDN mirror of VidFast. |
| `vidsrc` | VidSrc | HD | `https://vidsrc.me/embed/movie/{id}` | `https://vidsrc.me/embed/tv/{id}/{s}/{e}` | Mirror of the Videasy / VidSrc.sh pipeline. |
| `vidlink` | VidLink | Standard | `https://vidlink.pro/movie/{id}` | `https://vidlink.pro/tv/{id}/{s}/{e}` | Web player with a JWPlayer engine. |
| `vidrock` | VidRock | HD | `https://vidrock.to/movie/{id}` | `https://vidrock.to/tv/{id}/{s}/{e}` | Embed player for the VidRock CDN sources in section 2. |
| `111movies` | 111Movies | HD | `https://111movies.net/movie/{id}` | `https://111movies.net/tv/{id}/{s}/{e}` | VidMario player with server clusters (Pythagoras, Euler, Gauss). |
| `vidzee` | Vidzee | HD | `https://player.vidzee.wtf/embed/movie/{id}` | `https://player.vidzee.wtf/embed/tv/{id}/{s}/{e}` | Iframe embed player. |
| `superembed` | SuperEmbed | HD | `https://multiembed.mov/?video_id={id}&tmdb=1` | `https://multiembed.mov/?video_id={id}&tmdb=1&s={s}&e={e}` | MultiEmbed player gated by Cloudflare Turnstile. |

### Embed URL helper

```python
def get_watchfree_embed_url(provider: str, tmdb_id: int | str, season: int = None, episode: int = None) -> str:
    """Construct an embed player URL for any WatchFree provider."""
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

## 5. VixSrc

VixSrc resolves a TMDB id into a signed HLS master playlist. The playlist can include multiple audio tracks, VTT subtitles, and adaptive video. This is Main 2 in `api/streaming.py`.

### Flow

1. **Metadata**
   - Movie: `GET https://vixsrc.to/api/movie/{id}`
   - TV: `GET https://vixsrc.to/api/tv/{id}/{s}/{e}`
   - Headers: a browser `User-Agent`, `Origin: https://vixsrc.to`, and `Referer` set to the matching movie or episode page (`https://vixsrc.to/movie/{id}` or `https://vixsrc.to/tv/{id}/{s}/{e}`).
2. **Response**
   ```json
   { "src": "/embed/{video_id}?token={token}&expires={expires}&lang=en&skin=vixsrc" }
   ```
3. **Embed page**: `GET https://vixsrc.to{src}` with the same `User-Agent` and `Referer`. The HTML contains:
   ```javascript
   window.masterPlaylist = {
       params: { 'token': '{token}', 'expires': '{expires}', 'asn': '' },
       url: 'https://vixsrc.to/playlist/{video_id}'
   };
   ```
4. **Playlist**: `{url}?token={token}&expires={expires}`
   - Returns the `#EXTM3U` manifest.

Playback sends `User-Agent`, `Referer`, and `Origin: https://vixsrc.to`. The playlist is preflighted the same way as a VidRock HLS URL. The live implementation is `resolve_vixsrc` in `api/streaming.py`.

### Resolver

```python
import json
import re
import urllib.request

def resolve_vixsrc_stream(tmdb_id: int | str, season: int = None, episode: int = None) -> str | None:
    """Extract a direct HLS master playlist URL from VixSrc."""
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
        req = urllib.request.Request(api_url, headers={**headers, "Referer": ref, "Origin": "https://vixsrc.to"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if "src" not in data:
            return None

        embed_url = "https://vixsrc.to" + data["src"]
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
            return f"{url_m.group(1)}?token={token_m.group(1)}&expires={expires_m.group(1)}"
    except Exception:
        return None

    return None
```

---

## 6. Videasy / VidSrc

Videasy (`player.videasy.ws`) and VidSrc (`vidsrc.me`) share an encrypted backend powered by `vidsrc.sh` and dynamic WebAssembly decryption (`vsdec.js`).

1. **Gate token**
   `GET https://player.videasy.ws/vs_src.php?type=movie&id={id}` (or `type=tv&id={id}&season={s}&episode={e}`)
   - Returns: `{"src": "https://stellarconductornexus.com/embed/movie/{id}?vs={gate_token}"}`
2. **Metadata and pool**
   - `GET https://data.vidsrc.sh/api.php?type=movie&tmdb={id}`
   - Returns `data.stream_urls_api_host` (for example `riverandreed.space`).
3. **Session token**
   - `GET https://stellarconductornexus.com/embed/player/movie/{id}?vs={gate_token}`
   - Extracts a single-use IP-bound `CONFIG.apiToken`.
   - `GET https://{stream_urls_api_host}/generate.php?api_token={apiToken}` yields the playback session token `tk`.
4. **Encrypted stream URLs**
   - `GET https://{stream_urls_api_host}/api.php?type=movie&tmdb={id}&stream_urls&api_token={apiToken}`
   - `data.stream_urls` is Base64 ChaCha20 ciphertext (nonce plus encrypted URLs).
   - `vs.wasm_url` is a WebAssembly module URL valid for about five minutes (`https://data.vidsrc.sh/wasm.php?w={w}`).
5. **WASM decryption**
   - The module exports `alloc(len)` and `decrypt(ptr, len)`.
   - The decrypted payload is newline-delimited stream URLs (for example `https://{stream_urls_api_host}/pl/{hash}`).
6. **Master playlist**
   - `{stream_url}?token={tk}` returns the live HLS `#EXTM3U` playlist.

---

## 7. WatchFree Catalog APIs

- **Search suggestions**: `GET https://watchfree.win/api/search?q={query}`
- **Popular movies**: `GET https://watchfree.win/api/movies/popular`
- **TV season episodes**: `GET https://watchfree.win/api/tv/{id}/season/{s}`
- **Active viewer count**: `GET https://watchfree.win/api/active-users`
