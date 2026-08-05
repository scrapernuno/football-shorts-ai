"""FOOTBALL-SHORTS-AI-0062C — static operational certification for 0062A–0062C."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


REQUIRED = (
    "src/publishing/controlled_visibility_execution.py",
    "src/publishing/youtube_visibility_oauth_adapter.py",
    "src/publishing/run_controlled_visibility_execution.py",
    "src/publishing/publication_result_intake.py",
    "tests/publishing/test_controlled_visibility_execution.py",
    "tests/publishing/test_youtube_visibility_oauth_adapter.py",
    "tests/publishing/test_publication_result_intake.py",
    "dashboard/youtube-publication-result.html",
    "dashboard/assets/youtube-publication-result.js",
    "dashboard/data/youtube_publication_result.json",
    ".github/workflows/controlled-visibility-execution.yml",
)


@dataclass(frozen=True)
class PublicationExecutionCertification:
    schema: str
    certification_id: str
    status: str
    files: tuple[tuple[str, str], ...]
    blockers: tuple[str, ...]
    automatic_publication_enabled: bool = False
    credentials_persisted: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "certification_id": self.certification_id,
            "status": self.status,
            "files": [{"path": path, "sha256": digest} for path, digest in self.files],
            "blockers": list(self.blockers),
            "automatic_publication_enabled": False,
            "credentials_persisted": False,
        }


def certify(root: Path) -> PublicationExecutionCertification:
    blockers: list[str] = []
    files: list[tuple[str, str]] = []
    for relative in REQUIRED:
        path = root / relative
        if not path.is_file():
            blockers.append(f"MISSING:{relative}")
            continue
        files.append((relative, hashlib.sha256(path.read_bytes()).hexdigest()))

    forbidden = {
        "src/publishing/controlled_visibility_execution.py": ("auto_publish=True", "credentials_persisted=True"),
        "src/publishing/publication_result_intake.py": ("auto_publish=True", "network_used_by_intake=True"),
    }
    for relative, phrases in forbidden.items():
        path = root / relative
        if not path.is_file():
            continue
        source = path.read_text(encoding="utf-8")
        for phrase in phrases:
            if phrase in source:
                blockers.append(f"FORBIDDEN_CAPABILITY:{relative}:{phrase}")

    evidence = {"files": files, "blockers": sorted(blockers)}
    digest = hashlib.sha256(json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return PublicationExecutionCertification(
        schema="football-shorts-ai.publication-execution-certification.v1",
        certification_id=f"YTPUBCERT-{digest[:20].upper()}",
        status="CERTIFIED" if not blockers else "BLOCKED",
        files=tuple(files), blockers=tuple(sorted(blockers)),
    )


if __name__ == "__main__":
    result = certify(Path.cwd())
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    raise SystemExit(0 if result.status == "CERTIFIED" else 1)
