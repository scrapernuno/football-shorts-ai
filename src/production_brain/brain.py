from __future__ import annotations


def execute(topic: str) -> dict:
    return {
        "topic": topic,
        "pipeline": [
            "research",
            "story",
            "production",
            "publishing",
        ],
        "status": "READY_FOR_ENGINE_IMPLEMENTATION",
    }


if __name__ == "__main__":
    print(execute("football short demo"))
