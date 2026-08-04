from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / "dashboard" / "publishing-handover.html"
JS = ROOT / "dashboard" / "assets" / "publishing-handover.js"


def test_publishing_handover_page_contains_final_video_and_human_gate():
    text = HTML.read_text(encoding="utf-8")
    assert '<video id="finalVideo"' in text
    assert 'data-decision="approved"' in text
    assert 'data-decision="changes_requested"' in text
    assert 'data-decision="rejected"' in text
    assert 'id="exportButton"' in text


def test_publishing_handover_controller_is_fail_closed():
    text = JS.read_text(encoding="utf-8")
    assert "review_state === 'ready_for_review'" in text
    assert "upload_enabled: false" in text
    assert "publish_enabled: false" in text
    assert "auto_publish: false" in text
    assert "network_enabled: false" in text
    assert "human_render_review_handover.json" in text


def test_dashboard_studio_does_not_call_upload_or_publish_apis():
    text = JS.read_text(encoding="utf-8")
    forbidden = ("youtube.upload", "videos.insert", "fetch('https://", 'fetch("https://', "autoPublish()")
    assert not any(token in text for token in forbidden)
