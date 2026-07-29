from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "src" / "dashboard" / "certify_executive_overview.py"

OLD_FORBIDDEN_PATTERNS = r"""FORBIDDEN_JAVASCRIPT_PATTERNS = {
    "EXTERNAL_HTTP": r"https?://",
    "WEBSOCKET": r"\bWebSocket\s*\(",
    "LOCAL_STORAGE": r"\blocalStorage\b",
    "SESSION_STORAGE": r"\bsessionStorage\b",
    "INDEXED_DB": r"\bindexedDB\b",
    "DOCUMENT_COOKIE": r"\bdocument\.cookie\b",
}
"""

NEW_FORBIDDEN_PATTERNS = r"""FORBIDDEN_JAVASCRIPT_PATTERNS = {
    "WEBSOCKET": r"\bWebSocket\s*\(",
    "LOCAL_STORAGE": r"\blocalStorage\b",
    "SESSION_STORAGE": r"\bsessionStorage\b",
    "INDEXED_DB": r"\bindexedDB\b",
    "DOCUMENT_COOKIE": r"\bdocument\.cookie\b",
}

ALLOWED_EXTERNAL_JAVASCRIPT_URLS = frozenset({
    "https://www.tiktok.com",
})

ALLOWED_EXTERNAL_JAVASCRIPT_PREFIXES = (
    "https://www.tiktok.com/player/v1/",
)

REQUIRED_TIKTOK_PLAYER_MARKERS = frozenset({
    "FOOTBALL-SHORTS-AI-0031C.5G",
    "renderTikTokViralReferenceReview",
    "activateTikTokReferenceButton",
    "https://www.tiktok.com/player/v1/",
})
"""

OLD_VALIDATION = r"""    forbidden_matches = sorted(
        name
        for name, pattern
        in FORBIDDEN_JAVASCRIPT_PATTERNS.items()
        if re.search(
            pattern,
            source,
            flags=re.IGNORECASE,
        )
        is not None
    )


    require(
        not forbidden_matches,
        (
            "dashboard.js contém "
            "capacidades externas ou "
            "persistentes proibidas: "
            f"{forbidden_matches}"
        ),
    )
"""

NEW_VALIDATION = r"""    external_urls = sorted(
        set(
            re.findall(
                r"https?://[^\s\"'`<>)}]+",
                source,
                flags=re.IGNORECASE,
            )
        )
    )


    unauthorized_external_urls = sorted(
        url
        for url in external_urls
        if (
            url not in ALLOWED_EXTERNAL_JAVASCRIPT_URLS
            and not any(
                url.startswith(prefix)
                for prefix in ALLOWED_EXTERNAL_JAVASCRIPT_PREFIXES
            )
        )
    )


    require(
        not unauthorized_external_urls,
        (
            "dashboard.js contém URLs externos não autorizados: "
            f"{unauthorized_external_urls}"
        ),
    )


    tiktok_player_present = any(
        url.startswith("https://www.tiktok.com/player/v1/")
        for url in external_urls
    )


    if tiktok_player_present:
        missing_tiktok_player_markers = sorted(
            marker
            for marker in REQUIRED_TIKTOK_PLAYER_MARKERS
            if marker not in source
        )

        require(
            not missing_tiktok_player_markers,
            (
                "O player oficial TikTok perdeu marcadores governados: "
                f"{missing_tiktok_player_markers}"
            ),
        )

        require(
            "autoplay=0" in source,
            "O player oficial TikTok não pode ter autoplay ativo.",
        )


    forbidden_matches = sorted(
        name
        for name, pattern
        in FORBIDDEN_JAVASCRIPT_PATTERNS.items()
        if re.search(
            pattern,
            source,
            flags=re.IGNORECASE,
        )
        is not None
    )


    require(
        not forbidden_matches,
        (
            "dashboard.js contém capacidades persistentes ou canais "
            "externos proibidos: "
            f"{forbidden_matches}"
        ),
    )


    print(f"EXTERNAL_URL_COUNT={len(external_urls)}")
    print(
        "UNAUTHORIZED_EXTERNAL_URL_COUNT="
        f"{len(unauthorized_external_urls)}"
    )
    print(
        "OFFICIAL_TIKTOK_PLAYER_ALLOWED="
        f"{'YES' if tiktok_player_present else 'NOT_PRESENT'}"
    )
"""

OLD_HEADER = """    print(
        "NO EXTERNAL API"
    )
"""

NEW_HEADER = """    print(
        "NO EXTERNAL API"
    )

    print(
        "OFFICIAL TIKTOK PLAYER ALLOWLISTED "
        "FOR INTERNAL REVIEW ONLY"
    )
"""


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise ValueError(f"{label}: esperado 1 bloco, observado {count}.")
    return source.replace(old, new, 1)


def main() -> int:
    print('=' * 70)
    print('FOOTBALL-SHORTS-AI-0031C.5G.1')
    print('EXECUTIVE OVERVIEW TIKTOK PLAYER AUTHORITY RECOVERY')
    print('=' * 70)

    if not TARGET.is_file():
        raise FileNotFoundError(f"Ficheiro em falta: {TARGET}")

    source = TARGET.read_text(encoding='utf-8')

    if 'ALLOWED_EXTERNAL_JAVASCRIPT_URLS' in source:
        print('RECOVERY_STATUS=ALREADY_RECOVERED')
        return 0

    updated = replace_once(
        source,
        OLD_FORBIDDEN_PATTERNS,
        NEW_FORBIDDEN_PATTERNS,
        'FORBIDDEN_JAVASCRIPT_PATTERNS',
    )
    updated = replace_once(
        updated,
        OLD_VALIDATION,
        NEW_VALIDATION,
        'forbidden validation',
    )
    updated = replace_once(
        updated,
        OLD_HEADER,
        NEW_HEADER,
        'certification header',
    )

    temporary = TARGET.with_suffix(TARGET.suffix + '.tmp')
    temporary.write_text(updated, encoding='utf-8')
    temporary.replace(TARGET)
    py_compile.compile(str(TARGET), doraise=True)

    print('RECOVERY_STATUS=RECOVERED')
    print('OFFICIAL_TIKTOK_PLAYER_ALLOWLIST=YES')
    print('GENERIC_EXTERNAL_HTTP=BLOCKED')
    print('PERSISTENT_BROWSER_STORAGE=BLOCKED')
    print('PUBLICATION_EXECUTION_ENABLED=NO')
    print('CERTIFICATION_AUTHORITY_RECOVERY=PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
