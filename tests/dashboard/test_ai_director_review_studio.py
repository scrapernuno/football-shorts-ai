from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / "dashboard" / "ai-director-review.html"
CSS = ROOT / "dashboard" / "assets" / "ai-director-review.css"
JS = ROOT / "dashboard" / "assets" / "ai-director-review.js"
DATA = ROOT / "dashboard" / "data" / "ai_director_review_package.json"


def test_ai_director_review_assets_exist():
    for path in (HTML, CSS, JS, DATA):
        assert path.is_file(), path


def test_dashboard_supports_variant_comparison_timeline_and_human_review():
    html = HTML.read_text(encoding="utf-8")
    for marker in (
        "AI Director Review Studio",
        'id="variantGrid"',
        'id="timeline"',
        'data-decision="approved"',
        'data-decision="changes_requested"',
        'data-decision="rejected"',
        'id="exportButton"',
    ):
        assert marker in html


def test_review_script_is_fail_closed_and_does_not_operate_media():
    script = JS.read_text(encoding="utf-8")
    assert "football-shorts-ai.ai-director-review.v1" in script
    assert "football-shorts-ai.ai-director-human-review.v1" in script
    assert "factory_handover_requested" in script
    assert "extraction_enabled: false" in script
    assert "render_enabled: false" in script
    assert "auto_publish: false" in script
    assert "ffmpeg" not in script.lower()
    assert "youtube.upload" not in script.lower()


def test_initial_package_is_blocked_until_real_evidence_and_approval():
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    assert payload["schema"] == "football-shorts-ai.ai-director-review.v1"
    assert payload["director_state"] == "blocked"
    assert payload["handover_state"] == "blocked"
    assert payload["recommended_variant_id"] is None
    assert payload["variants"] == []
    assert "AI_DIRECTOR_EVIDENCE_MISSING" in payload["blockers"]
    assert "HUMAN_APPROVAL_REQUIRED" in payload["blockers"]
    assert payload["network_enabled"] is False
    assert payload["acquisition_enabled"] is False
    assert payload["extraction_enabled"] is False
    assert payload["render_enabled"] is False
    assert payload["auto_publish"] is False


def test_review_page_loads_exact_dashboard_assets():
    html = HTML.read_text(encoding="utf-8")
    assert 'href="assets/ai-director-review.css"' in html
    assert 'src="assets/ai-director-review.js"' in html
    script = JS.read_text(encoding="utf-8")
    assert "data/ai_director_review_package.json" in script
