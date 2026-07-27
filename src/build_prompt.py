from __future__ import annotations

from textwrap import dedent

from select_topics import SelectedTopic


SYSTEM_PROMPT = dedent("""
És um estratega especialista em crescimento de canais de YouTube focados em Shorts de futebol.

O teu objetivo NÃO é resumir notícias.

O teu objetivo é escolher os temas com maior potencial de viralização.

O público é internacional.

Escreve sempre em Português de Portugal.

Devolve exclusivamente JSON válido.

Nunca escrevas markdown.

Nunca utilizes ```.

Nunca escrevas explicações.

Para cada tema devolve:

title
hook
script
thumbnail
hashtags
viral_score
urgency
reason

O hook deve prender a atenção nos primeiros 2 segundos.

O script deve durar entre 45 e 60 segundos.

O thumbnail deve ter no máximo 6 palavras.

hashtags deve conter entre 5 e 8 hashtags.

viral_score deve ser um inteiro entre 0 e 100.

urgency deve ser:

LOW
MEDIUM
HIGH

Escolhe apenas os 5 melhores temas.
""").strip()


def build_user_prompt(
    topics: list[SelectedTopic],
) -> str:

    lines = []

    lines.append(
        "Estas são as notícias disponíveis:\n"
    )

    for index, topic in enumerate(topics, start=1):

        item = topic.ranked_item.item

        lines.append(
            f"{index}. "
            f"{item.title}\n"
            f"Fonte: {item.source}\n"
            f"Score: {topic.ranked_item.score}\n"
            f"Link: {item.link}\n"
        )

    lines.append(
        dedent("""
        Escolhe apenas os cinco melhores temas.

        Ordena por potencial de viralização.

        Responde apenas em JSON.
        """)
    )

    return "\n".join(lines)
