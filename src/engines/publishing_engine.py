from __future__ import annotations


class PublishingEngine:
    def execute(self, context: dict) -> dict:
        return {
            "title": context["topic"],
            "description": "",
            "hashtags": [],
            "platforms": ["youtube_shorts", "tiktok"],
            "publishing_status": "completed",
        }
