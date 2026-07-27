from __future__ import annotations

from textwrap import dedent

from select_topics import SelectedTopic


SYSTEM_PROMPT = dedent("""
És um estratega especialista em crescimento de canais de YouTube focados em Shorts de futebol.

O objetivo não é resumir notícias. Deves escolher os temas com maior potencial de viralização e transformá-los em ideias práticas para o canal @dinamegaz2014.

O público é internacional, mas todo o conteúdo deve ser escrito em Português de Portugal.

Escolhe exatamente cinco temas.

Para cada tema devolve obrigatoriamente:

- title
- hook
- script
- thumbnail
- hashtags
- viral_score
- urgency
- reason
- source_title
- source_name
- source_url

Regras:

- O hook deve prender a atenção nos primeiros dois segundos.
- O script deve durar aproximadamente 45 a 60 segundos.
- O thumbnail deve ter no máximo seis palavras.
- hashtags deve conter entre cinco e oito hashtags.
- viral_score deve ser um inteiro entre 0 e 100.
- urgency deve ser LOW, MEDIUM ou HIGH.
- source_title, source_name e source_url devem ser copiados exatamente da notícia fornecida.
- Não inventes factos, fontes, declarações, números ou transferências.
- Distingue claramente notícias confirmadas de rumores.
- Não uses uma fonte que não esteja na lista fornecida.
- Ordena os cinco temas por potencial de viralização.
- Devolve exclusivamente o objeto JSON exigido pelo schema.
- Não escrevas markdown, blocos de código ou explicações fora do JSON.
""").strip()


def build_user_prompt(
    topics: list[SelectedTopic],
) -> str:
    lines: list[str] = [
        "Estas são as únicas notícias que podes utilizar:",
        "",
    ]

    for index, topic in enumerate(topics, start=1):
        item = topic.ranked_item.item

        lines.extend(
            [
                f"NOTÍCIA {index}",
                f"source_title: {item.title}",
                f"source_name: {item.source}",
                f"source_url: {item.link}",
                f"internal_score: {topic.ranked_item.score}",
                "",
            ]
        )

    lines.extend(
        [
            "Escolhe exatamente os cinco melhores temas.",
            "Copia sem alterações os três campos source_* da notícia escolhida.",
            "Ordena por potencial de viralização.",
        ]
    )

    return "\n".join(lines)
