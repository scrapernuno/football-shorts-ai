from __future__ import annotations

import html
import json
import logging
import sys

from datetime import datetime
from pathlib import Path
from typing import Any


LOGGER = logging.getLogger("football_shorts.render_email")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_DIRECTORY = PROJECT_ROOT / "output"

DIGEST_FILE = OUTPUT_DIRECTORY / "digest.json"

EMAIL_FILE = OUTPUT_DIRECTORY / "digest.html"


class EmailRenderError(RuntimeError):
    """Erro ao renderizar o email."""


def load_digest(path: Path) -> dict[str, Any]:
    """
    Carrega e valida o digest produzido pela IA.
    """

    if not path.exists():
        raise EmailRenderError(
            f"Digest inexistente: {path}"
        )

    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except json.JSONDecodeError as exc:
        raise EmailRenderError(
            "Digest JSON inválido."
        ) from exc

    if not isinstance(payload, dict):
        raise EmailRenderError(
            "A raiz do JSON deve ser um objecto."
        )

    topics = payload.get("topics")

    if not isinstance(topics, list):
        raise EmailRenderError(
            "Campo 'topics' inexistente."
        )

    if len(topics) != 5:
        raise EmailRenderError(
            "São esperados exactamente cinco temas."
        )

    return payload


def escape(value: object) -> str:
    return html.escape(
        str(value if value is not None else ""),
        quote=True,
    )


def format_generated_at(value: object) -> str:

    raw = str(value or "").strip()

    if not raw:
        return "Data desconhecida"

    try:

        dt = datetime.fromisoformat(
            raw.replace("Z", "+00:00")
        )

        return dt.strftime(
            "%d/%m/%Y %H:%M UTC"
        )

    except Exception:

        return raw


def urgency_text(value: object) -> str:

    mapping = {

        "HIGH": "🔥 PUBLICAR JÁ",

        "MEDIUM": "🟡 PUBLICAR HOJE",

        "LOW": "🟢 PODE ESPERAR"

    }

    return mapping.get(
        str(value).upper(),
        "ANALISAR"
    )


def urgency_colour(value: object):

    mapping = {

        "HIGH": (
            "#fee2e2",
            "#991b1b"
        ),

        "MEDIUM": (
            "#fef3c7",
            "#92400e"
        ),

        "LOW": (
            "#dcfce7",
            "#166534"
        )

    }

    return mapping.get(

        str(value).upper(),

        (
            "#e5e7eb",
            "#374151"
        )

    )


