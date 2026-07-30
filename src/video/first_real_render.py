"""
FOOTBALL-SHORTS-AI-0050D
FIRST REAL FFMPEG RENDER

Governed render activation contract for VID-0001.
No automatic publishing.
No external platform execution.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RenderRequest:
    video_id: str
    production_id: str
    format: str = "vertical_9_16"
    resolution: str = "1080x1920"
    status: str = "READY"


@dataclass(frozen=True)
class RenderResult:
    video_id: str
    status: str
    mp4: str
    thumbnail: str
    subtitles: str
    auto_publish: bool = False


def create_render_request() -> RenderRequest:
    return RenderRequest(
        video_id="VID-0001",
        production_id="PRODUCTION-0001",
    )


def validate_render_request(request: RenderRequest) -> bool:
    return (
        request.video_id == "VID-0001"
        and request.production_id == "PRODUCTION-0001"
        and request.format == "vertical_9_16"
        and request.resolution == "1080x1920"
    )


__all__ = [
    "RenderRequest",
    "RenderResult",
    "create_render_request",
    "validate_render_request",
]
