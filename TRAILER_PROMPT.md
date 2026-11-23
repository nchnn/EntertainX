# Feature Prompt: Zero-Branding Video Trailer Embeds

Use the prompt below to implement zero-branding background trailers for hover cards, hero banners, and detail modals.

***

```markdown
Implement a seamless, zero-branding trailer preview component for movie and TV detail modals and hover cards.

### 1. TMDB Trailer Resolver
- Query TMDB for videos using GET /movie/{id}/videos or GET /tv/{id}/videos (or append_to_response=videos).
- Filter the results array using this exact priority:
  1. site === "YouTube" AND type === "Trailer" AND official === true (prefer size >= 1080)
  2. site === "YouTube" AND type === "Trailer"
  3. site === "YouTube" AND (type === "Teaser" OR type === "Clip")
- Extract the 11-character YouTube video key. If none exists, gracefully fall back to displaying the title backdrop image.

### 2. Embed URL Configuration
Build the YouTube embed URL with these query parameters to strip native player chrome and enable autoplay:
https://www.youtube-nocookie.com/embed/{KEY}?autoplay=1&mute=1&controls=0&rel=0&modestbranding=1&playsinline=1&enablejsapi=1&iv_load_policy=3&cc_load_policy=0

### 3. Visual Crop and Anti-Branding Styling (Scale-Crop Technique)
YouTube watermarks, channel titles, and overlays cannot be disabled via API alone. Strip them visually using CSS container clipping:
- Parent Container: Set fixed aspect ratio (16:9), position: relative, and overflow: hidden.
- Iframe / Web View:
  - position: absolute; inset: 0; width: 100%; height: 100%;
  - transform: scale(1.5); transform-origin: center center; (crops the top title bar and bottom-right YouTube watermark completely out of view)
  - pointer-events: none; (blocks hover detection so YouTube controls and share buttons never appear)
- Overlays: Place subtle bottom and edge gradients over the container to blend the video smoothly into the dark interface.

### 4. Player Controls and UX
- Backdrop Fallback: Render the high-resolution backdrop image underneath the video. Keep the iframe opacity at 0 until the video starts playing, then crossfade smoothly.
- Custom Controls: Provide an overlay container with pointer-events: auto hosting native app buttons:
  - Audio toggle (mute/unmute via postMessage iframe command {"event":"command","func":"unMute"})
  - Replay button
- Lifecycle: Pause or destroy the player instance immediately when the modal or preview card closes to avoid background resource and network leaks.
```
