"""
FOOTBALL-SHORTS-AI-0050E
DASHBOARD VIDEO PROMOTION

Promotes the first rendered video asset into the dashboard library.
No automatic publishing.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DashboardPromotion:
    video_id: str
    dashboard_status: str
    player_enabled: bool
    auto_publish: bool = False


def promote_first_video(video_id: str = "VID-0001") -> DashboardPromotion:
    if not video_id:
        raise ValueError("video_id_required")

    return DashboardPromotion(
        video_id=video_id,
        dashboard_status="READY",
        player_enabled=True,
        auto_publish=False,
    )


if __name__ == "__main__":
    result = promote_first_video()
    print(result)
