from __future__ import annotations

import json

from editorial.parser import (
    parse_editorial_package_dict,
    serialize_editorial_package,
)


def build_asset(
    description: str,
    query: str,
) -> dict[str, object]:
    return {
        "asset_type": "video",
        "description": description,
        "search_queries": [
            query,
            f"{query} football",
        ],
        "preferred_source": "Arquivo próprio ou fonte licenciada",
        "fallback_description": (
            "Utilizar vídeo genérico de estádio, adeptos ou treino."
        ),
        "copyright_note": (
            "Confirmar direitos de utilização antes da publicação."
        ),
    }


def build_scene(
    *,
    scene_number: int,
    start_second: int,
    end_second: int,
    voiceover: str,
    subtitle: str,
    visual_description: str,
    search_query: str,
) -> dict[str, object]:
    return {
        "scene_number": scene_number,
        "start_second": start_second,
        "end_second": end_second,
        "voiceover": voiceover,
        "subtitle": subtitle,
        "visual_type": "video",
        "visual_description": visual_description,
        "editing_pace": "fast",
        "transition": "cut",
        "subtitle_style": "large_center",
        "camera_movement": "zoom_in",
        "sound_effect": "whoosh",
        "asset": build_asset(
            visual_description,
            search_query,
        ),
    }


def build_topic(
    *,
    priority: int,
    topic_id: str,
    title: str,
    player: str,
    club: str,
    source_url: str,
    viral_probability: int,
) -> dict[str, object]:
    return {
        "topic_id": topic_id,
        "ranking": {
            "priority": priority,
            "viral_probability": viral_probability,
            "competition": "HIGH",
            "breaking": priority == 1,
            "publish_today": True,
            "reason": (
                f"O tema envolve {player}, {club} e tem forte "
                "potencial de comentários e partilhas."
            ),
        },
        "source": {
            "title": title,
            "name": "Fonte de teste",
            "url": source_url,
            "published": "2026-07-27T12:00:00+00:00",
            "confirmation_status": "REPORTED",
        },
        "editorial": {
            "primary_title": title,
            "alternative_titles": [
                {
                    "text": f"{player} pode mudar tudo?",
                    "score": 96,
                },
                {
                    "text": f"A bomba que envolve {club}",
                    "score": 92,
                },
                {
                    "text": f"O futuro de {player}",
                    "score": 89,
                },
            ],
            "primary_hook": (
                f"Espera… {player} pode mesmo ir para o {club}?"
            ),
            "alternative_hooks": [
                {
                    "text": (
                        f"O {club} acabou de surpreender toda a gente."
                    ),
                    "score": 95,
                },
                {
                    "text": (
                        f"Esta notícia sobre {player} pode mudar tudo."
                    ),
                    "score": 92,
                },
                {
                    "text": (
                        f"Ninguém esperava este movimento do {club}."
                    ),
                    "score": 90,
                },
            ],
            "script": (
                f"Segundo a fonte indicada, o {club} está associado "
                f"a um possível movimento por {player}. "
                "A informação ainda deve ser confirmada, mas o tema "
                "já está a gerar grande interesse. "
                "O impacto seria enorme para o jogador, para o clube "
                "e para o mercado. "
                "A grande questão é simples: esta operação faz sentido? "
                "Deixa a tua opinião nos comentários."
            ),
            "call_to_action": (
                f"Tu colocarias {player} no {club}? Comenta agora."
            ),
            "pinned_comment": (
                f"{player} no {club}: sim ou não? 👇"
            ),
            "description": (
                f"Análise rápida sobre o possível futuro de {player} "
                f"e o interesse do {club}."
            ),
            "hashtags": [
                "#football",
                "#shorts",
                "#futebol",
                "#transferencias",
                "#viral",
            ],
        },
        "storyboard": {
            "estimated_duration_seconds": 45,
            "required_clip_count": 5,
            "scenes": [
                build_scene(
                    scene_number=1,
                    start_second=0,
                    end_second=3,
                    voiceover=(
                        f"Espera… {player} pode mesmo ir para o {club}?"
                    ),
                    subtitle=f"{player} NO {club}?",
                    visual_description=(
                        f"Close-up de {player} a celebrar"
                    ),
                    search_query=f"{player} celebration",
                ),
                build_scene(
                    scene_number=2,
                    start_second=3,
                    end_second=10,
                    voiceover=(
                        "A notícia surgiu e surpreendeu os adeptos."
                    ),
                    subtitle="A NOTÍCIA SURPREENDEU",
                    visual_description=(
                        f"Adeptos do {club} num estádio"
                    ),
                    search_query=f"{club} fans stadium",
                ),
                build_scene(
                    scene_number=3,
                    start_second=10,
                    end_second=20,
                    voiceover=(
                        "O impacto desportivo e financeiro seria enorme."
                    ),
                    subtitle="IMPACTO ENORME",
                    visual_description=(
                        "Gráfico animado de transferência entre clubes"
                    ),
                    search_query="football transfer animation",
                ),
                build_scene(
                    scene_number=4,
                    start_second=20,
                    end_second=34,
                    voiceover=(
                        "Mas a informação ainda precisa de confirmação."
                    ),
                    subtitle="AINDA NÃO CONFIRMADO",
                    visual_description=(
                        "Conferência de imprensa de futebol"
                    ),
                    search_query="football press conference",
                ),
                build_scene(
                    scene_number=5,
                    start_second=34,
                    end_second=45,
                    voiceover=(
                        f"Tu colocarias {player} no {club}?"
                    ),
                    subtitle="SIM OU NÃO?",
                    visual_description=(
                        "Montagem rápida do jogador e dos adeptos"
                    ),
                    search_query=f"{player} {club} edit",
                ),
            ],
        },
        "publishing": {
            "urgency": "HIGH",
            "best_publish_time": "18:30",
            "publish_window_minutes": 90,
            "relevance_lifetime_hours": 24,
            "timezone": "Europe/Lisbon",
            "publication_reason": (
                "Tema recente com elevada procura e forte capacidade "
                "de gerar debate."
            ),
        },
        "analytics": {
            "predicted_ctr_percent": 8.5,
            "predicted_retention_percent": 82.0,
            "predicted_views_low": 10000,
            "predicted_views_high": 100000,
            "predicted_comment_rate_percent": 2.5,
            "confidence_score": 65,
            "prediction_basis": (
                "Estimativa editorial inicial sem acesso aos dados "
                "históricos do canal."
            ),
        },
        "checklist": {
            "hook_first_two_seconds": True,
            "duration_valid": True,
            "thumbnail_short": True,
            "call_to_action_present": True,
            "pinned_comment_present": True,
            "sources_require_confirmation": True,
            "missing_assets": [],
        },
    }