def normalise_hashtags(value: object):

    if not isinstance(value, list):
        return []

    result = []

    for tag in value:

        tag = str(tag).strip()

        if not tag:
            continue

        if not tag.startswith("#"):
            tag = "#" + tag

        result.append(tag)

    return result
  def render_topic(
    topic: dict[str, Any],
    position: int,
) -> str:

    background, foreground = urgency_colour(
        topic.get("urgency")
    )

    hashtags = " ".join(
        escape(tag)
        for tag in normalise_hashtags(
            topic.get("hashtags")
        )
    )

    return f"""
<table width="100%"
       cellpadding="0"
       cellspacing="0"
       style="
           background:#ffffff;
           border:1px solid #e5e7eb;
           border-radius:16px;
           margin-bottom:24px;
           font-family:Arial,Helvetica,sans-serif;
       ">

<tr>

<td style="padding:24px;">

<table width="100%">

<tr>

<td>

<div style="
font-size:13px;
font-weight:bold;
color:#6b7280;
text-transform:uppercase;
">

Tema {position}

</div>

</td>

<td align="right">

<span style="
background:{background};
color:{foreground};
padding:8px 12px;
border-radius:999px;
font-size:12px;
font-weight:bold;
">

{escape(urgency_text(topic.get("urgency")))}

</span>

</td>

</tr>

</table>

<h2 style="
margin-top:18px;
margin-bottom:10px;
font-size:28px;
color:#111827;
">

{escape(topic.get("title"))}

</h2>

<div style="
font-size:18px;
font-weight:bold;
color:#dc2626;
margin-bottom:20px;
">

🔥 Potencial Viral:
{escape(topic.get("viral_score"))}/100

</div>

<div style="
background:#eff6ff;
border-left:5px solid #2563eb;
padding:18px;
border-radius:8px;
margin-bottom:20px;
">

<div style="
font-size:12px;
font-weight:bold;
text-transform:uppercase;
color:#2563eb;
margin-bottom:6px;
">

HOOK

</div>

<div style="
font-size:20px;
font-weight:bold;
color:#1d4ed8;
line-height:1.4;
">

"{escape(topic.get("hook"))}"

</div>

</div>

<div style="
background:#f9fafb;
padding:18px;
border-radius:8px;
margin-bottom:20px;
">

<div style="
font-size:12px;
font-weight:bold;
text-transform:uppercase;
color:#6b7280;
margin-bottom:8px;
">

GUIÃO

</div>

<div style="
white-space:pre-line;
font-size:16px;
line-height:1.65;
color:#374151;
">

{escape(topic.get("script"))}

</div>

</div>

<table width="100%">

<tr>

<td width="48%"
    valign="top"
    style="
background:#111827;
padding:16px;
border-radius:8px;
">

<div style="
font-size:11px;
font-weight:bold;
color:#9ca3af;
text-transform:uppercase;
margin-bottom:6px;
">

Thumbnail

</div>

<div style="
font-size:22px;
font-weight:bold;
line-height:1.2;
color:white;
">

{escape(topic.get("thumbnail"))}

</div>

</td>

<td width="4%"></td>

<td width="48%"
    valign="top"
    style="
background:#f3f4f6;
padding:16px;
border-radius:8px;
">

<div style="
font-size:11px;
font-weight:bold;
text-transform:uppercase;
color:#6b7280;
margin-bottom:6px;
">

Porque este tema?

</div>

<div style="
font-size:14px;
line-height:1.6;
color:#374151;
">

{escape(topic.get("reason"))}

</div>

</td>

</tr>

</table>

<div style="
margin-top:18px;
font-size:15px;
color:#2563eb;
line-height:1.7;
">

{hashtags}

</div>

<div style="
margin-top:20px;
padding-top:18px;
border-top:1px solid #e5e7eb;
font-size:13px;
color:#6b7280;
line-height:1.5;
">

<b>Fonte:</b>

<a href="{escape(topic.get('source_url'))}">

{escape(topic.get('source_name'))}

</a>

<br><br>

{escape(topic.get('source_title'))}

</div>

</td>

</tr>

</table>
"""
  def render_email(
    digest: dict[str, Any],
) -> str:

    topics = digest["topics"]

    topic_cards = "\n".join(
        render_topic(
            topic,
            position,
        )
        for position, topic in enumerate(
            topics,
            start=1,
        )
    )

    generated_at = format_generated_at(
        digest.get("generated_at")
    )

    top_topic = topics[0]

    return f"""<!doctype html>
<html lang="pt">
<head>

<meta charset="utf-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<title>Football Shorts AI</title>

</head>

<body style="
margin:0;
padding:0;
background:#f3f4f6;
">

<table width="100%"
       cellpadding="0"
       cellspacing="0"
       style="
background:#f3f4f6;
">

<tr>

<td align="center"
    style="
padding:24px 12px;
">

<table width="100%"
       cellpadding="0"
       cellspacing="0"
       style="
width:100%;
max-width:720px;
">

<tr>

<td style="
background:#0f172a;
padding:30px;
border-radius:18px;
font-family:Arial,Helvetica,sans-serif;
">

<div style="
font-size:13px;
font-weight:bold;
letter-spacing:0.1em;
text-transform:uppercase;
color:#60a5fa;
margin-bottom:10px;
">

Football Shorts AI

</div>

<h1 style="
margin:0 0 12px 0;
font-size:32px;
line-height:1.2;
color:#ffffff;
">

Briefing diário para @dinamegaz2014

</h1>

<div style="
font-size:14px;
color:#cbd5e1;
">

Gerado em {escape(generated_at)}

</div>

</td>

</tr>

<tr>

<td style="height:20px;"></td>

</tr>

<tr>

<td style="
background:#dc2626;
padding:24px;
border-radius:16px;
font-family:Arial,Helvetica,sans-serif;
">

<div style="
font-size:12px;
font-weight:bold;
letter-spacing:0.08em;
text-transform:uppercase;
color:#fee2e2;
margin-bottom:8px;
">

Melhor oportunidade do dia

</div>

<div style="
font-size:28px;
font-weight:bold;
line-height:1.25;
color:#ffffff;
margin-bottom:8px;
">

{escape(top_topic.get("title"))}

</div>

<div style="
font-size:16px;
color:#fee2e2;
">

Potencial viral:

<b>
{escape(top_topic.get("viral_score"))}/100
</b>

·

{escape(urgency_text(top_topic.get("urgency")))}

</div>

</td>

</tr>

<tr>

<td style="height:24px;"></td>

</tr>

<tr>

<td>

{topic_cards}

</td>

</tr>

<tr>

<td style="
padding:20px;
text-align:center;
font-family:Arial,Helvetica,sans-serif;
font-size:12px;
line-height:1.6;
color:#6b7280;
">

Conteúdo gerado automaticamente com base em fontes jornalísticas.

Confirme sempre os factos antes de publicar, sobretudo quando o tema é apresentado como rumor.

</td>

</tr>

</table>

</td>

</tr>

</table>

</body>

</html>
"""
  def save_html(
    path: Path,
    content: str,
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = path.with_suffix(
        ".tmp"
    )

    temporary_path.write_text(
        content,
        encoding="utf-8",
    )

    temporary_path.replace(path)


def configure_logging() -> None:

    logging.basicConfig(

        level=logging.INFO,

        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | "
            "%(message)s"
        ),

    )


def main() -> int:

    configure_logging()

    try:

        digest = load_digest(
            DIGEST_FILE
        )

        html_content = render_email(
            digest
        )

        save_html(
            EMAIL_FILE,
            html_content,
        )

    except EmailRenderError as exc:

        LOGGER.exception(
            "Erro ao renderizar email: %s",
            exc,
        )

        print(
            f"ERRO_RENDER_EMAIL: {exc}",
            file=sys.stderr,
        )

        return 2

    except Exception as exc:

        LOGGER.exception(
            "Erro inesperado: %s",
            exc,
        )

        print(
            f"ERRO_INESPERADO: {exc}",
            file=sys.stderr,
        )

        return 1

    LOGGER.info(
        "Email HTML criado em %s",
        EMAIL_FILE,
    )

    print()

    print("=" * 72)
    print("EMAIL HTML GERADO COM SUCESSO")
    print("=" * 72)
    print(f"Ficheiro: {EMAIL_FILE}")
    print(
        f"Tamanho: {EMAIL_FILE.stat().st_size} bytes"
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )
