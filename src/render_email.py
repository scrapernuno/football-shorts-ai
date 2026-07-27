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
    """Erro ao validar ou renderizar o briefing HTML."""


def escape(value: object) -> str:
    return html.escape(
        str(value if value is not None else ""),
        quote=True,
    )


def load_digest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise EmailRenderError(
            f"O ficheiro digest não existe: {path}"
        )

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise EmailRenderError(
            "O digest não contém JSON válido. "
            f"Linha={exc.lineno}; coluna={exc.colno}"
        ) from exc

    if not isinstance(payload, dict):
        raise EmailRenderError(
            "A raiz do digest deve ser um objeto JSON."
        )

    topics = payload.get("topics")

    if not isinstance(topics, list) or len(topics) != 5:
        raise EmailRenderError(
            "O digest deve conter exatamente cinco temas."
        )

    for index, topic in enumerate(topics, start=1):
        if not isinstance(topic, dict):
            raise EmailRenderError(
                f"O tema {index} não é um objeto JSON."
            )

    return payload


def format_generated_at(value: object) -> str:
    raw_value = str(value or "").strip()

    if not raw_value:
        return "Data não disponível"

    try:
        parsed = datetime.fromisoformat(
            raw_value.replace("Z", "+00:00")
        )
    except ValueError:
        return raw_value

    return parsed.strftime("%d/%m/%Y às %H:%M UTC")


def urgency_label(value: object) -> str:
    return {
        "HIGH": "🔥 PUBLICAR JÁ",
        "MEDIUM": "🟡 PUBLICAR HOJE",
        "LOW": "🟢 PODE AGUARDAR",
    }.get(
        str(value or "").upper(),
        "ANALISAR",
    )


def urgency_colours(value: object) -> tuple[str, str]:
    return {
        "HIGH": ("#fee2e2", "#991b1b"),
        "MEDIUM": ("#fef3c7", "#92400e"),
        "LOW": ("#dcfce7", "#166534"),
    }.get(
        str(value or "").upper(),
        ("#e5e7eb", "#374151"),
    )


