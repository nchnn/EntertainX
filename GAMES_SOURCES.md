# Games Embedding and Reverse Engineering Specification

This document details how 1Flex (`1flex.org/games`) catalogs, sources, renders, and embeds browser games. It provides complete endpoint specifications, asset resolution URLs, iframe sandbox requirements, engine classifications, and a Python PySide6 integration guide for bit-clean in-GUI desktop playback without spawning external browser windows.

---

## 1. Architectural Overview

1Flex does not develop, compile, or store game binaries on its primary streaming servers. Instead, it operates as a lightweight client-side frontend that pulls game metadata and playable runtime bundles from the **Selenite** unblocked game infrastructure (`selenite.cc`), using **1Tube** (`1tube.org`) as an image mirror.

```
[1Flex Frontend: /games]
         │
         ├──► 1. Fetches Catalog: https://selenite.cc/resources/games.json (921 Games)
         │
         ├──► 2. Resolves Thumbnails:
         │       • Primary:  https://www.1tube.org/games/semag/{directory}/{image}
         │       • Upstream: https://selenite.cc/resources/semag/{directory}/{image}
         │
         └──► 3. Embeds Player:
                 <iframe src="https://selenite.cc/resources/semag/{directory}/index.html"
                         allow="fullscreen *; autoplay *; gamepad *; clipboard-write *">
```

### Key Architectural Characteristics
- **Zero Authentication / Keyless**: No API keys, tokens, or session cookies required.
- **Open CORS**: Endpoints serve `access-control-allow-origin: *`.
- **No Framing Restrictions**: The server omits `X-Frame-Options` and CSP `frame-ancestors` headers, allowing embedding inside standard web views or HTML iframes.
- **Obfuscation Nomenclature**: The asset directory is named `semag` ("games" spelled backwards), an established convention used to bypass institutional content filters and web firewalls.

---

## 2. Catalog and Metadata Extraction

### Endpoint
- **URL**: `GET https://selenite.cc/resources/games.json`
- **Method**: `GET`
- **Headers**:
  ```http
  User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36
  Accept: application/json
  ```

### Data Schema
The response is a JSON array of 920+ game descriptor objects:

```json
[
  {
    "name": "Geometry Dash",
    "image": "gd.webp",
    "directory": "webdash",
    "tags": [
      "top",
      "platformer"
    ]
  },
  {
    "name": "Pokemon Scarlet and Violet GBA",
    "image": "pokemon.jpg",
    "directory": "pokemonsavgba",
    "tags": [
      "rpg",
      "emulator"
    ]
  },
  {
    "name": "Boil Noodles at Night",
    "image": "boil.webp",
    "directory": "boilnoodles",
    "tags": [
      "action",
      "unity",
      "cooking"
    ]
  }
]
```

### Field Definitions

| Field | Type | Description | Example |
|---|---|---|---|
| `name` | String | Display title of the game | `"Geometry Dash"` |
| `image` | String | Filename of the game thumbnail icon | `"gd.webp"`, `"cover.png"` |
| `directory` | String | Unique slug / directory identifier for the game bundle | `"webdash"`, `"boilnoodles"` |
| `tags` | Array[String] | Categories, engine tags, and content rating tags | `["action", "unity"]` |

### Tag Taxonomy Breakdown
Auris and 1Flex catalog items carry 42 unique tags. The dominant genres include:
- `action` (332 titles)
- `flash` (243 titles, emulated via Ruffle WebAssembly)
- `platformer` (213 titles)
- `emulator` (212 titles, retro consoles via EmulatorJS WebAssembly)
- `unity` (135 titles, Unity WebGL/WASM exports)
- `sandbox` (75 titles)
- `puzzle` (67 titles)
- `horror` (63 titles)
- `racing` (56 titles)
- `shooter` / `fps` (66 titles)

---

## 3. Thumbnail and Media Asset Resolution

Each game references an image filename in its descriptor. The image is resolved by combining the base CDN path with the game directory and image filename.

### URL Construction Rule
1. **Primary CDN (1Tube Mirror)**:
   `https://www.1tube.org/games/semag/{directory}/{image}`
2. **Upstream CDN (Selenite Direct)**:
   `https://selenite.cc/resources/semag/{directory}/{image}`
3. **Local Fallback**:
   If an image fails with `HTTP 404`, supply a local placeholder icon (`assets/icons/gamepad.svg` or `/games/img/missing.svg`).

### Examples
- **Geometry Dash**:
  - `https://www.1tube.org/games/semag/webdash/gd.webp`
  - `https://selenite.cc/resources/semag/webdash/gd.webp`
- **Pokemon Scarlet and Violet GBA**:
  - `https://www.1tube.org/games/semag/pokemonsavgba/pokemon.jpg`
- **Cheese Rolling**:
  - `https://www.1tube.org/games/semag/cheeserolling/chese.webp`

---

## 4. Play and Embed Mechanics

### Target Embed URL
The playable game bundle is hosted as an HTML index inside the game directory:
`https://selenite.cc/resources/semag/{directory}/index.html`

