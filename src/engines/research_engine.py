from __future__ import annotations


class ResearchEngine:
    def execute(self, context: dict) -> dict:
        return {
            "topic": context["topic"],
            "facts": [],
            "sources": [],
            "research_status": "completed",
        }
