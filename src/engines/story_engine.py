from __future__ import annotations


class StoryEngine:
    def execute(self, context: dict) -> dict:
        topic = str(context["topic"]).strip()
        research = context.get("research", {})
        facts = research.get("facts", [])

        key_fact = facts[0] if facts else f"{topic} is the selected football topic."
        hook = f"What is really happening with {topic}?"

        scenes = [
            {
                "scene_id": "scene_01",
                "start_second": 0,
                "end_second": 4,
                "text": hook,
                "narration": hook,
                "purpose": "attention_hook",
            },
            {
                "scene_id": "scene_02",
                "start_second": 4,
                "end_second": 15,
                "text": "Here is the key detail",
                "narration": str(key_fact),
                "purpose": "key_fact_reveal",
            },
            {
                "scene_id": "scene_03",
                "start_second": 15,
                "end_second": 32,
                "text": "Why football fans are debating it",
                "narration": (
                    f"The story around {topic} creates a clear debate and gives fans "
                    "more than one possible interpretation."
                ),
                "purpose": "debate_moment",
            },
            {
                "scene_id": "scene_04",
                "start_second": 32,
                "end_second": 45,
                "text": "What is your opinion?",
                "narration": f"What do you think about {topic}? Tell us in the comments.",
                "purpose": "community_question",
            },
        ]

        return {
            "topic": topic,
            "hook": hook,
            "scenes": scenes,
            "script": [scene["narration"] for scene in scenes],
            "duration_target": "45s",
            "cta": "What is your opinion?",
            "story_status": "completed",
        }
