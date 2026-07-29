from __future__ import annotations

import json
import tempfile
from pathlib import Path

from production_brain import brain


EXPECTED_PACKAGES = {
    "research_package.json": "research_status",
    "story_package.json": "story_status",
    "production_package.json": "production_status",
    "publishing_package.json": "publishing_status",
}


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="football-shorts-ai-0041a-") as tmp:
        output_dir = Path(tmp) / "output"
        original_output = brain.OUTPUT
        brain.OUTPUT = output_dir

        try:
            result = brain.execute("football short certification demo")
        finally:
            brain.OUTPUT = original_output

        if result.get("status") != "COMPLETED":
            raise SystemExit("CERTIFICATION_FAILED: pipeline did not complete")

        for package_name, status_key in EXPECTED_PACKAGES.items():
            package_path = output_dir / package_name
            if not package_path.is_file():
                raise SystemExit(
                    f"CERTIFICATION_FAILED: missing package {package_name}"
                )

            payload = json.loads(package_path.read_text(encoding="utf-8"))
            if payload.get(status_key) != "completed":
                raise SystemExit(
                    f"CERTIFICATION_FAILED: invalid status in {package_name}"
                )

        publishing = result.get("publishing", {})
        if publishing.get("publishing_status") != "completed":
            raise SystemExit("CERTIFICATION_FAILED: publishing package incomplete")

        print("FOOTBALL-SHORTS-AI-0041A.1: CERTIFIED")
        print("PIPELINE_STATUS: COMPLETED")
        print("PACKAGES_GENERATED: 4")
        print("EXTERNAL_API_ACCESS: NOT REQUIRED")
        print("REAL_PUBLICATION: NOT EXECUTED")
        print("NEXT_AUTHORISED_STEP: REAL_CONTENT_GENERATION")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
