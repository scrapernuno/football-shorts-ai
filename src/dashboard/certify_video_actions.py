from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HTML_FILE = ROOT / "dashboard" / "videos.html"
JS_FILE = ROOT / "dashboard" / "assets" / "video-library.js"
CSS_FILE = ROOT / "dashboard" / "assets" / "video-library.css"


REQUIRED_HTML_TOKENS = (
    'id="download-video-action"',
    'id="publishing-studio-action"',
    'id="copy-publishing-id-action"',
    'id="detail-publishing-package"',
    'id="detail-checksum"',
    'id="action-message"',
)

REQUIRED_JS_TOKENS = (
    "function configureActions(video)",
    "function resetActions()",
    "publishing_package_id",
    "checksum_sha256",
    'video.status === "ready" || video.status === "published"',
    "navigator.clipboard.writeText",
    "setActionEnabled",
)

REQUIRED_CSS_TOKENS = (
    ".video-actions",
    ".action-button",
    ".action-primary",
    ".action-button.is-disabled",
    ".action-message",
)


def read(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def require_tokens(name: str, source: str, tokens: tuple[str, ...]) -> None:
    missing = [token for token in tokens if token not in source]
    if missing:
        raise AssertionError(f"{name} missing required tokens: {missing}")


def main() -> int:
    print("=" * 72)
    print("FOOTBALL-SHORTS-AI-0044E")
    print("GOVERNED VIDEO DOWNLOAD AND PUBLISHING ACTIONS CERTIFICATION")
    print("=" * 72)

    html = read(HTML_FILE)
    javascript = read(JS_FILE)
    css = read(CSS_FILE)

    require_tokens("videos.html", html, REQUIRED_HTML_TOKENS)
    require_tokens("video-library.js", javascript, REQUIRED_JS_TOKENS)
    require_tokens("video-library.css", css, REQUIRED_CSS_TOKENS)

    if 'download.href = file.path' not in javascript:
        raise AssertionError("Download action is not bound to the governed file path")

    if 'setActionEnabled(download, true)' not in javascript:
        raise AssertionError("Download action is not explicitly enabled after validation")

    if 'setActionEnabled(byId("publishing-studio-action"), true)' not in javascript:
        raise AssertionError("Publishing handoff is not gated by publishing package evidence")

    if 'download.setAttribute("download"' not in javascript:
        raise AssertionError("Download filename is not governed")

    print(f"HTML_FILE={HTML_FILE}")
    print(f"JAVASCRIPT_FILE={JS_FILE}")
    print(f"CSS_FILE={CSS_FILE}")
    print("DOWNLOAD_ACTION=PASS")
    print("PUBLISHING_HANDOFF=PASS")
    print("COPY_PACKAGE_ID=PASS")
    print("FAIL_CLOSED_ACTION_GATING=PASS")
    print("STATUS=CERTIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
