from __future__ import annotations

import json
from pathlib import Path

from engines.research_engine import ResearchEngine
from engines.story_engine import StoryEngine
from engines.production_engine import ProductionEngine
from engines.publishing_engine import PublishingEngine


OUTPUT = Path("output")


def write_package(name: str, payload: dict) -> None:
    OUTPUT.mkdir(exist_ok=True)
    (OUTPUT / name).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def execute(topic: str) -> dict:
    context = {"topic": topic}

    research = ResearchEngine().execute(context)
    context["research"] = research
    write_package("research_package.json", research)

    story = StoryEngine().execute(context)
    context["story"] = story
    write_package("story_package.json", story)

    production = ProductionEngine().execute(context)
    context["production"] = production
    write_package("production_package.json", production)

    publishing = PublishingEngine().execute(context)
    context["publishing"] = publishing
    write_package("publishing_package.json", publishing)

    context["status"] = "COMPLETED"
    return context


if __name__ == "__main__":
    result = execute("football short demo")
    print(json.dumps(result, indent=2, ensure_ascii=False))
