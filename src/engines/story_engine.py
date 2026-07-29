from __future__ import annotations


class StoryEngine:
    def execute(self, context: dict) -> dict:
        topic = context["topic"]
        return {
            "hook": f"{topic}: the football story everyone is discussing",
            "scenes": [
                "attention hook",
                "key fact reveal",
                "debate moment",
                "community question",
            ],
            "script": [
                f"What is really happening with {topic}?",
                "The next seconds reveal the key details.",
            ],
            "duration_target": "45s",
            "cta": "What is your opinion?",
            "story_status": "completed",
        }
