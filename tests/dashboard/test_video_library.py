from __future__ import annotations

from dashboard.certify_video_library import load_video_library


def test_dashboard_video_library_is_governed() -> None:
    library = load_video_library()

    assert library.schema_version == "1.0"
    assert library.generated_at
    assert len(library.videos) >= 1


def test_dashboard_video_ids_are_unique() -> None:
    library = load_video_library()
    video_ids = [video.video_id for video in library.videos]

    assert len(video_ids) == len(set(video_ids))


def test_initial_dashboard_video_is_vertical_and_ready() -> None:
    library = load_video_library()
    video = library.videos[0]

    assert video.status == "ready"
    assert video.orientation == "vertical"
    assert video.width == 1080
    assert video.height == 1920
    assert video.video_file is not None
    assert video.video_file.path == "videos/VID-000001.mp4"
    assert video.video_file.container == "mp4"
    assert video.video_file.mime_type == "video/mp4"
    assert video.thumbnail_path == "videos/VID-000001.jpg"
    assert video.subtitles_path == "videos/VID-000001.vtt"
    assert video.render_engine == "ffmpeg"