### 1Flex Web Implementation
In the 1Flex Next.js application (`app/games/page.js`), opening a game triggers an overlay dialog rendering an iframe:

```jsx
<iframe
  ref={iframeRef}
  src={`https://selenite.cc/resources/semag/${game.directory}/index.html`}
  title={game.name}
  className="min-h-0 w-full flex-1 border-0 bg-black"
  allow="fullscreen *; autoplay *; gamepad *; clipboard-write *"
  allowFullScreen={true}
/>
```

### URL State Management
- When a game is clicked, the web client updates the URL search query without reloading:
  `window.history.pushState({ game: directory }, "", "?play=" + encodeURIComponent(directory))`
- Direct links with `?play={directory}` automatically find and launch the matching game from the catalog.

---

## 5. Game Runtime Engines and Bundling Architecture

The 921 games in the Selenite catalog fall into four distinct technical runtime categories:

### 1. Pure HTML5 / Canvas / JavaScript
- **Examples**: 2048, Geometry Dash (WebDash port), Flappy Bird, Crossy Road.
- **Runtime**: Standard HTML5 `<canvas>` driven by engines like Phaser, PixiJS, or custom Canvas loops.
- **Network Requirements**: Self-contained static assets (`.js`, `.png`, `.mp3`). Extremely low memory footprint.

### 2. Unity WebGL (WebAssembly)
- **Examples**: Drive Mad, Duck Life 4, Boil Noodles at Night, Cheese Rolling.
- **Runtime**: Unity WebGL exporter (`Build/UnityLoader.js` or `Build/build.framework.js`, `.wasm`, `.data`).
- **Memory Requirements**: Needs 256MB to 1024MB WebAssembly heap allocation.

### 3. Emulated Flash (Ruffle WebAssembly)
- **Examples**: Fireboy and Watergirl, Papa's Pizzeria, Age of War, Bloons Tower Defense.
- **Runtime**: Ruffle (`ruffle.js`), an Adobe Flash Player emulator written in Rust and compiled to WebAssembly.
- **Assets**: Reads `.swf` vectors and renders to WebGL with audio synthesis.

### 4. EmulatorJS (Retro Consoles)
- **Examples**: Pokemon GBA hacks, GTA Vice City (ported 2D/PSX), Mario 64, Sonic.
- **Runtime**: `EmulatorJS` (`/resources/semag/emulatorjs/data/loader.js`) with RetroArch Libretro cores compiled to WebAssembly (GBA, NES, SNES, N64, Genesis, PS1).
- **Configuration injected into HTML**:
  ```javascript
  EJS_player = "#game";
  EJS_core = "gba"; // or nes, snes, n64, nds
  EJS_color = "#000000";
  EJS_startOnLoaded = true;
  EJS_pathtodata = "/resources/semag/emulatorjs/data/";
  EJS_gameUrl = "pag.gba";
  ```

---

## 6. Python Scraper and Catalog Manager

This module scrapes, parses, sanitizes, and indexes the entire games catalog from Selenite and 1Flex.

```python
import json
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass

CATALOG_URL = "https://selenite.cc/resources/games.json"
PRIMARY_IMAGE_BASE = "https://www.1tube.org/games/semag"
UPSTREAM_IMAGE_BASE = "https://selenite.cc/resources/semag"
EMBED_BASE = "https://selenite.cc/resources/semag"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Accept": "application/json"
}


@dataclass
class GameEntry:
    name: str
    directory: str
    image: str
    tags: list[str]
    thumbnail_url: str
    backup_thumbnail_url: str
    embed_url: str

    def to_dict(self) -> dict:
        return asdict(self)


