from __future__ import annotations


class ProductionEngine:
    def execute(self, context: dict) -> dict:
        topic = str(context["topic"]).strip()
        story = context.get("story", {})
        story_scenes = story.get("scenes", [])

        scenes = []
        visual_prompts = []

        for index, scene in enumerate(story_scenes, start=1):
            scene_id = f"scene_{index:02d}"
            screen_text = scene.get("text", topic)
            narration = scene.get("narration", screen_text)
            start_second = scene.get("start_second", (index - 1) * 8)
            end_second = scene.get("end_second", start_second + 8)
            visual_prompt = (
                f"Vertical 9:16 football editorial visual for '{topic}', "
                f"scene {index}, cinematic stadium atmosphere, dynamic motion, "
                f"clear subject separation, no logos, no watermarks"
            )

            scenes.append(
                {
                    "scene_id": scene_id,
                    "start_second": start_second,
                    "end_second": end_second,
                    "screen_text": screen_text,
                    "narration": narration,
                    "visual_prompt": visual_prompt,
                    "transition": "fast_cut" if index > 1 else "cold_open",
                }
            )
            visual_prompts.append(visual_prompt)

        if not scenes:
            fallback_prompt = (
                f"Vertical 9:16 football editorial visual for '{topic}', "
                "cinematic stadium atmosphere, dynamic action, no logos, no watermarks"
            )
            scenes = [
                {
                    "scene_id": "scene_01",
                    "start_second": 0,
                    "end_second": 8,
                    "screen_text": topic,
                    "narration": topic,
                    "visual_prompt": fallback_prompt,
                    "transition": "cold_open",
                }
            ]
            visual_prompts = [fallback_prompt]

        return {
            "topic": topic,
            "format": "vertical_9_16",
            "resolution": "1080x1920",
            "duration_target": story.get("duration_target", "45s"),
            "scenes": scenes,
            "video_structure": scenes,
            "visual_prompts": visual_prompts,
            "caption_style": "viral_shorts",
            "audio_guidance": {
                "voiceover": "energetic_editorial",
                "music": "high_energy_sports_bed",
                "ducking": True,
            },
            "production_status": "completed",
        }
