from __future__ import annotations


class StoryEngine:
    def execute(self, context: dict) -> dict:
        return {
            "hook": f"{context['topic']}: the story begins",
            "script": [],
            "duration_target": "30s",
            "story_status": "completed",
        }
