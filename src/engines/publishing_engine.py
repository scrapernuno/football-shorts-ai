from __future__ import annotations

import re


class PublishingEngine:
    def execute(self, context: dict) -> dict:
        topic = str(context["topic"]).strip()
        story = context.get("story", {})
        hook = str(story.get("hook", topic)).strip()

        normalized_words = re.findall(r"[A-Za-zÀ-ÿ0-9]+", topic)
        topic_tags = [f"#{word.lower()}" for word in normalized_words[:3] if len(word) > 2]

        hashtags = []
        for tag in ["#football", "#shorts", "#futebol", *topic_tags]:
            if tag not in hashtags:
                hashtags.append(tag)

        title = hook.rstrip(".!?")
        if len(title) > 70:
            title = f"{title[:67].rstrip()}..."

        description = (
            f"{hook}\n\n"
            "Um resumo rápido, direto e preparado para vídeo vertical. "
            "Comenta a tua opinião e segue para mais histórias de futebol."
        )

        return {
            "topic": topic,
            "title": title,
            "description": description,
            "hashtags": hashtags,
            "platforms": ["youtube_shorts", "tiktok"],
            "metadata": {
                "language": "pt-PT",
                "category": "sports",
                "content_type": "short_form_video",
                "made_for_kids": False,
            },
            "publishing_plan": {
                "youtube_shorts": {
                    "title": title,
                    "description": description,
                    "hashtags": hashtags,
                },
                "tiktok": {
                    "caption": f"{title} {' '.join(hashtags)}",
                    "hashtags": hashtags,
                },
            },
            "publishing_status": "completed",
        }