def normalize_hashtags(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    result: list[str] = []

    for item in value:
        tag = str(item).strip()

        if not tag:
            continue

        if not tag.startswith("#"):
            tag = f"#{tag}"

        result.append(tag)

    return result


def render_topic(
    topic: dict[str, Any],
    position: int,
) -> str:
    badge_background, badge_foreground = urgency_colours(
        topic.get("urgency")
    )

    hashtags = " ".join(
        escape(tag)
        for tag in normalize_hashtags(
            topic.get("hashtags")
        )
    )

    title = escape(topic.get("title"))
    hook = escape(topic.get("hook"))
    script = escape(topic.get("script"))
    thumbnail = escape(topic.get("thumbnail"))
    reason = escape(topic.get("reason"))
    viral_score = escape(topic.get("viral_score"))
    source_name = escape(topic.get("source_name"))
    source_title = escape(topic.get("source_title"))
    source_url = escape(topic.get("source_url"))
    urgency = escape(
        urgency_label(topic.get("urgency"))
    )

    return f"""
<table role="presentation"
       width="100%"
       cellpadding="0"
       cellspacing="0"
       border="0"
       style="
         margin:0 0 24px 0;
         background:#ffffff;
         border:1px solid #e5e7eb;
         border-radius:16px;
         font-family:Arial,Helvetica,sans-serif;
       ">
  <tr>
    <td style="padding:24px;">
      <table role="presentation"
             width="100%"
             cellpadding="0"
             cellspacing="0"
             border="0">
        <tr>
          <td style="
                font-size:13px;
                font-weight:700;
                color:#6b7280;
                text-transform:uppercase;
                letter-spacing:0.08em;
              ">
            Prioridade {position}
          </td>

          <td align="right">
            <span style="
                  display:inline-block;
                  padding:7px 12px;
                  border-radius:999px;
                  background:{badge_background};
                  color:{badge_foreground};
                  font-size:12px;
                  font-weight:700;
                ">
              {urgency}
            </span>
          </td>
        </tr>
      </table>

      <h2 style="
            margin:18px 0 8px 0;
            font-size:26px;
            line-height:1.25;
            color:#111827;
          ">
        {title}
      </h2>

      <div style="
            margin-bottom:20px;
            font-size:17px;
            font-weight:700;
            color:#dc2626;
          ">
        Potencial viral: {viral_score}/100
      </div>

      <div style="
            margin-bottom:18px;
            padding:16px;
            background:#eff6ff;
            border-left:4px solid #2563eb;
            border-radius:8px;
          ">
        <div style="
              margin-bottom:6px;
              font-size:12px;
              font-weight:700;
              color:#1d4ed8;
              text-transform:uppercase;
              letter-spacing:0.06em;
            ">
          Gancho — primeiros 2 segundos
        </div>

        <div style="
              font-size:19px;
              font-weight:700;
              line-height:1.4;
              color:#1e3a8a;
            ">
          “{hook}”
        </div>
      </div>

      <div style="
            margin-bottom:18px;
            padding:16px;
            background:#f9fafb;
            border-radius:8px;
          ">
        <div style="
              margin-bottom:8px;
              font-size:12px;
              font-weight:700;
              color:#4b5563;
              text-transform:uppercase;
              letter-spacing:0.06em;
            ">
          Guião
        </div>

        <div style="
              white-space:pre-line;
              font-size:16px;
              line-height:1.65;
              color:#1f2937;
            ">
          {script}
        </div>
      </div>

      <table role="presentation"
             width="100%"
             cellpadding="0"
             cellspacing="0"
             border="0"
             style="margin-bottom:18px;">
        <tr>
          <td width="48%"
              valign="top"
              style="
                padding:14px;
                background:#111827;
                border-radius:8px;
              ">
            <div style="
                  margin-bottom:6px;
                  font-size:11px;
                  font-weight:700;
                  color:#9ca3af;
                  text-transform:uppercase;
                ">
              Thumbnail
            </div>

            <div style="
                  font-size:20px;
                  font-weight:800;
                  line-height:1.2;
                  color:#ffffff;
                ">
              {thumbnail}
            </div>
          </td>

          <td width="4%"></td>

          <td width="48%"
              valign="top"
              style="
                padding:14px;
                background:#f3f4f6;
                border-radius:8px;
              ">
            <div style="
                  margin-bottom:6px;
                  font-size:11px;
                  font-weight:700;
                  color:#6b7280;
                  text-transform:uppercase;
                ">
              Porque este tema?
            </div>

            <div style="
                  font-size:14px;
                  line-height:1.5;
                  color:#374151;
                ">
              {reason}
            </div>
          </td>
        </tr>
      </table>

      <div style="
            margin-bottom:18px;
            font-size:14px;
            line-height:1.7;
            color:#2563eb;
          ">
        {hashtags}
      </div>

      <div style="
            padding-top:16px;
            border-top:1px solid #e5e7eb;
            font-size:13px;
            line-height:1.5;
            color:#6b7280;
          ">
        Fonte:
        <a href="{source_url}"
           style="
             color:#2563eb;
             text-decoration:none;
             font-weight:700;
           ">
          {source_name}
        </a>
        <br>
        {source_title}
      </div>
    </td>
  </tr>
</table>
"""


def render_email(digest: dict[str, Any]) -> str:
    topics = digest["topics"]
    top_topic = topics[0]

    cards = "\n".join(
        render_topic(topic, position)
        for position, topic in enumerate(
            topics,
            start=1,
        )
    )

    generated_at = escape(
        format_generated_at(
            digest.get("generated_at")
        )
    )

    top_title = escape(top_topic.get("title"))
    top_score = escape(top_topic.get("viral_score"))
    top_urgency = escape(
        urgency_label(top_topic.get("urgency"))
    )

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
  <table role="presentation"
         width="100%"
         cellpadding="0"
         cellspacing="0"
         border="0"
         style="background:#f3f4f6;">
    <tr>
      <td align="center"
          style="padding:24px 12px;">
        <table role="presentation"
               width="100%"
               cellpadding="0"
               cellspacing="0"
               border="0"
               style="
                 width:100%;
                 max-width:720px;
               ">
          <tr>
            <td style="
                  padding:30px;
                  background:#0f172a;
                  border-radius:18px;
                  font-family:Arial,Helvetica,sans-serif;
                ">
              <div style="
                    margin-bottom:10px;
                    font-size:13px;
                    font-weight:700;
                    color:#60a5fa;
                    letter-spacing:0.1em;
                    text-transform:uppercase;
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
                Gerado em {generated_at}
              </div>
            </td>
          </tr>

          <tr>
            <td style="height:20px;"></td>
          </tr>

          <tr>
            <td style="
                  padding:24px;
                  background:#dc2626;
                  border-radius:16px;
                  font-family:Arial,Helvetica,sans-serif;
                ">
              <div style="
                    margin-bottom:8px;
                    font-size:12px;
                    font-weight:700;
                    color:#fee2e2;
                    letter-spacing:0.08em;
                    text-transform:uppercase;
                  ">
                Melhor oportunidade do dia
              </div>

              <div style="
                    margin-bottom:8px;
                    font-size:27px;
                    font-weight:800;
                    line-height:1.25;
                    color:#ffffff;
                  ">
                {top_title}
              </div>

              <div style="
                    font-size:16px;
                    color:#fee2e2;
                  ">
                Potencial viral:
                <strong>{top_score}/100</strong>
                · {top_urgency}
              </div>
            </td>
          </tr>

          <tr>
            <td style="height:24px;"></td>
          </tr>

          <tr>
            <td>
              {cards}
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
              Conteúdo gerado automaticamente com base em fontes
              jornalísticas. Confirme sempre os factos antes de publicar,
              sobretudo quando o tema é apresentado como rumor.
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def save_html(path: Path, content: str) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = path.with_suffix(
        f"{path.suffix}.tmp"
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
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
    )


def main() -> int:
    configure_logging()

    try:
        digest = load_digest(DIGEST_FILE)
        email_content = render_email(digest)
        save_html(EMAIL_FILE, email_content)

    except EmailRenderError as exc:
        LOGGER.exception(
            "Falha ao renderizar o email: %s",
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
    print(f"Tamanho: {EMAIL_FILE.stat().st_size} bytes")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
