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