class GamesCatalog:
    def __init__(self) -> None:
        self.games: list[GameEntry] = []
        self._by_directory: dict[str, GameEntry] = {}

    def fetch_catalog(self, timeout: int = 10) -> list[GameEntry]:
        """Fetches and parses the entire game catalog from Selenite."""
        req = urllib.request.Request(CATALOG_URL, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw_data = json.loads(resp.read().decode("utf-8"))

        entries: list[GameEntry] = []
        for item in raw_data:
            name = item.get("name", "").strip()
            directory = item.get("directory", "").strip()
            image = item.get("image", "").strip()
            tags = item.get("tags", [])

            if not directory or not name:
                continue

            entry = GameEntry(
                name=name,
                directory=directory,
                image=image,
                tags=tags,
                thumbnail_url=f"{PRIMARY_IMAGE_BASE}/{directory}/{image}",
                backup_thumbnail_url=f"{UPSTREAM_IMAGE_BASE}/{directory}/{image}",
                embed_url=f"{EMBED_BASE}/{directory}/index.html",
            )
            entries.append(entry)

        # Sort alphabetically by title
        entries.sort(key=lambda g: g.name.lower())
        self.games = entries
        self._by_directory = {g.directory: g for g in entries}
        return self.games

    def search(self, query: str, tag: str | None = None) -> list[GameEntry]:
        """Filters catalog by title keyword and optional genre tag."""
        q = query.strip().lower()
        results = self.games

        if tag:
            t = tag.strip().lower()
            results = [g for g in results if t in [x.lower() for x in g.tags]]

        if q:
            results = [g for g in results if q in g.name.lower()]

        return results

    def get_by_directory(self, directory: str) -> GameEntry | None:
        """Looks up a specific game by slug directory."""
        return self._by_directory.get(directory)


if __name__ == "__main__":
    catalog = GamesCatalog()
    all_games = catalog.fetch_catalog()
    print(f"Loaded {len(all_games)} games.")

    # Test search
    dash_games = catalog.search("dash")
    print(f"Found {len(dash_games)} games matching 'dash':")
    for g in dash_games[:3]:
        print(f" - {g.name} -> {g.embed_url}")
```

---

## 7. Desktop Playback Pipeline (PySide6 QtWebEngine)

Per project requirements, EntertainX must never invoke external browsers (`webbrowser.open`) or spawn detached processes. Games run embedded directly inside the Qt window using `QWebEngineView`.

### Required Qt WebEngine Configuration
The web runtime requires WebGL, Audio Autoplay, Gamepad support, and LocalStorage for saving game progress:

```python
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class GamePlayerWidget(QWidget):
    """Self-contained desktop game player embedding Selenite game builds."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("GamePlayerWidget")
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar with game title and control buttons
        self.header = QWidget()
        self.header.setStyleSheet("background-color: #141414; padding: 6px;")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(12, 6, 12, 6)

        self.title_label = QLabel("Playing Game")
        self.title_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        self.btn_fullscreen = QPushButton("Fullscreen")
        self.btn_fullscreen.clicked.connect(self._toggle_fullscreen)
        header_layout.addWidget(self.btn_fullscreen)

        self.btn_close = QPushButton("Close")
        header_layout.addWidget(self.btn_close)

        layout.addWidget(self.header)

        # Embedded Chromium View
        self.web_view = QWebEngineView()
        self._configure_settings(self.web_view.settings())
        layout.addWidget(self.web_view)

        # Fullscreen handling
        self.web_view.page().fullScreenRequested.connect(self._handle_fullscreen_request)

    def _configure_settings(self, settings: QWebEngineSettings) -> None:
        """Enables essential capabilities for HTML5, WebGL, and WASM games."""
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)

    def load_game(self, game_name: str, embed_url: str) -> None:
        self.title_label.setText(game_name)
        self.web_view.setUrl(QUrl(embed_url))

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            self.header.show()
            self.btn_fullscreen.setText("Fullscreen")
        else:
            self.showFullScreen()
            self.header.hide()
            self.btn_fullscreen.setText("Exit Fullscreen")

    def _handle_fullscreen_request(self, request) -> None:
        request.accept()
        if request.toggleOn():
            self.showFullScreen()
            self.header.hide()
        else:
            self.showNormal()
            self.header.show()

    def stop_game(self) -> None:
        """Stops audio and clears page memory upon exit."""
        self.web_view.setUrl(QUrl("about:blank"))
```

---

## 8. Provider Comparison and Source Resilience Matrix

| Channel | Endpoint Base | Availability | CORS / Auth | Content Types |
|---|---|---|---|---|
| **Selenite Games Catalog** | `https://selenite.cc/resources/games.json` | 921 Games | Public / `*` | JSON Metadata Array |
| **Selenite Game Bundle** | `https://selenite.cc/resources/semag/{dir}/index.html` | High | Public / `*` | HTML5, Unity WASM, Flash (Ruffle), EmulatorJS |
| **1Tube Image CDN** | `https://www.1tube.org/games/semag/{dir}/{img}` | Fast / Cached | Public / `*` | WebP, PNG, JPG Cover Icons |
| **Selenite Image CDN** | `https://selenite.cc/resources/semag/{dir}/{img}` | Direct Upstream | Public / `*` | WebP, PNG, JPG Cover Icons |
| **selenite-old (GitHub)** | `https://github.com/selenite-cc/selenite-old` | Archived | Git clone | Full source code for hundreds of unblocked web games |
| **Flash Archive (GitHub)** | `https://github.com/selenite-cc/flasharchive` | Archived | Git clone | 51 classic SWF Flash games with Ruffle wrappers |

---

## 9. Performance and Memory Management Guardrails

1. **Memory Clean-Up on Page Navigation**:
   WebGL and WASM games consume 300MB to 1.2GB of RAM. When the user navigates away from a game or closes the player widget, the application must load `about:blank` on the `QWebEngineView` and delete the page reference to allow Chromium to garbage collect the WebAssembly heap.
2. **Persistent Game Saves**:
   HTML5 games save high scores and checkpoints in `window.localStorage` and `IndexedDB`. By assigning a persistent storage path to `QWebEngineProfile.defaultProfile().setPersistentStoragePath(...)`, player save states survive across application restarts.
3. **Sound Control**:
   `QWebEnginePage` provides `setAudioMuted(bool)` to allow muting background game music from the EntertainX media control panel.
