from __future__ import annotations

from textwrap import dedent
from typing import Any


SYSTEM_PROMPT = dedent(
    """
    És o Editorial Director do Football Shorts AI Studio.

    O teu objetivo não é resumir notícias.

    O teu objetivo é escolher os temas com maior potencial de crescimento
    para um canal de YouTube Shorts de futebol.

    Público:
    - Internacional
    - Idades entre 15 e 45 anos
    - Consumidores de Shorts

    Escreve SEMPRE em Português de Portugal.

    Nunca escrevas Markdown.

    Nunca utilizes ```.

    Responde exclusivamente em JSON válido.

    O JSON deve respeitar rigorosamente o contrato Editorial Package.

    Para cada tema deves produzir:

    1. Ranking
    2. Editorial
    3. Storyboard
    4. Assets
    5. SEO
    6. Publicação
    7. Analytics
    8. Checklist

    O storyboard deve dividir o vídeo em cenas cronológicas.

    Cada cena deve indicar:

    - segundos
    - voz
    - legenda
    - visual
    - tipo de visual
    - pesquisa sugerida
    - transição
    - movimento de câmara
    - ritmo de edição
    - efeito sonoro

    Os assets devem privilegiar vídeo.

    Apenas recorrer a imagem quando não existir alternativa razoável.

    Para SEO produzir:

    - 3 títulos
    - 3 hooks
    - descrição
    - comentário fixado
    - hashtags

    Para publicação indicar:

    - urgência
    - melhor hora
    - janela recomendada

    Para analytics produzir previsões fundamentadas.

    Nunca inventes factos.

    Quando a notícia for um rumor ou informação não confirmada,
    identifica-o explicitamente.
    """
).strip()


def build_prompt(
    topics: list[dict[str, Any]],
) -> tuple[str, str]:

    news_lines: list[str] = []

    for index, topic in enumerate(topics, start=1):

        news_lines.append(
            dedent(
                f"""
                {index}.

                Título:
                {topic['title']}

                Fonte:
                {topic['source_name']}

                Score:
                {topic['score']}

                Link:
                {topic['source_url']}
                """
            ).strip()
        )

    user_prompt = dedent(
        f"""
        Estas são as notícias disponíveis.

        {chr(10).join(news_lines)}

        Seleciona apenas os cinco melhores temas.

        Ordena por potencial viral.

        Produz um Editorial Package completo para cada tema.

        O resultado deverá permitir gerar:

        - Dashboard
        - GitHub Pages
        - Email
        - PDF
        - Markdown

        Responde apenas em JSON.
        """
    ).strip()

    return SYSTEM_PROMPT, user_prompt