def build_example_package() -> dict[str, object]:
    topics = [
        build_topic(
            priority=1,
            topic_id="vinicius-arsenal",
            title="Arsenal tenta contratar Vinícius Júnior",
            player="Vinícius Júnior",
            club="Arsenal",
            source_url="https://example.com/vinicius-arsenal",
            viral_probability=96,
        ),
        build_topic(
            priority=2,
            topic_id="diomande-real-madrid",
            title="Real Madrid aproxima-se de Yan Diomande",
            player="Yan Diomande",
            club="Real Madrid",
            source_url="https://example.com/diomande-real",
            viral_probability=89,
        ),
        build_topic(
            priority=3,
            topic_id="barcola-liverpool",
            title="Liverpool entra na corrida por Barcola",
            player="Bradley Barcola",
            club="Liverpool",
            source_url="https://example.com/barcola-liverpool",
            viral_probability=84,
        ),
        build_topic(
            priority=4,
            topic_id="chiesa-liverpool",
            title="Chiesa procura um novo capítulo",
            player="Federico Chiesa",
            club="Liverpool",
            source_url="https://example.com/chiesa-liverpool",
            viral_probability=76,
        ),
        build_topic(
            priority=5,
            topic_id="miura-59",
            title="Miura volta a marcar aos 59 anos",
            player="Kazuyoshi Miura",
            club="Clube de Miura",
            source_url="https://example.com/miura-59",
            viral_probability=72,
        ),
    ]

    return {
        "schema_version": "2.0",
        "generated_at": "2026-07-27T12:00:00+00:00",
        "channel": "@dinamegaz2014",
        "language": "pt-PT",
        "timezone": "Europe/Lisbon",
        "top_topic_id": "vinicius-arsenal",
        "topics": topics,
    }


def main() -> int:
    raw_package = build_example_package()

    package = parse_editorial_package_dict(
        raw_package
    )

    serialized = serialize_editorial_package(
        package
    )

    reparsed_payload = json.loads(serialized)

    if reparsed_payload != raw_package:
        raise SystemExit(
            "O ciclo JSON → contrato → JSON alterou os dados."
        )

    if len(package.topics) != 5:
        raise SystemExit(
            "O pacote deveria conter exatamente cinco temas."
        )

    if package.top_topic_id != "vinicius-arsenal":
        raise SystemExit(
            "O top_topic_id não foi preservado."
        )

    if package.topics[0].ranking.priority != 1:
        raise SystemExit(
            "A prioridade do primeiro tema não foi preservada."
        )

    if package.topics[0].storyboard.scenes[0].start_second != 0:
        raise SystemExit(
            "A timeline não começa no segundo zero."
        )

    if package.topics[0].storyboard.scenes[-1].end_second != 45:
        raise SystemExit(
            "A timeline não termina na duração prevista."
        )

    print("=" * 78)
    print("EDITORIAL PACKAGE PARSER TEST")
    print("=" * 78)
    print("STATUS: PASS")
    print(f"Schema version: {package.schema_version}")
    print(f"Canal: {package.channel}")
    print(f"Temas: {len(package.topics)}")
    print(f"Top topic: {package.top_topic_id}")
    print(
        "Cenas do tema principal: "
        f"{len(package.topics[0].storyboard.scenes)}"
    )
    print(
        "Duração do tema principal: "
        f"{package.topics[0].storyboard.estimated_duration_seconds}s"
    )
    print(f"JSON serializado: {len(serialized)} caracteres")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
