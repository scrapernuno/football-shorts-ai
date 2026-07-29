from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HTML_FILE = ROOT / "dashboard" / "videos.html"
JAVASCRIPT_FILE = ROOT / "dashboard" / "assets" / "video-library.js"
STYLESHEET_FILE = ROOT / "dashboard" / "assets" / "video-library.css"
LIBRARY_FILE = ROOT / "dashboard" / "data" / "video_library.json"


REQUIRED_HTML_TOKENS = {
    'id="video-list"',
    'id="video-player"',
    'id="video-search"',
    'id="video-status-filter"',
    'assets/video-library.css',
    'assets/video-library.js',
}

REQUIRED_JAVASCRIPT_TOKENS = {
    'data/video_library.json',
    'function validateLibrary',
    'function renderList',
    'function selectVideo',
    'document.createElement("source")',
    'document.createElement("track")',
    'video_file',
    'mime_type',
}

REQUIRED_CSS_TOKENS = {
    '.video-card',
    '.player-shell',
    '.player-panel',
    '@media (max-width: 960px)',
}


def require_file(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")
    return path.read_text(encoding="utf-8")


def require_tokens(source: str, tokens: set[str], label: str) -> None:
    missing = sorted(token for token in tokens if token not in source)
    if missing:
        raise ValueError(f"{label} missing required tokens: {missing}")


def main() -> int:
    print("=" * 72)
    print("FOOTBALL-SHORTS-AI-0044D")
    print("GOVERNED DASHBOARD VIDEO PLAYER CERTIFICATION")
    print("=" * 72)

    html = require_file(HTML_FILE)
    javascript = require_file(JAVASCRIPT_FILE)
    stylesheet = require_file(STYLESHEET_FILE)
    require_file(LIBRARY_FILE)

    require_tokens(html, REQUIRED_HTML_TOKENS, "HTML")
    require_tokens(javascript, REQUIRED_JAVASCRIPT_TOKENS, "JavaScript")
    require_tokens(stylesheet, REQUIRED_CSS_TOKENS, "CSS")

    print(f"HTML_FILE={HTML_FILE}")
    print(f"JAVASCRIPT_FILE={JAVASCRIPT_FILE}")
    print(f"STYLESHEET_FILE={STYLESHEET_FILE}")
    print(f"LIBRARY_FILE={LIBRARY_FILE}")
    print("VIDEO_LIBRARY_UI_STATUS=PASS")
    print("HTML5_PLAYER_BINDING_STATUS=PASS")
    print("RESPONSIVE_LAYOUT_STATUS=PASS")
    print("FOOTBALL_SHORTS_AI_0044D_STATUS=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
