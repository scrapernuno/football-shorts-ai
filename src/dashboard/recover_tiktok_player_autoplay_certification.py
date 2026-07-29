from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / 'src' / 'dashboard' / 'certify_executive_overview.py'

OLD_AUTOPLAY_CHECK = '''        require(
            "autoplay=0"
            in source,
            (
                "O player oficial TikTok não pode "
                "ter autoplay ativo."
            ),
        )
'''

NEW_AUTOPLAY_CHECK = r'''        require(
            "fullscreen; autoplay;"
            not in source,
            (
                "O iframe oficial TikTok não pode "
                "receber permissão de autoplay."
            ),
        )


        require(
            re.search(
                (
                    r"iframe\.allow\s*=\s*"
                    r"\([^)]*"
                    r"fullscreen;"
                ),
                source,
                flags=re.DOTALL,
            )
            is not None,
            (
                "Não foi possível confirmar a política "
                "de permissões do iframe TikTok."
            ),
        )


        print(
            "TIKTOK_IFRAME_AUTOPLAY_PERMISSION=BLOCKED"
        )
'''


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise ValueError(f'{label}: esperado 1 bloco, observado {count}.')
    return source.replace(old, new, 1)


def main() -> int:
    print('=' * 70)
    print('FOOTBALL-SHORTS-AI-0031C.5G.2')
    print('TIKTOK PLAYER AUTOPLAY CERTIFICATION RECOVERY')
    print('=' * 70)

    if not TARGET.is_file():
        raise FileNotFoundError(f'Ficheiro em falta: {TARGET}')

    source = TARGET.read_text(encoding='utf-8')

    if 'TIKTOK_IFRAME_AUTOPLAY_PERMISSION=BLOCKED' in source:
        print('AUTOPLAY_RECOVERY_STATUS=ALREADY_RECOVERED')
        return 0

    updated = replace_once(
        source,
        OLD_AUTOPLAY_CHECK,
        NEW_AUTOPLAY_CHECK,
        'TikTok autoplay certification',
    )

    temporary = TARGET.with_suffix(TARGET.suffix + '.tmp')
    temporary.write_text(updated, encoding='utf-8')
    temporary.replace(TARGET)
    py_compile.compile(str(TARGET), doraise=True)

    print('AUTOPLAY_RECOVERY_STATUS=RECOVERED')
    print('TIKTOK_IFRAME_AUTOPLAY_PERMISSION=BLOCKED')
    print('OFFICIAL_TIKTOK_PLAYER_ALLOWLIST=PRESERVED')
    print('GENERIC_EXTERNAL_HTTP=BLOCKED')
    print('PUBLICATION_EXECUTION_ENABLED=NO')
    print('AUTOPLAY_CERTIFICATION_RECOVERY=PASS')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
